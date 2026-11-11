from openarm_safety.filter import clamp, limit_joints, low_pass, step_toward


def test_step_toward_caps_the_move():
    assert step_toward(0.0, 1.0, 0.1) == 0.1
    assert step_toward(0.0, -1.0, 0.1) == -0.1
    assert step_toward(0.0, 0.05, 0.1) == 0.05


def test_target_outside_limit_is_clamped():
    out = limit_joints([0.1], [-0.5], [(0.0, 2.0)], 1.0)
    assert out == [0.0]


def test_arm_outside_limit_moves_back_inside():
    # 하한 0 인 관절이 -0.05 에 있어도 안쪽 목표로는 움직인다.
    out = limit_joints([-0.05], [0.5], [(0.0, 2.0)], 0.01)
    assert out[0] > -0.05


def test_arm_outside_limit_does_not_go_further_out():
    out = limit_joints([-0.05], [-1.0], [(0.0, 2.0)], 0.01)
    assert out[0] >= -0.05


def test_low_pass():
    assert low_pass(0.0, 1.0, 0.25) == 0.25
    assert clamp(5.0, 0.0, 1.0) == 1.0
