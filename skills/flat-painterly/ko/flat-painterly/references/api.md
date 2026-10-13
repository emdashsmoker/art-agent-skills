# codepaint API

엔진의 공개 함수 전체. 모든 길이 인자는 논리 단위이며 scale과 무관하게 같은 결과를 냄.

## 목차

- 기본 개념
- Canvas
- 물감(Linear, Radial)과 합성(Blend)
- geometry: 경로
- color: 색
- motifs: 절차적 소재
- figure: 인체 리그와 손
- figure3d: 몸을 돌리는 3차원 리그
- head3d: 각도별 머리, 얼굴, 머리카락
- faces: 얼굴 템플릿
- hairstyles: 머리 모양 템플릿과 긴 머리 드레이프
- character: 3차원 인물 그리기
- garment: 옷
- stage: 투샷 무대
- Perspective: 1점 투시
- solids: 3차원 입체와 카메라
- props: 현대 사물 부품
- styles: 화풍 도구
- post: 후보정
- io: 저장과 검수
- noise: 노이즈와 바탕 재질

## 기본 개념

- 경로(path)는 논리 좌표의 (N, 2) 배열
    + `geometry` 함수로 만들고 변형
- 형태(Shape)는 경로를 캔버스에 올려 만든 마스크 조각
    + `canvas.shape(path)`로 생성
    + `a & b` 교집합, `a - b` 차집합, `a | b` 합집합, `a * 0.5` 농도 조절
- 색은 `"#rrggbb"`, `"#rgb"`, 0-1 튜플, 0-255 튜플 모두 허용
- 이미지는 0-1 float RGB 배열 (높이, 폭, 3)
- 빛 방향 `light`는 빛이 있는 쪽을 가리키는 (x, y)
    + 왼쪽 위 광원은 `(-0.6, -0.8)`, 오른쪽 위 광원은 `(0.6, -0.8)`
- 각도는 도 단위이며 화면에서 시계 방향이 양수

## Canvas

```python
Canvas(width, height, scale=1.0, background="#ffffff", seed=7)
Canvas.from_image(image, width, height, seed=7)   # 패스 결과 위에 이어 그릴 때
```

- `background=None`이면 투명 캔버스
    + 인물처럼 따로 그려 배경에 얹을 층에 사용
- 속성: `width`, `height`, `scale`, `px_w`, `px_h`, `rgb`, `alpha`, `rng`, `flow`

### 형태 만들기

| 호출 | 역할 |
|---|---|
| `shape(*paths, soft=0.0)` | 경로를 형태로 변환. 경로 여러 개가 겹치면 짝홀 규칙으로 구멍 생성. soft는 가장자리 흐림 폭 |
| `full()` | 캔버스 전체 형태 |
| `soften(shape, amount)` | 가장자리 흐림 |
| `roughen(shape, amount=3.0, grain=12.0)` | 가장자리를 불규칙하게 흔듦. amount는 흔들림 폭, grain은 무늬 크기 |
| `mottle(shape, grain=60.0, coverage=0.5, soft=0.15, octaves=4)` | 형태 안을 얼룩 무늬로 남김. coverage는 남는 면적 비율 |
| `form_shadow(shape, light, amount=0.4, soft=0.0, roundness=1.0)` | 형태를 부풀린 입체로 보고 빛을 등진 쪽 amount 비율을 잘라낸 형태 |
| `contour(shape, width)` | 형태의 바깥 윤곽을 따라 안쪽으로 width 두께의 띠. 실루엣 전체에 선을 두를 때. 화면 밖으로 잘린 빈 형태는 그대로 돌려줌 |
| `form_light(shape, light, amount=0.15, soft=0.0, roundness=1.0)` | 면 안쪽에 맺히는 하이라이트. 빛을 가장 많이 받는 amount 비율 |
| `edge_light(shape, light, width=6.0, soft=0.0)` | 빛을 향한 윤곽을 따라가는 띠. 역광 테두리와 모서리 하이라이트 |

- `form_shadow`의 soft 0은 셀 채색의 또렷한 경계, 0.2-0.5는 회화의 부드러운 경계
- roundness를 1보다 줄이면 가장자리만 둥글고 가운데는 평평한 입체로 계산

### 칠하기

```python
fill(shape, paint, opacity=1.0, blend=Blend.NORMAL, clip=None, grain=0.0)
stroke(path, color, width=2.0, taper=1.0, closed=False, opacity=1.0,
       blend=Blend.NORMAL, clip=None, light=None, contrast=0.6, jitter=0.0, soft=0.0)
paste(other_canvas, opacity=1.0)
direct(shape, angle=None, around=None)
```

- `fill`의 paint는 색 또는 `Linear`, `Radial`
    + clip을 주면 그 형태 안쪽에만 칠함
    + grain 1.0이면 반투명 영역이 점묘 입자로 바뀜. soft를 준 형태와 함께 써서 점묘 그라데이션 생성
