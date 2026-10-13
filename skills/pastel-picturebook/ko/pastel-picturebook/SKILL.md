---
name: pastel-picturebook
description: "맑은 색과 가는 선, 단정한 셀 명암으로 엽서 한 장 같은 장면을 그리는 파스텔 그림책 스킬. 큰 눈의 인물은 종이인형처럼 반듯하게 서서 웃고, 손을 흔들고, V 사인을 한다. 무대는 햇살 비치는 해변, 벚꽃길, 산과 호수, 공원 피크닉, 노을 진 옥상, 카페와 방에서 비 오는 네온 거리와 눈 내리는 밤까지 이어진다. 확산모델과 이미지 생성 API 없이 numpy와 OpenCV 코드만으로 기획, 밑그림, 밑색, 명암, 선화, 마감 공정을 밟는다. 여성과 남성의 초상과 전신(정면, 3/4, 뒷모습, 측면, 앉기, 걷기, 눕기), 둘에서 넷까지의 인물 장면(손잡기, 어깨동무, 포옹, 춤, 셀카, 단체 사진, 건배), 표정, 개성, 의상, 소품, 손, 정물, 풍경, 도시, 실내, 날씨를 다룬다. 화풍은 애니메풍, 일러스트풍, 회화풍, 수채화, 연필 스케치, 흑백 만화, 픽셀 아트, 필름 야경 가운데 고른다. 설정 키와 얼굴 매개변수는 references/spec.md, 피사체별 구성과 장면 합성은 references/subjects.md, 공정 원리와 결함 진단은 references/pipeline.md, 새 피사체, 화풍, 소품의 추가 방법은 references/extending.md에서 읽는다. '/pastel-picturebook', '코드로 그림 그려줘', '확산모델 없이 그림', '그림책 같은 그림', '엽서 같은 그림', '파스텔 그림', '애니메풍 인물', '수채화로 그려줘', '해변 그림', '벚꽃 배경', '비 오는 카페', '커플 그림', '단체 사진', '정물화', '풍경화', 'draw with code', 'procedural painting' 등을 요청하거나 이미지 생성 도구가 없는 환경에서 그림을 요청할 때 반드시 이 스킬을 사용할 것."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and OUTPUT_EXCEPTION.md
---

# 파스텔 그림책

신경망 없이 코드만으로 그림을 그리는 스킬. 그림 제작 공정을 단계별 코드로 옮긴 도구 모음(`scripts/`)과 그 도구를 다루는 작업 절차를 제공

## 원리

- 사람이 그림을 그리는 순서를 그대로 코드 단계로 구현
    + (밑그림) 곡선, 골격, 투시로 형태를 배치
    + (밑색) 부위별 마스크에 단색을 채움
    + (명암) 형태에 높이를 주어 얻은 법선과 광원 방향으로 음영을 계산
    + (선화) 윤곽을 굵기 변화가 있는 획으로 변환
    + (마감) 화풍별 후처리 적용
- 8개 화풍은 같은 밑그림을 공유하고 팔레트, 명암 방식, 마감만 교체
    + 수채화, 연필, 흑백 만화, 픽셀 아트, 두머는 기존 화풍(일러스트풍, 애니메풍)을 바탕으로 마감 단계에서 다시 그림
- 그림의 품질은 렌더링 결과를 직접 보고 고치는 반복에서 결정
    + 코드는 좌표 오차를 스스로 알지 못하므로 눈으로 확인하는 절차가 필수

## 피사체

