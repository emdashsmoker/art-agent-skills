# paintkit API

`sys.path.insert(0, '<skill>/scripts')` 후 `from paintkit import ...`로 사용한다.
색은 `'#rrggbb'`나 `'#rgb'` 문자열 또는 0-1 실수 3개. 좌표는 픽셀, 원점은 좌상단, y는 아래가 양수.

## 목차

1. Canvas
2. 마스크 연산
3. 명암 (shading)
4. 색 (color)
5. 배경 요소 (scenery)
6. 도시 (city)
7. 현대 사물 (solids)
8. 마감 (finish)
9. 두머 무드 (doomer)
10. 폭 프로파일
11. 설정값

## 1. Canvas

`Canvas(width=1024, height=1280, background='#ffffff')`

### 도형 만들기 (마스크 반환)

| 메서드 | 설명 |
|---|---|
| `blob(points, smooth=True)` | 제어점을 지나는 닫힌 면. `smooth=False`는 직선 다각형 |
| `polygon(*polygons)` | 다각형 여러 개의 합집합 |
| `ellipse(cx, cy, rx, ry=None, rotation_deg=0)` | 타원 |
| `rect(x0, y0, x1, y1, radius=0)` | 축에 나란한 사각형. `radius`로 모서리를 둥글린다 (화면, 키, 버튼) |
| `ribbon(points, width, profile='taper', smooth=True)` | 중심선을 따라가는 가변 폭 띠 |
| `ribbons([(points, width, profile), ...])` | 띠 여러 개를 한 번에 (빠름) |
| `contour(points, left, right, bend=0)` | 중심선 양쪽 폭을 따로 정하는 띠. `left`, `right`는 `[(t, px), ...]` (t는 0-1 위치, left는 첫 점에서 끝 점으로 걸을 때 왼손 쪽). `bend`는 꺾인 관절을 둥글리는 반지름 px. 좌우가 비대칭인 팔다리, 비스듬한 병 |
| `empty()`, `full()` | 전부 0, 전부 1 |

### 스칼라 필드 (0-1 배열 반환)

| 메서드 | 설명 |
|---|---|
| `linear(p0, p1)` | p0에서 0, p1에서 1 |
| `radial(center, rx, ry=None, rotation_deg=0)` | 중심 1, 가장자리 0 |
| `noise(scale=64, octaves=4, seed=None, stretch=(1,1))` | 부드러운 잡음. `stretch=(6,1)`은 가로 줄무늬 |
| `ramp(field, *stops)` | 필드를 색 그라데이션 이미지로. stops는 색 목록 또는 `(위치, 색)` 목록 |

필드는 마스크와 곱해서 쓰거나 `ramp`로 색 이미지를 만들어 `fill`의 color로 넘긴다.

### 칠하기

| 메서드 | 설명 |
|---|---|
| `fill(mask, color, opacity=1)` | 새 표면을 칠한다. 그 밑의 선을 지운다 |
| `tint(mask, color, mode='multiply', opacity=1)` | 기존 색을 바꾼다. mode: `normal`, `multiply`, `screen`, `overlay`, `soft_light`, `add` |
| `paint_form(mask, color, light, shadow=0.12, soft=1.2, line_width=2.5, shadow_color=None, line_color=None, rim=0)` | 칠 + 형태 그림자 + 외곽선을 한 번에. 소품을 가장 빨리 추가하는 방법 |
| `paint_volume(mask, color, light, bulge=None, depth=1, gloss=0, shadow_color=None, light_color=None, line_width=0)` | 그림자-기본색-밝은색이 연속으로 이어지는 둥근 음영. 과일, 병, 천, 살결처럼 부피가 중요한 대상에 쓴다. `bulge`는 둥글림 반지름 px, `gloss`는 광택 점 |
| `paste(source, quad, opacity=1)` | 평면 그림(Canvas 또는 이미지)을 네 점 사각형에 원근으로 붙인다. 새 표면으로 취급되어 밑의 선을 지운다. 붙인 영역 마스크를 돌려준다 |
| `ink(points, width, color, profile='taper', opacity=1, clip=None)` | 펜 선 1획 |
| `ink_mask(mask, color, opacity=1, clip=None)` | 임의 마스크를 선 레이어에 올림 |
| `outline(mask, width, color, weight_dir=(0.4,1), weight_gain=0.45, wobble=0.12, clip=None)` | 마스크 외곽을 굵기 변화 있는 선으로. `weight_dir` 방향 쪽이 굵어진다 |

