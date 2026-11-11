#!/usr/bin/env bash
# 지금 자세를 모터 8개의 영점으로 기록한다. 토크는 켜지 않는다.
#   ./scripts/zero_manual.sh          # can0(오른팔), can1(왼팔)
#   ./scripts/zero_manual.sh can1     # 지정한 것만
# 먼저 팔을 손으로 영점 자세에 맞춰 둔다.

source "$(dirname "$0")/../install/setup.bash"   # 빌드한 openarm_can 도구

for iface in ${@:-can0 can1}; do
  openarm-can-cli -i "$iface" set_zero   # 모터 ID 1~8
done
