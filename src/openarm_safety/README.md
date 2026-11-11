# openarm_safety

teleop 이나 policy 가 낸 관절 명령을 팔 컨트롤러로 바로 보내지 않고 다듬어 넘기는 안전 필터.
시뮬레이션(`openarm_sim`)이나 실물(`openarm_bringup`)을 `robot_controller:=forward_position_controller` 로 띄운 채
다른 터미널에서 띄운다. 명령은 시뮬과 실물이 같다.

## 실행

```bash
ros2 launch openarm_safety safety_filter.launch.py   # 안전 필터
ros2 launch openarm_safety sliders.launch.py         # 시험 입력 — 양팔 관절 슬라이더
```

## 동작

필터는 `/safety_filter/command`(`sensor_msgs/JointState`)로 받은 목표를 다듬어 `/<arm>_forward_position_controller/commands` 와
그리퍼 action 으로 넘긴다. 입력이 들어오면 팔의 지금 자세에서 출발해 관절당 0.4 rad/s 로 목표까지 간 뒤
2 rad/s 상한으로 따라가고, 목표는 관절 한계 안으로 자른다. 팔이 이미 한계 밖에 있어도 안쪽으로 가는 명령은 통과하고,
입력이 0.3 s 넘게 끊기면 명령을 멈춘다. 한계·속도·그리퍼 값은 `config/safety_filter.yaml` 에서 바꾼다.
