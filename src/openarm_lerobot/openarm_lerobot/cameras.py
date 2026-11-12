"""카메라를 이 프로세스에서 직접 연다. LeRobot 의 OpenCVCamera 가 장치마다 읽기 스레드를 돌린다.

카메라 영상은 ROS topic 으로 보내지 않는다. 640×480 영상을 Python 노드가 topic 으로 받으면 역직렬화 비용으로
frame 이 빠지지만, 여기서는 웹캠의 MJPEG 를 한 번 풀기만 한다.
"""

from lerobot.cameras.opencv import OpenCVCamera, OpenCVCameraConfig


class Cameras:

    def __init__(self, cfg):
        self.cameras = {}
        for name, device in cfg['cameras'].items():
            camera = OpenCVCamera(OpenCVCameraConfig(
                index_or_path=device, fps=cfg['fps'],
                width=cfg['image_width'], height=cfg['image_height'], fourcc='MJPG'))
            try:
                camera.connect()
            except (ConnectionError, RuntimeError) as error:
                self.close()
                raise SystemExit(f'카메라 {name}({device}) 를 열 수 없습니다 — {error}')
            self.cameras[name] = camera
            print(f'카메라 {name}: {device}')

    def read(self, max_age):
        """카메라마다 마지막 frame(RGB). 하나라도 max_age 보다 오래됐거나 읽기가 멈췄으면 (None, 이유)."""
        frames = {}
        for name, camera in self.cameras.items():
            try:
                frames[name] = camera.read_latest(max_age_ms=int(max_age * 1000))
            except (TimeoutError, RuntimeError) as error:
                return None, f'카메라 {name} — {error}'
        return frames, None

    def snapshot(self, node, keys, max_age):
        """ROS 입력(keys)과 카메라 frame 을 한 dict 로. 어느 하나라도 없거나 오래됐으면 (None, 이유)."""
        values, reason = node.snapshot(keys, max_age)
        if reason:
            return None, reason
        frames, reason = self.read(max_age)
        if reason:
            return None, reason
        return {**values, **frames}, None

    def close(self):
        for camera in self.cameras.values():
            if camera.is_connected:
                camera.disconnect()
