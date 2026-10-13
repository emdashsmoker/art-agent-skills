---
name: soft-diorama
description: 이미지 생성 모델 없이 Python 코드만으로 그림(PNG)을 빚는 스킬. 굵기가 변하는 띠로 선과 머리카락을 긋는다. 초승달 그림자로 셀 음영을 넣는다. 말랑한 부피 음영으로 몸과 사물을 부풀린다. 장면은 뒤에서 앞으로 레이어를 쌓아 만든다. 결과물은 매끈한 인형 같은 인물이 단순한 기하 소품 사이에 놓인 작은 무대 세트의 맛을 낸다. 장면마다 조용히 멈춘 한순간을 담는다. 애니메, 일러스트, 수채, 유화 마감으로 같은 장면의 결을 바꾼다. 인물은 360도 회전하는 성인 전신 리그와 상반신 리그로 그린다. 서기, 걷기, 뛰기, 앉기, 눕기 포즈, 투샷과 그룹샷 배치, 헤어 24종, 표정 8종, 일상복부터 겨울 외투까지 지원한다. 정물, 현대 사물, 풍경, 원근 도시, 겨울밤 도시 무드 프리셋도 그린다. 참조 문서는 references 폴더의 primitives.md(도형, 띠, 음영 기초), api.md(엔진 함수), styles.md(화풍별 마감과 문제 해결), figure.md(얼굴, 머리카락, 상반신), fullbody.md(전신, 포즈, 의상, 헤어, 표정, 배치), objects.md(정물과 현대 사물), city.md(1점과 2점 투시 도시), doomer.md(겨울밤 도시 무드 프리셋)다. 사용자가 그림, 일러스트, 캐릭터, 전신, 투샷, 단체 구도, 헤어스타일, 표정, 풍경화, 정물화, 도시 풍경, 애니메풍, 수채화풍, 유화풍, 코드로 그림, draw, illustration, painting을 요청하거나 이미지 생성 모델 없이 그림이 필요하면 이 스킬을 사용한다. 차트, 다이어그램, UI 목업, 로고는 대상이 아니다.
license: GPL-3.0-or-later with an exception for generated images (see NOTICE.md)
---

# soft-diorama

코드로 그림을 그리는 스킬. 작화 절차를 함수 호출로 옮기고 렌더 결과를 눈으로 확인하며 다듬는다.

## 원리

- 모든 도형은 0-1 실수 마스크 1장
    + 교집합은 `a*b`, 합집합은 `np.maximum(a,b)`, 차집합은 `a*(1-b)`
    + 그림자, 역광, 하이라이트는 마스크를 옮기고 흐리고 빼서 만든다
- 기본 도형은 2종
    + `blob`: 제어점을 지나는 닫힌 면
    + `ribbon`: 중심선과 폭 프로파일로 만드는 띠 (펜 선, 머리카락 가닥, 꽃잎, 잎)
- 화면은 색 레이어 1장과 선 레이어 1장
    + `fill`은 새 물체를 칠하고 그 밑의 선을 지운다. 뒤에서 앞 순서로 그리면 가림이 자동 처리된다
    + `tint`는 이미 칠한 색을 바꾼다 (그림자, 빛, 그라데이션)
    + `ink`와 `outline`은 선 레이어에 그린다. 마감 단계가 색과 선을 따로 가공한다
- 형태는 작성자가 정하고 빛과 질감은 엔진이 만든다
    + 인물은 리그(`paintkit.figure`)가 비례를 잡아준다: 상반신, 전신, 손
    + 도시는 평면으로 그린 면을 원근 카메라(`paintkit.city`)로 붙인다
    + 현대 사물은 상자와 원통(`paintkit.solids`)을 같은 카메라로 놓고 화면, 자판을 평면으로 그려 붙인다
    + 카메라는 정면 1점 투시(`city.Perspective`)와 돌리고 기울이는 2점, 3점 투시(`city.Camera`) 두 가지
    + 그 외 대상은 부위별 마스크를 직접 설계한다
