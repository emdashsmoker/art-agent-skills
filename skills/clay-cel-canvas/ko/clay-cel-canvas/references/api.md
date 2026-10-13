# 엔진 함수 목록

모든 좌표와 크기는 캔버스 단위다 (캔버스 너비 = 1000). 색은 `"#RRGGBB"` 문자열이다.

## 목차

- 캔버스 생성
- 부분 그림 배치
- 카메라 투영
- 3차원 조형
- 포즈와 프레이밍
- 옷
- 치마와 드레스
- 여러 사람
- 머리 돌리기
- 머리와 얼굴 템플릿
- 분위기 층
- 장소 도우미
- 곡선 만들기
- 마스크 만들기
- 마스크 가공
- 칠하기
- 선 긋기
- 출력
- 색 도구

## 캔버스 생성

```python
Art(style, width_px=1024, aspect=1.25, light=(-0.45, -0.60, 0.66), seed=7,
    paper="#FFFFFF", view=None)
```

| 인자 | 뜻 |
|---|---|
| `style` | `STYLES["anime"]`, `STYLES["illust"]`, `STYLES["painterly"]` |
| `width_px` | 출력 너비 픽셀. 미리보기 512, 최종 1024 이상 |
| `aspect` | 높이 / 너비. 세로 인물 1.25, 정사각 1.0, 가로 풍경 0.62 |
| `light` | 빛이 오는 방향 `(x, y, z)`. x는 오른쪽, y는 아래쪽, z는 보는 사람 쪽이 양수 |
| `seed` | 난수 씨앗. 같은 값이면 같은 그림 |
| `view` | `(중심 x, 중심 y, 확대율)`. 좌표를 건드리지 않고 구도만 조정 |

속성: `art.width`, `art.height` (픽셀), `art.units_high` (단위), `art.rng` (난수 생성기), `art.style`,
`art.grade` (분위기 층, 기본 `None`. `references/styles.md`의 분위기 층).

## 부분 그림 배치

```python
with art.place(at=(x, y), scale=1.0, angle=0.0, flip=False, pivot=(0, 0)):
    draw_something(art)        # 이 안의 좌표와 크기는 모두 자체 좌표
```

| 인자 | 뜻 |
|---|---|
| `pivot` | 자체 좌표의 기준점 |
| `at` | 기준점이 놓일 캔버스 위치 |
| `scale` | 확대율. 미터 단위로 그린 것을 캔버스 단위로 바꾸는 용도로도 사용 |
| `angle` | 회전 각도. 양수는 화면상 시계 방향 |
| `flip` | 좌우 반전. 오른손을 왼손으로 바꿀 때 사용 |

- 블록은 겹쳐 쓸 수 있다 (몸 안의 머리, 팔 끝의 손)
- 블록 안에서 만든 마스크는 블록 밖에서도 그대로 쓸 수 있다
- 선 굵기 규칙
    + 굵기를 직접 준 선은 다른 크기처럼 함께 변환된다
    + 굵기를 생략한 선과 외곽선은 축소될 때만 가늘어지고 확대되어도 굵어지지 않는다
    + 블록 안의 선은 1.3 단위보다 가늘어지지 않는다

## 카메라 투영

```python
from atelier import Camera
camera = Camera(eye=(0.06, -0.80, 0.66), target=(0.0, 0.36, 0.12), focal=900, center=(500, 400))
curve = camera.project(points_3d)          # (N, 3) -> (N, 2) 캔버스 좌표
```

- 세계 좌표: x 오른쪽, y 보는 사람에게서 멀어지는 쪽, z 위쪽. 단위는 미터를 권장
- `eye`에서 `target`을 바라보며 `target`이 캔버스의 `center`에 놓인다

| 인자와 함수 | 뜻 |
|---|---|
| `focal` | 1 거리에서 본 1 단위의 캔버스 길이. 크면 망원, 작으면 광각 |
| `camera.project(points)` | 3차원 점을 캔버스 좌표로 변환 |
| `camera.depth(points)` | 시선 방향 거리 |
| `camera.scale_at(point)` | 그 지점에서 1 단위의 캔버스 길이. `art.place(scale=...)`에 넘김 |
| `camera.rays(canvas_points)` | 캔버스 점을 지나는 광선 방향 |
| `camera.to_world(vector)`, `camera.to_screen(vector)` | 화면 기준 방향(x 오른쪽, y 아래, z 보는 사람 쪽)과 세계 방향 사이 변환 |

