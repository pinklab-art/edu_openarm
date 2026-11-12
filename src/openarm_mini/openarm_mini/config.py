"""mini 설정 읽기와 보정값 읽기·쓰기. 리더암 설정의 유일한 통로.

mini.yaml      모든 mini 에 같은 설정(포트 이름·서보 id·방향·버스 속도). 리포에 들어 있고 코드가 고쳐 쓰지 않는다.
CALIBRATION    mini 한 대마다 다른 보정값(영점 tick·그리퍼 열림/닫힘 tick). `calibrate` 가 쓰고 리포 밖에 둔다.
"""

import os

import yaml

from ament_index_python.packages import get_package_share_directory

from openarm_mini.mapping import ARM_DOF

CALIBRATION_PATH = os.path.expanduser('~/.config/openarm_mini/calibration.yaml')
CALIBRATION_HEADER = """\
# OpenArm mini 보정값. `ros2 run openarm_mini calibrate` 가 쓴다.
# offset_ticks: 영점 자세의 서보 tick (관절 1~7·그리퍼), gripper_ticks: 그리퍼 끝까지 열림·닫힘 tick

"""
REQUIRED_KEYS = ('rate_hz', 'baudrate', 'ticks_per_rev', 'gripper_travel', 'arms')


class CalibrationMissing(ValueError):
    """보정값 파일이 없거나, 쓰려는 팔의 보정값이 없거나 형식이 틀렸다."""


def default_path():
    """설치된 mini.yaml 경로."""
    return os.path.join(get_package_share_directory('openarm_mini'), 'config', 'mini.yaml')


def load():
    """mini.yaml. 보정값은 들어 있지 않다."""
    path = default_path()
    with open(path, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    missing = [key for key in REQUIRED_KEYS if key not in (data or {})]
    if missing:
        raise ValueError(f'{path}: 항목 누락 {missing}')
    return data


def load_calibration_file():
    """보정값 파일 전체. 파일이 없으면 빈 dict."""
    if not os.path.exists(CALIBRATION_PATH):
        return {}
    with open(CALIBRATION_PATH, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def save_calibration(arm, offset_ticks, gripper_ticks):
    """한 팔의 보정값을 쓰고 파일 경로를 돌려준다. 다른 팔의 보정값은 그대로 둔다."""
    data = load_calibration_file()
    data[arm] = {'offset_ticks': list(offset_ticks), 'gripper_ticks': dict(gripper_ticks)}
    os.makedirs(os.path.dirname(CALIBRATION_PATH), exist_ok=True)
    with open(CALIBRATION_PATH, 'w', encoding='utf-8') as handle:
        handle.write(CALIBRATION_HEADER)
        yaml.safe_dump(data, handle, allow_unicode=True, default_flow_style=None, sort_keys=False)
    return CALIBRATION_PATH


def _valid(entry):
    try:
        gripper = entry['gripper_ticks']
        return (len(entry['offset_ticks']) == ARM_DOF + 1
                and isinstance(gripper['open'], int) and isinstance(gripper['closed'], int)
                and gripper['open'] != gripper['closed'])
    except (KeyError, TypeError):
        return False


def apply_calibration(cfg, arms):
    """load() 로 읽은 설정의 arms 각각에 보정값을 합친다. 보정값이 없거나 틀린 팔이 있으면 CalibrationMissing."""
    calibration = load_calibration_file()
    missing = [arm for arm in arms if not _valid(calibration.get(arm))]
    if missing:
        option = f' --arm {missing[0]}' if len(missing) == 1 else ''
        raise CalibrationMissing(
            f'{"·".join(missing)} mini 의 보정값이 없습니다 ({CALIBRATION_PATH}).\n'
            f'먼저 실행하세요: ros2 run openarm_mini calibrate{option}')
    for arm in arms:
        cfg['arms'][arm].update(calibration[arm])


def arms_or_exit(cfg, arm):
    """--arm 인자로 고른 팔 목록. 설정에 없는 팔이면 종료한다."""
    arms = [arm] if arm else list(cfg['arms'])
    unknown = [name for name in arms if name not in cfg['arms']]
    if unknown:
        raise SystemExit(f'설정에 없는 팔: {unknown} (가능: {sorted(cfg["arms"])})')
    return arms
