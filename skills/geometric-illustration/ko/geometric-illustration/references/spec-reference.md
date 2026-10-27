# 명세 필드 레퍼런스

명세 JSON은 `scripts/config.py`의 `DEFAULT_SPEC` 위에 덮어쓰기된다. 바꾸고 싶은 필드만 적는다.
단위 "머리 폭"은 머리 폭을 1로 둔 상대 길이이며 원점은 머리 중심, y축은 아래 방향이다.

## 목차
- 캔버스, 주제, 화풍
- 광원
- 팔레트
- 재질별 음영
- 캐릭터: 성별, 체형, 머리 배치, 얼굴, 얼굴 프리셋, 눈, 눈썹, 입, 표정, 머리카락, 의상, 포즈
- 투샷(그룹)
- 인체 습작
- 장면
- 배경과 선

## 캔버스, 주제, 화풍

| 필드 | 기본값 | 범위 | 효과 |
|---|---|---|---|
| `canvas.width` | 1024 | 256 이상 | 출력 폭(px) |
| `canvas.height` | 1280 | 256 이상 | 출력 높이(px). 전신은 1600 이상 권장 |
| `canvas.seed` | 7 | 정수 | 일러스트 그레인, 유화 붓터치, 수채 번짐의 난수 시드 |
| `subject` | `portrait` | `portrait`, `figure_study`, `still_life`, `cityscape`, `landscape` | 그릴 대상 |
| `style` | `anime` | `anime`, `illustration`, `oil`, `watercolor` | 화풍 |
| `framing` | `bust` | `bust`, `upper_body`, `full_body`, `wide` | `portrait` 전용. 머리 크기와 위치를 자동 계산. `wide`는 설정샷(전신 인물 높이가 화면의 34%, 발은 화면 높이 90% 지점) |
| `look` | `none` | `none`, `doomer` | 화풍 렌더 뒤 그림 전체 색보정. `doomer`: 채도 하향, 어두운 톤을 푸르게, 밝은 주황 불빛만 채도 유지, 검정을 회청색으로 띄움, 필름 그레인, 비네트(`looks.DOOMER`) |

## 광원

| 필드 | 기본값 | 효과 |
|---|---|---|
| `light.direction` | [-0.55, -0.65, 0.55] | 광원을 향하는 벡터. x 오른쪽, y 아래, z 관찰자 방향. x 부호가 배경 글로우 위치도 결정. 장면 주제는 시간대(`scene.time`) 또는 정물 세트(`scene.set`)가 정한 광원으로 대체 |
| `light.cast_distance` | 0.032 | 캐스트 섀도 오프셋(머리 폭). 앞머리 그림자, 머리카락 그림자 길이 |
| `light.rim_color` | `#BFD4FF` | 역광 림 라이트 색(일러스트, 유화) |
| `light.rim_strength` | 0.55 | 림 라이트 강도 0-1 |

## 팔레트

모든 색은 `#RRGGBB` 문자열 또는 0-255 RGB 배열이다. 선화 색은 각 밑색에서 자동 파생된다.

| 필드 | 대상 |
|---|---|
| `skin`, `blush`, `lips` | 피부, 볼 홍조, 입술 |
| `hair`, `hair_highlight` | 머리카락 밑색, 광택 색. 눈썹 색은 `hair`에서 파생 |
| `eye`, `sclera`, `lash` | 홍채, 흰자, 속눈썹 |
| `cloth`, `skirt` | 상의(수영복과 속옷은 그 자체), 하의(스커트, 바지, 반바지) |
| `belt`, `shoe`, `sole` | 벨트, 신발 윗면, 운동화 밑창과 끈 |
| `shirt`, `tie`, `accent` | 정장 셔츠, 넥타이, 레이스와 끈 같은 보조색 |
| `metal` | 귀걸이, 버클, 단추 |
| `drape` | 인체 습작 와상의 소파 천 |
| `chair` | `seated` 포즈의 의자(나무 재질 음영) |
| `hat` | `outfit.hat`의 모자(기본 짙은 회색) |
| `background` | [시작색, 끝색] 2색 배열. 끝색은 `flat` 배경색 |
| `background_glow` | `glow` 배경의 광원 쪽 번짐 색 |

## 재질별 음영

키는 재질 그룹명이다: `skin`(얼굴), `body`(마네킹 몸과 손), `hair`, `cloth`, `skirt`, `lips`, `eye_white`, `iris`, `metal`, `shoe`, `leather`, `glass`, `ceramic`, `fruit`, `lemon`, `wood`, `foliage`, `marble`, `device`(전자기기), `paper`, `food`, `liquid`, `default`.
그룹 `bg`, `sky`, `emissive`, `scenery`, `screen`(화면 내용)은 디자인된 색을 그대로 쓰며 음영을 받지 않는다.
`body` 그룹은 셀 그림자 정리(작은 빛 틈 메우기)를 추가로 받는다. 얼굴(`skin`)의 작은 디자인 그림자는 그대로 둔다.

