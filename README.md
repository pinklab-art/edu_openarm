# edu_openarm

OpenArm v1 실습 코드. Ubuntu 24.04 · ROS 2 Jazzy 기준.

설치·실물 준비·실행·문제 해결은 [wiki](https://github.com/pinklab-art/edu_openarm/wiki) 에 있다.

## 빌드

```bash
git clone https://github.com/pinklab-art/edu_openarm.git ~/edu_openarm
sudo apt install -y ros-dev-tools
sudo rosdep init              # 처음 한 번. 이미 했으면 에러가 나도 넘어간다
rosdep update

cd ~/edu_openarm
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

ROS discovery 범위 설정과 가상환경은 wiki 의 [설치 및 빌드](https://github.com/pinklab-art/edu_openarm/wiki/설치-및-빌드)를 따른다.

## 패키지

| 패키지 | 내용 |
| --- | --- |
| [openarm_can](src/openarm_can/README.md) | `enactic/openarm_can` 1.4.1. 자동 영점 도구에 위치값 wrap 안전장치를 넣고 기본 `--robot-version` 을 `v1` 로 바꿈 |
| [openarm_description](src/openarm_description/README.md) | `enactic/openarm_description` 의 v1 URDF·mesh. gripper finger 를 soft finger(fin ray)와 `arx5_mounter` 로 바꿈, TCP 는 finger 끝에서 11 mm 안쪽 |
| [openarm_hardware](src/openarm_hardware/README.md) | `enactic/openarm_ros2` 의 ros2_control 하드웨어 플러그인. 활성화 때 영점 자세로 천천히 이동, 중력보상 추가 |
| openarm_sim | MuJoCo 시뮬레이션 |
| openarm_bringup | 실물 실행 |
| openarm_moveit | MoveIt 설정과 예제 |
| openarm_safety | teleop·policy 명령의 안전 필터 |
| openarm_mini | OpenArm mini 리더암 teleop |
| openarm_lerobot | 한 팔 imitation learning — ROS 로 시연 기록, LeRobot 0.7.0 으로 ACT 학습, policy 추론 |
