---
name: maquette-painter
description: "화가가 작은 입체 모형(마케트)을 세워 놓고 보며 그리듯, 인물과 사물을 입체로 빚어 원근 카메라 앞에 세우고 빛과 그림자를 계산한 뒤, 그 모형을 셀화, 웹툰, 수채, 과슈, 유화, 수묵, 우키요에, 민화, 파스텔, 인상주의, 겨울밤 변두리를 그레인 낀 사진처럼 담는 두머 등 34개 화풍의 붓으로 칠하는 그림 스킬. 확산모델과 이미지 생성 API 없이 Python 코드만으로 그리며 인물은 관절과 단면으로 세운 작도 인형이라 손가락, 발가락, 이목구비가 흐트러지지 않고 같은 시드면 같은 그림이 나온다. 결과물은 조명 아래 세운 모형을 보고 그린 듯 형태와 명암이 또렷하고 단정하며 고요하다. 모형과 칠이 분리되어 있어 같은 장면을 화풍만 바꿔 셀화로도 유화로도 수묵으로도 다시 칠할 수 있다. 인물화, 투샷, 기모노와 한복, 풍경, 도시 거리, 실내, 정물, 현대 사물, 비와 눈이 내리는 장면, 스톡 아트를 PNG로 산출한다. 사용자가 그림, 일러스트, 초상화, 캐릭터, 풍경화, 정물화, 배경화면, 포스터, 표지 그림, 스톡 이미지를 '그려줘', '만들어줘', '생성해줘'라고 요청하거나 '코드로 그림', '확산모델 없이', 'maquette-painter', 'draw', 'paint', 'illustration'을 언급하면 반드시 이 스킬을 사용할 것. 차트, 다이어그램, UI 목업, 사진 편집 요청에는 사용하지 않는다. 세부 사용법은 references 폴더의 figure.md(인물, 포즈, 손, 머리, 의상, 투샷), scenery-objects.md(풍경, 날씨, 원근, 실내, 도시, 정물, 현대 사물), styles.md(화풍, 조명, 매체 파라미터, 마감), workflow.md(기획 질의, 아트 디렉션, 수정 절차), api.md(Canvas와 geom 저수준 도구), critique.md(검수 항목과 결함 처방)에 있다."
license: GPL-3.0-or-later. Generated images are free to use under the additional permission in NOTICE.md
---

# maquette-painter

코드로 세우는 마케트(작업용 입체 모형). 인물과 사물을 입체로 세워 구조(무엇이 어디에 있는가)를 정하고, 빛을 비춘 뒤, 매체(어떻게 칠하는가)를 입힘.

## 원칙

- 확산모델, 이미지 생성 API, 외부 3D 도구를 호출하지 않음
    + 이 스킬의 존재 이유가 코드 기반 작화이므로 해당 도구 사용은 범위를 벗어남
- 구조를 먼저 확정한 뒤 매체를 입힘
    + 구조 버퍼(밑색, 형태, 음영, 선화, 깊이) 1벌에서 모든 화풍을 렌더하므로 구조 결함은 화풍을 바꿔도 남음
- 렌더 결과를 반드시 눈으로 확인한 뒤 수정함
    + 코드가 오류 없이 실행되어도 그림은 틀릴 수 있음. 이미지 확인이 유일한 검증 수단임
- 인체 정확성은 작도 규칙이 보장함
    + 손가락 5개, 발가락 5개, 관절 비례는 뼈대 정의에서 생성되므로 포즈와 비례 수치만 지정하면 됨
- 누드, 성행위, 성적 암시가 있는 장면에는 미성년자를 그리지 않음
    + 성적 암시는 선정적 포즈, 속옷 차림, 신체 부위를 부각하는 구도를 포함
    + 미성년 여부는 명시된 나이나 학년, 아동 체형 비례, 2차 성징 이전의 몸, 아동임이 분명한 맥락으로 판단
    + 앳된 얼굴, 아니메와 웹툰 화풍의 큰 눈, 아이돌을 닮은 인상, 작은 키만으로는 미성년으로 판단하지 않음
    + 나이만 성인으로 정하고 아동 체형으로 그리는 요청은 미성년과 같은 기준을 적용
    + 이 기준은 스킬을 어떤 모델에서 실행하든 적용함
