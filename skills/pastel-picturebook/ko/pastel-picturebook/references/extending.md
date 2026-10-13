# 확장 방법

설정만으로 표현하지 못하는 요소를 추가하는 방법. 난이도 순서로 정리

## 목차

- 소품 추가 (훅 모듈)
- 기본기 함수
- 장면 객체
- 새 표정과 개성 프리셋
- 새 머리 모양
- 새 의상
- 새 내장 소품
- 새 실내 사물
- 새 화풍
- 손에 드는 새 물건
- 새 피사체
- 새 자세와 체형
- 새 장면 소품과 손 목표 지점

## 소품 추가 (훅 모듈)

- `--extras <파일>.py`로 넘긴 모듈의 함수 2개가 정해진 시점에 호출됨
    + `after_background(scene)`: 배경 직후. 인물 뒤에 놓일 요소(창문, 달, 식물)
    + `after_figure(scene)`: 인물 직후. 인물 앞에 놓일 요소(안경, 귀걸이, 꽃잎)
- 핵심 파일을 고치지 않으므로 기존 그림에 영향이 없음
- 안경, 모자, 목도리, 가방은 내장 소품(설정의 `accessories`, `references/spec.md`)으로 바로 쓸 수 있음. 아래 안경 예제는 훅 작성법의 본보기

```python
"""둥근 안경 예제."""
import numpy as np
from raster import ellipse, fill, over, rgb, screen, smooth, stroke

FRAME_COLOR = "#2A2230"

def after_figure(scene):
    fig, unit = scene.fig, scene.px(1.0)
    centers = [fig.points["eye_far_center"], fig.points["eye_near_center"]]
    rings = [ellipse(center + [0, 0.03 * unit], 0.30 * unit, 0.27 * unit, 64) for center in centers]
    for ring in rings:
        screen(scene.image, rgb("#FFFFFF"), fill(scene.size, ring), 0.10)
        over(scene.image, rgb(FRAME_COLOR), stroke(scene.size, np.vstack([ring, ring[:1]]), 0.022 * unit))
    inner_far = rings[0][np.argmin(np.linalg.norm(rings[0] - centers[1], axis=1))]
    inner_near = rings[1][np.argmin(np.linalg.norm(rings[1] - centers[0], axis=1))]
    bridge = smooth([inner_far, 0.5 * (inner_far + inner_near) - [0, 0.04 * unit], inner_near])
    over(scene.image, rgb(FRAME_COLOR), stroke(scene.size, bridge, 0.020 * unit))
```

- 소품 위치는 이미 계산된 기준점에서 가져옴
    + `fig.points`: `eye_far_center`, `eye_near_center`, `nose_tip`, `pendant`, `hair_band`
    + `fig.shapes`: `face`, `skin_body`, `cloth`, `hair_near`, `hair_far`, `hair_back`, `upper_lip`, `lower_lip` 등 닫힌 윤곽
    + `fig.paths`: `jaw`, `mouth_line`, `cloth_neckline`, `collar_r` 등 열린 곡선
- 머리 좌표로 위치를 지정할 때는 `fig.head_frame.project([(x, y, z)])` 사용
    + 귀 위치 예: `(-1.0, 0.25, -0.1)`
- `pose.mirror`는 완성 그림을 뒤집으므로 소품도 함께 뒤집힘

## 기본기 함수

`scripts/raster.py`. 이미지는 0-1 범위 float32 RGB, 좌표는 픽셀 (x, y)

| 함수 | 용도 |
|---|---|
| `smooth(points, closed=False)` | 제어점을 지나는 매끄러운 곡선 |
| `ellipse(center, rx, ry, count, angle_deg)` | 타원 윤곽 |
| `join(a, b, ...)` | 곡선 이어붙이기. 이음매는 모서리로 남음 |
| `taper(count, start, end, peak_at)` | 획의 굵기 분포 |
| `fill(size, polygon)` | 닫힌 윤곽의 마스크 |
| `stroke(size, path, widths)` | 굵기가 변하는 획의 마스크 |
| `over(image, color, mask, opacity)` | 일반 합성 |
| `multiply(...)`, `screen(...)` | 어둡게, 밝게 합성 |
| `blur(field, sigma)`, `shift(mask, dx, dy)` | 번짐, 이동 |
| `noise(size, cell, seed)` | 부드러운 노이즈 |
| `lambert(mask, light, sigma)` | 도형을 부풀려 얻은 조명량 |

