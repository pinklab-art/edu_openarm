"""mini 리더암 teleop. mini 노드와 안전 필터를 함께 띄운다.

팔(시뮬 또는 실물)은 robot_controller:=forward_position_controller 로 따로 띄워 둔다.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, Shutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('arms', default_value='left,right',
                              description='움직일 팔. 한 팔만 쓸 때는 left 또는 right'),
        IncludeLaunchDescription(PathJoinSubstitution(
            [FindPackageShare('openarm_safety'), 'launch', 'safety_filter.launch.py'])),
        Node(
            package='openarm_mini',
            executable='mini',
            output='screen',
            emulate_tty=True,
            parameters=[{'arms': LaunchConfiguration('arms')}],
            on_exit=Shutdown(),   # mini 노드가 멈추면(포트 없음 등) 안전 필터도 함께 내린다
        ),
    ])
