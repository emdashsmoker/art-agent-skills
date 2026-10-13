# API 요약

## 목차

- 좌표계
- Character 필드
- Head
- Palette와 Material
- HairStyle
- Painter
- 배경
- 렌더 진입점
- 도형 도구
- 입체 렌더러
- 3D 인물
- 3D 장면
- 야외 장면
- 색보정
- 손과 전신
- 지형과 풍경
- 도시
- 정물

## 좌표계

| 공간 | 원점 | 단위 | 용도 |
|---|---|---|---|
| 캔버스 단위 | 좌상단 | 1000 x 1333 (y는 아래로 증가) | 배경, 소품, 머리 중심 위치 |
| 머리 단위 | 두개골 중심 | 두개골 반지름 = 1 | 얼굴, 머리카락 |
| 몸 단위 | 쇄골 사이 오목한 지점 | 두개골 반지름 = 1 | 목, 어깨, 의상 |
| 눈 단위 | 눈 중심 | 눈 반폭 = 1 (x는 눈꼬리 방향) | 눈꺼풀, 홍채, 속눈썹 |

- 픽셀 크기는 `px_per_unit`이 결정
    + 미리보기 0.8(800 x 1066), 최종 1.6(1600 x 2133)
- 머리 단위의 주요 높이
    + 정수리 -1.00, 머리카락 윗선 -1.17, 눈썹 0.00 부근, 눈 0.30, 코끝 0.72, 입 0.945, 턱끝 1.20
- 몸 단위의 주요 위치
    + 어깨 끝 (1.40, 0.58), 겨드랑이 (0.99, 1.12), 원피스 목선 y 0.95-1.12

## Character 필드

| 필드 | 기본값 | 의미 |
|---|---|---|
| `palette` | `default_palette()` | 색 일체 |
| `hair` | `long_windy_hair()` | 머리 모양 데이터 |
| `head_center` | (445, 505) | 머리 중심, 캔버스 단위 |
| `head_radius` | 228 | 머리 크기, 클수록 화면을 가득 채움 |
| `roll` | 0.06 | 고개 기울임(라디안), 양수는 시계 방향 |
| `yaw` | -0.22 | 고개 돌림, 음수는 화면 왼쪽을 향함, 절대값 0.3 이내 |
| `eye_x`, `eye_y` | 0.41, 0.30 | 눈 중심 위치 |
| `eye_half_width` | 0.23 | 눈 크기, 0.20은 성숙한 인상, 0.25는 어린 인상 |
| `eye_open` | 1.0 | 눈 뜬 정도, 0.6 졸린 눈, 1.15 크게 뜬 눈 |
| `eye_slant` | 0.05 | 양수는 눈꼬리가 올라감 |
| `gaze` | (-0.06, 0.0) | 시선, 화면 기준 방향(눈 단위) |
| `smile` | 0.6 | 0 무표정, 1 뚜렷한 미소 |
| `brow_tilt` | 0.0 | 양수는 눈썹 안쪽이 올라감(순한 인상), 음수는 단호한 인상 |
| `lower_face` | 1.0 | 눈 아래 얼굴 길이 배율, 1.08-1.14는 성인 얼굴 |
| `outfit` | `Outfit.STRAP_DRESS` | `STRAP_DRESS`, `LONG_SLEEVE_TOP` |
| `neck_offset` | (0.10, 1.64) | 목 아래 기준점, 머리 단위 |
| `body_roll` | -0.04 | 어깨 기울임, 고개와 반대로 주면 자연스러움 |
| `shoulder_half_width` | 1.42 | 어깨 반폭 |

- 수정은 `dataclasses.replace(default_character(), 필드=값)`
    + 데이터클래스가 frozen이므로 직접 대입 불가

## Head

- `Head(character)`는 머리 단위의 점을 캔버스 단위로 변환
    + `flat(points)`은 기울임만 적용, 모자처럼 머리 전체에 얹는 소품에 사용
    + `on_face(points)`는 얼굴 곡면과 yaw를 적용, 안경이나 점처럼 얼굴에 붙는 소품에 사용
    + `on_skull(points)`는 두피 곡면과 yaw를 적용, 머리핀처럼 머리카락에 붙는 소품에 사용
    + `units(길이)`는 머리 단위 길이를 캔버스 단위로 변환

## Palette와 Material

- `Material(base, shadow, line, accent=None, light=None)`
    + `base` 밑색, `shadow` 그림자 색, `line` 선 색, `accent` 그라데이션 끝 색, `light` 연속 음영의 밝은 가장자리 색
- `Palette` 필드
    + 재질: `skin`, `hair`, `cloth`, `trim`(리본, 옷깃)
    + 눈: `iris_dark`(위), `iris_light`(아래), `iris_glow`(아래 반사광), `pupil`, `sclera`, `sclera_shadow`, `lash`
    + 기타: `hair_highlight`, `brow`, `lip`, `blush`
- 색은 `rgb("#RRGGBB")`로 작성, 혼합은 `mix(a, b, 비율)`

## HairStyle

| 필드 | 형식 | 의미 |
|---|---|---|
| `cap` | 닫힌 곡선의 점 목록 | 두상을 덮는 덩어리, 아랫변이 헤어라인 |
| `back_mass` | 닫힌 곡선의 점 목록 | 몸 뒤의 어두운 덩어리 |
| `back_locks` | `LockSpec` 목록 | 몸 뒤의 다발 |
| `bangs` | `LockSpec` 목록 | 이마 위 다발, 왼쪽에서 오른쪽 순 |
| `side_locks` | `LockSpec` 목록 | 어깨 앞으로 내려오는 옆머리 |
| `flyaways` | `LockSpec` 목록 | 실루엣을 깨는 가는 잔머리, 폭 0.02-0.03 |
| `highlight_radius` | 0.80 | 광택 띠의 반지름 |
| `highlight_thickness` | 0.17 | 광택 띠의 최대 반폭 |

- `LockSpec(root, tip, width, bend=0, sway=0)`는 머리 단위
    + 앞머리 끝은 눈 위에서 y 0.10 부근, 눈 사이에서 y 0.30 부근이 기본

## Painter

