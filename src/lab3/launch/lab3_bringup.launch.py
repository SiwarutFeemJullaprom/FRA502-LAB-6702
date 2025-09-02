from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    
    # --- 1. ประกาศ Argument ที่จะรับจากภายนอก ---
    # เราจะสร้าง Argument ชื่อ 'eater_name' และ 'killer_name'
    # พร้อมกำหนดค่า default ให้เป็น 'eater' และ 'killer'
    eater_name_arg = DeclareLaunchArgument(
        'eater_name', default_value='eater'
    )
    killer_name_arg = DeclareLaunchArgument(
        'killer_name', default_value='killer'
    )

    # --- 2. อ่านค่าจาก Argument ที่ประกาศไว้ ---
    # สร้างตัวแปรเพื่อเก็บค่าที่ส่งเข้ามา (หรือค่า default ถ้าไม่ได้ส่ง)
    eater_name = LaunchConfiguration('eater_name')
    killer_name = LaunchConfiguration('killer_name')
    
    # --- 3. Node Definitions (เหมือนเดิม แต่ใช้ตัวแปรใหม่) ---
    turtlesim_plus_node = Node(
        package='turtlesim_plus',
        executable='turtlesim_plus_node.py',
        name='turtlesim_plus'
    )
    
    eater_node = Node(
        package='lab3',
        executable='eater.py',
        namespace=eater_name, # ใช้ชื่อจาก Argument
        name='eater_node',
        parameters=[{
            'sampling_frequency': 100.0
        }]
    )
    
    killer_node = Node(
        package='lab3',
        executable='killer.py',
        namespace=killer_name, # ใช้ชื่อจาก Argument
        name='killer_node',
        parameters=[{
            'sampling_frequency': 100.0,
            'eater_name': eater_name # ส่งชื่อ eater ให้ killer รู้จัก
        }]
    )
    
    # --- 4. Service Call Definitions (เหมือนเดิม แต่ใช้ตัวแปรใหม่) ---
    kill_turtle1_cmd = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/remove_turtle', 'turtlesim/srv/Kill', '{name: "turtle1"}']
    )
    
    spawn_eater_cmd = ExecuteProcess(
        # สังเกตว่าเราสามารถใส่ LaunchConfiguration เข้าไปใน list ของ cmd ได้เลย
        cmd=['ros2', 'service', 'call', '/spawn_turtle', 'turtlesim/srv/Spawn', 
             ['{name: "', eater_name, '", x: 2.0, y: 2.0}']]
    )
    
    spawn_killer_cmd = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/spawn_turtle', 'turtlesim/srv/Spawn',
             ['{name: "', killer_name, '", x: 8.0, y: 8.0}']]
    )

    return LaunchDescription([
        # --- 5. เพิ่ม Argument ที่ประกาศไว้เข้าไปใน LaunchDescription ---
        eater_name_arg,
        killer_name_arg,
        
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