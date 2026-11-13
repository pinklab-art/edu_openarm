"""mini teleop 시연을 LeRobot 데이터셋으로 기록한다.

fps 주기마다 팔 자세(/joint_states), teleop 명령(/safety_filter/command), 카메라 영상을 한 frame 으로 묶어
LeRobotDataset 에 쌓는다. 카메라는 ROS 를 거치지 않고 이 프로세스가 직접 연다.
시작하면 → 키를 기다렸다가 첫 에피소드를 기록한다. 그 뒤 진행은 lerobot-record 와 같아서, 에피소드를
episode_time_s 동안 기록하고 reset_time_s 동안 환경을 되돌린 뒤 다음 에피소드로 넘어가기를 num_episodes 개가
찰 때까지 되풀이하고, 단계가 바뀔 때마다 음성으로 알린다.
키도 lerobot-record 와 같다(→·n 다음 단계, ←·r 지금 에피소드 다시 기록). 다만 Esc·q 는 Ctrl+C 처럼
저장하지 않은 지금 에피소드를 버리고 끝낸다. 이미 저장한 에피소드만 남는다.
설정의 display 가 true 면 기록 전후 내내 rerun 창에 카메라 영상과 관절값을 띄운다.
같은 repo_id 데이터셋이 이미 있으면 그 뒤에 에피소드를 이어 붙인다.
"""

import argparse
import multiprocessing
import signal
import subprocess
import time

from lerobot.configs.video import RGBEncoderConfig
from lerobot.datasets import LeRobotDataset
from lerobot.utils.constants import HF_LEROBOT_HOME
from lerobot.utils.keyboard_input import init_keyboard_listener
from lerobot.utils.utils import say

from openarm_lerobot import config as config_io
from openarm_lerobot import ros_io
from openarm_lerobot.cameras import Cameras
from openarm_lerobot.console import NoEcho, Rate, stop_flag
from openarm_lerobot.display import Display
from openarm_lerobot.features import dataset_features, same_features

MAX_AGE = 0.2   # 이보다 오래된 입력이 있으면 frame 을 만들지 않는다 [s]

HELP = '→ 또는 n: 다음 단계   ← 또는 r: 다시 기록   Esc · q · Ctrl+C: 지금 에피소드 버리고 끝내기'


def same_video(features, video):
    """이미 있는 데이터셋 영상이 설정의 압축(g·crf)과 같은지. 다르면 한 파일 안에 압축이 섞인다.
    영상 info 는 첫 에피소드를 인코딩할 때 생기므로, 아직 저장한 에피소드가 없으면 비교할 것이 없다."""
    infos = [feature.get('info') or {} for feature in features.values() if feature['dtype'] == 'video']
    return all(info.get('video.g') == video['g'] and info.get('video.crf') == video['crf']
               for info in infos if 'video.g' in info)


def open_dataset(cfg, repo_id):
    features = dataset_features(cfg)
    encoder = RGBEncoderConfig(g=cfg['video']['g'], crf=cfg['video']['crf'])
    threads = 4 * len(cfg['cameras'])   # 영상 frame 을 PNG 로 쓰는 스레드. lerobot-record 기본값과 같다
    root = HF_LEROBOT_HOME / repo_id   # lerobot-train 이 --dataset.repo_id 만으로 찾는 자리
    if root.exists():
        dataset = LeRobotDataset.resume(repo_id, root=root, image_writer_threads=threads, rgb_encoder=encoder)
        if dataset.meta.fps != cfg['fps'] or not same_features(dataset.meta.features, features):
            raise SystemExit(f'{repo_id} 는 지금 설정(팔·fps·카메라)과 다른 데이터셋입니다. --repo-id 로 새 이름을 주세요')
        if not same_video(dataset.meta.features, cfg['video']):
            raise SystemExit(f'{repo_id} 는 지금 설정과 영상 압축(video)이 다른 데이터셋입니다. --repo-id 로 새 이름을 주세요')
        print(f'{repo_id}: 에피소드 {dataset.meta.total_episodes}개 뒤에 이어서 기록합니다')
    else:
        dataset = LeRobotDataset.create(repo_id, cfg['fps'], features, root=root, robot_type=cfg['robot_type'],
                                        image_writer_threads=threads, rgb_encoder=encoder)
        print(f'{repo_id}: 새 데이터셋을 만듭니다')
    print(f'저장 위치 {dataset.root}')
    return dataset


