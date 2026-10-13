# 인물 리그

`scripts/codepainter/figure/`는 흉상 인물 1명을 매개변수로 그리는 2D 리그. 3D 모델을 쓰지 않고 정면 기준 배치를 고개 돌림에 맞춰 옆으로 미는 방식으로 동작한다.

## 호출

```python
from codepainter.figure import PortraitSpec, draw_portrait
masks = draw_portrait(painting, PortraitSpec(...), style, light=(-0.55, -0.62, 0.56))
```

- 배경을 먼저 그린 Painting 위에 호출
- 반환값은 `head`, `hair`, `body`, `eyes`, `figure` 마스크와 `frame`(HeadFrame)
    + `masks["head"]`는 회화풍 `finish`의 `importance`로 사용
    + `masks["figure"]`는 인물 전체 실루엣, 배경 효과를 인물 뒤로 제한할 때 사용

## PortraitSpec

| 항목 | 기본값 | 의미 |
|---|---|---|
| `crown` | (0.53, 0.115) | 정수리 위치, 캔버스 대비 비율 |
| `head_size` | 0.50 | 머리 높이 / 캔버스 높이 |
| `yaw` | -0.7 | 고개 돌림, -1은 화면 왼쪽 3/4 측면, 0은 정면, 1은 오른쪽 3/4 측면 (1 = 25도) |
| `turn_deg` | None | 고개 돌림(도), -90 - 90, 지정하면 `yaw` 대신 사용, 90은 옆얼굴 |
| `tilt` | 0.0 | 고개 기울임(도), 권장 범위 -8 - 8 |
| `jaw` | 0.85 | 턱선, 0은 둥근 달걀형, 1은 날카로운 V라인 |
| `eye_y` | 0.545 | 눈 높이(정수리 0, 턱 1), 낮출수록 성숙한 인상 |
| `eye_spacing` | 0.142 | 얼굴 중심선에서 눈 중심까지 거리 |
| `eye_size` | 1.18 | 눈 크기 배율 |
| `eye_open` | 1.0 | 눈 세로 폭, 1 미만은 가늘고 서늘한 눈매 |
| `eye_tilt` | 7.0 | 눈꼬리 올림(도) |
| `gaze` | None | 시선, None은 관람자 응시, -1 - 1은 좌우 |
| `smile` | 0.15 | 입꼬리 올림 |
| `lips` | 0.85 | 입술 색 강도, 0은 선만 표시 |
| `lashes` | 1.0 | 속눈썹 굵기, 0.6 미만이면 눈꼬리 속눈썹 생략 |
| `brow` | 1.0 | 눈썹 굵기, 클수록 낮고 곧은 눈썹 |
| `face_width` | 1.0 | 얼굴 폭, 0.9 좁고 길어 보임 - 1.1 넓고 둥글어 보임 |
| `cheek` | 0.0 | 광대, 1은 광대가 서고 그 아래가 들어감 |
| `nose` | 1.0 | 코 크기, 0.8 - 1.3 |
| `mouth` | 1.0 | 입 폭, 0.85 - 1.2 |
| `lip_full` | 1.0 | 입술 두께, 0.8 - 1.45 |
| `eye_shape` | "almond" | `almond`, `round`(둥근 눈), `droopy`(처진 눈), `sharp`(눈꼬리가 올라간 가는 눈) |
| `iris_size` | 1.0 | 홍채 크기, 0.8 작고 날카로움 - 1.15 크고 부드러움 |
| `brow_tilt` | 0.0 | 눈썹 기울기(도), 양수는 안쪽 끝이 올라감(걱정), 음수는 내려감(단호) |
| `brow_raise` | 0.0 | 눈썹 높이 이동(머리 단위) |
| `mouth_open` | 0.0 | 입 벌림, 0 - 1 |
| `eyes_closed` | None | `up`(웃으며 감은 눈), `down`(편안히 감은 눈) |
| `expression` | None | `smile`, `laugh`, `angry`, `sad`, `surprised` (얼굴 값 위에 덧씌움) |
| `glasses` | None | `round`, `square`, 테 색은 `glasses_color` |
| `earrings` | None | `stud`, `hoop`, `drop`, 색은 `jewel` |
| `stubble` | 0.0 | 턱과 인중의 수염 자국, 0 - 1 |
| `hat` | None | `beanie`(접은 단이 있는 니트 비니), 색은 `hat_color` |
| `hair_style` | "long" | `long`, `bob`, `short`(목덜미까지, 귀 노출), `wavy`, `ponytail`, `bun`, `two_block`, `slick` |
| `bangs` | "swept" | `swept`(옆가르마), `curtain`(가운데 가르마), `textured`(짧은 옆넘김 앞머리), `none`(앞머리 없이 넘김) |
| `outfit` | "turtleneck" | `turtleneck`, `blazer` |
| `skin`, `hair`, `eye`, `lip`, `cloth`, `cloth_second` | | 색, `cloth_second`는 블레이저 겉감 |
| `seed` | 7 | 머리카락 가닥과 하이라이트 배치 난수 |