- 그리는 순서는 항상 곡선, 마스크, 색, 선
    + 곡선으로 윤곽을 만들고 `fill`로 마스크를 얻은 뒤 `over`로 칠하고 `stroke`로 선을 얹음

## 장면 객체

`after_*` 훅과 `painter.py`의 모든 함수가 받는 `scene`

| 속성 | 설명 |
|---|---|
| `scene.image` | 현재 그림. 제자리에서 수정 |
| `scene.size` | (높이, 폭) |
| `scene.fig` | 밑그림 전체 |
| `scene.px(단위)` | 머리 단위를 픽셀로 변환 |
| `scene.mask(이름)` | `fig.shapes`의 마스크(캐시) |
| `scene.tone(그룹, 키)` | 팔레트 색 |
| `scene.edge(그림자량)` | 화풍의 경계 처리 적용 |
| `scene.soften(마스크, 번짐)` | 화풍에 맞춘 가장자리 처리 |
| `scene.ink(path, width, ...)` | 화풍의 선 굵기를 따르는 선 |
| `scene.shade_on`, `scene.lines_on` | 단계 이미지용 스위치. 명암과 선은 이 값이 참일 때만 그림 |
| `scene.rng` | 시드가 고정된 난수 |

- 소품도 화풍을 따르게 하려면 `scene.edge`, `scene.soften`, `scene.ink`를 사용
    + 직접 `over`만 쓰면 모든 화풍에서 같은 모양으로 그려짐

## 새 표정과 개성 프리셋

- 코드 수정 없이 JSON에 프리셋을 추가
    + 표정: `assets/expressions.json`, 개성: `assets/looks.json`의 `face_shape`, `eye_shape`, `hair_style`
- 프리셋은 설정 경로(점으로 이은 키)에 대한 연산 묶음

| 연산 | 의미 | 예 |
|---|---|---|
| `add` | 현재 값에 더함 | `{"mouth.smile": 0.05}` |
| `scale` | 현재 값에 곱함 | `{"eyes.open_down": 0.75}` |
| `set` | 값으로 옮김(문자열은 그대로 지정) | `{"eyes.arch": 0.15}`, `{"hair.style": "bun"}` |
| `style_scale` | 화풍 값에 곱함 | `{"face_render.blush_opacity": 1.4}` |
| `flags` | 표정 정보에 복사(그리기 분기용) | `{"tears": true}` |

```json
"sleepy": {"scale": {"eyes.open_up": 0.45, "eyes.open_down": 0.8}, "add": {"eyes.gaze_y": 0.03, "mouth.smile": 0.01}}
```

- 모든 연산은 `amount`(0-1)만큼 섞임. 사용자가 직접 적은 값은 바뀌지 않음
- 한쪽 눈만 바꾸려면 `eyes.near.<키>`, `eyes.far.<키>` 경로를 사용
- 새 피부색, 머리색, 눈색은 `looks.json`의 `skin_tone`(목표 피부색 1개), `hair_color`(5색 팔레트), `eye_color`(홍채 3색)에 이름과 색을 추가
- 추가 후 같은 설정으로 3개 화풍을 렌더링해 비례가 깨지지 않는지 확인

## 새 머리 모양

- `figure.py`의 `hair_guides`에서 구획별 가이드 제어점을 수정
    + 가이드는 뿌리에서 끝으로 진행하는 (x, y, z) 점 목록
    + 이마 위 점은 `fz(x, y)`로 얼굴 표면 깊이를 부여
    + 늘어지는 구간은 `drop(비율)`로 높이를 지정해야 `hair.length`가 계속 작동
- 묶은 머리나 올림머리는 구획을 추가
    + `sections`에 (안쪽 가이드, 바깥쪽 가이드)를 추가하고 `paint_figure`에 `paint_hair_section` 호출을 순서에 맞게 삽입
