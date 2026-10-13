---
name: cel-glow-atelier
description: 이미지 생성 모델 없이 Python(numpy, OpenCV) 코드만으로 그림을 빚는 일러스트 작업실. 파라미터 리그가 형태를 잡고 광원 벡터 1개에서 마스크 연산으로 모든 명암을 뽑아, 경계가 또렷한 셀 음영, 에어브러시 그라데이션, 림라이트와 블룸의 빛 번짐, 머리카락 천사링을 지닌 애니메풍, 부드러운 일러스트풍, 붓 터치를 재구성한 유화풍 3가지 맛을 낸다. 남녀 흉상과 전신(정면, 반측면, 옆모습, 뒷모습, 앉기, 기대기, 손 제스처, 성별별 의상 20종, 머리 12종, 눈매와 코와 입 프리셋, 피부톤 6단계), 두 인물 투샷, 도시 거리와 야경, 눈과 안개 같은 날씨, 자연 풍경, 실내, 상자와 원기둥으로 만드는 사물, 정물까지 같은 광원 아래 한 장면으로 그린다. 참조 문서 6종은 process.md(작화 공정), portrait-spec.md(인물 spec 키), figure-spec.md(전신, 포즈, 의상, 투샷), scenery.md(풍경과 도시 연산), style-guide.md(팔레트와 광원 레시피), paintkit-api.md(저수준 그리기 API). 사용자가 "코드로 그림 그려줘", "일러스트 그려줘", "캐릭터 그려줘", "인물 일러스트", "전신 일러스트", "남자 캐릭터", "투샷", "커플 일러스트", "애니메풍", "일러스트풍", "유화풍", "풍경화", "도시 야경", "배경 그려줘", "정물화", "사물 그려줘", "procedural illustration" 등을 요청하거나 확산모델 없이 그림이 필요하면 반드시 이 스킬을 사용할 것. 차트, 다이어그램, 아이콘, 로고에는 사용하지 않음.
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and THIRD_PARTY_NOTICES.md
---

# Cel Glow Atelier

코드만으로 그림을 그리는 스킬. 확산모델 API와 3D 모델링을 쓰지 않음.

## 원리

- 좌표를 직접 타이핑하는 방식은 실패함
    + 언어모델은 픽셀 좌표 감각이 약함
    + 언어모델은 비례, 공정, 색 이론 지식이 강함
- 그래서 그림을 3개 결정으로 분리함
    + (형태) 파라미터와 제어점으로 결정, 곡선과 안티에일리어싱은 엔진이 처리
    + (명암) 광원 벡터 1개에서 마스크 연산으로 자동 산출
    + (화풍) 같은 형태에 렌더 설정과 후처리만 교체
- 렌더링 결과를 눈으로 확인하고 고치는 반복이 품질을 결정함

## 준비

- 필요한 패키지는 numpy와 OpenCV 2개
- 작업 전에 아래 명령으로 확인

```bash
python3 -c "import numpy, cv2; print(numpy.__version__, cv2.__version__)"
```

- 없으면 사용 중인 환경의 방식으로 `numpy`, `opencv-python-headless` 설치
- 모든 스크립트는 이 스킬 폴더의 `scripts/` 기준

## 경로 선택

| 요청 | 경로 | 방법 |
|---|---|---|
| 인물 흉상 (정면부터 약 35도 반측면까지) | A1. 흉상 리그 | spec JSON 작성 후 `scripts/render.py` 실행 |
| 전신, 상반신, 손 제스처, 인체 습작, 앉기, 기대기, 옆모습, 뒷모습 | A2. 전신 리그 | spec에 `figure` 키 추가 후 `scripts/render.py` 실행 |
| 두 인물 투샷 (커플, 손잡기, 팔짱, 어깨 감싸기, 마주 보기) | A2. 전신 리그 | spec에 `duo` 키 추가 |
| 배경 속 다른 사람들 | A2. 전신 리그 | spec에 `extras` 목록 추가 |
| 도시 거리, 산과 호수, 들판, 실내 (인물 없음) | A3. 장면 빌더 | spec에 `"subject": "none"`과 `background` 연산 목록 작성 |
| 두머 감성 (패널 아파트 단지, 전선, 가로등, 눈 내리는 밤) | A2, A3 | 도시 연산 + `finish.preset` `"doomer"` (아래 두머 절) |
| 인물 + 소품, 장신구, 추가 요소 | B. 혼합 | `scene.build` 후 레이어 추가, `scene.finish` 호출 |
| 컴퓨터, 가전, 가구 같은 각진 사물 | C1. 사물 빌더 | `paintkit.objects`의 상자, 원기둥으로 스크립트 작성 |
| 정물, 유기적 형태, 빌더에 없는 구도 | C2. 자유 장면 | `paintkit` 프리미티브로 스크립트 작성 |