| 메서드 | 기능 |
|---|---|
| `part(name, mask, material, roundness=0.4, casts=(), tone=None, outline=True, volume=1.0, detail=None)` | 밑색, 음영, 선을 한 번에 그림 |
| `cast(occluder, receiver, offset_units)` | 드리운 그림자 마스크 반환 |
| `stroke(points, width, color, taper, opacity, clip)` | 굵기가 변하는 획 |
| `fill(polygon, color, opacity, clip)` | 음영 없는 평면 도형 |
| `glaze(mask, color, opacity)` | 투명한 색 덧칠(홍조, 입술) |

- `painter.canvas.mask(polygon, ...)`는 캔버스 단위 다각형을 0-1 마스크로 변환
- `painter.canvas.soft_ellipse(center, rx, ry, rotation)`은 가장자리가 흐린 타원
- `painter.canvas.part(name)`은 그려진 부품의 누적 마스크
    + 등록 이름: `hair_back`, `body`, `cloth`, `bow`, `face`, `eyes`, `mouth`, `hair_front`

## 배경

| 함수 | 내용 |
|---|---|
| `vertical_gradient(canvas, top, bottom)` | 세로 그라데이션 |
| `summer_sky(canvas, clouds, light)` | 파란 하늘과 적운, `clouds`는 `(밑변 중심, 폭, 높이, 뭉치 수)` 목록 |
| `sun_glow(canvas, center, radius)` | 빛 번짐 |
| `flat_graphic(canvas)` | 원과 잎사귀의 평면 구성 |
| `studio_backdrop(canvas)` | 어두운 바탕과 따뜻한 빛 웅덩이 |
| `bokeh_dusk(canvas)` | 저녁 그라데이션과 빛망울 |
| `gradient_stops(canvas, stops)` | 여러 색을 지나는 세로 그라데이션, `stops`는 `(높이 비율, 색)` 목록 |
| `cumulus_clouds(canvas, clouds, light, colors)` | 이미 칠한 하늘 위에 적운 추가, `colors`는 `(밝은 색, 그늘, 깊은 그늘)` |
| `stars(canvas, count, bottom_y)` | 별 |
| `beach(canvas, light, horizon_y, shore_y, clouds)` | 하늘, 바다, 파도선, 모래 |

## 렌더 진입점

- `studio.render(compose, style, output_path, px_per_unit, seed, light, units_size, finishing, review, grade)`
    + `style`은 `"anime"`, `"illust"`, `"painterly"`
    + `review=True`는 `_overview.png`와 `_face.png`를 함께 저장
    + `finishing=False`는 마감 전 상태를 저장하며 결함이 어느 단계에서 생겼는지 가릴 때 사용
- `studio.run_cli(scene_name, compose, units_size, light, description, grade)`는 `--style`, `--grade`, `--out`, `--preview`, `--seed`, `--no-review` 명령행을 제공
    + `grade`는 장면의 기본 색보정(`grade.GRADES` 이름), `--grade none`이면 끔
    + 순서는 `compose` → 화풍 마감 → `canvas.overlays`(내리는 눈 같은 덧그림) → 색보정
- `light`는 `(x, y, z)` 방향(x 오른쪽, y 아래, z 관찰자 쪽), 인물 음영, 그림자, 림라이트, 바닥 그림자, 구름 음영이 모두 따름
    + 가로 그림은 `units_size=(1333.0, 1000.0)`
- `canvas.importance`는 회화풍에서 세밀한 붓을 쓸 영역(0-1 지도), `canvas.shade_subject_as_one`은 대상 전체의 명암 그라데이션 사용 여부
- `canvas.overlays`는 화풍 마감 뒤에 실행할 `function(canvas)` 목록(붓질과 선화가 건드리지 않아야 하는 날씨)
- 회화풍 얼굴의 붓 세밀도는 얼굴 크기에 따라 자동(`finish.SMALL_FACE_UNITS`, `FACE_DETAIL`, `FACE_JOIN_UNITS`)
- 기본 광원은 `DEFAULT_LIGHT = (-0.52, -0.60, 0.61)`(좌상단 전방)
    + 광원을 바꾸면 눈 하이라이트와 머리카락 광택의 위치 상수도 함께 조정 필요

## 도형 도구

| 함수 | 기능 |
|---|---|
| `geometry.catmull_rom(points, closed)` | 모든 조절점을 지나는 매끈한 곡선 |
| `geometry.ellipse(center, rx, ry, rotation)` | 타원 다각형 |
| `geometry.lock(root, tip, width, bend, sway)` | 잎 모양 다발, `(다각형, 중심선)` 반환 |
| `geometry.ribbon(centerline, widths)` | 중심선 둘레의 띠 다각형 |
| `geometry.Frame(origin, scale, rotation).apply(points)` | 국소 좌표를 캔버스 단위로 변환 |

## 입체 렌더러

`relief.Relief(canvas)`에 부품을 뒤에서 앞으로 추가한 뒤 `render(painter)`를 1회 호출한다.

| 메서드 | 기능 |
|---|---|
| `add(name, mask, material, thickness=1.0, depth=0.0, height=None, tone=None, gloss=0.0, drape=False, bridge=0.0, edge=True)` | 부품 추가 |
| `bump(mask, thickness, fade=None)` | 가장자리가 있는 부풂(재질 유지) |
| `swell(soft_mask, height_units)` | 가장자리 없는 부풂, `canvas.soft_ellipse()`와 함께 사용 |
| `groove(mask, depth_px)` | 패임, 음수 깊이는 솟은 능선 |
| `tint(mask, color, opacity, only=None)` | 표면 색 덧칠, `only`는 받을 부품 이름 |
| `visible(*names)` | 해당 부품이 보이는 픽셀의 마스크 |
| `render(painter, cast_shadows=True, lines=True)` | 조명, 그림자, 선을 계산하여 캔버스에 합성 |

- `thickness` 1.0은 단면이 반원, 값이 작을수록 납작
- `depth`가 같으면 관절처럼 이음매 없이 합쳐지고 `depth=FRONT`는 아래에 있는 모든 형태 앞에 놓임
- `height`는 직접 만든 높이 지도(픽셀), 회전체는 `lathe_height(canvas, axis_x, top_y, bottom_y, profile(points))`
- `gloss`는 0(무광)에서 1(유리)
- `bridge`는 덧입힌 천이 덮고 지나가는 홈의 크기(캔버스 단위), `edge=False`는 밑 형태에서 자라나는 부품(어깨의 팔)의 경계선을 생략