| 필드 | 효과 |
|---|---|
| `cel_threshold.<그룹>` | 법선과 광원의 내적이 이 값보다 작으면 그림자. 높일수록 그림자 면적 증가. 피부는 -0.30으로 얼굴을 밝게 유지 |
| `shadow_tint.<그룹>` | 그림자 곱하기 색. 피부는 붉은 계열, 머리카락과 옷은 남청 계열이 기본 |

## 캐릭터

### 성별 (`character.sex`)

| 값 | 효과 |
|---|---|
| `female` | 기본. 성인 여성 체형, 얼굴, 긴 머리, 의상 `turtleneck_sleeveless` |
| `male` | 성인 남성 체형(넓은 어깨, 좁은 골반, 가슴근육, 굵은 목, 작게 그린 머리), 남성 얼굴 프리셋, 머리 `short`, 의상 `tee_jeans`, 귀걸이 없음 |

- 성별 프리셋은 기본값만 바꾼다. 명세에 적은 얼굴, 눈, 머리카락, 의상 필드가 프리셋보다 우선한다
- 남성 의상은 아래 의상 표에서 `bikini`, `innerwear`, `turtleneck_sleeveless`, `crop_hotpants`를 뺀 10종이다. 정장, 셔츠, 코트의 구두는 끈 달린 구두로 바뀐다

### 체형 (`character.build`)

| 성별 | 값 | 형태 |
|---|---|---|
| 여성 | `standard` | 기본. ANSUR II 마른 하위 표본을 애니메 일러스트로 보정 |
| 여성 | `slender` | 몸통 폭과 두께 약 9% 감소, 팔다리 약 12% 가늘게, 가슴 형태 0.8배 |
| 여성 | `fuller` | 가슴 형태 1.3배, 엉덩이 폭 약 9% 증가, 허리 4% 감소, 허벅지와 둔부 증가. 과장 없는 성인 체형 범위 |
| 여성 | `athletic` | 어깨 7% 증가, 허리 6% 증가, 위팔 14%, 종아리 10% 굵게 |
| 남성 | `standard` | 기본. ANSUR II 남성 요약 통계에서 추정 |
| 남성 | `slim` | 몸통 약 8% 감소, 팔다리 약 13% 가늘게 |
| 남성 | `athletic` | 어깨 9%, 가슴 폭 12%, 가슴근육 1.35배, 위팔 18%, 목 10% 증가, 허리 2% 감소 |

- 세로 기준 높이(목, 허리, 무릎, 발목)는 모든 체형이 같다. 포즈와 의상 재단선이 그대로 맞는다
- 의상은 체형의 몸을 부풀려 입히므로 체형을 따른다. 비키니와 브라 컵은 가슴 형태에 맞춰 커진다
- 배율 표: `scripts/rig_anatomy.py`의 `VARIANTS`. 검사: `python scripts/check_proportions.py --build female_fuller`
- `character.scale`: 투샷에서 다른 인물 대비 크기. null이면 여성 옆 남성 1.06

### 머리 배치 (`character.head`)

| 필드 | 기본값 | 범위 | 효과 |
|---|---|---|---|
| `x` | 0.50 | 0-1 | 머리 중심 가로 위치(캔버스 비율) |
| `y` | null | 0-1 | 머리 중심 세로 위치. null이면 프레이밍에서 계산 |
| `size` | null | 0.05-0.5 | 머리 폭(캔버스 폭 비율). null이면 프레이밍에서 계산 |
| `yaw` | 0.22 | -0.35-0.35 | 좌우 회전(라디안). 양수는 화면 오른쪽을 향함 |
| `roll` | -0.05 | -0.15-0.15 | 기울기(라디안) |

### 얼굴 프리셋 (`character.face_preset`)

| 값 | 효과 |
|---|---|
| `default` | 얼굴 필드 그대로 |
| `soft` | 둥근 턱선, 처진 눈꼬리, 완만한 눈썹 |
| `sharp` | 각진 턱, 올라간 눈꼬리, 가는 눈 |
| `mature` | 긴 얼굴, 작은 눈, 굵은 눈썹, 홍조 감소 |
| `gentle` | 처진 눈꼬리, 완만하고 가는 눈썹, 부드러운 턱선, 약한 미소 |
| `cool` | 가늘고 올라간 눈, 낮고 곧은 굵은 눈썹, 좁은 입, 홍조 감소 |
| `bold` | 굵은 속눈썹과 눈썹, 진한 입술, 넓은 입 |

