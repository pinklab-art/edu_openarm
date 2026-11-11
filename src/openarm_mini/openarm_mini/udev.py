"""mini 보드를 하나씩 꽂아 /dev/openarm_mini_<arm> 고정 이름을 거는 대화형 CLI."""

import argparse
import glob
import os
import subprocess
import sys
import time

from openarm_mini import config as config_io

RULES_PATH = '/etc/udev/rules.d/99-openarm-mini.rules'
RULES_HEADER = '# OpenArm mini 리더 보드 고정 이름 규칙\n'
SYMLINK_PREFIX = 'openarm_mini_'
TTY_PATTERNS = ('/dev/ttyUSB*', '/dev/ttyACM*')
ENUMERATION_WAIT_SEC = 1.0


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='udev',
        description='mini 보드에 /dev/openarm_mini_<arm> 고정 이름을 겁니다. 안내에 따라 모든 팔의 보드를 '
                    '하나씩 꽂으면 새 포트를 알아서 찾습니다. 좌우 보드를 서로 비교해야 하므로 늘 모든 팔을 함께 등록합니다.')
    return parser.parse_args(argv)


def prompt(message):
    input(f'{message} — 준비되면 Enter: ')


def list_ttys():
    return {port for pattern in TTY_PATTERNS for port in glob.glob(pattern)}


def usb_attributes(port):
    """tty 뒤에 붙은 USB 장치의 식별 속성. 못 찾으면 None."""
    node = os.path.realpath(f'/sys/class/tty/{os.path.basename(port)}/device')
    while node not in ('/', ''):
        if os.path.exists(os.path.join(node, 'idVendor')):
            def read(attr):
                path = os.path.join(node, attr)
                if not os.path.exists(path):
                    return None
                with open(path, 'r', encoding='ascii') as handle:
                    return handle.read().strip()
            return {'idVendor': read('idVendor'), 'idProduct': read('idProduct'),
                    'serial': read('serial'), 'kernels': os.path.basename(node)}
        node = os.path.dirname(node)
    return None


def build_rule(arm, attrs):
    """한 팔의 udev 규칙 한 줄."""
    parts = ['SUBSYSTEM=="tty"',
             f'ATTRS{{idVendor}}=="{attrs["idVendor"]}"',
             f'ATTRS{{idProduct}}=="{attrs["idProduct"]}"']
    if attrs.get('serial'):
        parts.append(f'ATTRS{{serial}}=="{attrs["serial"]}"')
    else:
        # serial 이 없는 보드는 꽂은 USB 포트 위치로 구분한다.
        parts.append(f'KERNELS=="{attrs["kernels"]}"')
    parts += [f'SYMLINK+="{SYMLINK_PREFIX}{arm}"', 'MODE="0660"', 'GROUP="dialout"']
    return ', '.join(parts)


def resolve_conflicts(collected):
    """serial 이 서로 같은 보드는 USB 포트 위치로 구분하게 바꾼다."""
    serials = [attrs['serial'] for attrs in collected.values() if attrs['serial']]
    duplicated = {serial for serial in serials if serials.count(serial) > 1}
    return {arm: dict(attrs, serial=None) if attrs['serial'] in duplicated else attrs
            for arm, attrs in collected.items()}


def merge_rules(existing_text, arm, rule):
    """기존 규칙 파일에서 같은 팔의 줄만 바꾼 새 내용."""
    marker = f'SYMLINK+="{SYMLINK_PREFIX}{arm}"'
    lines = [line for line in existing_text.splitlines()
             if line.strip() and not line.startswith('#') and marker not in line]
    lines.append(rule)
    return RULES_HEADER + '\n'.join(lines) + '\n'


def read_rules_file():
    if not os.path.exists(RULES_PATH):
        return ''
    with open(RULES_PATH, 'r', encoding='utf-8') as handle:
        return handle.read()


def install(content):
    subprocess.run(['sudo', 'tee', RULES_PATH], input=content, text=True,
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['sudo', 'udevadm', 'control', '--reload-rules'], check=True)
    subprocess.run(['sudo', 'udevadm', 'trigger', '--subsystem-match=tty'], check=True)


def detect_new_port(baseline):
    """baseline 이후 새로 생긴 tty 포트 하나."""
    time.sleep(ENUMERATION_WAIT_SEC)
    new_ports = sorted(list_ttys() - baseline)
    if not new_ports:
        sys.exit('새 포트가 보이지 않습니다. 보드를 꽂았는지 확인하고 다시 실행하세요.')
    if len(new_ports) > 1:
        sys.exit(f'새 포트가 여러 개입니다 {new_ports}. 보드를 하나씩 꽂으세요.')
    return new_ports[0]


def collect(arms):
    """팔마다 보드를 꽂게 해 USB 속성을 모은다."""
    prompt('mini 보드를 모두 뽑으세요')
    baseline = list_ttys()
    collected = {}
    for arm in arms:
        prompt(f'{arm} 보드를 꽂으세요')
        port = detect_new_port(baseline)
        attrs = usb_attributes(port)
        if attrs is None or not attrs['idVendor']:
            sys.exit(f'{port} 의 USB 속성을 찾지 못했습니다.')
        print(f'  {arm}: {port}, vendor {attrs["idVendor"]}, product {attrs["idProduct"]}, '
              f'serial {attrs["serial"] or "(없음 — USB 포트 위치로 구분)"}')
        collected[arm] = attrs
        baseline = list_ttys()
    return collected


def main(argv=None):
    parse_args(sys.argv[1:] if argv is None else argv)
    cfg = config_io.load()
    arms = list(cfg['arms'])

    attributes = resolve_conflicts(collect(arms))
    fallbacks = [attrs['kernels'] for attrs in attributes.values() if not attrs['serial']]
    if len(set(fallbacks)) < len(fallbacks):
        sys.exit('보드에 serial 이 없고 같은 USB 포트에 꽂았습니다. 서로 다른 포트에 꽂아 다시 실행하세요.')

    rules = {arm: build_rule(arm, attrs) for arm, attrs in attributes.items()}
    content = read_rules_file()
    for arm, rule in rules.items():
        content = merge_rules(content, arm, rule)
    print(f'\n{RULES_PATH} 에 넣을 규칙:')
    for rule in rules.values():
        print(f'  {rule}')
    prompt('sudo 로 등록합니다')
    try:
        install(content)
    except subprocess.CalledProcessError as error:
        sys.exit(f'규칙 등록에 실패했습니다: {error}')

    for arm in rules:
        cfg['arms'][arm]['port'] = f'/dev/{SYMLINK_PREFIX}{arm}'
    config_io.save(cfg)
    print('\n등록했습니다. 보드를 뽑았다 다시 꽂은 뒤 고정 이름을 확인하세요:')
    for arm in rules:
        print(f'  ls -l /dev/{SYMLINK_PREFIX}{arm}')