- 음영은 2종
    + `paint_form`: 경계가 분명한 셀 음영 (애니메)
    + `paint_volume`: 그림자에서 빛까지 연속으로 이어지는 둥근 음영 (일러스트, 회화, 살결, 정물)

## 준비

```bash
pip install -r <skill>/scripts/requirements.txt   # numpy, opencv-python
python <skill>/scripts/selftest.py                 # "all passed" 확인
```

- 의존성 설치와 selftest 통과를 가장 먼저 수행한다. 실패하면 그 원인부터 해결한다
- 확산 모델, 이미지 생성 API, 외부 이미지 다운로드는 사용하지 않는다

## 작업 절차

각 단계는 확인 가능한 산출물을 남긴다. 단계를 건너뛰면 뒤에서 더 큰 수정이 생긴다.

### 1. 기획

장면 스크립트 상단 주석 또는 짧은 메모로 아래 6개를 확정한다.

| 항목 | 정할 내용 |
|---|---|
| 주제 | 무엇을 그리는가. 인물이면 표정, 머리 모양, 옷 |
| 구도 | 캔버스 크기, 주인공의 위치와 크기, 시선 방향, 여백 |
| 화풍 | 아래 화풍표에서 1개 |
| 광원 | 빛의 방향 1개 (`light=(x, y)`, 표면에서 광원을 향하는 벡터, y는 아래가 양수) |
| 팔레트 | 주조색 1, 보조색 1-2, 강조색 1을 hex로. 배경과 인물의 명도 차이를 확보 |
| 레이어 순서 | 뒤에서 앞으로 그릴 순서 |

- 사용자가 인물의 연령대나 복장을 지정하지 않으면 성인 인물과 일상복을 기본값으로 한다
- 사용자가 지정한 요소는 그대로 따르고 지정하지 않은 요소만 스스로 정한다

### 2. 장면 스크립트 작성

- `scripts/examples/`에서 가장 가까운 예제를 복사해 출발한다
    + 상반신 인물: `anime_portrait.py`, `illustration_portrait.py`, `watercolor_portrait.py`, `oil_portrait.py`
    + 전신 인물: `city_night_walk.py` (의상 + 도시 배경), `figure_nude_study.py` (인체화, 여성과 남성), `couple_bench.py` (앉은 남녀, 3/4 각도, `skirt` 인자로 앉은 치마), `figure_turnaround.py` (정면부터 뒷모습까지 8방향 턴어라운드), `figure_back_view.py` (뒤돌아선 인물과 노을 도시)
    + 의상과 상황: `beach_bikini.py` (해변 비키니, 3분할), `bedroom_lingerie.py` (침실 란제리, 눕기), `hoodie_street.py` (가을 거리 후드티, 캥거루 주머니에 손), `summer_street.py` (여름 거리 크롭티와 핫팬츠, 걷기), `office_suits.py` (사무실 양복 두 명, `group`)
    + 전신에서 잘라낸 클로즈업: `figure_zoom.py` (전신, 허리 위, 상반신, 얼굴)
    + 손: `hand_study.py`
    + 풍경: `landscape_lake.py` (유화), `landscape_meadow.py` (애니메 배경, 원근 도로)
    + 도시: `city_night_walk.py` (1점 투시 거리), `city_corner.py` (2점 투시 모퉁이), `city_skyline_dusk.py` (강 건너 스카이라인)
    + 정물: `still_life_oil.py` (부피 음영 + 유화), `still_life.py` (수채)
    + 현대 사물: `desk_still_life.py` (컴퓨터 책상, 밤과 낮), `still_life_gadgets.py` (카메라, 헤드폰, 게임 패드)
    + 과정 시트: `process_sheet.py`
    + 연출 (화풍, 인원, 구도, 포즈 조합): `station_platform.py` (애니메, 승강장 투샷, 허벅지 샷), `riverside_run.py` (애니메, 옆모습 달리기, 날리는 포니테일), `park_group.py` (일러스트, 5명 그룹, 서기와 벤치 앉기), `rainy_window.py` (일러스트, 비 오는 창가 상반신 클로즈업, 테두리 빛), `autumn_lake_walk.py` (수채, 호숫가 뒷모습 원경), `picnic.py` (수채, 바닥에 앉은 투샷), `group_portrait_oil.py` (유화, 3인 허리샷 초상, `group(shot='waist')`), `winter_chair_oil.py` (유화, 의자에 앉은 인물)
    + 헤어, 표정, 겨울옷: `hairstyle_catalog.py` (헤어 24종 시트, 여성과 남성), `expression_sheet.py` (표정 8종 x 얼굴 스타일 4종), `winter_outfits.py` (코트, 패딩, 목도리, 비니, 부츠를 입은 네 명, `group`)
    + 두머 무드 프리셋: `doomer_man.py`, `doomer_woman.py`, `doomer_two_shot.py`, `doomer_establishing.py`, `doomer_city.py`, `doomer_landscape.py`, `doomer_still_life.py`. 고정 캐스트는 `doomer_cast.py`