## 3D 인물

### 좌표와 단위

| 공간 | 원점 | 단위 | 축 |
|---|---|---|---|
| 인물 공간 | 골반 | 머리 높이 = 1 | x 정면 시점의 화면 오른쪽, y 아래, z 정면 시점의 관찰자 쪽 |
| 관절 국소 공간 | 관절 | 머리 높이 | 뼈는 국소 +y 방향, `skeleton.point(관절, 국소점)`으로 인물 공간 변환 |
| 머리 국소 공간 | 머리 관절 | 머리 높이 | 얼굴 앞면이 +z, 두개골 중심 (0, -0.05, -0.03) |
| 화면 | 캔버스 단위 | `head_height` 캔버스 단위 = 머리 높이 1 | `Camera3D`가 인물 공간을 회전 후 정사영 또는 원근 투영 |

### figure3d

| 대상 | 내용 |
|---|---|
| `Figure3D(character, build, pose, hair, outfit, position, ground, head_height, yaw, pitch, head_scale, ground_shadow, props, distance)` | 3D 인물 사양, `outfit=None`은 맨몸 형태 확인용 |
| `draw_figure3d(painter, figure, relief=None)` | 그리고 `(relief, depth_image, skeleton, renderer)` 반환 |
| `figure_parts(figure)` | 카메라 없이 `FigureParts(skeleton, solids, decals, context, held)` 생성(장면 합성용) |
| `finish_figure(painter, renderer, image, figure, parts)` | 조명 뒤의 의상 선, 머리카락 가닥, 얼굴, 손에 든 물체의 화면 |
| `lowest_sole(skeleton)` | 낮은 쪽 발바닥의 인물 공간 y(앉은 자세의 바닥 높이) |
| `ground_points(parts)`, `floor_level(parts)` | 바닥에 닿는 인물 공간 점(선 자세는 발바닥, 눕기와 무릎 꿇기는 가장 낮은 부위)과 그 높이, `ground`와 장면 배치가 사용 |
| `floor_shadow(canvas, view, parts, light)` | 바닥에 닿는 부위 둘레의 바닥 그림자를 카메라 원근으로 투영(단독 인물과 장면 공용), 광원 반대쪽으로 기울고 낮은 광원에서 길어짐, 상수 `FLOOR_SHADOW*` |
| `FLOOR_SLACK` 0.06, `FLOOR_BAND` 0.12 | 발바닥보다 이만큼 낮은 부위가 있으면 그 부위가 닿음, 바닥에서 이 높이 안의 부위가 바닥에 놓인 것으로 봄 |
| `stool(skeleton, character, material=None)` | 앉은 자세용 의자, `props=(stool,)`로 전달 |

| `Figure3D` 필드 | 기본값 | 의미 |
|---|---|---|
| `character` | 필수 | 팔레트와 얼굴 설정, 얼굴 프리셋은 `adult_face()`, `male_face()` |
| `build` | `FEMALE_AVERAGE` | 체형 |
| `pose` | `STAND` | 자세 |
| `hair` | `LONG_HAIR` | 머리 모양 |
| `outfit` | None | 의상 |
| `position` | (500, 640) | 골반의 캔버스 위치 |
| `ground` | None | 바닥의 캔버스 y, 지정하면 바닥에 닿는 부위(`ground_points`)를 바닥에 맞춤 |
| `head_height` | 158 | 머리 높이 1의 캔버스 길이 |
| `yaw` | 0.0 | 0 정면, 양수는 앞면이 화면 오른쪽으로, π 뒷모습 |
| `pitch` | 0.16 | 양수는 내려다보는 시점 |
| `head_scale` | 1.0 | 1.0은 사실적 비례, 1.08-1.15는 애니메식 큰 머리 |
| `ground_shadow` | True | 발밑 그림자 |
| `props` | () | `f(skeleton, character) -> solids 또는 Prop3D` 목록, 손에 든 물체는 `props3d.held_*()` |
| `distance` | None | 원근 투영의 눈 거리(머리 높이), None은 정사영 |

### rig3d

| 대상 | 내용 |
|---|---|
| `Build(sex, shoulders, bust, waist, hips, thighs, limbs, muscle)` | 체형, 프리셋 `FEMALE_AVERAGE`, `FEMALE_FULLER`, `MALE_SLIM`, `MALE_ATHLETIC` |
| `Pose3D(rotations, hands, reach)`, `pose(hands=None, reach=None, **관절=(rx, ry, rz))` | 자세 |
| `Reach(target, pole, wrist, fingers, palm)` | 손을 `target=(관절, 국소점)`에 놓는 역운동학 지정 |
| `HandPose3D(curl, spread, thumb_out, thumb_curl)` | 손 자세, 프리셋 `RELAXED`, `OPEN`, `FIST`, `POINTING`, `HOLDING`, `PEACE`, `FLAT_HAND`, `TYPING`, `PHONE_GRIP`, `CUP_GRIP`, `PAD_GRIP`, `RUN_HAND`, `POCKET_GRIP`, `CUPPED`, `SMOKE_GRIP` |
| `POSES` | `stand`, `a_pose`, `contrapposto`, `hand_on_hip`, `arms_crossed`, `walk`, `sit`, `wave`, `point`, `think`, `hands_behind`, `cheer`, `peace`, `sit_type`, `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug`, `sit_game`, `run`, `kneel`, `kneel_sit`, `lie_back`, `lie_front`, `hands_in_pockets`, `stand_smoke`(왼손 주머니, 오른손 담배), `sit_smoke`(가슴 앞 담배) |
| `hand_frame(skeleton, side)` | 손 틀(y 손가락 방향, z 손등 바깥, x 손가락 마디를 가로지름)과 엄지 쪽 부호 |
| `pose_skeleton(Skeleton3D, joints(build), pose)` | 관절 위치와 회전 계산(순운동학 후 역운동학) |
| `mirrored(pose)` | 좌우를 맞바꾼 자세(회전, 손 자세, 손 목표점) |
| `joints(build)` | 골격, 관절 이름은 `pelvis`, `spine`, `chest`, `neck`, `head`와 좌우 `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle` |
| `body_solids(skeleton, build, skin, hands)` | 맨몸 형태 |
| `torso_solids(skeleton, build, skin)` | 팔다리를 뺀 몸통, 목, 가슴, 엉덩이, 승모근(끈과 주머니가 놓이는 표면) |
| `neck_path(skeleton, build)` | 목의 `(점, 반지름)`, 상수 `NECK_BASE`, `NECK_TOP`, `NECK_BASE_SCALE` |
| `TRUNK`, `TRUNK_LANDMARKS`, `ARM`, `LEG`, `FOOT` | 몸통 단면표와 팔다리 조절점 |
| `breast_shape`, `pec_shape`, `glute_shape`, `deltoid_shape`, `trapezius_shape` | 근육과 지방 덩어리의 중심과 반지름 |

