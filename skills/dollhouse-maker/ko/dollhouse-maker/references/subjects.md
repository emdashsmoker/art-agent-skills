# 소재 모듈

## 목차

- 얼굴 (head.py)
- 상반신 (bust.py)
- 전신 (figure.py)
- 손과 발 (extremities.py)
- 풍경 (landscape.py)
- 도시 (city.py)
- 현대 사물 (objects.py)
- 투샷 (pair.py)
- 원근 무대 (stage.py)
- 장면 템플릿 (scenes.py)

## 얼굴 (head.py)

정면 견본(높이별 반폭과 얼굴 좌표의 이목구비)을 먼저 그리고, 돌린 고개는 3/4 얼굴 작화 규칙으로 그린다. 깊이값과 회전 계산은 사용하지 않는다.

- 중심선을 돌린 쪽으로 휘어 이동(이마, 코, 입에서 가장 크게), 코끝과 머리카락처럼 돌출한 부분은 조금 더 이동
- 먼 쪽 반면은 가장자리로 갈수록 압축, 가까운 쪽 반면은 소폭 확대
- 가까운 쪽에 뒤통수가 드러나고 턱선은 귀 아래에서 턱끝으로 사선을 그림
- 먼 쪽 윤곽에 광대 돌출 추가
- 귀, 목, 올림머리처럼 얼굴 뒤에 있는 요소는 돌린 방향의 반대로 이동

```python
head = Head(HeadSpec(cx=480, top=170, size=560, yaw=0.2))
scene.add(head.back_parts())     # 뒷머리: 몸보다 먼저
scene.add(bust.parts())          # 목과 몸
scene.add(head.front_parts())    # 얼굴, 이목구비, 앞머리: 몸보다 나중
```

| HeadSpec 필드 | 기본값 | 의미 |
|---|---|---|
| `cx`, `top`, `size` | 필수 | 머리 축의 x, 정수리의 y, 머리 높이 px |
| `yaw` | 0 | 고개를 돌린 정도, 양수는 화면 오른쪽, 권장 범위 -0.45..0.45 |
| `roll` | 0 | 화면 평면 안 기울임 |
| `jaw` | 0.85 | 0은 둥근 턱, 1은 날렵한 턱선과 좁은 턱끝 |
| `eye_size`, `eye_open` | 1.0 | 눈 크기 배율, 뜬 정도 |
| `smile` | 0.3 | 입꼬리 올림 0..1 |
| `skin`, `hair`, `iris`, `lips` | 색 | 피부, 머리카락, 홍채, 입술 |
| `lip_alpha`, `blush`, `eyeshadow` | 0.6, 0.22, 0.25 | 입술색, 볼터치, 눈두덩 음영 농도 |
| `hair_style` | `"long"` | 12종, 아래 "머리 모양" 표 참조 |
| `bangs` | `"parted"` | `parted`(가르마), `swept`(옆으로 넘김), `full`(일자), `short`(짧게 친 앞머리 다발), `side`(옆 가르마, 짧은 머리용), `none` |
| `shading` | 0.6 | 얼굴 면 음영 0..1: 빛 반대쪽 옆면, 눈두덩, 볼과 콧등과 턱의 작은 광 |
| `light_side` | -1.0 | 광원 방향, -1은 화면 왼쪽, +1은 오른쪽(전신에서는 `FigureSpec.light_side`를 따름) |
| `face` | `"female"` | `female`, `male`(넓은 턱각, 짙은 일자 눈썹, 콧등과 콧방울, 입술색 없는 입선, 짧은 속눈썹) |
| `hair_length` | 2.1 | `long`, `wavy`의 머리끝 위치, 정수리 기준 머리 높이 배수 |
| `line` | 1.0 | 선 굵기 배율 |
| `seed` | 0 | 머리카락 난수 |
| `view` | `"front"` | `front`(얼굴이 관찰자 쪽, `yaw`로 돌림), `back`(뒤통수), `side`(옆얼굴 프로필) |
| `facing` | 1.0 | `side`에서 얼굴이 향하는 화면 방향, +1 오른쪽, -1 왼쪽 |
| `expression` | `"neutral"` | `neutral`, `smile`, `laugh`, `angry`, `sad`, `surprised`, `sleepy` |
| `eye_shape` | `"default"` | `default`, `droopy`(처진 눈), `upturned`(올라간 눈), `narrow`(가는 눈, 쌍꺼풀 없음) |
| `face_width` | 1.0 | 머리 전체 폭 배율, 권장 0.9(좁은 얼굴)..1.1(넓은 얼굴) |
| `brow_weight` | 1.0 | 눈썹 굵기 배율 |
| `age` | 0 | 0 청년, 0.5 중년, 1 노년: 팔자주름, 눈밑 처짐, 눈가 주름, 이마 주름, 처진 턱살 |
| `gray` | 0 | 머리카락과 눈썹의 흰머리 비율 0..1 |
| `beard` | `"none"` | `none`, `stubble`(면도 자국), `mustache`(콧수염), `goatee`(턱수염), `beard`(구레나룻까지 이어진 수염) |
| `beard_color` | None | 수염 색, None이면 머리카락 색 |
| `glasses` | `"none"` | `none`, `round`, `square`, `sunglasses` |
| `glasses_color` | `"#2a2630"` | 안경테 색 |
| `freckles` | 0 | 코와 볼의 주근깨 밀도 0..1 |
| `mole` | None | 점의 얼굴 좌표 `(u, v)`, 예: `(0.12, 0.79)` 입 옆 |

- 새 필드(`expression`부터 `mole`까지)의 기본값은 이전 버전과 같은 그림을 출력
- 허용값 밖의 문자열은 `ValueError`로 즉시 중단

### 뒷모습과 옆얼굴

- `view="back"`: 머리 피부, 양쪽 귀, 뒷머리만 작도하고 턱은 목에 가려 흐려짐
    + 늘어진 머리(`long`, `bob`, `medium`, `wavy`, `curly`)는 머리카락이 몸 위로 내려와 `back_parts()`가 빈 목록, 모든 머리카락은 `front_parts()`에 포함
    + 묶은 머리와 짧은 머리(`updo`, `ponytail`, `twintails`, `braid`, `short`, `buzz`)는 목덜미 머리선(`BACK_NAPE_V`), 올림머리 쪽진 부분, 뒤로 늘어진 꼬리를 작도
- `view="side"`: `profile.py`의 옆얼굴 윤곽표 1개(이마, 눈썹뼈, 코, 입술, 턱끝, 턱각, 뒤통수)로 작도
    + 눈은 앞이 열린 쐐기 모양, 홍채는 눈 앞쪽의 세로 타원, 여성은 속눈썹이 눈 앞으로 뻗음
    + 귀는 머리 중앙 약간 뒤, 위끝이 눈썹 높이
    + 턱각에서 목덜미까지의 아랫변은 목 위에 놓여 잉크 없이 흐려짐
    + 머리카락: 두개 위 모자 모양과 옆 머리선, 이마 앞에 늘어진 앞머리, 긴 머리는 귀를 덮는 옆머리와 등 뒤로 내려가는 뒷머리(`back_parts()`)
    + 윤곽 수치는 `FACE_LINE`, `BACK_LINE`, 머리선은 `SIDE_HAIRLINE`, 앞머리는 `BANGS`(성별, 스타일별)
- 옆얼굴의 국소 좌표는 x 앞쪽(얼굴 방향), v 아래(정수리 0, 턱끝 1)이며 `profile.Q(head, pts)`로 화면 좌표 변환

### 표정과 인상

같은 머리 모듈에서 표정, 눈매, 얼굴 폭, 나이, 수염, 안경, 피부 표지를 조합해 서로 다른 인물을 만든다. 정면, 3/4, 옆얼굴 모두 같은 필드로 동작한다. 견본은 `examples/faces.py`.

