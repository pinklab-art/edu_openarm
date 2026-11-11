"""teleop·policy 가 낸 관절 명령을 안전하게 다듬어 팔 컨트롤러로 넘기는 노드.

입력   /safety_filter/command                 sensor_msgs/JointState (팔마다 관절 7 + finger_joint1, 이름으로 구분)
출력   /<arm>_forward_position_controller/commands   std_msgs/Float64MultiArray
       /<arm>_gripper_controller/gripper_cmd          control_msgs/action/GripperCommand

주기마다 하는 일
  1. 입력이 input_timeout 보다 오래 끊기면 명령을 멈춘다(팔은 마지막 명령 자리에 선다).
  2. 입력이 다시 들어오면 팔의 실제 자세에서 출발해 ramp_speed 로 천천히 목표까지 간다.
  3. 목표에 닿으면 max_speed 로 따라간다. 입력이 갑자기 튀어도 이 속도를 넘지 않는다.
  4. 목표는 늘 joint_limits_deg 안으로 자른다. 팔이 이미 한계 밖이어도 안쪽으로는 움직인다.
  5. 그리퍼는 범위로 자르고 low-pass 로 손떨림을 거른 뒤, 조금씩 끊어 goal 로 보낸다.
"""

import math

import rclpy
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.exceptions import ParameterUninitializedException
from rclpy.node import Node
from rclpy.parameter import Parameter

from control_msgs.action import GripperCommand
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

from openarm_safety.filter import clamp, limit_joints, low_pass

ARM_DOF = 7


class ArmFilter:
    """한 팔의 입력·출력·필터 상태."""

    def __init__(self, node, arm):
        self.node = node
        self.arm = arm
        self.joints = [f'openarm_{arm}_joint{i}' for i in range(1, ARM_DOF + 1)]
        self.finger = f'openarm_{arm}_finger_joint1'

        # 한계가 비거나 뒤집히면 팔을 엉뚱한 자세로 끌고 가므로 노드를 띄우지 않는다.
        try:
            flat = node.get_parameter(f'{arm}.joint_limits_deg').value
        except ParameterUninitializedException:
            flat = None
        if flat is None or len(flat) != 2 * ARM_DOF:
            raise ValueError(f'{arm}.joint_limits_deg 는 하한·상한 {2 * ARM_DOF}개여야 합니다')
        self.limits = [(math.radians(flat[2 * i]), math.radians(flat[2 * i + 1]))
                       for i in range(ARM_DOF)]
        if any(low >= high for low, high in self.limits):
            raise ValueError(f'{arm}.joint_limits_deg 는 관절마다 하한 < 상한 이어야 합니다')

        self.target = None          # 입력 관절 7개 [rad]
        self.gripper_target = None  # 입력 finger [m]
        self.stamp_ns = None        # 입력을 받은 시각
        self.output = None          # 지난 주기에 보낸 관절 명령
        self.mode = 'idle'          # idle → ramp → follow
        self.gripper_filtered = None
        self.gripper_sent = None
        self.gripper_sent_ns = 0

        self.arm_pub = node.create_publisher(
            Float64MultiArray, f'/{arm}_forward_position_controller/commands', 10)
        self.gripper_client = ActionClient(
            node, GripperCommand, f'/{arm}_gripper_controller/gripper_cmd')

    def take_command(self, index, msg):
        """입력 JointState 에 이 팔의 관절 7개가 다 있고 값이 유한하면 목표로 받는다.

        버린 메시지는 입력 시각을 갱신하지 않으므로, 잘못된 입력만 오면 timeout 으로 명령이 멈춘다.
        """
        if not all(name in index for name in self.joints):
            return
        target = [msg.position[index[name]] for name in self.joints]
        gripper = msg.position[index[self.finger]] if self.finger in index else None
        values = target if gripper is None else target + [gripper]
        if not all(math.isfinite(v) for v in values):
            self.node.get_logger().warn(
                f'[{self.arm}] NaN·inf 가 든 명령을 버립니다', throttle_duration_sec=1.0)
            return
        self.target = target
        if gripper is not None:
            self.gripper_target = gripper
        self.stamp_ns = self.node.get_clock().now().nanoseconds


