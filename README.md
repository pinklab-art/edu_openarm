# edu_openarm

OpenArm v1 실습 코드. Ubuntu 24.04 · ROS 2 Jazzy 기준.

## 준비물

- OpenArm v1 본체
- CAN FD 어댑터 PEAK-System PCAN-USB Pro FD (드라이버 `peak_usb` 는 Ubuntu 커널에 포함)
- ROS 2 Jazzy

## 빌드

`src/openarm_can` 은 `enactic/openarm_can` 1.4.1 소스다. 자동 영점 도구(`setup/openarm-can-zero-position-calibration`)만
위치값 wrap 안전장치를 넣고 기본 `--robot-version` 을 `v1` 로 바꿨다.
`src/openarm_description` 은 `enactic/openarm_description` 에서 v1 URDF 와 mesh 만 남긴 것이고,
`src/openarm_sim/mjcf` 는 `enactic/openarm_mujoco` 의 v1 양팔 MJCF 다.
두 패키지 모두 gripper finger 를 실물과 같은 soft finger(fin ray)와 `arx5_mounter` 로 바꿨고, TCP 는 finger 끝에서 11 mm 안쪽이다.

```bash
sudo apt install -y ros-dev-tools
sudo rosdep init              # 처음 한 번. 이미 했으면 에러가 나도 넘어간다
rosdep update

cd ~/edu_openarm
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

`1 package had stderr output: openarm_can` 은 upstream 코드의 경고라 무시해도 된다.

## 스크립트

| 스크립트 | 용도 |
| --- | --- |
| `scripts/sim.sh` | 양팔을 MuJoCo 에 띄우고 실물과 같은 컨트롤러를 올린다 |
| `scripts/can_fd.sh` | CAN 인터페이스를 CAN FD(bitrate 1 Mbps, dbitrate 5 Mbps)로 올린다 |
| `scripts/motor_check.sh` | 팔마다 모터 8개의 응답과 상태를 읽는다(토크는 켜지 않음) |
| `scripts/zero_manual.sh` | 손으로 맞춘 지금 자세를 모터 8개의 영점으로 기록한다(토크는 켜지 않음) |
| `scripts/zero_auto.sh` | 관절마다 하드스톱을 찾아 영점을 잡는다(모터가 스스로 움직임) |

### MuJoCo 시뮬레이션

```bash
./scripts/sim.sh                                                # MoveIt 용 joint_trajectory_controller
./scripts/sim.sh robot_controller:=forward_position_controller  # teleop 용 forward_position_controller
```

MuJoCo 창에 양팔이 뜨고 관절 이름·명령 인터페이스(position)는 실물과 같다.
다른 터미널에서 `ros2 control list_controllers` 를 실행해 컨트롤러 5개(`joint_state_broadcaster`, 팔 2개, 그리퍼 2개)가 모두 `active` 이면 정상이다.
`Could not enable FIFO RT scheduling policy` 경고는 실시간 스케줄링 권한이 없다는 뜻이라 시뮬에서는 무시해도 된다.

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

### 영점 세팅 — 수동

수동 영점을 먼저 하고, 필요하면 전원을 껐다 켠 뒤 자동 영점으로 다시 잡는다. 수동을 먼저 하면 위치값이 0 근처에서 시작해 자동 영점 도중 값이 튀는 문제를 피한다.

1. 팔을 손으로 영점 자세에 맞춘다.
2. 영점을 기록한다.

   ```bash
   ./scripts/zero_manual.sh          # can0(오른팔), can1(왼팔)
   ./scripts/zero_manual.sh can1     # 지정한 인터페이스만
   ```

3. `./scripts/motor_check.sh` 로 모터 8개의 `pos` 가 0 근처인지 확인한다.

### 영점 세팅 — 자동

모터를 켜고 관절을 하나씩 하드스톱까지 밀어 기준을 잡은 뒤, 영점 자세로 돌아와 기록한다.
Python 바인딩이 필요하므로 처음 한 번 가상환경을 만든다.

```bash
sudo apt install -y python3-venv python3-dev
cd ~/edu_openarm
source install/setup.bash
python3 -m venv .venv
.venv/bin/pip install numpy ./src/openarm_can/python
```

팔 주변을 비우고, 비상시 전원을 바로 끌 수 있게 한 뒤 팔마다 한 번씩 실행한다.

```bash
./scripts/zero_auto.sh right_arm   # can0
./scripts/zero_auto.sh left_arm    # can1
```

영점을 기록한 직후(수동·자동 모두)에는 자동 영점을 바로 돌리지 않는다. 전원을 껐다 켜고 팔을 영점 자세로 돌려 둔 뒤 팔마다 한 번 실행한다.
실행 중 위치값이 한 주기에 크게 튀면 모터를 끄고 `[SAFETY ABORT]` 를 출력하며 멈춘다.
