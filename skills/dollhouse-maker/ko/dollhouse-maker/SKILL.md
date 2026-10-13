---
name: dollhouse-maker
description: "인형의 집처럼 벽 한 면을 열어 둔 1점 원근 모형 방에 인형처럼 단정한 사람들을 세워 조용한 일상의 한 컷을 꾸미는 스킬. 곡선, 리본, 비례 기준선을 Python 코드(numpy, OpenCV, scipy)로 작도하고 실루엣을 부풀린 가상 입체로 음영을 입혀, 깔끔한 윤곽, 매끈하게 부푼 명암, 손가락 다섯 개까지 정확한 인물을 만들고 같은 장면을 애니메, 일러스트, 유화, 수채화, 연필 소묘, 레트로 판화 포스터, 네온 야경 7가지 마감으로 바꿔 낸다. 카페, 교실, 사무실, 침실, 거실, 공원, 노을 옥상, 해변, 비 오는 거리와 밤 실내, 표정과 머리 모양과 나이가 제각각인 인물, 투샷부터 8인 그룹샷, 걷기와 앉기와 눕기, 손동작, 인체드로잉, 풍경, 도시, 현대 사물까지 다룬다. 이미지 생성 모델 없이 그림이 필요할 때, 또는 사용자가 '그림 그려줘', '일러스트 만들어줘', '코드로 그림', '캐릭터 시트', '표정 시트', '투샷', '단체 사진', '카페 장면', '밤 사무실', '수채화풍', '연필 스케치', '레트로 포스터', '네온 야경', '배경 일러스트', '확산모델 없이 이미지'를 요청할 때 반드시 사용할 것. 엔진 API는 references/api.md, 인물과 장면 모듈의 매개변수와 좌표는 references/subjects.md, 구도와 명암의 기준과 결함 대응표는 references/craft.md에 있다. 차트, 다이어그램, UI 시안, 사진 보정에는 사용하지 않는다."
license: GPL-3.0-or-later with an additional permission for generated images (see NOTICE.md)
---

# dollhouse-maker

그림을 화가의 작업 순서대로 코드로 작도하는 스킬. 형태는 2D 작도(곡선, 리본, 비례 기준선)로 만들고 명암은 실루엣을 부풀려 얻은 가상 법선으로 계산한다. 구조가 수치로 고정되므로 손가락 5개, 발가락 5개, 이목구비 위치가 항상 정확하다.

## 핵심 원리

- 그림 1장은 뒤에서 앞으로 쌓은 `Part`(평면 도형 1개)의 목록
    + 렌더러가 도형마다 입체 명암, 위 도형이 드리우는 그림자, 외곽선을 부여
- 장면은 1회 작도하고 화풍은 렌더링 시점에 선택
    + `anime`(단계 명암과 선), `illust`(부드러운 명암과 색선), `painterly`(붓질 재도장)
    + `watercolor`(투명 수채), `pencil`(연필 해칭), `poster`(레트로 판화 색면과 망점), `neon`(밤의 자홍 주광과 청록 테두리광)
    + 모든 장면은 어느 화풍으로도 렌더링 가능, 장면과 화풍은 서로 독립
- 몸통과 팔다리처럼 이어지는 도형은 `merge` 키로 묶어 한 표면으로 잉크 처리
    + 합집합의 실루엣과 앞뒤로 겹치는 경계만 선으로 그려 관절 이음매가 생기지 않음
- 3D 모델링, 깊이값, 회전 투영, 메시, 외부 이미지 생성 API, 네트워크 호출을 사용하지 않음
    + 몸과 얼굴의 3/4 시점은 회전 계산 대신 작화 규칙(중심선 이동, 먼 쪽 축소, 가까운 쪽 확대, 겹침 순서)으로 작도
    + 뒷모습은 등쪽 해부 표지, 옆모습은 몸의 앞뒤 윤곽표와 옆얼굴 윤곽표로 작도
    + 사물은 사선 투상 상자 작도(정면 실형, 깊이는 고정 사선 평행 이동)로 작도
    + 의존성은 `numpy`, `opencv-python-headless`, `scipy` 3종
