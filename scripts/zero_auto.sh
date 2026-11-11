#!/usr/bin/env bash
# 관절마다 하드스톱을 찾아 영점을 잡는다. 모터가 스스로 움직인다.
#   ./scripts/zero_auto.sh right_arm   # can0
#   ./scripts/zero_auto.sh left_arm    # can1
# 팔마다 한 번만 실행한다. 먼저 .venv 에 Python 바인딩을 설치해 둔다.

cd "$(dirname "$0")/.."
source install/setup.bash   # 빌드한 openarm_can 도구

.venv/bin/python "$(command -v openarm-can-zero-position-calibration)" --arm-side "$1"
