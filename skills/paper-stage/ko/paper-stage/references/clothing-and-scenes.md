# 의상, 자세, 투샷, 장면

전신 리그(`references/figure-body.md`) 위에 얹는 4개 층. 겹옷과 소매(`figure/clothing.py`), 앉기와 눕기 같은 비입식 자세(`figure/body.py`), 가구(`figure/props.py`), 여러 인물과 구도(`figure/stage.py`), 장면 배경(`codepainter/sets.py`).

## 의상

### 목록

`wardrobe.WARDROBE[이름]` 또는 `clothing.<상수>`로 사용.

| 이름 | 내용 | 사용 색 |
|---|---|---|
| `innerwear` | 하프컵 브라(컵 위 레이스, 가운데 심, 밑밴드, 어깨끈), 레이스 팬티와 리본 | `cloth` |
| `innerwear_stockings` | 위 구성에 비치는 허벅지 스타킹과 레이스 밴드 추가 | `cloth` |
| `crop_top_shorts` | 크롭 반팔 티, 로우라이즈 데님 핫팬츠(올 풀린 밑단), 운동화 | `cloth`, `cloth_second` |
| `hoodie` | 오버핏 후드티(뒤로 접힌 후드, 앞주머니, 끈, 시보리 소매와 밑단), 청바지, 운동화 | `cloth`, `cloth_second` |
| `hoodie_shorts` | 후드티와 핫팬츠, 운동화 | `cloth`, `cloth_second` |
| `suit` | 정장 바지(주름선), 셔츠와 칼라, 넥타이, 싱글 재킷(노치 라펠, 단추 2개, 주머니 덮개), 셔츠 소매 끝, 구두 | `cloth` |

- 남녀 모두 착용 가능, 체형 차이는 몸 마스크에서 자동 반영
- 0도, 45도, 90도와 앉기, 눕기에서 검증

### 조합

```python
from codepainter.figure import clothing, wardrobe

outfit = clothing.combine(wardrobe.jeans, clothing.sneakers, clothing.HOODIE)      # 그리는 순서대로 나열
dress_shirt = clothing.combine(clothing.suit_trousers, clothing.dress_shoes, clothing.shirt, clothing.tie)
draw_figure(painting, spec, body, pose, style, dress=outfit)
```

- `Outfit(body, sleeve, behind)` 3개 층
    + `body`는 몸통과 다리 위 옷, 앞팔보다 먼저 그림
    + `sleeve`는 팔을 그린 직후 그 팔 위에 그림, 형식 `f(painting, skeleton, side, masks, spec, style, light)`
    + `behind`는 뒷머리 직후 몸통보다 먼저 그림 (접힌 후드)
- 일반 함수 의상도 그대로 사용 가능, `combine`이 Outfit으로 감쌈
- 부품 함수는 `crop_tee`, `hot_pants`, `hoodie_body`, `hood`, `shirt`, `tie`, `jacket`, `suit_trousers`, `bra`, `briefs`, `stockings`, `sneakers`, `dress_shoes`

### 소매

```python
def blouse_sleeve(painting, skeleton, side, masks, spec, style, light):
    return clothing.draw_sleeve(painting, skeleton, side, masks, spec.cloth, style, light,
                                reach=1.6, ease=clothing.SLEEVE_EASE["loose"], cuff=(0.12, "#ffffff"))
```

| 인자 | 의미 |
|---|---|
| `reach` | 소매 끝 위치, 0 어깨, 1 팔꿈치, 2 손목 (반팔 0.42, 긴팔 1.9-1.97) |
| `ease` | 팔과의 여유(머리 높이), `fitted` 0.015, `tailored` 0.035, `loose` 0.045 |
| `cuff` | (길이, 색) 소매 끝을 손목으로 조이는 시보리 띠 |
| `under` | (길이, 색) 소매 밖으로 나오는 셔츠 소매 끝 |

- 어깨에서는 여유 없이 붙고 위팔 절반까지 여유가 커짐 (`SHOULDER_SNUG`)
    + 어깨부터 여유를 주면 퍼프 소매처럼 부풂