class Recorder:
    """카메라·ROS 입력·rerun 화면·키 입력을 쥐고 lerobot-record 의 기록·리셋 단계를 돈다."""

    def __init__(self, cfg, task, dataset):
        self.cfg, self.task, self.dataset = cfg, task, dataset
        self.stop = stop_flag()
        self.cameras = Cameras(cfg)
        self.display = Display(cfg, 'openarm_record') if cfg['display'] else None
        self.node, self.spinner = ros_io.start(cfg, record_action=True)
        self.rate = Rate(cfg['fps'])
        self.echo = NoEcho()
        self.listener, self.events = init_keyboard_listener()

    def announce(self, text, blocking=False):
        print(f'\n{text}')
        if self.cfg['play_sounds']:
            try:
                say(text, blocking)
            except subprocess.CalledProcessError:   # 음성 장치 문제로 기록을 멈추지 않는다
                pass

    def check_stop(self):
        """Ctrl+C 를 받았으면 지금 에피소드를 버리고 끝내도록 표시한다."""
        if self.stop:
            self.events.update(stop_recording=True, rerecord_episode=True, exit_early=True)
        return self.events['stop_recording']

    def tick(self):
        """입력 한 번 읽어 rerun 에 그린다. (값, 끊긴 이유)."""
        values, reason = self.cameras.snapshot(self.node, ['state', 'action'], MAX_AGE)
        if self.display and values:
            self.display.log(values, values['action'])
        return values, reason

    def wait_ready(self):
        """ROS 입력과 카메라가 모두 들어올 때까지 화면만 갱신하며 기다린다."""
        shown = None
        while not self.check_stop():
            _, reason = self.tick()
            if not reason:
                return
            if reason != shown:
                print(f'입력 대기 중 — {reason}')
                shown = reason
            self.rate.sleep()

    def wait_start(self):
        """첫 에피소드는 → 를 받을 때까지 기록하지 않고 화면만 갱신한다. 그 사이 팔과 물체를 시작 자세에 둔다."""
        self.wait_ready()
        if self.events['stop_recording']:
            return
        self.announce('Press right arrow to start')
        self.events.update(exit_early=False, rerecord_episode=False)
        while not self.check_stop() and not self.events['exit_early']:
            self.tick()
            self.rate.sleep()
        self.events.update(exit_early=False, rerecord_episode=False)

    def run(self, seconds, record):
        """seconds 동안 화면을 갱신하고 record 면 frame 을 쌓는다. → ← Esc Ctrl+C 로 일찍 끝난다."""
        start, slow = time.monotonic(), 0
        self.rate.restart()   # 직전 저장(인코딩)에 쓴 시간을 주기 초과로 세지 않는다
        while time.monotonic() - start < seconds:
            if self.check_stop() or self.events['exit_early']:
                self.events['exit_early'] = False
                break
            values, reason = self.tick()
            if record:
                if reason:
                    print(f'\n입력이 끊겨 이 에피소드를 다시 기록합니다 — {reason}')
                    self.events['rerecord_episode'] = True
                    break
                frame = {
                    'observation.state': values['state'],
                    'action': values['action'],
                    'task': self.task,
                }
                for camera in self.cfg['cameras']:
                    frame[f'observation.images.{camera}'] = values[camera]
                self.dataset.add_frame(frame)
                size = self.dataset.writer.episode_buffer['size']
                if size % self.cfg['fps'] == 0:
                    print(f'\r  {time.monotonic() - start:5.1f} / {seconds:g} s  {size} frame  주기 초과 {slow}회',
                          end='', flush=True)
            if not self.rate.sleep() and record:
                slow += 1

    def save(self):
        print(f'\n저장 중 ({self.dataset.writer.episode_buffer["size"]} frame)...')
        # 인코딩 프로세스는 같은 터미널에서 Ctrl+C 를 함께 받아 죽는다. 저장하는 동안은 무시하게 둔다
        handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            self.dataset.save_episode()
        finally:
            signal.signal(signal.SIGINT, handler)
        print(f'저장했습니다. 에피소드 {self.dataset.meta.total_episodes}개')

    def close(self):
        if self.dataset.has_pending_frames():
            self.dataset.clear_episode_buffer()
            print('\n저장하지 않은 에피소드를 버렸습니다')
        # finalize 를 빠뜨리면 마지막 parquet 파일이 닫히지 않아 이번 실행의 에피소드를 모두 잃는다. 다른 정리보다 먼저 한다
        self.dataset.finalize()
        if self.listener is not None:
            self.listener.stop()
        self.echo.restore()
        self.announce('Stop recording', blocking=True)
        ros_io.stop(self.node, self.spinner)
        self.cameras.close()
        if self.display:
            self.display.close()
        print(f'끝 — 에피소드 {self.dataset.meta.total_episodes}개')


