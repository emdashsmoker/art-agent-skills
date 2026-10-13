# 인물 작화

## 목차
- 구성 요소
- Figure (비례와 포즈)
- 체형과 표면 해부
- 남성 인물
- 포즈 규약
- 손
- Character (얼굴, 피부, 표정)
- Hair
- wardrobe (의상)
- 민속 의상 (기모노, 한복, 훈도시, 사라시)
- 손에 든 소품
- 앉은 인물과 탁자
- 여러 인물 (투샷)
- 화면 배치
- 인물 점검
- 자주 쓰는 조정

## 구성 요소

- `Figure`: 뼈대와 덩어리로 이루어진 작도 마네킹. 비례, 포즈, 손 모양을 가짐
- `Character`: Figure에 얼굴, 머리, 의상, 피부색을 입혀 캔버스에 그리는 단위
- `Hair`: 머리 덩어리(두피 캡)와 앞머리, 옆머리, 뒷머리
- `wardrobe`: 신체 덩어리를 감싸는 의상
- 그리는 순서는 `Character.draw`가 처리 (뒷머리, 신체와 의상, 얼굴, 앞머리, 눈썹)
- 좌표계: 머리 높이 단위(HU), x는 화면 오른쪽, y는 위, z는 관찰자 쪽. 인물은 정지 자세에서 관찰자를 바라봄

## Figure (비례와 포즈)

```python
Figure(sex="female", heads=7.75, slim=1.0, bust=1.0, pose="relaxed", hands=None,
       turn=0.0, lean=0.0, tilt=0.0, head_scale=1.0, curves=1.0, tone=None)
```

| 인자 | 의미 | 권장 값 |
|---|---|---|
| sex | female, male | |
| heads | 등신 | 애니메 6.8-7.4, 자연 7.5-7.75, 이상화 8, 패션 8.5 |
| slim | 몸통과 팔다리 굵기 배율 | 0.9 마름, 1.0 기본, 1.1 건장 |
| bust | 여성 흉부 크기 배율 | 0-1.3, 고전 인체 습작 0.9-1.15 |
| curves | 여성 허리와 골반의 대비 | 0.6 일자, 1.0 기본, 1.3 강조 |
| tone | 근육 결의 강도 | 0 매끈함, 여성 기본 0.55, 남성 기본 0.75, 1 운동선수 |
| pose | 프리셋 이름 또는 관절 사전 | 아래 표 |
| hands | `{"l": 프리셋, "r": 프리셋}` | 아래 손 항목 |
| turn | 몸 전체 회전, 양수는 화면 오른쪽을 향함 | 반측면 25-35, 측면 80-90, 뒷모습 180 |
| lean, tilt | 몸 전체 앞 기울임, 옆 기울임 | 0-10 |

- 포즈 프리셋 (`POSES`)

| 키 | 자세 |
|---|---|
| stand | 차렷 |
| relaxed | 팔을 살짝 벌린 편안한 직립 |
| contrapposto | 한쪽 다리에 체중을 실은 고전 자세 |
| hand_on_hip | 한 손을 허리에 올림 |
| walk | 걷기 |
| sit | 의자에 앉은 자세 (의자는 별도로 그림) |
| arms_up | 두 팔을 위로 올림 |
| venus | 한 팔은 가슴 앞, 한 팔은 아래로 내린 고전 인체 습작 자세 |
| allure | 콘트라포스토에 한 손을 머리 뒤로 올린 자세 |
| arms_behind_head | 두 손을 머리 뒤로 올려 흉곽이 열린 자세 |
| heroic | 두 손을 허리에 짚고 가슴을 편 자세 |
| david | 체중을 한쪽 다리에 싣고 한 손을 반대쪽 어깨 위에 올린 고전 조각 자세 |
| arms_crossed | 팔짱 |

- 프리셋 위에 일부 관절만 덮어쓰기: `figure.set_pose(head=(4, -26, -5), l_elbow=(25, 0, 0))`
- 포즈 사전에 `"_reach": {"r": "behind_head"}`를 넣으면 생성 시점에 해당 손을 목표로 보냄 (아래 `reach` 참조)

## 체형과 표면 해부

- 몸통 단면표는 실측 비례 기준 (허리 앞뒤 두께 약 0.7 HU, 골반 약 0.9 HU)
    + 옆모습에서 흉곽이 앞으로, 허리 뒤가 오목하게, 골반이 뒤로 기우는 S자 척추가 나타남