- 그 밖의 장면은 인물 연령을 제한하지 않음
    + 기본 인물은 날카로운 턱선의 성인 여성이며 프리셋에는 아동 체형과 교복 계열이 없음
    + 성인 남성은 `sex="male"` 1개로 같은 파이프라인을 거침 (남성 단면표, 근육 덩어리, 얼굴 입체, 짧은 머리)

## 준비

```bash
pip install numpy opencv-python-headless scipy skia-python
python scripts/check_env.py        # 버전 확인과 시험 렌더, 종료 코드 0이면 준비 완료
python scripts/check_env.py --full # 전 화풍 시험 렌더 (약 1분), 엔진을 수정한 뒤에도 실행
```

- 의존성 설치는 다른 작업보다 먼저 수행
- 로컬 환경에서는 프로젝트 전용 가상환경(conda 또는 venv) 안에 설치
- 엔진 위치는 `scripts/atelier/`, 장면 스크립트에서 `sys.path`에 `scripts` 폴더를 추가하여 임포트
- 결과물 수준은 `assets/gallery.jpg`에서 확인 가능 (예제 렌더 모음)

## 작업 흐름

| 단계 | 하는 일 | 산출물 |
|---|---|---|
| 1 기획 | 선택지를 제시하고 사용자 선택을 수집 | `Brief` |
| 2 디자인 | 아트 디렉션 문서 작성, 구도 확정 | `brief.md` |
| 3 구조 | 장면 스크립트 작성 (배경, 인물, 사물) | `scene.py` |
| 4 러프 | 저해상도 렌더로 구도와 명암 확인 | `*_rough.png` |
| 5 본 렌더 | 화풍과 마감 적용 | `*.png` |
| 6 검수와 수정 | 결과 확인, 결함 원인 단계로 돌아가 수정 | 수정된 `scene.py` |
| 7 전달 | 최종 이미지와 선택 내역 보고 | 이미지, 요약 |

### 1 기획

- `python scripts/brief_menu.py [subject]`로 선택지 목록을 얻어 사용자에게 제시
    + 주제, 화풍, 용도, 화면 비율, 구도, 디테일, 색 조합, 조명, 분위기, 배경, 인물 설정, 마감을 포함
    + 모든 항목에 기본값이 있으므로 "기본값으로"라는 답도 유효
- 사용자가 요청에서 이미 밝힌 항목은 다시 묻지 않음
- 요청이 충분히 구체적이거나 사용자가 맡긴 경우 질의를 생략하고 적용한 기본값을 결과 보고에 명시
- 선택 결과는 `Brief.from_answers(...)`로 기록, `brief.validate()`로 오타 확인
- 선택지별 의미와 질의 요령은 `references/workflow.md` 참조

### 2 디자인

- `brief.to_markdown()`으로 아트 디렉션 문서를 만들어 저장
- `message` 항목에 이 그림이 전달할 내용 1가지를 문장으로 기록
    + 메시지는 화면에 글자로 넣지 않고 구도, 색, 조명 결정의 기준으로 사용
- 시선이 머물 지점 1곳을 정하고 나머지 요소는 그 지점을 돕도록 배치

### 3 구조

장면 스크립트는 `build(canvas, light, brief)` 함수 1개와 `studio.run` 호출로 구성함.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("<skill-dir>/scripts")))          # 스킬 폴더의 scripts 경로
from atelier import Brief, Gradient, compose, geom, studio

brief = Brief.from_answers(style="anime_cel", framing="bust", lighting="studio",
                           message="차분하고 단단한 인상의 성인 여성")

def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    with canvas.layer(depth=0.95):                          # 배경: 먼 것부터
        canvas.add(geom.rect(0, 0, W, H), Gradient.linear((0, 0), (0, H), ["#cfdde6", "#efe6da"]), "wall", unlit=True)
    character = brief.character()                           # 브리프의 인물 설정으로 캐릭터 생성
    with canvas.layer(depth=0.3, group="figure"):           # 인물은 group="figure" 안에서 그림
        view = character.draw(canvas, light=light, **compose.framing(canvas, brief.framing))
    return {"views": [view]}                                # 본 렌더에서 손발 개수 자동 점검