- 수정 후 `1_sketch`로 가이드가 서로 교차하지 않는지 확인

## 새 의상

- 전신 의상은 `subject_figure.py`의 `paint_dress`, `paint_shirt`, `paint_pants`, `paint_drape`, `wardrobe.py`의 `paint_skirt`, `paint_jacket`, `paint_jeogori`가 본보기
    + 소매가 있는 옷은 `wardrobe.long_sleeves`로 소매를 만들고 `paint_garments`의 소매 목록에 추가
    + 측면 대응은 `wardrobe_profile.py`의 `top_piece`(상의), `skirt_piece`(치마), `trousers`(바지)를 조합
    + 몸 부위 마스크와 척추 좌표(`spine_at`, `spine_side`)로 윤곽을 만들고 `hang_fabric`으로 늘어짐 계산
    + `paint` 함수의 의상 칠 순서에 추가하고 `figure.clothes`에 키를 추가
- 짧은 본보기는 `wardrobe_casual.py`
    + 몸판 위에 얹는 부분(후드, 주머니, 끈)은 몸판을 칠한 뒤 같은 마스크 안에 덧그림
    + 몸에 밀착하는 옷(수영복)은 `cling`처럼 몸의 높이장을 흐려 그대로 사용
    + 정면과 뒷모습은 `body.view`로 갈라 다른 세부를 그림
    + 칠하는 순서 목록(`subject_figure.GARMENTS`, `wardrobe_profile.GARMENT_KEYS`)에 키를 넣어야 팔이 옷 위로 다시 올라감
- 색은 `kit.shade_solid`(또는 `wardrobe.shade_cloth`)로 칠하면 팔레트 묶음의 `pattern`이 자동으로 적용됨
- 초상 의상은 `figure.py`의 `outfit_curves`가 반환하는 윤곽(`cloth`), 목선(`neckline`), 주름(`folds`)을 교체
- `painter.py`의 `paint_outfit`은 윤곽 채움, 형태 그림자, 주름 그림자, 선 순서로 구성
    + 깃, 단추, 무늬는 같은 함수 끝에 `fill`과 `stroke`로 추가
- 간단한 덧옷(재킷, 스카프)은 훅 모듈의 `after_figure`에서 `fig.shapes["cloth"]`를 기준으로 그리는 편이 안전

## 새 내장 소품

- `scripts/accessories.py`에 기본값 dict를 `DEFAULTS`에 등록하고 그리기 함수를 추가
- 머리 소품은 머리 좌표(x 오른쪽, y 아래, z 관객 쪽, 눈 중간 원점)로 정의해 `fig.head_frame.project`로 투영하면 고개 돌림을 따름
    + 측면은 `fig.extra["profile"]["head"]`가 같은 역할
- 호출 위치
    + 초상: `painter.paint_figure`(머리카락 앞뒤 순서에 맞춰)
    + 정면과 뒷모습 전신: `subject_figure.paint_head_front`, `paint_head_back`, 몸 소품은 `paint_garments`
    + 측면: `anatomy_profile.paint_head`, 몸 소품은 `wardrobe_profile.paint_garments`
- 머리카락을 누르는 소품은 `press_hair`처럼 미리 저장한 배경(`remember_background`)으로 삐져나온 머리를 지움
- 색 묶음은 `assets/accessories.json`에 추가

## 새 실내 사물

- `scripts/interior.py`에 `paint_<이름>(scene, camera, item, floor_mask)` 함수를 쓰고 `WALL_ITEMS`(벽) 또는 `FLOOR_ITEMS`(바닥)에 등록
    + 좌표는 센티미터(X 오른쪽, Y 위, Z 안쪽). `camera.project`로 화면 좌표, `camera.scale(점)`으로 cm당 픽셀
    + 상자 모양은 `subject_desk.paint_box`, 둥근 것은 `relief.lathe`나 `disc_with_rim`, 바닥 그림자는 `floor_shadow`
    + 켜지는 광원은 `keep_lit`(밤에 어두워지지 않게)과 `scene.glows`(빛 번짐)에 등록