| 피사체 | `--subject` | 내용 | 기본 화면 | 잘 어울리는 화풍 |
|---|---|---|---|---|
| 초상 | `portrait` | 여성 또는 남성 흉상 | 1200x1600 | 8종 모두 |
| 전신 인물 | `figure` | 여성 또는 남성. 정면, 3/4 비스듬한 시점, 뒷모습(어깨 너머 돌아보기), 측면, 누운 자세. 서기, 앉기, 다리 꼬고 앉기, 무릎 꿇고 앉기, 벽에 기대기, 걷기(측면, 정면), 뛰기, 점프, 웅크려 앉기, 팔짱, 손 흔들기, V 사인, 기지개, 턱 괴기, 컵, 책, 우산, 와인잔, 휴대폰 들기, 포옹과 입맞춤(측면 두 인물). 의상 또는 인체 습작 | 1200x1600 | paint, illust |
| 손 | `hand` | 여성 또는 남성 손. 손등과 손바닥 습작(펼침, 이완, V, 가리킴) | 1600x1200 | anime, illust |
| 정물 | `still_life` | 탁자 위 병, 그릇, 과일 | 1600x1200 | paint, illust |
| 책상 | `desk` | 모니터, 노트북, 키보드, 마우스, 휴대폰, 머그, 화분, 스탠드, 노트 | 1600x1200 | anime, illust |
| 풍경 | `landscape` | 하늘, 산맥, 호수 반영, 침엽수 | 1600x1200 | illust, paint |
| 해변 | `beach` | 하늘, 수평선까지의 바다, 파도 거품, 젖은 모래와 마른 모래, 야자수 | 1600x1200 | anime, illust |
| 도시 | `city` | 1점 투시 거리, 낮 또는 야경 | 1200x1600 | anime, paint |
| 공원 | `park` | 피크닉 잔디밭. 깎은 줄무늬 잔디, 들꽃, 먼 숲, 초록 나무, 체크무늬 돗자리와 바구니 | 1600x1200 | anime, watercolor |
| 벚꽃길 | `sakura` | 머리 위에서 맞닿는 벚나무 터널, 소실점까지 뻗은 산책로, 떨어진 꽃잎과 날리는 꽃잎 | 1600x1200 | anime, illust, watercolor |
| 옥상 | `rooftop` | 노을 하늘과 지는 해, 역광의 스카이라인, 유리 난간, 전구 줄, 화분 | 1600x1200 | anime, illust |
| 불꽃놀이 | `fireworks` | 밤하늘의 불꽃(국화, 모란, 버들), 불 켠 고층 건물, 빛을 비추는 강, 강변 난간 | 1600x1200 | anime, manga |
| 판넬 단지 | `panelka` | 밤의 판넬 아파트 단지 마당. 불 켜진 창, 발코니, 현관등, 전봇대와 전선, 나트륨 가로등, 자작나무, 그네, 눈. 단지 사이 거리로도 구성 | 1600x1200 | doomer, anime |
| 외곽 들판 | `outskirts` | 해 질 녘 도시 외곽. 마른 풀밭, 흙길, 지평선까지 이어진 송전탑과 전선, 멀리 아파트 줄, 까마귀 | 1600x1200 | doomer, illust |
| 카페 | `cafe` | 눈높이 실내. 거리가 보이는 창, 카운터와 에스프레소 머신, 원탁, 펜던트 조명. 낮 또는 밤 | 1600x1200 | anime, illust |
| 방 | `room` | 눈높이 거실. 커튼 창, 소파, 책장, 러그, 스탠드. 낮 또는 밤 | 1600x1200 | anime, illust |
| 침실 | `bedroom` | 눈높이 침실. 머리판 침대, 협탁과 탁상 스탠드, 커튼 창. 기본 밤 | 1600x1200 | anime, illust |
| 욕실 | `bathroom` | 눈높이 욕실. 벽과 바닥 타일, 욕조, 세면대와 거울, 유리 샤워 칸, 수건 | 1600x1200 | anime, illust |

- 장면: 인물(초상, 전신)의 설정에 `backdrop`(다른 피사체를 배경으로), `companions`(다른 인물)를 넣어 합성
- 접촉: 손 목표점(`reach`)으로 상대의 손, 어깨, 팔꿈치, 등, 화면 지점에 손을 놓고, `lift`로 먼저 그린 인물의 손을 나중 인물 위에 다시 올림. `lift_under_head`면 상대 머리카락 아래로 지나감
- 장면 소품: `props`의 벤치(정면으로 앉은 인물들), 카페 탁자(측면으로 앉은 인물들). 손에 드는 우산은 비를 막음. 측면 인물이 기대는 기둥(`profile_pose.wall`)
- 여러 인물: 세 사람 이상도 같은 방식(`companions` 목록). 단체 사진, 건배, 춤, 셀카의 구성 값은 `references/subjects.md`의 여러 인물 장면 절
- 날씨: 설정 최상위 `weather`로 비, 눈, 꽃잎. 야외는 그림 전체, 실내는 창밖에만
- 피사체별 설정 항목은 `references/subjects.md`, 초상과 인물 얼굴의 설정 항목은 `references/spec.md` 참조
- 목록에 없는 피사체는 `references/extending.md`의 방법으로 새 모듈을 작성

