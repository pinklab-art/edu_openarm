"""ROS 관절 이름 ↔ LeRobot 데이터셋 feature 이름. ROS·torch 없이 numpy 만 쓴다."""

import numpy as np

ARM_DOF = 7


def ros_joint_names(arm):
    """팔 하나의 ROS 관절 이름 8개(관절 7 + finger_joint1). state·action 의 순서다."""
    return [f'openarm_{arm}_joint{i}' for i in range(1, ARM_DOF + 1)] + [f'openarm_{arm}_finger_joint1']


def feature_names(arm):
    """데이터셋에 남는 state·action 이름. LeRobot 의 <팔>_<관절>.pos 형식이다."""
    return [f'{arm}_joint{i}.pos' for i in range(1, ARM_DOF + 1)] + [f'{arm}_gripper.pos']


def dataset_features(cfg):
    """LeRobotDataset.create 에 넘기는 feature 정의."""
    names = feature_names(cfg['arm'])
    features = {
        'observation.state': {'dtype': 'float32', 'shape': (len(names),), 'names': names},
        'action': {'dtype': 'float32', 'shape': (len(names),), 'names': names},
    }
    for camera in cfg['cameras']:
        features[f'observation.images.{camera}'] = {
            'dtype': 'video',
            'shape': (cfg['image_height'], cfg['image_width'], 3),
            'names': ['height', 'width', 'channels'],
        }
    return features


def same_features(stored, features):
    """데이터셋에 적힌 feature(stored)가 지금 설정의 feature 와 같은지. 팔(관절 이름)·카메라·해상도를 본다."""
    def spec(f):
        return f['dtype'], tuple(f['shape']), list(f['names'])
    images = {k for k in stored if k.startswith('observation.images.')}
    return images == {k for k in features if k.startswith('observation.images.')} and all(
        k in stored and spec(stored[k]) == spec(f) for k, f in features.items())


def pick(positions, names):
    """{관절 이름: 값} 에서 names 순서로 값을 뽑는다. 하나라도 없으면 None."""
    if not all(name in positions for name in names):
        return None
    return np.array([positions[name] for name in names], dtype=np.float32)