- 실내, 공원, 옥상, 해변 장면은 1점 원근 무대로 작도
    + 앞면은 화면과 나란한 실형, 깊이 모서리는 소실점 1개로 모임
    + 카메라 1개가 벽, 가구, 인물 크기를 함께 결정하여 축척이 어긋나지 않음
- 옷은 몸의 실제 윤곽에서 재단
    + 몸통은 윤곽을 여유분만큼 키워 목선과 밑단 사이 띠로 자름
    + 소매와 바짓가랑이는 뼈를 따라 놓인 통으로 작도하여 모든 자세와 시점에 그대로 맞음

## 작업 절차

각 단계의 산출물을 확인한 뒤 다음 단계로 진행한다. 한 번에 완성하려는 시도는 결함 위치를 찾기 어렵게 만든다.

1. (의존성) `scripts/requirements.txt`의 패키지 3종을 작업 환경의 패키지 관리 규칙에 맞춰 설치한 뒤 `python scripts/selftest.py 출력폴더` 1회 실행으로 엔진 정상 여부 확인
2. (기획) 소재, 화면 비율, 화풍, 광원 방향, 초점 1곳을 문장으로 확정
    + 사용자가 지정하지 않은 항목은 기본값을 적용하고 적용 사실을 보고
3. (디자인 문서) 구도, 색 팔레트 3-5색, 명암 구조(가장 밝은 곳과 가장 어두운 곳의 위치)를 짧은 `.md`로 기록
    + 작성 기준은 `references/craft.md`의 구도, 색, 명암 항목
4. (밑그림) 큰 도형부터 뒤에서 앞 순서로 `Part` 배치, 선과 세부 없이 1차 렌더링
    + 전용 모듈이 있는 소재는 모듈을 사용, 없는 소재는 `scripts/examples/custom_scene.py` 방식으로 직접 작도
5. (선과 세부) 외곽선 굵기, 이목구비, 주름, 머리카락 가닥 등 `Line`과 `Stroke` 추가
6. (채색과 명암) 재질, 광원, 그림자 거리, 보조 음영 도형 조정
7. (후보정과 검수) 화풍 마감 적용 후 렌더링 결과를 직접 열어 확인, 결함 수정 후 재렌더링
    + 얼굴, 손, 관절은 `review.zoom`으로 확대 확인
    + 이미지를 열 수 없는 환경은 `review.stats` 수치로 대체

## 빠른 시작

`scripts/` 폴더를 작업 위치로 복사하거나 `sys.path`에 추가한 뒤 사용한다.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from codepaint import Scene, save, backdrop, finish
from codepaint.subjects.head import Head, HeadSpec
from codepaint.subjects.bust import Bust, BustSpec

scene = Scene(1024, 1280, light=(-0.55, -0.55, 0.63), seed=11)      # 빛은 좌상단 앞쪽
scene.set_background(backdrop.studio(1280, 1024, "#cfe3ee", "#7ea3c4"))
head = Head(HeadSpec(cx=480, top=170, size=560, yaw=0.20, jaw=0.95, bangs="swept"))
bust = Bust(head, BustSpec(outfit="camisole", cloth="#27354f"))
scene.add(head.back_parts(), bust.parts(), head.front_parts())     # 뒤에서 앞 순서
save(scene.render("anime"), "portrait.png")
```

전신 인체는 성별, 자세 프리셋, 체형 배율로 작도한다.

```python
from codepaint.subjects.figure import Figure, FigureSpec
figure = Figure(FigureSpec(cx=448, top=70, unit=180, outfit="slip", cloth="#2a2a40", bust=1.10, waist=0.95, legs=1.05),
                pose="pinup")    # 자세 프리셋 16종, 목록은 references/subjects.md의 자세 항목
