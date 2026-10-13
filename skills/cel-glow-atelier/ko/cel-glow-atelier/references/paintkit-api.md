# paintkit API

`scripts/paintkit`의 프리미티브 참조. 경로 B(혼합)와 경로 C(자유 장면)에서 사용.

## 목차

- 기본 개념
- core : 색, 경로, 마스크, 레이어
- light : 마스크 기반 조명
- backdrop : 배경
- finish : 후보정
- scenery : 풍경과 도시
- urban : 두머 도시 연산
- objects : 사물 (기기, 가구, 컵)
- hand와 figure : 손과 전신
- profile : 옆모습 전신
- back : 뒷모습 전신
- furniture : 인물용 가구
- duo : 투샷
- hat과 props : 모자와 담배
- features와 hairstyle : 얼굴 프리셋과 머리 질감
- scene과 Portrait : 리그 연결
- 자유 장면 레시피
- 주의 사항

## 기본 개념

- 모든 그리기는 "마스크(0-1 실수 배열) + 색" 조합
- 좌표는 픽셀, y축은 아래 방향, 색은 "#rrggbb" 문자열 또는 0-1 실수 3개
- 레이어는 뒤에서 앞 순서로 생성하고 마지막에 `canvas.flatten()`으로 합성
- 임포트 형식

```python
import sys
sys.path.insert(0, "<스킬 폴더>/scripts")
from paintkit import core as pk, light as lt, backdrop as bd, finish as fn, scene
from paintkit import scenery as sn, hand as hd, figure as fg, body as bo, objects as ob
from paintkit import profile as pf, furniture as fu, duo
```

## core : 색, 경로, 마스크, 레이어

| 함수 | 설명 |
|---|---|
| `pk.rgb(color)` | 색을 0-1 실수 RGB로 변환 |
| `pk.mix(a, b, t)` | 두 색 보간 |
| `pk.adjust(color, value, sat, hue_shift)` | 명도, 채도 배율과 색상 회전(0.01 = 3.6도) |
| `pk.spline(points, closed, n)` | 제어점을 지나는 매끈한 곡선 |
| `pk.piecewise(points, corners, closed)` | 지정한 제어점에서만 각이 지는 곡선 |
| `pk.bezier(p0, p1, p2, p3)` | 3차 베지에 |
| `pk.ellipse(cx, cy, rx, ry, rot_deg)` | 타원 폴리곤 |
| `pk.rotate(pts, deg, origin)` | 회전 |
| `pk.resample(path, n)` | 호 길이 균등 재표본화 |
| `pk.offset(path, distance)` | 경로를 법선 방향으로 평행 이동 |
| `pk.taper(n, width, head, tail, peak)` | 끝이 가늘어지는 굵기 프로파일 |
| `pk.fill_mask(shape, polys)` | 폴리곤(들)의 안티에일리어싱 마스크 |
| `pk.stroke_mask(shape, (path, widths))` | 가변 굵기 스트로크 마스크, 목록 입력 가능 |
| `pk.blur(mask, sigma)` | 가우시안 흐림 |
| `pk.shift(mask, dx, dy)` | 평행 이동 |
| `pk.linear_ramp(shape, p0, p1)` | p0에서 0, p1에서 1인 선형 경사 |
| `pk.radial_ramp(shape, center, radius, aspect)` | 중심 1, 반지름에서 0인 원형 경사 |
| `pk.smoothstep(e0, e1, x)` | 부드러운 계단 |
| `pk.noise(shape, scale, seed, octaves)` | 0-1 부드러운 노이즈 |
| `pk.save(image, path)`, `pk.load(path)` | 입출력 |

### Canvas와 Layer

```python
canvas = pk.Canvas(1200, 1500, background="#ffffff")
layer = canvas.layer("tree")                       # 맨 위에 추가
layer = canvas.layer("necklace", above="outfit")   # 지정 레이어 바로 위에 삽입
layer = canvas.layer("glow", mode="screen", opacity=0.8)
layer.paint(mask, "#ff8800", opacity=0.6)   # 색 자리에 H x W x 3 배열도 가능
layer.clip(mask)                             # 마스크 안쪽만 남김 (클리핑)
layer.erase(mask)                            # 마스크 영역 지움
image = canvas.flatten()                     # 0-1 실수 RGB
```