- A1, A2, A3은 같은 spec 형식을 쓰며 서로 조합 가능 (예 : 전신 인물 + 도시 거리 배경 + 가까운 행인)
- 남성은 `character.gender`를 `"male"`로 지정, 얼굴, 머리, 체형, 손이 함께 바뀜
- 경로 A2 작업 전 `references/figure-spec.md` 필독
- 경로 A3 작업 전 `references/scenery.md` 필독
- 경로 B 예시 : `assets/examples/custom_addition_example.py` (목걸이, 머리핀 추가)
- 경로 C1 예시 : `assets/examples/desk_setup_example.py` (모니터, 노트북, 키보드가 놓인 책상)
- 경로 C2 예시 : `assets/examples/still_life_example.py` (화병 정물), `assets/examples/landscape_example.py` (저수준 풍경), `assets/examples/doomer_still_life_example.py` (밤 부엌 창가, 창밖 장면 연산과 담배 연기 재사용)
- 경로 C 작업 전 `references/paintkit-api.md` 필독

## 작업 순서

그림은 공정 순서대로 만들 때 실패가 줄어듦. 상세는 `references/process.md` 참조.

1. (기획) 요청에서 인물, 분위기, 화풍, 광원 방향, 인물별 의상을 확정
    + 의상은 각 인물의 성별에 맞는 목록에서 고름 (아래 전신 `outfit` 성별 구분)
    + 사용자가 의상 예시를 나열하면 예시마다 맞는 성별의 인물에게 배정하고 다른 성별에는 그 성별의 같은 상황 의상을 고름 (예 : 여성 비키니에는 남성 `trunks`, 여성 크롭티와 핫팬츠에는 남성 `open_shirt_shorts`)
    + 다른 성별의 의상은 사용자가 그 조합을 명시한 경우에만 입힘
    + 인물이 2명 이상이면 머리, 눈매, 피부톤을 인물마다 다르게 배정 (같은 그림의 인물이 같은 얼굴로 보이지 않게)
2. (디자인) 팔레트와 구도를 5-10줄 메모로 먼저 작성
    + 색을 코드 작성 중에 즉흥으로 고르면 조화가 깨짐
    + 팔레트 규칙은 `references/style-guide.md` 참조
3. (작성) `assets/examples/`의 spec 1개를 복사하여 수정
4. (렌더) 아래 명령 실행, 흉상은 약 10초, 전신은 약 15-30초 소요

```bash
python3 scripts/render.py my_spec.json out.png --stages stages.png
```

5. (검수) 결과 PNG를 직접 열어 눈으로 확인
    + 이미지를 볼 수 없는 환경이면 사용자에게 결과 확인을 요청
    + 아래 검수 항목으로 결함을 찾고 spec을 수정하여 재렌더
    + 얼굴은 확대하여 별도 확인 (눈, 턱선, 머리카락 경계)
6. (전달) 최종 PNG 전달, 요청 시 공정 시트(`--stages`)도 함께 전달

## spec 핵심

전체 키와 허용 범위는 `references/portrait-spec.md` 참조. 가장 자주 쓰는 키는 다음과 같음.

```json
{
  "canvas": [1200, 1500],
  "style": "anime",
  "character": {
    "gender": "female",
    "jaw_sharpness": 0.85,
    "head_turn": 0.65,
    "head_tilt": -5,
    "gaze": [-0.45, 0.0],
    "hair_style": "long_straight",
    "bangs": "side_swept",
    "outfit": "blazer"
  },
  "palette": {"hair": "#2b3050", "hair_shadow": "#16182a", "hair_light": "#9aa9dc", "iris": "#3f7fb5"},
  "light": {"azimuth": 135, "elevation": 42},
  "background": [{"type": "gradient", "top": "#b9c8e6", "bottom": "#e9eef7"}]
}
```

