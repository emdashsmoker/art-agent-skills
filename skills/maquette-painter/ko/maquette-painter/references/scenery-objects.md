# 풍경, 배경, 사물

## 목차
- 풍경 구성 원리
- scenery 함수
- 날씨와 젖은 바닥
- 원근 구성 (Perspective)
- 실내 (room, chair)
- 도시 (city)
- 정물 (objects)
- 현대 사물 (props)
- 커스텀 대상 (Sculpture)
- 장면 구성 요령

## 풍경 구성 원리

- 뒤에서 앞으로 겹쳐 그림: 하늘, 구름, 원경 산, 중경 산과 언덕, 수면, 근경
- 각 요소의 `depth`(1 멀리, 0 가까이)가 공기 원근을 결정
    + `Light`의 `haze`, `haze_strength`가 depth에 비례하여 원경을 흐리게 함
    + 수채 화풍은 depth 0.75 이상의 층을 번지기 기법으로 처리
- 가까울수록 명도 대비와 채도를 높이고 형태를 크게 배치
- 모든 함수는 `seed` 인자로 형태를 고정 (같은 시드는 같은 결과)

## scenery 함수

| 함수 | 용도 |
|---|---|
| `sky(canvas, zenith, horizon, horizon_y, glow=(x, y, r))` | 그라데이션 하늘, glow는 해와 달의 빛무리 |
| `sun(canvas, x, y, radius)` | 해, 달 원반 |
| `clouds(canvas, cover, y0, y1, color, shadow, wispy, volume)` | 구름층, cover 0-1, wispy는 납작한 정도, volume은 조명을 받는 입체 정도 (0 평면) |
| `stars(canvas, count, y1)` | 밤하늘 별 |
| `mountains(canvas, base_y, peak, color, depth, roughness, snow, facets, forest, shape)` | 산맥 (아래 설명) |
| `hills(canvas, base_y, rise, color, depth)` | 완만한 언덕과 근경 지면 |
| `ground(canvas, y, color, far_color)` | 평평한 지면 |
| `water(canvas, y0, y1, color, reflect, ripples, light, glitter)` | 수면, 이미 그려진 위쪽 풍경을 반사 |
| `treeline(canvas, base_y, height, color, depth)` | 원경 숲 실루엣 |
| `conifer(canvas, x, base_y, height, snow)` | 침엽수 1그루, snow 0-1은 가지마다 쌓인 눈 |
| `broadleaf(canvas, x, base_y, height, spread, density)` | 활엽수 1그루, density 2-3은 작은 잎 덩어리가 촘촘한 수관 (꽃나무, 가까운 큰 나무) |
| `bare_tree(canvas, x, base_y, height, birch, spread, lean)` | 잎 없는 겨울나무 1그루, birch=True는 흰 껍질에 검은 무늬가 있는 자작나무 |
| `grass(canvas, y0, y1, color, density)` | 근경 풀 |
| `flowers(canvas, y0, y1, colors, count)` | 들꽃 |
| `rock(canvas, x, y, width, height)` | 바위 |
| `skyline(canvas, base_y, height, color, lit)` | 원경 도시 실루엣, lit은 불 켜진 창 색 |
| `contact_shadow(canvas, x, y, width)` | 바닥 접지 그림자 |
| `weather(canvas, kind, amount, near, wind)` | 비, 눈, 꽃잎이 내리는 층 1개 (아래 설명) |
| `wet_reflection(canvas, ground, light)` | 젖은 노면, 젖은 모래, 물 고인 바닥의 반사 (아래 설명) |

- `mountains`
    + 능선은 날카로운 봉우리와 안부를 만드는 노이즈, 산면은 경사 방향으로 늘인 노이즈로 깎아 능선과 계곡이 정상에서 흘러내림
    + 조명이 밝은 면과 그늘진 사면을 만들고 계곡에는 그늘이 고임
    + `snow=y`: 그 높이 위의 위를 향한 사면에만 눈, 가파른 암벽은 드러남
    + `forest=y`: 그 높이 아래 사면을 `forest_color` 숲으로 덮음
    + `shape="rounded"`: 수묵 산수의 둥근 봉우리 (기본 alpine)
