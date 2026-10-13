# 주제별 작업법

풍경, 도시, 정물, 현대 사물을 그릴 때 읽는 문서. 인물은 `references/figure.md`.

## 풍경

예제는 `examples/oil_summer_fields.py`, `examples/oil_harbor_sunset.py`, `examples/illustration_moonlit_camp.py`, `examples/oil_doomer_pylons.py`(송전탑 줄).

- 깊이를 만드는 세 가지 수단을 함께 사용
    + 공기 원근: 먼 것일수록 하늘색을 섞고 대비를 낮춤. `color.mix(색, 하늘빛, 0.3 * 거리)`
    + 크기 변화: 밭 띠, 나무, 물결, 풀이 멀수록 작고 촘촘해짐
    + 겹침: 화면 앞쪽 가장자리에 큰 나무나 언덕을 세워 뒤의 풍경을 일부 가림
- 화면을 하늘, 원경, 중경, 근경 네 층으로 나누고 뒤에서 앞으로 그림
- 지평선은 화면 중앙을 피해 위나 아래 3분의 1 근처에 둠
- 시선을 끄는 길이나 강은 S자로 굽혀 근경에서 원경의 초점까지 이음
    + 멀어질수록 폭을 급히 줄여야 눕혀진 평면으로 읽힘

| 소재 | 도구 |
|---|---|
| 뭉게구름 | `motifs.cumulus(canvas, center_x, base_y, width, height, light, palette, puffs)` |
| 산 능선 | `motifs.ridge(x_start, x_end, base_y, peak_height, roughness)` 결과에 아래 두 점을 붙여 닫음 |
| 나무의 잎 덩어리 | `motifs.canopy(canvas, cx, cy, width, height, light, palette, puffs, puff_size)` |
| 풀 | `motifs.grass(canvas, x_range, y_range, count, palette, blade)` |
| 물비늘, 꽃, 낙엽 | 작은 타원이나 `g.blob`을 난수로 흩뿌림. 가까울수록 크게 |

- 나무는 줄기를 `g.ribbon`으로 먼저 그리고 `canopy`를 위에 얹음
    + 좁고 긴 나무는 `puff_size=(0.32, 0.5)`처럼 뭉치를 키워야 틈이 메워짐
    + 나무 밑 풀밭에 MULTIPLY 그림자를 깔아 땅에 세움
- 유화풍에서는 `canvas.direct`로 층마다 붓 방향을 지정
    + 하늘은 완만한 사선, 밭과 물은 가로, 줄기와 풀은 세로, 잎 덩어리는 `around=중심`

## 도시

예제는 `examples/watercolor_old_town.py`, `examples/anime_doomer_courtyard.py`(2점 투시 단지), `examples/watercolor_doomer_block.py`(올려다본 3점 투시), `examples/illustration_doomer_rooftop.py`(내려다본 단지).

- 깊이 방향으로 뻗는 장면은 평행선이 소실점에 모여야 공간으로 읽힘
- `Perspective`로 장면 좌표(미터)를 화면에 투영

```python
from codepaint import Perspective
VIEW = Perspective(vanish=(690, 640), eye_height=1.6, focal=880)
wall = VIEW.side_wall(x=-3.6, z_near=5.0, z_far=10.5, y_bottom=0.0, y_top=12.5)   # 길 왼쪽 건물의 옆면
windows = VIEW.side_wall_grid(-3.6, 5.0, 10.5, 3.4, 12.0, columns=2, rows=3, margin=0.27)
road = VIEW.ground(-3.6, 4.2, 1.2, 90)
foot = VIEW.project(1.3, 0.0, 14.0)                                              # 길 위의 한 점
```

| 인자 | 뜻 |
|---|---|
| `vanish` | 소실점의 화면 좌표. 지평선이 이 높이를 지남 |
| `eye_height` | 눈높이. 1.6이면 선 사람의 시선, 키우면 내려다보는 구도 |
| `focal` | 깊이 1의 장면 길이 1이 화면에서 차지하는 길이. 키우면 망원 |