- `stroke`의 taper는 길이 방향 폭 배율 목록
    + `(0, 1, 0)`은 양 끝이 뾰족한 선, `(1, 0.3)`은 끝으로 갈수록 가는 선
    + closed=True와 light를 함께 주면 빛을 등진 쪽 윤곽이 굵어짐
    + jitter는 손 떨림 같은 폭 변화 0-1
- `paste`는 같은 픽셀 크기의 캔버스를 위에 합성
- `direct`는 유화 붓질 방향 지정
    + angle은 방향(0 가로, 90 세로), around는 그 점을 중심으로 도는 방향

### 출력

| 호출 | 역할 |
|---|---|
| `image(background="#ffffff")` | 0-1 RGB 이미지. 투명한 곳은 background로 채움 |
| `guide_image(step=100)` | 논리 좌표 격자를 덧그린 이미지. 위치 확인용 |
| `next_seed()` | 실행 간에 동일하게 재현되는 새 시드 |

## 물감과 합성

```python
Linear(stops, start, end)      # start에서 end로 변하는 선형 그라데이션
Radial(stops, center, radius)  # center에서 radius 거리까지 변하는 원형 그라데이션
```

- stops는 색 목록 `["#112", "#eef"]` 또는 (위치, 색) 목록 `[(0.0, "#112"), (0.7, "#88a"), (1.0, "#eef")]`
- `Blend.NORMAL` 덮어 칠하기, `Blend.MULTIPLY` 그림자와 수채 겹칠, `Blend.SCREEN` 빛과 안개, `Blend.ADD` 강한 발광

## geometry

| 호출 | 역할 |
|---|---|
| `spline(points, closed=True, corners=())` | 모든 제어점을 지나는 곡선. corners 인덱스에서 꺾임 |
| `polygon(points)` | 직선 다각형 |
| `ellipse(cx, cy, rx, ry=None, angle=0.0)` | 타원. ry 생략 시 원 |
| `rect(x, y, width, height, radius=0.0)` | 사각형. radius로 모서리 둥글림 |
| `blob(cx, cy, radius, wobble=0.25, lobes=7, rng=None, stretch=(1, 1))` | 불규칙한 유기적 형태. 구름, 번짐, 잎 덩어리 |
| `transform(path, translate=(0, 0), rotate=0.0, scale=1.0, about=(0, 0))` | about 기준 확대와 회전 후 이동 |
| `ribbon(centerline, widths, closed=False)` | 중심선에 폭을 입힌 윤곽 목록. `canvas.shape(*ribbon(...))`로 사용 |
| `densify(path, minimum_points)` | 점 수가 적은 경로를 촘촘히 재분할 |

- `ribbon`의 widths는 값 몇 개만 주면 길이 방향으로 보간
    + 나뭇가지, 머리카락 가닥, 팔다리처럼 굵기가 변하는 긴 형태에 사용

### Frame

부분 좌표계. 비례가 중요한 대상을 단위 좌표로 설계한 뒤 화면에 배치.

```python
head = g.Frame(origin=(1085, 372), unit=160, rotate=-5)   # 머리 반지름을 1로 둠
face = cv.shape(g.spline(head([(0, -1), (0.97, -0.3), (0.64, 1.0), (0, 1.37), ...])))
eye = head.child(0.49, 0.36, unit=0.31)     # 얼굴 안의 눈 좌표계
other_eye = head.mirrored().child(0.49, 0.36, unit=0.31)
```

| 호출 | 역할 |
|---|---|
| `frame(points)` | 단위 좌표 점열을 화면 좌표로 변환 |
| `frame.point(x, y)` | 점 1개 변환. `g.ellipse(*frame.point(x, y), ...)` 형태로 사용 |
| `frame.length(value)` | 단위 길이를 화면 길이로 변환 |
| `frame.mirrored()` | 좌우가 뒤집힌 좌표계. 좌우 대칭 부품에 사용 |
| `frame.child(x, y, unit=1.0, rotate=0.0)` | 이 좌표계 안의 한 점을 원점으로 하는 하위 좌표계 |

- 크기, 위치, 기울기를 바꿀 때 Frame 인자만 고치면 부품 좌표는 그대로 유지

## color

| 호출 | 역할 |
|---|---|
| `rgb(value)` | 색 표기를 0-1 배열로 변환 |
| `mix(a, b, amount)` | 두 색의 혼합 |
| `shift(color, hue=0.0, saturation=1.0, value=1.0)` | HSV 색상 이동, 채도 배율, 명도 배율 |
| `shade(color, depth=1.0)` | 그림자색. 색상을 한색으로 당기고 채도를 올리며 명도를 낮춤 |
| `tint(color, amount=0.5)` | 하이라이트색. 난색 흰색 쪽으로 혼합 |
| `luminance(image)` | 휘도 |

## motifs