- `style` : `anime`, `illust`, `painterly` 중 1개
- `gender` : `female`, `male`. 남성은 생략한 키에 남성 기본값이 들어감
- `hair_style` 12종
    + (기존) `long_straight`, `long_wavy`, `bob`, `short`, `medium`, `slicked`, `layered`
    + (v13) `long_curly`(곱슬 롱), `layered_bob`(레이어드 단발), `two_block`(투블럭), `perm`(짧은 펌), `pixie`(픽시컷)
- `bangs` : `side_swept`, `see_through`, `parted`, `short_fringe`, `swept_back`, `layered`
- 남성 기본 머리는 `layered`(정수리 볼륨, 뾰족한 결, 눈썹을 스치는 앞머리)
- `outfit` : `vneck`, `turtleneck`, `blazer`, `offshoulder`(여성), `crewneck`, `shirt`, `suit`. 생략하면 여성 `vneck`, 남성 `shirt`
- 철자가 틀린 키는 오류로 중단되며 허용 키 목록이 출력됨

### 얼굴 프리셋과 피부톤

```json
"character": {"gender": "female", "hair_style": "long_curly", "skin_tone": "brown",
              "eye_shape": "almond", "brow_shape": "arched", "nose_shape": "default", "mouth_shape": "heart"}
```

- `skin_tone` : `fair`, `light`, `medium`, `tan`, `brown`, `deep` (밝은 톤에서 짙은 톤 순)
    + 피부, 피부 그림자, 홍조, 입술색이 함께 바뀜. `palette`에 직접 적은 색이 프리셋보다 우선
- `eye_shape` : `round`(둥근 눈), `almond`(아몬드형), `upturned`(올라간 눈), `droopy`(처진 눈), `monolid`(홑꺼풀)
- `brow_shape` : `straight`(일자), `arched`(아치형), `thick`(짙은 눈썹)
- `nose_shape` : `dot`(점 코), `bridge`(콧날 코)
- `mouth_shape` : `small`(작은 입), `heart`(도톰한 하트형 입술)
- 모두 생략하거나 `default`면 성별 기본 얼굴, 흉상과 전신의 정면, 옆모습, 뒷모습에 같은 키가 적용됨
- 투샷 상대(`duo.partner`)와 배경 인물(`extras`)의 `character`에도 같은 키를 씀
- 예시 : `face_curly_brown`, `male_two_block`(흉상), `figure_pixie_city`, `male_perm_park`(옆모습), `figure_bob_lake`(뒷모습), `duo_tones_night`(투샷)

### 전신과 장면

```json
{
  "canvas": [1100, 1800],
  "style": "anime",
  "character": {"head_turn": -0.55, "gaze": [0.4, 0], "hair_style": "long_straight"},
  "figure": {"pose": "contrapposto", "outfit": "sweater_pants", "build": {"waist": 0.96}, "ground_shadow": 0.5},
  "placement": {"head_height": 0.115, "pelvis": [0.5, 0.47]},
  "background": [
    {"type": "sky", "top": "#3b3f7a", "bottom": "#f4a57a", "horizon": 0.47},
    {"type": "street", "horizon": 0.47, "time": "dusk", "eye": 0.9, "seed": 7, "cars": 4, "people": 5}
  ]
}
```

- `pose` : `standing`, `contrapposto`, `akimbo`, `wave`, `clasped`, `peace`, `pinup`, `walk`, `sitting`, `sitting_crossed`, `three_quarter`, `lean`, `arms_crossed`(팔짱), `pockets`(주머니에 손), `stretch`(기지개)
- 옆모습 `pose` : `side_stand`, `side_walk`, `side_sit`, `side_wave`, `side_lounge`(소파), `side_lean`(기둥). `facing`으로 `right` 또는 `left` 지정
- 뒷모습 `pose` : `back_stand`, `back_walk`, `back_lookback`, `back_sit`. `look`으로 `away`(뒤통수), `left`, `right`(옆얼굴로 돌아봄), `left_3q`, `right_3q`(반측면으로 돌아봄) 지정
- 손 각도 : `pose_overrides`의 `hand_left_roll`(-90-90), `hand_left_pitch`(0-75)와 `right` 짝
    + 늘어뜨린 손이 납작해 보이면 `roll` 60-75로 엄지 쪽 옆면을 보여줌
    + 인사하는 손은 `pitch` 30-40으로 관객 쪽으로 기울임
