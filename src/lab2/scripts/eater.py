#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point, PoseStamped
from turtlesim.msg import Pose
from turtlesim_plus_interfaces.srv import GivePosition
from std_srvs.srv import Empty
from std_msgs.msg import Int64
import pygame
import math

class EaterNode(Node):
    def __init__(self):
        super().__init__('eater_node')
        
        self.FORAGE_MODE = 0
        self.EVADE_MODE = 1
        self.current_mode_ = self.FORAGE_MODE
        self.game_started_ = False

        self.turtle1_pose_ = None
        self.pizza_locations_ = []
        self.current_target_ = None
        
        # <<<<<<< ตัวแปรสำหรับนับ Pizza ของเราเอง
        self.internal_pizza_count_ = 0

        # <<<<<<< สร้าง Publisher สำหรับ Pizza Count ที่ถูกต้อง
        self.correct_pizza_count_pub_ = self.create_publisher(Int64, '/correct_pizza_count', 10)

        self.vel_publisher_ = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.pose_subscriber_ = self.create_subscription(
            Pose, '/turtle1/pose', self.pose_callback, 10)
        
        self.mouse_subscriber_ = self.create_subscription(
            Point, '/mouse_position', self.mouse_callback, 10)
        self.goal_pose_subscriber_ = self.create_subscription(
            PoseStamped, '/goal_pose', self.goal_pose_callback, 10)
            
        # ไม่ต้อง Subscribe /turtle1/pizza_count ของ simulator อีกต่อไป

        self.spawn_pizza_client_ = self.create_client(GivePosition, '/spawn_pizza')
        self.eat_client_ = self.create_client(Empty, '/turtle1/eat')

        pygame.init()
        pygame.display.set_mode((100, 100))
        
        self.timer = self.create_timer(0.1, self.control_loop_callback)
        self.get_logger().info('Eater node has been started in FORAGE MODE.')

    def pose_callback(self, msg: Pose):
        self.turtle1_pose_ = msg
        
    def mouse_callback(self, msg: Point):
        if self.current_mode_ == self.FORAGE_MODE:
            self.spawn_pizza_at(msg.x, msg.y)
        elif self.current_mode_ == self.EVADE_MODE:
            self.current_target_ = (msg.x, msg.y)

    def goal_pose_callback(self, msg: PoseStamped):
        if self.current_mode_ == self.FORAGE_MODE:
            self.spawn_pizza_at(msg.pose.position.x, msg.pose.position.y)
        elif self.current_mode_ == self.EVADE_MODE:
            self.current_target_ = (msg.pose.position.x, msg.pose.position.y)
            
    def control_loop_callback(self):
        if self.current_mode_ == self.FORAGE_MODE and not self.current_target_ and self.pizza_locations_:
            self.current_target_ = self.pizza_locations_[0]

        vel_msg = self.calculate_velocity(self.current_target_)
        self.vel_publisher_.publish(vel_msg)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                teleop_vel = Twist()
                if event.key == pygame.K_UP: teleop_vel.linear.x = 2.0
                elif event.key == pygame.K_DOWN: teleop_vel.linear.x = -2.0
                elif event.key == pygame.K_LEFT: teleop_vel.angular.z = 2.0
                elif event.key == pygame.K_RIGHT: teleop_vel.angular.z = -2.0
                self.vel_publisher_.publish(teleop_vel)
                self.current_target_ = None

    def calculate_velocity(self, target):
        vel_msg = Twist()
        if target is None: return vel_msg
        if self.turtle1_pose_ is None:
            self.get_logger().warn("Waiting for initial pose...")
            return vel_msg
        target_x, target_y = target
        pose = self.turtle1_pose_
        dist_x = target_x - pose.x
        dist_y = target_y - pose.y
        distance = math.sqrt(dist_x**2 + dist_y**2)
        if distance < 0.5:
            if self.current_mode_ == self.FORAGE_MODE: self.call_eat_service()
            else: self.current_target_ = None
        else:
            angle_to_target = math.atan2(dist_y, dist_x)
            angle_diff = angle_to_target - pose.theta
            if angle_diff > math.pi: angle_diff -= 2 * math.pi
            elif angle_diff < -math.pi: angle_diff += 2 * math.pi
            if abs(angle_diff) > 0.1:
                vel_msg.linear.x = 0.0
                vel_msg.angular.z = 2.0 * angle_diff
            else:
                vel_msg.linear.x = 1.5 * distance
                vel_msg.angular.z = 0.0
        return vel_msg

    def spawn_pizza_at(self, x, y):
        if not self.spawn_pizza_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Service /spawn_pizza not available.')
            return
        request = GivePosition.Request()
        request.x = x
        request.y = y
        future = self.spawn_pizza_client_.call_async(request)
        future.add_done_callback(lambda f: self.spawn_pizza_callback(f, (x, y)))

    def spawn_pizza_callback(self, future, location):
        try:
            future.result()
            self.pizza_locations_.append(location)
            # <<<<<<< เพิ่มจำนวน Pizza และประกาศให้โลกรู้
            self.internal_pizza_count_ += 1
            count_msg = Int64()
            count_msg.data = self.internal_pizza_count_
            self.correct_pizza_count_pub_.publish(count_msg)
        except Exception as e: self.get_logger().error(f'Service call failed {e}')
            
    def call_eat_service(self):
        if not self.eat_client_.wait_for_service(timeout_sec=1.0): return
        request = Empty.Request()
        future = self.eat_client_.call_async(request)
        future.add_done_callback(self.eat_callback)

    def eat_callback(self, future):
        try:
            future.result()
            eaten_pizza = self.current_target_
            if eaten_pizza in self.pizza_locations_:
                self.pizza_locations_.remove(eaten_pizza)
            self.current_target_ = None
            
            # <<<<<<< ลดจำนวน Pizza และประกาศให้โลกรู้
            self.internal_pizza_count_ -= 1
            count_msg = Int64()
            count_msg.data = self.internal_pizza_count_
            self.correct_pizza_count_pub_.publish(count_msg)
            
            # <<<<<<< เช็คการเปลี่ยนโหมดโดยใช้ค่าของตัวเอง
            if self.internal_pizza_count_ == 0:
                self.current_mode_ = self.EVADE_MODE
                self.get_logger().info('All pizzas eaten! Switching to EVADE MODE.')

        except Exception as e: self.get_logger().error(f'Service call failed {e}')

def main(args=None):
    rclpy.init(args=args)
    node = EaterNode()
    rclpy.spin(node)
    node.destroy_node()
    pygame.quit()
    rclpy.shutdown()

if __name__ == '__main__': main()