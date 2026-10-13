# 전신과 손

`scripts/codepainter/figure/`의 전신 리그와 손 리그. 3D 모델 없이 평면 관절 골격에 굵기 프로필 튜브를 입히는 방식으로 동작한다. 머리는 흉상 리그의 머리를 그대로 얹는다.

## 호출

```python
from codepainter.figure import PortraitSpec, BodySpec, draw_figure, wardrobe
from codepainter.figure.body import make_pose

pose = make_pose("hand_on_hip", root=(0.50, 0.475), unit=0.105)
masks = draw_figure(painting, PortraitSpec(yaw=-0.5), BodySpec(), pose, style, dress=wardrobe.bodycon)
```

- 배경을 먼저 그린 Painting 위에 호출
- `dress=None`이면 옷 없는 인체로 그림
- 반환값은 `figure`, `skin`, `head`, `trunk`, `limbs`, `clothes`, `hair`, `eyes`, `hands` 마스크와 `skeleton`, `frame`
    + `masks["head"]`는 회화풍 `finish`의 `importance`로 사용
    + `masks["skeleton"].joints`는 관절 픽셀 좌표 사전, 소품 배치에 사용

## 단위와 각도

- 길이 단위는 머리 높이 1개
    + 기본 신장은 약 7.7등신, `BodySpec.legs=1.0`이면 8등신
- 좌우는 화면 기준, `l`은 보는 사람의 왼쪽
- 각도는 도 단위, 0은 수직 아래, 양수는 화면 오른쪽, 180은 수직 위
    + 예시 : 화면 왼쪽 팔을 바깥으로 벌리면 음수, 화면 오른쪽 팔을 바깥으로 벌리면 양수

## 포즈 프리셋

`make_pose(name, **overrides)`가 프리셋에 원하는 항목만 덮어쓴 Pose를 반환한다.

| 이름 | 내용 |
|---|---|
| `stand` | 정자세 |
| `contrapposto` | 짝다리, 양팔 내림 |
| `hand_on_hip` | 짝다리, 화면 오른쪽 손을 골반에 |
| `arm_behind_head` | 짝다리, 한 팔은 머리 뒤, 한 손은 골반 |
| `arms_up` | 양팔을 머리 뒤로 올림 |
| `walk` | 한 다리가 앞으로 교차하는 걸음 |
| `walk_side` | 옆에서 본 걸음 (`yaw=90`), 앞뒤로 벌린 다리와 반대로 흔드는 팔 |
| `stance` | 두 발을 벌리고 선 정면 자세, 남성 인물에 적합 |
| `back` | 뒷모습 짝다리 |
| `sit`, `sit_side`, `sit_front` | 의자에 앉기 (3/4, 측면, 정면) |
| `kneel`, `kneel_side`, `seiza` | 무릎 꿇기, 발뒤꿈치 위에 앉기 |
| `lie_back`, `lie_side` | 등을 대고 눕기, 옆으로 눕기 |

- 앉기, 무릎 꿇기, 눕기와 가구, 투샷, 구도 프리셋은 `references/clothing-and-scenes.md`

- 프리셋은 모두 화면 왼쪽 다리에 체중을 실음
    + 반대쪽은 `pelvis_tilt`, `chest_tilt`, `waist_shift`와 팔다리 각도의 부호를 뒤집어 지정
- 구도는 `root`와 `unit`으로 지정
    + 전신은 `root=(0.50, 0.475), unit=0.105`
    + 무릎 위 반신은 `root=(0.47, 0.715), unit=0.168`

## Pose