| 호출 | 역할 |
|---|---|
| `cumulus(canvas, center_x, base_y, width, height, light, palette, puffs=70, rng=None)` | 적운. palette는 (빛, 중간, 그늘) |
| `ridge(x_start, x_end, base_y, peak_height, roughness=0.5, points=48, rng=None)` | 산 능선 윗변 점열. 아래쪽 두 점을 이어 닫아서 사용 |
| `splatter(canvas, center, spread, count, palette, size_range, opacity, rng=None)` | 물감 방울 |
| `canopy(canvas, center_x, center_y, width, height, light, palette, puffs=40, puff_size=(0.14, 0.26), rng=None)` | 나무의 잎 덩어리. 칠한 형태 반환 |
| `grass(canvas, x_range, y_range, count, palette, blade=(14, 34), lean=0.35, rng=None)` | 풀잎. y가 큰 쪽이 가까운 풀 |

## figure

사용법과 자세 값은 `references/figure.md`.

```python
figure.Figure(frame, build=figure.FEMALE, hip_tilt=0, chest_tilt=0, spine=0, neck=None, head=None,
              arm_l=(8, 4), arm_r=(8, 4), leg_l=(3, 1), leg_r=(3, 1), stretch=None, shoulder_drop=0.0)
figure.Build(shoulder, ribcage, waist, hip, arm, leg, neck)   # 기본 제공: figure.FEMALE, figure.MALE
```

| 호출 | 역할 |
|---|---|
| `fig.joint(name)` | 관절의 화면 좌표. pelvis, shoulder_mid, neck_top, head, shoulder_l, elbow_l, wrist_l, hip_l, knee_l, ankle_l과 `_r` |
| `fig.torso()`, `fig.neck()`, `fig.head()` | 부위 윤곽(경로 목록) |
| `fig.limb(bone, side, scale=1.0)` | 팔다리 윤곽. bone은 upper_arm, forearm, thigh, shin. scale은 굵기 배율(옷) |
| `fig.foot(side, view="front", turn=12.0)` | 발 윤곽. view는 front, side, bare_front(발가락 포함), bare_back(뒤꿈치) |
| `fig.toes(side, view="bare_front", turn=12.0)` | 맨발 앞면의 발가락 5개 [(발가락 윤곽, 발톱 윤곽), ...]. 엄지부터 새끼발가락 순서 |
| `fig.parts()` | 모든 부위 윤곽의 사전 |
| `fig.on_thorax(x, y)`, `fig.on_pelvis(x, y)` | 흉곽 좌표와 골반 좌표의 점을 화면 좌표로 |
| `fig.head_frame()` | 머리 좌표계(원점 머리 중심, 단위 머리 높이) |
| `fig.hand_frame(side, turn=0.0, flip=False)` | 손 좌표계(원점 손목, 단위 손 길이) |
| `fig.limb_frame(start, end)` | 두 관절을 잇는 좌표계. 소매 끝, 장신구 배치용 |
| `figure.shape_of(canvas, paths)` | 겹치는 윤곽들을 구멍 없이 한 형태로 합침 |
| `figure.hand_open(frame, spread=1.0, curl=0.0, thumb=1.0, view="back")` | 손등 또는 손바닥에서 본 손 |
| `figure.hand_side(frame, curl=0.25)` | 엄지 쪽 옆에서 본 손 |

- 손 함수는 `Hand`를 반환
    + `hand.parts[이름]`은 부위 윤곽 목록, `hand.joints[이름]`은 마디 좌표, `hand.paths()`는 전체 윤곽 목록

## figure3d

3/4 측면, 옆모습, 뒷모습과 앞뒤로 흔든 팔다리를 그리는 리그. 사용법과 검증된 자세는 `references/figure.md`의 3차원 리그.

```python
from codepaint.figure3d import Figure3D, Depth, FEMALE_DEPTH, MALE_DEPTH
Figure3D(frame, build=figure.FEMALE, depth=FEMALE_DEPTH, turn=0.0, elevation=0.0, hip_tilt=0.0, chest_tilt=0.0,
         spine=0.0, neck=None, head=None, lean=0.0, arm_l=(8, 4), arm_r=(8, 4), leg_l=(3, 1), leg_r=(3, 1),
         swing=None, stretch=None, shoulder_drop=0.0, head_turn=0.0, foot_pitch=None)
Depth(chest, waist, hip, bust, glute)   # 몸통 앞뒤 반두께(머리 높이)
```

- turn 0이면 관절과 몸통 윤곽이 `figure.Figure`와 같음
- 몸 좌표는 x가 정면에서 본 화면 오른쪽, y가 아래, z가 몸 뒤쪽. 몸의 정면은 -z

