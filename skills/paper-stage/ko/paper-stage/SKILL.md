---
name: paper-stage
description: "오려 쌓은 종이 무대처럼 그리는 코드 그림 스킬이다. 닫힌 곡선을 마스크로 오려 뒤에서 앞으로 겹친다. 부풀린 높이맵의 빛이 면마다 도톰한 입체감을 낸다. 인물은 세트, 소품, 조명 속에 배우처럼 조용히 연출된다. 마무리는 은은한 번짐, 필름 입자, 화풍별 질감이 맡는다. 화풍은 맑은 셀의 애니메, 포근한 그라데이션의 일러스트, 붓 결이 남는 회화풍 3종이다. 확산 모델, 이미지 생성 API, 3D 엔진 없이 Python(numpy, Pillow, scipy)만 쓴다. 대상은 흉상, 전신, 투샷, 단체 컷, 장면 세트, 인체 습작, 정물, 현대 사물, 도시, 풍경, 동물이다. 참조 문서는 drawing-process.md(단계별 기법과 결함 표), engine-api.md(엔진 함수), figure-rig.md(얼굴, 표정, 헤어, 색, 소품), figure-body.md(전신, 포즈, 손), clothing-and-scenes.md(겹옷, 가구, 구도, 장면 세트), subject-recipes.md(리그 없는 주제), style-recipes.md(화풍 수치와 무드)다. '코드로 그림 그려줘', '일러스트 그려줘', '애니메풍 캐릭터', '전신 캐릭터', '옆모습', '앉은 자세', '커플 그림', '장면 그려줘', '후드티', '정장 입은', '포니테일', '안경 쓴', '인물화', '정물화', '풍경화', '도시 야경', '책상 일러스트', '유화 느낌으로', 'paper-stage', '/paper-stage', 'draw with code' 같은 요청에서 이미지 생성 도구가 없거나 코드 제작을 원하면 반드시 이 스킬을 사용한다. 차트, 다이어그램, UI 목업, 로고에는 쓰지 않는다."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE
---

# paper-stage

코드로 그림을 그리는 스킬. 화가의 작업 순서(기획, 형태, 선, 채색, 명암, 후보정)를 그대로 코드 단계로 옮긴다.

## 원칙

- 그림 1장은 닫힌 곡선으로 만든 조각(part)을 뒤에서 앞으로 쌓아서 구성
    + 조각 1개는 곡선, 마스크, 밑색, 명암, 외곽선 순서로 완성
- 화풍은 장면 코드와 분리
    + 장면 코드 1개를 `anime`, `illust`, `painterly` 3종으로 렌더링 가능
- 매 단계는 렌더링 결과를 눈으로 확인한 뒤 다음 단계로 진행
    + 좌표를 머릿속 계산만으로 확정하면 형태 오류가 누적
- 확산 모델, 이미지 생성 API, 3D 엔진은 사용 금지
    + 의존성은 numpy, Pillow(10.1 이상), scipy로 한정

## 준비

```bash
python -c "import numpy, PIL, scipy; print(PIL.__version__)"   # 실패 시 pip install numpy pillow scipy
```

- 엔진 위치는 이 스킬 폴더의 `scripts/codepainter/`
    + 작업 스크립트 첫머리에 `sys.path.insert(0, "<스킬 폴더>/scripts")` 삽입
- 동작 확인은 `python scripts/examples/portrait.py --style anime --out test.png`

## 작업 절차

각 단계의 산출물을 파일로 남긴다. 상세 기법은 `references/drawing-process.md` 참조.

### 1단계 (기획)

- 디자인 방향 문서(.md)를 먼저 작성
    + 핵심 인상 1문장, 구도, 색 3-5개, 빛의 방향, 화풍을 기록
- 명도 구조를 어두움, 중간, 밝음 3단으로 배분
    + 주제가 배경과 다른 명도에 놓여야 실루엣이 읽힘
- 화풍 선택 기준은 아래 표 적용

