import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'openarm_lerobot'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        # console_scripts 로 만들면 shebang 이 빌드한 python(/usr/bin/python3)으로 박혀 venv 의 LeRobot 을 못 찾는다.
        # `#!/usr/bin/env python3` 스크립트를 그대로 lib/ 에 넣어, activate 한 venv 의 python 으로 ros2 run 이 돌게 한다.
        (os.path.join('lib', package_name), [f for f in glob('scripts/*') if os.path.isfile(f)]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Woolim Park',
    maintainer_email='woolim@pinklab.art',
    description='OpenArm v1 한 팔 imitation learning — ROS 로 기록한 시연을 LeRobot 데이터셋으로 쌓고 학습한 policy 로 팔을 움직인다.',
    license='Apache-2.0',
    tests_require=['pytest'],
)