| 호출 | 역할 |
|---|---|
| `body.groups()` | 칠할 덩어리 [(이름, 윤곽 목록), ...]를 먼 것부터. 이름은 body, arm_l, arm_r, leg_l, leg_r |
| `body.joint(name)`, `body.joints3[name]` | 관절의 화면 좌표와 몸 좌표 |
| `body.torso()`, `body.neck()`, `body.limb(bone, side, scale=1.0)` | 부위 윤곽. 몸통은 높이별 단면을 투영해 만듦 |
| `body.foot(side)`, `body.toes(side)` | 어느 각도에서나 쓰는 맨발 실루엣, 발끝이 보일 때만 나오는 발가락 5개 |
| `body.foot_axes(side)` | 발의 앞 방향과 바깥 방향 |
| `body.surface(part, x, y, side="front")` | 몸통 겉면의 몸 좌표 점과 바깥 법선. part는 thorax 또는 pelvis, side는 front 또는 back |
| `body.on_thorax(x, y, side)`, `body.on_pelvis(x, y, side)` | 겉면 점의 화면 좌표. x, y는 `figure.Figure`와 같은 흉곽 좌표와 골반 좌표 |
| `body.facing(normal)`, `body.facing_at(part, x, y, side)` | 법선이 관찰자를 향하는 정도(-1에서 1). 0 이하면 보이지 않는 면 |
| `body.bulge(part, x, y, z, radii)` | 부위 좌표의 타원체 윤곽. 가슴, 엉덩이, 골반 앞쪽의 둥근 덩어리 |
| `body.local_point(part, x, y, z)` | 부위 좌표의 점을 몸 좌표로 |
| `body.project(point)`, `body.project_path(points)`, `body.depth_of(point)` | 몸 좌표를 화면 좌표와 시선 깊이로 |
| `body.head_center()`, `body.head_yaw()` | 두개골 중심의 몸 좌표, 관찰자 기준 머리 각도 |
| `body.hand_frame(side, turn=0.0, flip=False)` | 투영된 아래팔 방향의 손 좌표계 |
| `body.inside_torso(point)` | 몸 좌표 점이 몸통 단면 안인지. 관통 점검(`stage.collisions`)에 씀 |
| `body.torso_section(y)` | 몸 좌표 높이 y의 몸통 단면 (가운데 x, 가운데 z, 반폭, 앞 두께, 뒤 두께). 머리카락 드레이프에 씀 |
| `Figure3D(..., in_front=("arm_l",))` | 몸 앞을 가로지르는 팔다리를 몸 다음에 칠함 |

## character

```python
from codepaint import character as ch
model = ch.place(look, origin, unit, turn, elevation=0.0, head_pitch=0.0, ink=ch.ANIME, outfit=None, grips=(), **자세)
ch.paint_figure(canvas, model, defer=())
ch.paint_deferred(canvas, model, ("arm_l",))
look = ch.restyle(ch.FEMALE, face=faces.FEMALE_SOFT, hair=hairstyles.LONG_STRAIGHT,
                  hair_color=hairstyles.HAIR_COLORS["pink"])   # 얼굴, 머리, 머리색 템플릿 고르기
ch.Ink(light, light3d, line_width, line_scale, line_opacity, body_shadow, face_shadow, hair_shadow, shadow_soft,
       light_opacity)
```

| 호출 | 역할 |
|---|---|
| `ch.FEMALE`, `ch.MALE` | 성인 여성과 남성의 모습(Look: 성별, 체형, 몸통 두께, 머리 모양, 머리카락, 색, 어깨 내림, 얼굴 템플릿) |
| `ch.restyle(look, face=None, hair=None, hair_color=None)` | 얼굴 템플릿(얼굴형 포함), 머리 모양, 머리색만 바꾼 모습. 머리색은 팔레트의 hair, hair_shade, hair_light, line_hair만 바꿈 |
| `ch.face_spec(look)` | 모습의 얼굴 템플릿. `look.face`가 None이면 성별 기본 얼굴 |
| `ch.lowest_foot(look, unit, turn, elevation, **자세)` | 골반 중심에서 가장 낮은 발 끝까지의 화면 높이. 바닥에 발을 붙일 때 씀 |
| `ch.paint_figure(canvas, model, defer=())` | 인물 1명. defer의 팔다리 덩어리는 건너뜀 |
| `ch.paint_deferred(canvas, model, names)` | 미룬 덩어리(살, 표지, 옷)를 칠함 |
| `ch.paint_garment(canvas, model, piece)` | 옷 조각 1개 |
| `ch.choose_hand(model, side)` | 그 손의 Hand와 손가락 칠하는 순서. 막대 뒤로 손을 빼낼 때 씀 |
| `ch.paint_fingers(canvas, model, side)` | 손가락을 하나씩 칠함. 엄지 선은 손바닥 안쪽 구간만 옅게(`THUMB_LINE_ON_PALM` 0.35) 그어 손바닥과 이어지게 함 |
| `Ink.lit_from(light, light3d)` | 빛 방향만 바꾼 Ink |

## garment

```python
from codepaint import garment
outfit = garment.formal_dress(dress="#a8202c", length=3.75, flare=1.0, wave=0.09, swirl=55)
Garment(name, group, paths, palette, lines=(), dots=(), order=0, shine=0.0, facing=0.0, merge="")
Hem(length, flare=0.2, wave=0.0, waves=7, swirl=0.0, drift=0.0)
```

