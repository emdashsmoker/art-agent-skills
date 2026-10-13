# 엔진 API

`scripts/codepainter/` 패키지의 공개 함수 목록. 좌표 단위는 픽셀, x는 오른쪽, y는 아래쪽이 양수. 색은 `"#rrggbb"` 문자열 또는 0-1 범위 RGB. 마스크는 캔버스 크기의 float32 배열(0-1).

## 목차

- Painting (캔버스)
- geometry (곡선)
- shading (명암)
- color (색)
- styles (화풍)
- fx (후보정)
- objects (상자와 원통)
- backdrop (배경)
- scenery (자연물)
- sets (인물 장면 배경)
- painterly (붓질)

## Painting

`from codepainter import Painting`

| 호출 | 역할 |
|---|---|
| `Painting(width, height, background="#ffffff")` | 색 레이어 1장, 선 레이어 1장 생성 |
| `.mask(curve)` | 닫힌 곡선을 안티에일리어싱 마스크로 변환 |
| `.fill(mask, color, opacity=1.0, mode="normal")` | 마스크 영역에 색 칠하기, mode는 normal, multiply, screen, add, overlay, soft_light |
| `.part(mask, color)` | 불투명 조각 채우기, 가려진 선을 자동 삭제 |
| `.stroke(path, width, color, taper=(0.25, 0.35), tip=0.08, opacity=1.0, layer="line", clip=None)` | 필압이 있는 선 1개 |
| `.outline(curve, width, color, shade_side=(0.6, 0.7), contrast=0.5, closed=True)` | 빛 반대쪽이 굵어지는 외곽선 |
| `.outline_mask(mask, width, color, shade_side, contrast=0.5, keep=None)` | 마스크 가장자리 외곽선, 여러 조각을 합친 형태용 |
| `.erase_lines(mask)` | 마스크 영역의 선 삭제 |
| `.flatten(line_opacity=1.0)` | 색과 선을 합친 HxWx3 이미지 |
| `.line_art(paper="#ffffff")` | 선 레이어만 본 이미지 |
| `.snapshot(name)` | 현재 상태를 과정 단계로 기록 (`.stages`에 저장) |
| `.save(path, image=None)` | PNG 저장, image 생략 시 flatten 결과 저장 |

- `.color`는 HxWx3 배열, 직접 수정 가능
- `stroke`의 `width`에 숫자를 주면 `taper`로 양 끝이 가늘어짐
    + 점 개수와 같은 길이의 배열을 주면 굵기를 직접 지정
- `layer="line"`은 화풍이 굵기와 색을 바꾸거나 생략하는 외곽선용
    + `layer="color"`는 속눈썹, 입술선, 머리카락 가닥처럼 그림 자체에 속하는 표시용
- `fill`의 `mask`는 곱셈으로 잘라 사용
    + 예시 : `painting.fill(shadow * part_mask, color)`는 조각 내부에만 칠함
- 작은 다각형 수백 개(창, 눈송이, 타일)는 `raster.fill_many(polygons, painting.shape)`로 마스크 1장에 한 번에 래스터화

## geometry

`from codepainter import geometry as geo`. 모든 함수는 (N, 2) 배열을 반환.

