# openarm_sim

OpenArm v1 양팔을 MuJoCo 에 띄우고 실물과 같은 ros2_control 컨트롤러를 올린다.
`mjcf/` 는 `enactic/openarm_mujoco` 의 v1 양팔 MJCF 이고, gripper finger 를 실물과 같은 soft finger(fin ray)와
`arx5_mounter` 로 바꿨다.

## 실행

```bash
ros2 launch openarm_sim sim.launch.py                                                # MoveIt 용 joint_trajectory_controller
ros2 launch openarm_sim sim.launch.py robot_controller:=forward_position_controller  # teleop 용 forward_position_controller
```

MuJoCo 창에 양팔이 뜨고 관절 이름·명령 인터페이스(position)는 실물과 같다.
다른 터미널에서 `ros2 control list_controllers` 를 실행해 컨트롤러 5개(`joint_state_broadcaster`, 팔 2개, 그리퍼 2개)가 모두 `active` 이면 정상이다.
`Could not enable FIFO RT scheduling policy` 경고는 실시간 스케줄링 권한이 없다는 뜻이라 시뮬에서는 무시해도 된다.