- `water`는 호출 시점까지 그려진 그림을 반사하므로 수면 위 요소를 모두 그린 뒤 호출
    + `light=light`를 넘기면 명암이 들어간 풍경이 반사됨 (권장)
    + 잔물결은 멀수록 가늘고 촘촘하며 가까울수록 넓고 강함, 가까운 수면일수록 반사가 줄고 물빛이 드러남
    + `glitter=(x, 폭)`: 해 아래의 반짝이는 물길
- `conifer`는 처진 가지 여러 겹과 들쭉날쭉한 잔가지, `broadleaf`는 잎 덩어리 70여 개로 수관을 만들어 틈으로 하늘이 보임
- `treeline`은 높이와 색이 조금씩 다른 첨탑형과 둥근 수관이 섞인 숲 가장자리
- `bare_tree`는 줄기에서 굵은 가지, 굵은 가지에서 잔가지로 5단계까지 갈라짐
    + 잔가지 전체를 마스크 1장으로 그리므로 원경 숲에 수십 그루를 심어도 가벼움 (`doomer_landscape.py`의 자작나무 띠)
    + 원근 장면에서는 `camera.point`로 밑동 위치를, `camera.scale`로 높이를 화면 단위로 바꾸어 넘김
- 안개는 배경색을 `canvas.tint(마스크, 색, alpha)`로 덧칠 (`landscape_ink.py` 참조)
- 시간대는 하늘색과 조명 프리셋의 조합으로 표현

| 시간대 | 하늘 (zenith, horizon) | 조명 |
|---|---|---|
| 한낮 | #4f86c6, #d6e6f2 | noon |
| 황금 시간대 | #4a7fc0, #f3dfc2 | golden_hour |
| 해 질 녘 | #2f3a68, #f0a070 | golden_hour (elevation 8) |
| 블루 아워 | #1f2a58, #6f7fb8 | blue_hour |
| 밤 | #0d1530, #39406e | night |
| 흐린 날 | #9aa6b4, #d5dbe2 | overcast |

## 날씨와 젖은 바닥

- `weather(canvas, kind, amount=1, near=0.3, wind=0.18)`: kind는 rain, snow, petals
    + near 0은 먼 층(가늘고 촘촘하고 또렷함), 1은 렌즈 바로 앞 층(크고 성기고 흐림)
    + 인물보다 먼저 near 0.1-0.2로 1회, 인물 다음에 near 0.7-0.8로 1회 호출하면 깊이가 생김
    + wind는 낙하 1단위당 옆 흐름 (빗줄기 기울기, 꽃잎 회전 방향)
    + crisp=True는 매체 위에 또렷하게 남김 (비의 기본값), False는 그림 속에 칠해 매체와 대기 원근을 함께 받음 (눈, 꽃잎의 기본값)
    + 흰 눈은 밝은 하늘 앞에서 보이지 않으므로 어두운 숲이나 건물 앞에 내리도록 구도를 잡음
- `wet_reflection(canvas, ground, light, strength=0.55, ripple=0.5, streak=1, glow=0.8)`
    + ground는 젖은 바닥의 마스크 또는 경로 (`canvas.region_mask("road", "sidewalk")` 등)
    + 바닥에 선 모든 것을 자기 발끝 선 기준으로 뒤집어 비춤 (수평 원근에서 수직으로 선 물체는 정확)
    + 밝은 가로등, 간판, 창은 아래로 길게 번지는 빛 기둥이 됨 (glow, streak)
    + 먼 바닥일수록 거울에 가깝고 가까운 바닥일수록 바닥색이 드러남, 젖은 정도는 얼룩지게 달라짐
    + 바닥에 선 인물까지 비추려면 인물을 그린 뒤 호출하고, 앞쪽 빗줄기는 그 다음에 그림
- 예시: `scene_rain_night.py` (비 오는 밤거리), `scene_beach_sunset.py` (젖은 모래), `scene_snow_forest.py` (눈), `scene_blossom_walk.py` (꽃잎)

