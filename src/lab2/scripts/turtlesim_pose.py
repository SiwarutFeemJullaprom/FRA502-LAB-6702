#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import math

# ฟังก์ชันแปลงมุมเป็น Quaternion ยังคงเหมือนเดิม
def quaternion_from_euler(roll, pitch, yaw):
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    q = [0.0] * 4
    q[0] = sr * cp * cy - cr * sp * sy  # x
    q[1] = cr * sp * cy + sr * cp * sy  # y
    q[2] = cr * cp * sy - sr * sp * cy  # z
    q[3] = cr * cp * cy + sr * sp * sy  # w
    return q

class TurtlesimPoseNode(Node):
    def __init__(self):
        super().__init__('turtlesim_pose_publisher')
        self.get_logger().info('Turtlesim Pose Publisher node has been started.')

        # สร้าง Subscriber, Publisher, และ Broadcaster สำหรับเต่าทั้งสองตัว
        self.tf_broadcaster_ = TransformBroadcaster(self)

        self.odom1_publisher_ = self.create_publisher(Odometry, '/odom1', 10)
        self.odom2_publisher_ = self.create_publisher(Odometry, '/odom2', 10)

        self.pose1_subscriber_ = self.create_subscription(
            Pose, '/turtle1/pose', self.turtle1_pose_callback, 10)
        self.pose2_subscriber_ = self.create_subscription(
            Pose, '/turtle2/pose', self.turtle2_pose_callback, 10)

    # Callback สำหรับ turtle1
    def turtle1_pose_callback(self, msg: Pose):
        self.publish_odom_and_tf(msg, "turtle1", self.odom1_publisher_)

    # Callback สำหรับ turtle2
    def turtle2_pose_callback(self, msg: Pose):
        self.publish_odom_and_tf(msg, "turtle2", self.odom2_publisher_)

    # --- นี่คือฟังก์ชันกลางที่โจทย์ต้องการ ---
    def publish_odom_and_tf(self, pose_msg, turtle_name, odom_publisher):
        current_time = self.get_clock().now().to_msg()
        
        # 1. สร้างและ Broadcast Transform (TF)
        t = TransformStamped()
        t.header.stamp = current_time
        t.header.frame_id = 'odom'
        t.child_frame_id = turtle_name

        t.transform.translation.x = pose_msg.x
        t.transform.translation.y = pose_msg.y
        t.transform.translation.z = 0.0

        q = quaternion_from_euler(0, 0, pose_msg.theta)
        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]

        self.tf_broadcaster_.sendTransform(t)

        # 2. สร้างและ Publish Odometry
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = turtle_name

        # ใส่ข้อมูลตำแหน่งและทิศทาง
        odom_msg.pose.pose.position.x = pose_msg.x
        odom_msg.pose.pose.position.y = pose_msg.y
        odom_msg.pose.pose.orientation.x = q[0]
        odom_msg.pose.pose.orientation.y = q[1]
        odom_msg.pose.pose.orientation.z = q[2]
        odom_msg.pose.pose.orientation.w = q[3]
        
        odom_publisher.publish(odom_msg)

def main(args=None):
    rclpy.init(args=args)
    node = TurtlesimPoseNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()