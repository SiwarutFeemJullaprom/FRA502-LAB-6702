#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import Twist
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from turtlesim.srv import Kill
from std_msgs.msg import Int64
import math

class KillerNode(Node):
    def __init__(self):
        super().__init__('killer_node')

        self.WAITING_MODE = 0
        self.CHASING_MODE = 1
        self.current_mode_ = self.WAITING_MODE
        self.game_started_ = False
        
        self.tf_buffer_ = Buffer()
        self.tf_listener_ = TransformListener(self.tf_buffer_, self)

        self.vel_publisher_ = self.create_publisher(Twist, '/turtle2/cmd_vel', 10)
        
        self.remove_turtle_client_ = self.create_client(Kill, '/remove_turtle')
        
        # <<<<<<< เปลี่ยนไป Subscribe Topic ใหม่ที่ถูกต้อง
        self.pizza_count_subscriber_ = self.create_subscription(
            Int64, "/correct_pizza_count", self.pizza_count_callback, 10)

        self.timer_ = self.create_timer(0.1, self.control_loop)
        self.get_logger().info('Killer node has been started in WAITING MODE.')

    def pizza_count_callback(self, msg: Int64):
        if msg.data > 0:
            self.game_started_ = True
            
        if msg.data == 0 and self.game_started_ and self.current_mode_ == self.WAITING_MODE:
            self.current_mode_ = self.CHASING_MODE
            self.get_logger().info('Pizza is gone! Switching to CHASING MODE.')

    def control_loop(self):
        if self.current_mode_ != self.CHASING_MODE: return
        try:
            transform = self.tf_buffer_.lookup_transform('turtle2', 'turtle1', Time())
            dist_x = transform.transform.translation.x
            dist_y = transform.transform.translation.y
            distance = math.sqrt(dist_x**2 + dist_y**2)
            angle_to_target = math.atan2(dist_y, dist_x)
            vel_msg = Twist()
            if distance < 1.0: 
                self.get_logger().info("Target is close, removing turtle1...")
                self.call_remove_turtle_service('turtle1')
            else:
                vel_msg.linear.x = 1.5 * distance
                vel_msg.angular.z = 4.0 * angle_to_target
                self.vel_publisher_.publish(vel_msg)
        except Exception as e:
            self.vel_publisher_.publish(Twist())
            self.get_logger().warn(f'Could not find transform (target may be gone): {e}')

    def call_remove_turtle_service(self, turtle_name):
        if not self.remove_turtle_client_.wait_for_service(timeout_sec=1.0): return
        request = Kill.Request()
        request.name = turtle_name
        future = self.remove_turtle_client_.call_async(request)
        future.add_done_callback(self.remove_turtle_callback)

    def remove_turtle_callback(self, future):
        try:
            future.result()
            self.get_logger().info("Successfully removed turtle1. Killer is now WAITING.")
            self.current_mode_ = self.WAITING_MODE
            self.game_started_ = False
            # เราจะหยุด timer ไปเลย เพราะ Killer ทำงานสำเร็จแล้ว
            if self.timer_ and not self.timer_.is_canceled():
                self.timer_.cancel()
        except Exception as e:
            self.get_logger().error(f"Failed to remove turtle: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = KillerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__': main()