| 함수 | 역할 |
|---|---|
| `smooth(points, closed=False, corners=())` | 제어점을 지나는 매끄러운 곡선, corners는 각진 채로 둘 제어점 번호 |
| `ellipse(center, rx, ry, angle=0.0)` | 타원 |
| `arc(center, rx, ry, start, end)` | 열린 호, 각도는 라디안 |
| `bent_line(start, end, bend=0.0)` | 한쪽으로 휜 선, bend는 길이 대비 휨 비율 |
| `lock(root_a, root_b, tip, bend=0.0, belly=0.0)` | 끝이 뾰족한 닫힌 형태 (머리카락 뭉치, 잎, 불꽃, 천 주름) |
| `needle(start, end, width)` | 양 끝이 뾰족한 렌즈 형태 (하이라이트 줄기, 풀잎, 물빛) |
| `tube(path, left, right=None, caps=(True, True))` | 굵기가 변하는 관 (팔다리, 꼬리, 나뭇가지, 길) |
| `symmetric(profile, axis_x)` | 한쪽 윤곽을 세로축에 대칭시킨 회전체 (병, 그릇, 과일) |
| `quad_map(quad)` | 0-1 좌표를 벽, 바닥 사각형 위로 옮기는 원근 변환 함수 |
| `grid_cells(columns, rows, margin, inset)` | 창문, 타일용 0-1 좌표 격자 |
| `rounded_rect(x0, y0, x1, y1, radius)` | 둥근 모서리 사각형 (화면, 키, 버튼) |
| `Oblique(origin, across, back, up, scale)` | 사투상 좌표계, `.place(points3)`와 `.box(x, y, z, 폭, 깊이, 높이)` 제공 |
| `transform(points, scale, angle, translate, pivot)` | 확대, 회전, 이동 |
| `offset(path, distance)` | 법선 방향 평행 이동 |
| `wobble(path, amplitude, seed)` | 손떨림을 흉내 낸 미세 흔들림 |
| `subpath(path, start, end)` | 0-1 구간의 부분 경로 |
| `resample(path, count)` | 같은 간격으로 재표본 |
| `lerp(a, b, t)` | 두 점 또는 두 경로의 보간 |

- `bend`가 양수이면 아래로 내려가는 선은 화면 왼쪽으로, 오른쪽으로 가는 선은 아래쪽으로 휨
    + 음수이면 반대쪽으로 휨
    + 부호가 헷갈리면 렌더링으로 확인 후 반전
- `tube`의 `left`, `right`는 경로를 따라 같은 간격으로 놓인 반폭 목록
    + `left`는 아래로 내려가는 경로 기준 화면 왼쪽
- `quad_map`의 사각형은 좌상, 우상, 우하, 좌하 순서
    + 한 점으로 닫히는 사각형에는 사용 불가, 먼 변에 길이가 있어야 함
- 좌우 대칭 형태는 `symmetric` 사용, 또는 한쪽 제어점을 `(2 * 중심x - x, y)`로 뒤집어 생성

## shading

`from codepainter import shading as sh`. 기본 광원은 `DEFAULT_LIGHT = (-0.55, -0.62, 0.56)` (좌상단 앞쪽).

| 함수 | 역할 |
|---|---|
| `inflate(mask, bevel=None, smoothing=0.18)` | 마스크를 부풀린 높이맵, bevel 생략 시 완전히 둥근 형태 |
| `lighting(mask, light, bevel=None, depth=1.0, height=None)` | 램버트 조명값(-1 - 1) |
| `shadow_from_light(lit, threshold=0.25, softness=0.02)` | 조명값이 기준보다 낮은 영역의 그림자 마스크 |
| `cast_shadow(occluder, receiver, offset, softness=0.0)` | 가리는 조각이 받는 조각 위에 드리우는 그림자 |
| `rim(mask, direction, width, softness=0.0)` | 지정 방향을 향한 가장자리 띠 (림라이트, 가장자리 하이라이트) |
| `occlusion(occluder, receiver, radius)` | 맞닿는 부위의 부드러운 어둠 |
| `ground_shadow(mask, drop, squash, lean, softness)` | 물체가 탁자나 바닥에 드리우는 납작한 그림자 |
| `edge_band(mask, width, shade_side, contrast)` | 마스크 가장자리 띠, `outline_mask`의 내부 계산 |
| `melt(mask, radius)` | 합친 마스크의 홈과 모서리를 녹여 한 덩어리로 만듦 |
| `linear_ramp(shape, start, end)` | start에서 0, end에서 1이 되는 직선 그라데이션 |
| `radial_ramp(shape, center, radius)` | 중심 0, 반지름에서 1이 되는 원형 그라데이션 |
| `blur(image, sigma)` | 가우시안 블러 |
| `shift(mask, dx, dy)` | 마스크 이동 |
| `smoothstep(low, high, value)` | 부드러운 계단 함수 |

- `bevel`은 가장자리에서 면이 계속 솟는 거리(픽셀)
    + 공, 얼굴, 과일은 생략, 몸통과 판처럼 윗면이 평평한 형태는 폭의 20-30%
- `smoothing`은 뾰족한 형태에서 능선 자국이 보이면 0.4 이상으로 상향
- `light`의 x, y는 화면에서 빛이 오는 쪽을 가리키는 방향
    + 왼쪽 위 광원은 x와 y가 음수, z는 정면성

