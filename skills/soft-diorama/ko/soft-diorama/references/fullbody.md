# 전신 인물과 손 (paintkit.figure)

성인 전신 인물을 관절 각도로 포즈를 잡아 그린다. 여성과 남성 체형을 같은 리그로 그리고, 몸을 한 바퀴 돌려 정면, 3/4, 옆모습, 뒷모습을 그리며, 앉은 자세도 만든다. 몸은 여러 부위(몸통, 목, 다리, 발, 팔, 손)를 하나의 피부로 이어 칠한다. 전신을 한 번 만들면 `framing()`으로 상반신이나 얼굴까지 잘라 쓴다.

```python
from paintkit.figure import ILLUSTRATION, Figure, HairSpec, HandSpec, Physique, Pose, aim, draw_figure, framing
from paintkit.figure import wardrobe

figure = Figure(pelvis=(500, 760), height=1270, pose=Pose(hip_tilt=7, shoulder_tilt=-5))
masks = draw_figure(cv, figure, garments=[wardrobe.dress('#b0344a')])

man = Figure(**framing(cv.size, 'waist'), sex='male', pose=Pose(turn=-25, head_yaw=-20))
```

## 목차

1. 범위
2. 좌표와 각도
3. Figure
4. Pose
5. Physique와 몸의 곡선
6. 몸 돌리기 (turn): 정면, 옆모습, 뒷모습
7. 앉은 자세와 단축 (aim)
8. 줌 (framing)
9. 남성
10. 포즈 조리법과 포즈 프리셋 (poses)
11. 의상 (wardrobe)
12. 인체화(누드)
13. 손
14. 돌려받는 값
15. 배경 속에 세우기와 구도 (fit, thirds, group)
16. 헤어스타일 (hairstyles)
17. 얼굴 스타일과 표정 (expressions)
18. 한계

## 1. 범위

- 체형은 성인 약 8등신 비례로 고정되어 있다
- `sex='female'`(기본)과 `sex='male'` 두 체형
- 몸을 한 바퀴 돌린다 (`Pose.turn`, -180..180). 90은 화면 오른쪽을 향한 옆모습, 180은 뒷모습. 고개는 `head_yaw`로 따로 돌린다
- 서 있는 자세, 앉은 자세(`aim()`으로 허벅지를 앞으로), 위에서 내려다본 누운 자세(`roll`)
- 화풍은 `ILLUSTRATION`처럼 부드러운 look에서 가장 자연스럽다 (연속적인 부피 음영). `ANIME`는 셀 음영으로 칠한다

## 2. 좌표와 각도

- 길이 단위는 머리 단위(머리 높이의 절반). `figure.unit` = `height / 16.1` px
- 좌우는 항상 화면 기준이다. `left_arm`은 몸이 정면을 볼 때 화면 왼쪽에 보이는 팔
- 각도는 화면 기준 도(degree). 0은 아래, 양수는 화면 오른쪽, 음수는 화면 왼쪽, 180은 위

| 각도 | 방향 |
|---|---|
| 0 | 아래 |
| 90 | 화면 오른쪽 |
| -90 | 화면 왼쪽 |
| 150 | 오른쪽 위 |
| -150 | 왼쪽 위 |

- 주요 높이 (정수리 0 기준, 머리 단위): 턱 2.0, 어깨 3.0, 가슴 4.1, 허리 5.6, 골반 중심 7.6, 무릎 11.5, 발목 15.3, 발바닥 16.1

## 3. Figure

| 인자 | 의미 |
|---|---|
| `pelvis` | 골반 중심(고관절 선의 가운데) px. 똑바로 선 인물의 발바닥은 `pelvis.y + 0.53 * height` |
| `height` | 정수리에서 발바닥까지 px (똑바로 섰을 때) |
| `pose` | `Pose` |
| `physique` | `Physique` |
| `sex` | `'female'` 또는 `'male'`. 체형 표, 얼굴, 머리 기본값이 바뀐다 |
| `face`, `hair` | 상반신 리그와 같은 `FaceSpec`, `HairSpec`. None이면 성별 기본값 (`FEMALE_FACE`와 긴 머리, `MALE_FACE`와 `MALE_HAIR`) |
| `look` | 기본 `ILLUSTRATION` |
| `jaw` | 얼굴 아래쪽 폭 배율. None이면 여성 0.93, 남성 1.06 |
| `nude_details` | 유두, 배꼽, 몸의 주름과 근육 표시. 옷으로 전부 덮을 때는 False |

## 4. Pose

| 인자 | 기본값 | 의미 |
|---|---|---|
| `turn` | 0 | 몸 전체를 세로축으로 돌린다. -180..180. 양수면 몸 앞면이 화면 오른쪽을 향한다. 90 옆모습, 180 뒷모습 |
| `lean` | 0 | 척추 기울기. 양수면 상체가 화면 오른쪽으로 |
| `hip_tilt` | 0 | 양수면 화면 오른쪽 골반이 내려감 |
| `shoulder_tilt` | 0 | 양수면 화면 오른쪽 어깨가 내려감 |
| `left_arm`, `right_arm` | (-6,-1), (6,1) | (위팔, 아래팔) 각도. 4개 값이면 (위팔 각도, 아래팔 각도, 위팔 길이 비율, 아래팔 길이 비율) |
| `left_leg`, `right_leg` | (2.5,1), (-2.5,-1) | (허벅지, 정강이) 각도. 4개 값이면 길이 비율까지 |
| `left_hand`, `right_hand` | `HandSpec()` | 손 모양. 손끝은 아래팔 방향을 따른다. 손바닥 방향은 `view`로 정한다 (13절) |
| `left_foot`, `right_foot` | -0.12, 0.12 | 0은 발끝이 정면, -1은 화면 왼쪽을 향한 옆모습, +1은 오른쪽. 몸을 돌리면 발도 따라 돈다 |
| `front_leg` | None | 두 다리가 겹칠 때 앞에 오는 다리. None이면 몸을 돌린 쪽에서 가까운 다리 (정면이면 `'right'`) |
| `head_yaw`, `head_tilt` | 0 | 고개 회전, 기울임 |
| `neck` | 0 | 목의 기울기 |
| `roll` | 0 | 몸통 전체 회전. 90이면 머리가 화면 오른쪽인 누운 자세 |

팔다리 각도는 `roll`, `turn`과 무관한 화면 기준 절대 각도다. 몸을 크게 돌릴 때는 `aim()`으로 몸 기준 방향을 주면 어느 각도에서도 같은 자세가 유지된다 (6절).