- 눈높이보다 낮은 탁자 면을 보여 주려면 `eye`의 z를 `target`의 z보다 높게 둔다
- 3차원 점을 만드는 도우미(`frame`, `slab`, `disc`, `on_plane`, `hull`)는 `examples/desk.py`에 있다

## 3차원 조형

`atelier.sculpt`는 3차원 형태를 화소마다 광선으로 찾아 그림용 마스크와 빛을 만든다. 사람 몸 전체는 `atelier.mannequin`을 쓴다 (`references/figure.md`의 3차원 마네킹). `mannequin.build(scene, pose, physique=FEMALE 또는 MALE)`, `mannequin.dress(scene, marks, group, regions, thickness, smooth)`.

| 형태 | 만드는 법 |
|---|---|
| `Sphere(center, radius)` | 구 |
| `Ellipsoid(center, radii, rotation)` | 타원체 |
| `Capsule(a, ra, b, rb)` | 양 끝이 둥근 막대. 끝마다 반지름이 다를 수 있음 |
| `RoundBox(center, half, rounding, rotation)` | 모서리가 둥근 상자 |
| `Offset(shape, amount)` | 다른 형태를 일정 두께만큼 키운 형태. 옷, 껍질 |
| `HalfSpace(point, normal)` | 평면의 한쪽 전부. 파내기 전용. `carve(HalfSpace(p, n))`는 `n`이 가리키는 쪽을 남김 |
| `Intersection(*shapes)` | 형태들이 겹친 곳. 파내기 전용. 반공간 2개로 V 쐐기를 만듦 |
| `hanging_cloth(scene, group, top_from, top_to, drop, rng)` | 윗변에 매달려 세로 주름으로 늘어진 천 |

```python
scene = sculpt.Scene()
scene.add(shape, group="clay", blend=0.0, anchor=None, reach=None)
result = sculpt.render(art, camera, scene, step=2)
sculpt.paint(art, result, "clay", color, tint=shadow, deep=crease, sheen=0.3)
```

- 같은 `group`의 형태는 `blend` 폭만큼 녹아 이어진다. `anchor`를 주면 그 점에서 `reach`보다 먼 곳은 녹지 않는다
- `scene.carve(shape, group, blend)`는 그때까지 그 무리에 더한 형태에서 모양을 파낸다. 목선, 구멍, 홈
- `sculpt.paint()`는 밑색, 형태 그림자, 드리운 그림자, 골의 어둠, 광택, 윤곽선을 한 번에 칠하고 마스크를 반환한다
- 방향 행렬: `rotation(turn, lean, tilt)` 또는 `facing(up, front)`
- 그린 뒤에 덧칠할 때 쓰는 결과: `result.lit`, `result.shadow`, `result.ao`, `result.at(point)`, `result.visible(point)`, `result.disc(center, normal, radius)`
- 1280px에서 장면 하나가 10-40초 걸린다
- 카메라를 둘러쌀 만큼 큰 형태(넓은 바닥)도 그려진다
- `mannequin.build()`의 표지점: `chin`, `head_up`, `head_frame`, `skull`, `neck`, `nipples`, `navel`, `pelvis`, `pelvis_frame`, `chest`, `chest_frame`, 좌우 `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle`, 그리고 `forms`, `form_sides`, `leg_radii`, `arm_radius`
- `mannequin.dress(..., side=1 또는 -1)`은 한쪽 팔다리 형태만 키운다

## 포즈와 프레이밍

`atelier.staging` (`references/wardrobe.md`의 포즈 프리셋과 카메라 프레이밍).

```python
from atelier.staging import POSES, frame, pose_for
staging = pose_for("walking", physique, bust=0.95)      # pose, supports, hand_at, hand_behind_head
camera = frame(marks, physique, shot="knee", azimuth=30, elevation=5, aspect=1.5)
```

## 옷

`atelier.wardrobe` (`references/wardrobe.md`의 옷 만들기 원칙과 옷 목록). 옷 함수는 장면에 형태를 더하고 칠할 목록을 반환한다.

```python
from atelier import wardrobe as w
items = w.tee(scene, marks, physique) + w.jeans(scene, marks) + w.shoes(scene, marks, pose, physique, "sneaker")
# items: (group, colour, shadow) 또는 렌더링 뒤에 부를 함수(art, result)
```

## 치마와 드레스

`atelier.drape` (`references/wardrobe.md`의 치마와 드레스, 바람).