| `expression` | 눈 | 눈썹 | 입 |
|---|---|---|---|
| `neutral` | 기본 | 기본 | `smile` 필드값 사용 |
| `smile` | 약간 가늘게 | 약간 올림 | 입꼬리 올림 |
| `laugh` | 감은 눈(위로 볼록한 호) | 올림 | 크게 벌린 입, 윗니와 혀 |
| `angry` | 약간 가늘게 | 안쪽 끝을 내려 기울임, 미간 주름 | 입꼬리 내림 |
| `sad` | 약간 가늘게 | 안쪽 끝을 올려 기울임 | 입꼬리 내림 |
| `surprised` | 크게 뜸 | 크게 올림 | 동그랗게 벌린 입 |
| `sleepy` | 반쯤 감음 | 약간 올림 | 기본 |

- 표정 수치는 `head.EXPRESSIONS`, 눈매 수치는 `head.EYE_SHAPES`(기울기, 뜬 정도, 쌍꺼풀)
- 나이 표현: `age`가 주름과 턱살, `gray`가 머리색을 담당하므로 노년은 `age=1.0, gray=0.9` 조합
- 수염, 안경, 주름, 주근깨, 점은 `face_extras.py`가 작도
    + 정면과 3/4은 `marks()`, `beard()`, `glasses()`, 옆얼굴은 `marks_side()`, `beard_side()`, `glasses_side()`
    + 뒷모습에서는 작도하지 않음
- 피부색 다양화는 `skin`과 `FigureSpec.skin`을 같은 값으로 지정, 예: `"#8a5a3c"`, `"#a8724e"`, `"#d8a882"`

### 머리 모양

| `hair_style` | 정면과 3/4 | 뒷모습 | 옆얼굴 |
|---|---|---|---|
| `long` | 어깨 아래로 늘어진 머리, 옆머리가 귀를 덮음 | 등 위로 내려온 머리 | 귀를 덮는 옆머리와 등 뒤 뒷머리 |
| `bob` | 턱 아래 길이로 일자 커트 | 목덜미까지 | 짧은 옆머리 |
| `updo` | 정수리 위 쪽진 머리, 귀 노출 | 목덜미 머리선과 쪽 | 뒤통수 위 쪽 |
| `ponytail` | 뒤로 묶어 한쪽으로 늘어진 꼬리 | 뒤로 늘어진 꼬리 | 뒤로 늘어진 꼬리 |
| `short` | 짧은 머리, 귀 노출, 구레나룻 | 짧은 뒷머리 | 짧은 모자 모양 |
| `none` | 민머리 | 민머리 | 민머리 |
| `medium` | 어깨에 닿는 중간 길이(`MEDIUM_LEN`) | 어깨까지 | 중간 길이 옆머리 |
| `wavy` | 긴 머리 가장자리와 결이 물결(`WAVE`) | 물결진 긴 머리 | 물결진 옆머리 |
| `curly` | 머리 둘레의 둥근 곱슬 구름과 고리 무늬(`CURL_R`) | 둥근 곱슬 덩어리 | 뒤통수 쪽으로 부푼 곱슬 |
| `buzz` | 두피가 비치는 아주 짧은 머리(`BUZZ_VOL`, `BUZZ_SHOW`) | 짧은 머리선 | 얇은 모자 모양 |
| `twintails` | 귀 위 양쪽에서 묶어 늘어진 두 꼬리와 머리끈 | 양쪽 꼬리 | 귀 뒤에서 늘어진 꼬리 |
| `braid` | 한쪽 어깨 앞으로 늘어뜨린 땋은 머리(V자 마디) | 등 가운데로 내려온 땋은 머리 | 뒤통수에서 등 뒤로 내려온 땋은 머리 |

- 짧은 머리 계열(`short`, `buzz`)은 `bangs="short"`, 남성 중간 길이는 `bangs="side"`가 자연스러움
- 양갈래와 땋은 머리의 머리끈은 고정색 `#c84a5a`

### 얼굴 좌표 (u, v)

`head.P(u, v, lift)`는 정면 견본의 점을 돌린 얼굴의 화면 좌표로 변환한다. u는 중심선 기준 가로, v는 정수리 0에서 턱끝 1까지의 세로이며 단위는 머리 높이다. 장신구, 점, 안경 등 추가 세부는 이 함수로 위치를 잡아야 고개 회전을 따라간다.

| 기준점 | u | v |
|---|---|---|
| 헤어라인 중앙 | 0 | 0.185 |
| 눈썹 | ±0.05..±0.30 | 0.43 |
| 눈 중심 | ±0.156 | 0.548 |
| 눈 폭 | 0.200 | - |
| 귀 위쪽 | ±0.35 | 0.49 |
| 코끝 | 0 | 0.722 |
| 입 | 0 | 0.818 |
| 턱각 | ±0.26 | 0.80 |
| 턱끝 | 0 | 1.0 |

- `lift`는 얼굴에서 돌출한 정도(머리 높이 배수), 코끝 0.05, 머리카락 0.045, 돌린 방향으로 추가 이동
- `head.behind("ear" | "neck" | "bun", v)`는 얼굴 뒤에 있는 요소의 점, 돌린 방향의 반대로 이동
- 작화 규칙 수치는 `head.py` 상단 상수(CENTER_SHIFT, FAR_SQUEEZE, NEAR_SPREAD, SKULL_BACK, CHEEK_BUMP, BEHIND)에서 조정
- `head.chin()`, `head.neck_top()`은 턱끝과 목 시작점의 화면 좌표

### 얼굴 세부

- 눈: 홍채 결 18줄, 눈 앞머리의 분홍 주름, 윗눈꺼풀 바깥쪽 속눈썹 다발(여성 5개)
- 얼굴 면: 빛 반대쪽 옆면(관자에서 광대 아래로 들어와 턱선을 따라 턱끝까지)에 경계가 또렷한 그림자
    + 경계선 좌표는 `FACE_PLANE`, 농도는 `FACE[성별]["plane"]`와 `shading`의 곱
- 머리카락: 정수리에서 이마선으로 흐르는 결 선(`HAIR_FLOW`), 정수리 잔머리, 묶음으로 끊어진 광택 띠

### 남성 얼굴

- `face="male"`은 턱 폭표(`WIDTH_KEYS_MALE`)와 이목구비 표(`FACE["male"]`)를 함께 전환
- 짧은 머리(`hair_style="short"`)는 정수리 쪽이 두껍고 옆이 얇은 머리 두께(`SHORT_VOL`)로 작도
    + 외곽에 끝이 뾰족한 머리 결(`SHORT_TUFT`), 귀 앞 구레나룻(`SIDEBURN_V`) 추가
    + 귀는 머리카락 위에 그려져 짧은 뒷머리 경계를 덮음
- 성숙한 남성 인상은 `jaw` 0.88-0.95, `eye_size` 0.85-0.9, `lip_alpha` 0.1, `blush` 0, `eyeshadow` 0 조합

## 상반신 (bust.py)

```python
bust = Bust(head, BustSpec(outfit="camisole", cloth="#27354f", shoulder=1.0, turn=0.35, bust=1.0))
man = Bust(head_m, BustSpec(sex="male", outfit="tshirt", cloth="#33404c", turn=-0.35))
```

| BustSpec 필드 | 의미 |
|---|---|
| `outfit` | `camisole`, `tshirt`, `offshoulder`, `bare` |
| `cloth` | 옷 색 |
| `shoulder` | 어깨 폭 배율 |
| `turn` | 몸 방향 -1..1, 먼 쪽 어깨를 단축 |
| `bust` | 가슴 볼륨 배율(여성만) |
| `sex` | `female`, `male`(가파른 승모근, 넓은 어깨, 굵은 목과 팔, 목젖, 평평한 가슴) |
| `view` | `front`, `back`(쇄골과 목젖 대신 목덜미의 척추와 승모근 경계, 옷은 뒷목선) |