## 5. Physique와 몸의 곡선

| 인자 | 의미 |
|---|---|
| `bust` | 가슴 크기 배율 (남성은 가슴근육 크기) |
| `waist`, `hips`, `shoulders` | 폭 배율. `hips`는 허벅지 굵기에도 반영된다 |
| `limbs` | 팔다리 굵기 |
| `gloss` | 빛 쪽 가장자리의 은은한 윤기 (0-1) |

여성 굴곡을 강조하려면 `Physique(bust=1.15, waist=0.93, hips=1.10)` 정도에서 시작한다. 남성 근육질은 `Physique(shoulders=1.05, limbs=1.08)`. 1.25를 넘기면 형태가 어색해진다.

몸의 곡선은 아래 구조로 만든다. 체형을 바꿀 때는 `Physique` 배율을 먼저 쓰고, 표는 형태 자체가 어색할 때만 고친다.

- 팔다리는 바깥쪽과 안쪽 윤곽을 따로 정한다 (`fullbody.py`의 `_ARM_OUTER`, `_ARM_INNER`, `_LEG_OUTER`, `_LEG_INNER`, 남성은 `_MALE_` 접두어)
    + 허벅지: 바깥쪽은 엉덩이에서 완만하게 내려오고 안쪽은 사타구니 아래에서 빨리 좁아진다
    + 종아리: 바깥쪽 볼록함이 안쪽보다 조금 높다
    + 팔: 위팔 바깥의 어깨 근육, 아래팔 위쪽의 볼록함
    + 표의 값은 `(t, 반폭)`, 단위는 머리 단위. t는 관절에서 관절까지 0-1
- 무릎과 팔꿈치는 `Canvas.contour`의 `bend`로 둥글린다 (`_JOINT_BEND`)
- 몸통은 가슴-허리-골반 윤곽(`_CHEST_SIDE`, `_PELVIS_SIDE`)을 이은 뒤 허리를 한 번 부드럽게 다듬고(`_WAIST_SMOOTHING`) 엉덩이 옆에 타원 덩어리(`_HIP_CAP`)를 더한다. 골반을 기울여도 허리가 꺾이지 않는다
- 각 윤곽점에는 앞뒤 깊이(`_CHEST_DEPTH`, `_PELVIS_DEPTH`)가 있다. 몸을 돌리면 이 깊이로 옆 실루엣이 정해진다
- 피부 음영은 부위별 둥글림과 몸 전체의 넓은 둥글림(`broad_bulge`)을 섞는다. 다리는 발까지 한 덩어리로 음영을 계산해 발목이 공처럼 보이지 않는다

## 6. 몸 돌리기 (turn): 정면, 옆모습, 뒷모습

```python
three_quarter = Pose(turn=35, head_yaw=28, hip_tilt=5, shoulder_tilt=-3)
```

- 몸통의 각 높이를 단면(반폭, 앞 깊이, 뒤 깊이)으로 보고 돌린 실루엣을 계산한다
    + 몸이 향한 쪽 실루엣에 가슴과 배의 옆선이, 반대쪽에 등과 엉덩이가 드러난다
    + 먼 쪽 가슴은 위쪽 비탈이 가슴벽에서 이어지는 옆모습이 된다
- 배꼽, 쇄골, 복부 중심선, 유두는 몸 표면 위의 점이라서 함께 돈다 (`skeleton.chest.surface(x, y)`)
- 먼 쪽 팔은 몸통과 가슴 뒤로 숨는다. 먼 쪽 다리는 가까운 다리 뒤에 그려진다
- 고개는 몸보다 덜 돌리는 편이 자연스럽다: 3/4까지는 `head_yaw = turn * 0.6-0.8`, 옆모습과 뒷모습은 `head_yaw = turn`
- 옆모습(90): 몸 앞뒤 깊이로 가슴, 배, 등, 엉덩이 옆선이 생기고 다리는 옆에서 본 윤곽(앞은 허벅지와 무릎, 뒤는 종아리)으로 바뀐다. 얼굴은 코, 입술, 턱이 윤곽 밖으로 나온 옆얼굴, 눈은 가까운 쪽 하나만 보인다. 가까운 팔의 소매는 따로 그려진다
- 뒷모습(180 근처): 가슴과 얼굴은 숨고(몸 윤곽 밖으로 나온 부분만 보인다), 긴 머리는 등 앞에 그려진다. 발은 뒤꿈치 모양이 된다
- 몸을 크게 돌릴 때는 팔을 `aim()`으로 준다. 화면 각도로 준 팔은 뒷모습에서 몸 가운데로 모인다

```python
turn = 180
back = Pose(turn=turn, head_yaw=turn,
            left_arm=aim(turn, (-0.15, 1.0, 0.02), (-0.05, 1.0, 0.08)),     # 몸 기준으로 살짝 바깥
            right_arm=aim(turn, (0.15, 1.0, 0.02), (0.05, 1.0, 0.08)),
            left_hand=HandSpec('relaxed', 'rest'), right_hand=HandSpec('relaxed', 'rest'))   # 손도 몸을 따라 돈다
```

- 8방향 턴어라운드 시트: `scripts/examples/figure_turnaround.py [out] [female|male] [clothed|nude] [around|front]`
- 뒷모습 장면 예시: `scripts/examples/figure_back_view.py`

## 7. 앉은 자세와 단축 (aim)

화면 각도만으로는 관객 쪽으로 뻗은 허벅지를 표현할 수 없다. `aim(turn, upper, lower)`은 몸 기준 3D 방향을 화면 각도와 길이 비율로 바꾼다.

- 방향 벡터는 몸 기준 (x 화면 오른쪽, y 아래, z 몸 앞쪽)
- 반환값은 `(위 각도, 아래 각도, 위 길이 비율, 아래 길이 비율)`. Pose의 팔다리에 그대로 넣는다
- 반환값은 각 분절이 관객 쪽으로 나온 정도(`.forward`)도 함께 지닌다. 먼 쪽 팔의 손목이 어깨보다 1.6 머리 단위 넘게 앞으로 나오면(팔짱, 무릎 안기, 컵 들기) 아래팔과 손을 몸 앞에 그린다. 화면 각도로 직접 준 팔은 이 정보가 없어 먼 팔이 몸 뒤에 숨는다

