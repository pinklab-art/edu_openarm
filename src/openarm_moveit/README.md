# openarm_moveit

OpenArm v1 MoveIt 설정과 Python 예제. 시뮬레이션(`openarm_sim`)이나 실물(`openarm_bringup`)을
joint_trajectory_controller 로 띄운 채 다른 터미널에서 MoveIt 을 띄운다. 명령은 시뮬과 실물이 같다.

## 실행

```bash
ros2 launch openarm_moveit moveit.launch.py                # RViz 에서 Plan & Execute, 예제 ex01~ex03
ros2 launch openarm_moveit moveit.launch.py servo:=left    # MoveIt Servo 를 더해 예제 ex04
```

`You can start planning now!` 가 나오면 준비된 것이다. `No 3D sensor plugin(s) defined for octomap updates` 는
깊이 카메라를 쓰지 않는다는 뜻이라 무시해도 된다.

## 예제

| 예제 | 내용 | 실행 |
| --- | --- | --- |
| ex01 | 관절 하나씩 움직이기 (joint goal) | `ros2 run openarm_moveit ex01_joint_goal` |
| ex02 | 손끝 자세 지령 (pose goal) | `ros2 run openarm_moveit ex02_pose_goal` |
| ex03 | 손끝 직선 경로 (Cartesian path) | `ros2 run openarm_moveit ex03_cartesian_path` |
| ex04 | 키보드 teleop (MoveIt Servo) | `ros2 run openarm_moveit ex04_keyboard_servo` |

기본은 왼팔이고, 오른팔은 뒤에 `--ros-args -p arm:=right` 를 붙인다(ex04 의 오른팔은 MoveIt 도 `servo:=right` 로 띄운다).
ex02·ex03 은 단계마다 멈춰 기다리므로, 또 다른 터미널에서 다음 단계 신호를 보낸다.

```bash
ros2 topic pub --once /next_step std_msgs/msg/Empty '{}'
```
