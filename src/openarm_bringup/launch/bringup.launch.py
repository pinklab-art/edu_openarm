"""실물 OpenArm v1 양팔을 CAN 으로 띄우고 시뮬과 같은 컨트롤러를 올린다."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Shutdown
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile, ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('openarm_bringup')
    controllers = PathJoinSubstitution([share, 'config', 'controllers.yaml'])
    robot_controller = LaunchConfiguration('robot_controller')

    robot_description = ParameterValue(
        Command([FindExecutable(name='xacro'), ' ',
                 PathJoinSubstitution([share, 'urdf', 'openarm_real.urdf.xacro'])]),
        value_type=str)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_description}],
    )

    # 팔마다 OpenArmHW 가 CAN 으로 모터 8개를 켜고, 활성화되면 영점 자세로 천천히 이동한다.
    control_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        output='both',
        emulate_tty=True,
        parameters=[ParameterFile(controllers)],
        on_exit=Shutdown(),
    )

    spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='both',
        arguments=[
            'joint_state_broadcaster',
            ['left_', robot_controller],
            ['right_', robot_controller],
            'left_gripper_controller',
            'right_gripper_controller',
            '--param-file', controllers,
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_controller',
            default_value='joint_trajectory_controller',
            choices=['joint_trajectory_controller', 'forward_position_controller'],
            description='팔 컨트롤러. MoveIt 은 joint_trajectory_controller, teleop 은 forward_position_controller.',
        ),
        robot_state_publisher,
        control_node,
        spawner,
    ])