### 인상 프리셋

```python
from codepainter.figure.frame import FACES
from codepainter.figure.palette import look

spec = PortraitSpec(**{**FACES["cool"], **look("tan", "black", "gray"), "hair_style": "ponytail", "expression": "smile"})
```

| 이름 | 인상 |
|---|---|
| `cool` | 날카로운 턱, 눈꼬리가 올라간 가는 눈, 작은 홍채, 작은 입 |
| `bright` | 둥근 얼굴, 크고 둥근 눈, 넓은 미소 |
| `gentle` | 처진 눈, 걱정스레 올라간 눈썹 안쪽, 옅은 미소 |
| `elegant` | 좁은 얼굴, 광대, 도톰한 입술, 가는 눈썹 |
| `sporty` | 굵고 곧은 눈썹, 넓은 입, 큰 웃음 |
| `sharp_man` | 브이라인 턱, 가는 눈, 내려간 눈썹 안쪽 |
| `soft_man` | 둥근 눈, 부드러운 턱, 옅은 미소 |
| `rugged_man` | 넓은 턱, 큰 코, 아주 굵은 눈썹, 수염 자국 |

- 프리셋, 색, 머리는 사전 병합(`{**a, **b}`)으로 합침
    + 같은 키는 뒤에 쓴 값이 이김, 키워드 인자로 나눠 넘기면 키가 겹쳐 오류
- 남성 프리셋은 `short` 머리와 `textured` 앞머리를 포함, 다른 머리는 병합 시 덮어씀
- 표정(`expression`)은 프리셋 값 위에 더하거나 곱해서 적용 (`frame.EXPRESSIONS`)
    + `laugh`는 웃으며 감은 눈과 벌린 입, `surprised`는 올라간 눈썹과 작게 벌린 입
    + 앞머리가 눈썹을 덮는 머리는 `angry`, `sad`가 약하게 보임, 앞머리 `textured`나 `none`과 함께 쓰면 잘 읽힘

### 헤어스타일

| 이름 | 정면 | 측면과 뒷모습 |
|---|---|---|
| `wavy` | 물결치는 긴 머리와 옆머리 | 같은 물결 |
| `ponytail` | 뒤로 넘겨 묶은 머리, 관자놀이 잔머리 | 뒤통수에서 등으로 늘어지는 꼬리와 머리끈(색은 `cloth`) |
| `bun` | 정수리 뒤로 똥머리가 보임 | 뒤통수 위의 둥근 똥머리 |
| `two_block` | 긴 윗머리가 짧게 친 옆머리 위로 뾰족하게 덮임 | 같은 구조, 짧은 부분은 피부가 비침 |
| `slick` | 앞머리 없이 뒤로 넘긴 짧은 머리 (`bangs="none"`과 함께) | 매끈한 뒤통수 |

- 머리 덩어리는 기본 컷 4종(`long`, `bob`, `short`, `tied`) 위에 각자의 부속을 더함 (`hair.STYLE_BASE`)
- 꼬리와 똥머리는 뒷머리 층에 그려져 정면에서는 머리 뒤로 숨음

### 색 팔레트

- `palette.look(skin, hair, eye, outfit)`이 색 필드 사전을 돌려줌
    + 이름 대신 `"#rrggbb"`도 허용, 입술은 피부에 맞는 색이 자동 선택
    + `lipstick="#c0304a"`로 입술 색을 섞음
- 피부 7단계 : `porcelain`, `fair`, `light`, `olive`, `tan`, `brown`, `deep`
    + 볼 홍조, 그림자 경계의 붉은 기, 피부 하이라이트가 피부 명도에 맞춰 함께 이동
- 머리색 : 현실 8종(`black`, `dark_brown`, `brown`, `chestnut`, `auburn`, `blonde`, `platinum`, `gray`), 애니메 6종(`pink`, `sky`, `silver`, `lavender`, `mint`, `crimson`)
- 눈동자 : 현실 6종(`brown`, `amber`, `hazel`, `green`, `blue`, `gray`), 애니메 4종(`red`, `violet`, `gold`, `teal`)
- 의상 배색 8종 : `classic`, `warm`, `earth`, `pastel`, `sea`, `mono`, `denim`, `doomer` (`cloth`, `cloth_second` 순서)

### 인상 조절

