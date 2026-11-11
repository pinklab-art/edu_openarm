import pytest

from openarm_mini import feetech


def test_packet_ping():
    # 공식 SDK 가 id 1 PING 으로 보내는 바이트열과 같다.
    assert feetech.packet(1, feetech.PING) == bytes([0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB])


def test_packet_sync_read():
    data = feetech.packet(feetech.BROADCAST_ID, feetech.SYNC_READ, [56, 2, 1, 2])
    assert data[:5] == bytes([0xFF, 0xFF, 0xFE, 0x06, 0x82])
    assert data[-1] == feetech.checksum(list(data[2:-1]))


def reply(servo_id, error, payload):
    body = [servo_id, len(payload) + 2, error, *payload]
    return bytes([0xFF, 0xFF, *body, feetech.checksum(body)])


class FakeSerial:
    """쓴 바이트를 모으고, 준비된 응답을 읽어 준다."""

    def __init__(self, replies):
        self.buffer = bytearray(b''.join(replies))
        self.written = bytearray()
        self.is_open = True

    def reset_input_buffer(self):
        pass

    def write(self, data):
        self.written += data

    def read(self, size):
        chunk, self.buffer = bytes(self.buffer[:size]), self.buffer[size:]
        return chunk

    def open(self):
        raise feetech.serial.SerialException('보드 없음')

    def close(self):
        self.is_open = False


@pytest.fixture
def make_bus(monkeypatch):
    def make(replies):
        fake = FakeSerial(replies)
        monkeypatch.setattr(feetech.serial, 'Serial', lambda *args, **kwargs: fake)
        return feetech.FeetechBus('/dev/null', 1000000)
    return make


def test_read_positions(make_bus):
    bus = make_bus([reply(1, 0, [0x00, 0x08]), reply(2, 0, [0xA7, 0x0A])])
    assert bus.read_positions([1, 2]) == [2048, 2727]


def test_read_positions_missing_servo(make_bus):
    bus = make_bus([reply(1, 0, [0x00, 0x08])])
    assert bus.read_positions([1, 2]) is None


def test_read_positions_bad_checksum(make_bus):
    broken = bytearray(reply(1, 0, [0x00, 0x08]))
    broken[-1] ^= 0xFF
    bus = make_bus([bytes(broken)])
    assert bus.read_positions([1]) is None


def test_ping_returns_model(make_bus):
    bus = make_bus([reply(3, 0, []), reply(3, 0, [0x09, 0x03])])
    assert bus.ping(3) == 777


def test_read_positions_unplugged_then_closed(make_bus):
    bus = make_bus([])
    bus._serial.reset_input_buffer = lambda: (_ for _ in ()).throw(OSError(5, 'Input/output error'))
    assert bus.read_positions([1]) is None
    assert not bus._serial.is_open
    assert bus.read_positions([1]) is None   # 다시 열기 실패도 None


def test_read_positions_zero_length_reply(make_bus):
    bus = make_bus([bytes([0xFF, 0xFF, 0x01, 0x00])])
    assert bus.read_positions([1]) is None
