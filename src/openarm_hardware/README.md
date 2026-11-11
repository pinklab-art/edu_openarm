# openarm_hardware

`enactic/openarm_ros2` 의 ros2_control 하드웨어 플러그인(`openarm_hardware/OpenArmHW`). `openarm_bringup` 이 팔마다 하나씩 올린다.
활성화 때 실제 관절값을 받은 뒤에 영점 자세로 천천히 이동하고, 관절 토크에 URDF 모델의 중력을 더하는 기능을 넣었다.

## 게인 모드

```bash
ros2 service call /openarm_hw_<left|right>/gains/{default,impedance,zero_gravity} std_srvs/srv/Trigger
```