```python
from atelier import drape as d
items = d.sundress(scene, marks, wind=(0.35, -0.06, 0.05)) + d.scarf(scene, marks, wind=(0.35, -0.06, 0.05))
body = d.body_profile(marks, top, front, length, wind)  # 높이 t, 녹은 피부까지의 반지름 표 [줄, 방향]
profile = d.flare_profile(body, length, flare=0.30, hip_drop=0.145, ease=d.WAIST_EASE, press=None)
skirt = d.Flare(top, up, front, profile, length, folds=9, fold_depth=0.014, pleats=False, wind=(0, 0, 0),
                obstacles=[(point, radius), ...], fold_from=0.10)   # 직접 만드는 열린 껍질
d.ribbon(scene, group, points, across, half_width, thickness)    # 납작한 띠 (스카프 끝자락)
```

| 이름 | 하는 일 |
|---|---|
| `body_profile(...)` | 바람에 밀린 중심에서 잰 몸 둘레. 두 다리 사이는 볼록 껍질로 이음 |
| `flare_profile(...)` | 허리 여유, 엉덩이 따르기, A라인 퍼짐을 적용한 반지름 표와 손이 밀어 넣을 수 있는 한계 표 |
| `Flare` | 표를 따라 도는 열린 껍질. 주름, 바람, 손 자리 들임 |
| `Ribbon`, `ribbon()` | 경로와 너비 방향을 따라 얇은 상자를 이은 띠. 6마디씩 끊어 넣음 |

`atelier.wardrobe`의 `Surface(marks, regions)`는 고른 영역만 렌더링과 같은 방식으로 녹인 표면이다. `around()`와 `strap()`의 형태 목록 자리에 넣는다.

## 여러 사람

```python
from atelier.staging import pair_for, placed
a, b = pair_for("holding_hands", physique_a, physique_b)        # 둘의 Staging
art = nude.draw_cast(style, width, setting, [nude.Actor(sitter_a, pose_a, extras_a), nude.Actor(sitter_b, pose_b, extras_b)])
```

- `Scene.named(prefix)` 문맥 안에서 더한 형태는 무리 이름에 접두어가 붙는다
- `Render.within(prefix)`는 그 사람의 무리만 원래 이름으로 보여 주는 렌더 결과다
- `Scene.distance(points, group)`는 렌더링되는 그대로 녹은 무리 표면까지의 거리다

## 머리 돌리기

`atelier.turn` (`references/figure.md`의 머리 돌리기).

| 함수 | 하는 일 |
|---|---|
| `FaceDepth(axis, centre_y, half_width, half_height, depth, nose, nose_height, nose_spread)` | 머리 그림 하나의 깊이 모형 |
| `surface(points, turn, face)` | 얼굴 위의 점을 돌린 위치로 |
| `outline(points, turn, face, keep_until, chin_y)` | 얼굴 윤곽을 돌린 위치로 |
| `squeeze(point, turn, face)` | 그 자리에서 가로로 좁아지는 비율 |
| `clamp(turn)` | 각도를 ±35도로 제한 |

## 머리와 얼굴 템플릿

`examples/head_style.py` (`references/figure.md`의 머리와 얼굴 템플릿).

| 이름 | 하는 일 |
|---|---|
| `HeadLook(hair, hair_colour, eyes, brows, lips, eye_colour, earrings, hat, cigarette)` | 머리 모양, 머리색, 눈 모양, 눈썹, 입술, 눈동자 색, 귀걸이나 이어폰, 모자, 담배. 비운 항목은 머리의 기본값 |
| `head.styled(look)` | 머리 모듈(`portrait`, `portrait_male`)을 그 모양과 색으로 그리는 문맥 |
| `head.HAIR_STYLES` | 그 머리 모듈의 머리 모양 이름 |
| `hair_tones(colour)`, `eye_tones(colour)` | 이름이나 `"#RRGGBB"`에서 명암 색 |
| `portrait.draw(style, width, look)` | 흉상을 그 얼굴로 |
| `nude.Sitter(..., look=look)` | 전신 인물의 얼굴 |
| `outfits.Look(..., face=look)`, `outfits.Duo(..., faces=(a, b))` | 조합 예제의 얼굴 |
| `head.draw_head_back(art)` | 뒤에서 본 머리: 뒷머리, 모자, 연기 |

`examples/head_props.py`의 소품 (`references/figure.md`의 소품).

| 이름 | 하는 일 |
|---|---|
| `PropPlaces(skull, brim, mouth, ears, cable_join, cable_end, back_smoke)` | 머리 1개의 소품 위치 (그 머리의 그리기 단위) |
| `draw_beanie(art, tilt, places, under)` | 털모자. `under`는 모자 그림자를 받을 마스크 |
| `draw_cigarette(art, tilt, root, droop=24)` | 불붙은 담배. 불씨 끝 좌표를 반환 |
| `draw_smoke(art, tilt, start, drift=40)` | 흔들리며 오르는 연기 |
| `draw_earphones(art, tilt, places, in_sight)` | 유선 이어폰. `in_sight(side)`는 그 귀가 보이는지 |