- 색 묶음은 `assets/subject_cafe.json`, `subject_room.json`의 `style.palette`에 추가
- 새 실내 피사체(예: 사무실)는 `assets/subject_<이름>.json`에 `items`만 바꾸어 만들고 `render.py`의 `SUBJECT_MODULES`에 `"<이름>": "interior"`, `HORIZON_KEYS`와 `INTERIORS`에 이름을 등록(침실 `subject_bedroom.json`, 욕실 `subject_bathroom.json`이 본보기)
    + 새 사물 색 묶음은 그 피사체 파일의 `style.palette`에 추가. 벽 전체 무늬는 `room` 설정 키로 받아 `paint_shell` 다음 단계에서 그림(`room.wall_tiles`와 `paint_wall_tiles`)

## 새 화풍

- `assets/style_<이름>.json`을 복사하여 작성하고 `render.py`의 `STYLES`에 이름을 추가
- 결정 순서: `shading` 방식, `line_scale`, 팔레트, 비례(`figure`), 마감(`finish.kind`)
- 새 마감이 필요하면 `finish.py`에 함수를 추가하고 `FINISHERS`에 등록
- 다른 재료(판화, 유화 나이프, 색연필 등)를 흉내 내는 화풍은 `base` 방식이 가장 짧음
    + `{"name": "<이름>", "base": "illust", "finish": {"kind": "<이름>", ...}}`처럼 바탕 화풍을 물려받고 바꿀 값만 적음
    + 마감 함수는 `media.py`에 `finish_<이름>(image, fig, options, seed)`로 작성해 `FINISHERS`에 등록. 입력은 바탕 화풍의 완성 직전 그림(0-1 RGB), 출력도 같은 형식
    + 피사체별 `style_<바탕>` 팔레트 덮어쓰기는 `style_<이름>`이 없을 때 자동으로 따라옴

## 손에 드는 새 물건

- `held.py`에 `paint_<이름>(scene, grip, unit, group, ...)`을 작성해 마스크를 돌려주고 `GRIP`(손 안의 고정점), `GROUPS`(팔레트 묶음), `paint_held`의 분기에 등록
    + 물건은 손 뒤에 그려지고 손바닥, 손가락 마디, 네 손가락, 아래팔이 그 위에 다시 놓임. 엄지만 물건 뒤로 숨음
    + 와인잔(`paint_glass`)과 휴대폰(`paint_phone`)이 짧은 본보기
- 색 묶음은 `assets/subject_figure.json`의 `style.palette`에 추가

## 새 피사체

- `scripts/subject_<이름>.py`를 작성하고 `render.py`의 `SUBJECT_MODULES`에 등록
    + 기본 구성과 팔레트는 `assets/subject_<이름>.json`에 `spec`과 `style`로 저장
- 모듈이 제공해야 하는 함수 3개

```python
def build(spec):            # Figure 반환. 크기, 광원, 시드와 spec을 담음
def paint(fig, style, seed, shade=True, lines=True, extras=None):   # 이미지 반환
sketch = kit.sketch         # 밑그림 단계. kit.register로 등록한 윤곽을 그림
```

- 가장 짧은 본보기는 `scripts/subject_hand.py`, 사물 목록 방식은 `scripts/subject_still_life.py`
- 사람이 서는 야외 배경은 `interior.make_camera`의 센티미터 수평 카메라를 쓰면 `backdrop.place` "horizon"과 바로 맞음(`scripts/subject_park.py`, `scripts/subject_skyline.py`)
    + `render.py`의 `HORIZON_KEYS`에 ("camera", "horizon_y") 등록
    + 같은 모듈로 여러 피사체를 만들 때는 `SUBJECT_MODULES`에 이름마다 같은 모듈을 적고 `assets/subject_<이름>.json`만 다르게 둠
    + 반복되는 벽면(창 격자, 타일)은 화소마다 역투영한 면 좌표에 나머지 연산을 쓰면 수천 개의 창도 한 번에 그림(`subject_blocks.paint_block`)