### head3d

| 대상 | 내용 |
|---|---|
| `Hair3D(cap_center, cap_radii, bangs, bang_length, bang_width, frame_locks, sweep, spikes, lobes, back_length, back_width, tips, side_locks, ponytail, ears, scalp_drop, nape)` | 머리 모양, `tips`는 뒷머리 끝 가닥의 `(가로 위치, 길이 비율)` 목록 |
| `BACK_TIPS`, `back_sheet(skeleton, hair)`, `back_tips(skeleton, hair)` | 긴 머리 끝 가닥 기본값, 뒷머리 판과 끝 가닥의 단면 |
| `LONG_HAIR`, `BOB_HAIR`, `PONYTAIL_HAIR`, `MALE_SHORT_HAIR`, `MALE_MEDIUM_HAIR` | 제공 머리 모양 |
| `head_solids(skeleton, sex, skin, ears)`, `hair_solids(skeleton, hair, material)` | 두개골과 머리카락 형태 |
| `draw_face(painter, renderer, image, skeleton, character)` | 각도에 맞는 얼굴 표현 |
| `FRONT_LIMIT` 0.85, `PROFILE_LIMIT` 2.05 | 정면 얼굴과 옆얼굴의 경계 각도 |

### wardrobe3d

| 대상 | 내용 |
|---|---|
| `OUTFITS` | `crop_top_hot_pants`, `hoodie_jeans`, `hoodie_shorts`, `tank_top_jeans`, `sundress`, `bikini`, `t_shirt_jeans`, `shirt_trousers`, `swim_trunks`, `suit`, `winter_beanie`, `winter_headphones`, `hoodie_beanie` |
| `puffer(ctx)`, `beanie(ctx)`, `headphones(ctx)` | 패딩(층 3, 퀼팅 선 `outer_line`, 세운 깃, 지퍼), 비니(머리 국소 타원체를 챙 평면에서 자름, 접힌 단, 골 선, 슬롯 `hat`), 머리에 쓴 헤드폰(슬롯 `gear`) |
| `PUFFY`, `PUFFER_QUILT`, `PUFFER_COLLAR`, `BEANIE_CROWN`, `BEANIE_BRIM`, `BEANIE_CUFF`, `HEADPHONE_BAND`, `HEADPHONE_CUP` | 겨울 옷 치수 |
| `GARMENTS` | 옷 단품 등록부, `(ctx) -> Piece(solids, decals)` |
| `Outfit3D(garments, colors)` | 단품 이름 목록과 슬롯별 `Material` |
| `GARMENT_LAYERS`, `LAYER_GAP` | 겹쳐 입는 층 번호와 층 간격 |
| `TIGHT`, `FITTED`, `LOOSE`, `BULKY` | 피부에서 띄우는 두께 |
| `trunk`, `sleeve`, `leg`, `chest_cover`, `seat_cover`, `hip_cover` | 몸의 각 부분을 띄운 천 |
| `ring_curve`, `limb_ring`, `decal`, `chest_point` | 솔기와 단 선을 위한 곡선 |
| `flat_hem(points)` | 관의 마지막 점에서 평평하게 끝나는 단(풍선 모양 방지) |
| `over_skin(ctx, path, clearance, hug=False)` | 끈 경로를 촘촘히 나눈 뒤 몸통 표면 밖으로 밀어냄, `hug=True`는 떠 있는 점도 표면으로 당김, `ctx.skin()`은 `torso_solids` |
| `strap_over_skin(ctx, path, slot, half_width, half_thickness)` | 피부를 따라 눕는 납작한 어깨끈(탱크톱, 원피스) |
| `hem_cut(ctx, hem)` | 몸통 위치 `hem`의 단면 평면 아래를 잘라내는 판정, 하의 위 상의의 몸통과 엉덩이 덮개가 공유 |
| `hood(ctx)` | 목 뒤 말림과 등 위에 놓인 후드 층 |
| `front_seam(ctx, thickness, slot)` | 반바지류의 앞 중심 솔기 데칼(`SHORTS_LENGTH` 미만 다리 길이에 자동) |
| `pocket_sides(ctx)`, `pocket_hands(ctx, thickness, slot, sleeve_room)` | 앞주머니에 든 손의 쪽, 손을 덮는 천(엉덩이를 덮는 상의는 `POCKET_SLEEVE_ROOM`만큼 팔뚝 쪽으로 늘이고 넓힘) |
| `tuck_into_pocket(ctx, side)` | 주머니에 든 손의 긴 소매를 손목 위에서 끝내는 절단(`POCKET_TUCK`, 안쪽 벽 없음) |
| `bikini_cup`, `bikini_strings`, `side_tie`, `_cup_corner` | 삼각 컵, 홀터와 등끈과 연결끈, 골반의 매듭, 보이는 컵 모서리 |
| `_skirt_fall(ctx, hip_frame)` | 치마가 떨어지는 방향(서면 아래, 앉으면 허벅지를 따라), `SKIRT_LAP_BEND` |
| `pocket_hands(ctx, thickness, slot)` | 앞주머니에 든 손을 덮는 천(바지류가 자동 호출) |
| `fabric(밑색, 그림자, 선, 밝은색)` | 천 `Material` 생성 |

### body3d

