"""리더 서보 tick → 팔로워 관절값 변환."""

import math

ARM_DOF = 7


def ticks_to_rad(ticks, offset_ticks, sign, ticks_per_rev):
    """서보 tick 을 관절각 [rad] 으로 바꾼다. offset 이 관절 영점이다.

    tick 은 한 바퀴마다 0 으로 돌아오므로, 영점과의 차이를 ±반 바퀴 안으로 감싼다.
    mini 관절은 영점 자세에서 ±180° 안에서만 움직이므로 이 값이 늘 실제 각도다.
    """
    half = ticks_per_rev // 2
    diff = (ticks - offset_ticks + half) % ticks_per_rev - half
    return sign * diff * (2.0 * math.pi / ticks_per_rev)


def gripper_ticks_to_position(ticks, open_ticks, closed_ticks, open_value, closed_value):
    """리더 그리퍼 tick 을 팔로워 finger 위치 [m] 로 선형 대응시킨다."""
    span = open_ticks - closed_ticks
    ratio = 0.0 if span == 0 else min(max((ticks - closed_ticks) / span, 0.0), 1.0)
    return closed_value + ratio * (open_value - closed_value)


def arm_sample(arm_cfg, ticks, ticks_per_rev, travel):
    """한 팔의 tick 8개 → (관절 7개 [rad], finger [m])."""
    joints = [ticks_to_rad(ticks[i], arm_cfg['offset_ticks'][i], arm_cfg['signs'][i], ticks_per_rev)
              for i in range(ARM_DOF)]
    gripper = gripper_ticks_to_position(
        ticks[ARM_DOF], arm_cfg['gripper_ticks']['open'], arm_cfg['gripper_ticks']['closed'],
        travel['open'], travel['closed'])
    return joints, gripper