if __name__ == "__main__":
    studio.run(build, brief, "picture.png")
```

- 그리는 순서는 뒤에서 앞으로 (하늘, 원경, 중경, 인물, 근경)
- `canvas.layer(depth=...)`의 depth는 1이 가장 멀고 0이 가장 가까움
    + depth는 대기 원근(멀수록 흐려짐)과 그림자가 닿는 범위를 결정
- 좌표는 디자인 단위(캔버스 폭과 높이 기준), 해상도 배율은 엔진이 처리
- 주제별 도구

| 주제 | 사용 모듈 | 참조 문서 |
|---|---|---|
| 인물화, 전신 인물 | `Figure`, `Character`, `Hair`, `wardrobe` | `references/figure.md` |
| 민속 의상 (기모노와 오비, 한복, 훈도시, 사라시) | `wardrobe.kimono`, `obi`, `jeogori`, `chima`, `baji`, `fundoshi`, `sarashi` | `references/figure.md` |
| 투샷, 여러 인물 (어깨동무, 손잡기) | `Ensemble` | `references/figure.md` |
| 풍경화 | `scenery`, `scenery.Perspective` | `references/scenery-objects.md` |
| 날씨 (비, 눈, 꽃잎)와 젖은 바닥 | `scenery.weather`, `scenery.wet_reflection` | `references/scenery-objects.md` |
| 실내 (방, 창, 의자, 탁자), 앉은 인물 | `Perspective.room`, `Perspective.chair`, `objects.table(clip=...)` | `references/scenery-objects.md`, `references/figure.md` |
| 손에 든 소품 (우산, 양산), 촛불 | `props.umbrella`, `objects.candle` | `references/scenery-objects.md`, `references/figure.md` |
| 두머 차림 (비니, 후드티, 터틀넥, 지친 눈), 입에 문 담배 | `Hair("beanie")`, `wardrobe.hoodie`, `turtleneck`, `expression="tired"`, `props.cigarette` | `references/figure.md` |
| 도시 거리 | `city` (건물 입면, 거리 시설, 그림자) | `references/scenery-objects.md` |
| 두머 배경 (패널 아파트, 송전탑, 굴뚝, 겨울나무, 놀이터 철골) | `city.building(kind="panel")`, `city.pylon`, `city.chimney`, `city.struts`, `scenery.bare_tree` | `references/scenery-objects.md` |
| 정물화, 사물 | `objects`, `Sculpture` | `references/scenery-objects.md` |
| 현대 사물 (노트북, 모니터, 휴대폰, 머그, 헤드폰, 카세트, 담배와 연기) | `props` | `references/scenery-objects.md` |
| 라이브러리에 없는 대상 | `Sculpture`, `geom`, `Canvas` | `references/api.md` |
| 스톡 아트 | `geom` 도형과 `flat_vector`, `flat_shadow` 화풍 | `references/styles.md` |

- 가장 가까운 예제를 복사하여 시작 (`scripts/examples/`)

| 예제 | 내용 |
|---|---|
| `portrait_anime.py` | 애니메 흉상, 기본 구조 |
| `portrait_webtoon.py` | 세미실사 웹툰 반신, 커스텀 포즈와 실내 배경 |
| `figure_classical.py` | 르네상스풍 전신 누드, 한 손을 머리 뒤로 올린 콘트라포스토 |
| `figure_classical_male.py` | 르네상스풍 남성 전신 누드, 다비드 자세와 골반 천 |
| `portrait_male.py` | 웹툰 남성 흉상, 짧은 머리와 니트, 도시 불빛 배경 |
| `duo_couple.py` | 웹툰 투샷, 남자는 어깨동무, 여자는 허리 감싸기, 셔츠 칼라와 안경, 노을 도시 배경 |
| `scene_anime_film.py` | 인물과 원근 도시 거리(입면, 전선, 건물 그림자), 극장판 애니메 합성 |
| `landscape_watercolor.py` | 수채화 산과 호수 |
| `landscape_ink.py` | 수묵담채 산수 |
| `still_life_oil.py` | 바로크 유화 정물 |
| `still_life_modern.py` | 현대 정물 (노트북, 휴대폰, 커피, 헤드폰, 화분), 화면 발광과 창빛 그림자 |
| `stock_flat.py` | 플랫 스톡 일러스트 |
| `custom_subject_cat.py` | 라이브러리에 없는 대상(고양이)을 덩어리로 조립 |
| `scene_rain_night.py` | 레트로 애니메, 비 오는 밤거리, 어깨에 걸친 우산, 젖은 노면의 반사와 빛 기둥 |
| `scene_cafe_window.py` | 어반 스케치, 카페 창가 실내, 의자에 앉아 노트북 자판에 손을 올린 인물, 창밖 거리 |
| `scene_beach_sunset.py` | 인상주의 유화, 해 질 녘 물가, 손잡은 두 사람의 뒷모습, 젖은 모래 반사 |
| `scene_snow_forest.py` | 파스텔, 눈 내리는 숲길, 눈 쌓인 침엽수, 걸어가는 뒷모습과 발자국 |
| `portrait_candle.py` | 바로크 유화, 촛불 하나의 반신 초상, 탁자에 올린 팔짱 |
| `scene_blossom_walk.py` | 우키요에, 꽃나무 아래 산책, 후리소데 기모노와 오비, 종이 양산, 흩날리는 꽃잎 |
| `figure_hanbok.py` | 민화, 모란 사이에 선 한복 차림 여성 (저고리, 동정, 고름, 치마) |
| `doomer_male.py` | 두머, 나트륨등 아래 비니와 후드티 차림으로 담배를 문 남성 흉상, 패널 아파트 배경 |
| `doomer_female.py` | 두머, 단발과 터틀넥에 긴 코트, 이어폰을 끼고 팔짱 낀 여성, 자작나무와 긴 아파트 |
| `doomer_duo.py` | 두머, 언덕 위 벤치에 앉은 두 사람의 뒷모습, 내려다보이는 야경, 송전탑과 전선, 굴뚝 |
| `doomer_establishing.py` | 두머 흑백, 위층에서 내려다본 단지 안마당 (놀이터, 주차한 차, 쓰레기통, 원경의 송전탑과 굴뚝) |
| `doomer_city.py` | 두머, 밤의 변두리 대로, 나트륨등과 트롤리버스 전선, 진창의 바퀴 자국과 반사, 매점과 정류장 |
| `doomer_landscape.py` | 두머 흑백, 송전탑이 지나가는 눈 덮인 들판, 전선 위 까마귀, 자작나무 띠와 먼 아파트 |
| `doomer_still_life.py` | 두머, 밤의 부엌 창가 식탁 (홀더에 끼운 찻잔, 재떨이와 타는 담배, 성냥, 카세트), 창밖 아파트 |

### 4 러프

```bash
python scene.py --rough       # 절반 해상도 셀 렌더, 3단 명도, 삼분할 가이드를 한 장에 출력
```

- 러프에서 확인할 내용은 구도, 크롭, 명암 덩어리, 시선 지점
- 3단 명도 그림에서 주제가 읽히지 않으면 조명 또는 배색을 먼저 수정
- 러프가 통과되기 전에는 본 렌더를 실행하지 않음 (유화 계열은 렌더 시간이 길어짐)

### 5 본 렌더

```bash
python scene.py                              # 브리프의 화풍으로 본 렌더, 명도 통계와 손발 점검 출력
python scene.py --styles watercolor,oil,cel  # 같은 그림을 여러 화풍으로 비교
python scene.py --style oil --light rembrandt --scale 1.5 --out final.png
```

- 화풍 선택이 미정이면 `--styles`로 후보 2-4개를 한 장에 렌더하여 사용자에게 제시
- 화풍, 조명, 매체 파라미터 목록은 `references/styles.md` 참조
- 장면에 맞춘 매체 조정(파스텔 종이색, 붓 크기)은 `build`가 반환하는 사전의 `style_params`에 넣음

### 6 검수와 수정

- 렌더 이미지를 직접 열어 확인 (이미지 보기 기능이 없는 환경에서는 `image check` 수치와 `--buffers` 출력으로 대체)
- 결함은 발생 단계에서 수정
    + `python scene.py --buffers`가 밑색, 형태(normal), 조명, 영역, 선화, 깊이를 따로 보여 주므로 원인 단계를 특정 가능
- 점검 항목과 결함별 처방은 `references/critique.md` 참조
- 최소 1회 검수 후 수정, 같은 결함이 2회 수정에도 남으면 접근을 바꿈 (포즈 변경, 크롭 변경, 화풍 변경)
- 얼굴과 손처럼 작은 부위는 `qa.zoom`으로 확대하여 확인

### 7 전달

- 최종 PNG, 적용한 선택 내역(사용자 지정과 기본값 구분), 재현 명령을 함께 전달
- 사용자가 수정 요청을 하면 `Brief` 값 또는 `build` 내용만 고쳐 다시 렌더 (시드가 같으면 결과가 재현됨)

## 화풍 계열

| 계열 | 화풍 키 |
|---|---|
| 애니메이션, 만화 | anime_cel, anime_film, retro_anime, webtoon, manga |
| 일러스트, 디자인 | flat_vector, flat_shadow, poster, storybook, pop_art, art_nouveau |
| 서양 회화 | renaissance, baroque, academic, oil, impressionism, post_impressionism, expressionism, fauvism, pointillism, cubism |
| 동양 회화 | sumi_e, ink_color, ukiyo_e, minhwa |
| 소묘 | pencil, colored_pencil, charcoal, pastel |
| 수채 | watercolor, watercolor_loose, urban_sketch |
| 두머 | doomer, doomer_mono |

- 화풍은 매체, 매체 파라미터, 권장 조명, 마감 패스의 묶음
- 얼굴 작화 방식은 화풍에 따라 3종 (anime, semi, classic)으로 자동 선택
- 프리셋에 없는 화풍은 가장 가까운 프리셋의 파라미터를 조정하여 구성 (`references/styles.md`의 조합 요령 참조)

## 완성도 기대 수준

| 수준 | 대상 | 상태 |
|---|---|---|
| 안정 | 플랫 일러스트, 스톡 아트, 애니메와 웹툰 흉상과 반신, 풍경 전 매체, 정물, 현대 사물, 도시 거리와 차량, 수묵, 판화 계열, 두머 배경과 정물 | 1-2회 수정으로 완성 |
| 양호 | 전신 인물과 의상, 고전 누드(여성, 남성)의 체형과 근육 결, 세미실사 얼굴, 남성 얼굴과 짧은 머리, 투샷 접촉 동작과 뒷모습 손잡기, 인물이 있는 원근 장면, 3점 투시 장면, 유화 인물, 날씨 장면과 젖은 바닥, 실내와 앉은 인물, 우산을 든 인물, 기모노와 한복, 두머 인물 (비니, 후드티, 담배) | 포즈와 조명 조정 필요 |
| 한계 | 힘줄과 혈관 수준의 해부, 복잡한 의상 주름, 곱슬머리와 땋은 머리, 포옹처럼 두 팔이 서로 감기는 동작, 손으로 턱을 괴는 동작, 누운 자세, 군중, 기모노 무늬가 옷 주름을 따라 휘는 표현 | 양식화된 결과로 안내 |

- 한계 수준의 요청은 결과의 성격을 사용자에게 미리 알림

## 참조 문서

| 문서 | 읽는 시점 |
|---|---|
| `references/workflow.md` | 기획 질의, 아트 디렉션 문서, 반복 절차의 세부가 필요할 때 |
| `references/figure.md` | 인물을 그릴 때 (포즈 규약, 손, 머리, 의상, 얼굴, 크롭) |
| `references/scenery-objects.md` | 풍경, 원근 배경, 정물, 커스텀 대상을 그릴 때 |
| `references/styles.md` | 화풍, 조명, 매체 파라미터, 마감 패스를 고르거나 조정할 때 |
| `references/api.md` | `Canvas`, `geom` 등 저수준 도구로 직접 그릴 때 |
| `references/critique.md` | 렌더 결과를 검수하고 결함을 고칠 때 |