```python
turn = 30
seated = Pose(turn=turn, lean=4, head_yaw=turn * 0.8,
              left_leg=aim(turn, (0.04, 0.12, 1.0), (0.0, 1.0, 0.12)),      # 허벅지는 앞으로, 정강이는 아래로
              right_leg=aim(turn, (0.20, 0.12, 1.0), (0.04, 1.0, 0.08)),
              left_arm=aim(turn, (0.08, 1.0, 0.30), (0.05, 0.75, 1.0)),     # 손은 허벅지 위에
              right_arm=aim(turn, (-0.08, 1.0, 0.30), (-0.05, 0.75, 1.0)),
              left_hand=HandSpec('relaxed', 'back'), right_hand=HandSpec('relaxed', 'back'))
seat_y = pelvis_y + 0.80 * figure.unit                   # 의자 윗면 높이
```

- 허벅지가 수직에서 50도 넘게 벌어지면 앉은 자세로 보고 엉덩이와 허벅지 뿌리를 한 덩어리로 감싼다. 의자 면에 닿는 아랫선이 매끈해진다
- 앉은 자세는 몸을 20-40도 돌렸을 때 가장 잘 읽힌다. 정면(turn 0)에서는 허벅지가 관객을 향해 거의 사라진다
- 의자는 인물보다 먼저 그린다
- 바닥에 무릎을 세우고 앉는 자세는 `poses.sit_floor(knees_up=True)`. 엉덩이와 발이 같은 바닥 높이에 놓인다
- 전체 예시는 `scripts/examples/couple_bench.py`

## 8. 줌 (framing)

전신 리그 하나로 전신, 무릎 위, 허리 위, 상반신, 얼굴 클로즈업을 모두 만든다. 프레임 아래는 캔버스 밖으로 나갈 뿐 몸 전체가 그대로 계산된다.

```python
figure = Figure(**framing(cv.size, 'bust', center=0.5), pose=pose, sex='female', nude_details=False)
```

| shot | 화면 아래 끝 |
|---|---|
| `full` | 발바닥 아래 여백 |
| `knee` | 무릎 아래 |
| `thigh` | 허벅지 중간 |
| `waist` | 골반 아래 |
| `bust` | 가슴 아래 |
| `face` | 턱 아래 |

- `center`: 몸의 가로 위치 (0-1). `headroom`: 정수리 위 여백 (머리 단위, 기본 0.55)
- 선 자세 기준이다. 앉은 인물은 `pelvis`와 `height`를 직접 정한다
- 클로즈업일수록 선과 음영 굵기가 자동으로 커진다 (look의 `scale`이 머리 크기를 따른다)
- 전체 예시는 `scripts/examples/figure_zoom.py`

## 9. 남성

```python
man = Figure(pelvis=(500, 760), height=1330, sex='male', pose=Pose(turn=-30, head_yaw=-24))
```

- 체형: 넓은 어깨와 흉곽, 곧은 허리, 좁은 골반, 굵은 목과 팔다리. 가슴은 가슴근육(대흉근)으로 그린다
- 얼굴 `MALE_FACE`: 작은 눈(`eye_half_height` 0.074), 옅은 속눈썹(`lashes` 0.4), 굵고 낮은 눈썹(`brow_weight` 1.7, `brow_lift` -0.3), 얇은 입술, 볼 홍조 없음, 넓은 턱(`jaw` 1.06)
- 머리 `MALE_HAIR`: 짧은 머리(`length` 0.62), 옆으로 넘긴 짧은 앞머리(`bangs='short'`), 귀가 드러나고 구레나룻이 있다
- 목에 울대뼈를 그린다
- 수정할 때는 프리셋을 바꿔 넘긴다: `face=replace(MALE_FACE, eye_color='#5a4a3a')`, `hair=replace(MALE_HAIR, color='#6b4a3a')`
- 남성 헤어 12종은 16절, 남성 얼굴 스타일 4종과 표정은 17절
- 성별 표와 프리셋은 `fullbody.py`의 `_BUILDS`, `MALE_FACE`, `MALE_HAIR`

## 10. 포즈 조리법과 포즈 프리셋 (poses)

콘트라포스토(한쪽 다리에 체중)가 서 있는 인물을 살아 보이게 하는 기본이다. 골반과 어깨를 반대로 기울이고 척추를 살짝 눕힌다.

```python
# 체중은 화면 왼쪽 다리, 오른쪽 다리는 힘을 빼고 앞으로
contrapposto = Pose(lean=-4, hip_tilt=9, shoulder_tilt=-7, head_tilt=7, head_yaw=-16,
                    left_leg=(2, 0), right_leg=(-10, 5), front_leg='right', right_foot=0.55)

# 한 손은 골반에: 위팔을 바깥으로 벌리고 아래팔을 몸 쪽으로 꺾는다
hand_on_hip = dict(left_arm=(-30, 48), left_hand=HandSpec('relaxed', 'back'))

# 한 팔은 머리 뒤로: 위팔을 위로, 아래팔을 머리 쪽으로. 손은 머리와 머리카락에 가려진다
arm_behind_head = dict(right_arm=(150, -78), right_hand=HandSpec('relaxed', 'palm'))

pose = replace(contrapposto, **hand_on_hip, **arm_behind_head)     # dataclasses.replace

# 3/4 각도의 남성 콘트라포스토: 빛 쪽으로 몸을 돌리고 한 손은 허리에
male_study = Pose(turn=-32, head_yaw=-26, lean=3, hip_tilt=-6, shoulder_tilt=5,
                  left_leg=(6, -2), right_leg=(8, 6), right_arm=(38, -55))

# 위에서 본 누운 자세 (가로 캔버스)
lying = Pose(roll=78, lean=8, left_leg=(-86, -72), right_leg=(-70, -100), left_arm=(40, 100),
             right_arm=(20, -60), head_tilt=-22, left_foot=-0.9, right_foot=-0.9)
```

- 골반이 올라간 쪽 다리가 체중을 받는다. 그 다리는 곧게, 반대쪽은 무릎을 굽힌다

포즈 프리셋은 `paintkit.figure.poses`에 있다. 모두 `aim()`으로 만들어 몸을 어느 각도로 돌려도 자세가 유지된다. 함수마다 `turn`을 받고 나머지 Pose 필드를 키워드로 덮어쓴다.

