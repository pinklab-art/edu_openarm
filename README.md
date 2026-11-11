# edu_openarm

OpenArm v1 실습 코드. Ubuntu 24.04 · ROS 2 Jazzy 기준.

## 준비물

- OpenArm v1 본체
- CAN FD 어댑터 PEAK-System PCAN-USB Pro FD (드라이버 `peak_usb` 는 Ubuntu 커널에 포함)

## 스크립트

| 스크립트 | 용도 |
| --- | --- |
| `scripts/can_fd.sh` | CAN 인터페이스를 CAN FD(bitrate 1 Mbps, dbitrate 5 Mbps)로 올린다 |

### CAN FD 설정

```bash
./scripts/can_fd.sh          # can0(오른팔), can1(왼팔)
./scripts/can_fd.sh can1     # 지정한 인터페이스만
```

재부팅하면 설정이 풀리므로 부팅할 때마다 다시 실행한다.