- 전신 `outfit` 20종 (생략하면 여성 `dress`, 남성 `shirt_pants`)
    + (여성) `dress`, `blouse_skirt`, `bodycon`, `swimsuit`(별칭 `bikini`), `crop_hotpants`, `knit_dress`(니트 원피스), `tank_jeans`(민소매와 청바지)
    + (남성) `trunks`(수영 반바지), `open_shirt_shorts`(반소매 오픈 셔츠와 반바지)
    + (공용) `suit`(양복), `shirt_pants`, `tshirt_jeans`, `sweater_pants`, `hoodie_jeans`, `tank_shorts`(민소매와 트레이닝 반바지), `denim_jacket_chinos`, `leather_jacket_jeans`, `coat_turtleneck`(롱코트), `lingerie`(남성은 드로즈), `none`
    + 엔진은 spec에 적힌 의상을 성별과 무관하게 그대로 그림. 성별 맞춤은 spec을 쓰는 단계의 책임
    + 재킷과 코트 색은 `palette.outer`, 비우면 소재 색(데님 청색, 가죽 흑색, 코트 카멜)
- `build` : 체형 배율 (`bust`, `waist`, `hips`, `shoulders`, `legs`, `muscle`), 1.0이 기본
- `heels` : true면 하이힐
- `furniture` : `stool`, `chair`, `sofa`, `pillar`, `bed`, `none`. 앉은 포즈는 `stool`, `lean`은 `pillar`가 기본. `bed`는 정면 앉은 포즈 전용, 옆모습은 `bed`를 뺀 5종, 뒷모습은 `stool`, `chair`, `none`
- 팔은 손목 목표점(`reach_left`, `reach_right`)으로 지정하는 편이 쉬움
- 구도는 `placement.shot`이 가장 쉬움 : `full`, `thigh`, `knee`, `waist`, `bust` 중 1개와 가로 위치 `x`
    + 직접 지정은 `placement.head_height`와 `pelvis` : 0.115 전신, 0.20 무릎 위, 0.30 상반신
    + 더치 앵글은 `finish.tilt` 3-8도
- 인물이 서 있는 거리 장면은 `street.horizon`을 골반 높이에 맞추고 `eye` 0.9 사용 (원근 일치)
- `street`의 `cars`, `people`로 먼 차량과 행인을 추가
- 가까운 사람은 최상위 `extras`에 인물을 넣고 `"at": [x, z]` 미터로 거리 위에 배치
- `outfit` `none`은 의상 없는 인체. 엔진에 성기와 여성 유두 형태가 없어 그려지지 않음 (`lingerie`, `swimsuit`, 상의 없는 `trunks`도 같음)
- 실내 배경은 `{"type": "room", "window": "night", "lamp": [0.88, 0.48]}`처럼 `room` 연산 1개로 그림
- 모자는 `character.hat` `"beanie"`(비니), 색은 `palette.hat`. 정면, 반측면, 옆모습, 뒷모습 모두 지원
- 담배는 `figure.cigarette` : `left`, `right`(검지와 중지 사이), `mouth`(입꼬리). 연기는 자동으로 올라감
    + 주머니에 넣은 손(`pocket`, `tucked`)에 담배를 쥐게 하면 오류로 중단됨
    + 뒤통수만 보이는 뒷모습(`look` `away`)의 `mouth`는 그리지 않음

### 투샷

```json
{
  "canvas": [1400, 1600],
  "character": {"gender": "female", "hair_style": "long_wavy"},
  "figure": {"pose": "standing", "outfit": "dress", "heels": true, "ground_shadow": 0.45},
  "duo": {
    "pose": "arm_in_arm",
    "partner": {
      "character": {"gender": "male"},
      "figure": {"pose": "standing", "outfit": "suit"}
    }
  },
  "placement": {"shot": "full"}
}
```

- `duo.pose` : `side_by_side`, `hold_hands`, `arm_in_arm`, `arm_around`, `face_to_face`
- 상대는 `side`(기본 `right`) 쪽에 서고 실제 키 비율로 크기가 맞춰지며 두 사람의 발이 같은 바닥에 놓임
- 접촉하는 손의 위치와 시선은 자동으로 들어감, 상세는 `references/figure-spec.md`의 투샷 절

### 두머 감성

