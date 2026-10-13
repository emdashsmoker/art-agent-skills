---
name: flat-painterly
description: 관절 인형과 투시 상자로 세운 무대 장면에 애니메풍, 유화풍, 수채화풍, 일러스트풍 붓질을 입히는 코드 회화 스킬. 확산 모델이나 이미지 생성 API 없이 Python 코드(numpy, OpenCV)만으로 그린다. 같은 시드로 다시 그리면 픽셀까지 같은 그림이 나온다. 인물은 3D 관절 리그가 정면부터 뒷모습까지의 각도와 자세를 잡는다. 얼굴형, 머리 모양, 머리색, 의상은 템플릿에서 고른다. 두 사람이 손을 맞잡는 장면은 무대 도구가 팔의 관통을 점검한다. 도시, 실내, 현대 사물은 소실점 투시와 입체 도구가 세운다. 광원 하나, 빛 테두리, 블룸과 그레인 마감이 조용한 정지 화면 같은 인상을 낸다. 그리는 대상은 인물화, 캐릭터 턴어라운드, 투샷, 풍경화, 도시 풍경, 정물화, 배경 설정샷이다. 엔진의 함수와 인자는 references/api.md에 있다. 구도, 명암, 색과 검수 기준은 references/craft.md에 있다. 화풍별 작업법은 references/style-anime.md, style-oil.md, style-watercolor.md, style-illustration.md에 있다. 인물, 얼굴과 머리 템플릿, 의상, 투샷은 references/figure.md에 있다. 풍경, 도시, 정물, 현대 사물은 references/subjects.md에 있다. 분위기 프리셋은 references/mood-doomer.md에 있다. 사용자가 "코드로 그림 그려줘", "확산 모델 없이 애니메풍 그림", "코드 기반 일러스트" 같은 요청을 하면 이 스킬을 사용한다. 이미지 생성 모델을 쓸 수 없는 환경에서 삽화, 배경화, 포스터 그림이 필요할 때도 사용한다. 차트, 다이어그램, UI 목업, 사진 보정에는 사용하지 않는다.
license: GPL-3.0-or-later with an output exception. See NOTICE.md and LICENSE.
---

# flat-painterly

코드만으로 그림을 그리는 스킬. 확산 모델, 이미지 생성 API, 기존 이미지 합성을 사용하지 않는다.

## 원리

- 그림은 의미(무엇을 어디에 그릴지)와 양식(어떤 재료의 흔적으로 보일지)으로 나뉨
    + 의미는 작업자가 도형의 좌표와 색으로 직접 설계
    + 양식은 `codepaint` 엔진의 화풍 패스가 알고리즘으로 생성
- 좌표를 보지 않고 적으면 비례와 위치가 어긋남
    + 단계마다 렌더한 이미지를 직접 열어 보고 고치는 반복이 품질을 결정
    + 이미지를 볼 수 없는 환경이면 작업 전에 사용자에게 알리고 진행 여부를 확인

## 준비

- 의존성은 numpy와 opencv-python(또는 opencv-python-headless) 2종
- 작업 시작 시 자가 점검을 1회 실행

```bash
python <skill>/scripts/selftest.py   # 통과 시 OK 출력, 누락 패키지는 설치 명령을 안내
```

- 장면 코드는 사용자 작업 폴더에 `scene.py`로 작성하고 엔진을 경로로 불러옴

```python
import sys
sys.path.insert(0, "<skill>/scripts")
from codepaint import Blend, Canvas, Linear, Perspective, Radial, character, color, figure, figure3d, garment, head3d, io
from codepaint import motifs, post, props
from codepaint.stage import Stage
from codepaint import solids as s3
from codepaint import geometry as g
from codepaint.styles import anime, oil, watercolor, illustration
```

## 작화 공정

각 단계는 산출물 1개와 통과 조건 1개를 가짐. 통과 조건을 만족하지 못하면 다음 단계로 넘어가지 않음.

### 1단계 기획

