#!/usr/bin/python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point, PoseStamped
from turtlesim.msg import Pose
from std_msgs.msg import Bool, Int64
from std_srvs.srv import Empty
from turtlesim_plus_interfaces.srv import GivePosition
# Import Service ใหม่ที่เราสร้างขึ้น
from controller_interfaces.srv import SetMaxPizza, SetParam
import math

class EaterNode(Node):
    def __init__(self):
        super().__init__('eater_node')

        # === 1. PARSE PARAMETERS ===
        # ประกาศและรับค่า Parameter 'sampling_frequency' จาก launch file, ถ้าไม่มีให้ใช้ค่า default 100.0
        self.declare_parameter('sampling_frequency', 100.0)
        frequency = self.get_parameter('sampling_frequency').get_parameter_value().double_value
        self.timer_period = 1.0 / frequency # แปลงความถี่เป็นคาบเวลาสำหรับ Timer

        # === 2. INITIALIZE VARIABLES ===
        # ตัวแปรสำหรับเก็บค่า Gain ของ P-Controller
        self.kp_linear = 2.0
        self.kp_angular = 10.0
        
        # ใช้ชื่อ Namespace ที่ได้รับจาก launch file เป็นชื่อของเต่า
        self.turtle_name = self.get_namespace().replace('/', '')
        self.get_logger().info(f"Eater node for '{self.turtle_name}' has been started.")

        # ตัวแปรสำหรับจัดการสถานะและเป้าหมาย
        self.max_pizza = 5
        self.pizza_cnt = 0
        self.target_queue = []
        self.current_target = None
        self.current_pose = [0.0, 0.0, 0.0]
        self.controller_enable = False
        self.is_foraging = True # สถานะเริ่มต้นคือการหาพิซซ่า

        # === 3. CREATE ROS COMMUNICATIONS ===
        # -- Publishers --
        # Publisher สำหรับส่งคำสั่งความเร็วไปยังเต่า
        self.pub_cmdvel = self.create_publisher(Twist, f'/{self.turtle_name}/cmd_vel', 10)
        # Publisher สำหรับประกาศสถานะการกิน (True = กำลังกิน, False = กินเสร็จ/ว่าง)
        self.pub_eat_status = self.create_publisher(Bool, f'/{self.turtle_name}/eat_status', 10)
        
        # -- Subscribers --
        # Subscriber รับข้อมูลตำแหน่งของตัวเอง
        self.create_subscription(Pose, f'/{self.turtle_name}/pose', self.pose_callback, 10)
        # Subscriber รับตำแหน่งคลิกจากหน้าต่าง Turtlesim+
        self.create_subscription(Point, '/mouse_position', self.mouse_position_callback, 10)
        # Subscriber รับตำแหน่งคลิกจาก RViz
        self.create_subscription(PoseStamped, '/goal_pose', self.rviz_position_callback, 10)
        
        # -- Service Servers --
        # Service Server สำหรับตั้งค่าจำนวนพิซซ่าสูงสุด
        self.srv_set_max_pizza = self.create_service(SetMaxPizza, f'/{self.turtle_name}/set_max_pizza', self.set_max_pizza_callback)
        # Service Server สำหรับตั้งค่า Gain ของ Controller
        self.srv_set_param = self.create_service(SetParam, f'/{self.turtle_name}/set_param', self.set_param_callback)

        # -- Service Clients --
        # Service Client สำหรับเรียก service สร้างพิซซ่า
        self.spawn_pizza_client = self.create_client(GivePosition, '/spawn_pizza')
        # Service Client สำหรับเรียก service กินพิซซ่า
        self.eat_pizza_client = self.create_client(Empty, f'/{self.turtle_name}/eat')

        # === 4. CREATE TIMER ===
        # สร้าง Timer เพื่อเรียกฟังก์ชันควบคุมหลัก (timer_callback) ตามความถี่ที่กำหนด
        self.timer = self.create_timer(self.timer_period, self.timer_callback)

    # --- SERVICE SERVER CALLBACKS ---
    # ฟังก์ชันที่จะทำงานเมื่อมีคนเรียก Service /set_max_pizza
    def set_max_pizza_callback(self, request, response):
        current_max = self.max_pizza
        self.max_pizza = request.max_pizza.data
        
        log_msg = f"Max pizza changed from {current_max} to {self.max_pizza}."
        # สร้างข้อความตอบกลับ (response) ตามเงื่อนไขในโจทย์
        if self.max_pizza > current_max:
            response.log.data = f"Success: {log_msg}"
        else:
            response.log.data = f"Failed: {log_msg} (New max must be greater than current)"

        self.get_logger().info(response.log.data)
        return response

    # ฟังก์ชันที่จะทำงานเมื่อมีคนเรียก Service /set_param
    def set_param_callback(self, request, response):
        self.kp_linear = float(request.kp_linear.data)
        self.kp_angular = float(request.kp_angular.data)
        self.get_logger().info(f"Controller gains updated: kp_linear={self.kp_linear}, kp_angular={self.kp_angular}")
        return response

    # --- SUBSCRIBER CALLBACKS ---
    # อัปเดตตำแหน่งปัจจุบันของเต่าทุกครั้งที่ได้รับข้อมูลใหม่
    def pose_callback(self, msg: Pose):
        self.current_pose = [msg.x, msg.y, msg.theta]

    # จัดการเมื่อมีการคลิกในหน้าต่าง Turtlesim+
    def mouse_position_callback(self, msg: Point):
        self.add_target([msg.x, msg.y])

    # จัดการเมื่อมีการคลิก "2D Goal Pose" ใน RViz
    def rviz_position_callback(self, msg: PoseStamped):
        # แปลงพิกัดจาก RViz (จุด 0,0 อยู่ตรงกลาง) เป็น Turtlesim+ (จุด 0,0 อยู่มุมล่างซ้าย)
        point = [msg.pose.position.x + 5.5, msg.pose.position.y + 5.5]
        self.add_target(point)

    # --- HELPER FUNCTIONS ---
    # ฟังก์ชันกลางสำหรับจัดการเป้าหมายที่เข้ามา
    def add_target(self, point):
        if self.is_foraging: # ถ้าอยู่ในโหมดหาพิซซ่า
            if self.pizza_cnt < self.max_pizza:
                self.target_queue.append(point) # เพิ่มเป้าหมายใหม่เข้าคิว
                self.spawn_pizza(point) # เรียก service สร้างพิซซ่า
        else: # ถ้าอยู่ในโหมดหลบหนี
            self.target_queue = [point] # ให้ไปที่เป้าหมายใหม่ล่าสุดเท่านั้น

    # เรียก service สร้างพิซซ่า และนับจำนวน
    def spawn_pizza(self, position):
        request = GivePosition.Request()
        request.x, request.y = position
        self.spawn_pizza_client.call_async(request)
        self.pizza_cnt += 1

    # เรียก service กินพิซซ่า, ประกาศสถานะ, และเปลี่ยนโหมดถ้าจำเป็น
    def eat_pizza(self):
        request = Empty.Request()
        self.eat_pizza_client.call_async(request)
        
        # ประกาศให้โลกรู้ว่า "กำลังจะกิน" (True)
        status_msg = Bool()
        status_msg.data = True
        self.pub_eat_status.publish(status_msg)
        
        self.pizza_cnt -= 1 # ลดจำนวนพิซซ่าที่นับไว้
        
        # ประกาศให้โลกรู้ว่า "กินเสร็จแล้ว / ว่าง" (False)
        status_msg.data = False
        self.pub_eat_status.publish(status_msg)

        # ถ้าจำนวนพิซซ่าเป็น 0 ให้เปลี่ยนเป็นโหมดหลบหนี
        if self.pizza_cnt == 0:
            self.is_foraging = False
            self.get_logger().info("All pizzas eaten! Switching to EVADE mode.")

    # ฟังก์ชันสำหรับส่งคำสั่งความเร็ว
    def cmd_vel(self, vx, w):
        msg = Twist()
        msg.linear.x = vx
        msg.angular.z = w
        self.pub_cmdvel.publish(msg)

    # --- MAIN CONTROL LOOP ---
    # ฟังก์ชันที่ถูกเรียกซ้ำๆ ตามความถี่ที่กำหนด
    def timer_callback(self):
        # ถ้ามีเป้าหมายในคิวและยังไม่มีเป้าหมายปัจจุบัน ให้ดึงเป้าหมายใหม่ออกมาจากคิว
        if len(self.target_queue) > 0 and not self.controller_enable:
            self.current_target = self.target_queue.pop(0)
            self.controller_enable = True

        # ถ้าไม่มีเป้าหมาย ก็ไม่ต้องทำอะไร
        if not self.controller_enable or self.current_target is None:
            return

        # --- P-Controller Logic ---
        # คำนวณค่า error (ระยะทางและมุมที่ต่างจากเป้าหมาย)
        dx = self.current_target[0] - self.current_pose[0]
        dy = self.current_target[1] - self.current_pose[1]
        e_dis = math.hypot(dx, dy)
        e_ori = math.atan2(dy, dx) - self.current_pose[2]
        e_ori = math.atan2(math.sin(e_ori), math.cos(e_ori))

        # คำนวณคำสั่งควบคุมจากค่า error และ gain
        u_dis = self.kp_linear * e_dis
        u_ori = self.kp_angular * e_ori

        # เงื่อนไขการทำงานของ Controller
        if e_dis < 0.2: # ถ้าเข้าใกล้เป้าหมายมากพอ
            self.cmd_vel(0.0, 0.0) # หยุด
            if self.is_foraging:
                self.eat_pizza() # ถ้าอยู่ในโหมดหาพิซซ่า ให้กิน
            self.controller_enable = False # ปิดการควบคุมชั่วคราว
            self.current_target = None # ล้างเป้าหมายปัจจุบัน
        else: # ถ้ายังอยู่ไกลจากเป้าหมาย
            self.cmd_vel(u_dis, u_ori) # เคลื่อนที่ต่อไป

def main(args=None):
    rclpy.init(args=args)
    node = EaterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__=='__main__':
    main()