- 작성 순서
    + 디자인 메모 작성(구도, 광원, 팔레트)
    + 배경부터 앞쪽 순서로 칠함
    + 덩어리는 `relief.tube`, `relief.lathe`, `relief.ellipsoid`로 만들고 `kit.shade_solid`로 채색
    + 평면 도형은 `fill`과 `over`, 선은 `kit.ink_edges`
    + 바닥 그림자는 `kit.ground_shadow`
    + 회화풍 세밀도는 `fig.focus`(0-1 지도)에 기록

| 함수 | 용도 |
|---|---|
| `relief.tube(size, path, left, right, roundness)` | 경로를 따르는 관. 굵기는 경로점마다 지정 |
| `relief.lathe(size, axis_x, top_y, bottom_y, profile, tilt)` | 세로축 회전체 |
| `relief.ellipsoid(size, center, rx, ry)` | 공, 달걀꼴 |
| `relief.bump(...)` | 다른 면에 더하는 융기 높이 |
| `relief.union(parts, blend)`, `relief.place_over(base, part, lift)` | 한 덩어리로 합치기(`blend` px만큼 둥글게 이음), 앞에 겹치기 |
| `relief.blob(size, outline, depth)` | 임의 윤곽에서 가장자리만 둥근 입체 |
| `kit.shade_solid(scene, part, group, level, spread, gloss)` | 입체 채색. 화풍의 경계 처리를 자동 적용 |
| `kit.ink_edges(scene, mask, width)`, `kit.ink_tube(...)` | 외곽선, 뿌리를 생략한 관 외곽선 |
| `kit.vertical_gradient`, `kit.ridge_line`, `kit.below_line` | 하늘, 능선, 능선 아래 마스크 |

- 매 단계 렌더링을 직접 보고 고치는 반복은 모든 피사체에 동일하게 적용

## 새 자세와 체형

- 전신 자세는 설정의 `figure.pose` 각도로 조정(`references/subjects.md`)
    + 앉은 자세처럼 팔다리가 관객 쪽으로 나오는 자세는 `foreshorten`과 `toward`를 함께 지정
    + 팔다리가 몸 뒤로 가면 `toward` -1, 팔끼리 겹치면 위에 올 팔에 `over`
- 측면 자세의 대부분은 각도만으로 만들어짐(무릎 꿇기, 다리 꼬기, 벽에 발 대기). 몸에 닿는 사물은 그 자세의 골격 좌표에서 위치를 정해 인물보다 먼저 그림(`anatomy_profile.paint_wall`이 본보기)
- 몸과 머리의 시점이 다른 자세는 칠하는 순서만 바꿔 조합(뒷모습 몸에 `anatomy_profile.paint_turned_head`의 옆얼굴 머리를 얹는 `figure.look_back`)
- 손에 드는 새 물건은 `held.py`에 그리기 함수를 추가하고 잡는 위치 `GRIP`, 팔레트 `GROUPS`, `paint_held`의 분기에 등록
- 새 배경 장면은 피사체 모듈을 추가하면 `backdrop.subject`로 바로 사용 가능. 지평선이 있으면 `render.py`의 `HORIZON_KEYS`에 위치를 등록
- 뼈 길이와 부위 굵기는 `scripts/anatomy_body.py` 상단의 상수
    + 굵기 배열은 뿌리에서 끝 방향의 반폭(머리 단위)
- 새 체형(예: 근육질, 마른 체형)은 표를 하나 더 만듦
    + `anatomy_body.py`: `MALE = {**FEMALE, ...}`처럼 바꿀 키만 덮어쓴 dict를 `BUILDS`에 등록
    + `anatomy_profile.py`: 같은 방식으로 측면 표를 `BUILDS`에 등록
    + `assets/sex_<이름>.json`: 얼굴, 머리, 의상, 색 프리셋. 설정의 `sex`에 이름을 지정하면 병합됨
    + 점토 렌더링(채색 없이 회색 입체만)으로 형태를 먼저 확인한 뒤 채색
- 손 자세는 `scripts/anatomy_hand.py`의 `POSES`에 추가
    + 인물 크기에서 읽혀야 하는 손(V 사인 `peace`)은 손가락 벌림(`spread`)을 크게 둠