프리셋 결과는 성인 얼굴 범위(`eyes.size` 0.85-1.10, `eyes.openness` 0.70-0.95, `face.chin_length` 0.68-0.76, `face.jaw_width` 0.36-0.42, `blush` 0-0.35) 안으로 보정된다.

### 얼굴 (`character.face`)

| 필드 | 기본값 | 효과 |
|---|---|---|
| `cheek` | 0.485 | 광대 높이의 얼굴 반폭 |
| `jaw_width` | 0.385 | 턱각의 반폭. 작을수록 V라인 |
| `jaw_height` | 0.44 | 턱각의 높이 |
| `chin_length` | 0.70 | 턱끝 높이. 클수록 긴 얼굴 |
| `chin_width` | 0.04 | 턱끝 반폭. 0에 가까울수록 뾰족 |
| `jaw_sharpness` | 0.85 | 0-1. 턱각에서 턱끝까지 윤곽의 직선도 |

### 눈 (`character.eyes`)

| 필드 | 기본값 | 효과 |
|---|---|---|
| `size` | 1.1 | 눈 크기 배율 0.8-1.4 |
| `openness` | 0.92 | 세로 개방도 0.6-1.1 |
| `tilt` | 0.10 | 눈꼬리 상승 각도(라디안). 양수는 고양이 눈 |
| `spacing` | 0.205 | 눈 중심의 좌우 간격(머리 폭) |
| `height` | 0.13 | 눈 중심선 높이(머리 중심 기준 아래쪽) |
| `gaze` | [-0.15, 0.0] | 시선 x, y. -1-1 |
| `lash_weight` | 1.0 | 속눈썹 굵기 배율 |

### 눈썹 (`character.brows`)

| 필드 | 기본값 | 효과 |
|---|---|---|
| `angle` | 0.4 | 눈썹 산의 상승. 클수록 날카로운 인상 |
| `thickness` | 0.9 | 굵기 배율 |
| `height` | 0.0 | 위아래 오프셋(머리 폭) |
| `see_through` | 0.35 | 앞머리 위로 비쳐 보이는 눈썹의 불투명도 0-1 |

### 입과 홍조

| 필드 | 기본값 | 효과 |
|---|---|---|
| `mouth.smile` | 0.25 | 입꼬리 상승 0-1 |
| `mouth.width` | 1.15 | 입 폭 배율 |
| `mouth.lip_strength` | 0.65 | 입술 색 불투명도 0-1 |
| `blush` | 0.30 | 볼 홍조 불투명도 0-1. 0이면 생략 |
| `mouth.open` | 0 | 벌린 입 0-1. 미소가 0.3 이상이면 웃는 입(윗니, 혀), 미만이면 동그란 입 |
| `eyes.shape` | `open` | `closed`이면 웃으며 감은 눈(위로 굽은 속눈썹 선) |

### 표정 (`character.expression`)

| 값 | 효과 |
|---|---|
| `default` | 얼굴 필드 그대로 |
| `smile` | 입꼬리 상승, 눈 약간 가늘게 |
| `laugh` | 감은 눈, 벌린 입과 윗니, 홍조 증가 |
| `neutral` | 평평한 입, 완만한 눈썹 |
| `surprised` | 동그랗게 벌린 입, 커진 눈, 올라간 눈썹 |
| `serious` | 내려간 입꼬리, 가는 눈, 각진 눈썹 |
| `sad` | 처진 입꼬리, 안쪽이 올라간 눈썹, 아래를 보는 시선 |

표정은 얼굴 프리셋 다음에 적용되며 성별 프리셋의 눈, 눈썹 값을 바탕으로 바꾼다(`config.EXPRESSIONS`).

### 머리카락 (`character.hair`)

| 필드 | 기본값 | 효과 |
|---|---|---|
| `style` | `long` | `long` 긴 생머리, `updo` 올림머리, `short` 짧은 머리(남성 기본), 아래 이름 붙은 머리 모양 |
| `length` | 2.3 | 뒷머리 끝 높이(머리 폭). 1.4 어깨, 2.3 가슴, 3.5 이상 허리. 줄일 때 `side_length`도 함께 축소 |
| `volume` | 0.06 | 두피 위 볼륨 0-0.15 |
| `bangs` | `swept` | `swept` 한쪽 넘김, `parted` 가르마 커튼, `blunt` 일자, `slicked` 뒤로 넘김(이마 노출) |
| `bang_count` | 8 | 앞머리 다발 수 3 이상 |
| `bang_length` | 0.10 | 앞머리 끝 높이. 눈 중심선은 0.13 |
| `part` | -0.14 | 가르마 위치 -0.3-0.3 |
| `tuck` | `near` | 귀 뒤로 넘긴 쪽: `near` 가까운 쪽, `far` 먼 쪽, `none` 양쪽 내림 |
| `side_length` | 1.75 | 옆머리 끝 높이 |
| `seed` | 3 | 다발 폭, 끝 위치 변주의 난수 시드 |