## 원근 구성 (Perspective)

```python
camera = scenery.Perspective(canvas, horizon_y, eye=1.6, focal=1.2, yaw=0.0, pitch=0.0)
```

- 세계 좌표는 X 오른쪽, Y 위, Z 앞쪽(미터 등 임의의 길이 단위), 카메라는 (0, eye, 0)
- `eye`는 눈높이, `focal`은 화각 (0.8 광각, 1.5 표준, 3 망원)
- `yaw`는 카메라를 오른쪽으로 돌리는 각도. 0은 1점 투시, 20-45는 길모퉁이의 2점 투시
- `pitch`는 카메라를 위(+)나 아래(-)로 기울이는 각도. 세로선이 모이는 3점 투시 (빌딩 올려다보기 20-35, 내려다보기 -15 이하)
    + horizon_y는 화면 중심선으로 유지되고 실제 지평선은 pitch만큼 이동
- 카메라 뒤로 넘어가는 형태는 근평면에서 잘라 냄

| 메서드 | 용도 |
|---|---|
| `point(x, y, z)` | 세계 좌표를 캔버스 좌표로 변환 |
| `scale(z, x=0)` | 그 지점에서 길이 1이 차지하는 디자인 단위 (인물 키 계산) |
| `depth(x, z)` | 카메라 앞쪽 거리 (그리는 순서와 크기 계산) |
| `ground_quad(x0, x1, z0, z1)` | 바닥의 사각형 (도로, 카펫, 타일) |
| `quad(corners)` | 임의의 3D 다각형 |
| `face(origin, u_axis, v_axis)` | 평면 1개의 면 좌표 변환 함수 |
| `box(x, z, width, depth, height, color, clip)` | 상자 (건물, 가구), 카메라를 향한 면만 그림, clip은 그릴 영역 제한 |
| `room(x0, x1, z0, z1, height, wall, floor, openings)` | 카메라가 들어선 방의 바닥, 천장, 뒷벽, 옆벽 (아래 설명) |
| `chair(x, z, seat, back_side)` | 나무 의자 1개 |
| `windows(mapper, rows, cols, color, lit)` | 면 위의 창문 격자 |
| `sun(light)` | 장면 조명의 세계 좌표 방향 (그림자 계산) |
| `screen_normal(normal)` | 세계 좌표 법선을 캔버스 법선으로 변환 |

- `box`는 면 좌표 변환 함수 `{"front", "back", "left", "right", "top", "side"}`를 반환
    + `mapper(u, v, out=0)`: u는 바깥에서 본 왼쪽에서 오른쪽, v는 아래에서 위 (0-1), out은 벽에서 튀어나온 거리
    + `mapper.visible`, `mapper.size`(미터), `mapper.normal`로 면의 상태를 확인
    + "side"는 보이는 옆면 (1점 투시 거리에서 길을 향한 벽)
- 상자는 먼 것부터 그려야 가까운 상자가 먼 상자를 가림
- 인물을 장면에 세우는 절차
    + `foot_x, foot_y = camera.point(x, 0, distance)`
    + `height = 실제 키 * camera.scale(distance)`
    + `character.draw(canvas, foot_x, ground_y=foot_y, height=height, light=light)`
- 실내는 바닥 `ground_quad`, 벽 `quad`, 가구 `box`로 구성

## 실내 (room, chair)

```python
camera = sc.Perspective(canvas, H * 0.4, eye=1.15, focal=1.2)
street_outside(canvas, camera, light)                          # 장면의 창밖 풍경 함수: 방보다 먼저 그림
faces = camera.room(-3.4, 3.4, 0.3, 5.6, 3.1, wall="#efe4d2", floor="#a8805c",
                    openings={"back": [(0.05, 0.08, 0.95, 0.93)]})   # 뒷벽에 유리창 구멍
camera.chair(0.32, 3.0, back_side="right")                    # 앉을 인물보다 먼저
```