- 장면 좌표는 x 좌우, y 높이, z 깊이
    + 건물 한 채를 (벽의 x, 가까운 z, 먼 z, 높이)로 정의하고 높이와 색을 채마다 다르게 함
    + 가장 가까운 건물은 z 5 이상에서 시작. 더 가까우면 창과 문이 심하게 늘어남
    + 가장 가까운 건물에는 `front_wall`로 카메라를 마주 보는 정면 벽을 붙여 화면 가장자리를 채움
- 먼 건물부터 그려 가까운 건물이 덮게 함
- 길 한쪽 줄은 빛, 반대쪽 줄은 그늘로 나누고 그늘 줄이 길 위에 드리우는 그림자를 한 번에 겹칠
- 사람, 가로등, 차는 `VIEW.project(x, 0, z)`로 발 위치를 잡고 `VIEW.scale_at(z)`로 크기를 정함
    + 행인은 `figure.Figure(g.Frame(VIEW.project(x, 0.93, z), 0.225 * VIEW.scale_at(z)), ...)`
- 펜과 담채 양식은 칠을 끝낸 뒤 `cv.stroke(path, 잉크색, width=1.5, closed=True, jitter=0.5)`로 윤곽을 그음
- 길 끝에 탑이나 높은 건물을 두면 소실점이 초점이 됨
- 비스듬히 선 동, 내려다본 단지, 올려다본 동은 `solids`의 상자와 카메라 1대로 투영
    + 창과 발코니는 `camera.region(면, u0, v0, u1, v1)`로 면 위에 붙임. 옆면의 v는 위에서 아래로 감
    + 카메라를 위로 기울이면 세로선이 위로 모이는 3점 투시가 됨
    + 내려다본 단지는 깊이 줄마다 시야 폭 안에 동을 세워야 화면 아래가 비지 않음

## 정물

예제는 `examples/watercolor_still_life.py`.

- 물체는 3개 또는 5개로 묶고 크기를 대, 중, 소로 다르게 함
- 물체끼리 일부를 겹쳐 앞뒤 관계를 만들고 높이가 다른 물체로 삼각형 구도를 잡음
- 탁자 선은 화면 아래 3분의 1 근처에 두고 물체 뒤에서 끊기게 함
- 둥근 물체의 순서: 밑색, `form_shadow(soft=0.3-0.4)` 그늘, `form_light` 하이라이트, 바닥색이 비치는 반사광
    + 반사광은 그늘 쪽 아래에 이웃 물체나 탁자의 색을 낮은 불투명도로 얹음
- 수채화풍의 하이라이트는 칠하지 않고 종이로 남김
    + `칠할형태 = 몸통 - cv.shape(하이라이트경로, soft=4)`
- 그림자는 두 겹
    + 닿는 자리의 짙고 좁은 접지 그림자
    + 빛 반대쪽으로 길게 눕는 넓고 옅은 그림자
- 손잡이, 주둥이, 꼭지처럼 가늘고 휘는 부품은 `g.ribbon(중심선, 폭 목록)`
- 포도나 꽃잎처럼 반복되는 알은 뒤쪽부터 그리고 크기와 위치를 난수로 흔듦
- 배경은 물체의 보색 쪽 색을 옅게 깔아 물체를 띄움

## 현대 사물

예제는 `examples/anime_night_desk.py`(책상 장면), `examples/watercolor_gadget_studies.py`(기기 습작), `examples/watercolor_doomer_kitchen.py`(카세트 라디오와 잔 받침), `examples/anime_doomer_courtyard.py`(옆모습을 밀어낸 승용차).

- 컴퓨터, 전화기, 컵, 책, 스피커는 직육면체와 기둥의 조합
- `solids`로 3차원 입체를 만들고 카메라 1대로 투영
    + 모든 물건의 원근과 면 명암이 같은 시점과 빛을 따름
    + 물건마다 yaw와 pitch로 방향을 자유롭게 돌려 놓을 수 있음

