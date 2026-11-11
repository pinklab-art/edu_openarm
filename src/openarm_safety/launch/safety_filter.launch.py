"""안전 필터 노드를 config/safety_filter.yaml 설정으로 띄운다."""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution([FindPackageShare('openarm_safety'), 'config', 'safety_filter.yaml'])
    return LaunchDescription([
        Node(
            package='openarm_safety',
            executable='safety_filter',
            output='screen',
            emulate_tty=True,
            parameters=[config],
        ),
    ])
