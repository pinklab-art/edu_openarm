"""OpenArm mini 리더암 자세를 읽어 안전 필터 입력으로 보내는 노드.

출력   /safety_filter/command   sensor_msgs/JointState (팔마다 관절 7 + finger_joint1)
리더 서보 tick 을 mini.yaml 의 offset·sign 으로 관절각으로 바꿀 뿐, 한계·속도 제한은 안전 필터가 맡는다.
"""

import signal

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions

from sensor_msgs.msg import JointState

from openarm_mini import config as config_io
from openarm_mini.feetech import FeetechBus
from openarm_mini.mapping import ARM_DOF, arm_sample


class MiniNode(Node):

    def __init__(self):
        super().__init__('mini')
        self.declare_parameter('arms', 'left,right')
        self.cfg = config_io.load()
        arms = [arm.strip() for arm in self.get_parameter('arms').value.split(',') if arm.strip()]
        unknown = [arm for arm in arms if arm not in self.cfg['arms']]
        if unknown:
            raise ValueError(f'mini.yaml 에 없는 팔: {unknown}')

        self.arms = []
        for arm in arms:
            arm_cfg = self.cfg['arms'][arm]
            bus = FeetechBus(arm_cfg['port'], self.cfg['baudrate'])
            names = [f'openarm_{arm}_joint{i}' for i in range(1, ARM_DOF + 1)]
            names.append(f'openarm_{arm}_finger_joint1')
            self.arms.append((arm, arm_cfg, bus, names))
            self.get_logger().info(f'{arm}: {arm_cfg["port"]}')

        self.pub = self.create_publisher(JointState, '/safety_filter/command', 10)
        self.failed = set()
        self.create_timer(1.0 / self.cfg['rate_hz'], self._on_timer)

    def _on_timer(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        for arm, arm_cfg, bus, names in self.arms:
            ticks = bus.read_positions(arm_cfg['ids'])
            if ticks is None:
                # 이 팔은 이번 주기에 빠진다. 계속 빠지면 안전 필터가 그 팔의 명령을 멈춘다.
                if arm not in self.failed:
                    self.get_logger().warn(f'{arm}: mini 읽기 실패 — 보드 연결·전원을 확인하세요')
                    self.failed.add(arm)
                continue
            if arm in self.failed:
                self.get_logger().info(f'{arm}: mini 읽기 재개')
                self.failed.discard(arm)
            joints, gripper = arm_sample(
                arm_cfg, ticks, self.cfg['ticks_per_rev'], self.cfg['gripper_travel'])
            msg.name.extend(names)
            msg.position.extend(joints + [gripper])
        if msg.name:
            self.pub.publish(msg)

    def close(self):
        for _arm, _cfg, bus, _names in self.arms:
            bus.close()


def main(args=None):
    # Ctrl+C 는 터미널과 launch 양쪽에서 SIGINT 를 두 번 보낸다. 처리기는 멈춤 표시만 남기고
    # 루프가 그 표시를 보고 빠져나와 정리하므로, 정리 도중 두 번째 신호가 와도 끊기지 않는다.
    stop = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.append(True))
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    try:
        node = MiniNode()
    except (RuntimeError, ValueError) as error:   # 포트를 못 열었거나 설정에 없는 팔
        print(error)
        rclpy.shutdown()
        return 1
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    while not stop:
        executor.spin_once(timeout_sec=0.1)
    node.close()
    node.destroy_node()
    rclpy.shutdown()