- 산출물은 출력 폴더의 `brief.md`
    + 주제 1문장, 화풍, 초점 1곳, 캔버스 크기, 큰 덩어리 3-5개의 배치, 광원 방향
    + 명암 계획: 밝은 무리, 중간 무리, 어두운 무리에 각각 무엇이 속하는지
    + 팔레트 5-7색과 색마다의 역할(지배색, 보조색, 강조색, 그림자색 등)
- 통과 조건은 초점이 1곳으로 정해지고 모든 색에 역할이 적힌 상태
- 작성 형식은 `examples/brief_example.md` 참고
- 사용자가 화풍을 지정하지 않았으면 아래 화풍 선택 표로 1개를 골라 근거와 함께 알림

### 2단계 구도 러프

- 큰 덩어리만 평면 색으로 배치한 장면을 `scale=0.5`로 렌더
- 산출물은 `canvas.guide_image()`로 저장한 좌표 격자 이미지
- 통과 조건은 세부 없이 실루엣과 명암 무리만으로 주제와 초점이 읽히는 상태

### 3단계 형태

- 덩어리를 부품으로 나누고 부품 묶음을 1개 추가할 때마다 렌더해서 확인
- 인물은 `figure.Figure`(정면, 뒷면) 또는 `figure3d.Figure3D`(3/4, 옆모습, 앞뒤로 흔든 팔다리)로 자세부터 잡고 마네킹을 렌더해서 확인
    + 옷 입은 인물과 두 사람 장면은 `character.place`, `garment`의 옷 한 벌, `Stage`의 reach로 만들고 `character.paint_figure`로 칠함
    + 두 사람 장면은 칠하기 전에 `stage.collisions(models)`로 팔이 상대 몸을 뚫는지 확인. 보이는 자리의 관통은 칠하는 순서와 무관하게 팔이 잘려 보임
- 깊이 방향으로 뻗는 거리는 `Perspective`로 건물 상자를 투영
- 사물과 실내 가구는 `solids`의 상자, 둥근 판, 기둥을 카메라로 투영
- 그 밖에 비례가 중요한 대상(얼굴, 동물, 기물)은 `g.Frame` 단위 좌표로 설계
- 통과 조건은 격자 이미지에서 비례 오류, 부품 사이 틈, 의도하지 않은 겹침이 없는 상태

### 4단계 채색과 선

- 화풍별 참조 문서의 순서를 따름
    + 애니메풍은 부품마다 밑색, 그림자, 윤곽선을 함께 처리
    + 유화풍은 매끈한 밑그림과 붓질 방향 지정
    + 수채화풍은 밝은 색에서 어두운 색 순서의 겹칠
    + 일러스트풍은 평면 색면과 점묘 명암
- 통과 조건은 기획의 명암 계획과 실제 렌더의 밝기 배치가 일치하는 상태

### 5단계 화풍 패스

- 화풍에 맞는 패스 함수를 1회 적용
- 통과 조건은 초점부를 확대한 이미지에서 재료의 흔적(붓결, 번짐, 입자, 빛 번짐)이 보이고 형태가 뭉개지지 않은 상태

### 6단계 후보정

- `post` 모듈로 색 보정, 비네트, 입자를 필요한 만큼만 적용
- 통과 조건은 가장 밝은 곳과 가장 어두운 곳의 세부가 날아가지 않은 상태

### 7단계 검수

- 전체 이미지 1장과 초점부 확대 이미지 1장 이상을 직접 확인
- `references/craft.md`의 검수 목록으로 결함을 찾고 영향이 큰 순서로 3개까지 고친 뒤 다시 렌더
- 검수와 수정은 3회까지 반복하고 남은 약점은 사용자에게 그대로 보고
- 최종본은 `scale` 1.25 이상으로 렌더하고 장면 코드와 함께 전달

## 장면 코드 작성 규칙

- 좌표는 SVG와 같은 논리 좌표(왼쪽 위 원점, y 아래 방향)
    + 해상도는 `Canvas(width, height, scale=...)`의 scale로만 조절
    + 초안은 0.5, 확인용은 0.75-1.0, 최종본은 1.25-1.5