- 배경, 주인공, 전경, 마감 순서로 함수를 나눈다
- 색, 좌표, 시드 같은 설정값은 파일 상단 상수로 둔다
- 난수를 쓰는 모든 호출에 `seed`를 넘겨 재현 가능하게 한다

### 3. 렌더

```bash
python my_scene.py out.png
```

### 4. 검수

렌더한 PNG를 반드시 직접 열어 본다. 코드만 읽고 완료로 판단하지 않는다.

```bash
python <skill>/scripts/inspect_render.py out.png grid.png --grid 100          # 좌표 확인
python <skill>/scripts/inspect_render.py out.png face.png --crop 280,200,780,800 --zoom 2   # 확대
```

점검 항목

- 형태: 얼굴 비례, 좌우 균형, 실루엣이 한눈에 읽히는가
- 가림: 앞 물체가 뒤 물체를 제대로 덮는가, 떠 있는 선이나 빈틈이 없는가
- 명암: 모든 그림자가 같은 광원 방향을 따르는가
- 색: 배경과 주인공이 분리되는가, 하얗게 날아가거나 탁하게 뭉친 곳이 없는가
- 초점: 얼굴처럼 중요한 부위를 확대해서 확인했는가
- 가장자리: 캔버스 경계에서 어색하게 잘리는 곳이 없는가

### 5. 수정 반복

- 발견한 문제를 좌표와 함께 적고 스크립트를 고친 뒤 다시 렌더한다
- 최소 2회 반복한다. 첫 렌더가 그대로 완성인 경우는 드물다
- 증상별 처방은 `references/styles.md`의 문제 해결 표를 본다

### 6. 전달

- 최종 PNG와 장면 스크립트를 함께 전달한다 (스크립트가 있으면 사용자가 수정을 요청하기 쉽다)
- 과정 시트가 필요하면 `scripts/examples/process_sheet.py` 방식으로 선화-밑색-명암-완성 4컷을 만든다

## 화풍표

| 화풍 | 인물 look | 마감 함수 | 특징 |
|---|---|---|---|
| 애니메 | `ANIME` | `finish.finish_anime(cv)` | 단단한 그림자 경계, 짙은 유색 선, 블룸 |
| 일러스트 | `ILLUSTRATION` | `finish.finish_illustration(cv)` | 부드러운 명암, 가는 선, 글로우, 종이결 |
| 수채 | `SKETCH` | `finish.finish_watercolor(cv)` | 연필 선, 옅은 워시, 가장자리 안료 뭉침, 종이 여백 |
| 유화 | `PAINTERLY` | `finish.finish_oil(cv, detail=mask)` | 선 없음, 붓자국 재구성, 임파스토 |
| 두머 (무드 프리셋) | `ILLUSTRATION`, `light_height` 0.45-0.55 | `doomer.finish(cv)` | 낮은 채도의 청회색, 나트륨 주황 한 점, 남색으로 띄운 검정, 거친 입자 (`references/doomer.md`) |