- 가슴, 엉덩이, 위팔, 허벅지, 어깨띠, 아랫배는 몸통과 매끈하게 이어 붙음
    + 덩어리 사전에 `blend` 값(HU)을 주면 별도로 찍은 뒤 부드러운 합집합으로 결합하여 경계 주름이 생기지 않음
    + 가슴 아래 주름처럼 실제로 겹치는 깊은 단차는 유지됨
- 피부 막 처리가 덩어리 사이의 얕은 틈을 메움 (손, 발가락, 얼굴은 제외)
- 척추 고랑, 가슴뼈, 복부 중앙선, 배꼽은 표면에 눌러 새긴 홈
    + 추가 홈: `figure.extra_carves.append(dict(point=월드 좌표, radius=HU, depth=HU))`
- 근육 결 (`tone` 비례)
    + 오목한 곳: 목 아래 오목점, 비너스 보조개, 골반 앞 고랑, 삼각근 V자, 이두근과 삼두근 경계, 허벅지 바깥 띠, 무릎 힘줄 양옆, 아킬레스건 양옆, 갈비뼈 아래 경계
    + 볼록한 곳: 목빗근, 견갑골, 골반뼈, 위팔노근, 무릎 안쪽 물방울 근육, 종아리 두 갈래
    + 남성은 복근 격자, 가슴 아래 경계, 앞톱니근을 추가
    + 추가 볼록 표면: `figure.anatomy()`를 확장하거나 `extra_carves`에 홈을 추가
- `figure.table_point(name, y, angle, side)`: 몸통, 목, 팔다리 표면 위의 정지 자세 좌표 (angle 0 앞, 90 바깥, 180 뒤)
- `figure.surface_z(y, "front" 또는 "back")`: 높이 y에서 몸통 중앙선 표면의 z (소품과 표식 위치 계산용)
- 피부 광택은 얼굴 화풍에 따라 자동 (classic 0.06, semi 0.03, anime 0)
- 근육 결은 맨살에 100%, 옷 위에는 20%만 비침 (천이 홈을 덮음)

## 남성 인물

- `Figure(sex="male")`은 여성과 같은 관절과 파이프라인에 남성 단면표(`MALE`)를 사용
    + 어깨 관절 0.86 HU, 골반 폭 0.66 HU, 허리가 짧고 곧음, 흉곽이 깊음 (어깨가 넓고 골반이 좁은 V자 몸통)
    + 손 1.12배, 발 1.08배, 목이 굵고 허벅지 바깥선이 곧음
- 남성 근육 덩어리 (`blend`로 몸통에 매끈하게 결합)
    + 가슴판, 삼각근 머리, 승모근 경사, 광배근 날개
    + 엉덩이 덩어리는 여성보다 작음
- 남성 근육 결 (tone 기본 0.75): 이두근, 삼두근, 바깥 허벅지, 대퇴직근, 골반 위 복사근, 엉덩이 옆 오목, 가슴 아래 경계, 복근 격자, 앞톱니근, 목울대
- 얼굴과 머리는 `figure.sex`를 따라 자동 조정
    + 머리 단면: 턱 아래쪽 폭 증가, 턱 끝이 넓고 앞으로 나옴
    + 얼굴 입체: 눈썹뼈 1.9배, 눈구멍 1.25배, 광대 1.25배, 턱 1.5배, 턱 모서리 추가, 입술 0.6배
    + 이목구비: 눈 높이 0.8배, 속눈썹 0.45배, 눈꼬리 기울기 0.3배, 홍조 거의 없음, 눈썹은 낮고 곧고 굵음
    + semi 남성은 입술을 칠하지 않고 입선과 아랫입술 그늘만 그림, 콧대 한쪽에 선 1개 추가
    + 그리는 화풍의 목 가늘기(anime 0.74, semi 0.82)를 남성은 절반만 적용
- 고전 남성 인체 습작
    + 골반에 매듭지은 천(`wardrobe.loincloth()`)을 두르면 고전 회화의 관례와 맞고 다리가 드러남
    + 권장: `pose="david"` 또는 `heroic`, turn 10-25, rembrandt 조명, classic 얼굴, heads 7.9 (`figure_classical_male.py`)
- 웹툰 남성 초상: semi 얼굴, `Hair("crop", "textured")`, 밝은 상의와 studio 조명이 몸의 형태를 잘 보여 줌 (`portrait_male.py`)

## 포즈 규약

- 관절 값은 `(forward, twist, side)` 각도
    + forward 양수: 앞으로 굽힘 (팔다리는 앞으로 들기, 척추는 숙이기)
    + twist 양수: 화면 오른쪽으로 돌림
    + side 양수: 팔다리는 바깥으로 벌림, 척추와 머리는 화면 오른쪽으로 기울임
