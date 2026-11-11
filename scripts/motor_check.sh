#!/usr/bin/env bash
# 팔마다 모터 8개(관절 7 + 그리퍼)의 응답과 상태를 읽는다. 토크는 켜지 않는다.
#   ./scripts/motor_check.sh          # can0(오른팔), can1(왼팔)
#   ./scripts/motor_check.sh can1     # 지정한 것만
# 먼저 ./scripts/can_fd.sh 로 CAN FD 를 올려 둔다.

source "$(dirname "$0")/../install/setup.bash"   # 빌드한 openarm_can 도구

for iface in ${@:-can0 can1}; do
  openarm-can-health "$iface" 1 8   # 인터페이스, 읽는 시간(초), 모터 수
done