- 마감 함수는 (H, W, 3) 이미지를 돌려준다. `save_image(path, image)`로 저장한다
- 마감 없이 보려면 `cv.save(path)`를 쓴다 (형태 점검 단계에서 빠르다)

## 빠른 시작

```python
import sys
sys.path.insert(0, '<skill>/scripts')

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import ANIME, BodySpec, Character, FaceSpec, HairSpec, Head, Outfit, add_rim_light, draw_character

cv = Canvas(1024, 1280)
scenery.sky(cv, top='#2f74d0', bottom='#cfe9fb')
scenery.cloud_bank(cv, (330, 1180), count=7, size=(300, 760), seed=11)
cv.color = blur(cv.color, 1.6)                      # 배경을 살짝 흐려 인물을 앞으로

character = Character(
    head=Head(center=(530, 500), size=500, yaw=-20, tilt=-5),
    face=FaceSpec(eye_color='#3f8f86', smile=0.5),
    hair=HairSpec(color='#2f3556', bangs='side', part=24, length=3.1),
    body=BodySpec(turn=-8),
    outfit=Outfit(kind='vneck', color='#e9a23b'),
    look=ANIME,
)
masks = draw_character(cv, character)               # 부위별 마스크를 돌려준다
add_rim_light(cv, masks['all'], character.look)
save_image('out.png', finish.finish_anime(cv, seed=11))
```

리그 없이 물체 하나를 그리는 최소 단위

```python
vase = cv.blob([(400, 470), (560, 640), (520, 830), (380, 830), (340, 640)])
cv.paint_form(vase, '#7fb0c4', light=(-0.7, -0.7), shadow=0.22, line_width=2.4, rim=0.5)
```

## 인물 리그의 범위

| 리그 | 호출 | 지원 |
|---|---|---|
| 상반신 | `draw_character` | 고개 회전 ±40도, 앞머리 8종과 없음, 긴 머리와 단발, 웨이브, 묶음머리 6종, 헤어 프리셋 24종, 표정 8종, 옷 5종 |
| 전신 | `draw_figure` | 여성과 남성, 360도 몸 돌리기(정면, 3/4, 옆모습, 뒷모습), 포즈 프리셋 12종(`poses`), 구도 도우미(`fit`, `thirds`, `group`), 관절 각도 포즈, 앉은 자세(`aim`), 체형 조절, 의상 17종, 헤어 24종(`hairstyle`, 묶음머리와 클리퍼 컷 포함), 얼굴 스타일 8종(`face_style`), 표정 8종(`expression`), 인체화(누드), 위에서 본 누운 자세, `framing`으로 상반신과 얼굴 클로즈업 |
| 손 | `draw_hand` | 손등과 손바닥, 포즈 6종 (편 손, 힘 뺀 손, 주먹, 가리킴, 브이, 엄지 척), 손목 축 회전으로 옆에서 본 손 |

- 전신 인물은 성인 8등신 비례로 고정되어 있다
- 상반신 클로즈업도 전신 리그를 `framing(cv.size, 'bust')`로 줌해서 만들 수 있다. 몸을 돌리거나 남성을 그릴 때는 이 방법을 쓴다
- 인체화(누드)는 여성과 남성 모두 그린다. 엔진은 몸의 표면 형태를 그린다. 성기 형태를 그리는 기능은 없다
- 미성년자의 누드와 성행위 묘사는 그리지 않는다
    + 판단 근거는 두 가지다. 미성년자로 명시된 인물(18세 미만 나이 설정, 아동 지정), 이차성징 이전의 몸 묘사(아동 체형과 비례)