- 몸판과 만나는 곳의 선은 옅은 솔기로 남김 (`SEAM_OPACITY`)

### 몸판 설계 요령

- `wardrobe.fitted(..., ease, drape, cut)` 확장 인자
    + `drape`는 겨드랑이 아래 넓은 부분에서 천이 떨어지는 길이, 떨어지며 몸 쪽으로 돌아옴 (`DRAPE_PULL`)
    + 후드티 0.95, 재킷 0.6, 셔츠 0.3, 크롭티 0.35
    + `ease`는 어깨에서 0, 겨드랑이부터 최대, 어깨 패드처럼 솟지 않음
    + `cut`은 재킷 앞 트임처럼 옷에서 빼는 영역, 명암은 뚫리기 전 전체 형태로 계산
- 돌린 몸 위의 다각형(라펠, 넥타이, 앞 트임)은 `clothing._on_surface`로 변마다 점을 채워 배치
    + 꼭짓점만 감싸면 직선 변이 몸의 회전을 가로질러 가까운 쪽 라펠이 납작해짐
- 레이스는 `clothing.lace_edge(painting, skeleton, 경계선, color, style, clip, toward, depth)`
    + 비치는 띠, 바깥 가장자리의 반원 무늬, 망사 점, 박음선 순서
    + `toward`는 띠가 뻗는 방향, 누운 몸에서는 `clothing._turned`로 몸 기울기만큼 회전
- 정장 바지 다리는 `clothing.trouser_legs`로 무릎 폭을 발목까지 유지
    + 몸에 붙는 바지는 종아리를 따라가며 발목에서 오므라듦
- 돌린 몸의 바지와 반바지는 `wardrobe.leg_split`이 가까운 다리 윤곽을 천 안에 그림
    + 이 선이 없으면 45도에서 반바지가 치마처럼 보임
- 정면으로 앉은 정장 바지는 두 종아리가 붙어 한 덩어리가 되므로 왼쪽 다리 안쪽 선을 천 안에 그림 (`clothing._divide_trouser_legs`)
- 브라 어깨끈은 앞쪽 팔에 처음 가려지는 지점에서 끝냄
    + 측면에서 팔 위로 끈 끝만 떠 보이는 조각을 막음
- 접힌 후드는 어깨 위에 얹혀 목 절반 높이까지만 올라옴 (`HOOD_RINGS`)
    + 뒷모습에서는 등 위에 덮어 그림
- 엉덩이까지 오는 상의(후드티, 재킷)는 앉으면 허벅지 앞쪽 일부만 덮음 (`clothing.SEATED_TOP_LAP`)
- 뒷모습에서는 주머니, 끈, 넥타이, 라펠, 단추처럼 몸 앞면에 붙은 요소를 그리지 않음
    + 상의 목선은 뒷목 높이로 올라감 (`BACK_NECKLINE`)

## 앉기, 무릎 꿇기, 눕기

### 프리셋

| 이름 | 내용 |
|---|---|
| `sit_side` | 의자에 앉은 측면, 허벅지 수평, 정강이 수직, 손은 무릎 위 |
| `sit` | 같은 자세의 3/4 (`yaw=35`) |
| `sit_front` | 정면 앉기, 카메라가 20도 내려다봄 (`pitch=20`), 손은 무릎 위 |
| `kneel_side`, `kneel` | 무릎 꿇고 상체를 세움, 정강이와 발등이 바닥에 닿음, `kneel`의 손은 허벅지 바깥 옆 |
| `seiza` | 발뒤꿈치 위에 앉은 측면 |
| `lie_back` | 등을 대고 누운 측면 (`yaw=90, lean=-90`), 한쪽 무릎 세움, 두 발은 침대 위 |
| `lie_side` | 옆으로 누워 관람자를 향함 (`lean=90`), 위쪽 다리가 아래 다리 위에 놓임 |

### 동작 원리

- `swing["thigh_x"]`가 35-75도를 지나면 앉은 자세로 판정 (`skeleton.seated`)
    + 앉은 자세는 몸통 아래를 의자면(`SEAT_DROP` 0.36)에서 평평하게 자름
    + 몸통 바닥이 다리 사이로 늘어지면 의자 아래로 엉덩이가 처져 보임
