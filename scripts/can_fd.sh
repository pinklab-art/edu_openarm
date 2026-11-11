#!/usr/bin/env bash
# CAN 인터페이스를 CAN FD(1 Mbps / 5 Mbps)로 올린다.
#   ./scripts/can_fd.sh          # can0(오른팔), can1(왼팔)
#   ./scripts/can_fd.sh can1     # 지정한 것만
set -e

for iface in ${@:-can0 can1}; do
  sudo ip link set "$iface" down
  sudo ip link set "$iface" type can bitrate 1000000 dbitrate 5000000 fd on restart-ms 100
  sudo ip link set "$iface" txqueuelen 1000   # 짧으면 송신이 막힌다(ENOBUFS)
  sudo ip link set "$iface" up
done

# 어댑터를 꽂은 뒤 처음 올릴 때 두 번째 채널은 약 1초 뒤에 UP 이 된다.
sleep 2
ip -brief link show type can