이름 붙은 머리 모양(`rig_hair.HAIR_PRESETS`)은 세 기본 머리 위에 필드를 덮어쓴다. 색과 시드는 명세 값을 쓴다.

| `style` | 기반 | 모양 |
|---|---|---|
| `side_part` | `short` | 깊은 옆가르마, 짧게 넘긴 앞머리 |
| `slicked` | `short` | 이마를 드러내고 뒤로 넘긴 머리 |
| `two_block` | `short` | 옆은 짧게, 윗머리는 길게 내린 가르마 앞머리 |
| `medium` | `long` | 턱선과 목덜미까지 오는 중간 길이 |
| `bob` | `long` | 턱선 단발, 일자 앞머리 |
| `ponytail` | `updo` | 뒤에서 묶어 내린 꼬리 |
| `hime` | `long` | 일자 앞머리, 턱선 길이 옆머리, 긴 뒷머리 |
| `center_part` | `long` | 가운데 가르마 커튼 앞머리, 긴 생머리 |
| `shoulder` | `long` | 어깨 길이, 가르마 앞머리, 한쪽 귀 뒤로 넘김(남녀 공용) |
| `crop` | `short` | 눈썹 위 일자 앞머리의 짧은 머리 |

### 의상 (`character.outfit`)

| 필드 | 기본값 | 효과 |
|---|---|---|
| `type` | `turtleneck_sleeveless` | 의상 종류(아래 표) |
| `shoulder_width` | 0.93 | 어깨 반폭. 바스트업의 터틀넥 전용 |
| `skirt_length` | 6.2 | 스커트 밑단 높이(머리 폭, 서 있는 자세 기준). `turtleneck_sleeveless`의 상반신, 전신 전용 |
| `skirt_flare` | 1.15 | 밑단 반폭 목표. 엉덩이에서 이 폭까지 일정 기울기로 퍼진다. 다리가 더 나와 있으면 그만큼 넓어진다 |
| `earrings` | `drop` | `drop` 드롭, `stud` 스터드, `none` 없음 |
| `hat` | `none` | `none`, `beanie`(접힌 단 니트 비니). 머리카락 위에 그려 단 아래 앞머리와 옆머리만 보인다. 뒷모습에서도 그려진다 |
| `shoes` | null | null이면 의상 기본 신발. `pumps`, `sneakers`, `oxfords`, `none`으로 바꾼다 |

| `type` | 구성 | 신발 | 기본 색(`cloth` / `skirt`) |
|---|---|---|---|
| `turtleneck_sleeveless` | 슬리브리스 터틀넥, 미디 스커트, 벨트 | 펌프스 | 차콜 / 카멜 |
| `bikini` | 삼각 비키니, 끈 묶음 하의 | 맨발 | 네이비 |
| `innerwear` | 레이스 테두리 브라, 브리프 | 맨발 | 검정, 레이스 `accent` |
| `crop_hotpants` | 크롭 탱크톱, 데님 핫팬츠 | 운동화 | 흰색 / 연청 |
| `tee_jeans` | 반팔 티셔츠, 청바지 | 운동화 | 흰색 / 진청 |
| `suit` | 재킷, 셔츠, 넥타이, 슬랙스, 벨트 | 펌프스 | 차콜, `shirt`, `tie` |
| `hoodie_joggers` | 후드티(모자, 주머니, 끈), 조거 팬츠 | 운동화 | 회색 / 검정 |
| `swim_trunks` | 수영 반바지(허리끈, 옆줄). 남성 전용 | 맨발 | `skirt` 청록 |
| `shirt_slacks` | 드레스 셔츠(옷깃, 단추, 소맷부리), 슬랙스, 벨트 | 펌프스 / 남성 구두 | `shirt` 연청 / 차콜 |
| `knit_coat` | 크루넥 니트, 벨트 무릎길이 코트(라펠), 바지 | 펌프스 / 남성 구두 | `shirt` 아이보리, `cloth` 카멜 / 차콜 |
| `polo_shorts` | 폴로셔츠(옷깃, 단추 2개), 무릎 위 치노 반바지 | 운동화 | 네이비 / 베이지 |
| `tank_shorts` | 스포츠 싱글렛, 러닝 반바지(옆줄 `accent`) | 운동화 | 흰색 / 검정 |
| `denim_jacket` | 열린 청재킷(가슴 주머니, 단추), 티셔츠, 청바지 | 운동화 | `cloth` 청색, `shirt` 흰색 / 진청 |
| `track_suit` | 지퍼 트랙 재킷(스탠드 칼라), 트랙 팬츠, 소매와 다리 옆줄 | 운동화 | 남색, 줄 `accent` |

