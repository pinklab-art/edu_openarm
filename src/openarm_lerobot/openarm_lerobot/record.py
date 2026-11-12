"""mini teleop 시연을 LeRobot 데이터셋으로 기록한다.

fps 주기마다 팔 자세(/joint_states), teleop 명령(/safety_filter/command), 카메라 영상을 한 frame 으로 묶어
LeRobotDataset 에 쌓는다. 카메라는 ROS 를 거치지 않고 이 프로세스가 직접 연다. 에피소드 시작·저장은 터미널에서 Enter 로 한다.
설정의 display 가 true 면 기록 전후 내내 rerun 창에 카메라 영상과 관절값을 띄운다.
같은 repo_id 데이터셋이 이미 있으면 그 뒤에 에피소드를 이어 붙인다.
"""

import argparse
import multiprocessing
import signal
import time

from lerobot.datasets import LeRobotDataset
from lerobot.utils.constants import HF_LEROBOT_HOME

from openarm_lerobot import config as config_io
from openarm_lerobot import ros_io
from openarm_lerobot.cameras import Cameras
from openarm_lerobot.console import LineReader, Rate, stop_flag
from openarm_lerobot.display import Display
from openarm_lerobot.features import dataset_features, same_features

MAX_AGE = 0.2   # 이보다 오래된 입력이 있으면 frame 을 만들지 않는다 [s]

HELP_IDLE = 'Enter: 에피소드 시작   q+Enter: 끝내기'
HELP_RECORDING = 'Enter: 저장   x+Enter: 버리기   q+Enter: 버리고 끝내기'


def open_dataset(cfg, repo_id):
    features = dataset_features(cfg)
    threads = 4 * len(cfg['cameras'])   # 영상 frame 을 PNG 로 쓰는 스레드. lerobot-record 기본값과 같다
    root = HF_LEROBOT_HOME / repo_id   # lerobot-train 이 --dataset.repo_id 만으로 찾는 자리
    if root.exists():
        dataset = LeRobotDataset.resume(repo_id, root=root, image_writer_threads=threads)
        if dataset.meta.fps != cfg['fps'] or not same_features(dataset.meta.features, features):
            raise SystemExit(f'{repo_id} 는 지금 설정(팔·fps·카메라)과 다른 데이터셋입니다. --repo-id 로 새 이름을 주세요')
        print(f'{repo_id}: 에피소드 {dataset.meta.total_episodes}개 뒤에 이어서 기록합니다')
    else:
        dataset = LeRobotDataset.create(repo_id, cfg['fps'], features, root=root,
                                        robot_type=cfg['robot_type'], image_writer_threads=threads)
        print(f'{repo_id}: 새 데이터셋을 만듭니다')
    print(f'저장 위치 {dataset.root}')
    return dataset


def main():
    cfg = config_io.load()
    parser = argparse.ArgumentParser(description='mini teleop 시연을 LeRobot 데이터셋으로 기록')
    parser.add_argument('--repo-id', default=cfg['dataset']['repo_id'])
    parser.add_argument('--task', default=cfg['dataset']['task'])
    args = parser.parse_args()

    # save_episode 는 카메라마다 프로세스를 띄워 영상을 인코딩한다. 기본 fork 는 rclpy 스레드가 잡은 lock 까지
    # 복사해 자식이 멈추므로, 새 인터프리터로 띄우는 spawn 을 쓴다.
    multiprocessing.set_start_method('spawn')
    stop = stop_flag()
    cameras = Cameras(cfg)
    dataset = open_dataset(cfg, args.repo_id)
    display = Display(cfg, 'openarm_record') if cfg['display'] else None
    node, spinner = ros_io.start(cfg, record_action=True)
    reader = LineReader()
    rate = Rate(cfg['fps'])
    recording = False
    print(HELP_IDLE)

    try:
        while not stop:
            line = reader.poll()
            values, reason = cameras.snapshot(node, ['state', 'action'], MAX_AGE)
            if display and values:
                display.log(values, values['action'])
            if line == 'q':
                break
            if not recording:
                if line == '':
                    if reason:
                        print(f'시작할 수 없습니다 — {reason}')
                    else:
                        recording, start, slow = True, time.monotonic(), 0
                        print(f'에피소드 {dataset.meta.total_episodes} 기록 중 — {HELP_RECORDING}')
            elif line == '' and not dataset.has_pending_frames():
                recording = False
                print(f'frame 이 없어 저장하지 않았습니다 — {HELP_IDLE}')
            elif line == '':
                print(f'\n저장 중 ({dataset.writer.episode_buffer["size"]} frame)...')
                # 인코딩 프로세스는 같은 터미널에서 Ctrl+C 를 함께 받아 죽는다. 저장하는 동안은 무시하게 둔다
                handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
                try:
                    dataset.save_episode()
                finally:
                    signal.signal(signal.SIGINT, handler)
                recording = False
                print(f'저장했습니다. 에피소드 {dataset.meta.total_episodes}개 — {HELP_IDLE}')
            elif line == 'x':
                dataset.clear_episode_buffer()
                recording = False
                print(f'\n버렸습니다 — {HELP_IDLE}')
            elif reason:
                dataset.clear_episode_buffer()
                recording = False
                print(f'\n입력이 끊겨 에피소드를 버렸습니다 — {reason}\n{HELP_IDLE}')
            else:
                frame = {
                    'observation.state': values['state'],
                    'action': values['action'],
                    'task': args.task,
                }
                for camera in cfg['cameras']:
                    frame[f'observation.images.{camera}'] = values[camera]
                dataset.add_frame(frame)
                size = dataset.writer.episode_buffer['size']
                if size % cfg['fps'] == 0:
                    print(f'\r  {time.monotonic() - start:5.1f} s  {size} frame  주기 초과 {slow}회',
                          end='', flush=True)
            if not rate.sleep() and recording:
                slow += 1
    finally:
        if dataset.has_pending_frames():
            dataset.clear_episode_buffer()
            print('\n저장하지 않은 에피소드를 버렸습니다')
        dataset.finalize()
        ros_io.stop(node, spinner)
        cameras.close()
        if display:
            display.close()
        print(f'끝 — 에피소드 {dataset.meta.total_episodes}개')