## 범위

- 지원: 위 18개 피사체, 8개 화풍, 표정 8종, 개성(얼굴형, 눈매, 머리 모양과 색, 피부톤, 주근깨, 인물 시드), 내장 소품 5종(담배 포함), 손에 드는 물건 6종, 옷 무늬 3종, 날씨 3종, 설정을 통한 구성 변경, 피사체 합성 장면(인물 수 제한 없음), 손과 팔의 접촉(손잡기, 어깨동무, 기대기, 맞잡은 손), 측면 포옹과 입맞춤, 공유 소품(벤치, 탁자, 우산), 훅 모듈을 통한 소품 추가
- 미지원: 뒷모습과 앉은 자세의 3/4 회전, 정면 누운 자세, 앉거나 무릎 꿇은 측면 인물의 치마 주름 늘어뜨림(바지 권장), 사진 수준 묘사
    + 미지원 요청은 사용자에게 한계를 먼저 알리고 가능한 범위를 제안
- 내장 체형 표는 성인 비례(성인 체형과 얼굴 비례)
- 미성년자 기준
    + 18세 미만 인물의 노출과 성적 묘사는 그리지 않음
    + 판단 근거는 명시적 신호로 한정: 18세 미만 나이 설정, 미성년 학생 신분 설정, 이차성징 이전의 아동 체형 묘사
    + 동안 얼굴, 작은 키, 애니메풍 그림체는 성인에게도 흔한 특징이므로 그것만으로 미성년으로 판단하지 않음

## 의존성

- Python 3.9 이상, numpy, opencv-python
- 착수 전 `python -c "import numpy, cv2"`로 확인, 없으면 사용자 환경 규칙에 따라 설치
- 그 외 패키지와 외부 API 호출 없음

## 작업 절차

### 1. 기획

- 요청에서 피사체, 화풍, 구성 요소, 분위기를 뽑아 짧은 디자인 메모로 정리
    + 인물: 머리, 눈, 얼굴 인상, 의상, 자세, 배경
    + 장면: 구도, 광원 방향, 주조색, 주요 사물
- 화풍 선택 기준

| 화풍 | `--style` | 특징 | 어울리는 요청 |
|---|---|---|---|
| 애니메풍 | `anime` | 선화, 2단 셀 명암, 밝은 색 | 캐릭터, 배경 미술, 밝은 분위기 |
| 일러스트풍 | `illust` | 무선화, 입자 명암, 제한 팔레트, 종이 질감 | 포스터, 프로필, 감각적 분위기 |
| 회화풍 | `paint` | 연속 명암 후 붓질 재구성, 캔버스 질감 | 초상화, 정물, 고전적 분위기 |
| 수채화 | `watercolor` | 일러스트풍 바탕. 번지는 색 웅덩이, 진해지는 젖은 가장자리, 얼룩, 종이 결 | 풍경, 벚꽃, 서정적 분위기 |
| 연필 스케치 | `pencil` | 일러스트풍 바탕. 흑연 명암, 어두울수록 겹치는 해칭, 연필 윤곽선 | 습작, 크로키, 차분한 분위기 |
| 흑백 만화 | `manga` | 애니메풍 바탕. 먹, 망점, 굵은 먹선 | 만화 컷, 야경, 극적인 장면 |
| 픽셀 아트 | `pixel` | 애니메풍 바탕. 낮은 해상도 격자, 적은 색, 디더링, 외곽선 칸 | 게임풍, 레트로 분위기 |
| 두머 감성 | `doomer` | 애니메풍 바탕. 빠진 색과 차가운 청회색 계조, 나트륨 주황 불빛만 남김, 눌린 암부, 빛 번짐, 필름 입자, 비네트 | 판넬 단지, 겨울밤, 외로운 인물(이 스킬의 대표 감성) |

- 사용자가 화풍을 지정하지 않으면 피사체 표의 권장 화풍 중 1종을 고르고 선택 이유를 한 줄로 알림