- 블렌드 모드 : `normal`, `multiply`, `screen`, `overlay`, `add`, `softlight`
- `pk.Frame(origin, scale, rot_deg).to(points)` : 로컬 단위 좌표를 픽셀로 변환

## light : 마스크 기반 조명

| 함수 | 설명 |
|---|---|
| `lt.light_vector(azimuth_deg, elevation_deg)` | 광원 방향 벡터. 135 = 좌상단 |
| `lt.paint_form(layer, mask, base, shadow, light, radius, threshold, softness)` | 밑색과 형태 음영을 한 번에 칠함 |
| `lt.inflate(mask, radius)` | 평면 마스크를 쿠션처럼 부풀린 높이맵 |
| `lt.normals_from_height(height)` | 높이맵에서 법선맵 |
| `lt.sphere_normals(shape, center, rx, ry)` | 타원체 법선맵 (머리, 과일 등 둥근 형태) |
| `lt.lambert(normal_map, light)` | 확산 조명값 (-1-1) |
| `lt.form_shadow(lit, threshold, softness)` | 조명값에서 그림자 마스크 |
| `lt.cast_shadow(occluder, receiver, light, distance, softness, down_bias)` | 투영 그림자 |
| `lt.occlusion(occluder, receiver, spread, strength)` | 접촉 음영 |
| `lt.rim(mask, light, width, softness)` | 광원 쪽 가장자리 띠 |
| `lt.outline_mask(mask, width, light, variation)` | 굵기가 변하는 외곽선 띠 |

- `softness` 0.02는 셀 음영, 0.15는 일러스트, 0.3은 회화
- `radius`는 형태 두께의 절반 정도가 기준

## backdrop : 배경

- `bd.gradient(layer, top, bottom, angle_deg)`
- `bd.glow(layer, center, radius, color, opacity)`
- `bd.bokeh(layer, colors, count, size, opacity, seed)`
- `bd.wash(layer, colors, scale, seed)`
- `bd.light_shafts(layer, color, count, angle_deg, width_px, opacity)`
- `bd.petals(layer, color, count, size, seed)`

## finish : 후보정

입력과 출력은 모두 0-1 실수 RGB 이미지.

| 함수 | 설명 |
|---|---|
| `fn.diffusion(img, sigma, strength)` | 확산 글로우 |
| `fn.bloom(img, threshold, sigma, strength)` | 밝은 영역 번짐 |
| `fn.grade(img, contrast, saturation, shadow_tint, highlight_tint, tint_strength)` | 색 보정 |
| `fn.vignette(img, strength, color)` | 주변부 어둡게 |
| `fn.grain(img, amount, seed)` | 필름 그레인 |
| `fn.paper(img, strength, scale, seed)` | 종이 결 |
| `fn.canvas_weave(img, strength, period)` | 캔버스 직조 무늬 |
| `fn.chromatic(img, shift)` | 가장자리 색수차 |
| `fn.painterly(img, radii, threshold, detail, seed)` | 붓 터치 재구성 |
| `fn.tilt(img, degrees)` | 더치 앵글. 중심 기준 회전(양수는 반시계 방향)과 빈 모서리를 없애는 자동 확대 |

- `fn.painterly`의 `detail`은 세밀하게 남길 영역의 마스크 (얼굴 등)
- `radii`는 큰 붓에서 작은 붓 순서로 지정

## scenery : 풍경과 도시

- 레이어 1개에 직접 그리는 빌더 모음, 위치와 크기는 캔버스 비율
- 함수 : `sn.sky`, `sn.sun`, `sn.stars`, `sn.clouds`, `sn.ridge`, `sn.ground`, `sn.grass`, `sn.flowers`, `sn.water`, `sn.tree`, `sn.pine`, `sn.tree_line`, `sn.skyline`, `sn.street`, `sn.room`
- `sn.room(layer, floor, wall, floor_color, baseboard, window, ...)` : 실내 벽, 창, 나무 바닥. 인자는 `scenery.md`의 실내 절과 동일
- 인자는 `references/scenery.md`의 표와 동일하며 `light`에 광원 벡터를 넘김
- `sn.ridge`, `sn.ground`, `sn.water`, `sn.tree`는 그린 영역의 마스크를 돌려주므로 그 위에 음영이나 요소를 추가할 수 있음
- `sn.StreetView(layer, horizon, vanish_x, eye)` : 거리의 투시 변환기
    + `project(x, y, z)` : 미터 단위 좌표(가로, 높이, 깊이)를 픽셀로 변환
    + 벤치, 입간판 같은 사물을 거리 위 정확한 위치와 크기로 추가할 때 사용
    + 차량과 행인은 `sn.street`의 `cars`, `people` 인자로 그려짐