- 성숙한 인상은 `eye_y` 0.52-0.55, `eye_open` 0.85-1.0, `jaw` 0.8-1.0
- 어려 보이는 인상은 `eye_y` 0.57-0.60, `eye_open` 1.2-1.4, `eye_size` 1.3, `jaw` 0-0.4
- 남성 얼굴은 `PortraitSpec(**frame.MASCULINE, ...)`
    + 넓은 턱, 작고 가는 눈, 굵은 눈썹, 옅은 속눈썹, 무채색 입술, `short` 머리와 `textured` 앞머리
- 3/4 측면(`yaw` 절댓값 0.6-0.8)이 턱선을 가장 잘 보여줌
- 25도를 넘는 돌림은 `turn_deg`로 지정
    + 25도에서 90도 사이는 3/4 키와 옆얼굴 키를 보간
    + 이마-눈썹뼈-콧등 오목-코-입술-턱 중심선이 머리 윤곽에 합쳐져 옆얼굴 실루엣을 만듦
    + 턱 아랫선은 턱끝에서 귀 아래 턱각까지 비스듬히 올라가고 턱각 뒤는 목으로 이어져 외곽선이 없음
    + 56도를 넘으면 먼 쪽 눈과 눈썹, 먼 쪽 앞머리를 숨김
    + 가까운 눈은 옆얼굴 전용 쐐기 형태로 바뀌고 홍채는 세로로 좁아져 앞쪽(각막 쪽)으로 이동
    + 귀는 작아지고 뒤로 기울며 머리카락은 귀 바로 뒤를 돌아 목덜미까지 내려감
    + 긴 머리와 단발은 가까운 쪽 옆머리가 귀 뒤에서 목덜미 앞으로 흘러내려 뒤통수와 목덜미를 덮음
    + 먼 쪽 옆머리는 뒷머리와 함께 얼굴 뒤로 그려져 얼굴에 가려짐
    + 흉상 목은 옆얼굴로 갈수록 앞뒤로 두꺼워져 턱 아래에서 시작

### 옆얼굴 비례 (90도, 머리 단위, 얼굴 쪽 +x)

| 부위 | 위치 (x, y) |
|---|---|
| 이마 | (0.39, 0.36) |
| 눈썹뼈 | (0.42, 0.44) |
| 콧등 뿌리 오목 | (0.41, 0.49) |
| 코끝 | (0.51, 0.695) |
| 턱끝 | (0.43, 0.93) |
| 턱각 | (-0.06, 0.85) |
| 목덜미 | (-0.30, 0.80) |
| 귀 | x -0.02 - -0.16 (위쪽이 뒤로 기울어짐), 높이 0.49-0.71 |

- 수치를 바꾸려면 `frame.py`의 `PROFILE_CONTOUR`(외곽 22점, 9-10번은 턱끝 위)와 `MIDLINE`(높이, 돌출량) 수정
- 옆얼굴 눈과 귀 형태는 `face.py`의 `UPPER_LID_PROFILE`, `LOWER_LID_PROFILE`, `EAR_SHAPE_PROFILE`

## 좌표계

- 머리 단위는 정수리 y=0, 턱끝 y=1, 길이 1은 머리 높이
- `frame.face(points, lift)`는 정면 얼굴 평면 좌표를 픽셀로 변환
    + x는 얼굴 중심선 기준, 고개를 돌리면 자동으로 밀리고 좁아짐
    + `lift`는 튀어나온 정도, 코끝 0.1, 입술 0.03, 안경 0.05
- `frame.place(points)`는 머리 기준 좌표를 픽셀로 변환
    + 머리 옆과 뒤에 붙는 요소(귀걸이, 옆머리, 모자)에 사용
- `frame.px(units)`는 머리 단위 길이를 픽셀로 변환
- 두 좌표 모두 x 양수가 얼굴이 향한 반대편 먼 쪽
    + `yaw`가 음수이면 결과 전체가 좌우 반전

| 부위 | 얼굴 평면 좌표 (x, y) |
|---|---|
| 눈 중심 | (±eye_spacing, eye_y) |
| 눈썹 | (±0.06 - ±0.26, eye_y - 0.10) |
| 코끝 | (0, 0.70), lift 0.105 |
| 입 | (0, 0.826), lift 0.03 |
| 턱끝 | (0, 1.0) |
| 귓불 | `frame.place([(-0.32, 0.73)])` (가까운 쪽) |

## 소품 추가

`draw_portrait` 호출 뒤에 같은 Painting에 이어서 그린다.

