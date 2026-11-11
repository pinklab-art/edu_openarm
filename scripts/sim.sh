#!/usr/bin/env bash
# OpenArm v1 양팔을 MuJoCo 에 띄우고 실물과 같은 컨트롤러를 올린다.
#   ./scripts/sim.sh                                              # 팔 컨트롤러 joint_trajectory_controller
#   ./scripts/sim.sh robot_controller:=forward_position_controller

cd "$(dirname "$0")/.."
source install/setup.bash

ros2 launch openarm_sim sim.launch.py "$@"