- 세로 좌표는 머리와 같은 v 척도를 이어서 사용(턱끝 1.0, 목 아래 오목 1.34, 어깨 끝 1.41)
- `bust.B(x, v)`는 몸 기준 좌표를 화면 좌표로 변환, 목걸이나 옷 무늬 배치에 사용
- 뒷모습 초상은 `HeadSpec(view="back")`과 `BustSpec(view="back", turn=0)` 조합, 예제는 `examples/portrait.py`의 `build_back()`
    + 뒷목선 재단은 `BACK_EDGES`, `BACK_EDGES_MALE`
- 새 옷은 `OUTFITS`에 윗선(`edge`)과 옆선(`seam`)의 오른쪽 절반 좌표를 추가
    + 남성 몸통에 맞춘 재단은 `OUTFITS_MALE`에 추가, 없으면 공용 표를 남성 폭으로 늘려 사용

## 전신 (figure.py)

일러스트레이터의 작도 순서를 2D로 구현한다. 여성과 남성은 같은 절차를 거치고 비례표(`BODY`)만 다르다. 관절 뼈대로 자세를 잡고, 몸통은 해부학 기준점(목, 어깨, 겨드랑이, 가슴 옆, 허리, 골반, 가랑이)을 잇는 윤곽 1개로 그리고, 팔다리는 뼈를 따라 좌우 곡선이 다른 형태로 그린다. 모든 피부 도형은 한 표면으로 잉크 처리되어 관절에 선이 생기지 않는다. 단위는 머리 높이(hu)이며 기본 비례는 8등신이다.

```python
figure = Figure(FigureSpec(cx=448, top=70, unit=180, skin="#eec6ab", outfit="figure_study",
                           bust=1.08, waist=0.95, hip=1.02,
                           head=dict(hair_style="long", bangs="swept")), pose="contrapposto")
scene.add(figure.parts())        # 뒤에서 앞 순서로 정렬된 전체 도형
man = Figure(FigureSpec(cx=448, top=70, unit=180, sex="male", skin="#dcae8c", outfit="figure_study"), pose="heroic")
```

| 기준선 | 정수리 기준 hu |
|---|---|
| 턱끝 | 1.0 |
| 목 아래 오목 | 1.34 |
| 어깨 관절 | 1.64 |
| 가슴 정점 | 2.05 |
| 허리 | 2.75 |
| 배꼽 | 3.05 |
| 고관절 | 3.83 |
| 가랑이 | 4.15 |
| 무릎 | 5.80 |
| 발목 | 7.60 |
| 지면 | 8.0 |

| FigureSpec 필드 | 의미 |
|---|---|
| `cx`, `top`, `unit` | 골반 중심 x, 기본 자세의 정수리 y, 머리 높이당 px |
| `sex` | `female`, `male`, 비례표와 얼굴 기본값과 의상 목록을 함께 전환 |
| `skin` | 피부색 |
| `shoulder`, `waist`, `hip`, `bust`, `limb` | 어깨, 허리, 골반 폭과 가슴(남성은 대흉근) 크기, 팔다리 굵기 배율 |
| `legs` | 다리 길이 배율, 1.05 전후는 패션 일러스트 비례 |
| `gloss` | 어깨, 가슴, 골반, 팔다리의 부드러운 광택 0..1 |
| `blush` | 무릎, 팔꿈치, 어깨의 붉은 기 0..1 |
| `modeling` | 몸통 측면, 복부 양옆, 가슴 아래, 안쪽 허벅지의 형태 음영 0..1 |
| `light_side` | 장면 광원 방향, -1은 왼쪽, +1은 오른쪽(`Scene.light`의 x 부호와 일치시킴) |
| `outfit`, `cloth` | 의상 1개와 옷 색, 여성 `figure_study`, `bikini`, `onepiece`, `highleg`, `slip`, `dressed`, 남성 `figure_study`, `briefs`, `trunks`, `open_shirt`, `dressed` |
| `cloth2` | 열린 셔츠 아래 반바지 색, `dressed`의 하의 색, None은 `cloth`의 어두운 색 |
| `upper`, `lower` | `dressed`의 상의 `tee`, `longsleeve`, `shirt`, `blouse`와 하의 `jeans`, `slacks`, `skirt`, `long_skirt` |
| `shoes`, `cloth3` | 모든 의상 공통 신발 `sneakers`, `boots`, `heels`(None은 맨발)과 신발 색 |
| `left_item`, `right_item` | `grip` 손에 쥔 물건 `phone`, `mug`, `book`, `umbrella`, `clear_umbrella` |
| `ident` | 한 장면의 여러 인물을 구별하는 짧은 식별자, 모든 도형 이름과 키에 `ident/` 접두어를 붙임 |
| `head` | `HeadSpec`에 전달할 추가 필드 dict |
| `line`, `detail` | 선 굵기 배율, 배꼽과 쇄골 등 세부 표시 여부 |
| `form` | 피부 형태의 둥글기 배율, 1.5-1.8은 측광 유화 습작처럼 형태가 강하게 돌아감 |

- 굴곡을 강조하려면 `waist` 0.92-0.97, `bust` 1.05-1.15, `legs` 1.03-1.07 조합
    + 허리선은 3/4 시점에서 가까운 쪽이 오목하고 먼 쪽이 차오르도록 자동 작도
- 광택과 음영은 별도 도형으로 얹으므로 화풍과 무관하게 적용, 0으로 두면 해제
- 성숙한 인상의 얼굴은 `head=dict(eye_size=0.92, jaw=0.95, lip_alpha=0.75, eyeshadow=0.35)` 조합
- 마른 체형은 `hip` 0.95, `bust` 0.9, `limb` 0.95 조합
- 해부 표지는 `detail=True`에서 피부 그림자색 선으로 작도
    + 공통: 쇄골 사이 오목, 삼각근 끝, 팔꿈치 안쪽 주름, 무릎 위 안쪽 근육, 안쪽과 바깥쪽 복사뼈
    + 남성 추가: 전거근 톱니, 복근 구획, 장골 V선
    + 농도는 `LANDMARK[성별]`에서 조정
- 팔다리는 뼈마다 빛 쪽 광택 띠와 반대쪽 형태 그림자 띠를 받음(`gloss`, `modeling`)

### 남성 체형

| 항목 | 여성 | 남성 |
|---|---|---|
| 어깨 관절 x(흉곽 좌표) | 0.665 | 0.86 |
| 허리 반폭 | 0.45 | 0.615 |
| 골반 최대 반폭 | 0.88 | 0.695 |
| 위팔, 아래팔, 손 길이(hu) | 1.40, 1.12, 0.72 | 1.45, 1.15, 0.76 |
| 가슴 | 유방(물방울형) | 대흉근(아랫선만 잉크, 겨드랑이로 오르는 직선형) |
| 복부 | 정중선 1줄 | 백선, 건획 3열, 복직근 바깥선, 장골 V선 |
| 손 폭, 발 크기 | 1.0, 1.0 | 1.12, 1.08 |

- 수치는 `figure.py`의 `BODY["male"]` 사전에서 조정
- 골반 앞쪽은 여성과 같은 매끈한 형태로 작도(골반 세부 형태는 모듈에 없음)

### 의상

| outfit | 형태 | 작도 방식 |
|---|---|---|
| `bikini` | 삼각 컵, 홀터 끈, 밑가슴 끈, 브리프 | 몸 위에 얹고 몸통과 가슴 영역으로 자름 |
| `onepiece` | 스쿱 넥, 어깨끈, 골반 높이 다리 재단 | 몸에 붙는 의상: 피부 도형 안으로 잘라 몸 윤곽을 그대로 따름 |
| `highleg` | 깊은 V넥, 골반뼈까지 올라간 다리 재단 | `onepiece`와 동일 |
| `slip` | 가는 끈, 하트 넥, 허벅지 중간 직선 밑단 | 독립 실루엣: 허리를 스치고 골반과 허벅지 바깥선을 따라 내려옴 |