| 항목 | 기본값 | 의미 |
|---|---|---|
| `root` | (0.50, 0.51) | 골반 중심 위치, 캔버스 대비 비율 |
| `unit` | 0.120 | 머리 높이 / 캔버스 높이 |
| `view` | "front" | `front` 또는 `back` (뒷모습) |
| `lean` | 0 | 몸 전체 기울기 |
| `pelvis_tilt` | 0 | 골반선 기울기, 양수는 화면 오른쪽 골반이 내려감 |
| `chest_tilt` | 0 | 어깨선 기울기, 양수는 화면 오른쪽 어깨가 내려감 |
| `waist_shift` | 0 | 흉곽이 골반 위에서 옆으로 밀린 거리, 양수는 화면 오른쪽 |
| `yaw` | 0 | 몸 돌림(도), 45는 3/4, 90은 측면, 양수는 몸 앞면이 화면 오른쪽을 향함 |
| `head_yaw` | None | 머리 돌림(도), None이면 몸 `yaw`를 따름 |
| `swing` | {} | 뼈별 앞뒤 흔들림(도), 양수는 앞으로, 측면에서 드러남 |
| `turn` | 0 | 정면용 약한 돌림, -1 - 1, `yaw`를 쓰면 0으로 둠 |
| `arm_l`, `arm_r` | (-10, 3), (10, -3) | (위팔 각도, 아래팔 각도) |
| `leg_l`, `leg_r` | (-3, -1), (3, 1) | (허벅지 각도, 정강이 각도) |
| `foot_l`, `foot_r` | -18, 18 | 발 방향 |
| `hand_l`, `hand_r` | None | 손 방향, None은 아래팔 방향 유지 |
| `head_tilt` | 0 | 고개 기울임 |
| `behind` | () | 몸통 뒤로 가는 팔다리, 예시 `("arm_l",)` |
| `front_leg` | None | 다른 다리 앞으로 교차하는 다리, `"leg_l"` 또는 `"leg_r"` |
| `shorten` | {} | 뼈 길이 배율, 관람자 쪽으로 향한 팔다리의 단축 표현 |
| `pitch` | 0 | 카메라가 내려다보는 각도(도), 정면 앉기의 무릎 표현 |
| `ground` | None | 몸통이 닿는 의자면이나 침대면까지 화면 아래 거리, None은 앉은 자세에서 0.36 |

- `shorten`과 `swing`의 키는 `upper_arm_l`, `forearm_l`, `thigh_l`, `shin_l`, `foot_l`과 `_r` 짝
    + `swing`에 `foot_x`가 있으면 발 방향을 그 흔들림으로 직접 계산 (무릎 꿇기의 발등)

## 돌린 몸 (3/4, 측면)

```python
pose = make_pose("contrapposto", root=(0.50, 0.475), unit=0.105, yaw=45)     # 3/4
pose = make_pose("walk_side", root=(0.50, 0.475), unit=0.105)               # 측면 걸음
pose = make_pose("stand", yaw=-90, head_yaw=-60)                           # 왼쪽을 향한 측면, 머리는 덜 돌림
```

- 관절과 몸통 단면에 깊이 값을 두고 세로축으로 돌린 뒤 평면 투영 (2.5D)
    + 3D 모델과 3D 엔진은 미사용
    + `yaw=0`은 기존 정면 리그와 픽셀 단위로 같은 결과
- 몸통은 높이별 타원 단면의 연속
    + 정면 실루엣은 기존 폭 함수, 측면 실루엣은 `body.TRUNK_DEPTH`의 앞뒤 깊이
    + 측면 S자는 가슴 앞, 허리 뒤 오목, 엉덩이 뒤 돌출, 허벅지 앞 볼록, 종아리 뒤 볼록
- 가슴과 엉덩이는 단면에 얹은 볼륨
    + 돌린 몸에서는 위쪽 비탈이 곧게 이어지는 물방울형
    + 먼 쪽 가슴은 가까운 쪽에 가려진 부분의 표지를 그리지 않음
- 22도를 넘으면 먼 쪽 팔은 몸통 뒤, 가까운 쪽 다리는 앞에 자동 배치
    + 먼 쪽 팔이 숨으면 몸통의 먼 쪽 어깨 둥근 부분도 함께 제거
