---
name: polygon-cel
description: 다각형으로 빚고 셀로 칠하는 일러스트 스킬. 모든 형태는 확산모델 없이 수식이 계산한 다각형(두상 단위 비례, 3D 손 골격, 회전체 사물, 1점 투시 거리, 프랙털 산맥)으로 잡으므로 같은 JSON 스펙은 같은 그림을 재현한다. 기본 결은 진한 컬러 선화, 경계가 선명한 두 단계 셀 음영, 가장자리부터 둥글게 떨어지는 부피 음영, 차분한 저채도 팔레트이며 같은 장면을 소프트 일러스트(블룸과 난색 글레이즈), 유화(다중 크기 붓터치와 임파스토), 수채화(안료 고임, 번짐, 종이결)로도 마감한다. 그리는 대상은 젊은 성인 여성과 남성 인물(클로즈업부터 원경, 정면, 뒷모습, 옆모습, 걷기, 앉기, 눕기, 소품 쥐기, 투샷, 여러 줄 단체), 정물, 풍경, 도시 거리, 실내이며 일상복, 수영복, 운동복, 오피스룩, 드레스와 무드 프리셋을 지원한다. 스펙 필드와 허용값은 references/spec.md, 공정 원리와 결함 진단표는 references/process.md, 엔진 확장 레시피는 references/extending.md에 있다. 사용자가 '/polygon-cel', '코드로 그림 그려줘', '확산모델 없이 그려줘', '애니메풍 캐릭터', '인물 일러스트', '남자 캐릭터', '투샷', '커플 일러스트', '단체 일러스트', '뒷모습', '옆모습', '수영복 캐릭터', '오피스룩', '정물화', '풍경화', '도시 풍경', '밤거리 일러스트', '셀화풍', '수채화풍', '유화풍', 'draw an anime girl with code', 'still life with code' 등을 언급하거나 GPU와 이미지 생성 모델 없이 재현 가능한 그림이 필요할 때 반드시 이 스킬을 사용할 것.
license: GPL-3.0-or-later (전문은 LICENSE, 출력 이미지 추가 허가와 의존 라이브러리 고지는 THIRD_PARTY_NOTICES.md)
---

# polygon-cel

## 개요
- 그림 공정(기획, 구성, 형태, 선화, 채색, 화풍, 후보정)을 코드 모듈로 1:1 구현한 일러스트 엔진
- 모델 가중치 없이 numpy, OpenCV, skia-python만 사용
- 같은 스펙과 seed는 항상 같은 그림을 산출
- 작업자(사람 또는 LLM)의 역할은 장면 스펙 작성과 렌더 결과 검수
    + 형태 지식(비례, 얼굴, 헤어, 의상 구조)은 엔진에 내장
    + 공정별 원리는 references/process.md에 정리