man = Figure(FigureSpec(cx=448, top=70, unit=180, sex="male", outfit="trunks", cloth="#1f5f8f"), pose="akimbo")
scene.add(figure.parts())
```

옷, 시점, 손동작은 같은 `Figure`의 필드로 지정한다.

```python
import dataclasses
from codepaint.subjects.figure import POSES
walker = Figure(FigureSpec(cx=448, top=70, unit=180, outfit="dressed", upper="tee", lower="jeans", shoes="sneakers",
                           cloth="#f2efe8", cloth2="#3b5b8a"), pose="walk")             # 옆모습 걷기
back = Figure(FigureSpec(cx=448, top=70, unit=180, sex="male", outfit="dressed", upper="shirt", lower="slacks"),
              pose=dataclasses.replace(POSES["akimbo"], view="back"))                   # 아무 자세의 뒷모습
caller = Figure(FigureSpec(cx=448, top=70, unit=180, outfit="dressed", upper="longsleeve", lower="skirt",
                           right_item="phone"), pose="phone")                          # 휴대폰을 쥔 손
```

두 사람과 장소는 구도 함수와 장면 템플릿으로 조립한다.

```python
from codepaint.subjects import pair, scenes
s = scenes.park(1500, 1000)                                   # 카메라, 배경, 인물 자리
x, z, _ = s.spots["path"]
a = s.cam.fit(her_spec, pair.STAND_A, x, z)                   # 깊이 z에 맞는 크기와 발 위치
b = s.cam.fit(his_spec, pair.STAND_B, x, z)
two = pair.arm_over_shoulder(a, b, float(s.cam.P(x, 0, z)[0]))   # 어깨동무, 인물별 이름 공간 자동 부여
scene.add(s.back, two.parts, s.front)
```

- 남성은 `sex="male"` 1개 값으로 어깨, 골반, 팔다리 폭표, 대흉근, 복근, 손 폭, 얼굴과 짧은 머리 기본값이 함께 전환
- 남성 초상은 `HeadSpec(face="male", hair_style="short", bangs="short")`와 `BustSpec(sex="male")` 조합

현대 사물은 책상 작도 틀(`Desk`) 위에 놓고 뒤쪽 사물부터 추가한다.

```python
from codepaint.subjects import objects as ob
desk = ob.Desk(x=800, y=800, unit=62)                  # 책상면 원점의 화면 위치, 10 cm당 px
scene.add(ob.monitor(desk, -1.6, 3.4, screen_kind="desktop"),   # (중심 x, 앞 모서리 z), z가 클수록 뒤
          ob.keyboard(desk, -1.6, 0.4), ob.mug(desk, -5.6, 0.0))