- 앞면 해부 표지는 몸이 돌아간 만큼 흐려지고 보이지 않는 면에서 사라짐
- 의상은 정면 좌표를 몸 둘레에 감아 배치
    + 몸통 반폭을 넘는 x는 옆구리를 돌아 등으로 이어짐, `hip * (1 + pi/2)`가 등 한가운데
    + 수영복과 비키니 하의는 돌린 몸에서 엉덩이 아래까지 덮음
    + 치마는 돌린 몸에서 엉덩이와 허벅지를 감싸는 원뿔형 껍데기로 다시 그림
    + 새 의상의 치마는 `wardrobe._turned_skirt`, 몸을 감싸는 껍데기는 `body.wrapped_outline` 참조
- 머리는 몸을 따라 돌고 25도를 넘으면 옆얼굴 키로 넘어감 (`references/figure-rig.md`)
- 뒷모습(`view="back"`)은 돌림을 무시하고 정면 뒷모습으로 그림

### 포즈 요령

- 짝다리(콘트라포스토)는 골반선과 어깨선을 반대로 기울임
    + 체중을 실은 다리 쪽 골반이 올라가고 같은 쪽 어깨가 내려감
    + 체중 실린 다리는 수직에 가깝게, 반대쪽 다리는 무릎을 살짝 굽힘
    + 골반이 디딤발 위로 밀리므로 흉곽은 자유로운 다리 쪽으로 이동 (`waist_shift` 0.04-0.06)
    + 결과적으로 디딤발 쪽 골반이 튀어나오고 그 위 허리가 짧게 접힘
- 허리에 손은 위팔을 바깥으로 40도, 아래팔을 안쪽으로 -46도, `hand_r=-6`
- 머리 뒤로 올린 팔은 위팔 -150도 안팎, 아래팔 60도 안팎, `behind`에 해당 팔 등록
- 포즈는 렌더링으로 확인하며 5-10도 단위로 조정
    + 손목이 엉뚱한 곳에 가면 위팔과 아래팔 각도를 번갈아 수정

## BodySpec

| 항목 | 기본값 | 의미 |
|---|---|---|
| `shoulder` | 0.56 | 어깨 관절 사이 거리의 절반 |
| `chest` | 0.47 | 흉곽 반폭 |
| `waist` | 0.385 | 허리 반폭 |
| `hip` | 0.70 | 골반 반폭, 어깨 폭과 비슷하게 두어 모래시계형 실루엣 |
| `bust` | 1.45 | 가슴 크기, 0은 평평, 1은 작은 편, 1.45는 풍만, 1.8은 매우 풍만 |
| `limb` | 1.0 | 팔다리 굵기 배율 |
| `legs` | 0.95 | 다리 길이 배율 |
| `head` | 1.08 | 머리 크기 배율 |
| `build` | "female" | `female` 또는 `male`, 해부 표지와 허벅지 형태 선택 |
| `arms` | 1.0 | 팔 굵기 추가 배율 |
| `neck` | 1.0 | 목 폭 배율 |

- 기본값은 허리가 가늘고 골반이 넓은 굴곡 체형
- 더 풍만한 체형은 `BodySpec(bust=1.75, hip=0.74, limb=1.08)`
- 마른 패션 체형은 `BodySpec(bust=1.0, hip=0.62, chest=0.46, limb=0.92, legs=1.0, head=1.0)`
- 고관절 위치는 `hip`에 비례하므로 골반 폭을 바꾸면 허벅지도 함께 이동

## 남성 인물

```python
from codepainter.figure.body import MALE_BODY, make_pose
from codepainter.figure.frame import MASCULINE

spec = PortraitSpec(**MASCULINE, yaw=-0.45, skin="#e6bf9f", hair="#2a2022", cloth="#2c3a52", cloth_second="#d8d2c6")
draw_figure(painting, spec, MALE_BODY, make_pose("stance", root=(0.50, 0.475), unit=0.105), style, dress=wardrobe.trunks)
```

