# edu_openarm

OpenArm v1 실습 코드. Ubuntu 24.04 · ROS 2 Jazzy 기준.

## 준비물

- OpenArm v1 본체
- CAN FD 어댑터 PEAK-System PCAN-USB Pro FD (드라이버 `peak_usb` 는 Ubuntu 커널에 포함)
- ROS 2 Jazzy

## 빌드

upstream `enactic/openarm_can` 을 `openarm.repos` 에 고정한 커밋(tag 1.4.1)으로 받아 빌드한다.

```bash
sudo apt install -y ros-dev-tools
sudo rosdep init              # 처음 한 번. 이미 했으면 에러가 나도 넘어간다
rosdep update

cd ~/edu_openarm
vcs import src < openarm.repos
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

`1 package had stderr output: openarm_can` 은 upstream 코드의 경고라 무시해도 된다.

## 스크립트

| 스크립트 | 용도 |
| --- | --- |
| `scripts/can_fd.sh` | CAN 인터페이스를 CAN FD(bitrate 1 Mbps, dbitrate 5 Mbps)로 올린다 |
| `scripts/motor_check.sh` | 팔마다 모터 8개의 응답과 상태를 읽는다(토크는 켜지 않음) |

### CAN FD 설정

```bash
./scripts/can_fd.sh          # can0(오른팔), can1(왼팔)
./scripts/can_fd.sh can1     # 지정한 인터페이스만
```

재부팅하면 설정이 풀리므로 부팅할 때마다 다시 실행한다.

### 모터 검사

```bash
./scripts/motor_check.sh          # can0(오른팔), can1(왼팔)
./scripts/motor_check.sh can1     # 지정한 인터페이스만
```

모터 8개(`0x01`~`0x08`)가 모두 응답하고 `SILENT`·`FAULT` 표시가 없으면 정상이다.