| 화풍 | 특징 | 적합한 요청 |
|---|---|---|
| `anime` | 굵기 변화가 있는 선, 경계가 선명한 2단 음영 | 애니메이션, 셀화, 만화 캐릭터 |
| `illust` | 가는 색선, 부드러운 음영, 림라이트, 종이 질감 | 일러스트, 웹툰 표지, 삽화 |
| `painterly` | 선 없음, 큰 붓에서 작은 붓 순서로 재도장 | 유화, 회화, 인상주의 |

### 2단계 (형태)

- 주제에 맞는 출발점을 아래 표에서 선택

| 주제 | 출발점 | 레퍼런스 |
|---|---|---|
| 인물 흉상 | 흉상 리그 `draw_portrait` | `references/figure-rig.md` |
| 전신(여성, 남성), 손, 인체 습작 | 전신 리그 `draw_figure`, 손 리그 `hand.draw_hand` | `references/figure-body.md` |
| 겹옷 의상, 앉기와 눕기, 가구, 투샷, 장면 | `clothing`, `props`, `stage.draw_actors`, `sets` | `references/clothing-and-scenes.md` |
| 정물, 현대 사물, 도시, 풍경, 동물 | 가장 가까운 `scripts/examples/` 예제를 복사해 수정 | `references/subject-recipes.md` |

- 리그가 없는 형태는 엔진 기본 도형으로 직접 구성
    + `references/engine-api.md`에 전체 함수 수록
- 큰 덩어리부터 배치 후 실루엣을 렌더링으로 확인
    + 조각 색을 단색으로만 채운 상태에서 형태가 읽혀야 통과

### 3단계 (선)

- 외곽선은 `painting.outline`, 개별 선은 `painting.stroke` 사용
    + 선 굵기는 빛 반대쪽이 굵고 끝이 가늘어지게 설정
- 선을 생략할 곳을 정함
    + 밝은 면의 경계와 내부 주름은 생략하거나 가늘게 처리

### 4단계 (채색)

- 밑색, 형태 음영, 드리운 그림자, 하이라이트 순서로 적용
    + 형태 음영은 `styles.shade_form`, 드리운 그림자는 `shading.cast_shadow`
- 그림자색은 밑색에 보라 기운의 곱하기 색을 적용
    + `color.shadow_of`가 기본 제공, 피부는 붉은 기운 유지

### 5단계 (후보정)

- `styles.finish(painting, style)` 1회 호출
    + 애니메풍은 확산광과 입자, 일러스트풍은 블룸과 종이 질감, 회화풍은 붓질 재도장
- 회화풍은 `importance` 마스크로 얼굴 등 정밀 영역 지정

### 6단계 (검증)

- 렌더링한 PNG를 직접 열어 확인 후 결함을 수정
    + 최소 2회 반복, 얼굴 등 핵심부는 확대 크롭으로 추가 확인
- 점검 항목은 실루엣, 비례, 조각 겹침 순서, 빛 방향 일관성, 명도 3단 분리, 선 굵기 변화, 화면 가장자리 잘림
- 이미지를 볼 수 없는 환경이면 그 사실을 사용자에게 알리고 `fx.stage_sheet` 결과를 함께 전달

## 빠른 시작

### 인물 흉상

```python
import sys; sys.path.insert(0, "<스킬 폴더>/scripts")
from codepainter import Painting, backdrop
from codepainter.figure import PortraitSpec, draw_portrait
from codepainter.styles import finish, get_style

style = get_style("illust")                       # anime | illust | painterly
painting = Painting(1024, 1280)
backdrop.gradient(painting, "#6b9a97", "#2c4a52")
spec = PortraitSpec(yaw=-0.7, jaw=0.85, hair_style="long", bangs="swept", outfit="turtleneck",
                    hair="#4a353b", eye="#8a6a3c", cloth="#d2a24c")
masks = draw_portrait(painting, spec, style)
painting.save("portrait.png", finish(painting, style, importance=masks["head"]))
```

### 자유 주제

