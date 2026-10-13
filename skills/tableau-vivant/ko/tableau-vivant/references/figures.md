# 인물

체형, 얼굴, 표정, 자세, 손, 머리카락, 의상, 화장의 지정 방법

## 목차

- 체형과 얼굴
- 표정
- 자세 언어
- 손 목표 지점 (reach)
- 손에 든 사물 (held_by)
- 두 사람 자세 (pairs)
- 여러 사람 줄 (groups)
- 손 모양
- 머리카락
- 모자 (hat)
- 의상
- 화장과 눈 (look)
- 자주 생기는 문제

## 체형과 얼굴

### 프리셋

| 이름 | 특징 |
| --- | --- |
| `woman` | 젊은 성인 여성, 날카로운 턱선, 큰 눈, 모래시계 체형 (기본) |
| `woman_curvy` | 굴곡이 큰 글래머 체형 |
| `woman_slender` | 키가 크고 다리가 긴 모델 체형 |
| `woman_soft` | 부드러운 얼굴형, 평균 체형 |
| `woman_athletic` | 근육질, 날카로운 턱선 |
| `woman_classical` | 고전 회화 비례, 그리스식 콧대, 풍만한 체형 |
| `woman_mature`, `woman_elder` | 중년, 노년 |
| `woman_anime` | 큰 눈, 작은 코와 입, 짧은 턱, 가는 체형. 셀화용 (`stylize: anime` 기본) |
| `man` | 젊은 성인 남성, 각진 턱과 짙은 눈썹, 넓은 어깨와 좁은 허리 |
| `man_athletic` | 근육질. 복근과 가슴 윤곽 음영(`muscle_definition`) 포함 |
| `man_slim` | 마른 체형, 날카로운 턱선 |
| `man_classical` | 고전 조각 비례, 그리스식 콧대, 단련된 몸. 다비드 같은 고전 남성 누드용 |
| `man_mature`, `man_elder` | 중년, 노년 |
| `man_anime` | 긴 다리, 날렵한 턱, 약간 큰 눈. 셀화용 (`stylize: semi` 기본) |
| `androgynous` | 중성적 |

### 체형 축 (`phenotype`, 0-1)

| 축 | 0 | 1 |
| --- | --- | --- |
| `gender` | 남성 | 여성 |
| `age` | 0.77이 18세. 18세 미만 몸은 옷을 입은 모습만 (누드, 속옷, 비키니 거부) | 0.776 청년(약 23세), 0.80(41세), 0.82(56세), 0.97 노년 |
| `muscle` | 적음 | 많음 |
| `weight` | 마름 | 풍만 |
| `height` | 작음 | 큼 |
| `proportions` | 이상 비례 | 평범한 비례 |
| `cupsize`, `firmness` | 작음, 낮음 | 큼, 높음 |
| `african`, `asian`, `caucasian` | 세 값의 비율로 골격 특징 혼합 | |

### 얼굴 양식화 (`stylize`)

모핑으로 닿지 않는 만화적 비례를 얼굴에 적용. 눈과 눈꺼풀, 눈썹이 함께 움직여 메시가 찢어지지 않음

| 값 | 효과 |
| --- | --- |
| `none` | 사실 비례 |
| `semi` | 눈 조금 크게, 코와 입 조금 작게, 아래턱 조금 짧게. 웹툰, 세미실사 |
| `anime` | 눈 크게, 코 작게, 입 좁게, 아래턱 짧고 갸름하게. 애니메 |
| `chibi` | 가장 강한 데포르메 |

- 프리셋에 기본값이 있으면 그 값을 따르고, 인물 객체의 `stylize`가 덮어씀

### 얼굴과 신체 모핑 (`face`, -1에서 1)

254개 축. 전체 목록은 `python scripts/catalog.py shapes`. 자주 쓰는 축

