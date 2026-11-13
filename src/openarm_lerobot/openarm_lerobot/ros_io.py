"""기록·추론 노드가 함께 쓰는 ROS 입출력.

입력   /joint_states                  sensor_msgs/JointState  팔 자세(state)
       /safety_filter/command         sensor_msgs/JointState  teleop 명령(action, 기록 때만)
출력   /safety_filter/command         sensor_msgs/JointState  policy 명령(추론 때만)

콜백은 마지막 메시지와 받은 시각만 남기고, 기록·추론 루프가 주기마다 snapshot 으로 꺼내 쓴다.
"""

import threading
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions

from sensor_msgs.msg import JointState

from openarm_lerobot.features import pick, ros_joint_names

COMMAND_TOPIC = '/safety_filter/command'
TOPICS = {'state': '/joint_states', 'action': COMMAND_TOPIC}   # snapshot 키 → topic


class RobotIO(Node):

    def __init__(self, cfg, record_action):
        super().__init__('lerobot_io')
        self.joint_names = ros_joint_names(cfg['arm'])
        self.latest = {}   # 이름 → (받은 시각 [s], 값)
        self.lock = threading.Lock()

        self.create_subscription(JointState, TOPICS['state'], self._joints_callback('state'), 10)
        if record_action:
            self.create_subscription(JointState, COMMAND_TOPIC, self._joints_callback('action'), 10)
            self.command_pub = None
        else:
            self.command_pub = self.create_publisher(JointState, COMMAND_TOPIC, 10)

    def _store(self, key, value):
        with self.lock:
            self.latest[key] = (time.monotonic(), value)

    def _joints_callback(self, key):
        def callback(msg):
            if len(msg.name) != len(msg.position):
                return
            values = pick(dict(zip(msg.name, msg.position)), self.joint_names)
            if values is not None:   # 다른 팔만 담긴 메시지는 건너뛴다
                self._store(key, values)
        return callback

    def snapshot(self, keys, max_age):
        """keys 의 마지막 값을 dict 로 돌려준다. 없거나 max_age 보다 오래된 것이 있으면 (None, 이유)."""
        now = time.monotonic()
        with self.lock:
            latest = dict(self.latest)
        values = {}
        for key in keys:
            if key not in latest:
                return None, f'아직 받지 못한 topic — {TOPICS[key]}'
            stamp, value = latest[key]
            if now - stamp > max_age:
                return None, f'{now - stamp:.1f} s 동안 끊긴 topic — {TOPICS[key]}'
            values[key] = value
        return values, None

    def publish_command(self, values):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self.joint_names)
        msg.position = [float(v) for v in values]
        self.command_pub.publish(msg)


def start(cfg, record_action):
    """rclpy 를 띄우고 RobotIO 를 백그라운드 스레드에서 돌린다. Ctrl+C 는 호출한 쪽 루프가 받는다."""
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = RobotIO(cfg, record_action)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    return node, (executor, thread)


def stop(node, spinner):
    """spin 스레드가 끝난 뒤에 노드를 지운다. 도는 중에 지우면 종료 때 프로세스가 죽는다."""
    executor, thread = spinner
    executor.shutdown()
    thread.join(timeout=2.0)
    node.destroy_node()
    rclpy.try_shutdown()