```

풍경과 도시는 완성된 기준 그림을 반환하므로 `finish`로 화풍만 입힌다.

```python
from codepaint.subjects.landscape import build_landscape, LandscapeSpec
save(finish(build_landscape(LandscapeSpec(seed=3)), "painterly"), "lake.png")
```

## 소재별 진입점

| 소재 | 모듈 | 예제 | 권장 화풍 |
|---|---|---|---|
| 얼굴, 상반신 초상(여성, 남성) | `subjects/head.py`, `subjects/bust.py` | `examples/portrait.py` | anime, illust |
| 상황, 포즈, 구도, 그룹샷 시험 21장(빗속 2인, 밤 침실, 해변 휴식, 벤치, 수업, 포즈 16종, 노부부 산책, 뒷모습 4인, 라인업, 근접샷, 원경, 낮은 시점, 3분할, 단체 사진, 소파 4인, 횡단보도 8인, 공원 2쌍, 회의, 밤 사무실) | `subjects/scenes.py`, `subjects/stage.py`, `subjects/pair.py`, `subjects/figure.py` | `examples/variety.py`(`BUILDERS`) | 화풍 7종에 2-4장씩 |
| 인물 다양화(표정 7종, 눈매 4종, 얼굴 폭, 눈썹 굵기, 나이와 흰머리, 수염 4종, 안경 3종, 주근깨, 점, 머리 모양 12종)와 군중 | `subjects/head.py`, `subjects/face_extras.py`, `subjects/profile.py` | `examples/faces.py`(`BUILDERS`: 견본 시트 4장, 공원 군중) | anime, illust |
| 전신 인체(여성, 남성, 누드, 수영복, 슬립, 서기, 앉기, 눕기) | `subjects/figure.py` | `examples/figure.py` | anime, illust, painterly(scale 0.5) |
| 일상복(상의 4종, 하의 4종, 신발 3종) | `subjects/garments.py`, `subjects/extremities.py` | `examples/figure.py`(`street`, `turnaround()`) | anime, illust |
| 뒷모습, 옆모습(옆얼굴, 걷기, 의자 앉기) | `subjects/figure.py`, `subjects/side.py`, `subjects/profile.py` | `examples/figure.py`(`back`, `side_seated`), `examples/portrait.py`(`build_back()`) | anime, illust |
| 투샷(나란히 서기, 손잡기, 어깨동무, 대화) | `subjects/pair.py` | `examples/scenes.py`(`pairs()`) | illust, anime |
| 원근 장면(카페, 교실, 거실, 공원)과 실내 무대, 원근 가구, 밤 전환(`Set.night`), 가구 사이 인물 배치(`Set.arrange`) | `subjects/stage.py`, `subjects/scenes.py` | `examples/scenes.py` | anime, illust |
| 새 장소(사무실, 침실, 노을 옥상, 해변, 비 오는 밤거리, 저녁 거리)와 비, 젖은 바닥 반사, 우산 | `subjects/scenes.py`, `subjects/stage.py`, `subjects/held.py` | `examples/gallery.py` | 장소별 권장은 갤러리 참조 |
| 화풍 7종 x 상황 12종 묶음 | 위 모듈 전체 | `examples/gallery.py`(`BUILDERS`) | 모든 화풍 |
| 두머 연작 7장(겨울 밤 패널 아파트: 남성, 여성, 투샷, 설정샷, 도시, 풍경, 사물)과 후드티, 비니, 목도리, 담배, 눈, 패널 아파트, 나트륨 가로등, 송전탑, 지하보도, 버스정류장, 창턱 소품 | 예제 파일 안에서 엔진 부품으로 작도 | `examples/doomer.py`(`BUILDERS`) | 화풍 7종에 1장씩 |
| 손, 발, 손동작(주먹, 가리키기, 쥐기), 쥐는 물건 | `subjects/extremities.py`, `subjects/held.py` | `examples/hands.py`(`gestures()`) | illust |
| 산, 호수, 숲 풍경 | `subjects/landscape.py` | `examples/landscape.py` | painterly, anime |
| 도시 거리(낮, 황금시간, 저녁, 밤) | `subjects/city.py` | `examples/city.py` | anime, painterly(scale 0.6) |
| 현대 사물 15종(컴퓨터, 휴대 기기, 책상 소품, 생활 가전)과 의자 | `subjects/objects.py` | `examples/desk.py`(`study()`는 책상 앞 인물) | anime, illust |
| 그 외 모든 소재 | `Part`, `Ribbon`, `Stroke` 직접 작도 | `examples/custom_scene.py` | illust |

매개변수 전체 목록은 `references/subjects.md`, 엔진 API는 `references/api.md`에 있다. 예제 파일은 그대로 복사해 값만 바꾸는 출발점으로 사용한다.

## 화풍 선택

| 화풍 | 명암 | 선 | 마감 | 적합한 소재 |
|---|---|---|---|---|
| `anime` | 2단계 경계 명암 | 어두운 선, 그림자 쪽 굵게 | 확산광, 블룸 | 캐릭터, 배경 미술 |
| `illust` | 부드러운 명암과 약한 경계 | 고유색을 어둡게 한 색선 | 종이결, 역광 테두리 | 인물, 동물, 소품 |
| `painterly` | 연속 명암 | 선 없음 | 붓질 재도장, 임파스토, 캔버스결 | 풍경, 인체 습작, 정물 |
| `watercolor` | 밝은 연속 명암 | 가는 색선 | 번짐, 안료 고임, 입자, 흰 종이 테두리 | 아침 실내, 공원, 일상 장면 |
| `pencil` | 회색조 명암 | 흑연 선 | 명도별 3방향 해칭, 종이결 | 캐릭터 시트, 장면 습작 |
| `poster` | 2단계 평면 명암 | 굵은 남색 선 | 판화 색면, 망점, 바랜 종이 | 사무실, 교실, 도시 일상 |
| `neon` | 청보라 그늘, 자홍 주광 | 가는 어두운 선 | 강한 발광 번짐, 색수차, 어두운 비네트 | 밤거리, 밤의 방, 화면 빛 |

- 세부 조정은 `get_style("painterly", painterly=dict(scale=0.5))`처럼 필드를 덮어써서 수행
    + 인물과 건축은 `scale` 0.5-0.6, 넓은 풍경은 기본값 1.0 권장
- `poster`는 색상이 가까운 면을 한 색으로 합치므로 옷색을 피부와 색상이 먼 색으로 고름
- `neon`은 화면 안에 간판, 모니터, 스탠드 같은 발광원이 있는 밤 장면에 사용
- 화풍별 마감 기준은 `references/craft.md`의 화풍별 마감 항목

## 새 소재 작도 규칙

- 큰 덩어리 3-7개로 먼저 분해하고 작은 세부는 덩어리가 맞은 뒤에 추가
    + 덩어리 비례가 틀린 그림은 세부로 회복되지 않음
- 둥근 덩어리는 `polys`(다각형), 길쭉한 형태는 `Ribbon`(축과 좌우 폭)으로 작도
    + 팔다리, 꼬리, 머리카락 가닥, 나무 줄기는 리본이 정확한 원통 명암을 부여
- 몸통에서 자라나는 팔다리, 동물의 다리와 목은 `merge`, `joints`, `grow_from`으로 이음매 제거
    + 사용법은 `references/api.md`의 이어지는 도형 항목 참조
- 곡선은 제어점 4-8개를 `catmull_rom`으로 연결, 모서리가 필요한 곳은 곡선 2개를 이어 붙임
- 다른 도형 위에 놓이는 세부(홍채, 볼터치, 무늬)는 `clip`으로 바탕 도형 안에 가둠
- 이어지는 두 도형의 경계(목과 어깨, 팔과 몸통)는 `fade_t` 또는 `erase`로 흐려 이음매 제거
- 좌표는 기준 단위 1개(머리 높이, 몸 길이 등)의 배수로 계산하여 크기 변경에 대응
- 난수는 모두 `seed`로 고정하여 동일 입력에서 동일 그림 재현

## 검수

렌더링 후 아래 항목을 이미지에서 직접 확인한다. 결함별 원인과 조치는 `references/craft.md`의 결함 대응표에 있다.

- 실루엣만으로 소재가 읽히는가
- 초점에 가장 강한 명암 대비가 놓였는가
- 도형 사이 이음매, 뚫린 틈, 의도하지 않은 계단이 없는가
- 인물의 손가락 5개, 발가락 5개, 눈 2개의 시선 방향이 일치하는가
- 빛 방향이 모든 도형과 드리운 그림자에서 일치하는가
- 화면 가장자리에서 잘린 도형이 어색하지 않은가

## 작도 범위

- 미성년자의 누드와 성적 묘사는 작도하지 않음
    + 판단 기준은 이차성징 이전의 신체 묘사(아동 비례, 발달 전 가슴과 골반)
    + 나이 또는 설정이 18세 미만으로 명시된 인물에도 같은 규정 적용
    + 화풍 특성(애니메풍의 큰 눈과 작은 코)만으로는 미성년으로 판단하지 않음

## 한계

- 전신 모듈은 정면, 3/4, 옆모습, 뒷모습의 서기, 걷기, 앉기 자세와 3/4 옆으로 눕기 자세 지원
    + 엎드린 자세, 위나 아래에서 내려다본 시점, 카메라를 향한 강한 단축은 미지원
    + `turn` 절댓값 0.7 초과는 부정확하며 3/4과 옆모습 사이 각도는 미지원
    + 인체 비례는 성인 8등신 1종만 지원
    + 옆모습과 뒷모습에서는 고개 좌우 돌림(`head_yaw`)이 적용되지 않음
- 고개 돌림은 좌우 약 0.45 이내에서 안정적이며 고개 숙임은 옆모습의 `head_tilt`로만 표현
- 표정은 프리셋 7종이며 윙크, 한쪽 입꼬리 올림 같은 비대칭 표정은 미지원
    + 수염, 안경, 주름, 주근깨는 정면, 3/4, 옆얼굴에서 작도하고 뒷모습에서는 생략
    + 양갈래, 땋은 머리, 곱슬의 길이와 부피는 고정값(`TWIN_AXIS`, `BRAID_AXIS`, `CURL_R`)이며 `hair_length`는 `long`, `wavy`에만 적용
- 의상은 여성 수영복 3종과 슬립 드레스, 남성 수영복 2종과 열린 셔츠, 남녀 공통 일상복(상의 4종, 하의 4종, 신발 3종)
    + 재킷, 코트, 일상 원피스, 모자, 가방 등 장신구는 직접 작도 필요(안경은 `HeadSpec.glasses`로 지원)
    + 옷 주름은 정해진 위치의 선으로 표현하며 자세에 따라 당기는 주름은 미지원
- 투샷은 접촉 구도 4종(나란히 서기, 손잡기, 어깨동무, 대화) 지원
    + 포옹, 업기, 춤처럼 몸이 크게 맞물리는 구도는 미지원
    + 세 명 이상은 `ident`를 다르게 주어 직접 배치, 8인 그룹까지 시험 완료(`examples/variety.py`)
    + 걷는 군중은 `figure.walk(phase, stride)`로 사람마다 걸음 단계와 보폭을 다르게 지정
- 원근 무대는 1점 원근만 지원
    + 비스듬히 돌린 가구, 2점 원근 건물, 계단과 경사면은 미지원
    + 장면 템플릿은 9종(카페, 교실, 거실, 공원, 사무실, 침실, 노을 옥상, 해변, 도시 거리)이며 그 밖의 장소는 무대 부품으로 직접 조립
    + 템플릿은 카메라 키워드(`eye`, `horizon`, `focal`, `vp_x`)로 근접샷과 낮은 시점을 지원
    + 밤 장면은 템플릿에 `.night()` 적용, 인물을 가구 사이에 세울 때는 `Set.arrange`로 깊이 정렬
    + 가구 깊이는 가구 1개 단위로 정렬하므로 한 가구를 관통하는 배치(긴 탁자 한가운데 선 사람)는 앞뒤 중 하나로 처리
    + 뒷모습 인물끼리의 손잡기와 어깨동무는 미지원
    + 우산은 대가 화면에 수직인 자세만 지원
- 손은 자연, 주먹, 가리키기, 쥐기 4형태 지원, 그 밖의 손 자세(브이, 깍지)는 직접 작도 필요
    + 옆모습의 손은 손등 형태를 좁혀 근사
- 도시의 차량과 행인은 단순 형태이며 근경 주인공용 묘사는 직접 작도 필요
- 사물은 정면이 화면과 나란한 배치만 지원
    + 책상 위에서 비스듬히 돌린 사물은 미지원
    + 강한 원근의 근접 시점도 미지원
- 사진 수준 사실 묘사는 범위 밖이며 양식화된 그림이 목표
- 동물 등 전용 모듈이 없는 소재는 직접 작도 필요
- 1024x1280 기준 렌더링 1회 소요는 약 2-9초, 도시 회화풍은 약 13초, 2000x1300 연필풍은 약 20초

## 참조 문서

- `references/api.md`: 엔진 API 전체(Scene, Part, Line, Stroke, Ribbon, 이어지는 도형, 화풍, 재질, 붓질, 후보정, 배경, 검수 도구). 새 소재를 직접 작도할 때 읽기
- `references/subjects.md`: 소재 모듈의 매개변수, 좌표 규약, 비례 수치. 인물, 풍경, 도시를 다룰 때 읽기
- `references/craft.md`: 구도, 명암, 색, 선의 작화 기준과 결함 대응표. 디자인 문서 작성과 검수 단계에서 읽기
