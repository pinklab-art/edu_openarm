# openarm_lerobot

OpenArm 한 팔(기본 오른팔)로 하는 imitation learning 패키지. mini teleop 으로 시연한 동작을 ROS 노드가 LeRobot 데이터셋으로 기록하고,
`lerobot-train` 으로 ACT policy 를 학습한 뒤, 추론 노드가 policy 의 관절 명령을 `/safety_filter/command` 로 보낸다.
LeRobot 0.7.0 은 데이터셋·학습·policy 라이브러리로만 쓰고, 팔·mini 는 ROS 노드가 맡는다.
카메라는 ROS topic 을 거치지 않고 기록·추론 노드가 직접 연다. 실물 전용이다.

| 단계 | 실행 | 입력 → 출력 |
| --- | --- | --- |
| 기록 | `ros2 run openarm_lerobot record` | `/joint_states`(state), `/safety_filter/command`(action), 카메라 → `~/.cache/huggingface/lerobot/<repo_id>` |
| 학습 | `lerobot-train` | 데이터셋 → `outputs/train/<이름>/checkpoints/last/pretrained_model` |
| 추론 | `ros2 run openarm_lerobot policy <pretrained_model>` | `/joint_states`, 카메라 → `/safety_filter/command` |

## 세팅

처음 한 번 한다.

1. LeRobot 가상환경을 만든다. torch 까지 받으므로 몇 분 걸린다.

   ```bash
   sudo apt install -y python3-venv ffmpeg
   cd ~/edu_openarm
   python3 -m venv .venv_lerobot
   .venv_lerobot/bin/pip install "lerobot[training,viz]==0.7.0"
   ```

2. 카메라 두 대(작업대 위 `top`, 손목 `wrist`)를 노트북에 꽂고 장치마다 사진을 한 장씩 찍어 본다.

   ```bash
   cd ~/edu_openarm
   .venv_lerobot/bin/lerobot-find-cameras opencv
   ```

   `outputs/captured_images/opencv__dev_video<N>.png` 를 열어 어느 번호가 어느 카메라인지 확인하고,
   `config/lerobot.yaml` 의 `cameras` 와 다르면 고친다. 웹캠 하나가 `/dev/video` 를 두 개씩 잡으므로 사진이 나오는 번호를 쓴다.

LeRobot 을 쓰는 `record`·`policy`·`lerobot-train` 은 터미널마다 워크스페이스를 불러온 뒤 가상환경을 켜고 실행한다.

```bash
cd ~/edu_openarm
source install/setup.bash
source .venv_lerobot/bin/activate
```

## 시연 기록

터미널 3개를 띄운다. 1·2 는 가상환경 없이 실행한다.

```bash
ros2 launch openarm_bringup bringup.launch.py robot_controller:=forward_position_controller   # 1 실물
ros2 launch openarm_mini teleop.launch.py arms:=right                                         # 2 mini teleop + 안전 필터
ros2 run openarm_lerobot record                                                              # 3 기록 (가상환경)
```

`record` 를 띄우면 rerun 창에 카메라 2대와 팔 자세(observation)·mini 명령(action)이 뜬다.
카메라는 `record` 가 쥐고 있으므로 기록하는 동안 다른 프로그램으로는 열 수 없고, 영상은 rerun 창에서 본다.
`record` 터미널에서 Enter 로 에피소드를 시작하고, 시연이 끝나면 Enter 로 저장한다. 실수한 에피소드는 `x`+Enter 로 버린다.
`q`+Enter 로 끝내면 데이터셋을 마무리한다. 같은 `repo_id` 로 다시 실행하면 이전 에피소드 뒤에 이어서 기록한다.
데이터셋 이름과 작업 설명은 `--repo-id local/<이름>`, `--task "<설명>"` 으로 바꾼다.

## 학습

```bash
lerobot-train \
  --dataset.repo_id=local/openarm_pick \
  --policy.type=act \
  --policy.device=cuda \
  --policy.push_to_hub=false \
  --steps=30000 \
  --output_dir=outputs/train/act_openarm_pick \
  --job_name=act_openarm_pick
```

카메라 2대·batch 8 에서 GPU 메모리를 4 GB 쯤 쓰고, RTX 5060 Laptop 에서 초당 3.4 step(30000 step 에 약 2.5 시간)이다.

## 추론

시연 기록의 터미널 2 대신 안전 필터만 띄우고, 터미널 3 에서 policy 를 띄운다.

```bash
ros2 launch openarm_safety safety_filter.launch.py                                      # 2 안전 필터
ros2 run openarm_lerobot policy outputs/train/act_openarm_pick/checkpoints/last/pretrained_model   # 3 추론 (가상환경)
```

rerun 창에 카메라 2대와 팔 자세가 뜨고, 실행 중에는 policy 가 낸 명령이 action 으로 함께 그려진다.
Enter 로 실행하면 팔이 지금 자세에서 천천히 policy 의 첫 자세로 간 뒤 따라간다. 다시 Enter 를 치면 명령을 멈추고 팔은 그 자리에 선다.
관절 한계·속도 제한은 안전 필터가 맡는다.

## 설정

팔, 기록 주기, rerun 표시 여부(`display`), 카메라 장치·해상도, 기본 데이터셋 이름·작업 설명, 추론 장치(`cuda`·`cpu`)는 `config/lerobot.yaml` 에서 바꾼다.
기록과 추론은 같은 설정이어야 한다.
