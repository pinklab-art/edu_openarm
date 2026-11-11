# openarm_mini

OpenArm mini 리더암을 손으로 움직이면 OpenArm 이 같은 자세로 따라오는 teleop 패키지.
mini 노드가 팔마다 Feetech STS3215 서보 8개(관절 7 + 그리퍼)의 위치를 읽어 관절각으로 바꾼 뒤
`/safety_filter/command` 로 보내고, 관절 한계·속도 제한은 `openarm_safety` 가 맡는다.

## 세팅

처음 한 번 순서대로 한다.

1. 시리얼 포트 권한을 받는다. 로그아웃했다 다시 로그인해야 적용된다.

   ```bash
   sudo usermod -aG dialout $USER
   ```

2. mini 보드에 고정 이름 `/dev/openarm_mini_left`·`/dev/openarm_mini_right` 를 건다. 안내에 따라 보드를 하나씩 꽂는다.

   ```bash
   ros2 run openarm_mini udev
   ```

3. 서보를 새로 조립했으면 id 를 배정한다. 서보를 하나만 보드에 연결하고 실행한다.
   id 는 mini 관절 번호와 같게(관절 1~7 → id 1~7, 그리퍼 → id 8) 준다.

   ```bash
   ros2 run openarm_mini register --port /dev/openarm_mini_left          # 버스 스캔
   ros2 run openarm_mini register --port /dev/openarm_mini_left --id 3   # 연결된 서보를 id 3 으로
   ```

4. 서보 응답을 확인한다. 서보 8개가 모두 응답하면 관절값이 실시간으로 표시된다.

   ```bash
   ros2 run openarm_mini check
   ```

5. 캘리브레이션한다. mini 를 OpenArm 영점 자세와 같은 자세로 맞추고, 그리퍼를 끝까지 열고 닫으라는 안내를 따른다.
   결과는 `config/mini.yaml` 의 `offset_ticks`·`gripper_ticks` 에 저장된다.

   ```bash
   ros2 run openarm_mini calibrate              # 양팔 차례로
   ros2 run openarm_mini calibrate --arm left   # 한 팔만
   ```

   캘리브레이션 뒤 `check` 로 mini 관절을 움직여 보며 각도 부호가 OpenArm 관절 방향과 맞는지 본다.

## 실행

시뮬레이션이나 실물을 `forward_position_controller` 로 띄운 뒤 다른 터미널에서 teleop 을 띄운다.

```bash
ros2 launch openarm_sim sim.launch.py robot_controller:=forward_position_controller   # 시뮬
ros2 launch openarm_mini teleop.launch.py                                             # 양팔
ros2 launch openarm_mini teleop.launch.py arms:=left                                  # 왼팔만
```

teleop 을 띄우면 OpenArm 이 지금 자세에서 mini 자세까지 천천히 다가간 뒤 실시간으로 따라간다.
mini 보드가 빠지면 OpenArm 은 그 자리에 서고, 다시 꽂으면 지금 자세에서 천천히 다시 따라간다.
보드 포트를 열지 못하면 teleop 전체가 종료되므로 `check` 로 연결을 먼저 확인한다.