- 그리는 순서는 뒤에서 앞으로
- 팔레트는 파일 상단에 이름 있는 상수로 선언하고 본문에 색 코드를 직접 적지 않음
- 단계 또는 부품마다 함수 1개로 나눠 일부만 고쳐도 전체가 재현되게 구성
- 난수는 시드를 고정한 `np.random.default_rng(seed)` 또는 `canvas.rng`만 사용
- 곡선은 통과점만 적는 `g.spline(points, corners=...)`을 기본으로 사용
    + 뾰족한 끝(머리카락, 잎, 옷깃)은 그 점의 인덱스를 corners에 지정
- 부품 안쪽에만 그릴 그림자나 무늬는 `clip=부모형태`로 제한

가장 자주 쓰는 호출:

```python
cv = Canvas(1600, 900, scale=0.5, seed=7)
part = cv.shape(g.spline([(x, y), ...], corners=(2,)))       # 경로를 형태로
cv.fill(part, "#e05030")                                       # 칠
cv.fill(cv.form_shadow(part, light=(-0.6, -0.8), amount=0.4), "#902030")  # 자동 그림자
cv.fill(other, Linear(["#1b5fc4", "#e3f3fc"], (0, 0), (0, 900)), clip=part)
cv.stroke(g.spline(points, closed=False), "#301018", width=3, taper=(0, 1, 0))
io.save(cv.guide_image(), "out/stage.png")                     # 격자와 함께 저장해서 확인
```

완성 이미지의 위치 확인과 확대는 장면 코드 수정 없이 도구로 수행:

```bash
python <skill>/scripts/inspect_image.py out/final.png --width 1600 --grid 100
python <skill>/scripts/inspect_image.py out/final.png --width 1600 --crop 800 150 1360 700 --zoom 2
```

## 화풍 선택

| 화풍 | 어울리는 주제 | 핵심 도구 | 참조 문서 | 예제 |
|---|---|---|---|---|
| 애니메풍 | 인물, 캐릭터, 하늘, 실내와 사물, 배경 설정샷 | `anime.cel`, `anime.rim_light`, `anime.finish` | `references/style-anime.md` | `anime_sky_pilot.py`, `anime_night_desk.py`, `anime_city_window.py`, `anime_figure_base.py`, `anime_figure_base_male.py`, `anime_morning_light.py`, `anime_turnaround.py`, `anime_outfit_sheet.py`, `anime_cafe_talk.py`, `anime_doomer_bus_stop.py`, `anime_doomer_courtyard.py`, `anime_face_templates.py`, `anime_hair_templates.py`, `anime_hair_colors.py`, `anime_long_hair_platform.py`, `anime_long_hair_window.py`, `anime_long_hair_walk.py` |
| 유화풍 | 풍경, 인체화, 빛이 강한 장면 | `canvas.direct`, `oil.render` | `references/style-oil.md` | `oil_harbor_sunset.py`, `oil_summer_fields.py`, `oil_figure_study.py`, `oil_reclining_figure.py`, `oil_evening_dance.py`, `oil_doomer_overpass.py`, `oil_doomer_pylons.py` |
| 수채화풍 | 동식물, 정물, 거리 스케치, 여백이 있는 그림 | `watercolor.wash`, `watercolor.render` | `references/style-watercolor.md` | `watercolor_robin.py`, `watercolor_still_life.py`, `watercolor_old_town.py`, `watercolor_hand_studies.py`, `watercolor_gadget_studies.py`, `watercolor_street_walk.py`, `watercolor_doomer_block.py`, `watercolor_doomer_kitchen.py` |
| 일러스트풍 | 포스터, 그림책, 도형적 풍경과 인물 | `fill(grain=1.0)`, `illustration.render` | `references/style-illustration.md` | `illustration_moonlit_camp.py`, `illustration_autumn_walk.py`, `illustration_fantasy_walk.py`, `illustration_doomer_rooftop.py` |

- 예제는 모두 `examples/` 폴더에 있음
- 화풍이 정해지면 해당 참조 문서 1개와 주제가 가장 가까운 예제 1개를 먼저 읽음
    + 예제는 공정 전체를 따라간 장면 코드이며 부품 설계 방식을 그대로 응용 가능