```python
layer = canvas.layer("land")
sn.sky(layer, "#4f7fc0", "#f3d9b8", horizon=0.62)
sn.ridge(layer, base=0.60, height=0.30, color="#8f9cc4", shadow="#6a7aa8", light=LIGHT, seed=3)
lake = sn.water(layer, top=0.625)
```

## urban : 두머 도시 연산

- `from paintkit import urban as ur`. 레이어 1개에 직접 그리며 위치와 크기는 캔버스 비율 (scenery와 같은 규칙)
- 함수 : `ur.panel_blocks`, `ur.power_lines`, `ur.streetlamp`, `ur.snow`, `ur.fog`, `ur.bare_tree`
    + 인자는 `references/scenery.md`의 도시 연산 표와 동일
    + 모두 그린 영역의 마스크를 돌려줌 (`snow`는 눈송이, `panel_blocks`는 블록 전체)
- 창밖 풍경처럼 장면의 일부에만 넣을 때는 같은 크기의 캔버스를 따로 만들어 그리고 `flatten()` 결과를 유리 마스크로 칠함

```python
view = pk.Canvas(WIDTH, HEIGHT)
ur.panel_blocks(view.layer("blocks"), time="night", blocks=[{"x": [0.3, 0.8], "base": 0.95, "top": 0.2}])
ur.snow(view.layer("snow"), count=400)
canvas.layer("outside").paint(glass_mask, view.flatten())     # H x W x 3 색 필드를 마스크로 칠함
```

## objects : 사물 (기기, 가구, 컵)

- 원리 : 인공물은 상자와 원기둥의 조합이며 세부는 각 면 위에 올림
- `ob.Stage(shape, origin, scale, yaw, pitch, distance, light)` : 고정 카메라
    + 실제 치수(예 : cm)를 그대로 쓰면 화면 위치로 변환됨
    + 축 : x 오른쪽, y 위, z 관객에게서 멀어지는 방향
    + `origin`은 원점이 놓일 픽셀, `scale`은 단위당 픽셀
    + `yaw`는 카메라를 옆으로 돌린 각, `pitch`는 내려다보는 각
    + `distance` 생략 시 평행 투영(제품 그림처럼 깔끔함), 숫자를 주면 원근 투영
- 그리기 함수

| 함수 | 설명 |
|---|---|
| `ob.box(stage, layer, center, size, color, shadow, radius, edge)` | 상자. 보이는 면을 면별 명암으로 칠하고 `{면 이름: Face}` 반환 |
| `ob.cylinder(stage, layer, center, radius, height, color, shadow, top_color, taper)` | 세운 원기둥 (컵, 캔, 화분, 기둥) |
| `ob.pebble(stage, layer, center, size, color, shadow)` | 평면이 없는 낮고 둥근 물체 (마우스, 비누, 돌) |
| `ob.polygon(stage, layer, points, color, opacity, softness)` | 공간 좌표의 평면 다각형 (바닥, 벽, 종이) |
| `stage.ground_shadow(points, softness)` | 점들이 y = 0 평면에 드리우는 그림자 마스크 |
| `stage.project(points)` | 공간 좌표를 픽셀로 변환 |

- `center`는 물체 바닥면의 중심, `size`는 (가로 x, 높이 y, 깊이 z)
- `radius`는 모서리 둥글림(공간 단위)이며 가장 얇은 축에 수직인 큰 면 2개에 적용됨
- 면 이름 : `front`, `back`, `left`, `right`, `top`, `bottom`. 카메라에서 보이는 면만 반환됨
- `Face` : 면 위 좌표(u 오른쪽, v 아래, 0-1)로 세부를 배치
    + `face.rect(u0, v0, u1, v1, radius)` : 면 위 사각형의 픽셀 폴리곤
    + `face.at(uv)` : 면 좌표를 픽셀로 변환
    + `face.mask()` : 면 전체 마스크