- `MALE_BODY`는 어깨가 골반보다 넓고 허리가 곧은 마른 근육형
    + 팔 굵기 `arms=1.22`, 소매를 입혀도 위팔이 풍선처럼 부풀지 않는 값
    + 체형 조정은 `dataclasses.replace(MALE_BODY, arms=1.4, shoulder=0.72)`처럼 일부만 변경, 굵은 팔은 맨몸 습작에 한정
- `MASCULINE`은 얼굴 덮어쓰기 사전
    + 넓은 턱(`jaw=0.40`), 작고 가는 눈, 낮고 곧은 굵은 눈썹(`brow=1.55`), 옅은 속눈썹(`lashes=0.35`), 무채색 입술, 짧은 머리
    + 짧은 머리는 `hair_style="short"`, 앞머리는 `bangs="textured"`
- 해부 표지는 쇄골, 대흉근 판과 아래 경계선, 복직근 3단 마디, 복직근 바깥 홈, 전거근, 골반 위 V선
- 뒷모습 둔부는 `hip`에 비례해 작아지고 높게 붙으며 옆 오목면이 추가됨
- 리그는 생식기 형태를 그리지 않음
    + 정면 남성 맨몸은 가랑이가 매끈한 마네킹처럼 보이므로 `wardrobe.trunks`가 자연스러움
    + 짧은 하의 착용 예제는 `examples/figure.py --build male --outfit trunks`

## 매력 있는 인체의 조건

- 실루엣에 S자 흐름을 만듦
    + 짝다리 프리셋 사용, `pelvis_tilt` 7-9와 `chest_tilt` -5 - -7, `waist_shift` 0.04-0.06
- 약한 3/4 돌림이 입체감을 줌
    + `turn` 0.3 - 0.5 (또는 음수), 머리 `yaw`는 몸과 같은 쪽 소폭
- 허리와 골반의 폭 차이를 유지
    + 여성은 `waist / hip` 0.52 - 0.60 범위
    + 남성은 `shoulder`가 `hip`보다 0.12 이상 넓게
- 목은 길게 두고 어깨는 승모근 경사에서 삼각근으로 둥글게 이어짐
    + `body.py`의 `NECK`, `SHOULDER_DROP`, `torso_curve` 참조
- 몸통 옆선은 높이별 폭 함수 하나로 생성
    + 폭 기준점은 `FLANK_STATIONS`(골반-허리)와 `RIB_STATIONS`(허리-흉곽)
    + 단조 보간이라 기준점 사이에서 폭이 출렁이지 않고 허리 최소점이 매끈함
    + 골반 좌표계에서 흉곽 좌표계로 `TRUNK_BLEND` 구간에서 부드럽게 넘어감
    + 옆선 점을 좌표계별로 따로 찍으면 기울기가 다른 좌표계끼리 어긋나 허리에 혹과 패임이 생김
    + 폭 함수는 골반 최대폭 아래로 계속 이어져 바깥 허벅지로 둥글게 넘어감
- 두 허벅지 사이 틈은 명암 계산에서 메움 (`bridged_height`)
    + 틈 꼭대기가 깊은 가장자리로 계산되면 가랑이 위에 둥근 혀 모양 그림자가 생겨 패인 자국처럼 보임
    + 틈 꼭대기에서 메움을 시작해 `BRIDGE_DEPTH` 아래로 서서히 풀어 안쪽 허벅지 그림자가 자연스럽게 자라남
- 둔부는 흐린 마스크와 넓고 부드러운 명암 경계로 그림
    + 실루엣 안쪽의 날카로운 셀 경계는 찌그러진 자국으로 읽힘
    + 엉덩이 아래 주름은 안쪽 절반만 짧게 그림
- 빛은 측면에서 비춤
    + 몸 한쪽 전체가 그늘에 잠겨야 굴곡이 드러남
- 팔은 몸통에서 떼어 실루엣에 빈틈을 만듦
    + 허리에 손, 머리 뒤로 올린 팔이 허리선을 가리지 않음