- 한 그림에 두 화풍의 도구를 섞어도 됨(애니메 인물 뒤에 유화 배경 등)

## 주제별 도구

| 주제 | 핵심 도구 | 참조 문서 | 예제 |
|---|---|---|---|
| 인물(흉상, 전신) | `figure.Figure`로 자세, 부위 윤곽, 표지 좌표 | `references/figure.md` | `anime_sky_pilot.py`, `illustration_autumn_walk.py`, `anime_morning_light.py` |
| 인물의 각도와 자세 | `figure3d.Figure3D`(몸), `head3d.Head3D`(얼굴, 머리카락) | `references/figure.md` | `anime_turnaround.py`(남녀 다섯 각도 턴어라운드, 앉기, 걷기, 돌아보기) |
| 얼굴과 머리 템플릿 | `character.restyle`, `faces`(얼굴 6종), `hairstyles`(머리 8종, 머리색 12종, 긴 머리 드레이프) | `references/figure.md` | `anime_face_templates.py`, `anime_hair_templates.py`, `anime_hair_colors.py`, 긴 머리 장면 `anime_long_hair_platform.py`, `anime_long_hair_window.py`, `anime_long_hair_walk.py` |
| 의상 | `garment`의 옷 한 벌(일상복, 정장, 외투, 판타지), `character.paint_figure` | `references/figure.md` | `anime_outfit_sheet.py` |
| 두 사람 장면(투샷) | `Stage`(같은 시선, reach와 fists로 손 맞추기, poles로 팔꿈치 방향, palm_out으로 맞잡은 손, collisions로 관통 점검, 소품 투영), `paint_figure(defer=...)` | `references/figure.md` | `anime_cafe_talk.py`(카페), `watercolor_street_walk.py`(손잡고 걸어오기), `illustration_fantasy_walk.py`(손잡고 걷기), `oil_evening_dance.py`(춤) |
| 손 | `figure.hand_open`, `figure.hand_side` | `references/figure.md` | `watercolor_hand_studies.py` |
| 인체 습작(성인) | `figure.Figure`, 성인 얼굴 표지, 하반신 표지 | `references/figure.md` | `anime_figure_base.py`(여성 전신 베이스), `anime_figure_base_male.py`(남성 전신 베이스), `anime_turnaround.py`(남녀 턴어라운드와 포즈), `oil_figure_study.py`, `oil_reclining_figure.py`, `anime_city_window.py` |
| 풍경 | `motifs.cumulus`, `ridge`, `canopy`, `grass` | `references/subjects.md` | `oil_summer_fields.py`, `oil_harbor_sunset.py` |
| 도시, 실내 | `Perspective` | `references/subjects.md` | `watercolor_old_town.py` |
| 정물 | `form_shadow`, `form_light`, 형태 뺄셈 | `references/subjects.md` | `watercolor_still_life.py` |
| 현대 사물 | `solids`, `props` | `references/subjects.md` | `anime_night_desk.py`, `watercolor_gadget_studies.py` |
| 두머 분위기(패널 아파트 단지, 나트륨 가로등, 겨울 저녁) | 공통 팔레트와 광원 1곳, `Perspective`와 `solids`의 동, 화풍별 처방 | `references/mood-doomer.md` | 남성 `anime_doomer_bus_stop.py`, 여성 `oil_doomer_overpass.py`, 투샷 `illustration_doomer_rooftop.py`, 설정샷 `anime_doomer_courtyard.py`, 도시 `watercolor_doomer_block.py`, 풍경 `oil_doomer_pylons.py`, 사물 `watercolor_doomer_kitchen.py` |

- 주제가 정해지면 해당 참조 문서를 화풍 문서와 함께 읽음

## 참조 문서