- `color` 인자는 단색 또는 (H, W, 3) 이미지(그라데이션)
- `clip`은 선을 특정 마스크 안으로 제한한다

### 범위 추적과 출력

| 메서드 | 설명 |
|---|---|
| `track(name)` | 이후 모든 `fill`의 합집합을 기록 시작 |
| `tracked(name, stop=True)` | 기록된 마스크 반환 |
| `flatten(line_opacity=1)` | 색 + 선 합성 이미지 |
| `save(path)` | 마감 없이 저장 |

속성: `cv.color` (H,W,3), `cv.line_alpha` (H,W), `cv.size`, `cv.width`, `cv.height`.
배경 흐림은 `cv.color = blur(cv.color, 2.0)`.

## 2. 마스크 연산

`from paintkit import blur, shift, grow, smoothstep`

| 함수 | 설명 |
|---|---|
| `blur(mask, radius)` | 가우시안 흐림. 이미지에도 사용 가능 |
| `shift(mask, dx, dy)` | 평행 이동 |
| `grow(mask, px)` | 양수면 팽창, 음수면 수축 |
| `smoothstep(field, low, high)` | 필드를 부드러운 경계의 마스크로 |
| `raster.fill_holes(mask, threshold=0.5)` | 완전히 둘러싸인 빈틈만 메운다. 바깥으로 열린 틈은 그대로 |

## 3. 명암 (shading)

`from paintkit import shading`. 빛 방향은 표면에서 광원을 향하는 2D 벡터. 왼쪽 위 광원은 `(-1, -1)`.

| 함수 | 설명 |
|---|---|
| `crescent(mask, toward_light, distance, soft=0)` | 빛 반대쪽 가장자리의 초승달 그림자. 셀 음영의 기본 |
| `rim(mask, toward_light, width, soft=0)` | 빛 쪽 가장자리의 얇은 띠. 역광, 테두리 빛 |
| `cast(caster, receiver, offset, soft=0)` | caster가 receiver에 드리우는 그림자. offset은 빛 반대 방향 px |
| `form_shadow(mask, toward_light, threshold=0.55, soft=0.02)` | 형태를 부풀려 계산한 명암 경계. 둥근 덩어리에 적합 |
| `form_light(mask, toward_light)` | 위의 원본 필드 (-1..1). `band(field, t, soft)`로 직접 자를 때 |
| `volume(mask, toward_light, bulge, height=0.9)` | 0(깊은 그림자)-1(빛) 연속 필드. `cv.ramp`에 넣어 직접 색을 입힐 때. `height`가 낮을수록 빛이 옆에서 스친다 |
| `occlusion(neighbor, receiver, radius)` | 이웃 물체 근처의 부드러운 접촉 그림자 |
| `inner_glow(mask, radius)` | 가장자리 안쪽의 부드러운 띠 |

결과는 마스크이므로 `cv.tint(mask, shadow_of(color), 'normal', 0.9)`처럼 적용한다.

## 4. 색 (color)

`from paintkit import rgb, adjust, shadow_of, light_of, mix`

| 함수 | 설명 |
|---|---|
| `shadow_of(color, depth=1)` | 그림자색: 어둡게, 채도 약간 높게, 색상은 차가운 쪽으로 |
| `light_of(color, amount=1)` | 밝은색: 밝게, 채도 약간 낮게, 색상은 따뜻한 쪽으로 |
| `adjust(color, lightness=0, chroma=1, hue=0, toward_hue=None, toward=0)` | OKLCH 공간에서 명도 가감, 채도 배율, 색상 회전 |
| `mix(a, b, t)` | 두 색의 선형 혼합 |

피부 그림자는 `paintkit.figure.look.skin_shadow(color)`를 쓴다 (붉은 쪽으로 이동).

## 5. 배경 요소 (scenery)

`from paintkit import scenery`. 주인공보다 먼저 그린다.