- 의상은 앞쪽 팔과 손 아래에 그려져 허리에 얹은 손이 옷 위에 놓임
- 가슴은 옷감 안에서 별도로 부풀려 광택과 그림자를 받음
- 옷감 광택(측면 긴 광택, 가슴 반사광)은 `gloss`를 따르며 `slip`은 새틴처럼 더 강하게 적용
- 새 의상은 `SUITS`(몸에 붙는 의상)에 목선과 다리 재단 좌표를 추가하거나 `_slip`을 본떠 독립 실루엣을 작도

| 남성 outfit | 형태 | 작도 방식 |
|---|---|---|
| `briefs` | 낮은 허리 수영 브리프, 허리 밴드선 | 몸통과 허벅지 영역으로 자름 |
| `trunks` | 허리끈 수영 반바지, 허벅지 중간 밑단 | 골반 띠 1개와 다리 통 2개를 합친 독립 실루엣, 합집합 외곽만 잉크 |
| `open_shirt` | 앞이 열린 셔츠, 팔꿈치까지 걷은 소매, 아래에 `trunks` | 판 2장은 몸통 위, 소매는 위팔 바로 위에 쌓아 팔과 함께 앞뒤 순서를 따름 |

- 앉은 자세의 반바지는 의자 윗면에서 잘림

### 일상복 (garments.py, outfit="dressed")

옷은 몸의 실제 형태에서 재단한다. 몸통 윤곽을 여유분만큼 키운 뒤 목선과 밑단 사이 띠로 자르고, 소매와 바짓가랑이는 뼈를 따라 놓인 통(관절 위치 L: 0 뿌리, 1 팔꿈치나 무릎, 2 손목이나 발목)으로 작도한다. 같은 코드가 정면, 3/4, 뒷모습, 옆모습, 앉기, 눕기 자세에 그대로 적용된다.

| 상의 | 목선 | 소매 끝 L | 밑단 | 세부 |
|---|---|---|---|---|
| `tee` | 크루 | 0.48(반소매) | 골반 위, 하의 위로 내어 입음 | 목 밴드, 팔꿈치 없음 |
| `longsleeve` | 크루 | 1.93(손목) | 골반 위 | 목 밴드, 팔꿈치 안쪽 주름 |
| `shirt` | 칼라 | 1.88 | 하의 위 | 뾰족한 칼라 2장, 단추 여밈, 소맷부리 |
| `blouse` | V넥 | 1.86 | 하의 안으로 넣어 입음 | 어깨에서 허리로 흐르는 주름, 소맷부리 |

| 하의 | 허리 | 끝 L | 형태 | 세부 |
|---|---|---|---|---|
| `jeans` | 골반 | 1.93 | 다리에 붙는 통 | 허리 밴드, 앞 지퍼선, 앞주머니, 안쪽 솔기, 노란 스티치, 무릎 뒤 주름 |
| `slacks` | 허리 | 1.95 | 무릎 아래 일자 | 허리 밴드, 지퍼선, 주머니, 무릎 주름 |
| `skirt` | 허리 | 0.86(무릎 위) | 밑단으로 퍼짐 | 다리 사이를 잇는 천, 허리에서 밑단으로 흐르는 주름 |
| `long_skirt` | 허리 | 1.80(발목 위) | 크게 퍼짐 | 같음 |

- 가슴은 옷 아래에서 별도 볼륨으로 부풀어 광택과 그림자를 받음
- 소매는 팔과 함께 쌓여 팔의 앞뒤 순서를 따르고, 몸통 조각은 앞쪽 팔 아래에 그려짐
- 뒷모습: 높은 뒷목선, 셔츠 요크와 박스 주름과 뒷칼라, 블라우스 등 솔기, 청바지 요크와 뒷주머니, 슬랙스 입술 주머니, 치마 지퍼와 밑단 트임
- 옆모습: 옆선 솔기, 앞목에서 뒷목으로 이어지는 목선(`SIDE_NECKLINES`), 앞주머니 사선, 바깥 솔기, 먼 쪽 바짓가랑이는 별도 도형으로 어둡게
- 재단 수치는 `garments.py`의 `TOP_CUT`, `BOTTOM_CUT`, `NECKLINES`에서 조정, 새 옷은 표에 1줄 추가

| 신발 | 형태 | 정면, 옆, 뒤 |
|---|---|---|
| `sneakers` | 흰 고무창, 끈, 뒤꿈치 보강과 당김 고리 | 3종 |
| `boots` | 발목 위까지 오는 목, 굽 | 3종 |
| `heels` | 발등이 드러나는 펌프스, 가는 굽, 발이 발끝으로 기울어 길어짐 | 3종 |

- 신발 밑창 깊이(`SHOES[...]["sole_y"]`)가 `figure.ground_y()`에 반영됨

### 자세

`pose`는 프리셋 이름 또는 `FigurePose` 객체다. 정면과 3/4 프리셋은 `showcase`, `contrapposto`, `arms_up`, `seated`, `reclining`, `akimbo`, `heroic`, `standing`, `phone`, `coffee`, `point`, `desk`이고 옆모습 프리셋은 `side_stand`, `walk`, `side_seated`, `side_phone`이다. 뒷모습은 아무 프리셋에 `dataclasses.replace(POSES["akimbo"], view="back")`처럼 시점만 바꿔 적용한다. 모든 프리셋은 여성과 남성에 공통으로 적용된다. 각도 단위는 도이며 0은 수직 아래, 양수는 화면 오른쪽이다. 왼쪽과 오른쪽은 항상 관찰자 기준이다.

| FigurePose 필드 | 의미 |
|---|---|
| `view` | `front`, `back`(뒷모습), `side`(옆모습) |
| `facing` | `side`에서 몸이 향하는 화면 방향, +1 오른쪽, -1 왼쪽 |
| `turn` | 3/4 시점의 정도 -1..1, 양수는 몸이 화면 오른쪽을 향함, 권장 범위 -0.7..0.7 |
| `lean` | 몸통과 머리 전체를 골반 중심으로 기울이는 각도, 팔다리 각도는 화면 기준이라 따로 지정 |
| `seated` | True는 골반 아래에 의자에 눌린 엉덩이 덩어리 추가 |
| `pelvis_tilt` | 골반 기울기, 양수는 오른쪽 골반이 내려감(왼다리 지지) |
| `chest_tilt` | 어깨선 기울기, 골반과 반대 부호가 자연스러움 |
| `spine_shift` | 흉곽 중심의 좌우 이동(hu) |
| `head_tilt`, `head_yaw` | 머리 기울임과 좌우 회전 |
| `left_thigh`, `left_shin`, `right_thigh`, `right_shin` | 허벅지와 정강이 방향 |
| `left_leg_scale`, `right_leg_scale` | (허벅지, 정강이) 단축 비율, 1은 원래 길이 |
| `left_upper_arm`, `left_forearm`, `right_upper_arm`, `right_forearm` | 위팔과 아래팔 방향, 절댓값 90 초과는 든 팔 |
| `left_arm_scale`, `right_arm_scale` | (위팔, 아래팔) 단축 비율 |
| `left_arm_front`, `right_arm_front` | True는 몸통 앞, False는 몸통 뒤, None은 먼 쪽 팔을 자동으로 뒤에 배치 |
| `left_hand`, `right_hand` | `relaxed`, `open`, `hidden`, `fist`(주먹), `point`(검지로 가리킴), `grip`(물건을 쥠, `*_item` 표시) |
| `left_wrist`, `right_wrist` | 손목 꺾임 각도, 아래팔 방향에서 손을 추가로 돌림, 양수는 화면 오른쪽 |
| `left_foot_turn`, `right_foot_turn` | 발끝 벌림 각도, 40 이상은 옆에서 본 발로 작도 |
| `left_foot_pitch`, `right_foot_pitch` | 옆모습의 발 기울기, 양수는 발끝 들림(뒤꿈치 착지), 음수는 발끝 내림 |