## color

`from codepainter import color`

| 함수 | 역할 |
|---|---|
| `rgb(value)` | 문자열 또는 튜플을 RGB 배열로 변환 |
| `mix(a, b, amount)` | 두 색 혼합 |
| `adjust(color, hue=0.0, saturation=1.0, value=1.0)` | 색상 회전, 채도와 명도 배율 |
| `shadow_of(color, tint, depth=1.0)` | 그림자색 (보라 기운 곱하기, 채도 상향) |
| `light_of(color, tint, amount=0.5)` | 하이라이트색 (따뜻한 흰색 쪽으로 이동) |

## styles

`from codepainter.styles import get_style, shade_form, paint_part, line_color, finish, flat_version`

| 함수 | 역할 |
|---|---|
| `get_style(name, **overrides)` | `anime`, `illust`, `painterly` 프리셋 반환, 수치 덮어쓰기 가능 |
| `paint_part(painting, curve, color, style, light, line_width=2.5, bevel=None, shade=True, **shading)` | 조각 1개를 마스크, 밑색, 음영, 외곽선까지 1회 호출로 완성, 마스크 반환 |
| `shade_form(painting, mask, base, style, light, bevel=None, depth=1.0, threshold=None, shadow_color=None, height=None, terminator=None)` | 이미 칠한 조각에 화풍별 형태 음영 적용 |
| `line_color(style, fill_color, ink)` | 조각 색에 맞춘 외곽선 색 |
| `finish(painting, style, seed=0, importance=None, **brush_options)` | 화풍별 후보정, 완성 이미지 반환 |
| `flat_version(style)` | 빛을 끈 화풍, 밑색 단계 확인용 |
| `gloss(painting, mask, light, size=0.16, reach=0.45, color, opacity, softness)` | 둥근 조각의 빛 쪽 광택 점 |

- `threshold`를 높이면 그림자 면적이 증가
    + 기본값은 화풍의 `shadow_threshold`
- `depth`는 입체감 과장 배율

## fx

`from codepainter import fx`. 입력과 출력은 HxWx3 이미지.

| 함수 | 역할 |
|---|---|
| `fbm(shape, scale=1.0, octaves=4, seed=0, stretch=(1.0, 1.0))` | 구름 모양 노이즈(0-1), stretch는 (세로, 가로) 늘림 |
| `glow(image, radius, strength)` | 전체 확산광 |
| `bloom(image, threshold, radius, strength)` | 밝은 부분만 번지는 빛 |
| `grade(image, contrast, saturation, shadows, highlights, gamma)` | 대비, 채도, 명부와 암부 색조 |
| `paper(image, amount, seed)` | 종이 질감 |
| `grain(image, amount, seed)` | 필름 입자 |
| `vignette(image, strength)` | 가장자리 어둡게 |
| `doomer(image, seed=0, strength=1.0)` | 두머 무드 : 탈색, 청록 그늘, 바랜 검정, 비네트, 입자, 따뜻한 빛만 색 유지 |
| `warm_lights(image)` | 따뜻한 빛(가로등, 켜진 창) 정도 0-1 |
| `stage_sheet(stages, path, columns=3)` | 과정 단계를 한 장으로 정리 |

## objects

`from codepainter import objects`

| 함수 | 역할 |
|---|---|
| `paint_box(painting, faces, color, style, tones, line_width=2.2, top_color=None)` | `Oblique.box` 결과를 면별 명도로 칠함, 면 마스크 사전 반환 |
| `paint_cylinder(painting, center, radius, height, color, style, light, squash=0.36, hollow=None)` | 위에서 본 원통, `hollow`는 열린 윗면의 안쪽 색 |

## backdrop

`from codepainter import backdrop`. Painting의 색 레이어에 직접 그림.

| 함수 | 역할 |
|---|---|
| `gradient(painting, start_color, end_color, start=None, end=None)` | 직선 그라데이션 배경 |
| `mottle(painting, color, amount, scale, seed)` | 얼룩 변화, 평평한 배경의 인공적 느낌 제거 |
| `glow(painting, center, radius, color, opacity)` | 부드러운 빛 웅덩이 |
| `window_light(painting, corner, size, slant, panes, bar, color, opacity, softness)` | 벽에 비친 창문 빛 |
| `bokeh(painting, colors, count, radius, opacity, seed)` | 초점 밖 빛망울 |