| 목적 | 축 |
| --- | --- |
| 턱선을 날카롭게 | `chin-width-incr` 음수, `chin-bones-incr` 음수, `head-fat-incr` 음수, `l/r-cheek-bones-incr` 양수 |
| 눈을 크게 | `l-eye-scale-incr`, `r-eye-scale-incr` 양수 |
| 눈을 또렷하게 뜸 | `l-eye-height1-incr`, `r-eye-height1-incr` 양수 |
| 눈꼬리를 올림 | `l-eye-corner2-up`, `r-eye-corner2-up` 양수 |
| 코를 작게 | `nose-scale-horiz-incr`, `nose-scale-depth-incr` 음수 |
| 입술을 도톰하게 | `mouth-lowerlip-volume-incr`, `mouth-upperlip-volume-incr` 양수 |
| 목을 가늘게 | `neck-scale-horiz-incr` 음수 |
| 허리와 골반 | `measure-waist-circ-incr` 음수는 잘록하게, `measure-hips-circ-incr` 양수는 넓게 |
| 남성적 상체 | `torso-vshape-incr`, `measure-shoulder-dist-incr`, `torso-muscle-pectoral-incr`, `torso-muscle-dorsi-incr` 양수 |
| 팔다리 근육 | `l/r-upperarm-muscle-incr`, `l/r-upperarm-shoulder-muscle-incr`, `l/r-upperleg-muscle-incr` 양수 |
| 이마뼈와 턱 | `eyebrows-trans-forward` 양수는 굵은 눈썹뼈, `chin-bones-incr` 양수는 각진 턱 |
| 가슴 | 체형 축 `cupsize`, `firmness`와 `breast-trans-up`, `breast-volume-vert-up` |
| 엉덩이, 허벅지 | `buttocks-volume-incr`, `measure-thigh-circ-incr` |
| 다리 길이 | `upperlegs-height-incr`, `lowerlegs-height-incr` |
| 복부 탄력 | `stomach-tone-incr` |
| 어깨 너비 | `measure-shoulder-dist-incr` |

- 좌우 대칭 축은 `l-`과 `r-`를 같은 값으로 지정
- 프리셋 위에 덮어쓰는 방식. 지정한 축만 바뀜

## 표정

- 프리셋: `neutral`, `soft_smile`, `smile`, `serene`, `eyes_closed`, `serious`, `determined`, `sad`, `surprised`, `angry`, `melancholy`, `smirk`
- 직접 지정은 표정 단위 52개(0-1)의 객체
    + 예: `{"mouthSmileLeft": 0.5, "mouthSmileRight": 0.5, "browInnerUp": 0.3, "jawOpen": 0.2}`
    + 눈 감기 `eyeBlinkLeft/Right`, 시선 `eyeLookUp/Down/In/OutLeft/Right`, 입 `mouthPucker`, `mouthFunnel`, 눈썹 `browDownLeft/Right`, `browOuterUpLeft/Right`

## 자세 언어

뼈 각도를 직접 쓰지 않고 관절의 의미로 기술. 프리셋 이름 또는 객체. 객체에 `preset`을 넣으면 그 위에 덮어씀

```json
"pose": {
  "preset": "contrapposto",
  "head": {"turn": 20, "tilt": 6, "nod": 4},
  "arm.R": {"lift": 40, "forward": 60, "elbow": 80},
  "hand.R": "graceful"
}
```

### 프리셋

| 분류 | 이름 |
| --- | --- |
| 서기 | `stand`, `contrapposto`, `s_curve`, `arms_behind_head`, `look_over_shoulder`(뒷모습용, 카메라 `yaw` 150-180), `hand_on_hip`, `hands_on_hips`, `arms_crossed`, `hand_on_chest`, `hair_touch`, `thinking`, `venus`, `pray`(가슴 앞 합장), `a_pose` |
| 사물 들기 | `read_book`(펼친 책을 두 손으로), `read_seated`(의자에 앉아 책 읽기), `hold_cup`(오른손에 컵), `look_at_phone`(오른손 휴대폰을 내려다봄). 사물은 `held_by`로 손에 쥠 (아래 손에 든 사물) |
| 흡연 | `smoke`(담배 든 오른손을 내리고 고개 숙임), `smoke_inhale`(담배 든 손을 턱 옆으로), `sit_smoke`(앉아서 무릎에 팔꿈치, 담배는 무릎 사이). `cigarette`를 `held_by`로 쥠 |
| 남성 서기 | `david`(한 손을 어깨에 올린 고전 콘트라포스토), `heroic`(주먹을 허리에, 다리 벌림), `hands_in_pockets`(양손을 바지 주머니에. 옷 입은 인물용) |
| 동작 | `walk`, `run`, `jump`(공중에 뜬 상태), `fight_stance`, `wave`, `arms_up`, `reach_up`, `point_forward` |
| 앉기 | `sit_chair`, `sit_crossed_legs`, `sit_floor`, `kneel`, `kneel_sit`(발뒤꿈치에 앉음), `seated_side`(바닥에 비스듬히 앉음) |
| 눕기 | `recline`(옆으로 기대어 누움), `lie_back` |