- `showcase`는 지지 다리 쪽으로 골반을 밀어내고 한 손은 머리, 한 손은 허리에 둔 자세
- `akimbo`는 양손을 허리에 얹고 팔꿈치를 벌린 자세, 손목을 꺾어 손이 골반 위로 내려옴
- `heroic`은 오른다리로 서고 왼다리를 바깥으로 내놓은 고전 입상 자세
- `seated`는 상자에 걸터앉아 무릎을 오른쪽으로 모은 자세, 소품 위치는 `figure.seat_y()`
    + 허벅지는 `*_leg_scale`로 단축하고 꺾인 다리는 허벅지를 앞에 그려 둥근 끝이 무릎이 됨
    + 허벅지 단축 비율이 `FORESHORTENED_THIGH`(0.6) 미만인 정면 앉기(`desk`)도 정강이와 일직선이어도 두 도형으로 분리하여 무릎을 작도
    + 정면으로 향한 허벅지는 중간 굵기(`THIGH_GIRTH_T`)를 무릎까지 유지, 바지와 치마에는 무릎 끝선과 아래 음영 추가(`garments.KNEE_*`)
- `reclining`은 왼쪽 팔꿈치로 상체를 받치고 옆으로 누운 자세, 바닥면 위치는 `figure.rest_y()`
    + `lean`을 바꾸면 팔꿈치가 바닥에서 떨어지므로 `left_upper_arm`과 함께 조정
    + 누운 자세의 화면 배치는 `top = 골반 높이 - 3.85 * unit`으로 계산
- `phone`은 가까운 손에 쥔 휴대폰을 내려다보는 자세, `coffee`는 머그를 가슴 앞에 든 자세, `point`는 한 손을 허리에 두고 옆을 가리키는 자세
- `desk`는 정면으로 책상에 앉아 아래팔을 책상 위에 놓은 자세, 책상은 `figure.parts(inserts=[...], overlays=[...])`로 몸과 앞팔 사이에 끼움
    + `inserts`는 몸 뒤, 앞팔 앞에 그릴 도형(책상), `overlays`는 앞팔 앞, 얼굴 뒤에 그릴 도형(노트북 덮개)
    + 예제는 `examples/desk.py`의 `study()`
- 3/4 시점은 회전 계산 없이 작화 규칙으로 작도
    + 먼 쪽 반신 폭 축소, 가까운 쪽 소폭 확대, 먼 쪽 가슴이 윤곽 밖으로 돌출, 가까운 쪽 허벅지 위에 엉덩이 곡선 추가, 먼 쪽 팔은 몸통 뒤 배치
- 콘트라포스토는 `pelvis_tilt`와 `chest_tilt`를 반대 부호로, `spine_shift`를 지지 다리 쪽으로 지정
- 카메라 쪽으로 나오거나 물러나는 팔다리는 `*_scale`로 길이를 줄여 단축 표현
- 꺾임이 65도를 넘는 팔다리는 두 도형으로 분리되어 서로 겹쳐 그려짐
- 머리 뒤로 올린 손은 `hidden`으로 두면 머리에 가려진 것으로 처리
    + 들어 올린 팔의 아래팔은 두개골 중심 쪽으로 `HIDDEN_REACH`(0.5)만큼 더 그려 끝이 머리 뒤로 들어감(뒷모습 제외)
- `figure.joint("wrist_left")` 등으로 관절의 화면 좌표 조회, 소품 배치에 사용
- `figure.ground_y()`는 발바닥 높이, 바닥 그림자 배치에 사용
- `figure.seat_y()`는 앉은 자세의 의자 윗면, `figure.rest_y()`는 몸통의 가장 낮은 점(누운 자세의 바닥면)
- 윤곽 수치는 `figure.py` 상단 상수(CHEST, WAIST, PELVIS, THIGH_W, BREAST 등)와 `BODY` 사전에서 조정

### 뒷모습과 옆모습

뒷모습과 옆모습도 회전 계산 없이 작화 규칙으로 그린다.

- 뒷모습(`view="back"`): 정면과 같은 윤곽 위에 등쪽 해부 표지를 작도
    + 척추선, 견갑골 안쪽 가장자리와 아래끝, 척추 옆 기립근, 골반 위 보조개 2개, 엉덩이 사이 골, 엉덩이 아래 주름
    + 무릎 뒤 오금 주름, 종아리 안쪽 갈래, 팔꿈치 끝, 손은 손등이 보이도록 반전
    + 가슴과 쇄골과 목젖은 생략, 견갑골과 엉덩이에 광택
    + 앞으로 감은 팔(`*_arm_front=True`)은 뒷모습에서 몸통 뒤로 들어감
    + 비키니는 등 밴드와 목뒤 리본, 원피스는 깊게 파인 등, 반바지는 엉덩이 솔기, 열린 셔츠는 닫힌 등판(요크, 박스 주름)
- 옆모습(`view="side"`, `side.py`): 프레임의 x가 몸의 앞뒤 방향으로 바뀌고 + 가 몸 앞
    + 몸통은 목, 가슴, 허리 뒤 오목, 배, 엉덩이를 잇는 옆 윤곽 1개(`SIDE_TRUNK`, 깊이 배율 `SIDE_DEPTH`)
    + 여성 가슴은 가슴 앞에서 자라는 물방울 1개, 남성 대흉근은 윤곽에 포함
    + 두 다리는 골반 깊이 중앙의 고관절 1곳, 두 팔은 어깨 1곳에서 시작, 먼 쪽 팔다리를 먼저 조금 어둡게 그림
    + 다리 폭표는 앞(무릎뼈)과 뒤(종아리)가 다름(`SIDE_LEG`), 발은 옆모습, 손은 엄지가 앞을 향한 옆면
    + `right_*`가 가까운 쪽 팔다리, `left_*`가 먼 쪽 팔다리, 각도는 +가 앞으로 내밈
    + 머리는 옆얼굴, 목 위 두개 중심이 목보다 앞(`SIDE_HEAD_FORWARD`)
    + 모든 의상(수영복, 슬립, 반바지, 열린 셔츠, 일상복)이 옆모습 재단을 가짐
- `walk`는 가까운 다리를 앞으로 내딛고 먼 다리로 뒤를 차는 보행 중간 자세, 팔은 다리와 반대로 흔듦
    + `figure.walk(phase, stride, facing, arms)`는 걸음 단계별 자세를 생성
    + `phase` 0은 가까운 다리 착지, 0.25는 두 다리가 지나치는 순간, 0.5는 먼 다리 착지
    + `stride` 0.6은 산책, 1.0은 보통 걸음, 1.3은 빠른 걸음, `arms`는 팔 흔들기 배율
    + 군중은 사람마다 `phase`와 `stride`를 다르게 지정, 예제는 `examples/variety.py`의 `crosswalk()`
- `side_seated`는 의자에 곧게 앉아 손을 허벅지에 얹은 자세, 의자는 `objects.side_chair(앞모서리 x, figure.seat_y(), figure.ground_y(), unit, facing, depth)`
- 정면, 3/4, 옆, 뒤를 한 장에 놓는 캐릭터 시트는 `examples/figure.py`의 `turnaround()`

## 손과 발 (extremities.py)

손가락은 마디 3개(엄지 2개)를 해부학 길이 비율로 배치한다. 손가락과 발가락의 수와 비례가 구조로 고정된다.