### 2. 설정 작성

- 기본값과 다른 항목만 담은 JSON 파일 작성
    + 병합 순서: `assets/spec_default.json`(인물 계열만), `assets/style_<화풍>.json`, `assets/subject_<피사체>.json`, `assets/sex_<성별>.json`(`sex` 지정 시), 사용자 설정
- 남성은 `"sex": "male"` 한 줄로 얼굴, 짧은 머리, 체형, 의상, 색이 함께 바뀜
- 표정은 `"expression": "laugh"` 한 단어, 생김새는 `look`(얼굴형, 눈매, 머리 모양, 머리색, 눈색, 피부톤, 주근깨, 인물 시드)
    + 같은 화풍 안에서 여러 인물을 다르게 보이게 할 때는 `look.identity`에 서로 다른 정수
- 소품은 `accessories`(안경, 모자, 목도리, 가방, 담배), 옷 무늬는 팔레트 묶음의 `pattern`
- 색은 설정 안의 `style.palette`에 덮어쓰기

```json
{
  "pose": {"yaw_deg": 14, "mirror": true},
  "face": {"jaw_sharpness": 1.0, "jaw_width": 0.72},
  "hair": {"length": 1.55, "wave": 0.0},
  "style": {"palette": {"hair": {"base": "#8C3B2E", "shadow": "#5C211B", "light": "#E08A5B", "line": "#3A1410", "deep": "#3A1410"}}}
}
```

- 머리색을 바꿀 때는 `base`, `shadow`, `light`, `line`, `deep` 5개를 함께 지정하거나 `look.hair_color` 사용
    + 눈썹과 속눈썹은 머리색을 자동으로 따름

```json
{
  "expression": "smile",
  "look": {"face_shape": "round", "eye_shape": "big", "hair_style": "ponytail", "skin_tone": "tan", "freckles": 0.5, "identity": 12},
  "accessories": {"glasses": true, "hat": {"kind": "beanie", "pompom": true}, "scarf": true},
  "style": {"palette": {"scarf": {"pattern": {"kind": "check", "color": "#2F3A5A", "scale": 0.3}}}}
}
```
- 예제 설정(`assets/`)

