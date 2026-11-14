"""학습한 policy 로 팔을 움직인다.

fps 주기마다 팔 자세(/joint_states)와 카메라 영상(이 프로세스가 직접 연다)으로 다음 관절 명령을 계산해 /safety_filter/command 로 보낸다.
관절 한계·속도 제한은 안전 필터가 맡는다. 실행·멈춤은 터미널에서 Enter 로 하고, 멈추면 팔은 그 자리에 선다.
설정의 display 가 true 면 rerun 창에 카메라 영상과 관절값(실행 중에는 policy 명령까지)을 띄운다.
"""

import argparse

import torch

from lerobot.common.control_utils import predict_action
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies import get_policy_class, make_pre_post_processors

from openarm_lerobot import config as config_io
from openarm_lerobot import ros_io
from openarm_lerobot.cameras import Cameras
from openarm_lerobot.console import LineReader, Rate, stop_flag
from openarm_lerobot.display import Display

MAX_AGE = 0.2   # 이보다 오래된 입력이 있으면 멈춘다 [s]

HELP_IDLE = 'Enter: 실행   q+Enter: 끝내기'
HELP_RUNNING = 'Enter: 멈춤   q+Enter: 끝내기'


def load_policy(path, device):
    policy_cfg = PreTrainedConfig.from_pretrained(path)
    policy_cfg.pretrained_path = path
    policy_cfg.device = device
    policy = get_policy_class(policy_cfg.type).from_pretrained(path, config=policy_cfg)
    policy.to(device).eval()
    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg, pretrained_path=path,
        preprocessor_overrides={'device_processor': {'device': device}})
    return policy, preprocessor, postprocessor


def main():
    cfg = config_io.load()
    parser = argparse.ArgumentParser(description='학습한 policy 로 팔 움직이기')
    parser.add_argument('policy_path', help='학습 결과의 pretrained_model 폴더')
    parser.add_argument('--task', default=cfg['dataset']['task'])
    args = parser.parse_args()

    device = cfg['policy']['device']
    if device == 'cuda' and not torch.cuda.is_available():
        print('CUDA 를 쓸 수 없어 cpu 로 추론합니다')
        device = 'cpu'
    stop = stop_flag()
    policy, preprocessor, postprocessor = load_policy(args.policy_path, device)
    print(f'policy {policy.config.type} 를 {device} 에 불러왔습니다')
    if policy.config.type == 'act':   # chunk 설정은 ACT 의 config.json 에만 있다
        print(f'chunk {policy.config.chunk_size} 중 {policy.config.n_action_steps} 사용, '
              f'temporal ensembling {policy.config.temporal_ensemble_coeff}')

    cameras = Cameras(cfg)
    display = Display(cfg, 'openarm_policy') if cfg['display'] else None
    node, spinner = ros_io.start(cfg, record_action=False)
    reader = LineReader()
    rate = Rate(cfg['fps'])
    running = False
    print(HELP_IDLE)

    try:
        while not stop:
            line = reader.poll()
            values, reason = cameras.snapshot(node, ['state'], MAX_AGE)
            command = None
            if line == 'q':
                break
            if not running:
                if line == '':
                    if reason:
                        print(f'실행할 수 없습니다 — {reason}')
                    else:
                        # 지난 실행에서 쌓인 action chunk 를 비우고 새로 시작한다.
                        policy.reset()
                        preprocessor.reset()
                        postprocessor.reset()
                        running = True
                        print(f'실행 중 — {HELP_RUNNING}')
            elif line == '':
                running = False
                print(f'멈췄습니다 — {HELP_IDLE}')
            elif reason:
                running = False
                print(f'입력이 끊겨 멈췄습니다 — {reason}\n{HELP_IDLE}')
            else:
                observation = {'observation.state': values['state']}
                for camera in cfg['cameras']:
                    observation[f'observation.images.{camera}'] = values[camera]
                action = predict_action(
                    observation, policy, torch.device(device), preprocessor, postprocessor,
                    use_amp=False, task=args.task, robot_type=cfg['robot_type'])
                command = action.squeeze(0).cpu().numpy()
                node.publish_command(command)
            if display and values:
                display.log(values, command)
            rate.sleep()
    finally:
        ros_io.stop(node, spinner)
        cameras.close()
        if display:
            display.close()