```python
Hand(HandSpec(x, y, length=400, angle=0.0, mirror=False, spread=0.35,
              curl=(0.1, 0.15, 0.2, 0.25, 0.3), forearm=True)).parts()
Foot(FootSpec(x, y, unit=520, angle=0.0, mirror=False, view="front")).parts()
```

| HandSpec 필드 | 의미 |
|---|---|
| `x`, `y` | 손목 위치 |
| `length` | 손목에서 중지 끝까지 px |
| `angle` | 0은 손끝이 화면 아래, `np.pi`는 위 |
| `mirror` | False는 아래로 향한 손의 엄지가 화면 왼쪽 |
| `spread` | 손가락 벌림 0..1 |
| `curl` | (엄지, 검지, 중지, 약지, 소지) 굽힘 0..1 |
| `nails`, `forearm`, `open_wrist` | 손톱 표시, 아래팔 추가, 손목 선 생략 |
| `breadth` | 손바닥과 손가락 폭 배율, 남성 손은 1.12 |
| `shape` | `natural`(마디 굽힘), `fist`(주먹), `point`(검지를 편 주먹), `grip`(물건을 감싸 쥠) |

- `natural`의 굽힘은 마디 길이의 단축으로 표현
- `fist`, `point`, `grip`은 형태 구성으로 작도
    + 손등 덩어리, 접힌 손가락 4개의 끝마디 줄, 손가락 위로 감기는 엄지를 차례로 쌓음
    + `point`는 검지만 펴서 손등 위에 그림
    + `grip`은 손바닥 쪽 `(0, 0.56)` 지점(손 길이 배수)에 물건을 먼저 그린 뒤 손가락이 그 위를 감음
- 쥐는 물건은 `held.py`의 `phone`, `mug`, `book`, `umbrella`, `clear_umbrella`, 크기는 인물의 머리 높이 단위(`held.ITEMS[name](grip_point, unit, name)`)
    + 우산은 주먹 아래 손잡이 고리, 주먹에서 위로 곧은 대, 머리 위 돔 덮개로 작도(`held.UMBRELLA` 수치)
    + 덮개 외곽은 돔 옆모습 윤곽, 아래 테두리는 납작한 타원 아래 반쪽, 보이는 살은 옆모습 윤곽을 살 각도의 코사인만큼 좁힌 선
    + `clear_umbrella`는 반투명 비닐 덮개로 뒤 배경이 비침
    + 아래팔을 세워(`*_forearm` 170-180) 주먹을 얼굴 옆에 두면 대가 머리를 비켜 지나감
- 제스처 예제는 `examples/hands.py`의 `gestures()`
- 발은 `view="front"`(정면), `view="side"`(옆모습), `view="back"`(뒤꿈치) 3종, `unit`은 소속 인물의 머리 높이 px
    + `FootSpec.shoe`, `shoe_color`로 신발을 신김
    + `FootSpec.scale`은 발 크기 배율, 남성 발은 1.08
    + `mirror=False`는 엄지발가락과 발끝이 화면 왼쪽

## 풍경 (landscape.py)

풍경은 뒤에서 앞으로 쌓는 깊이 층이다. 먼 층일수록 밝고 푸르게, 능선은 매끄럽게, 층 아래에는 안개를 둔다.

```python
img = build_landscape(LandscapeSpec(width=1280, height=896, seed=3))
save(finish(img, "painterly", seed=1), "lake.png")
```

| LandscapeSpec 필드 | 의미 |
|---|---|
| `horizon` | 지평선 높이 비율 |
| `sky` | 하늘 그러데이션 `[(y비율, 색), ...]` |
| `sun`, `sun_color` | 해 위치 (x, y) 비율, None은 해 없음 |
| `haze`, `far`, `near` | 안개색, 가장 먼 능선색, 가장 가까운 능선색 |
| `ridges`, `peaks` | 능선 수, 봉우리 날카로움 0..1 |
| `cloud_cover` | 구름 양 0..1 |
| `lake`, `trees`, `grass_color` | 호수, 나무 표시와 풀색 |

다른 구성이 필요하면 아래 부품 함수를 직접 조합한다.

| 함수 | 용도 |
|---|---|
| `sky(h, w, stops, sun, sun_color, sun_size, glow)` | 하늘과 해 |
| `clouds(img, coverage, y_range, color, shadow, scale, seed)` | 구름 |
| `ridge_line(width, base, amplitude, roughness, seed, scale, peaks)` | 능선 높이 배열 |
| `ridge_layer(img, ridge, color, mist_color, mist, texture, slope_light)` | 능선 아래 채움 |
| `water(img, y0, reflect_strength, tint, ripple, sparkle, sun_x)` | 수면 반영과 윤슬 |
| `conifer(img, x, base_y, height, color)`, `tree_line(img, ridge, color, density, size)` | 침엽수 |
| `grass(img, y0, color, blade, count)` | 전경 풀 |

## 도시 (city.py)

1점 투시 거리. 건물 정면과 노면을 평면도로 먼저 그린 뒤 소실점으로 물러나는 사각형에 투영한다. 태양 방향 1개와 하늘 환경광으로 양지 쪽 건물, 음지 쪽 건물, 노면 그림자를 일치시킨다. 간판, 가로수, 가로등, 차량, 행인, 전신주는 거리순으로 정렬해 먼 것부터 그린다. 거리 단위는 미터다.

```python
img = build_city(CitySpec(width=1280, height=896, time="day", seed=2))
save(finish(img, "anime"), "street.png")
```

| CitySpec 필드 | 의미 |
|---|---|
| `horizon`, `vanish_x` | 지평선 높이와 소실점 가로 위치 비율 |
| `focal` | 초점거리(폭 대비), 작을수록 광각 |
| `eye_height` | 눈높이 m |
| `road_half`, `sidewalk` | 차도 반폭과 인도 폭 m |
| `time` | `day`, `golden`, `dusk`, `night` |
| `sky`, `lit` | 하늘색과 불 켜진 창 비율 직접 지정 |
| `wet_road` | 젖은 노면 반사 강도, 0은 마른 노면 |
| `signs`, `trees`, `cars`, `people` | 요소별 밀도 배율, 0은 제거 |
| `wires` | 전신주와 전선 표시 |
| `depth` | 거리 길이 m |

- 건물 유형은 조적 벽체, 유리 커튼월, 발코니, 띠창 4종이며 `seed`에 따라 배치
- 비 온 저녁은 `time="dusk", wet_road=0.55`, 맑은 낮은 `time="day"` 조합
- `City(spec).build()`는 (그림, 발광 지도)를 반환, 발광 지도에 직접 블룸을 적용할 때 사용
- `City.P(x, y, z)`는 거리 공간의 점을 화면 좌표로 변환, 인물이나 소품을 투시에 맞춰 배치할 때 사용
- `City.px_per_m(z)`는 거리 z에서의 미터당 픽셀, 전경 인물의 `unit` 계산에 사용

## 현대 사물 (objects.py)

사선 투상 상자 작도로 그린다. 정면은 실제 모양 그대로, 깊이는 고정된 사선 방향으로 평행 이동한다. 소실점, 회전, 깊이값은 사용하지 않는다. 단위는 10 cm, x는 오른쪽, y는 위, z는 화면 안쪽이며 책상면은 y = 0이다.

```python
from codepaint.subjects import objects as ob
desk = ob.Desk(x=800, y=800, unit=62, depth=(0.30, -0.42))
parts = ob.plant(desk, 7.6, 5.4) + ob.monitor(desk, -1.6, 3.4, glow=0.3) + ob.mug(desk, -5.6, 0.0)
scene.add(parts)                 # 뒤(z가 큰 사물)부터 앞으로 추가
```