| 대상 | 내용 |
|---|---|
| `ellipsoid(center, axes, radii, material, group, name, gloss)` | 회전한 타원체, `axes`는 열이 국소 축인 3x3 |
| `sweep(points, radii, material, group, name, caps, gloss)` | 조절점을 지나는 구 사슬(팔다리, 손가락) |
| `section_sweep(sections, material, step, overlap, group, name, gloss, cut)` | 타원 단면을 이은 형태(몸통, 머리카락 다발) |
| `solid.cut = f(인물 공간 점들) -> bool 배열` | 참인 곳의 앞면을 잘라 뒷면을 보임(재킷 앞섶, 얼굴 개구부, 비키니 트임) |
| `Camera3D(origin, scale, yaw, pitch, distance=None, shift=(0, 0, 0))` | 카메라, `distance`는 원근의 눈 거리(None은 정사영), `shift`는 장면 안 물체의 위치 |
| `DepthRenderer(canvas, camera).draw(solids)`, `.result()` | 깊이, 재질, 부품 버퍼 |
| `renderer.with_camera(camera)` | 버퍼를 공유하는 다른 물체용 렌더러(한 장면의 여러 물체가 서로 가림) |
| `renderer.project(points)` | 인물 공간 점의 화면 픽셀 위치와 깊이 |
| `RIGID_PREFIX` | `"rigid"`로 시작하는 그룹은 서로 녹아 붙지 않음(단단한 물체) |
| `to_relief(relief, image, px_per_head)` | 깊이 지도를 `Relief`로 넘겨 조명과 선을 계산 |
| `visible_runs(renderer, image, points, tolerance, material)` | 가려지지 않은 곡선 구간 |
| `SMOOTH_BLEND` 0.10, `CLOTH_BLEND` 0.06 | 같은 그룹의 형태가 녹아 붙는 폭(피부와 머리카락, 옷) |
| `SECTION_BLEND` 0.02 | 단면 형태의 이웃 타원체 사이 골을 메우는 폭 |
| `SECTION_OVERLAP` 7.0, `SECTION_END_REACH` 3.0 | 단면 타원체가 경로를 따라 뻗는 길이(간격 배수), 양 끝에서 뻗는 길이 |
| `SWEEP_BLEND` 0.02 | 구 사슬의 이웃 구 사이를 메우는 폭(셀 그림자 톱니 방지), 가는 사슬은 반지름의 25% |
| `SWEEP_SPACING` 0.22, `SWEEP_SUBPIXEL_RADIUS_PX` 1.0, `SWEEP_SUBPIXEL_SPACING` 1.0 | 구 사슬의 구 간격(반지름 비율), 화면 반지름 1픽셀 미만의 가는 사슬은 구가 맞닿는 간격으로 그려 같은 화소를 적은 구로 칠함 |
| `SURFACE_SMOOTH` 0.022 | 남은 능선을 지우는 높이 지도 흐림 폭 |
| `LINE_JUMP_SMOOTH`, `LINE_MIN_LENGTH` | 가림 선의 깊이 차를 경계를 따라 평균하는 폭, 짧은 선 조각 제거 기준 |
| `distance_to_solids(points, solids)` | 형태들의 합집합까지의 근사 부호 거리(안쪽 음수), 끈 배치와 겹침 검사가 사용 |
| `cut.lining = False` | 잘라내기 판정 함수에 붙이면 잘린 곳에 안쪽 벽을 그리지 않음(얇은 덮개의 밑단) |
| `SLIVER_AREA` 0.004 | 부드러운 형태 사이의 닫힌 틈 중 이 넓이(머리 높이 제곱) 이하를 먼 쪽 형태로 메우고 그 둘레의 선을 생략, 단단한 물체가 두른 구멍은 유지 |

### 얼굴

- `character.male_face(character)`는 성인 남성 얼굴 프리셋(가는 눈, 낮은 눈썹, 긴 하관, 어두운 홍채, 짙은 피부)
    + 남성 얼굴은 `Character`의 `lash_weight`(0.55), `lash_flicks`(False), `brow_weight`(1.65), `iris_scale`(0.88), `lip_tint`(0.30), `blush_strength`(0.35)를 바꿈, 기본값은 모두 1.0과 True
- 시선은 `replace(character, gaze=(0.0, 0.10))`처럼 지정하며 y 양수는 아래(휴대전화를 보는 눈)
- `character.adult_face(character)`는 성인 여성 얼굴 프리셋

## 3D 장면

### 좌표와 단위

| 공간 | 원점 | 단위 | 축 |
|---|---|---|---|
| 월드 | 바닥 위의 임의 점 | 머리 높이 = 1 = 23cm | x 화면 오른쪽(장면 yaw 0), y 아래(바닥 y = 0), z 카메라 쪽 |
| 물체 공간 | 물체 바닥면 중심 | 머리 높이, `props3d.cm(센티미터)`로 환산 | 정면이 +z, 위가 -y |

### scene3d

| 대상 | 내용 |
|---|---|
| `SceneCamera(target, origin, scale, yaw, pitch, distance)` | 장면 카메라, `target` 월드 점이 캔버스 `origin`에 오며 `scale`은 그 깊이의 머리 높이 1의 캔버스 길이 |
| `camera.for_object(at, yaw)` | 월드에 놓인 물체용 `Camera3D` |
| `camera.project(points)`, `camera.eye()` | 월드 점의 캔버스 위치와 깊이, 눈의 월드 위치 |
| `Placed(item, at, yaw)` | 장면 항목, `item`은 `Figure3D` 또는 `Prop3D`, 인물의 `at`은 골반 아래 바닥점(가장 낮은 부위가 이 높이에 닿음) |
| `draw_scene3d(painter, camera, items, relief=None, lighting=None)` | 하나의 깊이 버퍼로 그리고 `(relief, depth_image, renderer)` 반환, `lighting(canvas, image)`는 선과 얼굴까지 그린 뒤, 화면과 전구와 연기 전에 실행(밤 조명) |
| `anchor(placed, key)` | 놓인 물체의 기준점(`Prop3D.anchors`) 월드 위치 |
| `seated(figure, placed, key="seat", turn=0.0)` | 의자나 소파 좌석에 앉힌 인물 |
| `on_top(item, placed, offset, yaw, key="top")` | 책상, 테이블, 카운터 상판에 올린 물체, `offset`은 가구 기준 (x, 0, z) |
| `overlaps(items, tolerance)` | 사물과 가구끼리 공유하는 부피가 `tolerance`(1cm³)를 넘는 쌍, `Overlap(first, second, depth, volume)` 목록 |