| 계열 | 함수 | 내용 |
|---|---|---|
| 서기 | `contrapposto(turn=20)` | 한쪽 다리에 체중, 팔은 늘어뜨림 |
| 서기 | `arms_crossed(turn=15)` | 가슴 앞 팔짱 |
| 서기 | `hands_on_hips(turn=10)` | 팔꿈치를 벌려 허리에 손 |
| 서기 | `hands_in_pockets(turn=15, pouch=False)` | 바지 앞주머니에 손. 팔은 역운동학으로 주머니까지 뻗는다. `pouch=True`면 후드티 캥거루 주머니에 손 |
| 서기 | `stretch(turn=0)` | 두 팔을 머리 위로 뻗은 기지개 |
| 움직임 | `walk(turn=90, phase=0)` | 걷기 한 걸음. `phase` 0-1이 한 보폭. 옆모습(turn 60-90)에서 가장 잘 읽힌다 |
| 움직임 | `run(turn=90, phase=0)` | 달리기. 무릎을 높이 들고 뒷발을 차올린다. 몸이 앞으로 기운다 |
| 앉기 | `cross_legged_seat(turn=30)` | 의자에 앉아 다리 꼬기 |
| 앉기 | `squat(turn=40)` | 쪼그려 앉기. 무릎 위에 팔 |
| 앉기 | `sit_floor(turn=50, knees_up=False)` | 바닥에 앉기. 다리를 뻗고 뒤로 손을 짚거나(`False`) 무릎을 세워 끌어안기(`True`) |
| 기대기 | `lean_wall(turn=-25)` | 팔짱을 끼고 어깨를 벽에 기대기. 몸이 향한 반대쪽으로 기운다 |
| 눕기 | `lie_side()` | 옆으로 누워 아래팔을 베고 위쪽 손은 허리에. 머리는 화면 오른쪽. 가로 캔버스용 |

```python
from paintkit.figure import poses
walking = poses.walk(turn=75, phase=0.1)
seated = poses.cross_legged_seat(turn=-30, head_tilt=4)       # 나머지 Pose 필드는 키워드로 덮어쓴다
hair_up = replace(poses.contrapposto(turn=22), right_arm=(150, -78), right_hand=HandSpec('relaxed', 'palm'))
```

- 앉기, 눕기 프리셋은 의자와 바닥을 그리지 않는다. 엉덩이나 몸 아래쪽이 닿을 자리에 배경을 그린다
- `lie_side()`처럼 몸통을 굴린 자세(`roll`)는 팔다리 각도가 화면 기준이다. `aim()`은 `roll`을 따라가지 않는다
- 고개가 25도 넘게 기울면(누운 자세) 머리카락이 아래로 늘어지지 않고 머리와 함께 돌아 베개 위로 퍼진다
- 팔꿈치와 무릎의 꺾임은 두 각도의 차이다. (위팔 -30, 아래팔 48)이면 78도 꺾인다
- 포즈를 바꾼 뒤에는 마감 없이 `cv.save()`로 실루엣부터 확인한다
- 같은 인물을 여러 각도로 확인하려면 `scripts/examples/figure_turnaround.py`로 턴어라운드 시트를 만든다

## 11. 의상 (wardrobe)

몸에 붙는 옷은 몸 마스크를 영역으로 잘라 만든다. 그래서 어떤 포즈와 각도에도 맞는다. 치마는 골반에서 내려오는 별도 도형이다. `garments` 목록은 안쪽 옷부터 적는다.

| 함수 | 주요 인자 |
|---|---|
| `top(color, neckline=0.55, hem=-0.90, sleeve=0.0, scoop=0.55)` | `sleeve`: 어깨에서 소매 끝까지 길이(머리 단위). 0 민소매(끈), 1.2 반소매, 4.6-4.9 긴소매. `hem`: 골반 기준 밑단 높이 (-2 허리, 0 고관절). 남성 티셔츠는 `neckline=0.35, scoop=0.25` |
| `bottoms(color, waist=-1.15, length=1.0)` | `length`: 다리를 덮는 비율. 1 발목, 0.5 무릎, 0.2 짧은 바지 |
| `skirt(color, waist=-1.9, length=2.6, flare=0.45, folds=5)` | `length`: 골반 기준 밑단 높이 (3.9 무릎). `flare`: 밑단이 퍼지는 정도 |
| `dress(color, neckline=0.60, length=2.4, flare=0.40)` | 끈 달린 상의 + 치마 |
| `swimsuit(color, neckline=0.80, leg_cut=0.5)` | 원피스 수영복 |
| `bikini(color, tie=None, rise=0.0)` | 홀터넥 삼각 비키니와 옆을 묶은 하의. 컵 아랫단은 가슴 아래 주름 높이에 놓여 가슴이 끈 아래로 나오지 않는다. 목끈은 컵 꼭짓점에서 목 옆을 지나 목덜미 리본까지, 가슴 아래 끈은 주름을 따라 두 컵을 잇고 등 뒤 리본까지 간다. 하의 허리선은 골반뼈 높이에서 엉덩이 윤곽까지 닿고 옆 리본은 골반 옆선 위에 있다. `tie`: 끈 색. `rise`: 하의 높이 조절. 남성에게는 수영 팬티만 |
| `lingerie(color, lace='#f4eef2', bow=None)` | 브래지어와 팬티. 팬티 허리선은 골반뼈 높이에서 엉덩이 윤곽까지 닿는다. 레이스는 팬티 허리와 다리 트임을 앞뒤로 한 바퀴 두르고 브래지어 컵 윗단에 있다. 허리 앞에 작은 리본. `lace=None`이면 레이스 없음. 남성에게는 팬티만 |
| `hoodie(color, pocket=True, strings=True)` | 후드티. 긴소매, 손목과 밑단 시보리, 캥거루 주머니, 끈, 목 뒤 후드(뒷모습에서는 등 위) |
| `crop_top(color, sleeve=1.0, scoop=0.45)` | 배꼽 위에서 끝나는 상의. `sleeve=0`이면 끈 크롭탑 |
| `hot_pants(color='#5d7fae', waist=-1.25)` | 데님 핫팬츠. 단추, 앞주머니 스티치, 올이 풀린 밑단, 뒷모습에서 뒷주머니 |
| `suit(jacket, shirt='#f2f2ee', tie='#7a2a3a', trousers=None, buttoned=True)` | 양복 한 벌. 주름 잡힌 일자 바지, 깃 셔츠, 넥타이, 라펠과 주머니 덮개와 단추가 있는 재킷. 하나의 옷으로 넘긴다 |
| `shoes(color)` | 발을 덮는 단순한 신발 |
| `long_coat(color, length=3.4, buttoned=True, belt=None, lapel=None)` | 무릎까지 오는 겨울 코트. 넓은 라펠, 단추, 주머니 덮개, 뒤 솔기. 엉덩이에서 거의 곧게 떨어지고 앉으면 무릎 위에 얹힌다. `buttoned=False`면 가슴 아래부터 밑단까지 앞이 열린다. `belt`: 묶은 허리띠 색 |
| `padded_jacket(color, hem=0.40, collar=True)` | 패딩 점퍼. 부푼 몸판과 소매를 가로 박음선으로 나누고, 칸마다 부푼 빛을 넣는다. 세운 깃, 앞 지퍼 |
| `scarf(color, stripe=None, tail=True)` | 목에 두 번 감은 니트 목도리. 감은 고리는 앞이 조금 처지고 니트 골이 있다. 한쪽 끝이 가슴 앞, 관객에 가까운 쪽으로 늘어지고 끝에 술이 있다. `stripe`: 끝자락 줄무늬 색. `tail=False`면 감은 고리만 |
| `beanie(color, cuff=True, pompom=None)` | 니트 비니. 눈썹 위와 귀 윗부분까지 덮고 접은 단과 세로 골이 있다. `pompom`: 방울 색. 머리와 머리카락 다음에 칠해진다 |
| `boots(color, height=0.45, sole='#2a2624')` | 발과 정강이를 덮는 부츠. `height`: 정강이를 덮는 비율 (0.15 앵클, 1 무릎). 바지 다음에 넘기면 바지가 부츠 안에 들어간다 |