| Desk 인자 | 의미 |
|---|---|
| `x`, `y` | 책상면 원점(0, 0, 0)의 화면 위치 |
| `unit` | 10 cm당 px |
| `depth` | 깊이 1단위의 화면 이동량, x가 양수면 오른쪽 옆면, 음수면 왼쪽 옆면이 보임 |
| `light` | 사물 공간에서 광원을 향하는 방향, 기본은 왼쪽 위 앞 |

| 군 | 함수 | 주요 인자 |
|---|---|---|
| 컴퓨터 | `laptop`, `monitor`, `keyboard`, `mouse` | `screen_kind`(`desktop`, `code`, `video`, `off`), `open_deg`, `glow`, `width`, `color` |
| 휴대 기기 | `smartphone`, `tablet`, `headphones`, `camera` | `upright`(세운 휴대폰), `screen_kind`(`home` 포함), `cushion`, `trim` |
| 책상 소품 | `mug`, `desk_lamp`, `plant`, `books` | `drink`, `steam`, `light`(조명 빛 웅덩이), `pot`, `leaf`, `colors` |
| 생활 가전 | `tv`, `speaker`, `gamepad` | `screen_kind`, `glow`, `grille`, `accent` |
| 가구 | `chair`, `side_chair` | `seat_h`, `frame`(사무용 의자), `depth`, `facing`(옆에서 본 의자) |

- `laptop(..., facing="away")`는 화면 대신 덮개 뒷면과 로고를 작도, 책상 너머에 앉은 인물 앞에 놓을 때 사용
- `side_chair`는 사선 투상 없이 정확한 옆면으로 작도하며 등받이는 앉은 인물의 뒤쪽에 섬

- 모든 사물 함수의 위치 인자는 `(desk, x, z)`이며 x는 사물 중심, z는 사물 앞 모서리
- 면 색은 광원과 면 방향으로 결정: 윗면이 가장 밝고 정면이 중간, 빛 반대 옆면이 가장 어두움
- 원통(머그, 화분, 조명 받침)은 원통 축에 짧은축이 놓인 타원으로 작도하고 옆면은 빛에서 그림자로 쓸어내림
- 키, 버튼, 화면 내용은 놓인 면의 좌표로 배치되어 면의 사선을 따름
- 사물마다 책상에 빛 반대쪽으로 밀린 부드러운 접지 그림자가 자동 추가
- 화면 내용은 `screen()`, 상자는 `box()`, 원통은 `cylinder()`로 새 사물을 조립
- 장면 예제는 `examples/desk.py`의 `build()`, 15종 목록은 `catalog()`

## 투샷 (pair.py)

두 사람을 한 장면에 놓는 구도 함수 4종이다. a는 왼쪽, b는 오른쪽에 서고 각자 `ident`를 받아 도형이 섞이지 않는다. 맞닿는 팔은 2관절 역산(`reach`)으로 손이 목표점에 놓이도록 각도를 구한다.

```python
from codepaint.subjects import pair
two = pair.holding_hands(her_spec, his_spec, cx=700, gap=2.1, front="b")
scene.add(two.parts)             # 뒤에서 앞 순서, two.a와 two.b는 Figure
```

| 함수 | 구도 | 작도 방식 |
|---|---|---|
| `side_by_side(a, b, cx, gap=1.6, front="b")` | 어깨를 붙이고 서로 조금 돌아선 두 사람 | 앞 인물(`front`)을 나중에 그림 |
| `holding_hands(a, b, cx, gap=2.1, front="b")` | 손잡기 | 두 손이 골반 아래 중간점에서 만남, 앞 인물의 손이 `grip`으로 뒤 인물의 손을 감쌈 |
| `arm_over_shoulder(a, b, cx, gap=1.35)` | 어깨동무 | a의 아래팔이 b의 목 뒤로 어깨선을 따라 놓이고 손은 b의 먼 쪽 어깨 위에 걸침, 손만 b의 `overlays`로 이동 |
| `conversation(a, b, cx, gap=3.6)` | 3/4로 마주 보고 대화 | a는 머그를 든 채 듣고 b는 펼친 손으로 말함 |

- `cx`는 두 사람 사이 중심의 화면 x, `gap`은 두 골반 중심 사이 거리(hu)
- 두 사양의 `unit`과 `top`은 호출 전에 맞춤
    + 키 차이는 `top`으로 표현, 남성은 머리 높이의 0.3-0.5배 위가 자연스러움
    + 원근 장면에서는 `Camera.fit()`으로 같은 깊이에 맞춤
- `reach(figure, side, target, elbow)`는 손목을 목표 화면점에 놓는 (위팔, 아래팔) 각도를 반환
    + `elbow="out"`은 몸 바깥으로, `"up"`과 `"down"`은 높은 쪽과 낮은 쪽 팔꿈치를 선택
- `mirrored(pose)`는 좌우를 바꾼 자세, 두 사람이 서로를 향할 때 한 자세를 뒤집어 사용
- 세 명 이상은 `FigureSpec.ident`를 각각 다르게 주고 뒤에 선 사람부터 `scene.add`
- 손 파츠에는 `hand_left`, `hand_right` 태그가 붙어 다른 인물의 도형 순서 안으로 옮길 수 있음

## 원근 무대 (stage.py)

1점 원근 작도 틀이다. 상자의 앞면은 화면과 나란한 실형이고 깊이 모서리는 지평선 위 소실점 1개로 모인다. 단위는 미터, x는 시선 오른쪽, y는 바닥에서 위, z는 화면 안쪽 깊이다.

```python
from codepaint.subjects import stage as st
cam = st.Camera(1500, 1000, eye=1.3)                  # 눈높이 1.3 m, 지평선은 화면 높이의 0.42
room = st.Room(cam, width=6.4, depth=7.5, floor_kind="planks")
scene.add(room.parts(), room.window(-2.6, -0.4, 0.9, 2.3), st.sofa(cam, "sofa", 0.0, 6.0))
spec = cam.fit(spec, "standing", x=-0.6, z=4.0)        # 깊이 4 m에 선 인물의 크기와 위치
```

| Camera 필드와 메서드 | 의미 |
|---|---|
| `horizon`, `vp_x` | 지평선(눈높이)의 화면 y, 소실점의 화면 x |
| `focal` | 1 m 거리의 1 m가 차지하는 px, 기본은 수평 화각 58도, 키우면 망원 |
| `eye` | 눈높이(m), 서 있는 시점 1.5, 앉은 시점 1.2 |
| `P(x, y, z)` | 무대 점의 화면 좌표 |
| `scale(z)`, `unit_at(z)` | 깊이 z의 m당 px, 인물의 머리 높이 px(머리 0.215 m 기준) |
| `floor_y(z)`, `near_z()` | 깊이 z의 바닥 화면 y, 바닥이 화면 아래로 나가는 깊이 |
| `fit(spec, pose, x, z, seat=None, lie=None)` | 인물 사양의 크기와 위치를 깊이 z에 맞춤, `seat`(m)을 주면 그 높이 의자에 앉힘, `lie`(m)를 주면 누운 자세(`reclining`)를 그 높이 면 위에 눕힘 |