- `Pose.ground`는 몸이 닿는 면까지 화면 아래 방향 거리(머리 높이)
    + 의자, 침대, 바닥 위 몸통과 둔부가 그 선에서 납작해짐
    + 옆으로 누운 몸은 골반 반폭과 비슷한 값(0.66)이면 골반과 어깨가 닿고 허리가 뜸
- `Pose.pitch`는 카메라가 내려다보는 각도(도)
    + 관람자 쪽으로 뻗은 허벅지가 짧게나마 화면에 드러남
    + 정면 앉기는 정강이를 먼저, 허벅지를 그 위에 그려 무릎 끝이 정강이 위를 덮음
- 발 방향은 `swing["foot_x"]`로 직접 지정 가능
    + 0 아래, 90 앞, -90 뒤, 무릎 꿇기는 -84 안팎(발등이 바닥에)
- 누운 몸의 가슴은 화면 아래(중력) 쪽으로 처짐 (`anatomy.LYING_SAG`)
    + 등을 대고 누우면 가슴 볼륨이 흉곽 쪽으로 가라앉음 (`LYING_FLATTEN`)
    + `lean`이 30도 미만이면 기존 계산 그대로 유지

### 앉은 자세의 옷

- 다리 트임이 골반 높이 기준이면 앞으로 뻗은 허벅지를 전부 덮음
    + 앉은 자세는 `wardrobe.bottom_region`이 허벅지를 따라 일정 길이에서 자름
    + 핫팬츠 0.62, 팬티 0.16, 비키니와 수영복 0.12, 남성 트렁크 0.55 (고관절에서 허벅지 방향 머리 높이)
- 치마는 `wardrobe.seated_skirt`
    + 엉덩이와 허벅지 위로 덮고 두 허벅지 사이 틈을 메운 뒤 무릎 앞에서 아래로 늘어뜨림
- 새 하의 함수는 다리 트임을 `bottom_region(painting, skeleton, masks, 위선, 밑단선, 길이)`로 만들면 앉은 자세를 자동 지원

## 가구

```python
from codepainter.figure import props
from codepainter.figure.body import Skeleton

skeleton = Skeleton(pose, body, painting.shape)
chair = props.chair(skeleton, color="#6b4a33", cushion="#a8786a")
back = props.draw(painting, skeleton, chair, style)                     # 인물 뒤
masks = draw_figure(painting, spec, body, pose, style, dress=dress)
props.contact_shadows(painting, skeleton, masks["figure"], back, style)  # 닿는 곳 그림자
props.draw(painting, skeleton, chair, style, layer="front")             # 인물 앞으로 나오는 다리
props.floor_shadow(painting, skeleton, [masks["limbs"]["leg_l"], masks["limbs"]["leg_r"], back], style)
```

- 가구는 인물과 같은 3D 공간의 상자(`props.Box`)로 구성
    + 인물의 몸 돌림과 카메라 각도를 따르고 몸 기울기는 무시, 침대는 화면에서 수평 유지
    + 보이는 면만 면 방향 명암으로 칠함, `soft=True`인 쿠션과 매트리스는 부풀린 명암
- `props.chair(skeleton)`은 앉은 몸의 의자면 높이와 발 위치에 맞춰 생성
- `props.bed(skeleton)`은 누운 몸의 머리와 발 사이 길이로 생성, 베개는 머리 쪽
    + 침대 바닥까지 높이는 `props.BED_HEIGHT`
- `props.table(skeleton, reach=None, half=None)`은 앉은 몸 앞의 작은 카페 탁자 (정사각 상판, 기둥 1개, 바닥판)
    + 상판은 의자면보다 `props.TABLE["height"]` 위, 배꼽 높이
    + `reach`는 골반 중심에서 탁자 가운데까지 바라보는 방향 거리, 기본은 무릎 바로 앞
    + 마주 앉은 두 사람은 탁자를 한 사람에게만 주고 `reach`를 두 사람 거리의 절반으로 지정

