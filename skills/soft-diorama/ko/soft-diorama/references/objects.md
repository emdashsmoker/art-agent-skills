# 현대 사물 (paintkit.solids)

컴퓨터, 노트북, 휴대폰, 카메라, 헤드폰, 컵, 조명처럼 사람이 만든 물건을 원근 속에 놓고 그린다.

- 현대 사물은 대부분 상자와 원통이다
    + 상자: 모니터, 노트북, 키보드, 휴대폰, 책
    + 원통: 머그, 캔, 화분, 스탠드 받침, 렌즈
    + 바닥에 누운 납작한 물건: 게임 패드, 코스터, 쟁반
- 화면, 자판, 상표는 평면 Canvas로 따로 그린 뒤 면에 `paste`로 붙인다

```python
from paintkit import Canvas, city, solids

view = city.Perspective(vanishing=(700, 300), focal=1250, eye=1.45)   # 단위 m, X 오른쪽, Y 위, Z 앞쪽 깊이
# 비스듬히 본 장면: city.Camera(center=(700, 500), focal=900, position=(-1, 1.5, -1), yaw=35, pitch=15)
panel = solids.box(cv, view, (-0.33, 0.87, 1.91), (0.66, 0.40, 0.03), '#1c1e26')
cv.paste(screen_canvas, solids.patch(panel['front'], 0.018, 0.03, 0.982, 0.93))
```

## 목차

1. 카메라와 단위
2. 함수
3. 그리는 순서
4. 사물별 조리법
5. 화면과 자판 그리기
6. 밤 장면의 빛
7. 유화로 마감할 때
8. 예제와 한계

## 1. 카메라와 단위

- 카메라는 도시와 같은 `city.Perspective`(정면 1점 투시) 또는 `city.Camera`(돌리고 기울인 2점, 3점 투시)를 쓴다
    + `vanishing`: 소실점 px. 지평선 높이가 된다
    + `focal`: 클수록 망원. 책상 정물은 1200-2600
    + `eye`: 눈높이 m. 책상(0.74m)보다 0.3-0.7m 높게 두면 윗면이 보인다
- 물체 좌표는 미터. 실제 크기를 그대로 넣으면 비례가 맞는다

| 사물 | 크기 (폭 x 높이 x 깊이, m) |
|---|---|
| 책상 높이 | 0.74 |
| 24인치 모니터 패널 | 0.54-0.66 x 0.33-0.40 x 0.03 |
| 노트북 본체 | 0.30-0.34 x 0.016 x 0.22 |
| 키보드 | 0.44 x 0.02 x 0.14 |
| 휴대폰 | 0.075 x 0.008 x 0.155 |
| 머그 | 지름 0.08, 높이 0.095 |
| 음료 캔 | 지름 0.066, 높이 0.122 |
| 미러리스 카메라 몸체 | 0.13 x 0.08 x 0.045 |

- 카메라 높이와 초점거리 정하기
    + 물체가 화면에서 작으면 `focal`을 키우고 `vanishing`의 y를 줄인다 (지평선이 위로 가며 바닥이 넓어진다)
    + `view.project(x, y, z)`로 주요 점의 화면 위치를 먼저 계산해 구도를 확인한다

## 2. 함수

| 함수 | 설명 |
|---|---|
| `box(cv, view, origin, size, color, light_from='left', top_color=None, edge=0.5, turn=0)` | 바닥에 놓인 상자. `origin`은 앞-아래-왼쪽 모서리 (x, y, z), `size`는 (폭, 높이, 깊이). 카메라에서 보이는 면만 칠한다. `turn`(도)은 밑면 중심을 축으로 돌린다 (양수면 오른쪽 끝이 다가와 오른쪽 면이 보인다). `light_from`은 `'left'`, `'right'` 또는 빛 쪽 3D 벡터. 반환 `dict(front, back, left, right, top, side, quads, mask)`, 숨은 면은 None |
| `patch(quad, left, top, right, bottom)` | 면의 일부(비율 0-1)를 원근에 맞는 사각형으로. 베젤 안쪽 화면, 노트북 자판 영역, 트랙패드, 책 배면 |
| `disc(cv, view, center, y, radius, depth_radius=None)` | 높이 y의 수평면에 누운 원. 원 둘레를 투영해 기울인 카메라에서도 정확하다. 반환 `(mask, (cx, cy, rx, ry))` |
| `contact_shadow(cv, view, center, y, radius, depth_radius=None, offset=(0,0), strength=0.6, soft=0.35)` | 물체 밑의 부드러운 접지 그림자. 물체보다 먼저 칠한다 |
| `cylinder(cv, view, center, y, radius, height, color, top_radius=None, light, gloss=0, top_color=None, hollow=None)` | 선 원통과 원뿔대. `hollow`에 색을 주면 위가 열린 컵. 반환 `dict(mask, top, bottom)` (top, bottom은 px 타원) |
| `barrel(cv, view, center, z_back, z_front, radius, color, front_radius=None, light, gloss=0)` | Z축을 따라 누운 원통, 앞 끝이 관객 쪽 (렌즈, 스피커). 반환 `(mask, (cx, cy, r))` 앞 원 |
| `slab(cv, view, points, y, thickness, color, light, bulge=None, gloss=0, smooth=True)` | 위에서 본 외곽선 `[(x, z)]`을 두께만큼 세운 납작한 물체. 반환 `dict(mask, top)` |
| `flat_shape(cv, view, points, y, smooth=True)` | 수평면 위 외곽선 마스크 (그림자, 매트) |
| `flat_path(view, points, y)` | 수평면 위 경로를 px 점 목록으로. `cv.ribbon`에 넘겨 케이블, 끈을 그린다 |