- 관절 이름

| 부위 | 관절 |
|---|---|
| 몸통 | pelvis, waist, chest, neck, head |
| 팔 | l_clav, l_shoulder, l_elbow, l_wrist (오른쪽은 r_) |
| 다리 | l_hip, l_knee, l_ankle (오른쪽은 r_) |

- l_은 인물 기준 왼쪽 (정면에서 화면 오른쪽에 보임)
- 팔꿈치와 무릎은 forward 값만 사용 (팔꿈치 양수는 굽힘, 무릎 양수는 굽힘)
- 쇄골(clav)은 `(앞으로 내밀기, -, 어깨 올리기)`
- 자주 쓰는 값
    + 팔을 앞으로 90도 들기: `l_shoulder=(90, 0, 0)`
    + 팔을 옆으로 수평: `l_shoulder=(0, 0, 90)`
    + 고개를 화면 왼쪽으로 돌리고 살짝 숙이기: `head=(8, -25, 0)`
    + 체중을 오른 다리에 싣기: `pelvis=(0, 0, 7), r_hip=(0, 0, -7), l_hip=(15, -10, 11), l_knee=(28, 0, 0)`
- 손 위치로 팔 포즈 지정: `figure.reach(side, target)`가 손목이 목표에 닿도록 어깨와 팔꿈치 각도를 계산
    + 이름 목표 (`REACH_TARGETS`): hip, waist_front, chest, heart, opposite_shoulder, own_shoulder, fold, collar, lap, pelvis_front, chin, cheek, hair, behind_head, pocket, forward, up, side
    + hip은 체형에 맞춰 허리 옆 표면을 계산하므로 남녀 모두 손이 허리에 닿음
    + 좌표 목표: `figure.reach("l", (x, y, z), anchor="chest")`, 정지 자세 좌표이며 x 양수는 뻗는 팔 쪽
    + 반환값은 남은 거리(HU), 0.1 미만이면 도달
    + 몸통 포즈를 먼저 정한 뒤 호출 (목표가 몸통을 따라 움직임)
- 골반을 기울이면 두 다리가 함께 기울어지므로 서 있는 다리의 hip side 값을 반대로 보정
- 포즈를 새로 만들 때는 `--rough`로 확인하면서 관절을 1-2개씩 조정

## 손

- 손가락 5개는 뼈대 정의로 고정, 손 모양만 선택
- 프리셋 (`HAND_POSES`): relaxed, open, fist, point, hold, grace
- 직접 지정: `{"curl": [(손허리, 가운데마디) x 4], "spread": 벌림 각도, "thumb": (벌림, 맞섬, 굽힘)}`
- 손바닥 방향은 손목 관절의 twist로 조절: `l_wrist=(0, 90, 0)`
- 손이 화면에서 작게 보일 때(전신)는 relaxed 또는 grace가 안정적

## Character (얼굴, 피부, 표정)

```python
Character(figure, style="anime", jaw=0.7, cheek=1.0, hair=Hair(...), palette=None, outfit=(),
          expression="neutral", gaze=(0.0, 0.0), skin="fair", beard=0.0, glasses=None)
character.draw(canvas, x, ground_y=None, height=None, head_top_y=None, unit=None, light=None)
```

| 인자 | 의미 |
|---|---|
| style | anime (큰 눈, 선 위주), semi (웹툰, 세미실사), classic (자연 비례, 회화용) |
| jaw | 0 둥근 턱, 1 날카로운 V라인. 기본 0.7 |
| cheek | 볼 너비 배율 |
| palette | skin, iris, brow, lash, lip, eye_white, blush 색 덮어쓰기 |
| expression | neutral, gentle, smile, serious, sad, tired (반쯤 감긴 무거운 눈꺼풀, 내려앉은 눈썹) |
| gaze | 시선 이동 (x, y), 범위 -1에서 1 |
| skin | porcelain, fair, light, warm, olive, tan, brown, deep 또는 색상 코드 |
| beard | 수염 자국 0-1 (턱, 턱끝, 윗입술의 미세한 점묘와 옅은 그늘). 0.3 옅음, 0.6 짙음 |
| glasses | None, round (얇은 금속테), oval, square (굵은 뿔테) 또는 `dict(kind, color, lens)` |