| 호출 | 역할 |
|---|---|
| `casual_knit`, `casual_shirt`, `formal_dress`, `formal_suit`, `long_coat`, `mage_robe`, `light_armor` | 옷 한 벌. 색을 받아 '몸을 받아 조각 목록을 돌려주는 함수'를 돌려줌 |
| `loft(body, top, bottom, ease, hem=None, half=None, loose=0.0)` | 몸통 옷(Loft). `.outline()` 화면 윤곽, `.line_at(angle)` 세로선, `.ring_line(index)` 가로선 |
| `limb_span(body, bone, side, t0, t1, scale, widths=None, caps=(True, True), root=None)` | 뼈 구간을 굵게 감싼 띠(소매, 바짓가랑이, 장화, 팔 보호대) |
| `limb_marks(body, side, [(뼈, t, 각도), ...])`, `limb_surface(...)` | 옷 입은 팔다리 겉면의 주름 선과 점 |
| `shoe(body, side, growth, lift)`, `neck_band(body, height, ease)`, `bulge(body, part, center, radii)` | 신발, 목도리와 높은 깃, 둥근 조각(어깨 갑옷) |
| `surface_curve(body, part, points)`, `surface_dots(body, part, points)` | 몸통 겉면의 깃, 여밈선과 단추 |
| `cloth(base)` | 밑색 하나에서 (밑색, 그림자, 밝은 면, 선) 색 |

## stage

```python
from codepaint.stage import Stage, Collision, arm_toward, ELBOW_POLE
stage = Stage(origin, unit, elevation=0.0)        # origin은 세계 원점(바닥 가운데)의 화면 좌표
model = stage.place(look, x, z, turn, floor=0.0, head_pitch=0.0, ink=..., outfit=..., reach=None, pelvis_y=None,
                    grips=(), palm_out=(), poles=None, fists=None, **자세)
hits = stage.collisions([model_a, model_b])       # [Collision(model, limb, other, part), ...]. 빈 목록이면 관통 없음
```

- `reach={"arm_r": 세계 좌표}`는 손목, `fists={"arm_r": 세계 좌표}`는 쥔 주먹 가운데(`fist_world`)를 목표에 맞춤
- `poles={"arm_r": (바깥, 아래, 뒤)}`는 그 팔의 팔꿈치 방향(몸 좌표). 생략하면 `ELBOW_POLE` (0.45, 1.0, 0.35)
    + 어깨를 맞댄 두 사람의 안쪽 팔은 바깥이 상대 쪽이라 기본값이면 팔꿈치가 상대 몸으로 꺾임. 바깥 성분을 0 이하로 줄임
- `palm_out=("r",)`이면 그 쥔 손의 손바닥이 몸 바깥(옆 사람 쪽)을 향함. 맞잡은 두 손의 손가락이 서로를 감쌈
- `Collision`의 limb는 `forearm_r`처럼 뼈 이름과 쪽, part는 `torso` 또는 상대 팔 뼈 이름

| 호출 | 역할 |
|---|---|
| `stage.project(points)`, `stage.point(x, y, z)`, `stage.depth(point)` | 세계 좌표를 화면 좌표와 시선 깊이로 |
| `stage.joint_world(model, name)`, `stage.fist_world(model, side)`, `stage.to_world(model, point)` | 인물의 관절, 주먹 가운데, 몸 좌표 점의 세계 좌표 |
| `stage.far_first(models)` | 먼 사람부터 정렬 |
| `stage.collisions(models)` | 팔 뼈 중심선이 다른 인물의 몸통 안에 들거나 두 인물의 팔 뼈 거리가 굵기 합보다 작은 자리의 목록 |
| `stage.box(x, y, z 범위)` | 보이는 면 [(이름, 윤곽, 법선)] |
| `stage.cylinder(center, radius, top, bottom)` | {'side', 'top'} 윤곽. 옆면 다음에 윗면을 칠함 |
| `stage.ellipse(center, radius, y, radius_z=None)` | 바닥과 나란한 원(탁자 윗면, 접시, 바닥 그림자) |
| `arm_toward(shoulder, target, side, pole=ELBOW_POLE)` | 몸 좌표 목표에 손목이 닿는 팔 각도(벌림 2개, 흔들기 2개) |

## head3d

```python
from codepaint.head3d import Head3D, HeadSpec, HairStyle, Lock, FEMALE_HEAD, MALE_HEAD
head = Head3D.on_body(body, FEMALE_HEAD, pitch=0.0)       # Figure3D의 머리 자리와 각도에 맞춤
head = Head3D(frame, spec=FEMALE_HEAD, yaw=0.0, elevation=0.0, pitch=0.0)   # frame 단위는 두개골 반지름
HairStyle(thickness, hairline, locks, hang_from=0.3)
Lock(root, tip, width, lift=0.1, bulge=0.0, taper=(1.0, 0.95, 0.75, 0.35, 0.0), drape="", spread=0.0)   # root, tip은 (phi, v)
```