```json
{
  "style": "anime",
  "character": {"gender": "male", "hat": "beanie"},
  "palette": {"cloth": "#24242a", "cloth2": "#2e323c"},
  "figure": {"pose": "pockets", "outfit": "hoodie_jeans", "cigarette": "mouth"},
  "background": [
    {"type": "sky", "top": "#141a28", "bottom": "#3a3446"},
    {"type": "ground", "top": 0.8, "color": "#b9bec8"},
    {"type": "panel_blocks", "time": "night", "blocks": [{"x": [0.1, 0.9], "base": 0.82, "top": 0.2}]},
    {"type": "power_lines", "kind": "wood"},
    {"type": "streetlamp", "base": [0.75, 0.86], "height": 0.5},
    {"type": "snow", "count": 500}
  ],
  "finish": {"preset": "doomer"}
}
```

- 도시 연산 6종 : `panel_blocks`(판형 아파트), `power_lines`(전신주, 송전탑), `streetlamp`, `snow`, `fog`, `bare_tree`(잎 진 나무, 자작나무)
- `finish.preset` `"doomer"` : 채도 하향, 남회색 그림자, 나트륨 주황 하이라이트, 비네트, 필름 그레인. spec의 `finish` 키가 프리셋보다 우선
- 따뜻한 색은 창 불빛, 가로등, 담뱃불에만 두고 나머지는 회청색과 먹색으로 칠함
- `ground`는 `panel_blocks`보다 먼저 둠, 블록의 `base`가 지면선 아래로 묻혀야 땅에 선 것으로 보임
- 예시 7종 : `doomer_male`, `doomer_female`, `doomer_duo`, `doomer_establishing`(설정샷), `doomer_city`, `doomer_landscape`(json), `doomer_still_life_example.py`(사물화)
- 세부 연산 키는 `references/scenery.md`의 도시 연산 절, 색 레시피는 `references/style-guide.md`의 두머 절

### 생동감을 만드는 3개 키

- `head_turn` : 얼굴을 좌우로 돌림, 0이면 정면 증명사진처럼 보임. 1.0은 14도, 1.5-2.5는 반측면(21-35도)
- `head_tilt` : 고개 기울임, 3-6도가 자연스러움
- `gaze` : 눈동자 방향, 고개를 돌린 반대쪽으로 주면 관객을 바라봄

## 화풍

| 화풍 | 렌더 특징 | 후처리 |
|---|---|---|
| `anime` | 경계가 선명한 2단 음영, 색선, 머리 하이라이트 띠 | 확산 글로우, 블룸, 약한 그레인 |
| `illust` | 부드러운 그라데이션 음영, 가는 선, 림라이트, 도톰한 입술 | 글로우, 블룸, 비네트, 색 보정 |
| `painterly` | 선 없음, 넓고 부드러운 명암 | 붓 터치 재구성(큰 붓에서 작은 붓 순), 캔버스 결 |

- 화풍별 세부 조정은 `style_overrides`와 `finish` 키 사용
- 회화풍은 눈 크기를 줄이고 입술을 키우면 설득력이 올라감 (`eye_height` 0.078, `lip_fullness` 1.3)

## 검수 항목