- 손이 몸 쪽으로 향하는 `reach`에서 팔뚝이 몸통에 파묻히면 엔진이 팔꿈치를 바깥으로 필요한 만큼 돌림
- 의자에 앉는 자세는 의자 사물을 인물 뒤쪽(`at: [0, 0.12, 0]`)에 배치
- 긴 의자나 단 위에 눕히거나 앉히려면 인물 `position`의 z를 그 윗면 높이로 지정
- 인물은 가장 낮은 신체 지점이 지면에 닿도록 자동 배치
    + 자세에 `"airborne": 0.3`을 넣으면 그 높이만큼 공중에 뜸 (`jump`에 기본 내장)
- 인물 방향 `facing`은 각도 대신 바라볼 대상을 받음: 사물 이름(`"table"`), 다른 인물 이름, 장면 좌표 `[x, y]`
    + 사물의 `rotate_deg`도 같은 방식으로 지정 가능 (의자를 탁자 쪽으로)

### 관절

| 키 | 필드 | 의미 |
| --- | --- | --- |
| `body` | `lean`, `tilt`, `turn` | 골반부터 몸 전체. 앞으로 숙임, 인물 왼쪽으로 기울임, 왼쪽으로 돌림 |
| `torso` | `bend`, `side`, `twist` | 척추 전체에 분배 |
| `head` | `nod`, `tilt`, `turn` | 목과 머리에 분배. `nod` 양수는 숙임 |
| `arm.L`, `arm.R` | `lift` | 0 늘어뜨림, 90 수평, 180 위로 |
| | `forward` | 90 앞, 0 옆, -90 뒤 |
| | `twist` | 양수는 안쪽 회전. 팔꿈치를 굽혔을 때 팔뚝이 몸 앞을 가로지름 |
| | `elbow` | 0 폄, 150 최대 굽힘 |
| | `forearm_twist`, `wrist`, `wrist_side`, `shrug` | 손바닥 방향, 손목 굽힘, 손목 옆 꺾임, 어깨 으쓱 |
| `leg.L`, `leg.R` | `forward` | 엉덩관절 굽힘. 90은 허벅지 수평 |
| | `side`, `twist` | 벌림, 발끝 바깥 회전 |
| | `knee`, `ankle`, `foot_turn` | 무릎 굽힘, 발끝 내림, 발 돌림 |
| `gaze` | `yaw`, `pitch` | 눈동자 방향 |
| `bones` | `{뼈 이름: [rx, ry, rz]}` | 개별 뼈 직접 회전. 최후 수단 |

- `.L`은 인물 기준 왼쪽. 화면에서는 오른쪽에 보임

## 손 목표 지점 (reach)

손을 특정 위치에 놓을 때는 각도를 추측하지 않고 목표를 지정. 엔진이 어깨와 팔꿈치 각도를 계산

```json
"pose": {"preset": "stand",
         "reach.R": {"to": "chin", "elbow": "down", "offset": 0.03},
         "reach.L": "hip.L"}
```

| 필드 | 설명 |
| --- | --- |
| `to` | 신체 지점 이름, 인물 자체 좌표 `[x, y, z]`, 또는 다른 인물의 지점 `"이름:지점"` (예: `"b:shoulder.R"`) |
| `world` | `to` 대신 장면 좌표 `[x, y, z]`로 지정 |
| `elbow` | 팔꿈치가 향하는 쪽: `down`, `out`, `back`, `up`, `forward` |
| `elbow_world` | `elbow` 대신 장면 축 방향 `[x, y, z]`로 지정 |
| `offset` | 피부에서 띄우는 거리. 기본 0.02 |
| `lay` | `true`면 손바닥을 그 지점의 피부에 펴서 얹음. 손가락은 팔뚝이 지나는 방향을 따라 놓임 (가슴, 허리, 다른 인물의 어깨) |