```python
sa, sb = Skeleton(a.pose, a.body, shape), Skeleton(b.pose, b.body, shape)     # a는 오른쪽, b는 왼쪽을 바라봄
a.props = [props.chair(sa), props.table(sa, reach=(sb.origin[0] - sa.origin[0]) / 2 / sa.unit, half=1.0)]
b.props = [props.chair(sb)]
```

## 구도와 투샷

### 구도 프리셋

```python
from codepainter.figure.stage import frame

(pose,) = frame([(pose, body)], painting.shape, "waist")                       # full | knee | waist | bust
her_pose, his_pose = frame([(her_pose, BodySpec()), (his_pose, MALE_BODY)], painting.shape, "knee", centers=(0.38, 0.64))
```

- `root`와 `unit`을 계산해 지정한 컷이 캔버스에 맞도록 배치
    + `full` 발 아래, `knee` 무릎 아래, `waist` 허벅지 위, `bust` 가슴 아래에서 자름
    + 여러 인물은 같은 바닥 위에 서고 같은 크기 단위를 공유, 키 차이는 그대로 드러남
- `full`은 손발까지 각자 칸에 들어가게, 가까운 컷은 어깨폭만 맞추고 서로 겹침 (`overlap`)
- `floor`(픽셀 행)를 주면 배경 바닥선 위에 세움
    + 잔디나 바닥에 누운 인물은 `floor`를 바닥 앞쪽(캔버스 높이의 0.85-0.9)으로 주어야 지평선 위에 뜨지 않음

### 손 뻗기

```python
from codepainter.figure.stage import reach

his_pose = reach(his_pose, MALE_BODY, "l", target_pixel, painting.shape, depth=0.9)
```

- 위팔과 아래팔 각도, 앞뒤 흔들림을 2관절 역운동학으로 계산
    + `target`은 캔버스 픽셀, `depth`는 그 점이 그 인물 기준 관람자 쪽으로 나온 거리
    + 기본은 손바닥 중심을 목표에 맞춤 (`palm=True`), 닿지 않으면 팔을 끝까지 뻗음
    + 팔꿈치 방향은 `pole`(기본은 바깥, 아래, 뒤)
- `rest_hands(pose, body, shape, on="knees")`는 양손을 무릎(`"thighs"`는 허벅지 가운데) 위에 얹음
    + 어깨폭이 다른 체형에서도 앉은 손이 무릎에 닿음
    + 정면에 가까운 착석(22도 이하)은 손을 무릎 바깥으로 `stage.REST_OUTWARD`만큼 옮김, 두 손이 골반 앞쪽 위에서 겹치지 않음
- 정면 착석은 허벅지가 짧게 보여 선 자세처럼 읽히기 쉬움
    + 무릎 아래 정강이에 허벅지와 의자면 그림자를 자동으로 칠함 (`body.shade_under_knees`)
    + 확실하게 앉은 자세로 읽히려면 `yaw=15`에서 `20`, 남성은 무릎을 벌림 (`leg_l=(-14, -6), leg_r=(14, 6)`)
- 다른 인물의 관절 위치는 `Skeleton(그 인물 pose, body, shape).joints[...]`에서 얻음
    + 어깨 위는 `joints["shoulder_r"] - [0, 0.14 * skeleton.unit]`

### 여러 인물 그리기

```python
from codepainter.figure.stage import Actor, draw_actors, floor_shadows

her = Actor(spec_a, BodySpec(), her_pose, WARDROBE["suit"], depth=0.0, props=[chair])
him = Actor(spec_b, MALE_BODY, his_pose, WARDROBE["suit"], depth=-0.9, over=("hand_l",))
figures = draw_actors(painting, [her, him], style)
floor_shadows(painting, [her, him], style, color="#30353c")
```

- `depth`가 작은(먼) 인물부터 그림
    + 가까운 인물을 그린 직후 그 그림자를 먼 인물 위에 떨어뜨림