```python
from codepaint import props
from codepaint import solids as s3

CAMERA = s3.Camera(eye=(0, 50, -70), target=(0, 12, 35), focal=1150, center=(800, 470))
LIGHT = (-0.7, 0.6, -0.2)                       # 빛이 오는 쪽(3차원)
desk = s3.box((0, -2.5, 25), (150, 5, 66))       # 중심, (폭, 높이, 깊이) cm
s3.draw(cv, CAMERA, desk, {"top": "#6a4c44", "*": "#4a3236"}, LIGHT)

monitor = props.monitor((8, 0, 40), yaw=-4)
monitor.draw(cv, CAMERA, {"foot": "#3a3f62", "neck": "#2f3456", "panel": {"front": "#0a0c16", "*": "#3a3f62"}},
             LIGHT, line="#0b0d1c", width=1.4)
screen = monitor.faces["screen"]
cv.fill(cv.shape(CAMERA.region(screen, 0.02, 0.04, 0.98, 0.96)), "#151a2c")   # 화면 내용은 면 위 0-1 좌표
```

| 도구 | 용도 |
|---|---|
| `s3.box(center, size)` | 직육면체. 책상, 책, 스피커, 상자 |
| `s3.slab(center, size, radius)` | 모서리가 둥근 판. 전화기, 노트북, 모니터, 태블릿 |
| `s3.cylinder(base, radius, height, top_radius)` | 원기둥과 원뿔대. 컵, 렌즈, 전등갓, 화분 |
| `solid.rotated(yaw, pitch, about)`, `solid.moved(offset)` | 돌리고 옮기기 |
| `s3.draw(canvas, camera, solid, paint, light, line)` | 보이는 면만 먼 것부터 칠하고 윤곽선을 그음 |
| `camera.region(face, u0, v0, u1, v1)` | 면 위 사각 영역. 화면, 자판, 라벨 |
| `camera.face_ellipse(face, u, v, ru, rv)` | 면 위 타원. 스피커, 렌즈 유리, 단추 |
| `props.laptop`, `monitor`, `keyboard`, `phone`, `mug`, `book`, `desk_lamp` | 완성된 사물 부품. `Prop.draw`로 칠함 |
| `props.keycaps(canvas, camera, face, color, area=...)` | 면 위 자판 격자 |

- 장면 좌표는 x 오른쪽, y 위, z 깊이. 사물은 cm 단위가 편함
- 칠하는 순서
    + 한 사물 안의 면 순서는 `s3.draw`가 정함
    + 사물끼리는 먼 것부터 직접 호출하거나 `camera.order(solids)`로 정렬
    + 책상, 바닥, 벽처럼 다른 사물을 받치는 큰 면은 중심이 가까워도 맨 먼저 그림. `order`는 중심 깊이로만 정렬하므로 큰 면을 넣으면 순서가 틀림
    + 겹치는 사물 하나가 다른 사물을 관통하면 순서로 해결되지 않으므로 배치를 띄움
- 회전 방향
    + yaw 양수는 위에서 볼 때 시계 방향이며 정면이 화면 왼쪽으로 돎
    + pitch 양수는 윗부분이 카메라 반대쪽으로 넘어감. 눕힌 판은 `rotated(pitch=90, about=중심)`
    + 원기둥 축을 앞으로 눕히면 `rotated(pitch=-90)`이며 top 면이 카메라를 향함(렌즈)
- 면 이름
    + box는 front, back, left, right, top, bottom. top의 v는 뒤에서 앞으로
    + slab과 prism은 front, back, side. 눕힌 slab의 윗면은 front
    + cylinder는 top, bottom, side
- 화면과 자판 같은 세부는 입체를 칠한 다음 면 위 좌표로 얹음
    + 빛나는 화면은 마지막에 그 영역을 SCREEN 합성으로 한 번 더 칠하고 주변에 같은 색의 부드러운 빛을 깔음
- 물건마다 가장 잘 읽히는 각도가 다르면 칸마다 카메라를 따로 둠(습작 시트)
- 자동차처럼 옆모습이 특징인 사물은 옆모습 윤곽을 `s3.prism`으로 폭만큼 밀어내고 돌려 세움
    + 면 법선의 위 성분으로 윗면(지붕, 보닛)과 비스듬한 면(앞유리)을 골라 따로 칠함
- 위가 뚫린 그릇(잔 받침, 화분 테)은 보이는 옆면만 직접 칠함. `s3.draw`는 윗면 자리까지 실루엣으로 메움
- 손잡이, 전선, 헤드폰 띠처럼 휘는 막대는 3차원 점열을 `camera.path`로 투영해 굵은 선으로 그림
    + 굵기는 `camera.scale_at(점)`을 곱해 깊이에 맞춤