Canvas와 카메라 쪽 도구

| 메서드 | 설명 |
|---|---|
| `cv.rect(x0, y0, x1, y1, radius=0)` | 모서리가 둥근 사각형. 화면 속 창, 키, 버튼 |
| `cv.paste(source, quad)` | 평면 그림을 네 점 사각형에 원근으로 붙인다. 반환값은 붙인 영역 마스크 |
| `view.quad([(x,y,z) x 4])` | 임의의 3D 사각형 (기울어진 노트북 화면, 경사면). 순서는 왼위, 오른위, 오른아래, 왼아래 |

- `box`의 면 사각형은 모두 그 면을 바깥에서 본 왼위, 오른위, 오른아래, 왼아래 순서라서 `paste`와 `patch`에 바로 넘긴다. 붙인 그림이 뒤집히지 않는다
- 윗면 사각형은 먼 쪽이 위(왼위, 오른위), 가까운 쪽이 아래다
- 바닥 전체나 카메라 뒤까지 이어지는 면은 `city.project_polygon`, 바닥의 줄무늬와 타일은 `city.ground_rects`

## 3. 그리는 순서

뒤에서 앞으로, 각 물체는 아래 순서로 칠한다.

1. 방: 벽, 창, 액자, 책상 윗면
2. 먼 물체부터 접지 그림자 `contact_shadow`
3. 몸체 `box`, `cylinder`, `slab`
4. 면 위의 그림 `paste` (화면, 자판, 상표)
5. 작은 부품 (버튼, 다이얼, 손잡이, 케이블)
6. 빛 연출 (6절)과 마감

- 같은 깊이의 물체는 화면 아래쪽(가까운 쪽)에 있는 것을 나중에 그린다
- 물체 사이 거리는 깊이(z)로 벌린다. 화면에서 겹쳐 보이면 z를 조정한다

## 4. 사물별 조리법

```python
# 모니터: 받침 원통 + 목 상자 + 패널 상자 + 화면 붙이기
solids.contact_shadow(cv, view, (0.0, z), desk_y, 0.19, 0.10, strength=0.5)
solids.cylinder(cv, view, (0.0, z), desk_y, 0.12, 0.012, '#3a3d46', light=light)
solids.box(cv, view, (-0.025, desk_y, z), (0.05, 0.16, 0.02), '#30333c', edge=0)
panel = solids.box(cv, view, (-0.33, desk_y + 0.13, z - 0.04), (0.66, 0.40, 0.03), '#1c1e26', edge=0.3)
screen = solids.patch(panel['front'], 0.018, 0.03, 0.982, 0.93)
cv.paste(code_screen(960, 560), screen)

# 노트북: 본체 상자 + 자판 붙이기 + 뒤로 젖힌 덮개 (view.quad)
base = solids.box(cv, view, (x0, desk_y, z0), (x1 - x0, 0.016, z1 - z0), '#b9bdc6', light_from='right')
cv.paste(keyboard_top(600, 240), solids.patch(base['top'], 0.06, 0.08, 0.94, 0.58))
lid = view.quad([(x0, hinge_y + 0.215, z1 + 0.075), (x1, hinge_y + 0.215, z1 + 0.075),
                 (x1, hinge_y, z1), (x0, hinge_y, z1)])
cv.fill(cv.polygon(np.array(lid)), '#22252e')
cv.paste(chart_screen(640, 400), solids.patch(lid, 0.035, 0.05, 0.965, 0.92))

# 머그: 열린 원통 + 손잡이 띠 + 김
mug = solids.cylinder(cv, view, (0.62, 1.68), desk_y, 0.040, 0.095, '#e06a4a', top_radius=0.043,
                      light=light, gloss=0.5, hollow='#3a2418')
tx, ty, trx, _ = mug['top']

# 카메라 렌즈: 화면을 향한 원통, 앞 원에 테와 유리
_, (cx, cy, r) = solids.barrel(cv, view, (x, y), z, z - 0.05, 0.030, '#26272c', front_radius=0.028, light=light)

# 게임 패드: 위에서 본 외곽선을 두께 3cm로 세운다
solids.slab(cv, view, outline_xz, desk_y, 0.03, '#eceef2', light, gloss=0.25)
```

