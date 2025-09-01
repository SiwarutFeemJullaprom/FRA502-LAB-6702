from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='turtlesim_plus',
            executable='turtlesim_plus_node.py',
            name='turtlesim_plus'
        ),
        Node(
            package='lab2',
            executable='turtlesim_pose.py',
            name='turtlesim_pose'
        ),
        Node(
            package='lab2',
            executable='eater.py',
            name='eater'
        ),
        Node(
            package='lab2',
            executable='killer.py',
            name='killer'
        ),
    ])