- 의상마다 기본 색이 있다. 명세의 `palette`에 적은 색이 기본 색보다 우선한다
- 바스트업에서 `turtleneck_sleeveless`는 바스트업 전용 의상을, 다른 의상은 마네킹 몸에 입힌 3D 의상을 쓴다
- 현재 몸 모델에는 가슴 표시와 골반 세부 형태가 구현되어 있지 않다

### 포즈 (`character.pose`)

| 필드 | 기본값 | 효과 |
|---|---|---|
| `preset` | `relaxed` | 아래 포즈 표. 상반신, 전신 전용 |
| `turn` | 0.0 | 몸 회전: `front`, `three_quarter`(0.6), `side`(pi/2), `three_quarter_back`(2.3), `back`(pi), 앞에 `-`면 반대쪽, 숫자는 라디안. 양수는 가슴이 화면 오른쪽을 향함 |
| `look` | `auto` | `auto` 얼굴이 몸을 따라 돎(1.9 라디안 이상이면 뒤통수), `face` 얼굴을 `head.yaw`로 그림(어깨 너머 시선), `away` 뒤통수 |
| `custom` | null | 관절 직접 지정(아래) |

| 포즈 | 동작 | 기본 시점 |
|---|---|---|
| `relaxed` | 양팔 내림, 체중 이동 | 정면 |
| `hand_on_hip` | 한 손 허리 | 정면 |
| `hair_touch` | 한 손으로 머리 넘기기 | 정면 |
| `chin_rest` | 팔짱 위로 턱 괴기 | 정면 |
| `arms_crossed` | 팔짱 | 정면 |
| `hands_in_pockets` | 양손 앞주머니(후드티는 앞 주머니). 비키니와 속옷은 팔을 내림 | 정면 |
| `walking` | 앞발을 딛고 뒤꿈치를 든 보행, 팔 교차 흔들기 | `turn` 0.9 |
| `look_back` | 등을 보이고 어깨 너머로 돌아봄, 한 손 허리 | `turn` 2.55, `look` `face` |
| `lean_wall` | 화면 왼쪽 기둥에 어깨를 기대고 발목 교차 | 정면 |
| `seated` | 의자에 앉아 손을 허벅지에 올림. 전신 프레이밍이 앉은 높이에 맞춰짐 | `turn` 0.6 |

- 기본 시점은 명세가 `turn` 0, `look` `auto`일 때만 쓰인다. `turn`을 적으면 그 값이 우선한다
- 앉은 자세에서 스커트는 허벅지 위에 놓이는 천(무릎에서 끝남)으로, 코트 자락도 같은 방식으로 바뀐다

관절 직접 지정(`custom`): 정면을 향한 몸 좌표(머리 폭, 원점 머리 중심, y 아래, z 관찰자 방향)로 적고 회전(`turn`)은 그 뒤에 적용된다.

| 키 | 값 |
|---|---|
| `arm_left`, `arm_right`, `leg_left`, `leg_right` | `{target: [x, y, z], pole: [x, y, z], hand: 제스처 또는 발 모드, hand_u, hand_n, foot_dir}`(인물 기준 왼쪽, 오른쪽) |
| `chest`, `pelvis` | `[yaw, pitch, roll]` 라디안 |
| `shift` | 골반 가로 이동(체중 이동) |

기준값: 어깨 관절 (±0.74, 1.17), 팔꿈치 높이 2.75, 손목 높이 4.05, 고관절 (±0.32, 3.74), 무릎 5.96, 발목 8.10. 손 제스처: `relaxed`, `hip`, `hair`, `chin`, `cover`, `clasp`, `prop`, `pocket`(옷 아래로 숨김). 발 모드: `flat`, `point`(까치발, 펌프스).

## 투샷 (`characters`, `layout`)

`subject` `portrait`에서 `characters`에 2-3명을 적으면 단체 그림이 된다. 각 항목은 `character`와 같은 필드를 받고 `palette`를 추가로 받는다(성별 프리셋, 의상 기본 색, 인물 색 순으로 덮어씀).

| 필드 | 기본값 | 값 | 효과 |
|---|---|---|---|
| `layout.type` | `side_by_side` | `side_by_side`, `facing`, `front_back` | 나란히(2-3명), 마주 보기(서로를 향해 0.75 라디안 회전), 앞뒤(뒤 인물은 조금 작고 높게) |
| `layout.interaction` | `none` | `none`, `hold_hands` | 이웃한 두 인물의 안쪽 손을 사이에서 맞잡음 |
| `layout.gap` | null | 머리 폭 | 이웃 사이 간격. null이면 배치별 기본값 |