- `ob.grid(face, area, columns, rows, gap, radius)` : 같은 크기 칸의 격자 폴리곤 목록 (키보드 자판, 창문, 앱 아이콘)
- `ob.text_lines(face, layer, area, rows, colors, seed)` : 글이나 코드처럼 읽히는 짧은 막대 줄 (화면, 문서)
- 그리는 순서 : 벽과 바닥, 그림자, 먼 물체, 가까운 물체
- 그림자는 `multiply` 레이어에 모아 그리면 물체가 바닥에 붙어 보임

```python
stage = ob.Stage(canvas.shape, origin=(760, 640), scale=7.3, yaw=22, pitch=20)   # 1 단위 = 1 cm
faces = ob.box(stage, layer, center=(0, 12, 17), size=(64, 38, 2.4), color="#22252d", radius=1.2)
layer.paint(pk.fill_mask(canvas.shape, faces["front"].rect(0.03, 0.04, 0.97, 0.96)), "#1b2233")   # 화면
ob.text_lines(faces["front"], layer, (0.08, 0.15, 0.94, 0.92), rows=17, colors=("#7fd1c7", "#f2c14e"))
```

- 전체 예시 : `assets/examples/desk_setup_example.py` (모니터, 노트북, 키보드, 마우스, 휴대전화, 머그잔, 화분, 액자)
- 한계 : 곡면이 많은 사물(자동차 외형, 의자 등받이, 유선형 기기)은 상자 조합으로 단순화됨

## hand와 figure : 손과 전신

- `hd.Hand(shape, frame, pose, mirror, view, widen, roll, pitch)` : 손 1개, `widen`은 손가락 굵기 배율 (남성 1.15)
    + `frame`은 `pk.Frame(손목 픽셀, 손 길이 픽셀, 회전)`, 회전 0은 손가락이 화면 아래를 향함
    + `pose`는 제스처 이름 또는 `hd.HandPose(curl, spread, thumb_out, thumb_curl)`
    + `roll` : 손의 긴 축 기준 회전(도, -90-90), 양수는 엄지 쪽 옆면이 관객을 향함
    + `pitch` : 손가락이 관객 쪽으로 기우는 정도(도, 0-75)
    + 손 점은 (x, y, z) 3D이며 z는 손등 쪽 두께와 손가락 굽힘 깊이. 돌린 손은 손가락을 깊이 순으로 그림
    + `hand.paint(layer, skin, shadow, line_color, light)`로 칠하고 `hand.mask`로 영역 확인
    + `hd.HIDDEN_POSES` (`pocket`, `tucked`) : 그리지 않는 손. `hand.hidden`이 참이고 마스크가 비어 있음
- `fg.Figure` : 전신 리그. 보통 spec의 `figure` 키로 사용하며 상세는 `references/figure-spec.md`
- `bo.make_pose(name, overrides)` : 포즈 객체 생성
- `bo.make_build(values)` : 체형 객체 생성
- `bo.plan_for(gender)` : 성별 체형 계획 (`BodyPlan`, 비례와 굵기 곡선 전체)
- `bo.solve_skeleton(pose, build, plan)` : 관절 좌표만 계산 (그리기 전 자세 확인용)
- `bo.POSES`, `bo.REACH` : 포즈 프리셋과 여성 손목 목표점 사전 (남성은 `plan.reach`)
- `fg.OUTFITS`, `fg.OUTFIT_ALIASES` : 전신 의상 이름과 별칭 (`bikini`는 `swimsuit`)
- `fg.OUTFIT_GENDER`, `fg.DEFAULT_OUTFIT` : 의상별 재단 성별(표에 없으면 공용)과 성별별 기본 의상
- `fg.resolve_outfit(name)` : 별칭을 풀어 의상 이름 반환, 모르는 이름은 성별로 묶은 목록과 함께 `ValueError`
- `paintkit.wardrobe` : v9 의상 7종의 정면, 옆모습, 뒷모습 형태. 새 의상은 이 모듈에 시점별 함수 3개로 추가
- `scene.make_figure(canvas, cfg, character, style, head_height_px, pelvis_px, light)` : spec의 `figure` 사전으로 정면, 옆모습, 뒷모습 리그 중 맞는 것을 생성
- `spec.with_gender_defaults(character, palette)` : 성별 기본값을 채운 (character, palette) 사전