## 범위
- 주제(subject): character(인물), still_life(정물화), landscape(풍경화), city(도시 거리), interior(실내)
- 인물: 젊은 성인 비례의 여성 또는 남성 템플릿
    + 시점(view): front(정면에서 약 35도 측면까지), back(뒷모습, 어깨 너머로 돌아봄), side(옆모습 프로필)
    + 구도: closeup(얼굴 클로즈업), bust(바스트업), waist(웨이스트업), full(전신), wide(장면 속 작은 전신 인물의 원경 설정샷)
    + 전신 자세: 서기 3종, walk(걷기), lean(벽에 기대기), sit(의자, 스툴, 침대에 앉기), lie(침대에 눕기)
    + 팔 포즈 11종: 기본 7종, 팔짱, 턱 괴기, 머리 넘기기, 머리 뒤 깍지
    + 손 제스처 6종
    + 손 소품(body.hold): 휴대폰, 캔음료, 담배를 한 손에 쥠 (정면 시점)
    + 체형: 여성 slim, balanced(기본), fuller, 남성 slim, balanced(기본), athletic
    + 남성 근육 강도: body.muscle 0-1 (기본 slim 0.10, balanced 0.30, athletic 0.50)
    + 가슴 크기: small, medium(기본), large, xlarge (여성)
    + 얼굴: 얼굴형 4종, 얼굴 길이, 코 3종, 입술 3종, 속눈썹 4단계, 홍채 크기, 눈썹 두께
    + 헤어: long, bob, ponytail, short
    + 상의 17종: 일상복 6종(니트, 셔츠, 후디, 크롭티, 탱크톱, 티셔츠), 수영복 5종(비키니, 원피스 수영복, 래시가드, 비치 셔츠, 상의 탈의), 운동복(스포츠 브라), 파티 드레스 3종(슬립 드레스, 홀터 드레스, 오프숄더 원피스), 홈웨어 2종(캐미솔, 오버사이즈 티)
    + 오피스룩: 셔츠에 넥타이(tie) 또는 리본(bow), 슬랙스 또는 펜슬 스커트 조합 (셔츠 자동 턱인)
    + 하의 11종: A라인 스커트, 펜슬 스커트, 청바지, 슬랙스, 레깅스, 조거 팬츠, 돌핀 쇼츠, 비키니 하의, 보드 쇼츠, 수영 브리프, 박서 브리프
    + 신발: 스니커즈, 부츠, 샌들, 하이힐, 구두, 맨발
    + `"gender": "male"` 1줄로 남성 얼굴, 헤어, 골격, 의상 기본값 일괄 적용
    + 노출 의상은 성인 체형과 해부학적으로 그럴듯한 피부 형태로 표현 (여성 가슴 볼륨, 남성 대흉근과 복근)
    + 가슴은 볼륨과 음영으로 표현하며 가슴 표시와 골반 세부 형태를 그리는 레이어는 엔진에 없음
    + 수영복과 속옷 하의의 앞판은 매끈한 면으로 렌더
    + 배경: 단색, 그라데이션, 하늘, 보케, 창가, 해변, 침대, 실내 5종, 풍경화 장면, 도시 거리 장면
    + 머리 소품: 헤어핀, 귀걸이, 비니, 몸 소품: 목걸이
- 투샷과 단체: characters에 인물 2명 이상 (인원, 성별 조합 제한 없음)
    + 구도: waist, full, wide
    + 접촉(2명 전용): 손잡기(hand_hold, 정면과 뒷모습), 어깨동무(shoulder_arm, 정면)
    + 3명 이상은 나란히 서기와 앉기, 고개는 무리 중심을 향함
    + 여러 줄(pair.rows): 뒷줄은 작고 높게 서서 앞줄 머리 사이로 얼굴이 보임
    + 인원이 늘면 캔버스 가로 폭 자동 확장, 4096px을 넘으면 인물 크기를 줄여 맞춤
    + 옆모습 2명은 자동으로 서로 마주 봄
    + 인물별 시점, 포즈, 의상, 키 배율(place.scale) 개별 지정
- 정물: 고전 사물 9종(화병, 병, 컵, 머그, 항아리, 과일 4종), 현대 사물 9종(노트북, 모니터, 키보드, 마우스, 스마트폰, 헤드폰, 스탠드 조명, 책, 화분)
- 실내: 침실, 사무실, 카페, 수영장, 헬스장 (단독 장면 또는 인물 배경)
- 화풍: anime_cel, soft_illust, painterly, watercolor (모든 주제 공통)
- 무드(mood): doomer 1종 (밤의 고독)
    + 차가운 탈색 색보정, 필름 입자, 비네트, 전선이 늘어진 밤거리 배경, 무표정과 지친 눈을 기본값으로 묶음
    + 풍경화와 도시화에도 적용 (밤 시간대, 달과 별, 전선)
- 미성년자의 노출과 성행위를 포함한 성적 묘사는 수행하지 않음
    + (명시된 미성년 설정) 18세 미만 연령이나 미성년 신분이 스펙 또는 요청에 명시된 인물
    + (아동 신체 묘사) 이차성징 이전의 아동 신체로 그리도록 요청된 인물
- 포토리얼은 범위 밖임을 먼저 안내

## 준비
- 스킬 폴더 기준 경로: `scripts/render.py`, `scripts/selftest.py`
- 작업 시작 시 설치 확인을 가장 먼저 실행
```bash
python scripts/selftest.py || pip install -r scripts/requirements.txt
```
- 실행 환경 정책상 필요하면 pip 옵션(가상환경, `--break-system-packages` 등)을 환경에 맞게 선택