조합 예시

| 의상 | `garments` |
|---|---|
| 비키니 | `[wardrobe.bikini('#e8505a', tie='#fbf4ea')]` |
| 란제리 | `[wardrobe.lingerie('#7a2a4a', lace='#f4e6ea')]` |
| 후드티와 청바지 | `[wardrobe.bottoms('#2f3a52'), wardrobe.hoodie('#c8b48a'), wardrobe.shoes('#f0eee8')]` |
| 크롭티와 핫팬츠 | `[wardrobe.hot_pants(), wardrobe.crop_top('#f6f2ea'), wardrobe.shoes('#f4f4f4')]` |
| 양복 | `[wardrobe.suit('#2b2f3a', tie='#7a2a3a'), wardrobe.shoes('#1e1a18')]` |
| 겨울 코트 | `[wardrobe.bottoms('#2f3138'), wardrobe.top('#d8d2c8', sleeve=4.9, scoop=0.2), wardrobe.long_coat('#5b4a3e'), wardrobe.scarf('#8a2f35', stripe='#e8e0d4'), wardrobe.boots('#2a2420', height=0.5), wardrobe.beanie('#3f4a5a', pompom='#e8e4dc')]` |
| 패딩 | `[wardrobe.bottoms('#3a3d48'), wardrobe.padded_jacket('#2f3b2f'), wardrobe.boots('#3b3029', 0.2), wardrobe.beanie('#7a2f2f')]` |

```python
garments = [wardrobe.skirt('#2d3350', length=3.0, flare=0.32), wardrobe.top('#d9c8a8', sleeve=4.9, hem=-1.7)]
masks = draw_figure(cv, replace(figure, nude_details=False), garments)
```

- 팔과 손은 소매를 제외한 모든 옷보다 앞에 놓인다
- 몸을 돌리면 목선과 끈은 몸 표면을 따라 돌고, 목은 깃보다 앞에 놓인다
- 소매 있는 상의의 목둘레는 목을 감싼 고리(앞은 `scoop`만큼 낮고 뒤는 목덜미 아래)로 계산한다. 옆모습과 뒷모습에서는 관객을 향한 쪽 고리만 깃 선이 된다
- 민소매 끈은 앞에서는 가슴 쪽, 뒤에서는 등 쪽, 옆에서는 양쪽에 그려진다
- 바지는 다리 사이의 막힌 작은 틈을 메운다
- `bottoms(straight=True)`는 무릎 아래가 곧게 떨어지는 일자 바지다
- `top(close=True)`는 헐렁한 소매와 몸 사이의 좁은 틈을 천으로 메운다 (양복 재킷)
- `top(close=1.2)`처럼 숫자를 주면 그 넓이(머리 단위 제곱)보다 작은 막힌 틈도 메운다 (후드티). 허리에 손을 얹은 팔 안쪽처럼 넓은 틈은 남는다
- `top(cut=함수)`는 앞을 잘라 연 상의를 만든다. 함수는 `(cv, skeleton)`을 받아 잘라낼 마스크를 돌려준다 (`suit` 재킷의 V 여밈)
- `top(extend=함수)`는 상의에 몸 밖의 영역을 이어 붙여 한 벌로 칠한다. 함수는 `(cv, figure, skeleton, masks)`를 받아 마스크를 돌려준다 (`long_coat`의 아랫자락)
- `top(seal=0.05)`는 크게 부풀린 두 부분이 맞닿은 자리에 남는 가는 틈을 메운다 (코트, 패딩)
- 외투는 감싸는 옷 다음에 넘긴다: 바지, 상의, 외투, 목도리, 부츠, 비니 순
- 머리에 쓰는 옷은 garment 함수에 `over_head = True` 속성을 단다. `draw_figure`가 머리, 머리카락, 묶음머리 다음에 칠한다 (`beanie`)
- `HandSpec('pocket')`은 손을 그리지 않고 손목 주변을 옷 아래로 넣는다. 바지 앞주머니에 넣은 손
    + 팔 각도는 무시되고 어깨에서 주머니 입구까지 2관절 역운동학으로 다시 계산된다. 팔꿈치는 바깥 뒤쪽으로 굽는다
    + `HandSpec('pouch')`는 같은 방식으로 후드티 캥거루 주머니의 옆 입구로 손을 넣는다. 몸 앞을 가로지르는 소매는 별도 형태로 그려진다
    + 엉덩이를 덮는 긴 상의(후드티)에 `pocket`을 쓰면 손이 상의 아래로 사라진다. 후드티에는 `pouch`를 쓴다
- 비키니, 란제리처럼 몸 표면에 붙는 작은 천 조각은 몸 앞면과 뒷면에 따로 그려 몸을 돌려도 따라 돈다
    + 비키니와 란제리 하의는 허리선과 다리 트임 사이의 몸 표면을 좁은 띠로 나눠 투영한 뒤 몸 마스크로 자른다. 그래서 어느 각도에서도 허리띠가 엉덩이 윤곽까지 닿는다
    + 몸을 돌리면 화면에서 가까운 쪽 옆선을 경계로 앞면 조각과 뒷면 조각이 나뉜다
    + 끈의 점에 세 번째 값(lift)을 주면 몸 표면에서 띄운다. 띄운 컵 꼭짓점에서 시작한 끈이 피부로 내려앉는다
    + 팬티 레이스는 관객을 향한 구간에만 그린다. 몸 뒤로 돌아간 구간의 레이스는 앞쪽 천 위에 겹쳐 보인다
    + `fullbody.under_bust(figure)`는 가슴 아래 주름의 가슴 프레임 y를 돌려준다. 컵 아랫단과 가슴 아래 끈의 기준 높이