`tilt`는 그리기 단위의 점을 캔버스로 옮기는 함수다. 머리 모듈의 `tilt`, 사물화에서는 `np.asarray`를 넘긴다.

## 분위기 층

`atelier.mood` (`references/styles.md`의 분위기 층).

| 이름 | 하는 일 |
|---|---|
| `art.grade = doomer` | 마감 뒤에 차갑고 빛바랜 색, 비네트, 필름 입자 |
| `vignette(shape, start, amount)` | 모서리로 갈수록 줄어드는 배율 |
| `film_grain(shape, amount, size_px, rng)` | 덩어리진 입자 |
| `GRADES` | 이름별 분위기 |

## 장소 도우미

`examples/scenes.py` (`references/wardrobe.md`의 장면).

| 이름 | 하는 일 |
|---|---|
| `panel_block(art, box, floors, columns, balconies, lit, haze, haze_colour)` | 정면에서 본 조립식 아파트: 판 이음매, 창 격자, 켜진 창과 그 빛, 발코니, 지붕 |
| `bare_tree(art, base, height, colour, depth, spread, angle, width)` | 잎 없는 나무. 가지가 2-3개로 갈라짐 |
| `snowfall(art, result=None)` | 내리는 눈. 자체 씨앗을 써서 장면이 바뀌어도 눈송이가 그대로. 눈송이를 초점에 넣어 회화풍에서도 남김 |
| `keep_fine_lines(art)` | 주변보다 어두운 가는 선을 찾아 초점에 넣음. 회화풍 붓질이 전선과 잔가지를 지우지 않게 |
| `looking_back(camera)` | 카메라가 인물 뒤에서 보면 -1, 앞에서 보면 +1 |
| `ground_edge(art, camera, reach, height=0)` | 바닥 먼 끝의 캔버스 y. `height`를 주면 그 끝에 선 벽의 높이 |

## 곡선 만들기

곡선은 `(N, 2)` 배열이다. 조절점은 `(x, y)` 또는 `(x, y, True)`이며 세 번째 값이 참이면 모서리가 된다.

| 함수 | 결과 |
|---|---|
| `spline(points, closed=False, samples=16)` | 조절점을 지나는 매끄러운 곡선. 모서리 표시 지점만 꺾임 |
| `ellipse(cx, cy, rx, ry, angle=0)` | 닫힌 타원 |
| `symmetric(half_points, axis_x)` | 절반 조절점을 좌우 대칭으로 이어 붙인 조절점 목록 |
| `mirror(points, axis_x)` | 조절점 좌우 반전 |
| `rotate(curve, degrees, center)` | 곡선 회전. 양수는 화면상 시계 방향 |
| `resample(curve, step)` | 곡선 위의 점을 일정 간격으로 재배치 |
| `tube(points)` | `(x, y, 굵기)` 조절점을 매끄럽게 이은 `(N, 3)` 배열. 보통 `art.tube()`를 대신 사용 |

직선 다각형은 `np.array([(x, y), ...], float)`를 그대로 쓴다.

## 마스크 만들기

마스크는 `(height, width)` 크기의 0-1 실수 배열이다. 곱하면 교집합, `np.maximum`은 합집합, `1 - mask`는 반전이다.

| 함수 | 결과 |
|---|---|
| `art.shape(curve)` | 닫힌 곡선 내부 |
| `art.shapes(curves)` | 닫힌 곡선 여러 개를 한 번에. 창문, 꽃, 타일처럼 수가 많을 때 사용 |
| `art.tube(points)` | `(x, y, 굵기)` 조절점을 지나는 둥근 띠. 팔다리, 손가락, 줄기, 손잡이 |
| `art.brush(curve, width, taper="both")` | 곡선을 따라 그은 획 |
| `art.everywhere()` | 화면 전체 |
| `art.ramp(start, end)` | 선형 그라데이션. start에서 0, end에서 1 |
| `art.blob(center, radius)` | 중심이 1이고 반경에서 0이 되는 둥근 번짐 |
| `art.noise(cell, octaves=3)` | 0-1 범위의 매끄러운 난수 무늬. `cell`은 덩어리 크기 |

## 마스크 가공