def main():
    cfg = config_io.load()
    parser = argparse.ArgumentParser(description='mini teleop 시연을 LeRobot 데이터셋으로 기록')
    parser.add_argument('--repo-id', default=cfg['dataset']['repo_id'])
    parser.add_argument('--task', default=cfg['dataset']['task'])
    parser.add_argument('--num-episodes', type=int, default=cfg['dataset']['num_episodes'])
    parser.add_argument('--episode-time-s', type=float, default=cfg['dataset']['episode_time_s'])
    parser.add_argument('--reset-time-s', type=float, default=cfg['dataset']['reset_time_s'])
    args = parser.parse_args()

    # save_episode 는 카메라마다 프로세스를 띄워 영상을 인코딩한다. 기본 fork 는 rclpy 스레드가 잡은 lock 까지
    # 복사해 자식이 멈추므로, 새 인터프리터로 띄우는 spawn 을 쓴다.
    multiprocessing.set_start_method('spawn')
    dataset = open_dataset(cfg, args.repo_id)
    rec = Recorder(cfg, args.task, dataset)
    events = rec.events
    print(HELP)

    try:
        rec.wait_start()
        recorded = 0
        while recorded < args.num_episodes and not events['stop_recording']:
            rec.wait_ready()
            if events['stop_recording']:
                break
            rec.announce(f'Recording episode {dataset.meta.total_episodes}')
            rec.run(args.episode_time_s, record=True)

            # 마지막 에피소드는 리셋 없이 저장한다. 다시 기록할 때는 리셋부터 한다
            if not events['stop_recording'] and (recorded < args.num_episodes - 1 or events['rerecord_episode']):
                rec.announce('Reset the environment')
                rec.run(args.reset_time_s, record=False)

            # 다시 기록(←)과 끝내기(Esc·q·Ctrl+C)는 아직 저장하지 않은 이 에피소드를 버린다
            if events['rerecord_episode'] or events['stop_recording']:
                events['rerecord_episode'] = False
                events['exit_early'] = False
                if dataset.has_pending_frames():
                    dataset.clear_episode_buffer()
                    print('\n저장하지 않은 에피소드를 버렸습니다')
                if not events['stop_recording']:
                    rec.announce('Re-record episode')
                continue

            if dataset.has_pending_frames():
                rec.save()
                recorded += 1
            else:
                print('\nframe 이 없어 저장하지 않았습니다')
    finally:
        rec.close()
