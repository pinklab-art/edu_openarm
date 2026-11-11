"""안전 필터의 계산 — ROS 없이 숫자만 다룬다."""


def clamp(value, lower, upper):
    """value 를 [lower, upper] 안으로 자른다."""
    return min(max(value, lower), upper)


def step_toward(current, target, max_step):
    """current 에서 target 쪽으로 최대 max_step 만큼만 움직인 값."""
    return current + clamp(target - current, -max_step, max_step)


def limit_joints(output, target, limits, max_step):
    """관절마다 목표를 한계 안으로 자르고, 이번 주기에 max_step 만큼만 다가간다.

    출발점(output)이 한계 밖이어도 목표는 한계 안이므로 팔은 안쪽으로 돌아온다.
    한계 밖으로 더 나가는 명령은 목표가 잘려 있어 만들어지지 않는다.
    """
    return [step_toward(out, clamp(goal, low, high), max_step)
            for out, goal, (low, high) in zip(output, target, limits)]


def low_pass(previous, value, alpha):
    """1차 low-pass. alpha 가 1 이면 value 그대로, 0 에 가까울수록 느리게 따라간다."""
    return previous + alpha * (value - previous)