| 호출 | 역할 |
|---|---|
| `head.silhouette()` | 머리 윤곽 [두개골, 얼굴]. `figure.shape_of`로 합쳐 칠함 |
| `head.face(origin=(0, 0), unit=1.0, flip=False)` | 얼굴 표 좌표계(FaceFrame). craft.md의 정면 좌표를 넣으면 이 각도의 화면 좌표가 나옴 |
| `face(points)`, `face.point(x, y, lift=0)` | 점열과 점 1개. 세 번째 값은 얼굴면에서 앞으로 뜬 높이(콧대) |
| `face.child(x, y, unit)`, `face.mirrored()`, `face.length(value)` | 하위 좌표계(눈), 좌우 반전, 화면 길이 |
| `face.facing(x, y)`, `face.ellipse(x, y, rx, ry)` | 그 자리 얼굴면이 관찰자를 향하는 정도, 얼굴면에 붙인 타원(홍채, 볼 터치) |
| `head.ear(side)` | (바깥 윤곽, 안쪽 귓바퀴 선, 향하는 정도). 0.5보다 크면 머리 위에, 작으면 머리보다 먼저 칠함 |
| `head.nose_tip()` | 코끝의 화면 좌표 |
| `head.cap(style)` | 두피를 덮는 머리카락 윤곽 목록. 합쳐서 칠함 |
| `head.face_window(style)` | 덮개에서 빼낼 얼굴 자리. 얼굴이 보이지 않는 각도면 None |
| `head.locks(style)` | 다발 윤곽을 층별로 {"back": [...], "front": [...]}. back은 몸보다 먼저, front는 덮개 다음에 칠함. drape 다발은 몸이 필요하므로 `hairstyles.lock_layers`를 씀 |
| `head.lock_samples(style, lock, count)` | 다발 중심선의 머리 좌표 점과 법선 |
| `head.shell(phi, v, offset)`, `head.hairline(style, phi)` | 두피 위 점과 법선, 머리카락이 시작되는 높이. 빛 띠와 결 선에 씀 |
| `head.facing(normal)`, `head.view_vector(vector)` | 머리 좌표 법선이 관찰자를 향하는 정도, 시선 좌표로 바꾼 방향(빛 계산) |

- 머리 각도 phi는 0이 얼굴 정면, 90이 정면에서 본 화면 오른쪽 옆머리, 180이 뒤통수
- hairline은 0-180도의 (phi, v)를 적으면 좌우 대칭으로 씀
- `Lock.drape`는 어깨 아래로 내려오는 다발이 몸통을 따라 흐를 쪽(front 또는 back), `Lock.spread`는 내려갈수록 옆으로 벌어지는 양

## faces

얼굴 템플릿. 사용법과 목록은 `references/figure.md`의 얼굴과 머리 템플릿.

```python
from codepaint import faces
FaceSpec(head, eye, eye_center, eye_unit, brow, nose_bridge, nose_tip_y, mouth, blush=(), blush_at=(0.55, 0.74),
         blush_radii=(0.2, 0.08), chin_shade=(), stubble=0.0)
EyeShape(white, white_corners, iris, pupil, gleam, lid, lid_corners, lower, lower_style, iris_span, sclera, pupil_color,
         crease=(), crease_style=(1.3, (0.2, 1, 0.2), 0.6))
BrowShape(points, fill=False, corners=(), width=2.8, taper=(0.7, 1, 0.1))
MouthShape(lips, line, line_width, line_taper, lower=(), upper=(), shade=(), philtrum=())
```

| 이름 | 내용 |
|---|---|
| `faces.FEMALE_MATURE`, `FEMALE_SOFT`, `FEMALE_SHARP` | 여성 얼굴 3종. `faces.FEMALE_FACES` 사전 |
| `faces.MALE_CLEAN`, `MALE_GENTLE`, `MALE_RUGGED` | 남성 얼굴 3종. `faces.MALE_FACES` 사전 |
| `faces.ALMOND_EYE`, `NARROW_EYE`, `DROOPY_EYE`, `CAT_EYE`, `GENTLE_EYE`, `DEEP_EYE` | 눈 모양 |
| `faces.SOFT_FEMALE_HEAD`, `SHARP_FEMALE_HEAD`, `GENTLE_MALE_HEAD`, `RUGGED_MALE_HEAD` | 얼굴형(턱 단면) |

- 좌표는 craft.md 얼굴 표와 같은 정면 기준. 눈은 눈 중심 원점, 눈 반폭 1인 하위 좌표계

## hairstyles

머리 모양 템플릿과 긴 머리 드레이프. 사용법과 목록은 `references/figure.md`의 얼굴과 머리 템플릿.