- 신체 지점: `head_top`, `forehead`, `temple.L/R`, `cheek.L/R`, `mouth`, `chin`, `ear.L/R`, `nape`, `throat`, `shoulder.L/R`, `shoulder_top.L/R`(어깨 윗면, 얹은 손 자리), `chest`, `heart`, `breast.L/R`, `ribs.L/R`, `belly`, `waist.L/R`, `pocket.L/R`, `hip.L/R`, `pelvis`, `small_of_back`, `back_upper.L/R`, `back_lower.L/R`, `spine_upper`, `spine_lower`, `thigh.L/R`, `knee.L/R`
- 다른 인물의 지점을 쓰려면 그 인물이 먼저 추가되어 있어야 함 (`figures` 배열에서 앞에 둠)
- `reach`를 쓴 팔은 `lift`, `forward`, `twist`, `elbow`가 무시됨. `wrist`와 `forearm_twist`는 유효
- `lay`를 쓴 손은 손목 굽힘과 팔뚝 회전도 엔진이 정함. 손 모양은 `rest`나 `flat`이 자연스러움
- 얼굴 근처 목표는 손이 얼굴을 가리기 쉬움. 밑그림에서 확인 후 `offset`을 키우거나 목표를 `ear`, `temple`로 변경

## 손에 든 사물 (held_by)

사물에 `held_by`를 주면 좌표 계산 없이 손에 쥠. 인물이 먼저 추가되어 있어야 함 (사양 파일에서는 자동 처리)

```json
"props": [{"kind": "book", "held_by": "a:hands", "open": true},
          {"kind": "mug", "held_by": "b:hand.R"}]
```

| 값 | 의미 |
| --- | --- |
| `이름:hand.R`, `이름:hand.L` | 한 손. 컵, 병, 잔은 세워서 손에 감싸 쥠. 손바닥이 위를 보면 손바닥 위에 세움 |
| `이름:hands` | 두 손 사이. 책은 두 손바닥에 걸쳐 놓임 |

- 손바닥 위에 눕는 사물: `book`, `phone`, `tablet`, `plate`, `game_controller`. `cigarette`는 검지와 중지 사이. 나머지는 세워서 쥠
- 책은 `"open": true`로 펼친 책
- 짝이 맞는 자세: `read_book`, `read_seated` + 책, `hold_cup` + `mug`나 `takeaway_cup`, `look_at_phone` + `phone`, `smoke`, `smoke_inhale`, `sit_smoke` + `cigarette`
- `rotate_deg`는 손 안에서 사물을 돌림 (머그 손잡이 방향 등)

## 두 사람 자세 (pairs)

몸이 닿는 투샷은 최상위 `pairs` 배열로 지정. 엔진이 두 사람을 배치하고 맞닿는 손을 상대 몸에 맞춰 계산

```json
"pairs": [{"kind": "hold_hands", "facing": 35,
           "a": {"name": "a", "preset": "woman", "pose": "walk", "outfit": "summer_dress"},
           "b": {"name": "b", "preset": "man", "pose": "walk", "outfit": "tshirt_jeans"}}]
```

| `kind` | 모습 | 기본 간격 |
| --- | --- | --- |
| `hold_hands` | 나란히 서서 손을 잡음. a의 왼손과 b의 오른손 | 0.56m |
| `hand_on_shoulder` | a가 b의 가까운 어깨에 손을 얹음 | 0.52m |
| `arm_around` | a가 b의 어깨에 팔을 두르고 b는 a의 허리를 감쌈 | 0.44m |
| `hug` | 마주 보고 포옹. a는 b의 어깨를, b는 a의 허리를 감싸고 고개는 서로 반대쪽 | 0.34m |
| `dance` | 커플 댄스 홀드. a(리드)의 오른손은 b의 등, b의 왼손은 a의 어깨, 반대 손은 맞잡음. 두 사람 모두 상대의 오른쪽 어깨 너머를 봄 | 0.44m |

| 필드 | 설명 |
| --- | --- |
| `a`, `b` | 각 인물의 `figures` 항목과 같은 필드. 기본 화면에서 a가 왼쪽 |
| `at` | 두 사람의 중심 `[x, y]` |
| `facing` | 두 사람 전체의 방향. 0은 카메라 쪽 |
| `distance` | 간격 덮어쓰기 |