| 함수 | 결과 |
|---|---|
| `art.feather(mask, radius)` | 가장자리를 부드럽게 |
| `art.grow(mask, amount)` | 가장자리를 바깥으로 확장. 음수는 축소 |
| `art.move(mask, dx, dy)` | 평행 이동. 드리운 그림자와 역광 테두리에 사용 |
| `art.threshold(field, level, softness=0.05)` | 무늬를 마스크로 변환. 구름에 사용 |

자주 쓰는 조합:

```python
cast = art.move(caster, 6, 14) * receiver            # 드리운 그림자
rim = figure * (1 - art.move(figure, -5, 2))         # 오른쪽 가장자리 띠 (역광)
band = mask * (1 - art.move(mask, 0, 9))             # 위쪽 가장자리 띠 (눈꺼풀 그림자)
fade = mask * art.ramp((0, 400), (0, 900))           # 아래로 갈수록 짙어짐
```

## 칠하기

| 함수 | 동작 |
|---|---|
| `art.part(shape, color, shade=True, outline=True, bulge=None, shadow_tint=None, line_color=None, line_width=None)` | 부품 추가. 밑색, 형태 그림자, 외곽선을 한 번에 처리하고 마스크를 반환 |
| `art.paint(mask, color, opacity=1.0)` | 밑색 레이어에 색칠 |
| `art.shadow(mask, tint=None, opacity=1.0)` | 그림자 레이어에 곱하기 색 적용 |
| `art.light(mask, color="#FFFFFF", opacity=1.0)` | 빛 레이어에 스크린 색 적용 |
| `art.form_shadow(mask, bulge=None, tint=None, clip=None)` | 형태 그림자만 따로 적용. `clip`은 그림자가 떨어질 범위 |
| `art.erase_line(mask)` | 마스크 아래의 선을 지움. 두 부품을 하나로 이어 보이게 할 때 사용 |
| `art.shade_by(mask, lit, tint)` | 빛 값(1 밝음, 0 이하 어두움)에 따라 화풍대로 명암을 넣음 |
| `art.ink(alpha, color)` | 만들어 둔 선 마스크를 선화 레이어에 얹음 |
| `art.line_color(fill)` | 해당 색 부품에 쓰이는 화풍의 선 색 |
| `art.mark(curve, color, width, taper="both", opacity=1.0)` | 밑색 레이어에 획. 모든 화풍에서 보임 |
| `art.blur(radius)` | 지금까지 그린 전부를 흐림. 배경을 뒤로 밀 때 사용 |
| `art.focus_on(mask)` | 초점 영역 지정 |

`part()`의 `shape`에는 곡선과 마스크 모두 넣을 수 있다.

`bulge`의 두 가지 방식:

| 값 | 입체 | 쓰임 |
|---|---|---|
| 생략 | 풍선처럼 부푼 입체. 원은 구, 띠는 원기둥 | 과일, 팔다리, 몸, 구름, 수관, 병 |
| 반경 | 가장자리만 둥근 납작한 입체 | 옷, 얼굴, 벽, 천, 땅 |

## 선 긋기

| 함수 | 동작 |
|---|---|
| `art.line(curve, color=None, width=None, taper="both", opacity=1.0)` | 선화 레이어에 획. 선화가 없는 화풍에서는 생략됨 |
| `art.outline(mask, color=None, width=None, clip=None)` | 마스크 외곽선. `clip`으로 일부 구간만 남김 |

`taper` 값:

| 값 | 굵기 변화 |
|---|---|
| `both` | 양 끝이 가늘다 |
| `start` | 시작이 가늘다 |
| `end` | 끝이 가늘다 |
| `none` | 일정하다 |

## 출력

| 함수 | 동작 |
|---|---|
| `art.save(path, stage="final", downscale=1)` | 한 단계를 이미지로 저장 |
| `art.save_stages(path)` | 5단계를 가로로 이어 저장 |
| `art.compose(stage)` | 한 단계를 실수 RGB 배열로 반환 |

| `stage` | 내용 |
|---|---|
| `line` | 종이 위의 밑그림. 선화에 색 경계를 연필 선으로 더해 표시 |
| `flat` | 밑색과 선 |
| `shade` | 그림자 추가 |
| `light` | 빛 추가 |
| `final` | 화풍별 후보정 적용, 그 뒤 `art.grade` |

## 색 도구

| 함수 | 결과 |
|---|---|
| `mix(color_a, color_b, amount)` | 두 색의 혼합 |
| `adjust(color, hue=0.0, saturation=1.0, value=1.0)` | 색상 이동, 채도와 명도 배율 |
| `rgb(color)` | 0-1 범위의 RGB 배열 |
