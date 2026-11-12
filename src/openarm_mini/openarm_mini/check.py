"""mini 서보 응답과 관절값을 확인하는 CLI. 관절을 움직이며 방향·영점을 눈으로 본다.

보정값이 없으면 서보 응답과 tick 만 보여 준다. 각도는 calibrate 뒤에 나온다.
"""

import argparse
import math
import sys
import time

from openarm_mini import config as config_io
from openarm_mini.feetech import FeetechBus
from openarm_mini.mapping import ARM_DOF, arm_sample

READ_PERIOD_SEC = 0.1


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='check',
        description='mini 서보 응답을 확인한 뒤 관절값을 실시간으로 보여 줍니다. 종료는 Ctrl+C.')
    parser.add_argument('--arm', help='이 팔 하나만 확인합니다. 생략하면 모든 팔을 확인합니다.')
    return parser.parse_args(argv)


def label(index):
    return f'joint{index + 1}' if index < ARM_DOF else 'gripper'


def ping_arm(arm, bus, ids):
    """서보마다 응답을 찍고, 응답하지 않은 id 목록을 돌려준다."""
    missing = []
    for index, servo_id in enumerate(ids):
        model = bus.ping(servo_id)
        state = '응답 없음' if model is None else f'응답 (모델 {model})'
        print(f'  {arm:5s} {label(index):8s} id {servo_id:2d}  {state}')
        if model is None:
            missing.append(servo_id)
    return missing


def rows_for(arm, arm_cfg, ticks, cfg, calibrated):
    if not calibrated:
        return [f'{arm:5s} {label(i):8s} {ticks[i]:4d} tick' for i in range(ARM_DOF + 1)]
    joints, gripper = arm_sample(arm_cfg, ticks, cfg['ticks_per_rev'], cfg['gripper_travel'])
    rows = [f'{arm:5s} {label(i):8s} {ticks[i]:4d} tick  {math.degrees(joints[i]):+7.1f} deg'
            for i in range(ARM_DOF)]
    rows.append(f'{arm:5s} {label(ARM_DOF):8s} {ticks[ARM_DOF]:4d} tick  {gripper * 1000:5.1f} mm')
    return rows


def live_view(entries, cfg, calibrated):
    print('\n관절을 하나씩 움직여 방향과 영점이 맞는지 보세요. 종료는 Ctrl+C.')
    printed = 0
    try:
        while True:
            rows = []
            for arm, arm_cfg, bus in entries:
                ticks = bus.read_positions(arm_cfg['ids'])
                rows += [f'{arm:5s} 읽기 실패'] if ticks is None else rows_for(arm, arm_cfg, ticks, cfg, calibrated)
            if printed:
                sys.stdout.write(f'\x1b[{printed}A')
            sys.stdout.write(''.join(f'\x1b[2K{row}\n' for row in rows))
            sys.stdout.flush()
            printed = len(rows)
            time.sleep(READ_PERIOD_SEC)
    except KeyboardInterrupt:
        print()


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    cfg = config_io.load()
    arms = config_io.arms_or_exit(cfg, args.arm)
    calibrated = True
    try:
        config_io.apply_calibration(cfg, arms)
    except config_io.CalibrationMissing as error:
        calibrated = False
        print(f'{error}\n보정 전이라 tick 만 표시합니다.\n')
    entries = []
    failed = False
    try:
        for arm in arms:
            arm_cfg = cfg['arms'][arm]
            print(f'{arm}: {arm_cfg["port"]}, 서보 id {arm_cfg["ids"]}')
            try:
                bus = FeetechBus(arm_cfg['port'], cfg['baudrate'])
            except RuntimeError as error:
                print(f'  {error}')
                failed = True
                continue
            entries.append((arm, arm_cfg, bus))
            missing = ping_arm(arm, bus, arm_cfg['ids'])
            if missing:
                print(f'  {arm}: 서보 {missing} 가 응답하지 않습니다. 배선을 확인하고, id 는 register 로 배정하세요.')
                failed = True
        if not failed:
            live_view(entries, cfg, calibrated)
    finally:
        for _arm, _cfg, bus in entries:
            bus.close()
    if failed:
        sys.exit(1)