### sdf3d

| 대상 | 내용 |
|---|---|
| `Box(half, radius)` | 모서리 둥근 상자 |
| `Slab(half, corner, edge)` | 평면 모서리가 둥근 판(휴대전화, 패널, 상판, 쿠션), 두께는 국소 y |
| `Cylinder(radius, half_height, edge)`, `Cone(top, bottom, half_height, edge)` | 세로 원기둥, 원뿔대 |
| `Torus(major, minor, arc)` | 국소 xz 평면의 고리, `arc`로 일부만(손잡이) |
| `Moved(shape, offset, rotation)`, `Union(*shapes)`, `Cut(keep, carve)`, `Grid(shape, spacing, counts)` | 이동, 합집합, 빼기(속이 빈 컵), 격자 반복(자판) |
| `sdf_solid(shape, center, axes, material, group, name, gloss)` | 깊이 렌더러에 넣는 형태 |
| `turn_x`, `turn_y`, `turn_z` | 회전 행렬 |
| `MAX_STEPS`, `HIT_PX`, `GRAZE_PX` | 광선 진행 횟수와 적중 판정 거리 |

### props3d

| 대상 | 내용 |
|---|---|
| `Prop3D(name, solids, screens, decals, glows, footprint, rests_on, detail, anchors, glass, wisps)` | 물체, `rests_on`은 접촉 그림자를 받을 가구 이름, `detail`은 회화풍 붓 세밀도, `glass`는 투명 부품, `wisps`는 연기와 김 |
| `Wisp(points, width, color, opacity)`, `smoke_path(source, rise, seed, sway)`, `smoke_wisps(source, seed)`, `draw_wisp` | 위로 갈수록 넓어지고 옅어지는 연기 줄기 |
| `Screen(corners, content, material, brightness)`, `Glow(point, radius, color, strength)` | 발광 화면과 전구 |
| `laptop(lid_angle, screen)`, `monitor(screen, tilt)`, `keyboard()`, `mouse()`, `phone(screen)`, `tablet(screen)` | 기기 |
| `headphones()`, `game_controller()`, `television(screen)` | 기기 |
| `mug(body, drink)`, `paper_cup()`, `book()`, `book_stack(count, seed)`, `desk_lamp(lit)`, `potted_plant(height, seed)` | 생활 소품 |
| `drinking_glass(fill, drink, glass)` | 투명한 유리컵과 음료 |
| `cigarette(lit, smoke, seed)`, `ashtray(butts, lit, seed)`, `tea_glass(fill, drink, holder, steam, seed)` | 담배(불씨 `Glow`, 연기), 재떨이(꽁초, 테두리에 걸친 담배), 금속 받침의 차 유리잔(김) |
| `cassette()`, `cassette_player()` | 카세트테이프, 스피커 2개와 데크와 안테나가 있는 휴대용 카세트 플레이어 |
| `cable(points, sag, radius, material)` | 점을 지나는 케이블(점은 닿는 곳, 축은 반지름만큼 위), `Placed(cable)`로 월드 좌표 그대로 놓음 |
| `finish_glass(painter, view, image, solids)` | 투명 부품의 2차 합성(비침, 윤곽 쪽 색, 반사광, 윤곽선), `finish_prop`이 자동 호출 |
| `GLASS_BODY`, `GLASS_EDGE`, `GLASS_RIM`, `GLASS_SHINE`, `GLASS_HIGHLIGHT`, `GLASS_LINE` | 유리 표현 상수 |
| `held_phone(side, screen)`, `held_mug(side)`, `held_controller()`, `held_cigarette(side, lit, seed)` | 손 틀에 붙는 물체, `Figure3D.props`에 전달, 담배는 검지와 중지 사이에서 손등 쪽으로(`CIGARETTE_IN_FINGERS`) |
| `transformed(prop, origin, rotation)`, `frame(x_axis, y_axis)` | 물체 이동, 직교 틀 |
| `cm(value)`, `surface(밑색, 그림자, 선, 밝은색)`, `own_material(material)` | 단위 환산, 재질 생성, 물체 전용 재질 복사 |
| `contact_shadow`, `finish_prop(..., lights=True)`, `light_prop` | 접촉 그림자, 조명 뒤의 선과 유리, 화면과 빛과 연기(`lights=False`면 `light_prop`이 따로 그림) |

### furniture3d

| 대상 | 내용 |
|---|---|
| `desk`, `office_chair`, `sofa(seats)`, `low_cabinet`, `coffee_table`, `cafe_table`, `cafe_chair`, `counter`, `bookshelf`, `pendant_lamp(ceiling)`, `floor_lamp`, `rug` | 가구, 기준점 `seat`, `seat_0..`, `top` |
| `bed(width, length, frame_material, sheet, duvet, pillows)` | 침대, 기준점 `top`(매트리스), `duvet`(이불 위), `lie_back_0..`(베개별 눕기), `lie_back`, `lie_front` |
| `BED_TOP`, `LIE_HEAD`, `DUVET_SHARE`, `DUVET_LIFT` | 매트리스 높이, 누운 자세의 골반에서 머리까지 z, 이불이 덮는 길이 비율, 이불 높이 |
| `SEAT_TOP`, `SEAT_DROP` | 앉은 자세에 맞는 좌석 높이, 골반에서 좌석까지 |
| `DESK_HEIGHT`, `TABLE_HEIGHT`, `COUNTER_HEIGHT` | 상판 높이 |
| `radiator(sections, height_above_floor)`, `windowsill(width, depth, height)` | 주철 라디에이터(뒤가 -z), 벽에서 나온 창턱(기준점 `top`, 이름 `sill`) |

### interior