| 파일 | 내용 |
|---|---|
| `example_spec_bob.json` | 단발 초상(안경 훅 `example_props_glasses.py`와 함께) |
| `example_spec_figure_study.json` | 여성 정면 인체 습작, 손을 허리에 얹은 콘트라포스토 |
| `example_spec_figure_back.json` | 여성 뒷모습 인체 습작 |
| `example_spec_figure_side.json` | 여성 측면 인체 습작, 허리 아치 |
| `example_spec_figure_seated_side.json`, `example_spec_figure_seated_front.json` | 여성 앉은 자세(측면, 정면) |
| `example_spec_portrait_male.json` | 남성 초상 |
| `example_spec_figure_male.json` | 남성 전신(티셔츠, 긴바지) |
| `example_spec_figure_male_figure_study.json` | 남성 정면 인체 습작, 골반 천 |
| `example_spec_figure_male_back.json`, `example_spec_figure_male_side.json` | 남성 뒷모습, 측면 인체 습작 |
| `example_spec_figure_male_seated_side.json`, `example_spec_figure_male_seated_front.json`, `example_spec_figure_male_seated_front_figure_study.json` | 남성 앉은 자세(측면 인체 습작, 정면 의상, 정면 인체 습작) |
| `example_spec_hand_male.json` | 남성 손(손등, 손바닥, 가리킴) |
| `example_spec_figure_shirt_skirt.json`, `example_spec_figure_coat.json` | 긴소매 셔츠와 치마, 그 위의 코트 |
| `example_spec_figure_male_jacket.json`, `example_spec_figure_male_shorts.json` | 남성 재킷, 반바지 |
| `example_spec_figure_hanbok.json`, `example_spec_figure_male_hanbok.json`, `example_spec_figure_side_hanbok.json` | 한복(여성, 남성, 측면) |
| `example_spec_figure_male_walk.json`, `example_spec_figure_front_walk.json` | 측면 걷기(먼 쪽 팔 포함), 관객 쪽으로 걸어오기 |
| `example_spec_figure_male_arms_crossed.json` | 팔짱 |
| `example_spec_figure_hands_behind_head.json`, `example_spec_figure_male_hands_behind_back.json` | 머리 뒤의 손, 등 뒤의 손 |
| `example_spec_figure_holding.json`, `example_spec_figure_side_holding.json` | 컵과 책 들기(정면), 컵 들기(측면) |
| `example_spec_scene_city_night.json` | 도시 야경 속 인물(지평선 눈높이, 색조) |
| `example_spec_scene_pair.json` | 풍경 속 두 인물 |
| `example_spec_portrait_city_bokeh.json` | 흐린 도시 야경을 배경으로 한 초상 |
| `example_spec_city_night.json` | 도시 야경 |
| `example_spec_desk_night.json` | 어두운 방의 책상(화면과 스탠드 조명) |
| `example_spec_portrait_laugh.json`, `example_spec_portrait_cry_rain.json` | 활짝 웃는 포니테일과 주근깨, 비 오는 밤거리에서 우는 초상 |
| `example_spec_portrait_glasses_beanie.json`, `example_spec_portrait_male_cap.json` | 안경, 방울 비니, 체크 목도리. 야구 모자를 쓰고 윙크하는 남성 |
| `example_spec_figure_hoodie.json`, `example_spec_figure_side_hoodie.json` | 후드티(정면과 측면), 모자, 가방, 안경 |
| `example_spec_figure_swimsuit.json`, `example_spec_figure_bikini.json`, `example_spec_figure_male_trunks.json` | 줄무늬 수영복, 물방울 비키니, 남성 수영 바지 |
| `example_spec_figure_patterns.json` | 줄무늬 셔츠, 체크 치마, 목도리 |
| `example_spec_cafe_night_rain.json`, `example_spec_room_snow.json` | 비 오는 밤의 카페, 눈 오는 날의 방(`--subject cafe`, `room`) |
| `example_spec_city_rain.json`, `example_spec_landscape_snow.json` | 비 오는 거리, 눈 내리는 호수(`--subject city`, `landscape`) |
| `example_spec_scene_cafe.json`, `example_spec_scene_room_night.json` | 비 오는 날 카페 속 인물, 밤의 방 속 인물 |
| `example_spec_figure_wave.json`, `example_spec_figure_peace.json` | 손 흔들기, 윙크하며 눈가에 V 사인(손 목표점, 손바닥, 얼굴 앞 손) |
| `example_spec_figure_male_stretch.json`, `example_spec_figure_thinking.json` | 기지개, 코트 차림으로 턱 괴기 |
| `example_spec_figure_three_quarter.json`, `example_spec_figure_male_three_quarter.json` | 3/4 비스듬한 전신(원피스, 남성 재킷) |
| `example_spec_figure_side_run.json`, `example_spec_figure_male_side_jump.json`, `example_spec_figure_side_crouch.json` | 측면 뛰기, 점프, 웅크려 앉기 |
| `example_spec_figure_lying_back.json`, `example_spec_figure_lying_front.json` | 누워서 무릎 세우기, 엎드려 팔꿈치 괴기 |
| `example_spec_scene_umbrella_rain.json` | 비 오는 거리, 남자가 든 우산을 함께 쓰고 팔에 손을 얹고 걸어오는 두 사람 |
| `example_spec_scene_cafe_date.json` | 카페 탁자에 마주 앉은 두 사람(턱 괴기, 컵 들기) |
| `example_spec_scene_beach.json`, `example_spec_scene_beach_lying.json` | 해변에서 손잡고 손 흔들기, 모래 위에 누운 인물 |
| `example_spec_scene_snow_night.json`, `example_spec_scene_bench.json` | 눈 오는 밤거리를 어깨동무하고 기대어 걸어오기, 호숫가 벤치에서 손잡기 |
| `example_spec_scene_embrace.json`, `example_spec_scene_embrace_bath.json`, `example_spec_figure_underwear.json` | 밤의 침실과 욕실에서 속옷 차림으로 포옹하고 입맞춤하는 두 사람(측면), 여성 속옷(정면) |
| `example_spec_bedroom_day.json`, `example_spec_bathroom_night.json` | 낮의 침실, 벽등을 켠 밤의 욕실(`--subject bedroom`, `bathroom`) |
| `example_spec_scene_friends_photo.json`, `example_spec_scene_toast_party.json` | 벚꽃길에서 어깨동무하고 V 사인하는 세 친구, 밤의 거실에서 와인잔을 드는 네 사람 |
| `example_spec_scene_dance_rooftop.json`, `example_spec_scene_selfie_fireworks.json` | 노을 옥상에서 손을 맞잡고 도는 커플, 불꽃놀이 강변의 셀카 |
| `example_spec_scene_look_back.json`, `example_spec_scene_lean_wall.json` | 벚꽃길에서 어깨 너머 돌아보기, 밤거리 기둥에 기대어 서기 |
| `example_spec_scene_cross_legs.json`, `example_spec_scene_picnic_kneel.json` | 카페에서 다리 꼬고 앉기, 공원 돗자리에 무릎 꿇고 앉기 |
| `example_spec_scene_doomer_man.json`, `example_spec_scene_doomer_woman.json` | 두머 남성(비니, 후드티, 입에 문 담배), 두머 여성(단발, 검은 후드, 손에 든 담배). 눈 오는 단지 마당 |
| `example_spec_scene_doomer_pair.json`, `example_spec_scene_doomer_world.json` | 불 켜진 아파트를 바라보는 두 사람의 뒷모습, 넓은 단지 마당에 홀로 선 인물(세계관 설정샷) |
| `example_spec_panelka_street.json`, `example_spec_still_life_kitchen_night.json` | 판넬 아파트 사이 눈 내리는 밤길(`--subject panelka`), 밤의 부엌 식탁(재떨이, 유리잔 홍차, 캔, 창밖 아파트, `--subject still_life`) |