- `a`, `b`의 `pose`에 `walk` 같은 자세를 주면 맞닿는 팔만 바뀌고 나머지는 유지됨
- 상대 몸에 닿는 손바닥은 피부에 펴서 얹힘. 상대의 머리카락이 덮인 자리에서는 머리카락 위에 놓이고 손 아래 머리카락은 눌려 납작해짐
- 역할을 바꾸려면 `a`와 `b`를 바꿔 넣음. 예: 남성이 여성 어깨에 팔을 두르려면 남성을 `a`로
- 카메라를 생략하면 두 사람을 모두 담는 구도
- 예제: `seaside_walk_watercolor.json`(손잡고 걷기), `couple_dance_classical.json`(댄스), `pen_wash_park_bench.json`(벤치에 앉은 `arm_around`)

## 여러 사람 줄 (groups)

3명 이상이 한 줄로 서서 옆 사람과 차례로 닿는 군상은 최상위 `groups` 배열로 지정

```json
"groups": [{"kind": "arm_around", "members": [
  {"name": "p1", "preset": "woman_anime", "outfit": "sweater_skirt"},
  {"name": "p2", "preset": "man_anime", "outfit": "hoodie_jeans"},
  {"name": "p3", "preset": "woman_anime", "outfit": "tshirt_jeans"}]}]
```

| 필드 | 설명 |
| --- | --- |
| `kind` | `arm_around`(어깨동무), `hold_hands`(손잡은 줄), `hand_on_shoulder` |
| `members` | 각 인물의 `figures` 항목. 기본 화면에서 왼쪽부터. 이름 생략 시 `p1`, `p2` 순 |
| `at`, `facing` | 줄의 중심과 방향 |
| `spacing` | 옆 사람과의 간격. 생략 시 같은 `kind`의 `pairs` 간격 |

- 이웃한 두 사람마다 `pairs`의 a와 b처럼 닿음. 각자 왼팔은 오른쪽 이웃에, 오른팔은 왼쪽 이웃에 씀
- 양쪽 이웃과 닿는 가운데 사람은 정면을 봄
- 접촉 없는 군상은 `figures`에 여러 명을 넣고 위치와 `facing`을 지정
- 예제: `anime_friends_trio.json`(어깨동무 3명)

## 손 모양

- 프리셋: `relaxed`(기본), `open`, `flat`, `fist`, `point`, `peace`, `grip`, `pinch`, `graceful`, `thumbs_up`, `cigarette`(검지와 중지를 가볍게 모음), `rest`(몸에 얹은 손. 손가락을 모으고 살짝 굽힘)
- 직접 지정: `{"curl": [엄지, 검지, 중지, 약지, 소지], "spread": -1에서 1}`. `curl` 0은 폄, 1은 완전히 굽힘

## 머리카락

```json
"hair": {"style": "long_wavy", "bangs": "side", "part": "left", "color": "auburn",
         "density": 1.0, "length_scale": 1.0, "wind": [0.5, 0, 0]}
```

| 필드 | 선택지 |
| --- | --- |
| `style` | 긴 머리: `long_straight`, `long_wavy`, `very_long`, `shoulder`, `long_male`(어깨 길이 남성 장발) |
| | 단발과 곱슬: `bob`, `pixie`, `curly`, `afro` |
| | 짧은 머리: `buzz`(삭발에 가까움), `short_crop`, `textured_crop`(앞머리를 세운 짧은 머리), `side_part`(옆가르마), `undercut`(옆은 짧게, 윗머리는 뒤로), `slick_back` |
| | 묶은 머리: `ponytail`, `low_ponytail`, `bun`, `chignon`, `man_bun`, 그리고 `bald` |
| `bangs` | `none`, `wispy`, `full`, `side`, `curtain`, `long` |
| `part` | `center`, `left`, `right`, `none`(뒤로 넘김) |
| `color` | 이름 또는 RGB |
| `wind` | 늘어진 머리를 미는 방향과 세기. `[0.5, 0, 0]`은 화면 오른쪽으로 날림 |
| `face_framing` | 0은 앞머리 쪽 머리를 귀 뒤로 넘김, 1은 얼굴 옆으로 흘러내림. 기본 0.2 |