- `brief.character()`는 브리프 설정으로 Character를 만들어 줌. 인자로 figure, hair, outfit 등을 덮어쓸 수 있음
- `draw`에 `light`를 넘기면 턱 아래, 팔 아래 등 신체가 스스로 드리우는 그림자가 계산됨
- 얼굴 화풍별 특징
    + anime: 얼굴 음영을 평평하게 처리하여 얼굴이 그림자로 갈라지지 않음
    + semi: 얼굴 입체 55%, 쌍꺼풀 선, 아래 눈꺼풀, 콧방울, 윗입술 큐피드 활 표현
    + classic: 얼굴 입체 100%, 홍채가 조명을 받고 눈동자 흰자가 구면처럼 양끝에서 어두워짐
- 얼굴 입체는 머리 표면을 앞으로 밀어낸 변위(`head.FaceRelief`)로 만듦
    + 눈구멍, 콧대와 코끝, 콧방울, 광대, 입 주변, 윗입술과 아랫입술, 인중, 턱이 하나의 피부로 이어짐
    + 어떤 각도에서도 옆얼굴 윤곽과 음영이 일관됨
- 귀는 귓바퀴 테두리와 오목한 안쪽 그늘이 자동으로 그려짐
- 안경은 눈 앞에 떠 있는 단단한 테로 그려져 머리 회전에 맞춰 짧아지고 보이는 쪽 다리만 귀까지 이어짐
- `draw`는 `place`(투영), `build`(입체 생성), `paint`(채색과 얼굴) 3단계를 차례로 실행함. 여러 인물은 `Ensemble`이 단계를 나누어 호출
    + 단계 사이에 다른 요소를 끼워 그릴 수 있음: `build` 뒤에는 손과 관절의 화면 위치가 확정되고 아직 칠해지지 않음
    + 끼워 그릴 때는 `build(view)`를 back_hair 없이 호출 (늘어진 뒷머리는 `paint`가 그려서 소품보다 앞에 놓임)

## Hair

```python
Hair(style="long", fringe="swept", color="#3e2f45", side=None, volume=None, wave=0.0, sway=0.0,
     length=None, seed=1, gloss=0.55, strand=0.3, ring=0.0)
```

| 인자 | 선택지 |
|---|---|
| style | long, medium, bob, short, ponytail, bun, updo, crop (남성 짧은 머리), beanie (니트 비니) |
| fringe | swept (옆가르마), straight (일자 뱅), parted (가운데 가르마), curtain (커튼 뱅), wispy (가는 가닥), none, side_part (남성 옆 가르마), quiff (올려 넘김), textured (짧게 흐트러짐) |
| volume | 머리 부피. None이면 스타일 기본값 (crop 0.45, 나머지 1.0) |
| side | 옆머리 길이(HU), 0이면 없음 |
| wave | 0 직모, 1 굵은 웨이브 |
| sway | 바람 방향으로 쏠림, 음수는 왼쪽 |
| length | 뒷머리 길이(HU) 직접 지정 |
| strand | 머릿결 줄무늬 강도 (회화 화풍에서 0.3-0.5) |
| ring | 정수리 하이라이트 띠 강도 (애니메 화풍에서 자동 적용) |

- 앞머리와 옆머리는 두개골 위에 놓인 입체 가닥 (신체와 같은 높이 지도에 포함)
    + 얼굴을 올바르게 덮고 이마에 그림자를 드리우며 어느 각도에서도 얼굴이 비쳐 보이지 않음
    + 넓은 가닥은 3줄의 가는 가닥으로 나뉘어 결이 생김, side가 길면 끝이 중력 방향으로 흘러내림
- 머릿결은 가닥이 흐르는 방향을 따라 번진 줄무늬로 표현 (strand 값)
- classic 화풍은 가닥 사이 선을 생략하여 한 덩어리로, anime와 semi는 가닥마다 흐름 선을 그림
- crop은 두개골을 일정한 두께로 감싼 껍질 (`CROP_HAIRLINE`이 헤어라인을 정의)
    + 이마 위에서 둥글게, 관자놀이에서 살짝 올라가고, 귀 앞 구레나룻, 귀 뒤를 돌아 목덜미까지 내려감
    + 남성 앞머리 3종과 짝을 이루며 귀가 드러남
- 앞머리 경로 점에 세 번째 값을 주면 그 지점에서 두피 위로 띄움 (quiff의 들린 앞머리)
- beanie는 crop과 같은 껍질 방식의 니트 모자
    + 이마를 낮게 덮고 귀 윗부분을 지나 뒤통수로 내려가는 선(`BEANIE_LINE`)에서 끝나며 정수리가 조금 부풂
    + 접어 올린 밑단(`BEANIE_CUFF`)에 세로 골지와 접힌 선, 광택과 머릿결은 자동으로 꺼짐
    + 앞머리는 none과 짝을 이룸 (브리프에서 비니를 고르면 앞머리가 자동으로 none)
