# 도시 풍경 (paintkit.city)

건물 면을 평면으로 먼저 그리고 원근에 맞춰 붙이는 방식으로 도시를 만든다. 세계 좌표의 단위는 미터. X는 오른쪽, Y는 위, Z는 멀어지는 방향.

```python
from paintkit import city
```

## 목차

1. 먼 스카이라인
2. 건물 면 (facade)
3. 원근 카메라 (Perspective)
4. 거리 한 번에 만들기 (street)
5. 원근 붙이기 (Canvas.paste)
6. 낮과 밤
7. 인물 배치
8. 2점 투시 카메라 (Camera)

## 1. 먼 스카이라인

`city.skyline(cv, base_y, height=(120, 380), width=(46, 130), color, lit, lit_ratio=0.25, window_px=5, seed)`

- 평면 실루엣 건물 한 줄을 `base_y`까지 채운다
- 2-3줄을 겹친다. 먼 줄일수록 낮게, 밝게, 푸르게
- `lit_ratio=0`이면 낮의 실루엣

```python
city.skyline(cv, 560, height=(60, 190), color='#a88aa8', lit_ratio=0.0, seed=1)      # 가장 먼 줄
city.skyline(cv, 560, height=(90, 300), color='#6a5f8f', lit_ratio=0.18, seed=2)
city.skyline(cv, 560, height=(60, 230), color='#3a3a62', lit_ratio=0.30, seed=3)     # 가장 가까운 줄
scenery.water_reflection(cv, 560, tint='#2a2f5f')                                    # 강 건너 풍경
```

## 2. 건물 면 (facade)

`city.facade(width_m, height_m, wall, glass, lit, lit_ratio, floor_m=3.4, bay_m=3.0, window=(0.62, 0.55), shop=None, resolution=None, seed)`

- 건물의 한 면을 평면 Canvas로 돌려준다. 창문 격자, 창턱, 옥상 띠, 1층 상점이 그려진다
- `shop`에 색을 주면 1층이 상점 전면이 된다
- 돌려받은 Canvas에 간판이나 문을 더 그린 뒤 붙여도 된다

## 3. 원근 카메라 (Perspective)

`view = city.Perspective(vanishing=(620, 520), focal=900, eye=1.6)`

| 메서드 | 용도 |
|---|---|
| `project(x, y, z)` | 세계 좌표 → 캔버스 px |
| `scale(z)` | 그 거리에서 1m의 px 크기 |
| `depth_at_row(row_y)` | 캔버스의 그 줄에 보이는 지면의 거리 |
| `wall_quad(x, z_near, z_far, height)` | 길과 나란한 벽의 네 모서리 |
| `front_quad(x_left, x_right, z, height, base=0)` | 보는 사람을 마주한 벽 |
| `ground_quad(x_left, x_right, z_near, z_far)` | 지면의 띠 (도로, 보도, 밭) |

- `vanishing`의 y가 눈높이의 지평선이다
- `focal`이 캔버스 폭과 비슷하면 표준 화각, 작을수록 광각
- `position`, `depth(x, y, z)`, `scale_at(x, y, z)`, `quad(corners)`는 `Camera`와 같은 이름으로 쓸 수 있다

## 4. 거리 한 번에 만들기 (street)

```python
masks = city.street(cv, view, road_half=5.0, pavement=3.0, depth=(4.0, 160.0), height=(12.0, 38.0),
                    lit_ratio=0.3, shade_side='left', seed=5)
for z in (14, 30, 55, 90):
    city.street_lamp(cv, view, -5.6, z, on=False)
```

- 양쪽 건물 줄, 보도, 차선이 있는 도로를 그린다. `masks['road']`, `masks['left']`, `masks['right']`를 돌려준다
- 하늘과 먼 스카이라인을 먼저 그린 뒤 호출한다. 먼 건물은 하늘색 쪽으로 흐려진다 (`haze`로 색 지정 가능)
- `walls`, `glass`, `shops`, `asphalt`, `paving`으로 색을 바꾼다
- `street_lamp(cv, view, x, z, height=7.0, glow, on=True)`은 가로등 1개. 켜면 빛 번짐과 바닥의 빛 웅덩이가 생긴다

## 5. 원근 붙이기 (Canvas.paste)

`cv.paste(source, quad, opacity=1.0)`. `source`는 Canvas 또는 이미지, `quad`는 (좌상, 우상, 우하, 좌하) 네 점.