- (얼굴) 눈 2개의 크기와 높이가 의도와 일치하는가
- (얼굴) 턱선이 매끈한가, 꺾이거나 울퉁불퉁한 곳이 없는가
- (얼굴) 한 그림 속 인물들의 머리, 눈매, 피부톤이 서로 구별되는가
- (머리) 이마와 관자놀이에 피부색 틈이 없는가
- (머리) 앞머리가 눈을 과하게 가리지 않는가
- (명암) 그림자가 모두 광원 반대쪽에 있는가
- (색) 배경이 인물보다 대비가 낮은가, 인물이 배경에 묻히지 않는가
- (전신) 손이 의도한 위치에 닿았는가, 팔꿈치가 몸을 뚫지 않는가
- (전신) 발이 바닥선과 그림자 위에 놓였는가, 배경의 지평선과 인물 크기가 맞는가
- (전신) 허리, 골반, 가슴의 굴곡이 의도한 체형으로 읽히는가
- (전신) 남성은 어깨가 골반보다 넓은 역삼각형으로 읽히는가, 가슴 근육이 넓고 평평한가
- (전신) 앉은 인물의 엉덩이가 앉는 면 위에 있는가, 기댄 어깨가 기둥에 닿는가
- (옆모습) 코와 턱끝이 진행 방향을 향하는가, 먼 쪽 팔다리가 몸 뒤에 있는가
- (뒷모습) 뒤통수와 목덜미가 자연스럽게 이어지는가, 돌아본 얼굴이 어깨 위에 놓였는가
- (반측면) 먼 쪽 눈이 볼 윤곽 안에 있는가, 가까운 쪽 귀 뒤로 뒷머리가 이어지는가
- (투샷) 맞잡은 손과 팔짱 낀 팔이 실제로 닿았는가, 두 사람의 발이 같은 바닥선에 있는가, 키 차이가 자연스러운가
- (의상) 각 인물의 의상이 그 성별의 목록에서 나왔는가, 사용자가 요청하지 않은 다른 성별 의상이 없는가
- (의상) 주머니에 넣은 손의 소매와 손목이 주머니 위치에서 끝나는가, 레이스와 데님 결이 의상 안에만 있는가
- (손) 손가락이 서로 엉키지 않는가, 손바닥과 손등의 방향이 의도와 맞는가
- (사물) 모든 물체가 같은 방향에서 빛을 받는가, 바닥 그림자가 물체에 붙어 있는가
- (두머) 따뜻한 색이 창 불빛, 가로등, 담뱃불에만 있는가, 비니 위로 머리카락이 삐져나오지 않는가
- (두머) 담배가 손가락 사이나 입꼬리에 붙어 있는가, 연기가 담뱃불에서 시작하는가, 전선이 먼 기둥에서 끝나는가
- (구도) 머리 위 여백과 좌우 균형이 적절한가
- (마감) 가장자리에 줄, 점, 빈 영역 같은 결함이 없는가

## 흔한 문제와 처방

