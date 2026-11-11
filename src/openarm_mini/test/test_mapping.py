import math

import pytest

from openarm_mini.mapping import arm_sample, gripper_ticks_to_position, ticks_to_rad

TRAVEL = {'closed': 0.0, 'open': 0.044}


def test_ticks_to_rad_offset_is_zero():
    assert ticks_to_rad(2048, 2048, 1, 4096) == 0.0


def test_ticks_to_rad_quarter_turn_and_sign():
    assert ticks_to_rad(3072, 2048, 1, 4096) == pytest.approx(math.pi / 2)
    assert ticks_to_rad(3072, 2048, -1, 4096) == pytest.approx(-math.pi / 2)


def test_ticks_to_rad_wraps_across_tick_zero():
    # 영점이 tick 30 일 때 4040 은 영점에서 -86 tick, 곧 -7.6 도다(+352 도가 아님).
    assert math.degrees(ticks_to_rad(4040, 30, 1, 4096)) == pytest.approx(-7.56, abs=0.01)


@pytest.mark.parametrize('ticks, expected', [(2727, 0.044), (2047, 0.0), (2387, 0.022),
                                             (3000, 0.044), (1000, 0.0)])
def test_gripper_maps_and_clamps(ticks, expected):
    assert gripper_ticks_to_position(ticks, 2727, 2047, 0.044, 0.0) == pytest.approx(expected)


def test_gripper_reversed_direction():
    # 오른팔처럼 열림 tick 이 닫힘보다 작아도 같은 비율로 대응한다.
    assert gripper_ticks_to_position(1438, 1438, 2103, 0.044, 0.0) == pytest.approx(0.044)
    assert gripper_ticks_to_position(2103, 1438, 2103, 0.044, 0.0) == pytest.approx(0.0)


def test_arm_sample_returns_seven_joints_and_finger():
    arm_cfg = {'signs': [1, -1, 1, 1, 1, 1, 1], 'offset_ticks': [2048] * 8,
               'gripper_ticks': {'open': 2727, 'closed': 2047}}
    joints, gripper = arm_sample(arm_cfg, [2048, 3072] + [2048] * 5 + [2727], 4096, TRAVEL)
    assert len(joints) == 7
    assert joints[1] == pytest.approx(-math.pi / 2)
    assert gripper == pytest.approx(0.044)
