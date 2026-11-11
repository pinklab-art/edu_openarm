import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'openarm_mini'

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
    description='OpenArm mini 리더암 teleop — Feetech 서보 자세를 읽어 안전 필터로 보내는 노드와 세팅 CLI.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mini = openarm_mini.mini_node:main',
            'udev = openarm_mini.udev:main',
            'register = openarm_mini.register:main',
            'calibrate = openarm_mini.calibrate:main',
            'check = openarm_mini.check:main',
        ],
    },
)
