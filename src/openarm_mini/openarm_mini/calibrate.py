"""mini 의 영점 자세와 그리퍼 열림·닫힘을 읽어 보정값 파일에 적는 대화형 CLI."""

import argparse
import sys

from openarm_mini import config as config_io
from openarm_mini.feetech import FeetechBus
from openarm_mini.mapping import ARM_DOF


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='calibrate',
        description='mini 캘리브레이션. 팔마다 영점 자세와 그리퍼 열림·닫힘을 읽어 저장합니다.')
    parser.add_argument('--arm', help='이 팔 하나만 합니다. 생략하면 모든 팔을 차례로 합니다.')
    return parser.parse_args(argv)


def read_after_prompt(bus, ids, message):
    input(f'{message} — 준비되면 Enter: ')
    ticks = bus.read_positions(ids)
    if ticks is None:
        sys.exit('읽기에 실패했습니다. `ros2 run openarm_mini check` 로 서보 응답을 먼저 확인하세요.')
    return ticks


def calibrate_arm(arm, arm_cfg, baudrate):
    ids = arm_cfg['ids']
    try:
        bus = FeetechBus(arm_cfg['port'], baudrate)
    except RuntimeError as error:
        sys.exit(str(error))
    try:
        offsets = read_after_prompt(bus, ids, f'{arm} mini 를 영점 자세로 맞추세요')
        gripper_id = [ids[ARM_DOF]]
        open_ticks = read_after_prompt(bus, gripper_id, f'{arm} 그리퍼를 끝까지 여세요')[0]
        closed_ticks = read_after_prompt(bus, gripper_id, f'{arm} 그리퍼를 끝까지 닫으세요')[0]
    finally:
        bus.close()
    if open_ticks == closed_ticks:
        sys.exit(f'{arm} 그리퍼 열림·닫힘 tick 이 같습니다({open_ticks}). 그리퍼를 끝까지 움직였는지 확인하세요.')
    gripper_ticks = {'open': open_ticks, 'closed': closed_ticks}
    print(f'  offset_ticks {offsets}, gripper open {open_ticks} / closed {closed_ticks}')
    return offsets, gripper_ticks


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    cfg = config_io.load()
    for arm in config_io.arms_or_exit(cfg, args.arm):
        offsets, gripper_ticks = calibrate_arm(arm, cfg['arms'][arm], cfg['baudrate'])
        print(f'  {arm} 값을 {config_io.save_calibration(arm, offsets, gripper_ticks)} 에 저장했습니다.')