| 함수 | 설명 |
|---|---|
| `sky(cv, top, bottom, horizon_y=None)` | 세로 그라데이션 하늘 |
| `cumulus(cv, center, width, height, color, shade, light, puffs=22, edge=1)` | 뭉게구름 1개 (2색조) |
| `cloud_bank(cv, y_range, count, size, color, shade, light, seed)` | 뭉게구름 여러 개 |
| `clouds(cv, y_range, color, coverage, scale, edge, opacity)` | 잡음 기반의 흐릿한 구름층 (새털구름, 안개) |
| `sun_glow(cv, center, radius, color, opacity)` | 광원 주변의 빛 번짐 |
| `light_rays(cv, origin, angle_deg, spread_deg, count)` | 빛줄기 |
| `bokeh(cv, count, colors, radius, region, opacity)` | 초점 밖 빛망울 |
| `mountains(cv, base_y, height, color, jagged, scale, snow, light)` | 산 능선. 뒤쪽일수록 밝고 푸르게 겹친다 |
| `hills(cv, base_y, amplitude, color, scale)` | 완만한 언덕 |
| `horizon_sea(cv, horizon_y, far, near, sparkle)` | 수평선 아래 바다와 윤슬 |
| `water_reflection(cv, water_y, darken, ripple, tint)` | 수면 위쪽 그림을 뒤집어 비춤. 비출 대상을 모두 그린 뒤 호출 |
| `tree(cv, base, height, kind='round'|'pine', leaf, trunk, light, line_width=0)` | 나무. `round`는 잎 덩어리 3색조 |
| `grass(cv, y_range, count, colors, blade)` | 풀잎 |
| `leaves(cv, center, reach, count, colors, size, blur_px)` | 잎 무더기. 모서리에 두면 화면 틀이 된다 |
| `petals(cv, count, color, size, region, blur_range)` | 흩날리는 꽃잎 |
| `wash_backdrop(cv, colors, scale, strength)` | 추상적인 색 번짐 배경 |

## 6. 도시 (city)

`from paintkit import city`. 상세와 예시는 `references/city.md`.

| 함수 | 설명 |
|---|---|
| `facade(width_m, height_m, wall, glass, lit, lit_ratio, shop, resolution, seed)` | 건물 한 면을 평면 Canvas로 |
| `skyline(cv, base_y, height, width, color, lit, lit_ratio, window_px, seed)` | 먼 건물 실루엣 한 줄 |
| `Perspective(vanishing, focal, eye)` | 1점 투시 카메라. `project`, `scale`, `wall_quad`, `front_quad`, `ground_quad`, `quad(corners)` (임의 3D 사각형) |
| `Camera(center, focal, position, yaw=0, pitch=0)` | 돌리고 기울이는 카메라 (2점, 3점 투시). `project`, `quad`, `depth`, `scale_at`, `vanishing_point`, `horizon_y` |
| `project_polygon(view, points, near=0.3)` | 카메라 뒤로 이어지는 평면 다각형을 앞부분만 남겨 투영 |
| `ground_rects(cv, view, rects, y=0)` | 땅 위 직사각형 `[(x0, z0, x1, z1)]` 마스크 |
| `street(cv, view, ...)` | 도로, 보도, 양쪽 건물 줄 |
| `road_texture(width_m, length_m, asphalt, line, lanes, crosswalk_at)` | 위에서 본 도로 평면 |
| `street_lamp(cv, view, x, z, height, glow, on)` | 가로등 |

## 7. 현대 사물 (solids)

`from paintkit import solids`. 상세와 조리법은 `references/objects.md`.

| 함수 | 설명 |
|---|---|
| `box(cv, view, origin, size, color, light_from, top_color, edge, turn=0)` | 바닥에 놓인 상자. 보이는 면만 칠하고 면 사각형과 마스크를 돌려준다. `turn`으로 세로축 회전 |
| `patch(quad, left, top, right, bottom)` | 면의 일부를 비율로 잘라낸 사각형 (원근 보정) |
| `disc(cv, view, center, y, radius, depth_radius)` | 수평면에 누운 원 |
| `contact_shadow(cv, view, center, y, radius, ...)` | 접지 그림자 |
| `cylinder(cv, view, center, y, radius, height, color, top_radius, light, gloss, top_color, hollow)` | 선 원통, 원뿔대, 열린 컵 |
| `barrel(cv, view, center, z_back, z_front, radius, color, ...)` | 화면을 향한 원통 (렌즈) |
| `slab(cv, view, points, y, thickness, color, light, ...)` | 위에서 본 외곽선을 세운 납작한 물체 |
| `flat_shape(cv, view, points, y)`, `flat_path(view, points, y)` | 수평면 위 외곽선 마스크, 경로 |

인물 리그의 새 도구 (상세는 `references/fullbody.md`)