| 증상 | 처방 |
|---|---|
| 인형처럼 놀란 눈 | `eyelid_open` 0.85-0.92, `iris_scale` 0.95 |
| 얼굴이 넓적함 | `jaw_sharpness` 상향, `face_width` 0.95 |
| 정면이라 밋밋함 | `head_turn` 0.5-0.8, `head_tilt` 3-6, `gaze` 반대 방향 |
| 머리카락이 한 덩어리 | `hair`와 `hair_shadow` 명도 차이 확대, `hair_light` 지정 |
| 인물이 배경에 묻힘 | 배경 채도와 대비 하향, `style_overrides.rim_light` 0.6 이상 |
| 회화풍 얼굴이 뭉개짐 | `finish.radii` 마지막 값을 2로, 캔버스 해상도 상향 |
| 색이 탁함 | 그림자색의 색상을 붉은 쪽이나 보라 쪽으로 옮기고 채도를 올림 |
| 팔이 어색하게 꺾임 | `reach_*` 목표점 조정, 반대 해가 필요하면 `elbow_*` -1 |
| 얼굴 근처 손의 팔꿈치가 옆으로 튀어나옴 | `arm_*_scale`을 [0.45, 0.65]로 줄여 팔이 앞으로 나온 것으로 표현 |
| 전신에서 얼굴이 뭉개짐 | `head_height` 상향(무릎 위 구도), 캔버스 세로 1800 이상 |
| 인물이 거리에 떠 있음 | `ground_shadow` 0.4 이상, `street.horizon`을 `pelvis` y와 일치 |
| 몸매가 밋밋함 | `build`의 `waist` 0.95, `hips` 1.05, `bust` 1.08, 포즈를 `contrapposto`나 `pinup`으로 |
| 팔이 일자로 뻣뻣함 | `reach_*` 목표점을 몸 쪽으로 당겨 팔꿈치가 굽게 함 |
| 거리가 비어 보임 | `street`에 `cars` 3-6, `people` 5-10 |
| 사물이 공중에 떠 보임 | `stage.ground_shadow`로 바닥 그림자 추가 |
| 남성이 소년처럼 보임 | `jaw_sharpness` 0.85-0.9, `eye_height` 0.060-0.065, `hair_style`과 `bangs`를 `layered`로 |
| 남성 얼굴이 밋밋함 | `head_turn` 0.4 이상과 반대쪽 `gaze`, `smile` 0.1-0.35, 이마가 넓으면 `slicked` 대신 `layered` |
| 늘어뜨린 손이 납작함 | `hand_*_roll` 60-75 |
| 뒷모습이 단조로움 | `back_lookback`으로 어깨 너머 돌아보기, 관객과 눈을 맞추려면 `look` `right_3q`, 몸에 붙는 의상, 측광(`azimuth` 120-140) |
| 반측면 얼굴의 먼 쪽 눈이 가려짐 | `head_turn`을 2.0 이하로 낮춤, 먼 쪽 앞머리가 짧은 `bangs` 선택 |
| 반측면 턱이 뾰족하게 튀어나와 보임 | `jaw_sharpness`를 0.6-0.75로 낮춤 (먼 쪽 볼 곡선이 둥글어짐), `chin_length` 0.95 |
| 남성 체형이 가늘어 보임 | `build`의 `muscle` 1.2-1.3, `shoulders` 1.05 |
| 배경 인물이 화면 밖으로 나감 | `at`의 x를 줄이거나 z를 늘림 (`figure-spec.md`의 배경 인물 절) |
| 소파가 잘림 | 캔버스 가로를 1600 이상으로, 소파 폭은 약 6 머리 |
| 투샷에서 손이 닿지 않거나 겹침 | `duo.gap`을 0.1-0.2씩 조정 (팔짱 1.3-1.5, 손잡기 1.85-2.1) |
| 허리에 얹은 손이 골반 앞을 덮음 (허벅지 위 구도) | `pose_overrides`에 `reach_left` [-0.68, -0.34], `reach_right` [0.68, -0.34], `hand_*_pitch` 55 |
| 역광에서 얼굴 절반이 어두움 | `style_overrides.face_shadow_level` -0.3 |
| 회화풍 얼굴의 눈이 둥둥 뜸 | `eye_height` 0.078, `lip_fullness` 1.3 |
| 투샷의 한 사람이 화면 밖으로 나감 | `placement.shot` 사용, 캔버스 가로를 1400 이상으로 |
| 주머니에 넣은 손이 보임 | 주머니 있는 의상으로 변경 (`bodycon`, `knit_dress`, `swimsuit`, `trunks`, `lingerie`는 주머니 없음) |
| 남성에게 원피스나 비키니가 입혀짐 | `figure.outfit`을 남성 또는 공용 의상으로 지정 (생략 시 남성은 `shirt_pants`) |
| 열린 재킷 안이 어두워 묻힘 | 안에 입은 옷 `cloth`를 재킷 `outer`보다 밝게 |
| 머리 위로 든 손이 잘림 | `head_height` 대신 `placement.shot` 사용 (손끝까지 자동 포함) |
| 침대가 잘림 | 캔버스 가로를 세로보다 길게, `"shot": "full"`과 `"x": 0.42` |
| 인물들이 같은 얼굴로 보임 | 인물마다 `hair_style`, `eye_shape`, `brow_shape`, `skin_tone`을 다르게 지정 |
| 곱슬머리 질감이 안 보임 | `hair_light`를 머리색보다 확실히 밝게 (명도 차 40% 이상) |
| 아파트 블록이 공중에 뜨거나 지면에 덮임 | `ground`를 `panel_blocks` 앞에 두고 블록 `base`를 지면선보다 아래로 |
| 두머 풍경이 뿌옇게 씻겨 보임 | 하늘 `top`을 어둡게, `tree_line`을 진하게, `fog` `opacity` 0.3 이하 |
| 눈밭에서 자작나무가 묻힘 | 가까운 나무는 `birch` false와 어두운 `color`, 자작나무는 어두운 숲 앞에 배치 |
| 담배 든 손이 주머니 오류로 중단됨 | 담배를 반대 손이나 `mouth`로, 또는 손을 꺼내는 포즈로 변경 |
| 블록 측면 벽이 꼬여 보임 | `side`를 줄이거나 `vanish`를 블록에서 멀리 둠 (측면 폭은 정면 폭의 0.8까지만 그려짐) |

## 미성년자 보호

- 미성년자에게는 아래 3가지를 그리지 않음
    + 누드 (`outfit` `none`, 여성의 상의 없는 `trunks`)
    + 속옷 차림 (`lingerie`)과 `pinup` 포즈
    + 성행위
- 손잡기, 포옹, 입맞춤 같은 애정 표현과 일상적인 수영복 차림은 해당하지 않음
- 미성년자 판단은 명시적 신호로만 함
    + 요청이나 설정에서 18세 미만으로 명시된 인물
    + 이차성징 이전의 아동 체형을 묘사하도록 요구한 경우
