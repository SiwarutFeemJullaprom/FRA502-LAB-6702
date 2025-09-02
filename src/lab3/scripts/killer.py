#!/usr/bin/python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from turtlesim.srv import Kill
from std_msgs.msg import Bool
# Import Service ใหม่ที่เราสร้างขึ้น
from controller_interfaces.srv import SetParam
import math

class KillerNode(Node):
    def __init__(self):
        super().__init__('killer_node')

        # === 1. PARSE PARAMETERS ===
        self.declare_parameter('sampling_frequency', 100.0)
        # รับชื่อของ Eater มาจาก launch file เพื่อใช้เป็นเป้าหมาย
        self.declare_parameter('eater_name', 'eater') 
        frequency = self.get_parameter('sampling_frequency').get_parameter_value().double_value
        self.timer_period = 1.0 / frequency
        eater_name = self.get_parameter('eater_name').get_parameter_value().string_value

        # === 2. INITIALIZE VARIABLES ===
        self.kp_linear = 2.0
        self.kp_angular = 10.0
        self.turtle_name = self.get_namespace().replace('/', '')
        self.get_logger().info(f"Killer node for '{self.turtle_name}' has been started.")

        # ตัวแปรสถานะ
        self.target_pose = None
        self.current_pose = [0.0, 0.0, 0.0]
        self.controller_enable = False
        self.is_eater_eating = True # เริ่มต้นโดยสมมติว่า Eater ยังไม่พร้อมให้ล่า

        # === 3. CREATE ROS COMMUNICATIONS ===
        # -- Publisher --
        self.pub_cmdvel = self.create_publisher(Twist, f'/{self.turtle_name}/cmd_vel', 10)
        
        # -- Subscribers --
        # รับตำแหน่งของตัวเอง
        self.create_subscription(Pose, f'/{self.turtle_name}/pose', self.pose_callback, 10)
        # รับตำแหน่งของเป้าหมาย (Eater)
        self.create_subscription(Pose, f'/{eater_name}/pose', self.target_callback, 10)
        # รับสถานะการกินของ Eater เพื่อใช้เป็น "สัญญาณ" เริ่ม/หยุด การไล่ล่า
        self.create_subscription(Bool, f'/{eater_name}/eat_status', self.eat_status_callback, 10)

        # -- Service Server --
        self.srv_set_param = self.create_service(SetParam, f'/{self.turtle_name}/set_param', self.set_param_callback)

        # -- Service Client --
        self.remove_turtle_client = self.create_client(Kill, '/remove_turtle')

        # === 4. CREATE TIMER ===
        self.timer = self.create_timer(self.timer_period, self.timer_callback)

    # --- SERVICE SERVER & SUBSCRIBER CALLBACKS ---
    # อัปเดตค่า Gain เมื่อได้รับ request
    def set_param_callback(self, request, response):
        self.kp_linear = float(request.kp_linear)
        self.kp_angular = float(request.kp_angular)
        self.get_logger().info(f"Controller gains updated: kp_linear={self.kp_linear}, kp_angular={self.kp_angular}")
        return response

    # อัปเดตตำแหน่งเป้าหมาย
    def target_callback(self, msg: Pose):
        self.target_pose = [msg.x, msg.y]

    # อัปเดตตำแหน่งตัวเอง
    def pose_callback(self, msg: Pose):
        self.current_pose = [msg.x, msg.y, msg.theta]

    # ฟังก์ชันที่สำคัญที่สุด! ใช้ในการตัดสินใจเริ่ม/หยุด การไล่ล่า
    def eat_status_callback(self, msg: Bool):
        if not msg.data: # ถ้า Eater ไม่ได้กำลังกิน (แปลว่าพิซซ่าหมดแล้ว)
            self.is_eater_eating = False
            self.controller_enable = True # เปิดระบบควบคุมการไล่ล่า
            self.get_logger().info("Eater has finished eating. Engaging chase mode!")
        else: # ถ้า Eater กลับไปกินอีก (มีการสร้างพิซซ่าใหม่)
            self.is_eater_eating = True
            self.controller_enable = False # ปิดระบบควบคุมการไล่ล่าชั่วคราว
            self.get_logger().info("Eater is eating again. Pausing chase.")

    # --- HELPER FUNCTIONS ---
    # เรียก service ลบเต่าเป้าหมาย
    def kill_turtle(self, name: str):
        if not self.remove_turtle_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("Service /remove_turtle not available.")
            return
            
        request = Kill.Request()
        request.name = name
        self.remove_turtle_client.call_async(request)

    # ส่งคำสั่งความเร็ว
    def cmd_vel(self, vx, w):
        msg = Twist()
        msg.linear.x = vx
        msg.angular.z = w
        self.pub_cmdvel.publish(msg)

    # --- MAIN CONTROL LOOP ---
    def timer_callback(self):
        # ถ้ายังไม่ถึงเวลาไล่ล่า หรือยังไม่เห็นเป้าหมาย ก็ไม่ต้องทำอะไร
        if not self.controller_enable or self.target_pose is None:
            return

        # P-Controller Logic สำหรับการไล่ล่า
        dx = self.target_pose[0] - self.current_pose[0]
        dy = self.target_pose[1] - self.current_pose[1]
        e_dis = math.hypot(dx, dy)
        e_ori = math.atan2(dy, dx) - self.current_pose[2]
        e_ori = math.atan2(math.sin(e_ori), math.cos(e_ori))

        u_dis = self.kp_linear * e_dis
        u_ori = self.kp_angular * e_ori

        if e_dis < 0.5: # ถ้าไล่ทันแล้ว
            self.cmd_vel(0.0, 0.0) # หยุด
            self.kill_turtle(self.get_parameter('eater_name').get_parameter_value().string_value) # สั่งลบเป้าหมาย
            self.controller_enable = False # ปิดการควบคุม
            self.get_logger().info("Target caught! Killer standing by.")
            self.timer.cancel() # หยุดการทำงานของ timer ไปเลย
        else: # ถ้ายังไกล
            self.cmd_vel(u_dis, u_ori) # ไล่ต่อไป

def main(args=None):
    rclpy.init(args=args)
    node = KillerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__=='__main__':
    main()