- 프레이밍은 `framing`을 따르며 가장 큰 인물이 화면에 맞는다. 폭이 모자라면 전체가 줄어든다
- 앉은 인물과 선 인물이 섞이면 같은 바닥에 선다
- 앞뒤 순서는 목록 순서다(첫 인물이 맨 앞)
- 인체 습작(`figure_study`)은 투샷을 지원하지 않는다

## 인체 습작 (`figure_study`)

`subject`가 `figure_study`일 때만 쓰인다. 인물은 성인 비례로 고정되고 화면에 맞춰 자동 배치된다.

| 필드 | 기본값 | 값 | 효과 |
|---|---|---|---|
| `figure_study.pose` | `venus` | `back_three_quarter`, `venus`, `reclining`, `seated` | 포즈. 아래 표 참조 |
| `figure_study.hair` | null | null, `long`, `updo`, `short` | 머리 모양. null이면 포즈 기본값(남성은 `short`) |

| 포즈 | 구도 | 가림 방식 |
|---|---|---|
| `back_three_quarter` | 등을 보인 3/4 입상, 어깨 너머로 돌아봄, 한 손은 올림머리 | 등 방향 시점 |
| `venus` | 정면 콘트라포스토 입상 | 팔, 손, 머리카락 |
| `reclining` | 소파에 비스듬히 누운 뒷모습(오달리스크) | 등 방향 시점, 천 |
| `seated` | 바닥에 앉아 무릎을 끌어안은 측면 | 허벅지와 팔 |

`character.sex`가 `male`이면 같은 4포즈를 남성 체형으로 그린다. 가슴을 가리던 머리카락 다발은 없다. `venus`에서 가슴을 가리던 팔은 옆으로 내리고 골반을 가리는 손은 그대로 둔다. 골반 세부 형태가 없는 몸과 골반 주변 무선 구역 원칙은 남녀가 같다.

`character`의 얼굴, 눈, 머리 색 필드는 그대로 적용되며 다음 범위로 보정된다: `eyes.size` 0.85-1.10, `eyes.openness` 0.70-0.95, `face.chin_length` 0.68-0.76, `face.jaw_width` 0.36-0.42, `blush` 0-0.35.

## 장면 (`scene`)

`still_life`, `cityscape`, `landscape` 주제는 장면이 정한 구도와 광원을 그린다. 배치의 세부 변주는 `character.hair.seed`(장면 난수 시드)로 바뀐다.

| 필드 | 기본값 | 값 | 효과 |
|---|---|---|---|
| `scene.time` | `dusk` | `dusk`, `day`, `golden`, `blue_night`, `rain_night`, `snow_night` | 풍경화, 도시화의 시간대. 아래 표 참조 |
| `scene.site` | null | 도시 `street`, `panel` / 풍경 `lake`, `outskirts` | 장소. null이면 첫 값(`street`, `lake`). 아래 표 참조 |
| `scene.set` | `classic` | `classic`, `desk`, `cafe`, `gaming`, `kitchen` | 정물화 세트. 아래 표 참조 |
| `scene.palette` | {} | 색 사전 | 장면 색 덮어쓰기. 키는 아래 표. 선택한 시간대 또는 세트의 색 위에 덮어씀 |

### 시간대 (`scene.time`)

| 값 | 의미 | 켜지는 요소 |
|---|---|---|
| `dusk` | 황혼(기본) | 지평선의 해, 해 길, 구름과 능선 림 라이트, 일부 창문과 가로등 |
| `day` | 맑은 낮 | 높은 해, 흰 구름, 호수 반짝임. 도시는 해 쪽 건물 그림자 띠와 외벽 명암 대비, 하늘을 비추는 유리창 |
| `golden` | 골든아워 | 지평선 위의 낮은 해, 금빛 해 길과 림 라이트, 소수의 창문 불빛 |
| `blue_night` | 블루아워 야경 | 달, 별, 달빛 길, 호숫가 마을 불빛, 대부분의 창문, 가로등, 간판 |
| `rain_night` | 비 오는 밤 | 비 줄기, 짙은 구름, 안개 낀 능선, 호수의 빗방울 고리, 젖은 도로에 비친 불빛 기둥 |
| `snow_night` | 눈 내리는 밤 | 흐린 하늘, 내리는 눈(먼 눈과 가까운 큰 눈송이), 나트륨 가로등, 눈 덮인 길의 바퀴 자국, 일부 창문 불빛, 맨가지 나무와 자작나무 |