## 작업 절차

### 1. 요청 해석과 디자인 브리프
- 렌더 전에 브리프 5줄을 작성하고 사용자에게 공유
    + (핵심 메시지) 그림이 전달할 분위기 1문장
    + (화풍) 선택 화풍과 선택 근거
    + (구도) 인물은 구도, 고개 방향(yaw), 포즈, 장면은 주제와 시간대, 사물 배치
    + (팔레트) 주조색 1개와 보조색
    + (조명) 주광 방향과 역광 유무
- 사용자가 정하지 않은 항목은 아래 기본 판단으로 채우고 브리프에 명시
    + 인물이 주인공인 요청은 bust, 손이나 의상이 중요하면 waist, 스타일링 전신 요청은 full
    + 손을 보여줄 요청은 wave, hand_on_hip 포즈, 손을 숨길 요청은 behind, pocket 포즈
    + 표정이 주인공인 요청은 closeup, 일상 장면은 실내 배경과 sit, lean 포즈, 휴식 장면은 lie 포즈
    + 뒷모습 요청은 view back과 head.yaw 25-35 (어깨 너머로 돌아보는 얼굴), 옆모습 요청은 view side
    + 두 사람 요청은 characters 2명, 친밀한 관계는 hand_hold 또는 shoulder_arm, 상반신 위주는 waist, 걷기와 스타일링은 full
    + 투샷 남성은 place.scale 1.06, 고개 방향은 생략(서로를 향하는 기본값)
    + 3명 이상 요청은 characters에 인원수만큼 나열, pair.contact는 생략
    + 남성 근육은 기본값 사용, 근육을 강조하는 요청에만 body.muscle 0.7-1.0
    + 쓸쓸한 밤, 두머 감성 요청은 mood doomer, 인물은 어두운 후디와 비니, 손에 휴대폰, 캔음료, 담배 중 1개
    + 장면이 주인공이고 인물이 작게 보여야 하는 설정샷은 framing wide와 place.x 0.3-0.4
    + 7명 이상 단체나 졸업 사진 같은 구도는 pair.rows 2
    + 앉은 모습이 잘 읽혀야 하면 view side와 pose sit, 클로즈업은 목둘레가 높은 상의
    + 화풍 미지정 시 인물은 anime_cel, 정물화와 풍경화는 painterly 또는 watercolor, 도시는 anime_cel
    + 색은 references/spec.md의 팔레트 구성 요령 적용
- 모호한 핵심 요소(화풍, 구도)가 결과를 크게 바꾸면 렌더 전에 1회 질문

### 2. 스펙 작성
- references/spec.md에서 필드와 허용값 확인
- assets/examples/ 예시 스펙을 출발점으로 복사해 수정
- 스펙 파일은 작업 폴더에 저장하여 재현 근거로 보존

### 3. 초안 렌더와 검수
```bash
python scripts/render.py spec.json -o draft.png --quality draft
```
- 렌더 결과 이미지를 직접 열어 검수 항목 확인
- 결함은 references/process.md의 결함 진단표로 원인 확인 후 스펙 수정
- 초안 반복은 3회 이내 권장

### 4. 최종 렌더와 전달
```bash
python scripts/render.py spec.json -o final.png --quality final
```
- final은 2배 해상도 렌더 후 축소하므로 선이 더 매끄러움 (소요 시간 약 3배)
- 전달물은 최종 PNG와 사용한 스펙 JSON
- 공정 확인이 필요하면 `--passes DIR`로 채색 패스, 선화 패스, 인물 마스크 저장

### 5. 스펙으로 표현할 수 없는 요청
- 새 의상, 헤어스타일, 배경, 화풍은 references/extending.md의 레시피로 엔진 확장
- 확장 전에 사용자에게 추가 범위와 예상 한계를 알리고 진행 여부 확인

