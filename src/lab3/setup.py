from setuptools import setup
import os
from glob import glob

package_name = 'lab3'

setup(
    name=package_name,
    version='0.0.0',
    packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('*.rviz')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        # --- นี่คือบรรทัดที่ถูกต้องสำหรับติดตั้ง Executable Scripts ของ ROS 2 ---
        (os.path.join('lib', package_name), glob('scripts/*.py'))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='siwarut',
    maintainer_email='siwarut.jull@mail.kmutt.ac.th',
    description='LAB3 Final Project',
    license='Apache License 2.0',
    tests_require=['pytest'],
    # เราจะไม่ใช้ entry_points หรือ scripts=[] ในกรณีนี้
)