- 화풍(큰 눈, 동안), 작은 키, 마른 체형처럼 나이를 암시하는 요소만으로는 미성년자로 판단하지 않음

## 한계

- 흉상의 얼굴 회전은 약 35도(반측면)까지이며 완전 측면과 뒷모습은 전신 리그에서만 지원
- 전신 정면 리그의 몸통 회전은 약 30도까지 자연스러움
- 옆모습 리그는 서기, 걷기, 앉기, 인사, 소파에 기대 앉기, 기둥에 기대 서기 6종
- 뒷모습 리그는 서기, 걷기, 돌아보기, 앉기 4종이며 뒷모습 소파는 등받이가 몸을 가리므로 지원하지 않음
- 반측면 돌아보기는 몸은 뒷모습 그대로 두고 얼굴만 돌리는 애니메식 표현임
- 앉은 자세는 정면 2종, 옆모습 2종, 뒷모습 1종이며 눕기, 달리기, 웅크리기는 지원하지 않음
- 전신 의상은 20종이며 한복, 웨딩드레스, 패딩처럼 목록 밖 의상은 경로 B로 직접 그려야 함
- 흉상 의상은 7종이며 전신 신규 의상(재킷, 코트, 민소매)의 흉상판은 없음
- 모자는 비니 1종, 손에 드는 소품은 담배 1종이며 그 밖의 모자와 소품은 경로 B로 직접 그려야 함
- 묶음 머리(포니테일, 올림머리, 양갈래, 땋은 머리)는 지원하지 않음
- 체형은 `build` 배율로만 조정하며 체형 프리셋은 없음
- 판형 아파트는 직육면체 블록(정면과 측면 1면)이며 곡면 건물은 지원하지 않음
- 배경 인물(`extras`)은 주인공 뒤에만 놓이며 접촉 연출은 `duo`로만 가능
- 투샷은 2명까지이며 접촉 포즈는 손잡기, 팔짱, 어깨 감싸기 3종. 포옹, 키스, 업기, 안기처럼 몸이 크게 겹치는 연출은 지원하지 않음
- 투샷의 접촉 포즈는 정면 리그 전용이며 `face_to_face`는 옆모습 2명으로 그림
- 침대는 가장자리에 앉은 정면 포즈만 지원하며 침대에 눕기는 지원하지 않음
- 인체는 굴곡과 주요 윤곽까지 표현하며 근육 세부는 없음
- 사물 빌더는 상자와 원기둥 조합이므로 곡면이 많은 사물은 단순화됨
- 거리의 차량과 행인은 먼 거리용 단순 형태임
- 손은 7개 제스처를 회전(`roll`)과 기울임(`pitch`)으로 돌려 그리며, 손을 아래에서 올려다보는 시점은 지원하지 않음
- 리그와 빌더 밖 요소는 경로 B 또는 C2로 직접 그려야 하며 난도가 높음
- 품질 수준은 깔끔한 2D 일러스트이며 확산모델의 사실 묘사와는 다른 영역
- 못 그리는 요청은 가능한 범위를 사용자에게 먼저 알림

## 참조 파일

| 파일 | 읽는 시점 |
|---|---|
| `references/process.md` | 공정별 판단 기준과 수정 요령이 필요할 때 |
| `references/portrait-spec.md` | spec의 전체 키, 범위, 머리와 얼굴 프리셋, 피부톤, 배경 종류를 확인할 때 |
| `references/figure-spec.md` | 전신, 남성 체형, 포즈, 가구, 옆모습, 뒷모습, 배경 인물, 투샷, 손 각도, 전신 의상, 구도 설정 시 |
| `references/scenery.md` | 도시, 풍경, 실내 장면, 두머 도시 연산, 인물과 배경의 원근을 맞출 때 |
| `references/style-guide.md` | 팔레트 설계, 장면별 광원 레시피, 두머 색 레시피, 화풍 미세 조정 시 |
| `references/paintkit-api.md` | 경로 B, C로 직접 그릴 때 (사물 빌더 `objects` 포함) |
| `assets/examples/*.json` | 시작 spec (여성 흉상 5종, 남성 흉상 4종, 전신 35종, 투샷 6종, 장면 7종) |
| `assets/examples/*.py` | 혼합 모드와 자유 장면 예시 코드 |
