from openarm_lerobot.features import dataset_features, feature_names, pick, ros_joint_names, same_features

CFG = {'arm': 'right', 'cameras': {'top': '/dev/video0', 'wrist': '/dev/video2'},
       'image_width': 4, 'image_height': 2}


def test_names_line_up():
    assert ros_joint_names('right')[0] == 'openarm_right_joint1'
    assert ros_joint_names('right')[-1] == 'openarm_right_finger_joint1'
    assert feature_names('right')[-1] == 'right_gripper.pos'
    assert len(ros_joint_names('left')) == len(feature_names('left')) == 8


def test_dataset_features():
    features = dataset_features(CFG)
    assert features['action']['shape'] == (8,)
    assert features['observation.images.wrist']['shape'] == (2, 4, 3)
    assert set(features) == {'observation.state', 'action',
                             'observation.images.top', 'observation.images.wrist'}


def test_pick_keeps_order_and_rejects_missing():
    names = ros_joint_names('right')
    positions = {name: float(i) for i, name in enumerate(reversed(names))}
    assert list(pick(positions, names)) == list(range(7, -1, -1))
    del positions[names[3]]
    assert pick(positions, names) is None


def test_same_features_catches_arm_and_camera_changes():
    stored = {k: {**f, 'shape': list(f['shape'])} for k, f in dataset_features(CFG).items()}
    stored['timestamp'] = {'dtype': 'float32', 'shape': [1], 'names': None}
    assert same_features(stored, dataset_features(CFG))
    assert not same_features(stored, dataset_features({**CFG, 'arm': 'left'}))
    assert not same_features(stored, dataset_features({**CFG, 'image_width': 8}))
    assert not same_features(stored, dataset_features({**CFG, 'cameras': {'top': '/dev/video0'}}))