| 호출 | 역할 |
|---|---|
| `hairstyles.BOB`, `LONG_STRAIGHT`, `SHOULDER`, `PONYTAIL` | 여성 머리 4종(턱선 단발, 긴 생머리, 어깨선 중단발, 묶은 머리). `FEMALE_HAIRS` 사전 |
| `hairstyles.SHORT`, `SIDE_PART`, `CROPPED`, `MALE_LONG` | 남성 머리 4종(짧은 머리, 옆 가르마, 아주 짧은 머리, 목을 덮는 긴 머리). `MALE_HAIRS` 사전 |
| `hairstyles.lock_layers(model)` | 다발 윤곽을 층별로 {"back": [...], "tucked": [...], "front": [...]}. drape 다발은 몸통을 따라 흐르게 계산하고 얼굴 뒤를 지나는 다발은 tucked로 나눔 |
| `hairstyles.HairColor(base, shade, light, line)` | 머리색 1개 |
| `hairstyles.HAIR_COLORS` | 머리색 12종 사전: black, dark_brown, chestnut, blonde, silver, pink, sky_blue, navy, red, purple, mint, orange |
| `hairstyles.head_to_body(model)` | 머리 좌표 점을 몸 좌표로 옮기는 (원점, 행렬). 옮긴 점은 같은 화면 자리에 투영됨 |
| `hairstyles.drape(body, points, side)` | 몸 좌표 중심선에서 몸통에 든 구간을 side 쪽 겉면 밖으로 밀어낸 점열 |

## Perspective

사용법은 `references/subjects.md`.

```python
Perspective(vanish, eye_height=1.6, focal=900.0)
```

| 호출 | 역할 |
|---|---|
| `project(x, y, z)` | 장면의 점(x 좌우, y 높이, z 깊이)을 화면 좌표로 |
| `path(points)` | 장면 점열을 화면 경로로 |
| `scale_at(z)` | 깊이 z에서 장면 길이 1의 화면 길이 |
| `side_wall(x, z_near, z_far, y_bottom, y_top)` | 깊이 방향으로 뻗은 벽 |
| `front_wall(x_left, x_right, z, y_bottom, y_top)` | 카메라를 마주 보는 벽 |
| `ground(x_left, x_right, z_near, z_far, y=0.0)` | 지면 위의 사각형 |
| `side_wall_grid(x, z_near, z_far, y_bottom, y_top, columns, rows, margin=0.25)` | 옆면 벽의 칸 목록(창문) |
| `front_wall_grid(x_left, x_right, z, y_bottom, y_top, columns, rows, margin=0.25)` | 정면 벽의 칸 목록 |

## styles

### anime

| 호출 | 역할 |
|---|---|
| `cel(canvas, outline, base, shade=None, amount=0.0, line=None, width=3.0, light=(-0.6, -0.8))` | 셀 부품 1개: 밑색, 자동 그림자, 윤곽선. 채운 형태 반환 |
| `rim_light(canvas, light, width=4.0, tint="#fff4dc", opacity=0.7)` | 투명 배경 캔버스의 광원 쪽 윤곽에 빛 테두리 |
| `finish(canvas, diffusion, bloom, shadows, highlights, grade_amount, aberration, grain)` | 촬영 효과를 입힌 이미지 반환 |

### oil

```python
oil.render(canvas, brush_radii=(22.0, 10.0, 4.5), relief=0.55, weave=0.05, color_jitter=0.05, detail=None)
```

- 밑그림을 다층 붓질로 다시 그린 이미지 반환
- detail에 형태를 주면 가장 작은 붓이 그 안에서만 쓰임

### watercolor

```python
watercolor.wash(canvas, outline, paint, opacity=0.85, soft=6.0, rough=7.0, blend=Blend.MULTIPLY, cover=False)
watercolor.render(canvas, wobble=2.2, bleed=0.55, turbulence=0.30, granulation=0.22, edge=0.55, paper_tint="#fbf7ee")
```

- `wash`는 붓 자국 1개를 칠하고 형태 반환
- `render`는 안료와 종이 효과를 입힌 이미지 반환

### illustration

```python
illustration.render(canvas, roughness=0.8, ink_mottle=0.10, paper_tint="#f7f1e3", paper_fiber=0.05, misregister=0.0)
```

- 인쇄 질감을 입힌 이미지 반환

## solids

사용법은 `references/subjects.md`의 현대 사물. 장면 좌표는 x 오른쪽, y 위, z 깊이.

