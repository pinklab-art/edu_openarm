"""기록·추론 루프의 터미널 입력과 종료 신호."""

import atexit
import queue
import signal
import sys
import threading
import time

try:
    import termios
except ImportError:   # Windows
    termios = None


class LineReader:
    """터미널에서 친 줄을 백그라운드 스레드로 받아 둔다. 루프는 poll 로 막힘 없이 꺼낸다."""

    def __init__(self):
        self.lines = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in sys.stdin:
            self.lines.put(line.strip().lower())

    def poll(self):
        try:
            return self.lines.get_nowait()
        except queue.Empty:
            return None


def stop_flag():
    """Ctrl+C·SIGTERM 을 받으면 채워지는 리스트. 루프는 지금 frame 을 마친 뒤 빠져나간다."""
    stop = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.append(True))
    return stop


class Rate:
    """fps 주기로 루프를 맞춘다. 주기를 넘기면 다음 주기부터 다시 센다."""

    def __init__(self, fps):
        self.period = 1.0 / fps
        self.restart()

    def restart(self):
        """지금부터 주기를 다시 센다. 루프 밖에서 오래 멈췄다가 다시 돌 때 부른다."""
        self.next = time.monotonic()

    def sleep(self):
        self.next += self.period
        delay = self.next - time.monotonic()
        if delay > 0:
            time.sleep(delay)
            return True
        self.next = time.monotonic()
        return False


class NoEcho:
    """터미널 echo 를 끈다. 화면 전체에서 키를 받는 동안 → 가 ^[[C 로 찍히지 않게 하고, restore 로 되돌린다."""

    def __init__(self):
        self.saved = None
        if termios and sys.stdin.isatty():
            fd = sys.stdin.fileno()
            self.saved = termios.tcgetattr(fd)
            attrs = termios.tcgetattr(fd)
            attrs[3] &= ~termios.ECHO   # lflags
            termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
            atexit.register(self.restore)   # 정리 도중 예외로 끝나도 셸 echo 를 되돌린다

    def restore(self):
        if self.saved is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.saved)
            self.saved = None