- `room`은 방 안에서 보이는 면만 그리고 면 좌표 함수(`back`, `left`, `right`, `floor`, `ceiling`)를 반환
    + 면 좌표는 방 안에서 본 왼쪽에서 오른쪽(u), 아래에서 위(v), 바닥과 천장의 v는 카메라에서 멀어지는 방향
    + `openings`의 (u0, v0, u1, v1)는 벽에 뚫린 창과 문, 먼저 그린 바깥 풍경이 그 자리로 보임
    + 창틀, 액자, 선반은 반환된 면 좌표로 `geom.polygon([face(u, v), ...])`을 만들어 그림
- `chair`의 back_side는 등받이 위치: far (카메라를 보는 사람), near (등을 보이는 사람), left, right (옆으로 앉은 사람의 등 쪽)
- 의자에 앉은 인물과 탁자는 그리는 순서로 겹침을 맞춤 (`references/figure.md`의 앉은 인물 항목)
- 예시: `scene_cafe_window.py` (카페 창가, 원형 탁자, 의자, 창밖 거리)

## 도시 (city)

거리 장면은 `city` 모듈이 실제 치수(미터)로 건물 입면, 거리 시설, 그림자를 만듦.

```python
from atelier import city, scenery as sc
camera = sc.Perspective(canvas, horizon, eye=1.6, focal=0.9, yaw=0)
city.road(camera, -4, 4, 0.5, 300, crossing=9)                    # 차도, 중앙선, 횡단보도
city.sidewalk(camera, -8, -4, 0.5, 300)                             # 연석이 있는 보도
buildings = [city.building(camera, x, z, 8, 9, 16, "#c9a27e", kind="apartment", light=light, awning="#2f6f5f")]
city.lamp(camera, 4.6, 12); city.car(camera, 2.2, 14, "#a8302c"); city.pedestrian(camera, 5, 10)
city.cast_shadows(camera, light, buildings)                         # 모든 요소를 그린 뒤 마지막에 호출
```

| 함수 | 용도 |
|---|---|
| `building(camera, x, z, width, depth, height, color, kind, light, night, sky, awning, sign, roof, seed)` | 건물 1동, 보이는 모든 벽에 입면 |
| `facade(camera, face, color, kind, ...)` | 벽 1면의 입면 (직접 만든 상자에 사용) |
| `cast_shadows(camera, light, buildings)` | 건물이 바닥과 다른 건물 벽에 드리우는 그림자 |
| `road`, `sidewalk` | 차도와 보도 |
| `lamp(camera, x, z, height, night)` | 가로등, 밤에는 빛무리와 바닥의 빛 웅덩이 |
| `utility_pole`, `wires(camera, anchors, sag, painted)` | 전신주와 처진 전선, painted=True는 선화 대신 물감으로 그림 (선을 흐리게 하는 화풍에서도 보임) |
| `pylon(camera, x, z, height, yaw)` | 격자형 송전탑, 반환값은 전선 걸 점 목록 (아래 설명) |
| `chimney(camera, x, z, height, radius, lights)` | 붉은 띠와 흰 띠의 보일러 굴뚝, 경고등, 반환값은 연기용 꼭대기 점과 축척 |
| `struts(camera, members, color, width)` | 월드 좌표 선분 묶음을 실제 굵기로 그림 (놀이터 철골, 난간, 안테나) |
| `tree(camera, x, z, height)` | 가로수 |
| `car(camera, x, z, color, kind, facing, yaw, night, light)` | 차량 (아래 설명) |
| `pedestrian(camera, x, z, color)` | 원경 행인 실루엣 (가까운 인물은 `Character`) |

- 입면 종류(`kind`): apartment (틀과 창턱이 있는 창, 1층 상점), old (높은 창과 상인방, 처마 돌림띠), office (유리 커튼월), house (작은 창, 상점 없음), panel (조립식 패널 아파트)
- `kind="panel"`
    + 층 높이 2.8 m (`city.PANEL_STOREY`), 패널 폭 3.2 m마다 창 1개, 패널마다 조금씩 다른 콘크리트 색과 이음매
    + 4칸마다 출입구 (반 층 어긋난 계단실 창, 문, 차양, 밤에는 문 위 전등), 출입구 사이 칸에 튀어나온 발코니
    + 밤에는 창의 약 3분의 1이 노랑, 주황, 형광등 흰색, TV 빛 파랑 중 하나로 켜지고 일부는 커튼이 반쯤 가림
    + 높이는 `층수 * city.PANEL_STOREY + 0.8` (5층, 9층, 12층, 16층이 흔한 규격)