| 호출 | 역할 |
|---|---|
| `box(center, size)` | 직육면체. 면 이름 front, back, left, right, top, bottom |
| `slab(center, size, radius=0.0, segments=10)` | 모서리가 둥근 판. 면 이름 front, back, side |
| `prism(outline, depth, smooth_sides=False)` | xy 평면 윤곽을 z 방향으로 밀어낸 기둥 |
| `cylinder(base_center, radius, height, top_radius=None, segments=64)` | 원기둥과 원뿔대. 면 이름 top, bottom, side |
| `circle(center, radius, segments=64)` | 수평 원 위의 3차원 점열 |
| `solid.moved(offset)`, `solid.rotated(yaw=0, pitch=0, about=(0, 0, 0))` | 새 Solid를 돌려주는 변형 |
| `solid.face(name)`, `solid.center` | 이름으로 면 찾기, 중심 |
| `face.point(u, v)`, `face.region(u0, v0, u1, v1)` | 면 위 0-1 좌표의 3차원 점과 사각 영역 |
| `Camera(eye, target, focal=1200, center=(800, 450))` | 원근 카메라 |
| `camera.project(point)`, `camera.path(points)` | 화면 좌표로 투영 |
| `camera.depth(point)`, `camera.scale_at(point)` | 깊이, 그 깊이에서 길이 1의 화면 길이 |
| `camera.visible_faces(solid)`, `camera.order(solids)` | 보이는 면과 입체를 먼 것부터 정렬. order는 중심 깊이 기준이라 책상 같은 받침 면은 넣지 않음 |
| `camera.region(face, u0, v0, u1, v1)` | 면 위 사각 영역의 화면 경로 |
| `camera.face_ellipse(face, u, v, radius_u, radius_v=None)` | 면 위 타원의 화면 경로 |
| `face_color(base, normal, light, ambient=0.35, highlight=0.25)` | 빛 각도에 따른 면의 색 |
| `draw(canvas, camera, solid, paint, light, line=None, width=2.0, opacity=1.0)` | 입체를 칠하고 면 이름별 형태 사전 반환 |

- `paint`는 색 1개 또는 `{면 이름: 색}` 사전. 사전에 없는 면은 `"*"`의 색을 씀

## props

모든 함수는 `Prop`을 반환. position은 물건 바닥 중심(cm), yaw는 위에서 볼 때 시계 방향.

| 호출 | 부위(solids) | 면(faces) |
|---|---|---|
| `laptop(position, yaw=0, size=(31, 21.5), open_angle=108)` | base, lid | screen, deck |
| `monitor(position, yaw=0, size=(60, 34), stand_height=11, tilt=6)` | foot, neck, panel | screen |
| `keyboard(position, yaw=0, size=(44, 13.5), height=2.0)` | body | keys |
| `phone(position, yaw=0, size=(7.2, 15.0), thickness=0.8)` | body | screen |
| `mug(position, radius=4.2, height=9.5, handle=True)` | body, 선 handle | surface |
| `book(position, yaw=0, size=(15, 2.6, 22))` | body | cover |
| `desk_lamp(position, yaw=0, reach=26, height=38, shade_radius=7)` | base, shade, 선 arm | 점 bulb |

| 호출 | 역할 |
|---|---|
| `prop.draw(canvas, camera, paints, light, line=None, width=2.0)` | paints는 `{부위 이름: 색 또는 면 이름별 색 사전}`. 선 부위는 색이 있을 때만 그림 |
| `keycaps(canvas, camera, face, color, rows=5, columns=15, gap=0.18, light_edge=None, area=(0, 0, 1, 1))` | 면 위 자판 격자 |
| `LAPTOP_KEY_AREA`, `LAPTOP_TOUCHPAD` | 노트북 deck 면의 자판 영역과 터치패드 영역 |

## post

모든 함수는 이미지를 받아 이미지를 반환.

| 호출 | 역할 |
|---|---|
| `bloom(image, threshold=0.75, radius=24.0, strength=0.5)` | 밝은 곳의 빛 번짐 |
| `diffusion(image, radius=12.0, strength=0.3)` | 화면 전체의 부드러운 공기감 |
| `grade(image, shadows=None, highlights=None, amount=0.15, contrast=1.0, saturation=1.0)` | 어두운 곳과 밝은 곳에 색조를 입히는 색 보정 |
| `vignette(image, strength=0.25, softness=0.75)` | 가장자리를 눌러 시선을 중앙으로 |
| `grain(image, amount=0.03, seed=0, size=1.0)` | 필름 입자 |
| `chromatic_aberration(image, shift_px=1.0)` | 렌즈 색수차 |
| `light_gradient(image, color, start, end, strength=0.3, screen=True)` | 화면 한쪽에서 드는 빛 또는 그늘. start와 end는 0-1 화면 비율 |

- radius와 shift_px는 픽셀 단위이므로 `값 * canvas.scale`로 전달

## io

| 호출 | 역할 |
|---|---|
| `save(image, path)` | PNG 저장. 폴더가 없으면 생성 |
| `crop(image, box, scale, zoom=2.0)` | 논리 좌표 box 영역을 잘라 확대 |
| `sheet(images, columns=2)` | 여러 이미지를 한 장에 배치. 단계 비교용 |

## noise

| 호출 | 역할 |
|---|---|
| `fbm(shape_hw, scale_px, seed, octaves=4)` | 프랙탈 노이즈 0-1 |
| `value_noise(shape_hw, scale_px, seed)` | 부드러운 노이즈 0-1 |
| `white(shape_hw, seed)` | 백색 노이즈 0-1 |
| `paper_texture(shape_hw, seed, scale=1.0)` | 수채화지 요철 |
| `canvas_weave(shape_hw, seed, scale=1.0)` | 캔버스 직조 무늬 |

- 장면 코드에서 직접 쓸 일은 드물고 새 화풍 패스를 만들 때 사용