## 검수 항목
- 얼굴: 좌우 눈 크기와 높이 균형, 홍채 하이라이트 방향이 광원과 일치
- 헤어: 앞머리 끝이 얼굴 윤곽을 어색하게 가르지 않음, 뒷머리가 판자처럼 보이지 않음
- 신체: 어깨와 목 연결, 소매와 몸판 경계선, 손가락이 엉키지 않음
- 남성: 칼라와 목둘레가 굵은 목에 맞음, 반바지가 두 다리로 분리, 정수리 다발이 가시처럼 튀지 않음
- 뒷모습: 손이 엉덩이 위에 놓이지 않음, 등 위 뒷머리가 어둡게 뭉치지 않음
- 옆모습: 가슴이 몸 실루엣과 이어짐, 앞머리 끝이 이마 앞에서 뾰족하게 끝남
- 투샷과 단체: 인물의 발이 같은 지면, 뒤 인물의 선이 앞 인물 위로 비치지 않음, 인물이 캔버스 가장자리에 닿지 않음
- 여러 줄 단체: 뒷줄 얼굴이 앞줄 머리 사이로 보임, 뒷줄이 앞줄보다 작음
- 손 소품: 쥔 물건이 손가락 아래로 들어가 쥔 형태로 읽힘, 캔과 휴대폰을 감싼 손가락이 물건 가장자리에서 둥근 관절로 끝남, 후디 끈이 쥔 손 위로 지나가지 않음, 담배 연기가 소매 위를 타지 않음
- 원경: 작은 인물의 머리, 손, 발이 장면에 묻히지 않음
- 투샷 접촉: 잡은 손이 두 인물 사이에서 만남, 어깨동무 팔뚝이 상대 목 뒤에서 나와 먼 쪽 어깨 위에 놓임
- 자세: 앉은 허벅지가 의자 위에 놓임, 누운 인물 전신이 캔버스 안에 들어옴, 올린 팔의 소매가 팔을 따라 이어짐
- 정물: 사물끼리 파묻히지 않음, 그림자 방향이 광원과 일치
- 실내와 현대 사물: 가구와 사물 윗면이 같은 시점 기울기, 화면 내용이 화면 틀 안에 위치
- 풍경과 도시: 원경이 근경보다 흐리고 밝음(공기 원근), 소실점 수렴
- 색: 주조색 1개, 배경이 주제보다 저대비
- 화풍: 유화의 얼굴 얼룩, 수채화의 종이 페이드 형태 확인, 밤 그림 수채화가 낮처럼 하얗게 뜨지 않음
- 캔버스: 주제 주변 여백 확보

## 요청에서 스펙으로 변환 예시
- 요청: "비 오는 오후, 창가에서 미소 짓는 단발 여성, 수채화"
```json
{"style": "watercolor", "framing": "bust",
 "character": {"head": {"yaw": -14, "roll": 3},
   "hair": {"color": "#3A2E30", "style": "bob", "bangs": "full"},
   "eyes": {"color": "#6B7FA8", "shape": "droopy"},
   "expression": {"mouth": "soft", "blush": 0.3, "eye_smile": 0.2},
   "outfit": {"type": "knit_sweater", "variant": "crew", "color": "#D9CFC2"}},
 "lighting": {"key": "upper_right"},
 "background": {"type": "window", "colors": ["#DDE3EA", "#B9C3CF", "#F2F5F8"]}}
```
- 요청: "가을 산책 전신, 오프숄더 원피스, 뒷짐, 부드러운 일러스트"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"head": {"yaw": 12}, "body": {"pose": "behind"},
   "hair": {"color": "#6B3F2E", "style": "long", "bangs": "parted", "wave": 0.4},
   "outfit": {"type": "offshoulder_dress", "color": "#B8866B", "shoes": "boots"},
   "accessories": ["necklace"]},
 "background": {"type": "gradient", "colors": ["#F6E3C8", "#D9B48F"]},
 "post": {"grade": "sunset"}}
```

- 요청: "손 흔들며 웃는 단발 여성, 셔츠, 웨이스트업"
```json
{"style": "anime_cel", "framing": "waist",
 "character": {"head": {"yaw": -12, "roll": 4}, "body": {"pose": "wave"},
   "expression": {"mouth": "open_smile", "eye_smile": 0.2},
   "hair": {"style": "bob", "bangs": "full"}, "outfit": {"type": "shirt", "bottom": "a_line_skirt"}},
 "background": {"type": "window"}}