```python
sign = Canvas(300, 120, '#e04a6a')                                     # 평면으로 그린 간판
sign.fill(sign.ellipse(150, 60, 90, 30), '#fff3d0')
cv.paste(sign, view.wall_quad(-8.0, 12.0, 15.0, 6.0))                   # 왼쪽 벽에 붙임

rows = Canvas(600, 1200, '#5fa652')                                    # 밭고랑 무늬
ys = np.arange(1200)[:, None] * np.ones((1, 600))
rows.fill(((ys // 14) % 2 == 0).astype(np.float32), '#79bd60')
cv.paste(rows, view.ground_quad(6.0, 60.0, 5.0, 220.0), opacity=0.75)   # 지면에 눕힘
```

도시 밖 장면에도 쓴다: 타일 바닥, 벽의 그림, 책상 위의 종이, 원근 도로(`examples/landscape_meadow.py`).

## 6. 낮과 밤

| | 낮 | 밤 |
|---|---|---|
| 하늘 | `sky` + `cloud_bank` | 짙은 남색에서 지평선의 보라-분홍으로 `ramp` |
| `lit_ratio` | 0 | 0.4-0.5 |
| `shade_side` | `'left'` 또는 `'right'` | `None` |
| 벽 색 | 밝은 회색, 베이지 | 어두운 남보라 계열 |
| 가로등 | `on=False` | `on=True` |
| 마감 | `finish_anime(glow=0.1)` | `finish_anime(glow=0.3)` + `finish.vignette` |

젖은 도로: 가로등과 상점 아래로 세로 빛줄기를 `screen`으로 얹고 `masks['road']`로 자른다 (`examples/city_night_walk.py`).

## 7. 인물 배치

```python
depth = 1.75                                          # 카메라에서 1.75m
scale = view.scale(depth)
figure = Figure(pelvis=view.project(-0.4, 0.90, depth), height=1.70 * scale, ...)
```

- 배경을 다 그린 뒤 `cv.color = blur(cv.color, 2.6)`으로 흐리고 인물을 그리면 초점이 인물에 맞는다
- 가로등 방향을 `look.light`로 삼고 같은 색의 `add_rim_light`를 넣는다

## 8. 2점 투시 카메라 (Camera)

카메라를 돌리면(yaw) 건물의 두 면이 각각 다른 소실점으로 달아나는 2점 투시가 된다. 위나 아래로 기울이면(pitch) 세로선도 모이는 3점 투시가 된다.

```python
view = city.Camera(center=(700, 560), focal=720, position=(-10.0, 1.6, -10.0), yaw=45, pitch=-7)
```

| 인자, 메서드 | 의미 |
|---|---|
| `center` | 시선이 캔버스에 닿는 px (보통 캔버스 중앙) |
| `position` | 카메라 위치 m. y가 눈높이 |
| `yaw` | 양수면 +X 쪽(화면 오른쪽)을 본다. 45면 모퉁이를 대각선으로 본다 |
| `pitch` | 양수면 아래를 본다 (책상, 바닥). 음수면 올려다봐 높은 건물이 위로 모인다 |
| `project(x, y, z)`, `quad(corners)` | `Perspective`와 같다 |
| `depth(x, y, z)`, `scale_at(x, y, z)` | 시선 방향 거리, 그 점에서 1m의 px |
| `vanishing_point(heading)`, `horizon_y()` | 방향(0 = +Z, 90 = +X)의 소실점, 지평선 높이 |

카메라 뒤로 이어지는 땅이나 길은 그대로 투영하면 뒤집힌다. 두 함수가 카메라 앞에서 잘라 준다.

| 함수 | 용도 |
|---|---|
| `project_polygon(view, points, near=0.3)` | 수평이든 아니든 평면 다각형 `[(x, y, z)]`를 카메라 앞부분만 남겨 투영 |
| `ground_rects(cv, view, rects, y=0)` | 땅 위 직사각형들 `[(x0, z0, x1, z1)]`의 마스크 (차선, 횡단보도, 보도블록, 러그) |

모퉁이 건물은 상자로 세우고 보이는 면마다 facade를 붙인다.

```python
faces = solids.box(cv, view, (x0, 0.0, z0), (x1 - x0, height, z1 - z0), wall, edge=0)
for name in ('front', 'left'):                  # 이 카메라에서 보이는 두 길가 면
    if faces[name] is not None:
        width = (x1 - x0) if name == 'front' else (z1 - z0)
        cv.paste(city.facade(width, height, wall, resolution=28), faces[name])
```

- 먼 건물부터 그린다 (카메라와의 거리로 정렬)
- 밤에는 벽색을 어둡게 넘겨 창만 빛나게 한다: `facade(..., adjust(wall, lightness=-0.30), ...)`
- 전체 예시는 `scripts/examples/city_corner.py [out] [dusk|night]`
