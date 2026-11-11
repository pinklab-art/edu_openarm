import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'openarm_moveit'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Woolim Park',
    maintainer_email='woolim@pinklab.art',
    description='OpenArm v1 MoveIt 실습 — move_group·RViz·Servo 조립과 Python 예제 넷.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'ex01_joint_goal = openarm_moveit.ex01_joint_goal:main',
            'ex02_pose_goal = openarm_moveit.ex02_pose_goal:main',
            'ex03_cartesian_path = openarm_moveit.ex03_cartesian_path:main',
            'ex04_keyboard_servo = openarm_moveit.ex04_keyboard_servo:main',
        ],
    },
)
