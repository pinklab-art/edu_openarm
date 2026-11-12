"""lerobot.yaml 읽기. 카메라·기록·추론 설정의 유일한 통로."""

import os

import yaml

from ament_index_python.packages import get_package_share_directory

REQUIRED_KEYS = ('arm', 'fps', 'robot_type', 'display', 'cameras', 'image_width', 'image_height', 'dataset', 'policy')


def default_path():
    return os.path.join(get_package_share_directory('openarm_lerobot'), 'config', 'lerobot.yaml')


def load(path=None):
    path = path or default_path()
    with open(path, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    missing = [key for key in REQUIRED_KEYS if key not in (data or {})]
    if missing:
        raise ValueError(f'{path}: 항목 누락 {missing}')
    if data['arm'] not in ('left', 'right'):
        raise ValueError(f'{path}: arm 은 left 또는 right 여야 합니다')
    return data