### 3. 렌더링

```bash
cd <스킬 폴더>/scripts
python render.py --subject portrait --style anime --spec <설정>.json --out <출력>.png --stages <단계 폴더>
```

- `--subject` 생략 시 `portrait`
- `--stages`는 공정 단계 이미지 4장을 추가 저장
    + `1_sketch`(밑그림), `2_flat`(밑색), `3_shaded`(명암), `4_inked`(선화)
- `--extras <파일>.py`는 소품 추가용 훅 모듈
- 소요 시간(CPU 2코어 실측): 애니메풍과 일러스트풍 3-10초, 회화풍 12-20초, 새 매체 화풍 4종은 바탕 화풍과 비슷(마감 1-2초). 두 인물 장면은 약 2배, 네 인물 장면은 약 4배, `--stages` 사용 시 약 2배

### 4. 검수

- 결과 PNG를 이미지로 직접 열어 확인, 핵심 부위는 확대해서 한 번 더 확인
    + 전체 1회, 얼굴이나 손 등 초점 부위 크롭 1회가 최소 기준
- 검수 항목
    + 비례: 이목구비 간격, 머리와 몸의 비율, 팔다리 길이
    + 가림: 앞머리와 눈, 팔과 몸통, 사물 간 앞뒤 관계
    + 입체: 광원 방향과 그림자 방향의 일치, 덩어리감
    + 색: 주요 요소가 서로 구분되는지
    + 결함: 끊긴 선, 뜬 조각, 이음매 줄, 의도하지 않은 얼룩
- 결함이 보이면 원인 단계를 `--stages` 이미지로 좁힌 뒤 해당 설정값만 수정
    + 형태 문제는 `1_sketch`, 색 문제는 `2_flat`, 명암 문제는 `3_shaded`에서 확인

### 5. 수정 반복과 전달

- 설정 수정 후 재렌더링, 검수 통과까지 반복
- 최종 PNG와 사용한 설정 JSON을 함께 전달
    + 같은 설정과 `seed`는 같은 그림을 재현
- 사용자가 공정을 궁금해하면 단계 이미지도 함께 전달

## 자주 쓰는 조정