- 머리카락은 자세가 잡힌 뒤 중력 방향으로 자라므로 고개를 숙이거나 누운 자세에서도 자연스럽게 늘어짐
- 앞머리를 제외한 머리카락은 얼굴 앞을 지나지 않도록 엔진이 옆으로 밀어냄
- 묶은 머리(`ponytail`, `bun`, `chignon`)는 얼굴을 가리지 않아 안전
- 짧은 머리는 두피 위 껍질이 부피를 맡고 윗머리 다발이 결을 냄. 스타일링한 머리는 빗은 방향을 유지하며 머리에 붙음

## 모자 (hat)

```json
"hat": "beanie"     또는     "hat": {"style": "beanie", "color": [0.30, 0.10, 0.10]}
```

- `beanie`: 니트 비니. 이마 위에서 뒤통수 아래로 내려가는 선까지 덮고 끝단을 접어 올린 모양. 세로 골지 무늬
- 머리카락 위에 씌워짐. 비니 아래로 긴 머리가 흘러내림
- 기본 색은 짙은 회흑색

## 수염 (beard)

```json
"beard": "short_beard"
"beard": {"style": "full_beard", "color": "auburn"}
```

| 값 | 모양 |
| --- | --- |
| `none` | 없음 (기본) |
| `stubble` | 면도 자국. 턱과 입 주변이 가장 짙고 볼 쪽으로 옅어짐 |
| `short_beard` | 짧게 다듬은 수염. 구레나룻에서 턱까지 |
| `full_beard` | 턱 아래로 풍성하게 내려오는 수염 |
| `goatee` | 입 주변과 턱 |
| `mustache` | 콧수염 |

- 색 기본값은 머리색. 수염 아래에는 면도 자국 채색이 함께 들어가 경계가 자연스러움

## 의상

### 프리셋

| 분류 | 이름 (괄호는 색을 바꿀 때 쓰는 id) |
| --- | --- |
| 없음 | `nude` |
| 속옷, 수영복 | `underwear`(bra, briefs), `briefs`, `trunks`, `swimsuit`, `bikini`(bikini_top, bikini_bottom) |
| 고전 남성 누드 | `perizoma`(perizoma). 골반에 낮게 두른 비스듬한 허리천 |
| 거리 | `hoodie_jeans`(hoodie, hood, pocket, cords, jeans, shoes. 후드를 내린 헐렁한 후드티), `long_coat`(coat, lapels, sweater, trousers, boots. 무릎 길이 울 코트와 터틀넥) |
| 일상 | `tshirt_jeans`(tshirt, jeans, shoes), `tank_shorts`(tank, shorts), `sportswear`(sports_top, leggings, shoes), `sweater_skirt`(sweater, skirt, boots), `blouse_trousers`(blouse, trousers, shoes), `office`(blouse, pencil_skirt, shoes), `shirt_trousers`(shirt, collar, trousers, belt, shoes. 깃이 열린 셔츠를 벨트 바지에 넣어 입음), `suit`(jacket, lapels, shirt, tie, trousers, shoes) |
| 드레스 | `sundress`, `summer_dress`, `little_black_dress`(dress), `evening_gown`(gown) |
| 전통, 고전 | `chiton`(chiton, belt), `hanbok`(jeogori, chima), `kimono`(kimono_top, kimono_skirt, obi), `robe`(robe_top, robe_skirt) |
| 장르 | `bodysuit`, `tactical`(bodysuit, vest, belt, boots) |

- 색 변경: `"colors": {"dress": [0.8, 0.1, 0.2]}`
- 남성 체형(`gender` 0.5 미만)에 여성 재단 프리셋을 지정하면 남성용으로 자동 전환
    + `sportswear`는 티셔츠와 반바지, `swimsuit`는 수영 트렁크, `bikini`는 보드 쇼츠, `underwear`는 남성 속옷
    + `blouse_trousers`와 `office`는 `shirt_trousers`(셔츠와 바지)
    + 색 지정은 원래 id(`sports_top`, `leggings`, `swimsuit`, `bikini_bottom`, `blouse`)로도 적용됨
    + 원래 재단을 그대로 입히려면 의상 객체 배열로 직접 구성