- 피부색은 `#f2d2b8` 안팎의 중간 밝기로 지정
    + 밑색이 흰색에 가까우면 윤기 하이라이트가 묻힘

## 의상

| 이름 | 내용 | 사용 색 |
|---|---|---|
| `wardrobe.bikini` | 삼각 컵과 끈, 로우라이즈 하의 | `cloth` |
| `wardrobe.swimsuit` | 원피스 수영복 | `cloth` |
| `wardrobe.bodycon` | 몸에 붙는 끈 원피스, 허벅지 길이 | `cloth` |
| `wardrobe.slip_dress` | 끈 원피스, 엉덩이에서 퍼지는 치마 | `cloth` |
| `wardrobe.top_and_jeans` | 민소매 상의와 붙는 바지 | `cloth`, `cloth_second` |
| `wardrobe.trunks` | 짧은 사각 하의와 허리 밴드, 남성 습작용 | `cloth`, `cloth_second` |
| `wardrobe.shirtless_jeans` | 상의 없이 골반에 걸친 일자 청바지 | `cloth_second` |
| `wardrobe.jeans` | 바지만, `rise`(허리선 위치)와 `ease`(여유) 지정 | `cloth_second` |
| `lingerie`, `lingerie_stockings` | 레이스 브라와 팬티, 스타킹 | `cloth` |
| `crop_top_shorts` | 크롭티, 핫팬츠, 운동화 | `cloth`, `cloth_second` |
| `hoodie`, `hoodie_shorts` | 후드티와 청바지 또는 핫팬츠, 운동화 | `cloth`, `cloth_second` |
| `suit` | 셔츠, 넥타이, 재킷, 정장 바지, 구두 | `cloth` |

- 마지막 4종은 `wardrobe.WARDROBE[이름]`으로 사용, 소매와 겹옷 구조는 `references/clothing-and-scenes.md`

- 몸에 붙는 옷은 몸 마스크에서 잘라냄
    + `wardrobe.fitted(painting, skeleton, body_mask, region, color, style, light)`에 영역 곡선만 전달
    + 영역은 목선과 밑단만 설계하고 옆은 몸 밖 멀리까지 넓게 잡음
    + 여유 있는 옷은 `ease`(머리 높이 단위)로 몸에서 띄움, 일자 청바지는 0.05-0.06
- 좌표는 `skeleton.on_chest`, `skeleton.on_waist`, `skeleton.on_pelvis`로 지정
    + 가슴 좌표는 어깨선이 y=0, 아래로 양수, 가슴 중심 0.66, 흉곽 아래 1.05
    + 골반 좌표는 고관절이 y=0, 허리 -0.78, 배꼽 -0.50, 가랑이 0.45
- 새 의상 함수의 형식은 `f(painting, skeleton, masks, spec, style, light)`, 그린 마스크 반환
    + `masks["skin"]`은 그 시점까지 그려진 몸, `masks["trunk"]`은 몸통만

```python
def tunic(painting, skeleton, masks, spec, style, light):
    top = skeleton.on_chest([(-3, 0.40), (-0.2, 0.46), (0.2, 0.46), (3, 0.40)])      # 목선
    hem = skeleton.on_pelvis([(3, 0.62), (-3, 0.62)])                                 # 밑단
    region = np.vstack([geo.smooth(top), hem])
    return wardrobe.fitted(painting, skeleton, masks["skin"], region, spec.cloth, style, light)
```

- 다리 사이를 가로지르는 치마는 몸 마스크를 행 단위로 메운 뒤 `fitted`에 전달
    + `wardrobe.bodycon`의 `_span_rows` 사용 방식 참조

## 인체 습작

