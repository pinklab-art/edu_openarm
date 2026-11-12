"""rerun 창에 카메라 영상과 관절값을 띄운다. lerobot-record --display_data 와 같은 화면이다."""

from lerobot.utils.rerun_visualization import init_rerun, log_rerun_data, shutdown_rerun

from openarm_lerobot.features import feature_names


class Display:

    def __init__(self, cfg, session_name):
        self.names = feature_names(cfg['arm'])
        self.cameras = list(cfg['cameras'])
        init_rerun(session_name=session_name)

    def log(self, values, action=None):
        """values 의 state·카메라 영상과 action(관절 8개)을 한 주기분 보낸다."""
        observation = {name: float(v) for name, v in zip(self.names, values['state'])}
        for camera in self.cameras:
            observation[camera] = values[camera]
        if action is not None:
            action = {name: float(v) for name, v in zip(self.names, action)}
        log_rerun_data(observation=observation, action=action)

    def close(self):
        shutdown_rerun()