- 밤 장면의 검은 머리는 `gloss=0.2` 전후로 낮추면 정수리 광택이 조각나 보이지 않음

## wardrobe (의상)

- 의상은 `outfit` 리스트에 안쪽 옷부터 순서대로 넣음

| 함수 | 주요 인자 |
|---|---|
| `top(color, sleeves, hem, neck)` | sleeves: none, cap, short, elbow, three_quarter, long |
| `pants(color, length)` | length: full, cropped, knee, shorts |
| `skirt(color, hem, flare)` | hem: 3.2 미니, 2.5 무릎, 1.2 미디, 0.5 맥시 |
| `dress(color, sleeves, hem, flare, neck)` | |
| `coat(color, hem, sleeves)` | 다른 옷 위에 입는 겉옷 |
| `drape(color, top_y, hem, flare)` | 골반에 두른 고전 천 (치마처럼 발까지). 남성은 자신의 골반 폭을 따름 |
| `loincloth(color, top_y, length, width, knot)` | 골반 띠, 앞뒤로 늘어진 천, 한쪽 골반의 매듭 (고전 남성 인체 습작). length는 앞 천 길이(HU), knot은 "l" 또는 "r" |
| `shoes(color)` | |
| `hoodie(color, sleeves, hem, strings, pocket)` | 후드를 내린 후드티: 목을 감싸는 두툼한 후드 깃, 등에 늘어진 후드 자루, 목 앞 끈 2가닥, 배 앞 주머니 |
| `turtleneck(color, sleeves, hem)` | 목을 감싸 접어 올린 깃의 몸에 붙는 니트 |

- hem, neck, top_y는 정지 자세 기준 높이(HU). 허리 4.95, 엉덩이 4.2, 무릎 2.1
- 세부 장식은 `detail` 인자로 추가
    + `top(..., detail=wardrobe.neckline("v", depth, width))`: V넥 또는 스쿱넥
    + `coat(..., detail=wardrobe.open_front(inner_color, lapel=True, buttons=0))`: 앞을 열어 입은 코트와 라펠
    + `top(..., neck=6.62, detail=wardrobe.collar(open_neck=True, buttons=5))`: 셔츠 칼라와 단추 여밈
- `folds` 인자는 주름 음영 강도 (0이면 매끈함)
- 의상은 가슴, 엉덩이, 남성 가슴판과 삼각근 머리까지 감싸므로 근육 덩어리가 옷을 뚫지 않음
- 무늬, 로고, 리본 등은 `draw` 이후 `canvas.add(..., clip=view.part_mask("top") > 0.5)`로 옷 영역 안에 그림

- 두머 차림
    + 남성: `Hair("beanie", "none")`, `hoodie`, `expression="tired"`, 입에 문 담배 (`doomer_male.py`)
    + 여성: `Hair("bob", "straight", gloss=0.2)`, `turtleneck`, 앞을 연 긴 `coat`, 팔짱 (`doomer_female.py`)
    + 줄 이어폰은 얼굴 옆 점에서 가슴의 한 점으로 모이는 가는 선 2개와 아래로 이어지는 선 1개로 그림 (`doomer_female.py`의 `earphones`)

## 민속 의상 (기모노, 한복, 훈도시, 사라시)

| 함수 | 주요 인자 | 형태 |
|---|---|---|
| `kimono(color, sleeves, hem, collar, under, pattern)` | sleeves: short, tomesode, furisode / pattern: None, blossom, dots | 왼쪽 섶이 위로 오는 여밈 깃, 깃 띠, 목 안쪽 흰 반에리, 팔 아래로 늘어진 소매 주머니, 발목 길이의 감싼 자락 |
| `obi(color, width, cord, bow)` | width: wide (여성), narrow (남성) | wide는 허리에서 가슴 아래까지 덮는 띠, 등 뒤 상자 매듭(오타이코), 가운데 끈(오비지메). narrow는 엉덩이에 낮게 맨 띠와 작은 매듭 |
| `jeogori(color, length, git, dongjeong, goreum)` | length: short (여성), long (남성) | 오른쪽으로 여미는 깃(깃 색), 목 쪽 흰 동정, 오른쪽 가슴에서 늘어진 고름 2가닥, 아래가 둥근 소매 |
| `chima(color, top, hem, flare)` | top: 가슴 위 높이 (기본 6.05) | 가슴 위에서 묶어 가슴 아래부터 엉덩이까지 곧게 떨어지고 그 아래로 넓게 퍼지는 치마 |
| `baji(color, ease)` | | 통이 넓은 바지, 발목에서 대님으로 조인 모양 |
| `fundoshi(color, apron, twist)` | apron: 0 (로쿠샤쿠), 1.0 안팎 (엣추) | 꼰 허리띠, 앞 주머니, 엉덩이 사이 가닥. apron은 앞으로 늘어진 천 길이(HU) |
| `sarashi(color, lo, hi)` | 배: lo 4.62, hi 5.6 / 가슴: lo 5.5, hi 6.35 | 몸에 납작하게 여러 번 감은 흰 천과 감긴 줄 |

