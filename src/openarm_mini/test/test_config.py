import pytest

from openarm_mini import config

ARMS = {'left': {'port': '/dev/openarm_mini_left'}, 'right': {'port': '/dev/openarm_mini_right'}}
LEFT = {'offset_ticks': [2048] * 8, 'gripper_ticks': {'open': 2727, 'closed': 2047}}


@pytest.fixture
def calibration_path(tmp_path, monkeypatch):
    path = tmp_path / 'openarm_mini' / 'calibration.yaml'
    monkeypatch.setattr(config, 'CALIBRATION_PATH', str(path))
    return path


def fresh_cfg():
    return {'arms': {arm: dict(values) for arm, values in ARMS.items()}}


def test_missing_file_asks_for_calibrate(calibration_path):
    with pytest.raises(config.CalibrationMissing, match='ros2 run openarm_mini calibrate$'):
        config.apply_calibration(fresh_cfg(), ['left', 'right'])


def test_missing_one_arm_names_that_arm(calibration_path):
    config.save_calibration('left', **LEFT)
    with pytest.raises(config.CalibrationMissing, match='calibrate --arm right'):
        config.apply_calibration(fresh_cfg(), ['left', 'right'])


def test_saved_arm_is_merged_and_other_arm_kept(calibration_path):
    config.save_calibration('left', **LEFT)
    config.save_calibration('right', [2000] * 8, {'open': 1438, 'closed': 2103})
    cfg = fresh_cfg()
    config.apply_calibration(cfg, ['left', 'right'])
    assert cfg['arms']['left']['offset_ticks'] == LEFT['offset_ticks']
    assert cfg['arms']['left']['port'] == '/dev/openarm_mini_left'
    assert cfg['arms']['right']['gripper_ticks'] == {'open': 1438, 'closed': 2103}


def test_only_requested_arms_are_checked(calibration_path):
    config.save_calibration('left', **LEFT)
    config.apply_calibration(fresh_cfg(), ['left'])


def test_wrong_tick_count_counts_as_missing(calibration_path):
    config.save_calibration('left', [2048] * 7, LEFT['gripper_ticks'])
    with pytest.raises(config.CalibrationMissing):
        config.apply_calibration(fresh_cfg(), ['left'])
