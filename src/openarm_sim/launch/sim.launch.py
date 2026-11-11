"""OpenArm v1 양팔을 MuJoCo 에 띄우고 실물과 같은 컨트롤러를 올린다."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Shutdown
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile, ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('openarm_sim')
    controllers = PathJoinSubstitution([share, 'config', 'controllers.yaml'])
    robot_controller = LaunchConfiguration('robot_controller')

    robot_description = ParameterValue(
        Command([FindExecutable(name='xacro'), ' ',
                 PathJoinSubstitution([share, 'urdf', 'openarm_sim.urdf.xacro'])]),
        value_type=str)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_description}],
    )

    # MuJoCo 창을 띄우고 그 안의 로봇을 ros2_control 하드웨어로 쓴다.
    # use_sim_time 을 켜지 않아 시뮬도 실물처럼 wall clock 으로 돌고, 명령 stamp 를 자기 시계와
    # 비교하는 MoveIt Servo 가 시뮬과 실물에서 같은 설정으로 돈다.
    mujoco = Node(
        package='mujoco_ros2_control',
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
        mujoco,
        spawner,
    ])