- 입는 순서 (안쪽부터)
    + 기모노: `[kimono(...), obi(...), shoes("#f4f2ec")]` (흰 신발이 버선 역할)
    + 여성 한복: `[chima(...), jeogori(...)]`, 저고리가 치마 위를 덮음
    + 남성 한복: `[baji(...), jeogori(..., length="long")]`
    + 축제 차림: `[fundoshi(), sarashi()]`, 위에 `coat(hem=4.2, sleeves="elbow", detail=open_front(...))`을 걸치면 핫피
- `Brief`의 outfit 선택지 kimono, hanbok, festival이 위 조합을 성별에 맞춰 만들어 줌
- 기모노 자락과 한복 치마는 걷는 다리가 단면 모서리로 비치지 않도록 넓어지며 보폭이 크면 자락이 넓게 벌어져 보임
- 깃, 고름, 감긴 줄은 몸통 표면 좌표 위에 그리므로 몸을 돌려도 따라감. 관찰자를 등진 쪽은 그리지 않음
- 기모노 무늬는 옷 위에 흩뿌린 평면 문양이며 옷 주름을 따라 휘지 않음
- 예시: `scene_blossom_walk.py` (후리소데와 오비), `figure_hanbok.py` (여성 한복), 검증 시트 `tools/verify_sheets.py folk`

## 손에 든 소품

- 우산처럼 손에 쥐고 몸 뒤로 지나가는 소품은 인물 앞뒤로 나누어 그림 (`scene_rain_night.py`, `scene_blossom_walk.py`)

```python
figure.reach("r", (0.05, 5.55, 0.62), anchor="chest")         # 가슴 앞에서 쥠
figure.hands["r"] = "fist"
view = character.place(canvas, x, ground_y=foot_y, height=h)
character.build(view)                                           # 손의 위치가 확정됨
fist = view.group_mask("hand_r") > 0.5
ys, xs = np.nonzero(fist)
grip = (xs.mean() / canvas.scale, ys.mean() / canvas.scale)     # 주먹의 중심
spec = dict(hand=grip, centre=(head_x - unit * 0.75, head_y - unit * 1.3), radius=unit * 2.6, view=0.42)
props.umbrella(canvas, part="back", **spec)                    # 캐노피와 우산대: 인물 뒤
character.paint(view, light=light)
props.umbrella(canvas, part="front", clip=1.0 - fist.astype("float32"), **spec)   # 손잡이: 주먹 아래
```

- 어깨에 걸쳐 뒤로 기울인 우산은 안쪽 면이 머리 뒤에서 후광처럼 보임 (view 0.4-0.55)
- 양산은 캐노피 중심을 머리 위 반대쪽 어깨 방향에 두면 얼굴이 가려지지 않음
- 손에 쥔 소품의 위치는 `view.joint("r_wrist")`보다 손 마스크의 중심이 정확함 (손목에서 손바닥만큼 떨어져 있음)

## 앉은 인물과 탁자

- `pose="sit"`은 발이 바닥에 닿도록 놓이며 골반이 의자 높이(약 0.45 m)에 옴
    + 키(`height`)는 선 키 그대로 주고 발 위치(`ground_y`)는 앉은 발끝의 바닥점으로 잡음
    + 의자는 인물보다 먼저 그림 (`Perspective.chair`, 등받이를 인물의 등 쪽에)
- 탁자에 올린 손은 탁자 위에, 무릎은 탁자 아래에 와야 하므로 그리는 순서를 3단으로 나눔 (`scene_cafe_window.py`)
    + 탁자 전체와 탁자 위 소품(노트북, 머그)을 먼저 그림
    + 인물을 그림 (손과 팔뚝이 탁자 위에 놓임)
    + 탁자 상판만 다시 그리되 `clip=view.group_mask("pants")`로 다리 부분에만 덮음
