"""joint_state_publisher_gui 슬라이더를 안전 필터 입력으로 연결한다(시뮬 시험용 입력).

슬라이더 창이 양팔 관절값을 /joint_states 대신 /safety_filter/command 로 보낸다.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='sliders',
            remappings=[('joint_states', '/safety_filter/command')],
        ),
    ])
