# openarm_bringup

실물 OpenArm v1 양팔을 시뮬레이션(`openarm_sim`)과 같은 컨트롤러로 띄운다. CAN FD 설정·모터 검사·영점 세팅을 마친 뒤
MuJoCo 대신 이 launch 를 띄우면 MoveIt·안전 필터 명령은 시뮬레이션과 같다.

## 실행

```bash
ros2 launch openarm_bringup bringup.launch.py                                                # MoveIt 용 joint_trajectory_controller
ros2 launch openarm_bringup bringup.launch.py robot_controller:=forward_position_controller  # teleop 용 forward_position_controller
```

URDF 가 양팔이라 `can0`·`can1` 이 둘 다 올라와 있어야 한다. 팔마다 모터 8개를 켠 뒤 양팔이 영점 자세까지 관절당 0.4 rad/s 로
이동하고 그리퍼가 닫히므로, 띄우기 전에 팔 주변을 비우고 비상시 전원을 바로 끌 수 있게 한다.
다른 터미널에서 `ros2 control list_controllers` 를 실행해 컨트롤러 5개가 모두 `active` 이면 정상이다.
끝낼 때는 팔을 `home` 으로 보낸 뒤 bringup 을 `Ctrl+C` 로 끄고 전원을 내린다. 전원이 꺼지면 모터 힘이 빠져 팔이 중력으로 떨어진다.

## 설정

팔마다 쓰는 CAN 인터페이스와 양팔 공통 중력보상 사용 여부는 `config/hardware.yaml` 에서 바꾼다.