## scenery

`from codepainter import scenery`

| 함수 | 역할 |
|---|---|
| `ridge(shape, base_y, relief, roughness, seed, tilt)` | 산맥이나 언덕 실루엣 (닫힌 다각형) |
| `clouds(shape, coverage, scale, seed, stretch, softness, band)` | 구름 마스크 |
| `conifer(base, height, width, tiers, seed)` | 침엽수 1그루의 다각형 목록 |
| `blades(region_box, count, length, seed, lean)` | 풀잎의 (뿌리, 끝, 휨) 목록 |
| `reflect(painting, waterline, depth, ripple, darken, tint, seed)` | 수면 반영 |
| `noise_line(count, roughness, octaves, seed)` | 1차원 프랙탈 노이즈 |
| `puffs(painting, center, width, height, count, seed, flat_base)` | 뭉게구름, 덤불의 (마스크, 덩이 마스크 목록) |
| `foliage(painting, center, width, height, count, seed)` | 나무 수관의 (마스크, 잎 뭉치 마스크 목록) |
| `scatter(region_box, count, seed, near_scale, far_scale)` | 가까울수록 커지는 (x, y, 크기) 목록 |
| `skyline(shape, base_y, heights, widths, seed)` | 먼 도시 실루엣 |
| `street_wall(base_near, vanishing, near, far, height)` | 1점 투시 거리의 건물 벽 사각형 |
| `windows(painting, quad, columns, rows, lit_colors, dark, lit, margin, inset, seed)` | 벽 위 창문 격자, 불 켜진 창 마스크 반환 |
| `panel_facade(painting, quad, floors, bays, seed, lit, wall, shade, balcony_every, stairs_every, line_width)` | 패널 아파트 한 면 : 이음매, 창, 발코니, 계단실, 켜진 창 마스크 반환 |
| `bare_tree(painting, base, height, seed, color, birch, lean, depth, width)` | 잎 없는 겨울나무, `birch=True`는 흰 줄기의 자작나무 |
| `snowfall(painting, count, seed, size, color, opacity, keep_clear)` | 내리는 눈, `keep_clear` 마스크(얼굴) 위는 걷어냄 |
| `wire(start, end, sag, count)` | 두 점 사이에 늘어진 전깃줄 경로 |
| `sodium_lamp(painting, foot, height, side, ground, color)` | 휘어진 팔의 나트륨 가로등과 바닥 빛 웅덩이, 등 머리 위치 반환 |

## sets

`from codepainter import sets`. 인물 장면용 전체 배경, 사용법은 `references/clothing-and-scenes.md`.

| 함수 | 역할 |
|---|---|
| `beach(painting, style, horizon, seed)` | 한낮 바다와 모래사장 |
| `bedroom(painting, style, floor, seed)` | 저녁 침실 벽, 창빛, 커튼, 나무 바닥 |
| `office(painting, style, floor, seed)` | 통유리 너머 빌딩, 화분, 카펫 |
| `night_street(painting, style, horizon, seed)` | 밤거리, 불 켜진 창, 가로등, 젖은 도로 |
| `cafe(painting, style, floor, seed)` | 카페 벽, 창 너머 도시, 펜던트 조명, 타일 바닥 |
| `park(painting, style, horizon, seed)` | 한낮 공원, 나무 두 줄, 잔디, 산책로 |
| `panel_block(painting, style, horizon, seed, lamp, lit)` | 두머 단지 마당, 패널 아파트, 앙상한 나무, 나트륨등, 눈 |
| `light_figures(painting, figures, info, style)` | 인물에 장면 주변광과 테두리 빛 적용 |

- 배경 함수는 `SetInfo(horizon, ground, grade, ambient, rim)` 반환
- `SETS`는 이름에서 함수로의 사전

## painterly

`from codepainter import painterly`

- `repaint(source, seed=0, importance=None, ground=None, detail=1.0, bristle=1.0, impasto=1.0, canvas=1.0, layers=BRUSH_LAYERS)`
    + source를 붓질 단위로 다시 그린 이미지 반환
    + `finish`가 회화풍에서 자동 호출하므로 직접 호출은 세부 조정 시에만 필요