- 손을 자판 위에 두는 목표 예시: `figure.reach(side, (0.26, 5.78, 1.7), anchor="chest")` (정지 자세 좌표, 몸 앞 1.7 HU)
- 반신 크롭에서 팔짱 낀 팔을 탁자에 올리는 장면은 탁자를 인물 다음에 그리고 팔 마스크를 뺀 clip으로 덮음 (`portrait_candle.py`)
    + `arms = sum(view.group_mask(g) for g in ("arm_l", "arm_r", "hand_l", "hand_r"))`
    + `objects.table(canvas, y, clip=1.0 - arms)`
- 옆으로 앉은 인물(turn -60에서 -75)이 손, 다리, 탁자의 겹침이 가장 잘 읽힘. 정면으로 앉으면 탁자 위 노트북이 상체를 가림
- 벤치에 앉은 뒷모습(turn 180)은 벤치 다리와 좌판, 인물, 등받이 순서로 그림 (`doomer_duo.py`)
    + 발 위치는 좌판보다 0.45 m 앞의 바닥점, 등받이 살 사이로 외투가 보이고 좌판 아래로 종아리와 뒤꿈치가 보임
    + 카메라가 벤치 뒤 1.1 m 높이에서 내려다보면 두 사람 너머로 원경이 열림

## 여러 인물 (투샷)

```python
ensemble = Ensemble.from_framing(canvas, compose.framing(canvas, "three_quarter"), man)   # 가장 큰 인물 기준
ensemble.add(man, W * 0.42, depth=-30)            # depth: 관찰자 쪽 이동량(디자인 단위), 음수는 뒤로
ensemble.add(woman, W * 0.60, size=0.95)          # size: 머리 크기 배율 (작은 상대 0.92-0.96)
ensemble.touch(man, "l", woman, "around_shoulder")
with canvas.layer(depth=0.3, group="figure"):
    views = ensemble.draw(light=light)
```

- 모든 인물이 하나의 바닥선과 머리 크기를 공유하므로 한 인물의 손을 상대 몸에 지정 가능
    + 풍경 속 전신 투샷처럼 바닥선을 직접 정할 때는 `Ensemble(canvas, ground_y, unit)` (unit은 머리 1개 높이)
- `touch(reacher, side, partner, spot)`의 접촉 위치

| spot | 동작 |
|---|---|
| around_shoulder | 상대 등 뒤로 팔을 둘러 먼 쪽 어깨를 감쌈 (어깨동무) |
| shoulder | 가까운 쪽 어깨 앞에 손을 얹음 |
| upper_arm | 상대 위팔을 잡음 (팔짱에 가까운 동작) |
| waist | 상대 허리 뒤에 손을 둠 |

- `hold_hands(a, side_a, b, side_b)`: 두 인물 사이 엉덩이 높이에서 손을 맞잡음
- 접촉을 정하기 전에 상대 포즈를 먼저 확정 (손이 상대 몸의 현재 위치로 이동)
- 반환값은 손목이 목표에서 벗어난 거리(HU), 0.1 미만이면 접촉 성공
- `draw`가 처리하는 내용
    + 두 인물의 입체를 먼저 만든 뒤 깊이를 비교하여 뒤에 있는 부분을 지움 (팔이 상대 등 뒤로 지나감)
    + 먼 인물부터 채색하고 늘어진 뒷머리는 앞에 선 인물 뒤로 숨김
    + 한 인물이 상대에게 드리우는 그림자와 손이 닿은 자리의 접촉 그늘을 계산
    + 한 인물의 손이 화면상 상대 골반 앞에 놓이면 `tangent check` 경고 출력 (`ensemble.tangents()`로 직접 확인 가능)
- 배치 요령
    + 두 인물 중심 사이 거리는 1.7 HU 이상 (가까우면 팔과 몸이 서로 파고듦)
    + 어깨동무는 감싸는 쪽을 depth -30 정도 뒤에, 손잡기는 같은 depth로 2 HU 정도 떨어뜨림
    + 서로 마주 보는 장면은 turn을 35 안팎으로 반대 방향 지정
    + 두 인물이 붙어 서면 안쪽 손이 상대 몸 앞으로 늘어지므로 안쪽 손에도 `touch`로 위치 지정 (어깨동무에는 상대 허리)
    + 뒷모습 손잡기는 `scene_beach_sunset.py` 참조 (같은 depth, 중심 사이 약 2 HU)