- `pylon`
    + 네 다리가 허리까지 좁아지고 면마다 X자 가새, 팔 3단과 애자, 꼭대기 피뢰 첨탑
    + 반환한 점으로 `wires(camera, [t[k] for t in towers], sag=...)`를 이으면 탑 사이에 전선이 처짐
    + 탑 1개만 화면에 두고 화면 밖 탑과 전선을 이으면 하늘을 가로지르는 전선이 생김 (`doomer_duo.py`)
- 입면 구성: 층 돌림띠, 처마 코니스, 벽 속에 들어앉은 창(태양 방향에 따라 창 윗면과 옆면 그림자), 하늘을 반사하는 유리, 1층 상점 유리, 간판과 글자 덩어리, 줄무늬 차양, 벽 밑동의 어두운 띠, 옥상 구조물
- `night=True`: 창의 절반 정도가 켜지고 상점 유리와 간판이 발광 (마감의 `bloom`과 함께 사용)
- 해가 낮거나 옆에서 비추면 거리 대부분이 그늘에 들어감 (실제 현상). 거리를 밝히려면 azimuth -30, elevation 45 전후
- `car`
    + 옆면 단면(범퍼, 보닛, 앞유리, 지붕, 뒷유리, 트렁크)을 차폭 방향으로 이어 만든 차체, 위쪽 유리 부분은 안쪽으로 좁아짐
    + kind: sedan, hatch, suv / facing 1은 앞이 멀리, -1은 앞이 카메라 쪽 / yaw로 비스듬히 세움
    + 바퀴와 휠, 휠 하우스, 옆 창과 가운데 기둥, 문 틈과 손잡이, 사이드미러, 전조등, 미등, 그릴, 번호판
    + `light`를 넘기면 도로에 그림자를 드리움, 근경 클로즈업에서도 형태가 유지됨
- 건물은 먼 것부터 그리고 반환값을 모아 `cast_shadows`에 넘김

## 정물 (objects)

| 함수 | 용도 |
|---|---|
| `use_light(light)` | 이후 모든 사물의 그림자를 장면 조명에 맞춤 (정물 장면 시작 시 1회 호출) |
| `backdrop(canvas, top, bottom, y, glow)` | 정물과 초상의 배경 벽, glow=(x, y, r)는 벽에 떨어진 빛 |
| `table(canvas, y, color, edge, grain, clip)` | 나뭇결이 있는 탁자 상판과 앞 모서리 하이라이트, clip은 그릴 영역 제한 |
| `cloth(canvas, points, color, folds, flow)` | 천, flow 방향(도)으로 길게 흐르는 주름 |
| `revolve(canvas, x, base_y, width, height, color, profile)` | 회전체 그릇 |
| `sphere`, `apple`, `pear`, `citrus`, `grapes` | 구와 과일 |
| `plate`, `book` | 접시, 책 |
| `flower(canvas, x, y, size, petal, centre, petals, tilt, turn)` | 꽃, tilt는 기울어 보이는 정도, turn은 회전 |
| `stem` | 줄기 |
| `floor_shadow(canvas, shape, base_y)` | 임의의 형태를 탁자 위 그림자로 눕힘 |
| `candle(canvas, x, base_y, width, height, lit, holder)` | 놋쇠 받침의 초, 녹은 윗면, 흘러내린 촛농, 심지, 불꽃. 불꽃 위치를 반환 |
| `flame(canvas, x, y, size, halo)` | 초 불꽃 (흰 심, 노란 몸통, 주황 테두리, 푸른 밑동, 빛무리) |