```python
frame = masks["frame"]
ink = "#2a1c24"
for side in (1.0, -1.0):                                   # 안경
    center = (side * spec.eye_spacing, spec.eye_y + 0.01)
    rim = frame.face(geo.ellipse(center, 0.10, 0.075), lift=0.05)
    painting.fill(painting.mask(rim), "#ffffff", 0.12)     # 렌즈 반사
    painting.outline(rim, frame.px(0.009), ink, contrast=0.2)
bridge = frame.face([(-0.045, spec.eye_y - 0.01), (0.045, spec.eye_y - 0.01)], lift=0.06)
painting.stroke(bridge, frame.px(0.008), ink, taper=(0.0, 0.0))

lobe = frame.place([(-0.315, 0.76)])[0]                    # 귀걸이
drop = geo.ellipse(lobe + [0, frame.px(0.05)], frame.px(0.018), frame.px(0.03))
painting.part(painting.mask(drop), "#e8c46a")
```

- 안경, 귀걸이, 수염 자국, 비니는 `PortraitSpec` 값으로 바로 지정 (`figure/accessories.py`)
    + 위 예시는 그 밖의 소품을 직접 그리는 방법
- 비니(`hat="beanie"`)는 머리 둘레의 고리를 접은 단 아랫선으로 삼아 정면, 3/4, 측면, 뒷모습에서 함께 돌아감
    + 단 아랫선은 이마에서 머리 단위 0.30, 뒤통수에서 0.50 (`accessories.HAT_BAND`)
    + 단 위의 머리카락은 모두 덮고 단 아래 앞머리, 옆머리, 꼬리는 그대로 보임
    + 모자를 쓰면 머리 부피가 `hair.HAT_PRESSED` 배로 눌려 정수리 위로 삐져나오는 가닥이 없음
    + 검은 머리에 검은 비니는 머리 모양처럼 읽히므로 `hat_color`를 머리보다 1단 밝게 지정
- 머리카락보다 뒤에 있어야 하는 소품은 `figure/portrait.py`의 조립 순서에 맞춰 직접 삽입
    + 조립 순서는 뒷머리(꼬리, 똥머리 포함), 몸, 옷, 귀, 얼굴, 수염 자국, 이목구비, 귀걸이, 앞머리, 비니, 안경

## 헤어 변형

```python
from codepainter.figure import HeadFrame, hair
frame = HeadFrame(spec, painting.shape)
plan = hair.plan_hair(frame, spec)
a, b, t = frame.place([(0.30, 0.20), (0.40, 0.34), (0.52, 1.35)])      # 먼 쪽으로 흘러내린 긴 옆머리 추가
plan.locks.insert(0, geo.lock(a, b, t, bend=-0.08 * frame.side, belly=0.2))
masks = draw_portrait(painting, spec, style, hair_plan=plan)
```

- `plan.locks`는 뒤에서 앞 순서의 뭉치 목록, 각 뭉치는 `geo.lock` 결과
    + 목록 앞쪽에 넣으면 다른 뭉치 뒤에, 뒤쪽에 넣으면 맨 앞에 그려짐
- `plan.back`은 뒷머리 실루엣 닫힌 곡선, 통째로 교체 가능
- `bend`에는 `frame.side`를 곱해야 좌우 반전 시 방향이 유지됨
- 새 헤어스타일 전체는 `figure/hair.py`의 `STYLE_BASE`에 기본 컷을 등록하고 `_back_sides`, `_bang_defs`, `_plan_knots`에 분기 추가

## 의상 추가

```python
from codepainter.figure import outfit

def draw_tee(painting, frame, spec, style, light, head):
    points = outfit.shoulder_side(1.0, 0.02) + outfit.shoulder_side(-1.0, 0.02)[::-1]
    curve = geo.smooth(outfit.body_points(frame, points), closed=True, corners=(0, 5, 6, 11))
    return paint_part(painting, curve, spec.cloth, style, light, line_width=frame.px(0.006), bevel=frame.px(0.26))

outfit.OUTFITS["tee"] = draw_tee          # 이후 PortraitSpec(outfit="tee") 사용 가능
```

- 의상 함수는 그린 영역의 마스크를 반환
- `outfit.body_points`는 몸통 좌표(좌우 대칭, 머리 단위)를 픽셀로 변환하며 상체 돌림을 반영

## 한계

- 머리는 정면에서 옆얼굴(90도)까지 지원
    + 흉상 의상(터틀넥, 블레이저)의 몸통은 3/4까지만 돌아감, 옆얼굴 흉상은 몸통이 정면에 가깝게 남음
    + 블레이저 깃은 정면형으로 남아 옆얼굴 흉상에서는 목과 깃이 따로 놀 수 있음, 옆얼굴 흉상은 터틀넥 권장
    + 뒷모습 머리는 전신 리그의 `view="back"`에서 지원
- 귀를 드러내는 묶음머리는 미포함
    + 필요 시 기본 도형으로 직접 구성하고 검증 반복을 늘림
- 전신과 손은 `references/figure-body.md`의 전신 리그 사용
- 위아래 고개 각도(끄덕임)는 미지원