- 치마와 원피스는 앉은 자세를 알아서 따른다. 허벅지가 몸 아래 방향에서 크게 벗어나면 치마가 허벅지 위에 얹힌다
    + `length`는 앉으면 허벅지를 따라 잰다. 3.9(무릎)보다 길면 남는 길이만큼 무릎에서 아래로 늘어진다
    + 예시: `scripts/examples/couple_bench.py [out] [illustration|anime] skirt`
- 새 옷이 필요하면 `masks`의 부위 마스크와 `skeleton.chest.pt(x, y)`, `skeleton.chest.surface(x, y)`, `skeleton.pelvis.round_pts(points)`로 영역을 만들어 같은 방식으로 자른다
- 가슴 프레임 y: 0 목 아래 오목한 곳, 1.4 가슴 중심. 골반 프레임 y: -2.05 허리, -1.3 배꼽, 0 고관절, 0.7 가랑이

## 12. 인체화(누드)

- 리그는 몸의 표면 형태를 그린다. 가랑이는 부드러운 그림자로 처리한다. 성기 형태를 그리는 기능은 없다
    + 여성: 쇄골, 가슴, 유두, 복부 중심선, 배꼽, 서혜부 주름, 무릎, 발가락
    + 남성: 쇄골, 가슴근육 아랫선, 작은 유두, 복직근의 가로 마디와 가장자리, 장골 고랑(가랑이 위에서 멈춤), 전거근, 울대뼈
    + 뒷모습(공통): 척추 고랑과 양옆 근육, 날개뼈, 허리 보조개, 엉덩이 골과 아랫주름, 무릎 뒤 주름
    + 표면 표시는 관객을 향한 정도에 따라 옅어지고 윤곽 너머에서는 사라진다
- 미성년자의 누드와 성행위 묘사는 그리지 않는다
    + 판단 근거는 두 가지다. 미성년자로 명시된 인물(18세 미만 나이 설정, 아동 지정), 이차성징 이전의 몸 묘사(아동 체형과 비례)
- 그럴듯함을 만드는 요소 순서
    + 포즈: 콘트라포스토와 S자 흐름, 3/4 각도(`turn` 25-35)
    + 빛: `replace(ILLUSTRATION, light=(-0.65, -0.75), light_height=0.55, shade_depth=1.25)`. `light_height`를 낮추면 몸의 굴곡과 근육이 깊게 드러난다
    + 배경: 어둡고 단순하게. 몸과 명도 차이를 크게
    + 테두리 빛: 그림자 쪽에 차가운 색 `add_rim_light`
- 긴 머리(`side_length` 2.0 이상)나 천, 팔의 위치로 가리는 연출이 가능하다
- 전체 예시는 `scripts/examples/figure_nude_study.py [out] [illustration|oil] [female|male]`

## 13. 손

```python
from paintkit.figure import HandSpec, draw_hand
draw_hand(cv, wrist=(400, 600), direction_deg=180, length=260, skin='#f3cdb6', look=look,
          spec=HandSpec('peace', 'back'), thumb_side=1, forearm=0.5)
```

| 인자 | 의미 |
|---|---|
| `wrist` | 손목 중심 px |
| `direction_deg` | 손끝이 향하는 방향 (0 아래, 180 위) |
| `length` | 손목에서 중지 끝까지 px |
| `spec.pose` | `open`, `relaxed`, `fist`, `point`, `peace`, `thumbs_up` |
| `spec.view` | `back` 손등(손톱, 손마디), `palm` 손바닥(손금) |
| `spec.roll` | 손을 길이 축으로 돌린 각도. 0 평면, 90 옆에서 본 손. 양수면 엄지 쪽이 관객을 향한다 |
| `spec.nails` | 매니큐어 색. 빈 문자열이면 자연색 |
| `thumb_side` | 손끝이 아래를 향할 때 엄지가 화면 오른쪽이면 +1, 반대면 -1 |
| `forearm` | 손목 뒤로 함께 그릴 아래팔 길이 (손 길이의 배수). 손 습작용 |

- 손을 돌리면 손바닥 두께, 굽힌 손가락, 엄지의 앞뒤 깊이가 옆으로 드러난다. 옆에서 본 손은 얇은 손바닥 위로 손가락이 손바닥 쪽으로 말린다
    + 힘 뺀 엄지는 손이 돌아갈수록 검지를 따라 손바닥 앞으로 모인다
    + 손이 돌아갈수록 손가락 사이가 좁아진다
    + 접힌 손가락은 옆에서 보면 고리 모양으로 손바닥에 말려 들어간다
- 전신 리그에서는 `roll`을 직접 주지 않는다. 몸 방향과 `view`로 손이 알아서 돈다
    + `back`: 정면에서 손등이 보이게 둔 손. 몸을 돌리면 옆에서는 옆선, 뒤에서는 손바닥이 보인다
    + `palm`: 정면에서 손바닥이 보이게 둔 손
    + `rest`: 늘어뜨린 팔의 자연스러운 손. 손바닥이 허벅지를 향한다. 정면과 뒤에서는 비스듬한 옆모습, 옆에서는 손등이 보인다. 몸을 돌리는 그림의 늘어뜨린 손에 권장
- 새 손 모양은 `paintkit.figure.hand.POSES`에 `(엄지, 검지, 중지, 약지, 소지 굽힘 0-1), 벌림 0-1, 엄지 뻗음 0-1`을 추가한다. 굽힘이 0.7을 넘으면 접힌 손가락으로 그려진다
- look의 `scale`을 손 크기에 맞춘다: `replace(look, scale=length / 260)`
- 전체 예시는 `scripts/examples/hand_study.py`

## 14. 돌려받는 값

`draw_figure`의 반환 dict.

| 키 | 내용 |
|---|---|
| `all` | 인물 전체 마스크 |
| `skin` | 피부 전체 |
| `torso`, `neck`, `left_leg`, `right_leg`, `left_foot`, `right_foot`, `left_arm`, `right_arm`, `left_hand`, `right_hand`, `left_breast`, `right_breast` | 부위 마스크 (남성의 `_breast`는 가슴근육). 먼 쪽 팔과 손은 몸에 가려진 부분이 빠진 마스크 |
| `garment_0`, `garment_1`, ... | 옷 마스크 (목록 순서) |
| `face`, `eyes`, `front_hair`, `back_hair` | 머리 부위 |
| `tie` | 묶음머리(포니테일, 땋은 머리, 번). 없으면 None 또는 빈 마스크 |
| `skeleton` | 관절 좌표 `skeleton.joints['left_wrist']` 등과 `chest`, `pelvis` 프레임, `head` |