- 앉거나 무릎 꿇으면 치마가 무릎에서 아래로 흘러내리고 바닥에 닿으면 펼쳐짐
- 허벅지, 엉덩이, 허리에 얹은 손은 옷감을 눌러 옷 위에 놓임 (다른 인물의 손도 같음)
    + 팔짱처럼 다른 팔 밑에 끼운 손은 옷을 누르지 않음

### 직접 구성

`outfit`에 의상 객체 배열을 지정. 안쪽 옷부터 바깥 옷 순서

```json
"outfit": [
  {"type": "bottom", "id": "pants", "length": "full", "ease": 0.012, "color": [0.2, 0.2, 0.25]},
  {"type": "top", "id": "shirt", "sleeve": "elbow", "neckline": "v", "bottom": 0.28, "ease": 0.01, "folds": 0.005, "color": [0.9, 0.9, 0.88]},
  {"type": "footwear", "id": "shoes", "style": "ankle_boots", "color": [0.15, 0.1, 0.1]}
]
```

| type | 주요 필드 |
| --- | --- |
| `top` | `sleeve`(none, cap, short, elbow, three_quarter, long), `neckline`, `top`, `bottom`, `ease`, `folds`, `drape`(천이 근육 굴곡을 건너가는 정도. 재킷 40), `drape_floor`(어깨 위에서 여유를 얼마나 남길지 0-1) |
| `bottom` | `length`(brief, short, bermuda, capri, full, footed), `top`, `ease`, `folds` |
| `skirt` | `length`(micro, mini, above_knee, knee, midi, ankle, floor), `flare`, `folds`, `fold_count`, `waist`(0.30 미만이면 골반에 걸침), `wind`, `hem_slant`(한쪽이 올라간 단) |
| `dress` | `top`의 `sleeve`, `neckline`과 `skirt`의 필드를 함께 사용. `bodice_folds` |
| `band` | `top`, `bottom`, `ease`. 허리띠, 오비 |
| `footwear` | `style`(shoes, ankle_boots, boots, socks, stockings) |
| `tie` | 넥타이. `tip`(끝 높이), `ease` |
| `lapel` | 재킷 V 깃. `neckline`, `width`, `over_ease`와 `drape`(아래 재킷과 같은 값), `gap`(재킷 위 높이) |

- `neckline`: `turtle`, `crew`, `boat`, `v`, `deep_v`, `scoop`, `square`, `straps`, `halter`, `strapless`, `one_shoulder`
- `top`, `bottom`은 신체 높이 좌표(미터)
    + 0.72 목 밑, 0.66 어깨, 0.58 겨드랑이, 0.52 가슴, 0.46 밑가슴, 0.36 허리, 0.14 골반, 0.06 가랑이, -0.28 무릎, -0.74 발목
- `ease`는 피부에서 띄우는 거리. 겹쳐 입는 옷은 바깥 옷의 `ease`를 0.004 이상 크게 지정
- `folds`는 주름 깊이(미터). 0.004는 잔주름, 0.02 이상은 깊은 드레이프
- 팔꿈치와 무릎을 굽히면 소매와 바짓단에 모이는 주름이 자동으로 생김. 헐렁한 옷(`ease`가 큰 옷)일수록 깊음
- 상의는 어깨에서 맞고 아래로 갈수록 헐렁해짐. 여유(`ease`)는 주로 가슴 아래와 소매 아래쪽에 들어감
    + 그래서 근육질 체형에 헐렁한 셔츠를 입혀도 어깨가 패드처럼 부풀지 않음
- `drape`는 천이 근육 굴곡을 따라가지 않고 오목한 곳을 건너가게 만듦
    + 정장 프리셋의 재킷과 깃에는 40이 적용됨
    + 소매가 있고 `ease`가 0.008 이상인 상의(블라우스, 티셔츠, 스웨터 등)는 자동으로 10이 적용되어 어깨 위에 천이 내려앉음
    + 몸에 붙는 상의로 두려면 `"drape": 0`

