"""Feetech STS3215 서보 버스. pyserial 로 STS 프로토콜 패킷을 직접 주고받는다.

패킷   0xFF 0xFF  ID  LEN  INSTR  PARAM...  CHECKSUM
응답   0xFF 0xFF  ID  LEN  ERROR  DATA...   CHECKSUM
LEN 은 LEN 뒤의 바이트 수, CHECKSUM 은 ID 부터 마지막 PARAM 까지 합의 비트 반전 하위 8비트다.
2바이트 값은 하위 바이트가 먼저 온다.
"""

import termios

import serial

BROADCAST_ID = 0xFE
PING = 0x01
READ = 0x02
WRITE = 0x03
SYNC_READ = 0x82

# STS 시리즈 제어 테이블 주소
MODEL_ADDRESS = 3
ID_ADDRESS = 5
LOCK_ADDRESS = 55
PRESENT_POSITION_ADDRESS = 56

TIMEOUT_SEC = 0.05
# 보드를 뽑으면 pyserial 이 감싸지 못한 termios·OS 오류가 그대로 올라온다.
PORT_ERRORS = (serial.SerialException, OSError, termios.error)


def checksum(body):
    """ID 부터 마지막 PARAM 까지의 바이트 → checksum."""
    return ~sum(body) & 0xFF


def packet(servo_id, instruction, params=()):
    """명령 패킷 바이트열."""
    body = [servo_id, len(params) + 2, instruction, *params]
    return bytes([0xFF, 0xFF, *body, checksum(body)])


def word(low, high):
    return low | (high << 8)


class FeetechBus:
    """리더 서보 위치를 tick 으로 읽고, id 를 바꾸는 시리얼 버스."""

    def __init__(self, port, baudrate):
        try:
            self._serial = serial.Serial(port, baudrate, timeout=TIMEOUT_SEC)
        except serial.SerialException as error:
            raise RuntimeError(f'{port}: 포트를 열지 못했습니다 ({error})') from error

    def _send(self, data):
        self._serial.reset_input_buffer()
        self._serial.write(data)

    def _receive(self, servo_id):
        """servo_id 의 응답 하나를 읽어 (error, data) 로 돌려준다. 시간 초과·손상이면 None."""
        header = self._serial.read(4)
        if len(header) < 4 or header[0] != 0xFF or header[1] != 0xFF or header[2] != servo_id:
            return None
        rest = self._serial.read(header[3])
        if header[3] < 2 or len(rest) < header[3] or rest[-1] != checksum([servo_id, header[3], *rest[:-1]]):
            return None
        return rest[0], bytes(rest[1:-1])

    def read_positions(self, ids):
        """ids 순서대로 현재 위치 tick 을 한 번에 읽는다(sync read). 하나라도 실패하면 None.

        보드가 뽑혀 포트가 끊기면 포트를 닫아 두고, 다음 호출에서 다시 열어 본다.
        """
        try:
            if not self._serial.is_open:
                self._serial.open()
            self._send(packet(BROADCAST_ID, SYNC_READ, [PRESENT_POSITION_ADDRESS, 2, *ids]))
            ticks = []
            for servo_id in ids:
                reply = self._receive(servo_id)
                if reply is None or len(reply[1]) != 2:
                    return None
                ticks.append(word(*reply[1]))
            return ticks
        except PORT_ERRORS:
            self._serial.close()
            return None

    def ping(self, servo_id):
        """서보가 응답하면 모델 번호, 아니면 None."""
        self._send(packet(servo_id, PING))
        if self._receive(servo_id) is None:
            return None
        self._send(packet(servo_id, READ, [MODEL_ADDRESS, 2]))
        reply = self._receive(servo_id)
        if reply is None or len(reply[1]) != 2:
            return None
        return word(*reply[1])

    def scan(self, id_range):
        """id_range 를 차례로 ping 해 {id: 모델 번호} 로 돌려준다."""
        found = {}
        for servo_id in id_range:
            model = self.ping(servo_id)
            if model is not None:
                found[servo_id] = model
        return found

    def write_u8(self, servo_id, address, value):
        """1바이트 레지스터 쓰기. 성공 여부를 돌려준다."""
        self._send(packet(servo_id, WRITE, [address, value]))
        reply = self._receive(servo_id)
        return reply is not None and reply[0] == 0

    def set_servo_id(self, current_id, new_id):
        """서보 id 를 바꾼다. EEPROM 잠금을 풀고 쓰고 다시 잠근다."""
        if not self.write_u8(current_id, LOCK_ADDRESS, 0):
            return False
        # 쓰기 응답 대신 새 id 의 ping 으로 바뀌었는지 확인한다.
        self.write_u8(current_id, ID_ADDRESS, new_id)
        if self.ping(new_id) is None:
            self.write_u8(current_id, LOCK_ADDRESS, 1)
            return False
        self.write_u8(new_id, LOCK_ADDRESS, 1)
        return True

    def close(self):
        self._serial.close()