### 장소 (`scene.site`)

| 장면 | 값 | 구성 |
|---|---|---|
| `cityscape` | `street` | 상가와 간판이 늘어선 대로, 차선, 차량(기본) |
| `cityscape` | `panel` | 앞마당 너머 5-12층 패널 아파트(이음매, 발코니, 계단실 창), 뒤 열의 단지, 맨가지 가로수, 전선과 가로등 |
| `landscape` | `lake` | 산 능선, 호수, 호숫가 침엽수(기본). 눈 오는 밤에는 앞쪽 나무가 자작나무 |
| `landscape` | `outskirts` | 교외 들판, 눈 위 오솔길, 지평선의 단지와 굴뚝, 굴뚝 꼭대기 항공 경고등, 멀어지는 송전탑 행렬, 앞쪽 자작나무 |

모든 장소는 모든 시간대에서 그려진다. `outskirts`의 색은 `snow_night` 외 시간대에서 그 시간대의 호수 팔레트에서 파생된다.

### 정물 세트 (`scene.set`)

| 값 | 구성 | 광원 |
|---|---|---|
| `classic` | 병, 주전자, 사과, 레몬, 포도, 천(기본) | 왼쪽 위 창가 빛 |
| `desk` | 노트북(코드 화면), 머그와 김, 스마트폰, 데스크 램프, 화분, 노트와 펜 | 오른쪽 데스크 램프 |
| `cafe` | 라테와 받침, 조각 케이크와 딸기, 포크, 아이스 라테 잔, 스마트폰, 이어폰 케이스, 큰 창과 보케 | 왼쪽 뒤 오후 창가 빛 |
| `gaming` | 모니터(게임 화면), RGB 키보드, 마우스, RGB 장패드, 헤드셋 거치대, 음료 캔, 벽면 RGB 조명 | 앞쪽 위의 부드러운 빛과 화면, RGB 발광 |
| `kitchen` | 체크 무늬 비닐 식탁보, 금속 받침에 끼운 찻잔과 숟가락, 카세트 라디오(테이프 창, 스피커, 주황 주파수 창, 안테나), 카세트테이프, 흰 창틀 너머 눈 내리는 밤의 단지 | 화면 밖 오른쪽 위 백열등 1개 |

### 팔레트 키

| 장면 | 주요 팔레트 키 |
|---|---|
| 공통 하늘 | `zenith`, `upper`, `middle`, `lower`, `horizon`, `sun`, `sun_glow`, `cloud_top`, `cloud_lit`, `cloud_rim`, `haze`, `moon`, `star`, `rain`, `snow` |
| `landscape` | `ridge_far`, `ridge_mid`, `ridge_rim`, `hill`, `shore`, `water_top`, `water_deep`, `pine`, `tree`, `grass`, `glitter`, `ripple`, `village` |
| `landscape` `outskirts` | `field_far`, `field_near`, `drift`, `path`, `pylon`, `birch`, `birch_mark`, `town`, `town_lit`, `chimney`, `beacon` |
| `cityscape` | `wall_a`, `wall_b`, `wall_c`, `wall_front`, `roof_rim`, `window_lit`, `window_dark`, `sign_a`, `sign_b`, `sign_c`, `road`, `road_far`, `walk`, `line`, `pole`, `lamp`, `lamp_pool`, `skyline` |
| `cityscape` `panel` | 위 키에 더해 `window_cool`(푸른 창), `seam`(패널 이음매), `yard`(앞마당), `tree`(가로수), `rut`(눈길 바퀴 자국) |
| `still_life` `classic` | `wall_top`, `wall_low`, `window_light`, `table`, `table_edge`, `grain`, `drape`, `drape_light`, `bottle`, `jug`, `jug_band`, `apple`, `apple_blush`, `lemon`, `grape`, `stem`, `gloss` |
| `still_life` `desk` | `wall_top`, `wall_low`, `table`, `table_edge`, `grain`, `lamp_light`, `laptop`, `laptop_key`, `editor`, `mug`, `coffee`, `phone`, `wallpaper_a`, `wallpaper_b`, `lamp`, `pot`, `soil`, `leaf`, `leaf_edge`, `cover`, `pages`, `pen`, `gloss`, `steam` |
| `still_life` `cafe` | `wall_top`, `wall_low`, `window`, `frame`, `table`, `table_edge`, `vein`, `cup`, `latte`, `foam`, `plate`, `sponge`, `frosting`, `cream`, `berry`, `fork`, `glass`, `coffee_milk`, `milk`, `ice`, `straw`, `phone`, `wallpaper_a`, `wallpaper_b`, `case`, `gloss`, `bokeh` |
| `still_life` `gaming` | `wall_top`, `wall_low`, `table`, `table_edge`, `grain`, `monitor`, `game_sky_a`, `game_sky_b`, `game_hill`, `game_near`, `hud`, `hp`, `keyboard`, `pad`, `mouse`, `headset`, `can`, `can_label`, `can_top`, `gloss`, `screen_spill` |
| `still_life` `kitchen` | `wall_top`, `wall_low`, `table`, `table_edge`, `check`, `window_night`, `window_haze`, `block`, `block_far`, `block_lit`, `block_cool`, `lamp_pool`, `frame`, `sill`, `glass`, `tea`, `holder`, `spoon`, `player`, `player_face`, `grille`, `dial`, `cassette`, `label`, `reel`, `gloss`, `steam`, `snow`, `lamp_light` |

