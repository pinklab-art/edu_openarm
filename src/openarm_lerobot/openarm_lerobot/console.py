"""기록·추론 루프의 터미널 입력과 종료 신호."""

import queue
import signal
import sys
import threading
import time


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
        self.next = time.monotonic()

    def sleep(self):
        self.next += self.period
        delay = self.next - time.monotonic()
        if delay > 0:
            time.sleep(delay)
            return True
        self.next = time.monotonic()
        return False