- `over`에 적은 부위는 모든 인물을 그린 뒤 다시 덮어 그림
    + 뒤에 선 사람의 손이 앞사람 어깨나 팔 위에 얹히는 장면
    + 이름은 `hand_l`, `hand_r`, `arm_l`, `arm_r`
    + 덮어 그리는 손은 팔이 보이는 쪽 손을 사용, 팔이 앞사람 뒤로 숨은 손은 손만 떠 보임
    + 그런 손이면 `draw_actors`가 경고를 냄, 반대쪽 손으로 잡거나 `reach(..., pole=...)`로 팔꿈치를 앞으로 보냄
- 반환값은 모든 인물 마스크의 합, 장면 조명(`sets.light_figures`)에 사용
- `draw_figure` 마스크에 `hands`(좌우 손 마스크) 추가

## 장면 배경

```python
from codepainter import sets

info = sets.SETS["night_street"](painting, style)        # beach | bedroom | office | night_street | cafe | park | panel_block
figures = draw_actors(painting, actors, style)
sets.light_figures(painting, figures, info, style)       # 장면의 주변광과 테두리 빛
image = fx.grade(finish(painting, style), **info.grade)
```

| 이름 | 내용 | 조명 |
|---|---|---|
| `beach` | 하늘과 구름, 곶, 반짝이는 바다, 파도선, 젖은 모래 | 한낮, 보정 없음 |
| `bedroom` | 회벽, 창빛 무늬, 커튼, 나무 바닥, 걸레받이 | 따뜻한 주변광과 오른쪽 테두리 빛 |
| `office` | 통유리 너머 빌딩, 창틀, 화분, 회색 카펫 | 차가운 한낮 |
| `night_street` | 밤하늘, 불 켜진 창, 가로등, 상점 불빛, 젖은 도로 반사, 빛망울 | 보랏빛 주변광과 주황 테두리 빛 |
| `cafe` | 크림색 벽, 도시가 보이는 창, 나무 징두리 벽, 펜던트 조명, 타일 바닥 | 따뜻한 주변광과 노란 테두리 빛 |
| `park` | 하늘과 구름, 나무 두 줄, 잔디, 산책로, 풀잎 | 한낮, 보정 없음 |
| `panel_block` | 흐린 하늘, 패널 아파트 3동, 앙상한 나무, 전깃줄, 나트륨 가로등, 눈과 진창 | 차가운 주변광과 가로등 쪽 주황 테두리 빛, 마무리는 `fx.doomer` |

- `panel_block(painting, style, lamp=0.82, lit=0.22)`의 `lamp`는 가로등의 가로 위치(폭 비율), 인물 테두리 빛도 그쪽에서 옴
    + 내리는 눈은 인물을 그린 뒤 `scenery.snowfall(painting, count, keep_clear=얼굴 마스크)`로 추가
- `SetInfo`는 바닥선(`horizon`), 바닥 그림자 색(`ground`), 색 보정(`grade`), 주변광(`ambient`), 테두리 빛(`rim`)
    + 테두리 빛 폭은 캔버스 높이의 `sets.RIM_WIDTH`, 애니메풍에서도 약간 번지게 하여 외곽선처럼 보이지 않게 함
- 완성 예제는 `examples/scene.py --scene beach|bedroom|office|night_street|cafe|park`

## 한계

- 사진 원근 없이 정사영, 인물 사이 깊이는 그리는 순서와 그림자로만 표현
    + 멀리 선 인물을 작게 그리려면 `unit`을 직접 줄임
- 팔을 감아 안기, 깍지 낀 손처럼 두 몸이 서로 감기는 접촉은 미지원
    + `over`는 손과 팔 단위 덮어쓰기만 지원
- 앉은 정면은 무릎이 관람자 쪽으로 단축되어 의자와 손 위치가 있어야 앉은 자세로 읽힘
- 누운 자세의 긴 머리는 바닥 쪽으로 처지고 짧게 모이는 근사만 지원 (`hair.GRAVITY_SHARE`, `LYING_LENGTH`)
    + 침대 면 위로 부채꼴로 퍼지는 표현은 미지원
- 엎드린 자세, 쪼그려 앉기, 다리 꼬기는 프리셋 없음
    + `swing`과 `ground`로 직접 구성 가능하나 검증 반복 필요
- 옷 주름은 고정 위치의 몇 줄, 자세에 따른 당김 주름은 미지원