- 각도 맞추기가 번거로운 팔은 `reach`(손 목표점)로 두고 `bend`만 고름. 역산 코드는 `anatomy_body.solve_arm`, 측면은 `anatomy_profile.aim_arm`
- 새 측면 동작은 `lean`과 다리 각도의 조합. 각도는 몸 기준이므로 화면 각도에 `lean`을 더해 적음
- 깊이가 주인 정면 동작(걸어오기처럼 다리가 관객 쪽과 뒤쪽으로 갈림)은 `anatomy_body.stride_pose`처럼 키 하나가 팔다리의 각도, `foreshorten`, `toward`를 한꺼번에 채우는 프리셋으로 만듦
    + 뒤꿈치를 든 발은 다리 설정의 `tiptoe` true(발 길이 `TIPTOE_LENGTH`), 그 다리의 윤곽선은 다른 다리 뒤에 머묾
    + 뒤로 흔든 팔은 팔 설정의 `behind_clothes` true. 몸 뒤로 가는 팔 부분(`arm_behind`)이 맨몸 윤곽 밖의 옷 뒤에서도 숨음(`subject_figure.tucked_arms`)
    + 앉은 자세 표현(무릎 윤곽, 무릎 조명, 접힘, 부푼 바지)은 `body.seated`에 든 다리만 받음. 허벅지가 길이의 `SEATED_SHARE`(0.5) 넘게 관객 쪽으로 나와야 앉은 다리
- 누운 방향을 늘릴 때는 `lying.turns`(회전 코드), `frame_spec`(눈 위치와 광원 회전), `resting_side`(바닥에 닿는 쪽)를 함께 고침

## 새 장면 소품과 손 목표 지점

- 여러 인물이 함께 쓰는 소품은 `scripts/props.py`에 `paint_<이름>(scene, geo, mirror)`를 쓰고 `PAINTERS`에 등록
    + `geo`는 완성 그림 기준 픽셀 좌표. 그리는 인물이 좌우 반전이면 `flip_x`로 뒤집어 씀
    + 크기와 위치는 `render.resolve_props`가 재서 넘김. `render.bench_geometry`, `table_geometry`처럼 인물의 `measure`(지점과 몸 단위)로 계산하는 함수를 추가
    + 색 묶음은 `assets/subject_figure.json`의 `style.palette`에 추가(벤치는 `seat`, 탁자는 `table`)
- 손이 겨눌 새 지점
    + 머리: `subject_figure.HEAD_MARKS`(정면), `anatomy_profile.PROFILE_HEAD_MARKS`(측면)에 머리 좌표로 추가
    + 몸: `anatomy_body.joint_marks`(겨눌 때 쓰는 자세 전 관절)와 `subject_figure.landmarks`(장면에서 다른 인물이 읽는 지점)에 함께 추가
- 앞뒤가 엇갈리는 새 부위 재배치는 `subject_figure.lift_mask`(정면)와 `anatomy_profile.lift_mask`(측면, 칠할 때 저장하는 `fig.extra["arm_masks"]`)에 부위 이름과 마스크를 추가
    + 측면 인물이 겨눌 새 지점은 `anatomy_profile.landmarks`에 추가. 측면 팔의 `reach`도 `render.arms_of`가 읽어 상대 지점을 화면 위치로 바꿈
    + `render.paint_layer`가 그 인물이 칠한 화소로 한정하고 부위(`core`)와 바깥 윤곽 띠(`ring`)로 나눔. `lay_lifts`는 띠에서 아래보다 어두운 화소(윤곽선)만 올림
    + 뒤에 그린 인물의 얼굴과 앞머리 아래로 지나가게 하려면 `lift_under_head`. 가리는 영역은 그 인물이 그린 `fig.extra["head_cover"]`(얼굴, 가까운 머리, 몸 밖으로 나온 먼 머리)
- 비를 막는 물건은 `fig.extra["shelter"]`에 마스크를 더하면 날씨 단계가 그 영역의 빗줄기를 뺌