- `references/api.md`: 엔진의 모든 함수와 인자. 장면 코드를 쓰기 전에 읽음
- `references/craft.md`: 화풍과 무관한 작화 원칙(구도, 명암, 색, 형태)과 검수 목록. 기획과 검수 단계에서 읽음
- `references/style-*.md`: 화풍별 작업 순서, 패스 인자 조절법, 흔한 결함과 처방
- `references/figure.md`: 인체 리그의 자세 지정, 검증된 자세 값, 몸의 표지 좌표, 하반신 표지, 손, 인체 습작, 3차원 리그와 각도별 머리, 얼굴과 머리 템플릿, 의상, 투샷과 무대
- `references/subjects.md`: 풍경, 도시, 정물, 현대 사물의 작업법과 투시, 입체 도구
- `references/mood-doomer.md`: 두머 분위기의 색, 빛, 소재, 구도, 화풍별 처방, 후보정 값. 화풍 문서와 함께 읽음

## 한계

- 3차원 리그는 몸 전체의 회전, 상체 숙임, 팔다리의 앞뒤 흔들기, 머리만 돌리기를 다룸
    + 투영은 원근이 없는 정사영. 화면 쪽으로 크게 뻗은 손발이 커 보이는 원근 과장은 표현하지 않음
    + 허리를 크게 비튼 자세(골반과 가슴이 서로 다른 방향을 보는 자세), 눕기, 물구나무는 검증하지 않음
    + 손이 목표 지점에 닿는 자세는 `Stage`의 reach(손목)와 fists(주먹 가운데)가 두 뼈 역운동학으로 맞춤. 팔꿈치 방향은 poles로 정하며 다리의 역운동학은 없음
    + 머리카락은 단발, 중단발, 긴 생머리, 묶은 머리, 남성 머리 4종을 검증함. 긴 다발은 drape로 몸통을 피하지만 팔과 소품은 피하지 않음
- 옷은 몸통 단면을 부풀린 덩어리와 정해 둔 주름 선
    + 천의 물리 계산이 없어 앉은 자세의 치마, 바람에 크게 펄럭이는 천은 다루지 않음
- 두 사람 장면은 칠하는 순서와 미룬 덩어리로 앞뒤를 정함
    + 앞뒤는 덩어리(팔 하나) 단위라서 위팔은 상대 뒤, 아래팔은 상대 앞인 엇갈림은 표현하지 못함
    + 관찰자 쪽으로 굽힌 아래팔은 소매가 위팔과 한 덩어리로 칠해져 팔꿈치의 겹침이 드러나지 않음. 두 사람이 함께 드는 물건(우산 등)은 팔이 앞으로 굽어 어색해지므로 내린 팔로 손을 맞잡는 자세가 안정적
    + 서로 끌어안기처럼 두 몸이 깊게 엇갈리는 자세는 검증하지 않음
    + `stage.collisions`는 팔 대 상대 몸통, 팔 대 상대 팔만 점검함. 다리, 옷, 손의 관통은 렌더를 보고 확인
    + 무대는 정사영이라 깊이에 따른 크기 변화가 없음. 깊은 배경은 `Perspective`로 따로 그림
- 손은 머리 높이의 4분의 3 크기까지는 그럴듯하게 읽히고 화면을 채우는 확대에서는 마디가 단순해 보임
- 인물의 얼굴과 살은 양식화된 회화 수준이며 사진 같은 사실 묘사와 글자 렌더링은 범위 밖
- 인체 습작과 매력 연출은 성인 표지를 모두 갖춘 인물의 인체화로 한정
    + 화풍은 가리지 않으며 성인 표지 목록은 `references/figure.md`
    + 전신 베이스 예제는 여성과 남성 모두 하반신까지 가리지 않고 그리며 골반 앞쪽은 고전 조각과 해부도 수준의 둥근 면으로 표현
    + 미성년으로 보일 여지가 있는 인물에는 적용하지 않음
- 입체 도구는 상자, 둥근 판, 기둥의 조합만 다룸
    + 게임 패드, 자동차처럼 자유 곡면이 많은 사물은 2D 윤곽으로 보완해야 함
- 실존 인물의 초상, 기존 작품의 캐릭터, 특정 작가 그림의 모사는 하지 않고 화풍의 일반 기법만 사용