| 부품 | 함수 |
|---|---|
| 방 | `Room(cam, width, depth, height, wall, back, floor, ceiling, floor_kind)`, `.parts()`, `.window(...)`, `.picture(...)` |
| 상자 | `box(cam, name, x0, y0, z0, w, h, d, color)`: 보이는 면만 뒤에서 앞 순서로, 윗면 밝게, 옆면 어둡게 |
| 가구 | `table`(사각, `round_top` 원형), `chair`(`facing="away"` 앞에서 본 의자, `"toward"` 뒤에서 본 의자), `sofa`, `shelf`, `rug`, `plant`, `floor_lamp`, `pendant`, `blackboard` |
| 야외 | `Ground(cam)`(하늘, 잔디, 소실점으로 가는 길), `.treeline()`, `tree`, `bench`, `lamp_post` |
| 날씨 | `rain(width, height, count, length, angle, color, alpha, seed)`: 화면 전체 빗줄기, 가까운 빗방울일수록 길고 굵고 밝음, `splashes(cam, x_range, z_range, count)`: 젖은 바닥의 빗방울 고리 |
| 그림자와 반사 | `contact(cam, name, x, z, w, d)`, `figure_shadow(cam, figure, z)`, `reflection(parts, ground_y, color, alpha, blur, squash)`: 젖은 바닥에 비친 도형의 부드러운 실루엣, 반사할 도형보다 먼저 추가 |
| 깊이와 조명 표시 | `placed(parts, depth)`: 가구 1개의 도형에 정렬 깊이 기록, `lit(parts)`: 빛을 내는 도형(전등갓, 전구, 빛 번짐)에 `light` 꼬리표 |

- 상자는 시선 오른쪽에 있으면 왼쪽 옆면이, 눈높이 아래에 있으면 윗면이 보이도록 자동 선택
- 가구 함수의 위치 인자는 (중심 x, 앞 모서리 z)
- 가구 함수는 모든 도형에 정렬 깊이(`Part.depth`)를 기록
    + 서서 뒤에 서는 가구(탁자, 상자, 책장)는 앞 모서리 깊이
    + 앉는 가구(의자, 소파, 벤치)는 앞 모서리에서 깊이의 `SIT_SHARE`(0.6)만큼 뒤
    + 바닥에 붙은 것(러그, 바닥 그림자)은 `FLOOR`로 항상 인물 아래
    + 다른 가구 위에 놓인 물건(책상 위 모니터)은 받치는 가구와 같은 깊이로 `placed` 지정
- 바닥 판재와 타일 줄눈은 소실점으로 모이는 선과 깊이별 가로선으로 작도
- 인물보다 앞에 있는 가구(인물 앞 탁자)는 인물 뒤에 추가하고, 인물이 기대는 책상은 `Figure.parts(inserts=...)`로 몸과 팔 사이에 끼움

## 장면 템플릿 (scenes.py)

| 함수 | 장소 | 인물 자리(`spots`) | 구성 |
|---|---|---|---|
| `cafe(w, h)` | 카페 | `left_seat`, `right_seat`(옆모습으로 마주 앉기) | 벽돌 뒷벽, 거리가 보이는 창, 카운터와 메뉴판, 펜던트 조명, 앞쪽 원형 탁자(`front`) |
| `classroom(w, h)` | 교실 | `seat_a`, `seat_b`(정면으로 앉기) | 사물함, 게시판, 시계, 왼쪽 벽 창, 빈 책상 줄, 두 자리의 책상(`inserts`) |
| `living_room(w, h)` | 거실 | `sofa_left`, `sofa_right` | 소파, 러그, 앞 탁자(`front`), 창, 그림, 책장, 스탠드, 화분 |
| `park(w, h)` | 공원 | `path` | 하늘, 먼 나무 띠, 잔디, 길, 나무, 벤치, 가로등, 앞쪽 나무(`front`) |
| `office(w, h)` | 고층 사무실 | `desk_seat`(정면으로 앉기), `stand` | 도시 고층 건물이 보이는 긴 창, 천장 조명판, 모니터 책상 줄과 칸막이, 화분, 수납장, 앞 책상(`inserts`)과 노트북 덮개(`overlays`) |
| `bedroom(w, h)` | 아침 침실 | `bed_edge`(침대 앞 모서리에 앉기) | 커튼 달린 뒷벽 창, 바닥의 햇빛 조각, 헤드보드와 이불과 베개의 2인용 침대, 협탁 2개와 스탠드, 그림, 러그 |
| `rooftop(w, h)` | 노을 옥상 | `rail`(난간 앞에 서기) | 노을 하늘과 낮은 해(`image`), 역광의 먼 도시 실루엣 3겹, 콘크리트 바닥, 난간벽과 손잡이, 줄 조명, 물탱크, 실외기 |
| `street(spec, rain)` | 도시 거리(`CitySpec` 시간대) | `road`(앞쪽 도로 중앙) | `city.py` 거리 그림(`image`)과 같은 카메라, `rain=True`면 빗줄기와 빗방울 고리(`front`) |
| `rainy_street(w, h)` | 비 오는 밤 거리 | `road` | 밤, 젖은 도로 반사, 간판 밀도 상향, 비 |
| `beach(w, h)` | 해변 | `shore` | 하늘과 구름, 바다 띠와 파도선, 모래(`image`), 파라솔, 수건 |

- 반환값 `Set`: `cam`, `back`(인물 뒤), `front`(인물 앞), `spots`(이름별 (x, z, 의자 높이 또는 None)), `inserts`(자리별 몸과 팔 사이 도형), `overlays`(자리별 팔과 얼굴 사이 도형), `image`(야외 장소의 배경 그림 또는 None)
- 그리는 순서는 `image`(있으면 `Scene.set_background`), `back`, 인물(뒤에 있는 사람부터), `front`
- `street()`는 거리 그림의 카메라 수치(`horizon`, `vanish_x`, `focal`, `eye_height`)를 무대 카메라에 그대로 옮겨 `cam.fit`으로 세운 인물이 도로 위에 맞게 섬
    + 낮은 시점은 `CitySpec(eye_height=0.5, horizon=0.62)`처럼 지정, 화면 아래 끝까지 도로를 채움(`GROUND_FILL`)
- `street()`와 `rainy_street()`를 제외한 템플릿은 카메라 키워드(`horizon` px, `eye` m, `focal` px, `vp_x` px)를 받음
    + 예: `scenes.cafe(1500, 1000, eye=1.55, horizon=300)`은 선 사람 눈높이의 근접 구도
    + 가구와 벽은 바뀐 카메라로 다시 배치되며 `spots`의 무대 좌표는 그대로 유효
- `Set.arrange((z, parts), ...)`는 인물을 가구 사이에 깊이 순서로 끼운 그리기 목록을 반환
    + 벽, 바닥, 창, 벽걸이처럼 깊이가 없는 도형과 바닥 도형이 먼저 그려짐
    + 가구와 인물은 먼 것부터 가까운 것 순서, 같은 깊이면 가구 다음에 인물
    + 사용법: `scene.add(s.arrange((z1, fig1.parts()), (z2, [shadow, *fig2.parts()])), s.front)`
    + 책상 줄 사이에 선 인물은 앞 책상과 의자에 다리가 가려짐
- `Set.night(room, people, lamps, tint)`는 같은 장소의 밤 장면을 새 `Set`으로 반환
    + 모든 색을 밤 색(`NIGHT_TINT`)으로 `room` 비율만큼 이동, 창유리는 밤하늘, 창밖 경치는 더 어둡게
    + 햇빛 조각(`daylight` 꼬리표)은 제거, 전등과 전구와 천장 조명판(`light` 꼬리표)은 밝기 유지, 빛 번짐은 `lamps`배
    + `front` 맨 앞에 인물까지 덮는 옅은 밤 막(`people`)과 그 위 빛 번짐을 추가
    + 거리는 `CitySpec(time="night")`을 사용하고 `night()`는 실내와 공원, 옥상, 해변에 사용
- 완성 예제는 `examples/scenes.py`의 `cafe()`, `classroom()`, `living_room()`, `park()`, `examples/gallery.py`의 새 장소 6종
- 상황, 포즈, 구도, 그룹샷 시험 21장은 `examples/variety.py`(`BUILDERS`)
    + 3-8인 배치, 근접과 원경, 낮은 시점, 누운 인물, 벤치와 소파의 정면 앉기, 회의 탁자 예시 포함
    + `office_late()`는 밤 사무실(`night()`), 책상 줄 사이를 걷는 인물(`arrange()`, `walk()`) 예시