class SafetyFilterNode(Node):

    def __init__(self):
        super().__init__('safety_filter')
        self.declare_parameter('arms', ['left', 'right'])
        self.declare_parameter('rate_hz', 100.0)
        self.declare_parameter('input_timeout', 0.3)
        self.declare_parameter('ramp_speed', 0.4)
        self.declare_parameter('max_speed', 2.0)
        self.declare_parameter('follow_tolerance', 0.02)
        self.declare_parameter('gripper_range', [0.0, 0.044])
        self.declare_parameter('gripper_alpha', 0.25)
        self.declare_parameter('gripper_deadband', 0.001)
        self.declare_parameter('gripper_period', 0.1)
        self.declare_parameter('gripper_max_effort', 10.0)
        arms = list(self.get_parameter('arms').value)
        for arm in arms:
            self.declare_parameter(f'{arm}.joint_limits_deg', Parameter.Type.DOUBLE_ARRAY)

        p = lambda name: self.get_parameter(name).value   # noqa: E731
        self.period = 1.0 / p('rate_hz')
        self.timeout_ns = int(p('input_timeout') * 1e9)
        self.ramp_step = p('ramp_speed') * self.period
        self.max_step = p('max_speed') * self.period
        self.follow_tolerance = p('follow_tolerance')
        self.gripper_range = tuple(p('gripper_range'))
        self.gripper_alpha = p('gripper_alpha')
        self.gripper_deadband = p('gripper_deadband')
        self.gripper_period_ns = int(p('gripper_period') * 1e9)
        self.gripper_max_effort = p('gripper_max_effort')

        self.arms = [ArmFilter(self, arm) for arm in arms]
        self.state = None
        self.create_subscription(JointState, '~/command', self._on_command, 10)
        self.create_subscription(JointState, '/joint_states', self._on_state, 10)
        self.create_timer(self.period, self._on_timer)
        self.get_logger().info(f'안전 필터 시작 — 팔 {arms}, 입력 /safety_filter/command')

    def _on_command(self, msg):
        if len(msg.position) != len(msg.name):
            self.get_logger().warn('name 과 position 길이가 다른 명령을 버립니다', throttle_duration_sec=1.0)
            return
        index = {name: i for i, name in enumerate(msg.name)}
        for arm in self.arms:
            arm.take_command(index, msg)

    def _on_state(self, msg):
        self.state = dict(zip(msg.name, msg.position))

    def _on_timer(self):
        if self.state is None:
            return
        now_ns = self.get_clock().now().nanoseconds
        for arm in self.arms:
            self._update_arm(arm, now_ns)

    def _update_arm(self, arm, now_ns):
        log = self.get_logger()
        fresh = arm.stamp_ns is not None and now_ns - arm.stamp_ns <= self.timeout_ns
        if not fresh:
            if arm.mode != 'idle':
                log.warn(f'[{arm.arm}] 입력이 끊겨 명령을 멈춥니다')
                arm.mode = 'idle'
            return

        if arm.mode == 'idle':
            if not all(name in self.state for name in arm.joints):
                return
            # 실제 자세에서 출발한다. 지난 출력이나 입력 자세에서 시작하면 팔이 튄다.
            arm.output = [self.state[name] for name in arm.joints]
            arm.gripper_filtered = self.state.get(arm.finger)
            arm.mode = 'ramp'
            log.info(f'[{arm.arm}] 입력 수신 — 지금 자세에서 천천히 출발합니다')

        step = self.ramp_step if arm.mode == 'ramp' else self.max_step
        arm.output = limit_joints(arm.output, arm.target, arm.limits, step)
        arm.arm_pub.publish(Float64MultiArray(data=arm.output))

        if arm.mode == 'ramp':
            gap = max(abs(out - clamp(goal, low, high))
                      for out, goal, (low, high) in zip(arm.output, arm.target, arm.limits))
            if gap < self.follow_tolerance:
                arm.mode = 'follow'
                log.info(f'[{arm.arm}] 목표에 닿아 따라가기 시작합니다')

        self._update_gripper(arm, now_ns)

    def _update_gripper(self, arm, now_ns):
        if arm.gripper_target is None:
            return
        goal = clamp(arm.gripper_target, *self.gripper_range)
        if arm.gripper_filtered is None:
            arm.gripper_filtered = goal
        arm.gripper_filtered = low_pass(arm.gripper_filtered, goal, self.gripper_alpha)
        # GripperActionController 는 action goal 만 받는다. goal 이 몰리지 않게
        # 움직임이 deadband 보다 크고 gripper_period 가 지났을 때만 새로 보낸다.
        moved = arm.gripper_sent is None or \
            abs(arm.gripper_filtered - arm.gripper_sent) > self.gripper_deadband
        if not moved or now_ns - arm.gripper_sent_ns < self.gripper_period_ns:
            return
        if not arm.gripper_client.server_is_ready():
            return
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = arm.gripper_filtered
        goal_msg.command.max_effort = self.gripper_max_effort
        arm.gripper_client.send_goal_async(goal_msg)
        arm.gripper_sent = arm.gripper_filtered
        arm.gripper_sent_ns = now_ns


def main(args=None):
    rclpy.init(args=args)
    node = SafetyFilterNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