- 유리, 금속의 반사: 화면 유리는 `paste`한 그림 위에 사선 띠를 `screen`으로 얹는다
- 캔 상표처럼 원통을 감싸는 무늬는 원통 마스크와 곱한 뒤 `shading.form_light`로 돌아가는 명암을 다시 곱한다
- 놓인 물체가 떠 보이면 접지 그림자를 물체 폭의 1.2배로 키우고 `strength`를 올린다

## 5. 화면과 자판 그리기

화면은 평면 Canvas 하나다. 그 위에 `cv.rect`로 창과 글줄을 그린 뒤 `paste`한다.

```python
def code_screen(width, height):
    cv = Canvas(width, height, '#141a2a')
    cv.fill(cv.rect(0, 0, width, height * 0.07), '#222a40')                        # 제목 줄
    for row in range(16):                                                           # 글줄 = 둥근 막대
        y = height * (0.11 + row * 0.052)
        cv.fill(cv.rect(width * 0.21, y, width * 0.5, y + height * 0.022, radius=height * 0.01), '#7fd0ff')
    return cv
```

- 글자는 그리지 않는다. 색 막대의 길이와 들여쓰기만으로 코드, 문서, 표가 읽힌다
- 자판은 둥근 사각형 격자 하나. 스페이스 바만 길게 만든다
- 화면 그림의 비율은 붙일 면의 실제 비율과 맞춘다 (16:9 패널이면 960x540 근처)

## 6. 밤 장면의 빛

빛을 내는 면(화면, 전등 갓 입구, 창)을 마스크로 모은 뒤 나머지만 어둡게 한다.

```python
glowing = np.maximum.reduce([monitor, laptop, phone, lamp_mouth, window])
pool = cv.radial(lamp_floor, 560, 330)                                  # 스탠드 빛이 닿는 곳
cv.tint((1 - glowing) * (1 - 0.8 * pool), '#2f3566', 'multiply', 0.72)  # 방을 푸르게 가라앉힌다
cv.tint(pool * (1 - glowing), '#ffd2a0', 'multiply', 0.30)             # 빛 웅덩이는 제 색 + 따뜻하게
cv.tint(halo * (1 - monitor), '#7fd0ff', 'screen', 0.30)                # 화면 주위의 차가운 번짐
```

- 전등 빛은 `screen`으로 크게 올리지 않는다. 화면이 하얗게 날아간다. 어둡게 누르는 범위를 줄이는 쪽이 자연스럽다
- 화면의 번짐 중심은 화면 아래 가장자리 조금 밑에 둔다. 책상 위로 빛이 떨어지는 느낌이 난다
- 낮 장면은 어둡게 누르는 단계를 빼고 창 쪽에서 따뜻한 `radial`을 `screen`으로 얹는다

## 7. 유화로 마감할 때

- 물체 영역에 `detail` 마스크를 주면 버튼, 다이얼, 렌즈 테가 뭉개지지 않는다

```python
room = cv.color.copy()                       # 방까지 칠한 직후 저장
...                                          # 물체들을 칠한다
objects = (np.abs(cv.color - room).max(axis=-1) > 0.03).astype(np.float32)
image = finish.finish_oil(cv, radii=(20, 10, 5, 3), impasto=0.28, detail=objects)
```

- 화면 속 글줄처럼 아주 작은 무늬는 유화에서 사라진다. 화면이 주인공이면 일러스트 마감을 쓴다

## 8. 예제와 한계

| 예제 | 내용 |
|---|---|
| `examples/desk_still_life.py [out] [night\|day]` | 모니터, 노트북, 키보드, 마우스, 휴대폰, 머그, 스탠드, 책, 화분이 있는 책상. 밤에는 화면과 스탠드 조명 |
| `examples/still_life_gadgets.py [out] [oil\|illustration]` | 카메라, 헤드폰, 게임 패드, 휴대폰, 캔을 가까이서 본 정물 |

- 상자는 `turn`으로 돌린다 (`desk_still_life.py`의 휴대폰과 책). 장면 전체를 비스듬히 보려면 `city.Camera`의 `yaw`를 쓴다
- 원통은 세로로 선 것과 Z축으로 누운 것만 있다. 옆으로 누운 병은 `slab`이나 기본 도형으로 만든다
- 곡면이 복잡한 물건(자동차, 의자 등받이, 운동화)은 함수가 없다. 부위를 상자, 원통, 판으로 나눠 조립한다
- 글자는 지원하지 않는다. 상표와 화면 글은 색 막대와 도형으로 대신한다