## 화면 배치

- 크롭 프리셋: `compose.framing(canvas, kind, x=...)`가 `draw`에 넘길 인자를 만들어 줌

| kind | 범위 |
|---|---|
| face | 얼굴 클로즈업 |
| bust | 흉상 |
| half | 허리 위 |
| three_quarter | 무릎 위 |
| full | 전신 |

- 직접 배치
    + 전신: `draw(canvas, x, ground_y=발이 닿는 y, height=키)`
    + 클로즈업: `draw(canvas, x, head_top_y=정수리 y, unit=머리 1개 높이)`
- 원근 배경 안에 세울 때는 `Perspective.point`와 `Perspective.scale`로 발 위치와 키를 계산 (`scene_anime_film.py` 참조)
- 바닥 접지는 `scenery.contact_shadow(canvas, x, y, width)`를 인물보다 먼저 호출

## 인물 점검

- `view = character.draw(...)`의 반환값으로 후속 작업 수행
    + `view.joint("l_wrist")`: 관절의 캔버스 좌표 (소품을 손에 쥐여 줄 때 사용)
    + `view.part_mask("head")`: 부위가 실제로 보이는 영역
    + `view.to_canvas(figure.world("chest", (x, y, z)))`: 신체 표면의 임의 지점
- `qa.check_figure(view)`는 손과 발마다 (보이는 개수, 정의된 개수)를 반환
    + 정의된 개수는 항상 5. 보이는 개수가 적으면 다른 부위에 가려졌거나 화면 밖 (신발을 신으면 발가락은 0으로 표시)

## 자주 쓰는 조정

| 증상 | 조정 |
|---|---|
| 얼굴이 그림자로 반이 갈림 | 조명을 soft_front로 변경 또는 `draw(face_flatten=0.8)` |
| 머리가 너무 큼, 작음 | `heads` 조정 |
| 어깨가 넓어 보임 | `slim=0.92` 또는 `turn` 증가 |
| 옷 주름 음영이 지저분함 | 의상의 `folds=0` |
| 선이 굵음, 가늚 | `draw(line_width=...)` |
| 포즈가 뻣뻣함 | pelvis와 chest에 서로 반대 방향 side 값, head에 약한 twist와 side |
| 인체 습작이 마네킹처럼 보임 | `allure` 같은 비대칭 포즈, turn 15-35, rembrandt 조명, classic 얼굴 |
| 가슴이 붙인 공처럼 보임 | bust 0.9-1.15 유지, 측면 조명보다 반측면 조명 |
| 체형이 밋밋함 | curves 1.1-1.3, heads 7.8-8 |
| 근육 결이 너무 드러남, 안 보임 | tone 0.3 또는 0.8, 등과 다리의 결은 역광이나 측광에서 잘 보임 |
| 남성이 여성스러워 보임 | `sex="male"` 확인, jaw 0.5-0.7, `Hair("crop", ...)`, beard 0.2-0.4 |
| 남성 얼굴이 작아 보임 (웹툰) | `head_scale=1.05`, heads 7.7 |
| 남성 상의가 부풀어 보임 | 상의 `ease=0.025`, 코트 `ease=0.04`, 팔짱 포즈에 앞이 열린 코트 조합은 피함 |
| 투샷에서 팔이 상대 몸을 뚫음 | 두 인물 거리를 넓히거나 감싸는 쪽 depth를 더 뒤로 |
| 뒷모습 투샷의 손잡기 | 두 인물 turn 170-190, `hold_hands(왼쪽 인물, "r", 오른쪽 인물, "l")` (뒷모습에서 오른손은 화면 오른쪽) |
| 걷는 인물의 긴 코트 뒤로 다리가 뚫고 나옴 | 보폭 축소 `set_pose(l_hip=(18, 0, 2), r_hip=(-8, 0, 2))`, 코트 `ease=0.12` |
| 앉은 인물의 손이 탁자에 가려짐 | 탁자를 인물보다 먼저 그리고 다리 부분만 clip으로 다시 덮음 (앉은 인물과 탁자 항목) |
| 손으로 턱을 괴는 포즈에서 팔꿈치가 위로 솟음 | 손 목표 IK가 팔꿈치를 위로 보내는 해를 고름. 팔짱(arms_crossed)이나 탁자 위 팔 같은 안정 포즈로 대체 |
| 어깨동무 손이 어색함 | `touch(..., hand="hold", wrist=(0, -60, -45))` 기본값에서 wrist 각도를 10-15도씩 조정 |