```
- 요청: "해변에서 손 흔드는 비키니 여성, 전신"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"head": {"yaw": -10}, "body": {"pose": "wave", "stance": "contrapposto"},
   "expression": {"mouth": "open_smile"}, "hair": {"style": "ponytail", "bangs": "full"},
   "outfit": {"type": "bikini", "variant": "triangle", "bottom_style": "high_leg", "shoes": "sandals"}},
 "background": {"type": "beach"}}
```
- 요청: "해변에 선 근육질 남성, 보드 쇼츠, 전신"
```json
{"style": "anime_cel", "framing": "full",
 "character": {"gender": "male", "head": {"yaw": -10},
   "body": {"figure": "athletic", "stance": "contrapposto", "pose": "hand_on_hip"},
   "expression": {"mouth": "smile"}, "outfit": {"type": "shirtless", "bottom": "board_shorts"}},
 "background": {"type": "beach"}}
```
- 요청: "단발에 둥근 얼굴, 도톰한 입술, 짙은 속눈썹의 여성"
```json
{"style": "anime_cel", "framing": "bust",
 "character": {"face_shape": "round", "face": {"length": 0.94, "nose": "button", "lips": "full"},
   "eyes": {"shape": "round", "iris": 1.12, "lashes": "heavy"},
   "hair": {"style": "bob", "bangs": "full"}, "outfit": {"type": "shirt"}},
 "background": {"type": "bokeh"}}
```
- 요청: "밤거리에 서 있는 후디 차림 여성"
```json
{"style": "anime_cel", "framing": "waist",
 "character": {"head": {"yaw": -12}, "body": {"pose": "pocket"},
   "hair": {"style": "bob", "bangs": "full"}, "outfit": {"type": "hoodie", "color": "#B7A8D6"}},
 "background": {"type": "city", "city": {"time": "night"}}}
```
- 요청: "사무실 의자에 앉은 오피스룩 여성, 전신"
```json
{"style": "anime_cel", "framing": "full",
 "character": {"head": {"yaw": 10}, "body": {"pose": "sit", "bust": "large"},
   "outfit": {"type": "shirt", "variant": "bow", "bottom": "pencil_skirt"}},
 "background": {"type": "office"}}
```
- 요청: "해변에서 어깨 너머로 돌아보는 비키니 뒷모습"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"view": "back", "head": {"yaw": 32, "roll": -3},
   "body": {"figure": "fuller", "stance": "contrapposto"},
   "outfit": {"type": "bikini", "bottom_style": "high_leg"}},
 "background": {"type": "beach"}}
```
- 요청: "슬립 드레스 입은 여성 옆모습"
```json
{"style": "soft_illust", "framing": "full",
 "character": {"view": "side", "body": {"figure": "fuller", "bust": "large"}, "outfit": {"type": "slip_dress"}},
 "background": {"type": "gradient"}}
```
- 요청: "노을 진 거리에서 손잡은 커플, 전신"
```json
{"style": "soft_illust", "framing": "full", "pair": {"contact": "hand_hold"},
 "characters": [
   {"hair": {"style": "long", "wave": 0.3}, "outfit": {"type": "offshoulder_dress", "shoes": "heels"}},
   {"gender": "male", "place": {"scale": 1.06}, "outfit": {"type": "shirt", "bottom": "slacks"}}],
 "background": {"type": "city", "city": {"time": "dusk"}}}
```
- 요청: "헬스장에서 어깨동무한 남자 둘"
```json
{"style": "anime_cel", "framing": "full", "pair": {"contact": "shoulder_arm", "lead": 1},
 "characters": [
   {"gender": "male", "outfit": {"type": "tank_top", "bottom": "joggers", "shoes": "sneakers"}},
   {"gender": "male", "body": {"figure": "athletic", "pose": "hand_on_hip"},
    "outfit": {"type": "tee", "bottom": "joggers", "shoes": "sneakers"}}],
 "background": {"type": "gym"}}
```
- 요청: "밤거리에서 마주 보는 남녀 옆모습"
```json
{"style": "soft_illust", "framing": "full",
 "characters": [
   {"view": "side", "head": {"yaw": 0, "roll": 0}, "outfit": {"type": "slip_dress", "shoes": "heels"}},
   {"gender": "male", "view": "side", "head": {"yaw": 0, "roll": 0}, "place": {"scale": 1.06}}],
 "background": {"type": "city", "city": {"time": "night"}}}