| 대상 | 내용 |
|---|---|
| `living_room()`, `office()`, `cafe()`, `bedroom()` | `Room(surfaces, items, places, size)`, `places`는 가구 이름별 `Placed` |
| `draw_room(painter, camera, room, items)` | 벽면을 칠한 뒤 가구와 인물을 한 깊이 버퍼로 그림 |
| `Shell(x0, x1, z0, z1, height)`, `shell_surfaces(...)`, `trims(...)` | 맞춤 방의 바닥, 천장, 벽 3면, 걸레받이와 구석 그림자 |
| `on_back_wall`, `on_left_wall`, `on_right_wall`, `sunlight` | 벽 장식과 창문 햇빛 자국 |
| `paint`, `planks`, `carpet_tiles`, `bricks`, `window`, `curtain`, `artwork`, `menu_board`, `outdoor_view`, `wallpaper(width, height, rng, ground, motif, stripe)` | 벽면 텍스처, 창밖 종류 `sky`, `city`, `street`, `panel_night`(밤의 맞은편 패널 아파트), `city_night`(달 아래 불 켜진 빌딩), `golden`(낮은 해와 금빛 하늘) |
| `SkyView(stops, skyline, lit_share, disc_color, disc_at, disc_size, stars)`, `SKY_VIEWS`, `sky_view(width, height, rng, view)` | 하늘 단계, 해나 달, 빌딩 실루엣으로 된 창밖, `SKY_VIEWS`에 이름을 등록하면 `window(..., 이름)`으로 사용 |
| `Surface(corners, texture, facing)`, `draw_surface(canvas, camera, surface)` | 투영되는 평면, 눈이 뒤에 있으면 생략, 칠한 영역의 마스크 반환 |
| `keep_detail(canvas, mask, detail)` | 회화풍에서 마스크 영역에 세밀한 붓 요청(창이 줄지은 벽, 창밖 풍경) |

### screens

- `render(content, width, height, rng)`, 프리셋 `desktop`, `code`, `video`, `chat`, `home`, `game`
- 새 화면은 `function(width, height, rng) -> RGB 이미지`를 `Screen.content`에 전달

## 야외 장면

### outdoor

| 대상 | 내용 |
|---|---|
| `metres(value)` | 미터를 머리 높이로(1m = 4.35) |
| `Light(wall, seam, glass, lit, lit_share, balcony, snow, snow_shade, ambient)`, `NIGHT`, `DUSK`, `OVERCAST`, `replace_light(light, **바꿀_필드)` | 야외 빛, 건물 벽과 창, 눈 색, 인물과 사물의 환경광 |
| `Fog(color, distance, horizon_band, horizon_strength)`, `FOG_NIGHT`, `FOG_DUSK`, `FOG_OVERCAST` | 거리 안개와 지평선 연무 |
| `NIGHT_SKY`, `DUSK_SKY`, `OVERCAST_SKY`, `sky(canvas, stops, clouds, horizon)` | 하늘 색 단계(1.0이 지평선), 구름층 |
| `Snow(count, size, opacity, streak)`, `SNOW_LIGHT`, `SNOW_HEAVY`, `snowfall(canvas, rng, snow)` | 내리는 눈 |
| `facade(length_m, floors, rng, light, entrances, balconies)`, `panel_block(at, length, floors, rng, light, depth, yaw, entrances)`, `Block(surfaces, center)` | 패널 아파트 입면 텍스처와 상자, `yaw`는 긴 면을 +z에서 돌림(π/2이면 +x를 봄) |
| `draw_blocks(canvas, camera, blocks, fog)` | 먼 것부터, 거리만큼 안개를 섞어 칠함 |
| `ground_plane(texture, extent, center)`, `snow_texture(rng, light, extent, paths)`, `road_texture(rng, light, extent, road_width, ..., along)`, `asphalt_texture` | y = 0 땅 평면, 눈밭(밟힌 길 `paths`는 평면 좌표 0..extent), 가운데 도로(`along="x"`면 x 방향) |
| `Lamp(at, color, reach, strength, cone)`, `SODIUM` | 광원, `reach`에서 절반으로 감쇠, `cone`은 아래로 비추는 반각(라디안) |
| `light_ground(canvas, camera, lamps)`, `light_plane(canvas, camera, lamps, point, normal, ambient, mask)` | 땅의 빛 웅덩이, 임의 평면(방의 벽)의 조명, `ambient`가 있으면 곱하기 조명 |
| `night_lighting(camera, ambient, lamps)` | `draw_scene3d(lighting=...)`용 조명, 인물과 사물에 환경광과 등빛 |
| `draw_lit_room(painter, camera, surfaces, views, items, lamps, ambient, view_detail)` | 자체 등으로 밝히는 방, 면마다 칠한 뒤 조명, 창밖과 해 조각(`views`)은 조명 뒤에, 사물과 인물은 같은 등 아래 |
| `wet_reflections(canvas, camera, lamps, width, strength)` | 젖은 도로에 비친 등빛 줄기 |
| `catenary(a, b, sag)`, `draw_wires(canvas, camera, image, wires, width, color, tolerance)` | 늘어진 전선 점, 깊이 비교로 가려지는 전선 그리기 |
| `atmosphere(canvas, camera, image, fog)`, `horizon_y(camera)` | 연무, 지평선의 캔버스 y |
| `world_points(canvas, camera, depth, where)`, `plane_points(canvas, camera, point, normal)`, `ground_points(canvas, camera)` | 화소에서 월드 좌표로 되돌리기 |
| `World(light, sky, fog, ground, blocks, lamps, items, wires, snow, clouds, wet)`, `draw_world(painter, camera, world, rng)` | 야외 그림 한 장의 구성과 정해진 순서의 그리기 |
| `FACADE_DETAIL`, `GROUND_DETAIL`, `WIRE_DETAIL` | 회화풍 붓 세밀도(입면, 땅, 전선) |

### street3d

| 대상 | 내용 |
|---|---|
| `street_lamp(height, arm, pole, housing, lit)`, `lamp_light(placed, color, reach, strength, cone)` | 콘크리트 기둥과 +x로 뻗은 팔의 가로등(기준점 `bulb`), 그 등의 `Lamp` |
| `power_pole(height, crossarm, wood, insulators, lean)`, `wires_between(poles, sag)` | 나무 전봇대(기준점 `wire_0..`), 이웃 전봇대의 같은 애자끼리 잇는 전선 |
| `bench(seats, slats, legs)` | 마당 벤치(+z를 봄, 기준점 `seat_0..`) |
| `bus_stop(width, depth, height, frame_material, seats, lit)`, `shelter_light(placed, reach, strength)` | 유리 벽 버스 정류장(기준점 `seat_0..`, `light`), 형광등의 `Lamp` |
| `birch(height, seed)` | 겨울 자작나무(흰 줄기, 검은 껍질 무늬, 가는 가지) |
| `LAMP_HEIGHT`, `LAMP_ARM`, `LAMP_REACH`, `LAMP_CONE`, `POLE_HEIGHT`, `CROSSARM`, `WIRE_SAG`, `STREET_DETAIL` | 치수와 빛 상수 |

