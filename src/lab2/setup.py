from setuptools import setup
import os
from glob import glob

package_name = 'lab2'

setup(
    name=package_name,
    version='0.0.0',
    packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('*.rviz')),
        # เพิ่มบรรทัดนี้เพื่อติดตั้ง launch file
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py'))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='siwarut',
    maintainer_email='siwarut@todo.todo',
    description='FRA502 LAB2 - Eater vs. Killer',
    license='Apache License 2.0',
    tests_require=['pytest'],
    scripts=[
        'scripts/eater.py',
        'scripts/killer.py',
        'scripts/turtlesim_pose.py'
    ],
)