| 함수 | 설명 |
|---|---|
| `figure.aim(turn, upper, lower)` | 3D 방향의 팔다리를 화면 각도와 길이 비율로. 앉은 자세, 단축, 옆모습과 뒷모습의 팔 |
| `figure.seen_from_behind(pose)` | 몸 뒷면이 관객을 향하는지 (`turn`이 약 105도 이상). 장면 코드에서 뒷모습 전용 소품을 고를 때 |
| `figure.framing(size, shot, center=0.5, headroom=0.55)` | 전신 리그를 줌한 `pelvis`, `height`. shot: `full`, `knee`, `thigh`, `waist`, `bust`, `face` |
| `figure.fit(box, pose, sex, align, scale)` | 포즈 인물을 상자에 가장 크게 넣는 `pelvis`, `height` |
| `figure.thirds(size, column, margin)` | 3분할선 중심 상자 (`left`, `center`, `right`) |
| `figure.group(box, poses, sexes, scales, gap, shot=None, headroom)` | 여러 인물을 한 바닥선에 나란히 놓는 배치 목록. `shot='waist'` 등으로 단체 클로즈업 |
| `figure.pose_bounds(figure)` | 인물이 차지하는 화면 상자 |
| `figure.poses.*` | 포즈 프리셋 12종 (`contrapposto`, `arms_crossed`, `hands_on_hips`, `hands_in_pockets(pouch=False)`, `stretch`, `walk`, `run`, `cross_legged_seat`, `squat`, `sit_floor`, `lean_wall`, `lie_side`). `poses.POSES`는 이름과 함수의 표 |
| `wardrobe.bikini`, `lingerie`, `hoodie`, `crop_top`, `hot_pants`, `suit` | 의상 (`references/fullbody.md` 11절) |
| `wardrobe.long_coat`, `padded_jacket`, `scarf`, `beanie`, `boots` | 겨울 외투, 목도리, 비니, 부츠. `beanie`는 머리 다음에 칠해진다 (`references/fullbody.md` 11절) |
| `Figure(sex='male')`, `MALE_FACE`, `MALE_HAIR` | 남성 체형과 얼굴, 머리 프리셋 |
| `figure.hairstyle(name, **changes)` | 이름 붙은 헤어 24종 (`FEMALE_STYLES` 12, `MALE_STYLES` 12, 합친 표 `HAIRSTYLES`). 묶음머리, 클리퍼 컷 포함 (`references/fullbody.md` 16절) |
| `figure.face_style(sex, name, **changes)` | 성별 얼굴 스타일 4종씩 (`FACE_STYLES`) |
| `figure.expression(face, name, amount=1.0)` | 표정 8종 (`EXPRESSIONS`)을 얼굴에 입힌다. `amount`로 세기 조절 (`references/fullbody.md` 17절) |
| `skeleton.chest.surface(x, y)`, `.back_surface(x, y)` | 돌린 몸통 앞면, 뒷면 위의 화면 좌표. 옷 무늬나 문신을 몸에 붙일 때 |
| `skeleton.chest.facing(x, y, back=False)` | 그 점이 관객을 향한 정도 (1 정면, 0 윤곽, 음수 숨음). 덧그린 표시를 옅게 할 때 |

## 8. 마감 (finish)

`from paintkit import finish`

| 함수 | 주요 인자 |
|---|---|
| `finish_anime(cv, glow=0.22, diffusion=0.10, contrast=1.05, saturation=1.06, shadows, highlights, aberration=0.8, grain_amount=0.012)` | glow: 블룸 세기. diffusion: 전체 소프트 필터 |
| `finish_illustration(cv, glow=0.24, line_soften=0.7, texture=0.035, contrast, saturation)` | texture: 종이결 세기 |
| `finish_watercolor(cv, paper, wash=0.14, edge_darkening=1.3, bleed=3.5, turbulence=0.34, granulation=0.24, wobble=2.5, line_color, line_opacity=0.7, border=0.06)` | wash: 물 탄 정도. border: 여백 비율, 0이면 여백 없음 |
| `finish_oil(cv, radii=(28,14,7,3), impasto=0.35, canvas_weave=0.025, keep_lines=1.0, ground, detail=None)` | radii: 붓 반지름 목록(큰 것부터). detail: 세밀하게 다시 칠할 영역 마스크 |

조립용 부품: `bloom`, `grade`, `vignette`, `grain`, `chromatic_aberration`, `light_wash(image, field, color, mode, opacity)`, `paper_texture`, `line_art(cv)`, `contact_sheet(images, columns)`.

- 모든 마감 함수는 `seed`를 받는다
- 유화는 1024x1280 기준 20-30초, 나머지는 10초 이내
- 유화 붓질은 형태 경계 위에서 시작하지 않고 자기 색이 속한 쪽으로 물러나 시작한다. 경계에 두 색이 섞인 회색 점선이 생기지 않는다