```python
from codepainter import Painting, geometry as geo, shading as sh
from codepainter.styles import finish, get_style, paint_part

style = get_style("anime")
painting = Painting(1024, 1024, "#cfe3ea")
apple = geo.smooth([(330, 520), (380, 330), (520, 300), (680, 350), (720, 540), (620, 730), (420, 720)], closed=True)
mask = paint_part(painting, apple, "#c8323c", style, line_width=4)          # 밑색, 음영, 외곽선
painting.fill(sh.rim(mask, (-0.6, -0.7), 26, 6), "#ffd9d0", 0.6)             # 빛 받는 쪽 하이라이트
leaf = geo.lock((520, 310), (540, 300), (650, 210), bend=-0.2, belly=0.5)    # 끝이 뾰족한 잎
paint_part(painting, leaf, "#4f8a3c", style, line_width=3)
painting.save("apple.png", finish(painting, style))
```

### 전신

```python
from codepainter.figure import PortraitSpec, BodySpec, draw_figure, wardrobe
from codepainter.figure.body import make_pose

style = get_style("illust")
painting = Painting(1024, 1536, "#6f5a48")
pose = make_pose("hand_on_hip", root=(0.50, 0.475), unit=0.105)       # stand, contrapposto, arms_up, walk, stance, back 등
masks = draw_figure(painting, PortraitSpec(yaw=-0.55, cloth="#1f2430"), BodySpec(), pose, style,
                    dress=wardrobe.bodycon)                           # dress=None은 인체 습작
painting.save("figure.png", finish(painting, style, importance=masks["head"]))
```

- 남성은 `BodySpec()` 자리에 `body.MALE_BODY`, 얼굴은 `PortraitSpec(**frame.MASCULINE, ...)`
- 인물마다 다른 사람으로 보이게 하려면 인상 프리셋(`frame.FACES`), 머리 8종, 색 팔레트(`palette.look`)를 조합
    + `PortraitSpec(**{**FACES["cool"], **look("tan", "black", "gray"), "hair_style": "ponytail"})`
    + 표정(`expression`), 안경, 귀걸이, 수염 자국도 같은 사양에서 지정 (`references/figure-rig.md`)
- 몸 돌림은 `make_pose(..., yaw=45)` (3/4), `yaw=90` (측면), 측면 걸음은 `make_pose("walk_side")`
- 의상은 `wardrobe.WARDROBE["lingerie" | "crop_top_shorts" | "hoodie" | "suit" ...]`
- 앉기는 `sit`, `sit_side`, `sit_front`, 무릎은 `kneel`, `seiza`, 눕기는 `lie_back`, `lie_side` (가구는 `props.chair`, `props.bed`)

### 투샷과 장면

```python
from codepainter import fx, sets
from codepainter.figure.body import MALE_BODY
from codepainter.figure.frame import MASCULINE
from codepainter.figure.stage import Actor, draw_actors, floor_shadows, frame, reach

painting = Painting(1536, 1024)
info = sets.SETS["beach"](painting, style)                                      # beach | bedroom | office | night_street | cafe | park
her = Actor(PortraitSpec(cloth="#e0455a"), BodySpec(), make_pose("contrapposto", yaw=20), wardrobe.WARDROBE["bikini"])
him = Actor(PortraitSpec(**MASCULINE), MALE_BODY, make_pose("stance", yaw=-25), wardrobe.WARDROBE["trunks"], depth=-0.3)
her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "full", centers=(0.40, 0.62))
him.pose = reach(him.pose, him.body, "l", (760, 560), painting.shape, depth=0.5)   # 손을 캔버스 한 점으로
figures = draw_actors(painting, [her, him], style)                             # 먼 인물부터, 서로 그림자
sets.light_figures(painting, figures, info, style)
floor_shadows(painting, [her, him], style, color=info.ground)
painting.save("couple.png", fx.grade(finish(painting, style), **info.grade))
```

- 완성 예제는 `python scripts/examples/scene.py --scene office --style illust --out office.png`

### 두머 무드 (서명 화풍)

차가운 콘크리트 세계 속 따뜻한 불빛 하나. 흐린 하늘, 패널 아파트, 겨울, 나트륨 가로등이 공통 요소다.