- `dress=None`이면 해부 표지를 그림
    + 여성 정면은 쇄골, 가슴, 복부 중앙선과 옆선, 배꼽, 골반뼈, 서혜부 주름, 무릎, 발가락
    + 남성 정면은 위 "남성 인물" 항목 참조
    + 뒷모습은 척추선, 견갑, 허리 보조개, 둔부와 그 아래 주름, 오금
    + 표지는 `figure/anatomy.py`에 부위별 함수로 분리
- 그럴듯함을 결정하는 요소는 3가지
    + 골반과 어깨의 반대 기울기
    + 관절에서 가늘고 근육에서 굵은 윤곽
    + 빛 반대쪽 전체가 한 덩어리로 어두워지는 명암
- 미성년자의 누드와 성적 묘사는 그리지 않음 (`SKILL.md`의 금지 기준)
- 반신 구도가 발과 손의 약점을 가림
- 회화풍은 `finish(..., importance=masks["head"], detail=0.85)` 권장
    + 피부에 잔붓질이 과하면 `detail`을 낮춤

## 손

```python
from codepainter.figure import hand
hand.draw_hand(painting, wrist=(400, 700), angle=180, length=300, skin="#f4d6c0", style=style,
               pose=hand.HAND_POSES["point"], thumb_side=-1.0, view="back", forearm=0.6)
```

| 항목 | 의미 |
|---|---|
| `angle` | 손끝 방향, 0은 아래, 180은 위 |
| `length` | 손목에서 가운뎃손가락 끝까지 픽셀 길이 |
| `thumb_side` | 1.0은 아래로 향한 손 기준 화면 왼쪽에 엄지, -1.0은 반대 |
| `view` | `back`은 손등(손톱, 마디), `palm`은 손바닥(손금) |
| `forearm` | 함께 그릴 아래팔 길이, 손 길이 대비 |

- 준비된 포즈는 `relaxed`, `open`, `fist`, `point`, `peace`
- 직접 지정은 `hand.HandPose(curl=(검지, 중지, 약지, 소지), spread, thumb, thumb_curl)`
    + `curl` 0은 편 손가락, 1은 손바닥으로 완전히 접은 손가락
- 전신에서는 `draw_figure(..., hands={"l": hand.FIST, "r": hand.OPEN})`으로 손 포즈 지정

## 한계

- 시점은 정면부터 측면(90도)까지와 정면 뒷모습
    + 등 쪽 3/4(90도 초과 돌림)는 미지원
    + 앉기, 무릎 꿇기, 눕기는 프리셋 범위에서 지원 (`references/clothing-and-scenes.md`)
- 뒷모습의 머리는 뒤통수만 그림
    + 뒤돌아보는 얼굴은 미지원
- 손은 평면 손 리그를 팔 끝 방향에 맞춰 그림
    + 측면에서도 손바닥과 손가락이 정면형으로 보임, 물건을 쥔 손의 옆모습은 미지원
    + 관람자 쪽으로 뻗은 손은 길이만 짧아지고 폭은 유지
    + 머리 뒤로 올린 손(`arm_behind_head`, `arms_up`)은 머리, 목, 뒷머리에 가려짐
- 돌린 몸은 정사영, 내려다보는 각도는 `pitch`로 20도 안팎까지
    + 올려다보는 원근과 소실점 원근은 미지원
    + 머리 리그는 `pitch`를 따르지 않음
- 옷은 붙는 옷, 치마, 소매, 겹옷(셔츠와 재킷)까지, 자세에 따른 당김 주름은 미지원
- 발은 측면에서 뒤꿈치, 발등, 둥근 발끝으로 읽히는 길이(`FOOT_LENGTH_3D` 0.74)
    + 발가락 갈래와 발바닥 아치는 미표현
- 남성 체형은 마른 근육형 1종
    + 거구, 노년, 비만 체형은 `BodySpec` 수치와 `body.py` 상단 굵기 프로필 수정으로 대응
- 전신 구도에서 얼굴이 작아 회화풍은 이목구비가 뭉개짐
    + 얼굴이 중요하면 반신 구도 또는 `importance`를 높게 지정
