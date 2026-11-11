import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'openarm_safety'

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
    description='OpenArm v1 안전 필터 — teleop·policy 관절 명령을 한계·속도 안으로 다듬는 노드.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'safety_filter = openarm_safety.safety_filter_node:main',
        ],
    },
)
