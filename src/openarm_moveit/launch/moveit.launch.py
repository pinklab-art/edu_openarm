"""떠 있는 OpenArm v1 양팔(MuJoCo 시뮬 또는 실물) 위에 MoveIt 을 띄운다.

로봇 쪽 ros2_control 과 robot_state_publisher 는 먼저 띄워 둔다. 이 launch 는 move_group 과 RViz,
그리고 servo 인자를 주면 MoveIt Servo 노드를 올린다.

    ros2 launch openarm_moveit moveit.launch.py
    ros2 launch openarm_moveit moveit.launch.py servo:=left
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration

from launch_param_builder import ParameterBuilder
from launch_ros.actions import Node

from moveit_configs_utils import MoveItConfigsBuilder


def moveit_configs(joint_limits):
    """move_group 과 Servo 가 같이 쓰는 URDF·SRDF·IK 솔버. 관절 한계 파일만 다르게 고른다."""
    xacro_path = os.path.join(
        get_package_share_directory('openarm_description'),
        'assets', 'robot', 'openarm_v1.0', 'urdf', 'openarm_v10.urdf.xacro')
    return (
        MoveItConfigsBuilder('openarm', package_name='openarm_moveit')
        .robot_description(file_path=xacro_path)
        .robot_description_semantic(file_path='config/openarm_bimanual.srdf')
        .robot_description_kinematics(file_path='config/kinematics.yaml')
        .joint_limits(file_path=joint_limits)
        .trajectory_execution(file_path='config/moveit_controllers.yaml')
        .planning_pipelines(pipelines=['ompl'], default_planning_pipeline='ompl')
        .to_moveit_configs()
    )


def moveit_nodes(context):
    moveit_params = moveit_configs('config/moveit_joint_limits.yaml').to_dict()
    nodes = [
        Node(
            package='moveit_ros_move_group',
            executable='move_group',
            output='screen',
            parameters=[moveit_params],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            output='log',
            arguments=['-d', os.path.join(
                get_package_share_directory('openarm_moveit'), 'config', 'moveit.rviz')],
            parameters=[moveit_params],
        ),
    ]

    arm = LaunchConfiguration('servo').perform(context)
    if arm == 'none':
        return nodes

    # Servo 는 느린 속도 상한(servo_joint_limits.yaml)으로 Jacobian 과 충돌 검사를 한다.
    servo_config = moveit_configs('config/servo_joint_limits.yaml')
    servo_params = ParameterBuilder('openarm_moveit').yaml('config/servo.yaml')
    servo_params = servo_params.to_dict()
    servo_params['move_group_name'] = f'{arm}_arm'
    servo_params['command_out_topic'] = (
        f'/{arm}_joint_trajectory_controller/joint_trajectory')
    servo = Node(
        package='moveit_servo',
        executable='servo_node',
        name='servo_node',
        output='screen',
        parameters=[
            {'moveit_servo': servo_params},
            {'update_period': servo_params['publish_period']},    # 가속도 제한 필터 주기
            {'planning_group_name': f'{arm}_arm'},
            servo_config.robot_description,
            servo_config.robot_description_semantic,
            servo_config.robot_description_kinematics,
            servo_config.joint_limits,
        ],
    )
    # move_group 이 planning scene 을 연 뒤에 시작한다
    return nodes + [TimerAction(period=5.0, actions=[servo])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'servo', default_value='none', choices=['none', 'left', 'right'],
            description='MoveIt Servo 로 움직일 팔. none 이면 Servo 를 띄우지 않는다.'),
        OpaqueFunction(function=moveit_nodes),
    ])