```
- 요청: "카페에 선 친구 셋, 웨이스트업"
```json
{"style": "anime_cel", "framing": "waist",
 "characters": [
   {"body": {"pose": "wave"}, "expression": {"mouth": "open_smile"}, "outfit": {"type": "knit_sweater"}},
   {"hair": {"style": "bob", "bangs": "full"}, "body": {"pose": "chin_rest"}, "outfit": {"type": "shirt"}},
   {"hair": {"style": "ponytail"}, "body": {"pose": "pocket"}, "outfit": {"type": "hoodie"}}],
 "background": {"type": "cafe"}}
```
- 요청: "모니터와 키보드가 놓인 책상 정물"
```json
{"subject": "still_life", "style": "anime_cel",
 "still_life": {"table": "#D8D2C8", "wall": "#DCE2E8", "cloth": null, "objects": [
   {"type": "monitor", "x": 0.42, "depth": 0.05}, {"type": "keyboard", "x": 0.42, "depth": 0.55},
   {"type": "mouse", "x": 0.66, "depth": 0.58}, {"type": "mug", "x": 0.82, "depth": 0.5}]}}
```
- 요청: "노을 진 산과 호수, 유화"
```json
{"subject": "landscape", "style": "painterly", "landscape": {"time": "sunset", "clouds": 3}}
```
- 요청: "레몬과 사과, 노란 꽃이 꽂힌 항아리 정물, 수채화"
```json
{"subject": "still_life", "style": "watercolor",
 "still_life": {"cloth": null, "objects": [
   {"type": "jar", "x": 0.32, "depth": 0.2, "flowers": "#F2D35A"},
   {"type": "lemon", "x": 0.52, "depth": 0.7}, {"type": "apple", "x": 0.66, "depth": 0.6}]}}
```
- 요청: "비 그친 밤 골목 야경"
```json
{"subject": "city", "style": "anime_cel", "city": {"time": "night"}}
```
- 요청: "두머 감성, 밤거리에서 담배 든 비니 남자"
```json
{"style": "anime_cel", "framing": "waist", "mood": "doomer",
 "character": {"gender": "male", "head": {"yaw": -12, "pitch": 4}, "eyes": {"openness": 0.72},
   "accessories": ["beanie"], "body": {"hold": {"item": "cigarette", "side": "left"}},
   "outfit": {"type": "hoodie", "color": "#2A2C34", "bottom": "jeans"}}}
```
- 요청: "텅 빈 밤거리를 홀로 걷는 사람, 원경, 유화"
```json
{"style": "painterly", "framing": "wide", "mood": "doomer",
 "character": {"gender": "male", "view": "side", "facing": "right", "place": {"x": 0.36},
   "head": {"yaw": 0, "roll": 0}, "body": {"pose": "walk"}, "accessories": ["beanie"],
   "outfit": {"type": "hoodie", "color": "#2A2C34", "bottom": "jeans", "shoes": "sneakers"}}}
```
- 요청: "사무실 단체 사진, 7명, 두 줄"
```json
{"style": "soft_illust", "framing": "waist", "pair": {"rows": 2}, "background": {"type": "office"},
 "characters": [{}, {"hair": {"style": "bob"}}, {"hair": {"style": "ponytail"}}, {},
   {"gender": "male"}, {"gender": "male"}, {"gender": "male"}]}
```

## 참조 파일
- references/spec.md: 스펙 전체 필드, 허용값, 기본값, 팔레트 요령 (스펙 작성 시 항상 참조)
- references/process.md: 공정별 원리, 비례 캐논, 화풍 알고리즘, 결함 진단표, 한계 (검수와 디버깅 시 참조)
- references/extending.md: 레이어 모델, 좌표계, 스택 순서, 확장 레시피 (엔진 수정 시 참조)
- assets/examples/*.json: 주제, 구도, 시점, 자세, 화풍, 성별, 의상, 배경, 투샷, 단체, 무드별 예시 스펙 66종 (duo_로 시작하는 9종이 투샷, group_으로 시작하는 4종이 단체, doomer_로 시작하는 7종이 두머 무드)