## 9. 두머 무드 (doomer)

`from paintkit import doomer`. 무드 프리셋. 디자인 방향과 예제는 `references/doomer.md`

| 함수 | 주요 인자 |
|---|---|
| `PALETTE` | 이름 붙은 색 표 (`night`, `concrete`, `sodium`, `snow`, `ember` 등) |
| `panel_facade(width_m, floors, wall=None, lit_ratio=0.2, balconies=0.45, glazed=0.5, entrances=0, windows=True, resolution=None)` | 패널 아파트 한 면의 Canvas. `paste()`로 붙인다 |
| `panel_block(cv, view, x0, x1, z0, z1, floors, wall=None, lit_ratio=0.2, balconies=0.45, glazed=0.5, entrances=2, antennas=2, shade=0.45, haze=None, haze_amount=0.0)` | 바닥 위 직육면체 아파트. 눈이 보는 면만 칠한다. 긴 면은 창, 짧은 면은 그늘진 막벽. `Perspective`, `Camera` 모두 가능 |
| `utility_pole(cv, base, height, color=None, arm=True)` | 전봇대. 전선을 걸 점 목록을 돌려준다 |
| `pylon(cv, base, height, color=None)` | 격자 송전탑. 팔 끝 점 목록(아래 팔부터, 왼쪽부터) |
| `wires(cv, spans, sag=0.05, width=1.2, color=None, opacity=0.9)` | `spans`: (시작점, 끝점) 목록. `sag`: 경간 길이 대비 처짐 |
| `bare_tree(cv, base, height, color=None, birch=False, spread=26.0, lean=0.0)` | 잎 없는 나무. `birch=True`면 줄기와 큰 가지가 흰 껍질 |
| `snowfall(cv, count, size=2.2, color=None, region=None, opacity=0.85)` | 눈송이. 일부는 크고 흐린 가까운 눈 |
| `smoke(cv, start, rise, drift=0.0, width=3.0, color, opacity=0.45, strands=4)` | 흔들리며 퍼지는 연기 가닥과 옅은 안개 |
| `lamp_glow(cv, point, radius, color=None, strength=0.8)` | 등의 빛 번짐과 밝은 중심 |
| `cigarette(cv, base, tip, width, lit=True)` | 필터, 종이, 불씨. 불씨 위치를 돌려준다 |
| `mouth_point(head, side=1.0)` | 입꼬리 픽셀 위치와 얼굴이 향한 화면 방향 |
| `finish(cv, glow=0.3, warmth=0.5, fade=0.35, saturation=0.68, grain_amount=0.045, vignette_strength=0.32, posterize=0.18)` | 두머 마감. `warmth`: 밝은 곳의 나트륨 주황. `fade`: 검정을 남색으로 띄우는 정도 |

- 난수를 쓰는 함수(`panel_facade`, `panel_block`, `bare_tree`, `snowfall`, `smoke`, `finish`)는 `seed`를 받는다

## 10. 폭 프로파일

`ribbon`과 `ink`의 `profile` 인자. 획의 시작(0)에서 끝(1)까지 폭의 변화.

| 이름 | 모양 | 용도 |
|---|---|---|
| `taper` | 가늘게-굵게-가늘게 | 일반 펜 선, 잎, 꽃잎 |
| `in` | 굵게 시작해 뾰족하게 끝 | 속눈썹, 풀잎, 주름 선 |
| `out` | 뾰족하게 시작해 굵게 끝 | |
| `flat` | 일정한 폭, 끝은 둥글게 닫힘 | 끈, 테, 띠. 끝이 각진 막대는 `polygon`으로 |
| `brush` | 빠르게 굵어지고 길게 빠짐 | 붓 터치 |
| `lock` | 좁은 뿌리, 넓은 몸통, 뾰족한 끝 | 늘어진 머리 가닥 |
| `clump` | 넓은 몸통이 끝에서 급히 모임 | 앞머리 덩어리 |
| `finger` | 조금씩 가늘어지다 둥글게 끝남 | 손가락, 발가락, 둥근 막대 |

숫자 목록 `[0.3, 1.0, 0.6]`이나 함수 `lambda t: ...`도 넘길 수 있다.

## 11. 설정값

`paintkit/config.py`: `SUPERSAMPLE`(가장자리 품질), `SPLINE_SAMPLES`, `RIBBON_STEP_PX`, `DEFAULT_WIDTH/HEIGHT`, `DEFAULT_SEED`.