`classic` 세트에서 `drape`만 바꾸면 `drape_light`는 같은 색조로 자동 파생된다. RGB 조명의 색상 순환은 `scene_modern.RGB_PHASE`에서 시작한다.

## 배경과 선

| 필드 | 기본값 | 효과 |
|---|---|---|
| `background.type` | `glow` | `flat`, `gradient`, `glow`, `scene` |
| `background.scene` | `cityscape` | `type`이 `scene`일 때 인물 뒤에 그릴 장면: `cityscape`, `landscape`. 시간대는 `scene.time` |
| `line.weight` | 1.0 | 전체 선 굵기 배율 |

`scene` 배경에서 인물은 장면의 광원 방향을 받고, 피부와 옷 색에 시간대 색조가(`character.SCENE_TINTS`), 림 라이트에 시간대 색이(`SCENE_RIMS`) 적용된다.

## 예시

### 인물

```json
{
  "style": "illustration",
  "framing": "upper_body",
  "character": {
    "head": {"yaw": -0.2},
    "eyes": {"gaze": [0.15, 0.0]},
    "hair": {"bangs": "parted", "part": 0.0, "tuck": "none"},
    "pose": {"preset": "hand_on_hip"}
  },
  "palette": {"hair": "#6B4A3A", "hair_highlight": "#C9A48A", "eye": "#4F7FB8"},
  "light": {"direction": [0.55, -0.65, 0.55]}
}
```

얼굴이 왼쪽(`yaw` 음수)을 향하면 광원 x를 양수로 바꿔 얼굴 넓은 면을 밝힌다.

### 몸 회전, 포즈, 체형

```json
{"style": "anime", "framing": "full_body", "canvas": {"width": 1024, "height": 1600},
 "character": {"sex": "male", "build": "athletic", "outfit": {"type": "denim_jacket"},
               "hair": {"style": "two_block"}, "pose": {"preset": "walking", "turn": "side"},
               "expression": "smile"}}
```

### 투샷과 배경 합성

```json
{"style": "illustration", "framing": "full_body", "canvas": {"width": 1280, "height": 1600},
 "background": {"type": "scene", "scene": "cityscape"}, "scene": {"time": "dusk"},
 "characters": [
   {"sex": "female", "build": "fuller", "outfit": {"type": "knit_coat"}, "hair": {"style": "bob"}, "expression": "laugh"},
   {"sex": "male", "outfit": {"type": "shirt_slacks"}, "hair": {"style": "slicked"}, "palette": {"shirt": "#E8E4DA"}}],
 "layout": {"type": "side_by_side", "interaction": "hold_hands"}}
```

### 인체 습작과 장면

```json
{"subject": "figure_study", "style": "oil", "canvas": {"width": 1600, "height": 1024},
 "figure_study": {"pose": "reclining"}, "palette": {"drape": "#3E4A6E"}}
```

```json
{"subject": "cityscape", "style": "illustration", "canvas": {"width": 1600, "height": 1000},
 "scene": {"time": "blue_night", "palette": {"window_lit": "#FFE2A0", "sign_a": "#FF9A5C"}}}
```

```json
{"subject": "still_life", "style": "watercolor", "canvas": {"width": 1400, "height": 1050},
 "scene": {"set": "cafe", "palette": {"berry": "#C8325A"}}}
```

### 두머 설정샷

```json
{"style": "anime", "look": "doomer", "framing": "wide", "canvas": {"width": 1600, "height": 1000},
 "background": {"type": "scene", "scene": "cityscape"}, "scene": {"time": "snow_night", "site": "panel"},
 "character": {"head": {"x": 0.34}, "hair": {"style": "medium"}, "pose": {"preset": "walking"},
               "outfit": {"type": "knit_coat", "hat": "beanie", "shoes": "oxfords", "earrings": "none"}},
 "palette": {"cloth": "#423E3C", "skirt": "#202227", "hat": "#6A7078"}}
```