관절 이름: `pit`, `neck_base`, `neck_top`, 그리고 `left_`/`right_` + `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle`.
소품을 손에 쥐게 하려면 `skeleton.joints['right_wrist']` 근처에 그린다. `fullbody.far_side(pose)`는 몸을 돌렸을 때 먼 쪽(`'left'`, `'right'`, None)을 알려준다. `fullbody.in_pocket(pose, name)`은 그 쪽 손이 주머니(`pocket`, `pouch`)에 들어 있는지 알려준다.

## 15. 배경 속에 세우기와 구도 (fit, thirds, group)

- 바닥 그림자를 먼저 깐다: `cv.tint(blur(cv.ellipse(x, floor_y, 300, 30), 18), '#120e12', 'multiply', 0.75)`
- 원근 장면에서는 카메라가 크기를 정한다 (`references/city.md`)

```python
scale = view.scale_at(x_m, 0.0, z_m)                  # 그 자리의 1m가 몇 px인지
figure = Figure(pelvis=view.project(x_m, 0.90, z_m), height=1.70 * scale, ...)
```

- 2점 투시 장면(`city.Camera`)에서는 인물이 카메라를 향하는 정도를 `turn`으로 맞춘다

원근 없는 장면은 구도 도우미로 인물을 놓는다. 셋 다 `Figure(**...)`에 바로 넘기는 `pelvis`, `height`를 돌려준다.

| 함수 | 내용 |
|---|---|
| `fit(box, pose, sex='female', align='bottom', scale=1.0)` | 포즈를 잡은 인물을 상자 `(x0, y0, x1, y1)` 안에 가장 크게 넣는다. 가로는 가운데, 세로는 바닥(`bottom`)이나 가운데(`center`)에 맞춘다 |
| `thirds(size, column='left', margin=0.06)` | 3분할선(`left`, `center`, `right`)을 중심으로 한 상자. `fit`에 넘긴다 |
| `group(box, poses, sexes, scales, gap=0.04, shot=None, headroom=0.55)` | 여러 인물을 한 바닥선에 같은 축척으로 나란히 놓는다. `scales`: 상대 키 (남성 1.0, 여성 0.94). `gap`이 음수면 서로 겹친다. `shot`(`waist`, `thigh`, `bust` 등)을 주면 가장 큰 인물이 그 샷으로 상자 높이를 채우고 바닥선은 화면 아래로 나간다. 줄이 상자보다 넓으면 그만큼 느슨한 샷이 된다 |
| `pose_bounds(figure)` | 인물이 차지하는 화면 상자. 머리카락, 손, 발까지 포함 |

```python
from paintkit.figure import fit, group, thirds
pose = poses.contrapposto(turn=22)
x0, _, x1, _ = thirds(cv.size, 'left')                          # 왼쪽 3분할선에 세우기
figure = Figure(**fit((x0, 120, x1, 1330), pose), pose=pose, nude_details=False)

man, woman = poses.arms_crossed(turn=30), poses.hands_on_hips(turn=-35)
places = group((260, 80, 1300, 1050), [man, woman], sexes=['male', 'female'], scales=[1.0, 0.94], gap=0.10)
pair = [Figure(**places[0], pose=man, sex='male'), Figure(**places[1], pose=woman)]

trio = [poses.contrapposto(turn=30), poses.hands_in_pockets(turn=5), poses.arms_crossed(turn=-30)]
places = group((40, 60, 1160, 1500), trio, sexes=['female', 'male', 'male'], scales=[0.95, 1.0, 1.02],
               gap=-0.10, shot='waist', headroom=0.6)   # 허리샷 목표. 세로 화면에 셋이면 폭에 맞춰 무릎샷까지 느슨해진다
```
- 겹친 단체 사진은 가운데 인물을 마지막에 그려 앞에 세운다

- 상자의 바닥이 발이 닿는 바닥선이다. 바닥 그림자는 `figure.pelvis[0]` 아래 바닥선에 깐다
- 누운 인물은 `fit`의 상자 바닥을 바닥면보다 0.4-0.5 머리 단위 아래로 둔다. 서 있는 발 기준 여유가 들어 있다
- 의상별 장면 예시: `beach_bikini.py`, `bedroom_lingerie.py`, `hoodie_street.py`, `summer_street.py`, `office_suits.py`
- 인원과 구도별 장면 예시: `station_platform.py` (투샷), `park_group.py` (5명, 서기와 앉기), `picnic.py` (바닥에 앉은 투샷), `group_portrait_oil.py` (겹친 3인 허리샷)

## 16. 헤어스타일 (hairstyles)

```python
from paintkit.figure import hairstyle

figure = Figure(**framing(cv.size, 'bust'), hair=hairstyle('ponytail', color='#3a2a24'))
man = Figure(**framing(cv.size, 'bust'), sex='male', hair=hairstyle('two_block'))
```

- `hairstyle(name, **changes)`는 이름 붙은 `HairSpec`의 복사본을 돌려준다. 색, `seed`, 길이 등 어떤 인자든 바꿔 넘긴다
- 표는 `FEMALE_STYLES`, `MALE_STYLES`, 둘을 합친 `HAIRSTYLES`. 이름은 머리 모양만 뜻하므로 성별과 상관없이 쓸 수 있다
- 시트: `scripts/examples/hairstyle_catalog.py [out] [female|male]` (아래 표 순서, 위 앞 3/4, 아래 뒤 3/4)

| 여성 | 모양 |
|---|---|
| `long` | 긴 생머리와 가벼운 앞머리 (기본 `HairSpec`) |
| `long_wavy` | 옆으로 넘긴 앞머리, 웨이브 긴 머리 |
| `center_long` | 가운데 가르마, 커튼 앞머리, 긴 머리 |
| `hime` | 일자 앞머리, 볼 옆에서 자른 옆머리, 긴 머리 |
| `bob` | 일자 앞머리 단발 |
| `pixie` | 옆으로 넘긴 앞머리의 아주 짧은 머리 |
| `ponytail` | 높은 포니테일, 얼굴 옆 가닥 |
| `low_ponytail` | 목덜미에서 묶은 낮은 포니테일 |
| `braid` | 목덜미에서 땋아 내린 한 갈래 |
| `bun` | 정수리 뒤 높은 번, 이마를 드러냄 |
| `low_bun` | 가운데 가르마, 목덜미 쪽머리 |
| `half_up` | 윗머리만 작게 묶은 반묶음 |