- `revolve`의 profile: vase, bottle, jug, bowl, cup, glass, pot, candle 또는 `[(반지름 비율, 높이 비율), ...]`
- 모든 사물은 `(x, base_y)`에 놓이며 그림자가 탁자면 위에 납작하게 누움
    + 실루엣을 빛 방향으로 밀고 시점 기울기로 눌러 만든 그림자, 물체에서 멀수록 가장자리가 흐려짐
    + 물체가 닿는 자리에는 가장 어두운 접촉 그림자
    + 그림자는 table, cloth, plate, book 영역에만 떨어짐
    + `use_light`를 호출하지 않으면 `light_from`(left, right)으로 방향을 정함
- 표면 질감: 사과의 세로 줄무늬와 점, 배의 홍조와 반점, 레몬 껍질의 오톨도톨함, 포도의 뽀얀 분, 그릇 입구의 밝은 테두리

## 현대 사물 (props)

컴퓨터, 휴대폰 같은 현대 사물은 판재(윤곽선에 두께를 준 조각)를 3D로 세우고 기울여 조립함.
정물과 같은 탁자 시점을 쓰므로 `objects`의 사물과 한 화면에 섞어 배치 가능.

```python
from atelier import objects as ob, props
ob.use_light(light)                                         # 그림자 방향을 장면 조명과 맞춤
props.laptop(canvas, x, base_y, width, screen_kind="code", yaw=10)
props.mug(canvas, x2, base_y2, width2)
```

| 함수 | 실제 크기 | 주요 인자 |
|---|---|---|
| `laptop` | 31 x 22 cm | color, screen_kind, open_angle(덮개 각도, 90 직립), keys, yaw |
| `monitor` | 화면 60 x 34 cm | color, screen_kind, yaw |
| `keyboard` | 36 x 12 cm | color, keys, yaw |
| `mouse` | 6 x 11 cm | color, yaw |
| `phone` | 7.2 x 15 cm | screen_kind, lying(눕힘 또는 세움), yaw |
| `tablet` | 25 x 17.5 cm | screen_kind, yaw (거치대에 세운 자세) |
| `mug` | | color, inside(음료 색), handle(left, right) |
| `headphones` | 18 cm | color, cushion, yaw |
| `pen` | 14 cm | color, yaw |
| `plant` | | pot, leaf (다육식물 화분) |
| `umbrella` | | 손잡이와 캐노피 중심을 화면 좌표로 받는 우산, 양산 (아래 설명) |
| `cassette` | 10 x 6.3 cm | color, label, stripe, yaw (창으로 보이는 릴 2개와 나사 5개) |
| `cigarette(canvas, start, end, width, lit)` | | 필터 끝에서 불붙은 끝까지 화면 좌표로 받음, 반환값은 불씨 위치 |
| `smoke(canvas, x, y, height, width, drift, alpha, strands)` | | 불씨에서 피어올라 갈라지며 흐려지는 연기 가닥 |

- 모든 함수는 `(canvas, x, base_y, width)`: 사물 앞쪽 가장자리 중앙이 탁자에 닿는 화면 위치와 그려질 폭
- `yaw`는 사물을 수직축으로 돌리는 각도 (양수는 오른쪽이 멀어짐)
- 보이는 면만 먼 것부터 그리고 면마다 자기 법선으로 빛을 받음
- 그림자는 3D 면을 빛 방향으로 탁자 위에 투영하여 계산, 닿는 자리에는 접촉 그림자
- 화면 내용 (`screen_kind`, 직접 그릴 때는 `props.screen(canvas, mapper, kind)`)

| kind | 내용 |
|---|---|
| code | 코드 편집기 (줄 번호, 색 구분된 코드 덩어리, 커서) |
| desktop | 바탕화면, 창, 독 |
| chat | 메신저 말풍선 |
| photo | 풍경 사진 |
| off | 꺼진 화면 (어두운 유리 반사) |