## profile : 옆모습 전신

- `pf.SideFigure(canvas, spec, style, head_height, pelvis_px, pose, outfit, build, heels, light, facing, furniture)` : 옆모습 리그
- `pf.make_side_pose(name, overrides)` : `side_stand`, `side_walk`, `side_sit`, `side_wave`, `side_lounge`, `side_lean` 프리셋과 덮어쓰기
- `profile_head.ProfileHead(figure, frame)` : 옆얼굴 머리 (얼굴, 귀, 눈, 머리카락). 옆모습 리그와 뒷모습 돌아보기가 함께 씀
    + `profile_head.ProfileFrame(origin, scale, pitch_deg, sign)` : 옆얼굴 좌표 변환, `sign` -1은 왼쪽을 봄
    + `head.masks()`, `head.paint_face(layer, features, face, neck)`, `head.paint_hair(layer, hair)`
- 옆얼굴 좌표 : 원점은 눈높이의 머리 중심선, 얼굴은 +x. 눈 약 (0.34, 0), 코끝 약 (0.50, 0.16), 귀 약 (-0.04, 0.06)
- `figure.face_frame.to(points)` : 옆얼굴 좌표를 픽셀로 변환 (왼쪽을 볼 때는 렌더 뒤 레이어가 반전되므로 `figure.head.to` 사용)

## back : 뒷모습 전신

- `bk.BackFigure(canvas, spec, style, head_height, pelvis_px, pose, outfit, build, heels, light, look=...)` : 뒷모습 리그, `fg.Figure`를 상속하여 같은 골격을 씀
- `bk.make_back_pose(name, overrides)` : `back_stand`, `back_lookback`, `back_walk`, `back_sit` 프리셋과 덮어쓰기, (포즈, 기본 look)을 돌려줌
- `bk.LOOKS` : `away`, `left`, `right`, `left_3q`, `right_3q` (`_3q`는 정면 얼굴 리그를 35도로 돌려 씀)
- 혼합 모드에서 `figure.masks`의 `torso`는 목덜미까지 포함 (뒷머리 아래 피부)

## furniture : 인물용 가구

- `fu.paint(figure, kind, color)` : 정면 인물 뒤에 `chair`, `sofa`, `pillar`, `bed`를 그림 (보통 spec의 `figure.furniture`로 사용)
- `fu.floor_level(figure)` : 발밑 바닥의 골격 y 좌표(골반 아래 머리 단위). 다른 인물이나 사물을 같은 바닥에 세울 때 사용
- `fu.paint_side(figure, kind, color, near)` : 옆모습 가구 `stool`, `chair`, `sofa`, `pillar`. `near=False`는 인물 뒤, `near=True`는 인물 앞(소파의 가까운 팔걸이)
- `fu.back_contact(figure)` : 옆모습에서 등이 가장 뒤로 나온 지점(머리 단위), 등쿠션과 기둥 위치 기준
- `fu.paint_back_chair(figure, color, near)` : 뒤에서 본 의자. `near=False`는 앉는 면과 다리, `near=True`는 등받이
- `fu.stage_for(figure, yaw)` : 인물 발밑 바닥이 원점이고 1 단위 = 1 머리인 `objects.Stage`
    + 인물 옆에 탁자, 상자, 화분 같은 사물을 같은 축척으로 놓을 때 사용

## duo : 투샷

- 보통 spec의 최상위 `duo` 키로 사용하며 상세는 `references/figure-spec.md`의 투샷 절
- `duo.DUO_POSES` : `side_by_side`, `hold_hands`, `arm_in_arm`, `arm_around`, `face_to_face`
- `duo.stature_ratio(main_gender, partner_gender, scene.stature_units, scene.STATURE_M)` : 실제 키 비율로 계산한 상대의 머리 크기 배율
- `duo.Duo(canvas, duo_spec, main_cfg, main_character, partner_character, partner_cfg, style, light, head_px, main_pelvis, scene.make_figure, scene.stature_units, scene.STATURE_M)` : 두 인물의 배치와 접촉 계획
    + `render(shadow_main, shadow_partner)` : 두 인물을 그리고 주인공 객체를 돌려줌, 상대는 `portrait.partner`