```python
from codepainter import fx, scenery, sets
from codepainter.figure.frame import FACES
from codepainter.figure.palette import look

painting = Painting(1024, 1536)
info = sets.SETS["panel_block"](painting, style, lamp=0.86)                     # 흐린 단지 마당, 가로등은 오른쪽
spec = PortraitSpec(**{**FACES["sharp_man"], **look("light", "black", "gray", "doomer"), "hat": "beanie", "expression": "sad"})
actor = Actor(spec, MALE_BODY, make_pose("stance", yaw=-22, head_tilt=7), wardrobe.WARDROBE["hoodie"])
(actor.pose,) = frame([(actor.pose, actor.body)], painting.shape, "waist", centers=(0.40,))
figures = draw_actors(painting, [actor], style)
sets.light_figures(painting, figures, info, style)
scenery.snowfall(painting, 1400, keep_clear=actor.masks["head"])                # 얼굴 위 눈송이는 걷어냄
painting.save("doomer.png", fx.doomer(finish(painting, style)))                 # 탈색, 따뜻한 빛만 색 유지
```

- 남성, 여성, 투샷, 설정샷, 도시, 풍경, 사물 7컷 완성 예제는 `python scripts/examples/doomer.py --cut all --out-dir doomer`
- 무드 규칙과 부품은 `references/style-recipes.md`의 두머 무드 참조

### 상자형 사물

```python
from codepainter import objects

desk = geo.Oblique(origin=(120, 820))                                 # (가로, 뒤쪽, 높이) 좌표를 화면에 배치
faces = desk.box(200, 100, 0, 300, 200, 40)                           # 윗면, 앞면, 옆면 사각형
objects.paint_box(painting, faces, "#b9bfc8", style)
screen = geo.quad_map(faces["top"])                                   # 면 위에 0-1 좌표로 세부 배치
painting.fill(painting.mask(screen(geo.rounded_rect(0.1, 0.1, 0.9, 0.9, 0.05))), "#18203a")
```

## 레퍼런스

| 파일 | 내용 | 읽는 시점 |
|---|---|---|
| `references/drawing-process.md` | 단계별 기법, 결함과 수정법 | 모든 작업 시작 전 |
| `references/engine-api.md` | 엔진 함수 전체 목록 | 자유 주제 구성 시 |
| `references/figure-rig.md` | 흉상 리그 매개변수, 인상 프리셋, 표정, 헤어 8종, 색 팔레트, 소품(안경, 귀걸이, 수염, 비니) | 얼굴, 머리, 색 작업 시 |
| `references/figure-body.md` | 포즈 프리셋, 3/4와 측면, 여성과 남성 체형, 의상, 인체 습작, 뒷모습, 손 | 전신과 손 작업 시 |
| `references/clothing-and-scenes.md` | 겹옷과 소매, 앉기와 눕기, 가구, 구도 프리셋, 손 뻗기, 투샷, 장면 배경 | 의상 조합, 자세, 여러 인물 작업 시 |
| `references/subject-recipes.md` | 정물, 현대 사물, 도시, 풍경, 동물 구성법과 예제 목록 | 리그 없는 주제 작업 시 |
| `references/style-recipes.md` | 화풍 수치 의미, 조정법, 신규 화풍 정의, 두머 무드 | 화풍 조정, 두머 무드 작업 시 |

## 범위

- 인물은 정면, 3/4, 측면(90도), 뒷모습, 앉기, 무릎 꿇기, 눕기까지 지원
    + 등 쪽 3/4, 엎드리기, 다리 꼬기, 물건을 쥔 손, 서로 감싸 안는 접촉은 직접 구성해야 하며 검증 반복 증가
- 여러 인물은 정사영 위에서 그리는 순서, 그림자, 손 덮어쓰기로 겹침 표현
- 리그는 생식기 형태를 그리지 않음
    + 남성 정면 맨몸은 가랑이가 매끈한 마네킹처럼 보이므로 짧은 하의(`wardrobe.trunks`)가 자연스러움
- 목표 품질은 정돈된 일러스트 수준
    + 사진 수준의 사실 묘사는 대상 외

## 금지

- 미성년자의 누드와 성적 묘사(성행위 포함)는 그리지 않음
    + 대상 : 이차성징 이전의 신체로 묘사된 인물, 18세 미만으로 명시된 인물
    + 판정 근거는 명시된 나이와 신체 묘사이며 동안 얼굴, 작은 키, 애니메 화풍의 얼굴 비율만으로는 미성년으로 판정하지 않음