- 켜진 화면은 스스로 빛나므로(unlit) 어두운 장면에서도 밝게 남음, 유리에는 옅은 반사 띠
- 노트북을 yaw 180 전후로 돌리면 덮개 뒷면이 보이고 화면과 자판은 그려지지 않음 (맞은편 사람이 쓰는 노트북)
- `umbrella(canvas, hand, centre, radius, color, ribs, view, rise, part)`
    + hand는 손잡이를 쥔 점, centre는 캐노피 테두리의 중심, 두 점을 잇는 선이 우산대와 캐노피 축이 됨
    + view가 양수이면 눈보다 높은 캐노피를 올려다보아 안쪽 면이 보임, 0은 수평, 음수는 위에서 내려다봄
    + ribs 8은 서양 우산, ribs 24와 rise 0.38은 납작한 종이 양산
    + 사람이 든 우산은 2번에 나누어 그림: part="back"(캐노피, 우산대)은 인물 전에, part="front"(손잡이 고리, 몸 앞 우산대)는 인물 다음에 손 마스크를 뺀 clip으로 그림 (`references/figure.md`의 손에 든 소품 항목)
- 담배와 연기
    + 입에 문 담배는 인물을 그린 뒤 `character.face.pts([(입 폭 * 0.45, 입 높이)])`로 입꼬리를 찾아 그 점에서 시작 (`doomer_male.py`)
    + 재떨이 위 담배는 테두리 위 점에서 시작 (`doomer_still_life.py`)
    + `smoke`는 반환된 불씨 위치에서 호출, drift는 오를수록 옆으로 흐르는 정도, 굴뚝 연기는 drift 3-4로 옆으로 길게 누움
- 새 현대 사물은 `props._Frame`의 `plate(outline, origin, a_axis, b_axis, thickness, colors, region, facing=...)`로 조립
- 선화가 필요한 화풍(셀, 수채, 판화)은 `outline=2.5`를 지정
- 배치 요령
    + 높이가 다른 사물을 삼각형 구도로 묶고 일부를 겹침
    + 뒤쪽 사물부터 그림
    + 가장 밝은 사물을 시선 지점에 둠

## 커스텀 대상 (Sculpture)

라이브러리에 없는 대상(동물, 가구, 탈것, 소품)은 덩어리로 조립함.

```python
from atelier import Sculpture
form = Sculpture(canvas, detail=130)                      # detail: 부위의 대략적 크기(디자인 단위)
form.sweep([(x, y, z), ...], width=[...], depth=[...], part="body")   # 경로를 따라 굵기가 변하는 덩어리
form.ball((x, y, z), (rx, ry, rz), part="head", angle=0)             # 타원체
form.composite({"body": "#e6a960", "head": "#e6a960"}, line_width=3, light=light)
```

- 좌표는 캔버스 디자인 단위, z는 관찰자 쪽이 양수 (겹침 순서와 음영을 결정)
- `sweep`의 width는 화면상 반폭, depth는 앞뒤 반두께
- 같은 `group`의 부위는 매끄럽게 이어지고 다른 group 사이에는 겹침선이 생김
- 조립 후 평면 요소(얼굴, 무늬, 수염)는 `canvas.add`, `canvas.tint`, `canvas.stroke`로 위에 그림
    + `form.part_mask("head") > 0.5`를 clip으로 넘기면 해당 부위 안에만 그려짐
- 덩어리 뒤에 놓일 평면 요소(귀 등)는 `composite` 전에 그림
- 조립 절차: 큰 덩어리(몸통) 배치, 작은 덩어리(머리, 다리, 꼬리) 추가, `--rough`로 실루엣 확인, 세부 추가
- 실루엣이 대상을 설명하도록 특징 부위(귀, 꼬리, 부리, 뿔)를 과장
- 전체 예시는 `scripts/examples/custom_subject_cat.py`

## 장면 구성 요령

- 인물과 배경이 함께 있는 장면은 배경을 낮은 대비로, 인물을 높은 대비로 구성
- 배경과 인물의 광원 방향을 일치 (하늘의 glow 위치와 `Light`의 azimuth)
- 인물은 `canvas.layer(depth=0.3, group="figure")` 안에서 그림
    + anime_film, retro_anime 화풍은 group이 figure인 영역만 셀로 칠하고 나머지는 과슈로 칠함
- 근경 요소(풀, 난간, 나뭇가지)를 인물 앞에 두면 깊이감이 생김