- 혼합 모드에서 두 인물의 관절은 `portrait.joints`와 `portrait.partner.joints`, 픽셀 변환은 각자의 `at`

## hat과 props : 모자와 담배

- `paintkit.hat` : `character.hat`이 `none`이 아닐 때 리그가 머리를 그린 직후 자동 호출됨
    + 형태는 각 머리 틀(정면 `head.to`, 옆모습 `ProfileFrame.to`)의 머리 단위로 정의되어 고개 회전과 기울기를 따라감
    + 비니 위로 솟은 머리카락은 머리카락 레이어(`hair_front`, `hair_back`, `see_through`)에서 지워짐
- `paintkit.props`
    + `pr.paint_cigarette(layer, base, tip, width, line_color=None, line_opacity=0.6)` : 두 픽셀 점 사이에 필터, 종이, 재, 불씨, 불빛 번짐을 그림 (필터 쪽이 `base`)
    + `pr.smoke(layer, start, rise_px, width_px, seed=0, color, opacity=0.5, drift=0.25)` : `start`에서 `rise_px`만큼 오르는 연기. `drift`는 오르는 높이 대비 옆으로 흐르는 비율 (음수는 왼쪽)
    + 인물의 담배는 `figure.cigarette` 키로 자동 처리, 위 2개 함수는 정물이나 혼합 모드용
- 정물 예 : `assets/examples/doomer_still_life_example.py` (재떨이에 걸친 담배를 `stage.project`로 놓고 연기 2줄기)

```python
base, tip = stage.project([(4.0, 2.5, -14.0), (-2.0, 2.0, -11.6)])     # 필터, 불씨 (cm)
pr.paint_cigarette(layer, base, tip, width=0.8 * PIXELS_PER_CM, line_color="#12141a")
pr.smoke(canvas.layer("smoke"), tip, rise_px=500, width_px=3.0, color="#cdd5e0", opacity=0.6, drift=-0.12)
```

## features와 hairstyle : 얼굴 프리셋과 머리 질감

- 보통 spec의 `character` 키(`eye_shape`, `brow_shape`, `nose_shape`, `mouth_shape`, `skin_tone`, `hair_style`)로 사용
- `paintkit.features`
    + `EYE_SHAPES`, `BROW_SHAPES`, `NOSE_SHAPES`, `MOUTH_SHAPES` : 프리셋 이름과 형태 데이터 (머리 단위, 성별 공통)
    + `features.check(spec)` : 허용되지 않은 이름이면 `ValueError`
    + `features.eye_lids(shape, w, h, tilt)` : 프리셋 눈의 위아래 눈꺼풀 제어점
- `paintkit.spec.SKIN_TONES` : 피부톤 6단계의 성별별 `skin`, `skin_shadow`, `blush`, `lip`
    + `spec.skin_tone_palette(tone, gender)` : 팔레트 값 딕셔너리, `with_gender_defaults`가 성별 팔레트와 spec 팔레트 사이에 끼워 넣음
- `paintkit.hairstyle`
    + `hairstyle.paint_curls(fig, layer, mask, seed)` : 마스크 위에 C자 컬 질감 (어두운 호 + 광원 쪽 밝은 호)
    + `hairstyle.paint_undercut(fig, layer, zone, keep)` : `zone`을 짧게 친 머리색으로 칠하고 `keep`(긴 머리) 아래에 그늘을 둠
- 머리 모양 데이터는 `paintkit.anatomy.HAIR_STYLES`이며 새 키는 `ears`, `wave_freq`, `ragged`, `volume`, `curls`, `undercut`, `nape_locks`, `profile`

## scene과 Portrait : 리그 연결

```python
canvas, portrait = scene.build(spec)      # 배경과 인물을 레이어로 그림
# ... 여기에 추가 레이어를 그림 ...
image = scene.finish(canvas, portrait, spec)
pk.save(image, "out.png")
```