## 화장과 눈 (look)

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `iris_color` | 갈색 | 이름 또는 RGB |
| `iris_size`, `pupil_size` | 1.08, 1.0 | 홍채와 동공 크기 배율 |
| `catchlight`, `catchlight_size` | 0.95, 1.15 | 눈의 반사광 |
| `lip_color`, `lip_strength`, `lip_gloss` | 장밋빛, 0.78, 0.45 | 입술 색, 농도, 윤기 |
| `brow_color`, `brow_thickness`, `brow_arch` | 머리색 기반, 1.15, 1.0 | 눈썹 |
| `lash_strength`, `lash_width`, `crease` | 0.9, 1.0, 0.45 | 속눈썹 선, 굵기, 쌍꺼풀 선 |
| `eyeshadow_color`, `eyeshadow_strength` | 갈색, 0.30 | 눈두덩 |
| `blush_color`, `blush_strength` | 분홍, 0.20 | 볼 |
| `contour` | 0.5 | 눈두덩과 광대 아래의 음영, 콧대와 광대 위의 밝음. 얼굴 입체감 |
| `skin_gloss` | 0.16 | 피부 윤기. 0.4 이상이면 셀화에서 광택 면이 그려짐 |
| `flesh_variation` | 0.3 | 관절, 귀, 코끝, 손끝의 붉은 기. 고전 유화는 0.6 권장, 셀화는 0.1 |
| `nail_color`, `nail_strength` | 연분홍, 0.6 | 손발톱 |
| `areola_color`, `areola_strength` | 장밋빛, 0.40 | 누드에서의 유륜 색조 |
| `muscle_definition` | 0 | 가슴, 복근, 골반 V선, 견갑골의 요철. 조명에 따라 음영이 생김. 남성 기본 0.5, 근육질 1.0 |
| `body_relief` | 0.6 | 쇄골, 척추, 등 아래 보조개의 은은한 요철. 모든 인물 공통 |
| `stubble`, `beard_color` | 0, 수염색 | 면도 자국 농도와 색. 보통 `beard`가 자동 설정 |

- 남성 프리셋은 자연스러운 입술, 눈화장 없음, 짙은 눈썹, 무광 피부가 기본

## 자주 생기는 문제

| 증상 | 처방 |
| --- | --- |
| 앞머리가 눈을 가림 | `bangs`를 `wispy` 또는 `none`으로, 또는 묶은 머리 |
| 손이 몸에 묻힘 | `reach`의 `offset`을 0.04-0.06으로 (옷 위에 얹은 손은 엔진이 옷감을 눌러 처리) |
| 마주 앉은 두 사람이 서로 반대쪽을 봄 | `facing`에 각도 대신 탁자 이름을 지정 |
| 투샷에서 한 사람이 다른 사람을 가림 | `pairs`의 `facing`을 30-45로, 또는 카메라 `yaw` 조정 |
| 손이 허공에 뜸 | 각도 지정을 `reach`로 교체 |
| 팔이 부자연스럽게 꼬임 | `reach`의 `elbow` 방향 변경 (`down`에서 `out` 등) |
| 몸에 얹은 손이 갈고리처럼 보임 | `reach`에 `"lay": true`, 손 모양 `rest` |
| 옷 사이로 피부가 비침 | 해당 옷의 `ease`를 0.003 키움 |
| 긴 머리가 어깨에서 뻗침 | `length_scale`을 줄이거나 `style`을 `shoulder`로 |
| 얼굴이 올려다보는 듯함 | `head.nod`를 5-10 추가, 카메라 `pitch`를 5로 |
| 전신 구도에서 눈이 검게 뭉침 | 선을 긋는 화풍은 작은 눈에 위 속눈썹 선만 남김. 그래도 어두우면 `look.lash_strength`를 0.5로, 또는 `canvas.detail`을 `fine`으로 |
| 누드가 밋밋함 | 자세 `s_curve`나 `arms_behind_head`, 체형 `woman_curvy`, `look.skin_gloss` 0.3-0.45, 조명 `three_quarter` + `warm` |
| 남성 상체가 밋밋함 | 체형 `man_athletic`, `look.muscle_definition` 0.8-1.0, 조명 `side` 또는 `rembrandt`(요철은 측면광에서 가장 잘 보임) |
| 남성 누드의 하체 처리 | 고전풍은 `perizoma`, 현대풍은 `briefs`나 `trunks`. `nude`는 인체 모델에 생식기 세부가 없어 매끈하게 표현됨 |