## 색보정

| 대상 | 내용 |
|---|---|
| `grade.Grade(saturation, shadow_tint, highlight_tint, split_strength, fade, contrast, halation_threshold, halation_radius, halation_color, halation_strength, grain, grain_size, vignette)` | 마감된 그림 위의 색보정 |
| `grade.DOOMER`, `grade.DOOMER_DAY`, `grade.GRADES` | 밤(청록 그늘, 나트륨 주황 번짐, 바랜 검정, 입자), 흐린 낮 |
| `grade.COZY_NIGHT`, `grade.LATE_SUN`, `grade.GOLDEN_HOUR` | 따뜻한 일상 색보정(방 안의 밤, 늦은 오후, 야외 노을), 채도 유지와 약한 입자 |
| `grade.apply(canvas, grade)` | 번짐 → 채도 → 분할 톤 → 바램과 대비 → 비네팅 → 입자 |

## 손과 전신

| 대상 | 내용 |
|---|---|
| `rig_hand.draw_hand(relief, painter, frame, material, pose, view, mirror, name, depth, turn)` | 손 추가, 손톱과 손금을 그리는 함수를 반환 |
| `rig_hand.HandPose(spread, curl, bend, thumb_angle, thumb_curl)` | 손 자세 |
| `rig_hand.OPEN_HAND`, `RELAXED_HAND`, `VICTORY_HAND` | 제공 자세 |
| `rig_figure.Figure(character, pose, pelvis, head_height, outfit, body, outfit_material, head_scale, ground_y)` | 전신 인물 사양 |
| `rig_figure.Pose(...)` | 관절 각도와 손목 각도, 필드는 `references/subjects.md` |
| `rig_figure.BodyShape(bust, waist, hips, thighs)` | 체형 폭 배율, 프리셋 `AVERAGE`, `SLENDER`, `HOURGLASS` |
| `rig_figure.FigureOutfit`, `rig_figure.OUTFITS` | 의상 이름과 의상 레이어 함수 등록부 |
| `rig_figure.STANDING`, `CONTRAPPOSTO`, `HAND_ON_HIP`, `ARM_RAISED`, `A_POSE` | 제공 자세 |
| `character.adult_face(character)` | 성인 얼굴 프리셋(하관 1.12배, 작은 눈) |
| `rig_figure.draw_figure(painter, figure)` | 전신을 그리고 `(relief, skeleton)` 반환 |
| `rig_figure.Skeleton(figure).joints` | `left`와 `right`의 `shoulder`, `elbow`, `wrist`, `hip`, `knee`, `ankle` 좌표 |
| `character.long_straight_hair()`, `character.figure_palette()` | 전신용 긴 생머리, 깊은 피부색 팔레트 |

## 지형과 풍경

| 함수 | 기능 |
|---|---|
| `terrain.alpine_lake_heightmap(rng, peak_height, sea_level)` | `(높이 지도, 수면 높이)` 반환 |
| `terrain.colorize(heightmap, sea_level, rng, light, palette)` | `(색 지도, 지면 높이, 물 마스크)` 반환 |
| `terrain.render(canvas, ground, color, water, camera, haze, haze_distance)` | 투영, `(지형 마스크, 물 마스크, 깊이)` 반환 |
| `terrain.Camera(position, eye_height, horizon, focal, far)` | 카메라 |
| `scenery.reflect_water(canvas, water_mask)` | 물 반사와 잔물결 |
| `scenery.pine(painter, base, height, width)` | 침엽수 |
| `scenery.grass(canvas, top_y, blade_count, blade_height, flowers)` | 전경 풀밭 |

- 지형의 광원은 지도 공간 벡터 `(x, y, z)`, y는 카메라에서 멀어지는 방향

## 도시

| 함수 | 기능 |
|---|---|
| `city.StreetCamera(vanishing_point, focal, eye_height).project(points_xyz)` | 미터 좌표를 캔버스 단위로 투영 |
| `city.Building(side, near, depth, height, wall, lit_share, shop)` | 건물 사양 |
| `city.draw_buildings(canvas, camera, buildings, street_half_width, haze, layer, mirrored)` | 입면 그리기, 발광 마스크 반환 |
| `city.draw_road(canvas, camera, street_half_width, sidewalk)` | 도로, 보도, 차선, 횡단보도 |
| `city.draw_signs(canvas, camera, signs, layer, mirrored)` | 돌출 간판 |
| `city.draw_lamps(canvas, camera, positions)` | 가로등 |
| `city.wet_reflection(canvas, mirror_layer, road_mask)` | 젖은 노면 반사 |
| `city.bloom(canvas, glow, color)` | 빛 번짐 |
| `city.skyline(canvas, camera, rng, depth, count, haze)` | 먼 고층 건물 |

## 정물

| 함수 | 기능 |
|---|---|
| `stilllife.room(canvas, table_back_y, table_front_y)` | 벽과 탁자 |
| `stilllife.lathe_object(relief, name, axis_x, top_y, bottom_y, radius_points, material, gloss, ...)` | 병, 주전자, 배 |
| `stilllife.round_fruit(relief, name, center, radius, material, ...)` | 사과, 오렌지 |
| `stilllife.tilted_ellipse_fruit(relief, name, center, rx, ry, rotation, material)` | 레몬 |
| `stilllife.grapes(relief, name, top_center, count, grape_radius)` | 포도송이 |
| `stilllife.cloth(relief, name, outline)` | 주름진 천 |
| `stilllife.mouth()`, `band()`, `label()` | 주둥이, 띠무늬, 라벨 |
| `stilllife.table_shadow(relief, base, half_width, away)` | 탁자 위 그림자 |
| `stilllife.stem(painter, top_center, length, lean, leaf)` | 꼭지와 잎 |

- 재질 상수는 `RED_APPLE`, `GREEN_APPLE`, `ORANGE`, `LEMON`, `PEAR`, `GRAPE`, `GLASS`, `CERAMIC`, `PAPER`, `CLOTH`