- 레이어 순서 (흉상) : background, hair_back, body, outfit, face, features, hair_front, see_through, rim, ambient, foreground
- `portrait.head.to(points)` : 머리 단위 좌표를 픽셀로 변환, 기울임과 회전 반영
- `portrait.head.to_rigid(points, depth)` : 얼굴 표면에서 떨어진 점(귀, 귀걸이)을 고정 깊이로 회전해 픽셀로 변환. 반측면에서 차이가 남
- `portrait.head.wide` : 14도를 넘는 회전 보정의 강도 (0-1)
- `portrait.head.turned_outline(outline, anchors)` : 얼굴 윤곽 회전. `anchors`는 `anatomy.face_anchors(spec)`이며 반측면에서 볼 곡선을 이목구비 기준으로 다시 그림
- `portrait.body.to(points)` : 몸 단위 좌표를 픽셀로 변환, 기울임 미반영
- `portrait.px(value)` : 머리 단위 길이를 픽셀로 변환
- `portrait.masks` : `face`, `body`, `cloth`, `hair_back`, `hair_cap`, `hair_bangs`, `hair_sides`, `hair_front`, `eyes`, 귀가 보이면 `ears`
- `portrait.figure_mask()` : 인물 전체 실루엣
- `scene.SHOTS` : 구도 프리셋 이름 (`full`, `thigh`, `knee`, `waist`, `bust`)
- `portrait.light` : 광원 벡터, 추가 요소 음영에 재사용

### 머리 단위 기준점

| 위치 | 좌표 (x, y) |
|---|---|
| 정수리 | (0, -0.52) |
| 눈썹 | (±0.17, -0.108) |
| 눈 중심 | (±0.172, 0) |
| 코끝 | (0, 0.183) |
| 입 | (0, 0.283) |
| 턱끝 | (0, 0.455) |
| 얼굴 반폭 (눈 높이) | 0.335 |
| 목 아래 중앙 (몸 단위) | (0, 0.78) |
| 어깨 끝 (몸 단위) | (±0.505, 0.935) |

## 자유 장면 레시피

- 요소 1개를 그리는 표준 순서
    + 제어점 4-8개로 `pk.spline` 경로 작성
    + `pk.fill_mask`로 마스크 생성
    + `lt.paint_form`으로 밑색과 형태 음영 적용
    + 필요 시 `lt.cast_shadow`, `lt.rim` 추가
    + 선이 필요한 화풍이면 `lt.outline_mask`를 어두운 색으로 칠함
- 장면 전체 순서
    + 하늘이나 벽 같은 가장 먼 면부터 레이어 생성
    + 먼 요소일수록 명도 대비와 채도를 낮춤 (대기 원근)
    + 가까운 요소일수록 진하고 선명하게
    + 모든 요소에 같은 `light` 벡터 사용
    + 마지막에 `finish` 함수 2-4개를 연결
- 자연물은 작은 덩어리 여러 개의 군집으로 작성
    + 나무 수관 : 타원 7개 안팎의 군집을 여러 개 겹침
    + 산 능선 : 난수 높이의 제어점을 스플라인으로 연결
- 반사와 수면 : `canvas.flatten()` 결과를 뒤집어 어둡게 칠하고 잔물결 스트로크 추가
- 전체 예시 : `assets/examples/landscape_example.py`, `assets/examples/still_life_example.py`, `assets/examples/desk_setup_example.py`, `assets/examples/doomer_still_life_example.py`
- 자유 장면에 spec과 같은 마감을 입히려면 `scene.finish(canvas, None, {"style": "illust", "finish": {"preset": "doomer"}, "seed": 7})`

## 주의 사항

- 폴리곤 제어점은 화면 밖으로 넉넉히 내보내 가장자리 틈을 방지
- 선 굵기와 반지름은 캔버스 크기에 비례하는 상수로 파일 상단에 정의
- 스트로크 수백 개는 `pk.stroke_mask`에 목록으로 한 번에 전달해야 빠름
- 난수는 `np.random.default_rng(seed)`로 고정하여 재현성 확보
- 요소 1-2개를 추가할 때마다 렌더하여 확인
