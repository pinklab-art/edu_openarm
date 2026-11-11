"""mini 서보에 id 를 배정하는 CLI. 서보를 하나씩 보드에 연결해 실행한다."""

import argparse
import sys

from openarm_mini import config as config_io
from openarm_mini.feetech import FeetechBus

MAX_ID = 253
SCAN_MAX_ID = 20


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='register',
        description='mini 서보 id 배정. --id 없이 실행하면 버스를 스캔만 합니다.')
    parser.add_argument('--port', required=True, help='mini 보드 시리얼 포트 (예: /dev/ttyACM0)')
    parser.add_argument('--id', type=int, dest='new_id', help=f'배정할 id (1~{MAX_ID})')
    parser.add_argument('--from', type=int, dest='current_id',
                        help='바꿀 서보의 지금 id. 버스에 서보가 하나뿐이면 생략합니다.')
    parser.add_argument('--full-scan', action='store_true',
                        help=f'id 1~{MAX_ID} 전체를 스캔합니다 (기본 1~{SCAN_MAX_ID})')
    return parser.parse_args(argv)


def change_id(bus, found, current_id, new_id):
    if current_id is None:
        if len(found) != 1:
            sys.exit('서보가 여러 개 잡혔습니다. --from 으로 바꿀 서보의 지금 id 를 지정하세요.')
        current_id = next(iter(found))
    elif current_id not in found:
        sys.exit(f'id {current_id} 서보가 버스에 없습니다.')
    if current_id == new_id:
        print(f'이미 id {new_id} 입니다.')
        return
    if new_id in found:
        sys.exit(f'id {new_id} 는 버스의 다른 서보가 쓰고 있습니다.')
    if not bus.set_servo_id(current_id, new_id):
        sys.exit(f'id {current_id} → {new_id} 변경에 실패했습니다.')
    print(f'id {current_id} → {new_id} 바꿨습니다.')


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.new_id is not None and not 1 <= args.new_id <= MAX_ID:
        sys.exit(f'id 는 1~{MAX_ID} 이어야 합니다: {args.new_id}')
    cfg = config_io.load()
    try:
        bus = FeetechBus(args.port, cfg['baudrate'])
    except RuntimeError as error:
        sys.exit(str(error))
    try:
        max_id = MAX_ID if args.full_scan else SCAN_MAX_ID
        print(f'{args.port} 에서 id 1~{max_id} 스캔 중...')
        found = bus.scan(range(1, max_id + 1))
        if not found:
            sys.exit('응답하는 서보가 없습니다. 전원·배선을 확인하세요.')
        for servo_id, model in sorted(found.items()):
            print(f'  id {servo_id:3d}  응답 (모델 {model})')
        if args.new_id is not None:
            change_id(bus, found, args.current_id, args.new_id)
    finally:
        bus.close()