- 몸을 90도 넘게 돌리는 포즈는 팔을 `aim(turn, ...)`으로 준다. 몸 기준 방향이라 어느 각도에서도 같은 자세로 보인다
- 몸을 돌리는 그림의 늘어뜨린 손은 `HandSpec('relaxed', 'rest')`를 쓴다. 손이 몸 방향을 따라 비스듬히 돈다
- 주머니에 넣은 손은 `HandSpec('pocket')`(바지 앞주머니)이나 `HandSpec('pouch')`(후드티 캥거루 주머니)를 쓴다. 팔 각도는 리그가 역운동학으로 계산한다. 체형과 몸 각도가 달라도 손목이 주머니에 닿는다
- 미지원: 원근이 강한 단축 포즈, 허리를 앞뒤로 굽힌 자세
    + 미지원 요소는 기본 도형으로 직접 그린다. 반복 횟수가 늘어난다는 점을 사용자에게 알린다
- 안경, 귀걸이, 머리핀, 옷 무늬는 `head.at()`과 돌려받은 마스크로 덧그린다 (`references/figure.md`)
- 단체 초상과 투샷 클로즈업은 `group(..., shot='waist')`로 배치한다. 겹친 줄은 가운데 인물을 마지막에 그린다 (`references/fullbody.md` 15절)
- 인물마다 헤어를 다르게 고른다. 같은 장면의 여러 인물이 같은 머리 모양이면 실루엣이 반복된다 (`hairstyle()`, `references/fullbody.md` 16절)
- 표정은 `expression(face, name)`으로 입힌다. 일자 앞머리는 눈썹 표정을 가리므로 표정이 중요하면 이마가 보이는 헤어를 고른다 (17절)

전신 최소 예시

```python
from paintkit.figure import ILLUSTRATION, Figure, Pose, draw_figure, framing, wardrobe

figure = Figure(pelvis=(500, 760), height=1270, pose=Pose(hip_tilt=7, shoulder_tilt=-5, lean=-3),
                look=ILLUSTRATION, nude_details=False)
masks = draw_figure(cv, figure, garments=[wardrobe.dress('#b0344a', length=2.6), wardrobe.shoes('#3a2020')])

# 3/4 각도의 남성, 허리 위 클로즈업
man = Figure(**framing(cv.size, 'waist'), sex='male', pose=Pose(turn=-30, head_yaw=-24), nude_details=False)
draw_figure(cv, man, garments=[wardrobe.bottoms('#3a3d48'), wardrobe.top('#c9d6e3', sleeve=1.25, scoop=0.25)])
```

## 참조 문서

| 파일 | 읽는 시점 |
|---|---|
| `references/api.md` | 엔진 함수의 인자와 동작을 확인할 때 |
| `references/figure.md` | 인물을 그릴 때. 얼굴, 머리카락, look 매개변수, 인상 조절, 소품 추가 |
| `references/fullbody.md` | 전신, 포즈, 몸 돌리기, 앉은 자세, 남성, 줌, 체형, 의상(겨울 외투 포함), 헤어스타일, 얼굴 스타일과 표정, 인체화, 손을 그릴 때 |
| `references/city.md` | 도시, 거리, 원근이 있는 건물과 바닥, 2점 투시 카메라를 쓸 때 |
| `references/objects.md` | 컴퓨터, 휴대폰, 카메라, 컵 같은 현대 사물과 책상 풍경을 그릴 때 |
| `references/styles.md` | 화풍별 조리법, 조명 연출, 문제 해결 표 |
| `references/doomer.md` | 두머 무드 프리셋으로 그릴 때. 디자인 방향, 팔레트, 소재 함수, 고정 캐스트, 예제 장면 |
| `references/primitives.md` | 리그에 없는 대상을 기본 도형으로 설계할 때 |