| 남성 | 모양 |
|---|---|
| `buzz` | 버즈컷. 머리 전체를 짧게 밀어 두피가 비친다 |
| `crew` | 크루컷. 짧은 윗머리, 옆과 뒤를 점점 짧게 |
| `side_part` | 옆 가르마 짧은 머리 (`MALE_HAIR`와 같음) |
| `fringe` | 이마를 덮는 가벼운 앞머리 (댄디컷) |
| `two_block` | 투블럭. 숱 많은 윗머리 아래 옆과 뒤를 짧게 밀었다 |
| `comma` | 옆으로 넘겨 눈썹 위에서 휘는 앞머리 (쉼표머리) |
| `center_part` | 가운데 가르마 앞머리 |
| `slicked_back` | 이마를 드러내고 뒤로 빗어 넘긴 올백 |
| `spiky` | 위로 뻗친 머리와 뾰족한 앞머리 |
| `shoulder` | 어깨까지 오는 가운데 가르마 장발 |
| `man_bun` | 뒤로 넘겨 정수리 뒤에 묶은 번 |
| `low_tail` | 뒤로 넘겨 목덜미에서 묶은 짧은 꽁지머리 |

- 묶음머리 꼬리는 중력으로 늘어지고 한쪽으로 살짝 흔들리며 등 위에 얹힌다. 머리가 많이 기울면(25도 넘게) 나머지 각도만큼 함께 돈다
- 달리기나 바람 장면은 `hairstyle('ponytail', flow=0.7)`. 꼬리와 땋은 머리가 머리 뒤로 날리며 끝이 조금 처지고 물결친다 (0 늘어짐 .. 1 수평)
- 번은 머리에 고정되어 머리와 함께 돈다
- 정면에서 높은 포니테일은 목 옆으로 조금만 보인다. 꼬리를 보여주려면 고개나 몸을 30도 이상 돌린다

## 17. 얼굴 스타일과 표정 (expressions)

```python
from paintkit.figure import expression, face_style

face = expression(face_style('female', 'sharp', eye_color='#5a4a3a'), 'tired')
figure = Figure(**framing(cv.size, 'face'), face=face)
calm = expression(face_style('male', 'plain'), 'smile', amount=0.5)
```

| 성별 | 스타일 | 인상 |
|---|---|---|
| 여성 | `soft` | 기본 (`FEMALE_FACE`) |
| 여성 | `sharp` | 가늘고 올라간 눈꼬리, 옅은 홍조 |
| 여성 | `mature` | 조금 작은 눈, 짙은 입술, 낮은 눈썹 |
| 여성 | `bright` | 큰 눈, 수평 눈꼬리, 밝은 미소 |
| 남성 | `plain` | 기본 (`MALE_FACE`) |
| 남성 | `sharp` | 가는 눈, 올라간 눈꼬리, 낮은 눈썹 |
| 남성 | `gentle` | 조금 큰 눈, 높은 눈썹, 옅은 미소 |
| 남성 | `rugged` | 작은 눈, 아주 굵고 낮은 눈썹, 조금 짙은 피부 |

| 표정 | 바뀌는 곳 |
|---|---|
| `neutral` | 입꼬리 평평 |
| `smile` | 입꼬리 올림, 아랫눈꺼풀 조금 올림 |
| `grin` | 크게 벌린 입과 윗니, 눈웃음 |
| `sad` | 안쪽이 올라간 눈썹, 처진 입꼬리, 내리깐 시선 |
| `angry` | 안쪽이 내려온 눈썹, 처진 입꼬리, 조금 내린 눈꺼풀 |
| `surprised` | 올라간 눈썹, 크게 뜬 눈, 동그랗게 벌린 입 |
| `tired` | 반쯤 내린 눈꺼풀, 내리깐 시선 |
| `pensive` | 내린 눈꺼풀, 옆 아래를 보는 시선, 눈을 맞추지 않음 |

- `expression(face, name, amount)`: 입, 눈꺼풀, 시선, 눈썹 기울기는 목표값으로 바꾸고 눈썹 높이는 얼굴 자체 값에 더한다. 그래서 남성의 낮은 눈썹은 어느 표정에서도 낮게 남는다
- `amount` 0 .. 1로 원래 얼굴에서 표정까지 섞는다. `eye_contact` 같은 켜고 끄는 값은 0.5에서 바뀐다
- 일자 앞머리는 눈썹을 가린다. 눈썹 표정을 살리려면 `center_long`, `side_part` 같은 이마가 보이는 헤어를 쓴다
- 시트: `scripts/examples/expression_sheet.py [out]` (행: 위 표 순서, 열: 여 soft, 여 sharp, 남 plain, 남 rugged)
- 두머 무드 장면에는 `tired`, `pensive`, `neutral`이 어울린다

## 18. 한계

- 몸이 앞이나 뒤로 숙인 자세(허리 굽힘)는 없다. `lean`은 화면 안에서 기우는 것만 표현한다
- 옷은 몸에 붙는 형태다. 바람에 날리거나 크게 접히는 천, 단추를 푼 셔츠 자락은 없다
- 핫팬츠를 옆에서 보면 다리 사이가 천으로 이어져 짧은 치마처럼 보인다
- 원근이 강한 단축(카메라를 향해 뻗은 팔 등)은 `aim()`의 길이 비율로 흉내 내며, 끝부분의 크기 변화는 없다
- 팔이 몸 뒤로 가는 포즈는 먼 쪽 팔만 몸에 가려진다. 가까운 팔을 등 뒤로 돌리는 포즈는 없다
- 손은 손목 축 회전까지 지원한다. 손끝이 관객을 향하는 단축은 없다. 물건을 쥔 손은 `fist`에 소품을 겹쳐 표현한다
- 앉은 치마는 허벅지와 무릎을 감싼 볼록한 형태다. 다리를 꼬거나 벌려 생긴 천의 처짐은 없다
- 묶음머리 꼬리는 팔, 옷, 등받이와의 충돌을 계산하지 않는다. 등을 기댄 자세에서는 꼬리 위치를 눈으로 확인한다
- `fit()`, `group()`의 인물 크기 계산은 높은 번의 높이를 넣지 않는다. 번이 잘리면 `headroom`이나 상자 위 여백을 늘린다
- 목도리 끝은 한쪽만 앞으로 늘어진다. 두 끝을 모두 늘어뜨리거나 어깨 뒤로 넘긴 모양은 없다