| 원하는 변화 | 설정 |
|---|---|
| 턱을 더 날카롭게 | `face.jaw_sharpness` 1.0, `face.jaw_width` 0.70, `face.chin_width` 0.10 |
| 눈매를 올리기 | `eyes.tilt` 0.13, `eyes.brow_slant` 0.9 |
| 온화한 표정 | `mouth.smile` 0.035, `eyes.brow_slant` 0.4 |
| 단발, 웨이브 | `hair.length` 1.5, `hair.wave` 0.06 |
| 반대 방향 보기 | `pose.mirror` true |
| 체형 | `figure.shape`의 `shoulders`, `bust`, `waist`, `hips`, `thighs`, `legs` 배율(1.0 기준) |
| 뒷모습, 측면 | `figure.view` "back" 또는 "side" |
| 남성 | `sex` "male" |
| 앉은 자세(측면) | `figure.profile_pose.seat` true, 허벅지 `thigh` 84 전후 |
| 앉은 자세(정면) | `figure.seat`, 다리 `foreshorten` [0.34, 1.0]과 `toward` [1, 0] |
| 의상 바꾸기 | `figure.clothes`에 `shirt`, `pants`, `skirt`, `dress`, `jacket`, `coat`, `jeogori`, `chima`, `baji`를 조합. 끌 때는 null |
| 긴소매, 반바지 | `shirt.sleeve` 1.9, `pants.length` 0.42 |
| 팔짱 | 팔 `fore` -92 전후, 위에 오는 팔 `"over": true`, 아래 손 `"tucked"` |
| 손을 몸 뒤로 | 해당 아래팔 `toward` [0, -1] |
| 물건 들기 | `figure.holds` {"right": {"kind": "cup"}}, 손 자세 `"grip"` |
| 배경과 다인물 | `backdrop` {"subject": "city", "place": "horizon"}, `companions` [인물 설정] |
| 머리 대 몸 비율 | `figure.body_scale` (0.9는 6.8등신, 1.0은 7.4등신, 1.05는 7.7등신) |
| 자세 | `figure.pose`의 팔다리 각도, `shoulder_tilt`, `pelvis_tilt` |
| 정물, 책상 구성 | `objects` 목록에 사물 추가, 삭제, 이동 |
| 도시 야경 | `night.on` true |
| 손바닥 보이기 | `hands` 항목의 `view` "palm" |
| 다른 거리, 다른 산세 | `seed` 변경 |
| 극적인 조명 | `light` [-0.8, -0.3, 0.5] |
| 표정 | `expression` "smile", "laugh", "sad", "cry", "surprise", "angry", "wink", "kiss". 약하게는 {"name": "smile", "amount": 0.5} |
| 얼굴형, 눈매 | `look.face_shape` "round", "long", "square", "heart". `look.eye_shape` "big", "narrow", "droopy", "cat" |
| 머리 모양 | `look.hair_style` "ponytail", "bun", "curly", "bob", "short" |
| 피부톤, 머리색, 눈색 | `look.skin_tone` "fair"에서 "dark"까지 6단계, `look.hair_color`, `look.eye_color` |
| 주근깨, 점 | `look.freckles` 0.6, `look.moles` [[0.35, 0.55]] |
| 다른 사람처럼 | `look.identity` 정수 변경 |
| 후드티, 수영복, 속옷 | `figure.clothes`에 `hoodie`, `swimsuit`, `bikini`, `trunks`, `underwear`(true면 기본값. 속옷은 여성 브라와 팬티, 남성 드로즈) |
| 옷 무늬 | `style.palette.<묶음>.pattern` {"kind": "stripes", "check", "dots", "color", "scale"} |
| 안경, 모자, 목도리, 가방 | `accessories` {"glasses": true, "hat": {"kind": "cap"}, "scarf": true, "bag": true} |
| 실내 배경 | `backdrop` {"subject": "cafe", "room", "bedroom", "bathroom", "place": "horizon"}. 밤은 배경 설정에 `time` "night" |
| 비, 눈 | `weather` {"kind": "rain"} 또는 {"kind": "snow"} |
| 손을 원하는 곳에 | 팔에 `reach` {"mark": "chin"} 또는 {"at": [x, y]}, `bend` "down", 얼굴 앞이면 `front` true |
| 손바닥 보이기(전신) | `hand_right_view` "palm", 손 `open` 또는 `peace` |
| 3/4 비스듬한 전신 | `figure.pose.turn` 30, `pose.yaw_deg` 22 |
| 관객 쪽으로 걸어오기 | `figure.pose.stride` {"lead": "left"}. 전신 구도는 `head_unit` 0.034-0.036 |
| 뛰기, 점프 | 측면 `profile_pose`에 다리 각도와 `lift`(체공 높이), 다리 `foot`(발끝 각도) |
| 누운 자세 | 측면 인물에 `figure.lying` {"face": "up" 또는 "down", "ground": 0.8} |
| 손잡기, 어깨동무 | 두 손 `reach`를 같은 `at` 지점으로. 상대 어깨는 {"mark": "shoulder_right", "of": "main"}과 동반 인물의 `lift`, `lift_under_head` true |
| 팔에 손 얹기 | 동반 인물 팔 `reach` {"mark": "elbow_right", "of": "main"}, `lift` 아래팔 |
| 기대기 | `roll_deg` 상대 쪽, `figure.neck_shift` 0.5-0.8, `pose.horizon_drop` |
| 포옹과 입맞춤 | 마주 선 측면 두 인물. 팔 `reach` {"mark": "upper_back" 또는 "lower_back", "of": 상대}, 상대 위로 오는 팔은 동반 인물의 `lift` ["arm_near"], `expression` "kiss" |
| 벤치, 카페 탁자 | 최상위 `props` [{"kind": "bench"}] 또는 [{"kind": "table", "elbow_of": "main"}] |
| 우산 | 주 인물 `figure.holds` {"right": {"kind": "umbrella"}}, 손 `grip`, 팔 `reach` {"at": 두 얼굴 사이}, `foreshorten` [1.0, 0.65], `front` true. 비가 우산 아래를 피함 |
| 와인잔, 휴대폰 | `figure.holds` {"left": {"kind": "glass"}} 또는 {"kind": "phone"}, 손 `grip` |
| 무릎 꿇고 앉기 | 측면 다리 `thigh` 70 `shin` -90 `foot` 172. 돗자리 장면은 배경 카메라 `eye_height` 100과 `horizon_drop` |
| 다리 꼬고 앉기 | 측면 `seat` true, 가까운 다리 `thigh` 94 `shin` 12, 먼 다리 `thigh` 84 `shin` -4 |
| 벽에 기대어 서기 | 측면 `profile_pose.wall` true, `lean` -6, 가까운 다리 `thigh` 36 `shin` -88 `foot` 88 |
| 어깨 너머 돌아보기 | 뒷모습 `figure.look_back` true(왼쪽은 {"side": "left"}). 옆얼굴이 어깨 너머로 보임 |
| 정면 인물의 팔 방향 | `arm_left`는 화면 왼쪽 팔. 가운데로 뻗는 팔은 왼쪽 인물 `arm_right`, 오른쪽 인물 `arm_left` |
| 벚꽃잎 | `weather` {"kind": "petals"} |
| 새 배경 | `backdrop` {"subject": "park", "sakura", "rooftop", "fireworks", "panelka", "place": "horizon"} |
| 두머 감성 | `--style doomer`. 배경은 `panelka`(밤) 또는 `outskirts`(해 질 녘), 날씨 `snow` |
| 담배 | 입에 물기 `accessories.cigarette` true, 손에 들기 `figure.holds` {"left": {"kind": "cigarette"}}, 정물 `ashtray` |

## 참조 문서

- `references/spec.md`: 초상과 인물 얼굴, 머리카락, 표정, 개성, 소품, 팔레트와 무늬 설정 전체 목록
- `references/subjects.md`: 전신(의상 포함), 장면 합성(여러 인물 포함), 손, 정물, 책상, 풍경, 도시, 공원과 벚꽃길, 옥상과 불꽃놀이, 판넬 단지와 외곽 들판, 카페와 방, 날씨의 설정 항목
- `references/pipeline.md`: 단계별 구현 원리와 화풍 차이(다른 매체 마감 포함). 결함 원인을 찾거나 화풍을 새로 만들 때 읽기
- `references/extending.md`: 훅 소품, 새 표정과 개성 프리셋, 새 머리 모양, 새 의상, 새 내장 소품, 새 실내 사물, 새 화풍, 손에 드는 새 물건, 새 자세, 새 피사체 추가 방법
