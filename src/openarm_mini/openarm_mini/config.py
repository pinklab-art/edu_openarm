"""mini.yaml 읽기·쓰기. 리더암 설정의 유일한 통로."""

import os

import yaml

from ament_index_python.packages import get_package_share_directory

HEADER = """\
# OpenArm mini 리더암 설정.
# arms.<arm>.port 는 `ros2 run openarm_mini udev`, offset_ticks·gripper_ticks 는 `ros2 run openarm_mini calibrate` 가 갱신한다.

"""
REQUIRED_KEYS = ('rate_hz', 'baudrate', 'ticks_per_rev', 'gripper_travel', 'arms')


def default_path():
    """설치된 mini.yaml 경로. --symlink-install 이면 src 의 파일로 이어진다."""
    return os.path.join(get_package_share_directory('openarm_mini'), 'config', 'mini.yaml')


def load():
    path = default_path()
    with open(path, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    missing = [key for key in REQUIRED_KEYS if key not in (data or {})]
    if missing:
        raise ValueError(f'{path}: 항목 누락 {missing}')
    return data


def save(data):
    """설정을 쓰고 경로를 돌려준다. 맨 위 머리말만 다시 붙고 줄 끝 주석은 남지 않는다."""
    path = default_path()
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(HEADER)
        yaml.safe_dump(data, handle, allow_unicode=True, default_flow_style=None, sort_keys=False)
    return path


def arms_or_exit(cfg, arm):
    """--arm 인자로 고른 팔 목록. 설정에 없는 팔이면 종료한다."""
    arms = [arm] if arm else list(cfg['arms'])
    unknown = [name for name in arms if name not in cfg['arms']]
    if unknown:
        raise SystemExit(f'설정에 없는 팔: {unknown} (가능: {sorted(cfg["arms"])})')
    return arms
