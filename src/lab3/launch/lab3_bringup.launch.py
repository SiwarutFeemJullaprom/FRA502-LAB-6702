import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    
    eater_name = 'eater' # นี่คือ XXXX
    killer_name = 'killer' # นี่คือ YYYY
    
    turtlesim_plus_node = Node(
        package='turtlesim_plus',
        executable='turtlesim_plus_node.py',
        name='turtlesim_plus'
    )
    
    eater_node = Node(
        package='lab3',
        executable='eater.py',
        namespace=eater_name,
        name='eater_node',
        parameters=[{
            'sampling_frequency': 100.0
        }]
    )
    
    killer_node = Node(
        package='lab3',
        executable='killer.py',
        namespace=killer_name,
        name='killer_node',
        parameters=[{
            'sampling_frequency': 100.0,
            'eater_name': eater_name
        }]
    )
    
    # <<<<<<< จุดที่แก้ไข: เอา shell=True ออกทั้งหมด >>>>>>>
    
    kill_turtle1_cmd = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/remove_turtle', 'turtlesim/srv/Kill', '{name: "turtle1"}']
    )
    
    spawn_eater_cmd = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/spawn_turtle', 'turtlesim/srv/Spawn', f"{{name: '{eater_name}', x: 2.0, y: 2.0}}"]
    )
    
    spawn_killer_cmd = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/spawn_turtle', 'turtlesim/srv/Spawn', f"{{name: '{killer_name}', x: 8.0, y: 8.0}}"]
    )

    return LaunchDescription([
        turtlesim_plus_node,
        eater_node,
        killer_node,
        
        TimerAction(
            period=2.0,
            actions=[
                kill_turtle1_cmd,
                spawn_eater_cmd,
                spawn_killer_cmd
            ]
        )
    ])