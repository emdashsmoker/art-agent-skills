# 피사체별 설정

`--subject`로 고르는 피사체마다 기본 설정 파일 `assets/subject_<이름>.json`이 있다. 사용자 설정에는 바꿀 항목만 적는다. 파일 안의 `spec`은 구성, `style`은 모든 화풍 공통 팔레트, `style_<화풍>`은 해당 화풍 전용 덮어쓰기

## 목차

- figure (전신 인물)
- 장면 합성 (backdrop, companions, 접촉, 소품)
- hand (손)
- still_life (정물)
- desk (책상)
- landscape (풍경)
- beach (해변)
- city (도시)
- park, sakura (공원과 벚꽃길)
- rooftop, fireworks (노을 옥상과 불꽃놀이 강변)
- panelka, outskirts (판넬 아파트 단지와 외곽 들판)
- cafe, room, bedroom, bathroom (실내)
- weather (날씨)

## figure (전신 인물)

머리는 초상과 같은 구조를 작은 크기로 사용한다. 얼굴, 머리카락, 팔레트 항목은 `spec.md`와 동일

### 성별

| 키 | 기본 | 설명 |
|---|---|---|
| `sex` | "female" | "male"이면 남성 체형 표(`anatomy_body.MALE`, `anatomy_profile.MALE`)와 남성 프리셋 사용 |

- 남성 체형: 넓은 어깨와 가슴, 좁은 허리와 골반, 굵은 목과 팔다리, 가슴근, 복근, 골반 위 V선, 뒷모습의 승모근과 광배근
- 남성 측면: 눈썹뼈, 곧은 코, 앞으로 나온 턱끝, 울대뼈, 깊은 가슴, 평평한 배, 작은 엉덩이, 짧은 머리
- `figure.shape` 배율은 남녀 모두 적용

### 구도

| 키 | 기본 | 설명 |
|---|---|---|
| `pose.head_center` | [0.50, 0.105] | 눈 중간점의 화면 위치. 세로값을 키우면 인물이 내려감 |
| `pose.head_unit` | 0.060 | 머리 단위 크기(화면 폭 대비). 0.060은 전신, 0.085는 무릎 위 구도 |
| `figure.body_scale` | 1.0 | 머리 대비 몸 크기. 0.9는 6.8등신, 1.0은 7.4등신, 1.05는 7.7등신 |
| `figure.neck_shift` | 0.05 | 목이 머리 중심에서 옆으로 비켜난 정도 |
| `figure.floor` | {"y": 0.84} | 바닥선 높이(화면 높이 대비). null은 바닥 생략. 측면은 {"at_feet": true}로 발바닥에 맞춤 |
| `figure.view` | "front" | "front"(정면), "back"(뒷모습), "side"(측면, 화면 오른쪽을 봄. `pose.mirror`로 반전) |

### 체형

| 키 | 기본 | 범위 | 설명 |
|---|---|---|---|
| `figure.shape.shoulders` | 1.0 | 0.9-1.1 | 어깨와 윗가슴 폭 배율 |
| `figure.shape.bust` | 1.0 | 0.8-1.2 | 가슴 크기 배율 |
| `figure.shape.waist` | 1.0 | 0.9-1.15 | 허리 폭 배율 |
| `figure.shape.hips` | 1.0 | 0.9-1.12 | 골반과 엉덩이 폭 배율(뒷모습, 측면에서는 엉덩이 크기도 함께) |
| `figure.shape.thighs` | 1.0 | 0.9-1.12 | 허벅지 굵기 배율 |
| `figure.shape.legs` | 1.0 | 0.95-1.1 | 다리 길이 배율 |

### 자세

`figure.pose`. 각도는 곧게 내린 상태에서 바깥쪽으로 벌어지는 정도(도). 좌우는 화면 기준

| 키 | 기본 | 설명 |
|---|---|---|
| `shoulder_tilt`, `pelvis_tilt` | 3, -6 | 어깨선과 골반선의 기울기. 부호를 반대로 주면 콘트라포스토 |
| `arm_left`, `arm_right` | | `upper`(위팔), `fore`(아래팔), `hand`(손) 각도와 선택 항목 `foreshorten` [위팔, 아래팔], `toward` [위팔, 아래팔], `over`(다른 팔 위에 놓임), `behind_clothes`(몸 뒤로 간 손이 치마와 코트 뒤로 숨음) |
| `leg_left`, `leg_right` | | `thigh`(허벅지), `shin`(정강이), `foot`(발) 각도와 선택 항목 `foreshorten`, `toward` |
| `hand_left`, `hand_right` | "relaxed" | 손 자세 이름: `open`, `relaxed`, `victory`, `peace`(넓게 벌린 V, 인물 크기용), `point`, `grip`(쥐기), `fist`(주먹), `tucked`(숨김) |
| `hand_left_view`, `hand_right_view` | "back" | "palm"이면 손바닥이 보이는 손(엄지가 반대쪽). 손 흔들기, V 사인 |
| `turn` | 0 | 몸 돌리기(도). 3/4 시점 전신(아래 절) |
| `stride` | 없음 | 관객 쪽으로 걸어오는 자세. {"lead": "left" 또는 "right", "amount": 0-1, "arms": true}(아래 절) |
| `figure.holds` | | 손에 든 물건. {"right": {"kind": "cup"}, "left": {"kind": "book"}}. 선택 항목 `size`, `offset` [x, y](머리 단위), `group`(팔레트) |

- 손을 허리에 얹기: `upper` 28, `fore` -45, `hand` -32, `foreshorten` [1.0, 0.75]
    + 아래팔이 화면 안쪽으로 기울어 짧아 보이는 만큼 `foreshorten`으로 줄임
- 체중을 실은 다리는 `thigh` 0 전후, 쉬는 다리는 `thigh` 5-8과 `shin` -8 전후
- `toward`는 짧아진 뼈가 향하는 쪽을 표시(1 관객 쪽, 0 평면, -1 몸 뒤쪽)
    + 관객 쪽 뼈는 앞으로 솟아 뒤의 몸을 가리고, 윗면이 광원을 향하며, 가까운 끝이 커 보임
    + 몸 뒤쪽 뼈는 몸통과 머리에 가려 보이는 부분만 그려짐
    + `toward`가 없으면 `foreshorten`은 길이만 줄임
- 자세 예시

| 자세 | 값 | 예제 |
|---|---|---|
| 팔짱 | 두 팔 `upper` 12-14, `fore` -92 - -96, `foreshorten` [0.72, 0.9], `toward` [1, 0]. 위 팔 `"over": true`, 아래 손 `"tucked"` | `example_spec_figure_male_arms_crossed.json` |
| 머리 뒤의 손 | 두 팔 `upper` 150, `fore` -78, `foreshorten` [1.0, 0.55], `toward` [0, -1] | `example_spec_figure_hands_behind_head.json` |
| 등 뒤의 손 | 두 팔 `upper` 8, `fore` -38, `foreshorten` [1.0, 0.55], `toward` [0, -1] | `example_spec_figure_male_hands_behind_back.json` |
| 컵 들기 | `upper` 10, `fore` -128, `foreshorten` [1.0, 0.55], `toward` [0, 1], 손 `"grip"`, `holds` cup | `example_spec_figure_holding.json` |
| 책 들기 | 늘어뜨린 팔, 손 `"grip"`, `holds` book | `example_spec_figure_holding.json` |

- 든 물건은 손 뒤에 놓임: 컵은 손가락이 몸통 앞을 감싸고 손잡이는 손목 반대쪽, 책은 손가락이 위 모서리를 쥐고 표지 위에 놓임

- 위팔이 90도를 넘으면 어깨 관절이 위와 안쪽으로 올라감(팔을 든 어깨)
- 관객 쪽으로 오는 아래팔은 자기 위팔 위에 윤곽선이 그려짐

### 손 목표점과 얼굴 앞 팔

팔에 `reach`를 주면 손바닥 가운데가 그 지점에 닿도록 위팔과 아래팔 각도를 코드가 역산(2관절 역기구학). `upper`, `fore`를 맞추는 반복 렌더링이 필요 없음

| 팔 키 | 설명 |
|---|---|
| `reach` | {"mark": 이름} 자기 몸의 지점, {"at": [x, y]} 화면 비율 위치(좌우 반전 후 그림 기준), {"mark": 이름, "of": "main" 또는 동반 인물 번호} 다른 인물의 지점(장면에서만). 선택 항목 `offset` [dx, dy](머리 단위, 인물 자신의 방향) |
| `bend` | 팔꿈치 방향. "out"(기본, 몸 바깥), "in", "down", "up", "straight"(곧게 편 팔을 관객 쪽으로 짧게 줄여 닿게 함) |
| `hand` | 주면 손 방향을 이 각도로 고정(어깨에 걸친 손처럼 손가락이 아래로). 없으면 아래팔 방향에 `wrist`(도)를 더함 |
| `foreshorten`, `toward` | 그대로 적용. 역산은 줄어든 뼈 길이로 계산 |
| `front` | true면 머리를 그린 뒤 아래팔과 손(소매 포함)을 다시 올림. 손이 얼굴과 머리카락 앞에 오고 얼굴에 손 그림자가 짐 |

- `reach`를 준 팔은 프리셋 팔의 각도와 단축을 물려받지 않음(오른팔 기본값은 허리에 얹은 손)
- 지점 이름
    + 머리: `chin`, `mouth`, `cheek_left`, `cheek_right`, `temple_left`, `temple_right`, `crown`(정수리 위)
    + 몸: `shoulder_*`, `elbow_*`, `wrist_*`, `hand_*`, `hip_*`, `knee_*`, `ankle_*`(*는 left, right), `pit`, `bust`, `waist`, `navel`, `hips`
    + 다른 팔의 `elbow_*`, `wrist_*`, `hand_*`를 겨누면 그 팔을 먼저 놓고 계산(턱 괴는 팔의 팔꿈치를 받치는 손)
- 손이 얼굴 가까이 가는 자세는 위팔을 관객 쪽으로 줄여야 팔꿈치가 아래로 내려옴: `foreshorten` [0.45-0.55, 1.0], `toward` [1, 0]
- 손이 자기 어깨에 아주 가까우면 두 뼈 길이 차이보다 가까워 접히지 못함. 아래팔도 함께 줄이거나(`foreshorten` [0.6, 0.7], `toward` [1, 1]) 목표를 어깨에서 떨어뜨림
- 자세 예시

| 자세 | 값 | 예제 |
|---|---|---|
| 손 흔들기 | `reach` {"mark": "temple_right", "offset": [1.6, -0.3]}, `bend` "down", 손 `open`, `hand_right_view` "palm" | `example_spec_figure_wave.json` |
| V 사인 | `reach` {"mark": "cheek_right", "offset": [1.15, 0]}, `bend` "down", `foreshorten` [0.45, 1], `toward` [1, 0], `wrist` -25, `front` true, 손 `peace`, 손바닥 | `example_spec_figure_peace.json` |
| 기지개 | 두 팔 `reach` {"mark": "crown", "offset": [±0.15, -0.6]}, `bend` "out", 한 팔 `over` | `example_spec_figure_male_stretch.json` |
| 턱 괴기(선 자세) | 오른팔 `reach` {"mark": "chin", "offset": [0, 0.45]}, `foreshorten` [0.55, 1], `toward` [1, 0], `front` true, 손 `fist`. 왼팔 `reach` {"mark": "elbow_right", "offset": [-0.2, 0.35]} | `example_spec_figure_thinking.json` |

### 몸 돌리기 (3/4 시점)

`figure.pose.turn`(도)으로 몸통을 세로축으로 돌린 비스듬한 전신. 양수는 몸 앞면이 화면 오른쪽으로 돌아감

- 몸통 단면(타원)의 보이는 폭이 sqrt((폭 cos)^2 + (깊이 sin)^2)로 바뀜
- 관절(어깨, 골반, 팔다리)은 몸 가운데 면에 있으므로 가로 위치가 cos만큼 좁아짐
- 앞면의 모양(가슴, 배꼽, 쇄골, 목선, 단추, 지퍼)은 앞면 깊이 x sin만큼 돌아가는 쪽으로 이동. 먼 쪽 가슴은 윤곽선에 걸림
- 먼 쪽 팔은 몸통 뒤로 지나가 윤곽 밖으로 나온 부분만 보임(`reach`로 놓은 팔은 예외로 앞에 그려짐). 가까운 다리가 먼 다리 앞에 옴
- 머리는 `pose.yaw_deg`로 함께 돌림(몸 `turn`의 0.7배 전후, 22 이하)
- 의상은 같은 키를 그대로 사용. 정면 시점(`figure.view` "front")만 지원
- 권장 범위 -35에서 35
- 예제: `example_spec_figure_three_quarter.json`(여성 30도), `example_spec_figure_male_three_quarter.json`(남성 -30도, 재킷)

### 앉은 자세(정면)

| 키 | 설명 |
|---|---|
| `figure.seat` | 벤치 그리기. `half_width`(반폭, 머리 단위, 기본 2.2), `board`(상판 두께, 0.45), `leg`(다리 굵기, 0.28). null은 생략 |
| 다리 | `thigh` 양수는 무릎을 벌림, 음수는 모음. `foreshorten` [0.30-0.40, 1.0], `toward` [1, 0] |
| 팔 | 손을 허벅지에 얹기: `upper` 8-14, `fore` -18-0, `foreshorten` [1.0, 0.70], `toward` [0, 1] |

- 허벅지가 관객 쪽으로 나와 무릎 윤곽이 정강이 위에, 허벅지 윤곽이 배 위에 그려짐
- 입체 단서를 자동으로 추가
    + (원근) 무릎 쪽 허벅지가 넓어지고 정강이와 발도 무릎 깊이만큼 커짐
    + (윗면) 위를 향한 허벅지 윗면에 위쪽 조명. 무릎 쪽으로 갈수록, 허벅지 능선에 가까울수록 밝음
    + (접힘) 허벅지와 몸통이 만나는 접힘, 무릎 아래 그늘
- 앉은 허벅지는 의자에 눌려 단면이 넓고 평평해짐
- 바지는 무릎에서 허벅지 폭만큼 부풀고 무릎 위 윗면이 밝아짐
- `figure.clothes.drape`는 앉은 정면에서 무릎 천으로 바뀜
    + 골반을 두르고 허벅지와 무릎을 덮은 뒤 무릎 사이로 처짐, 매듭 끝자락은 허벅지 위에 놓임
    + 손은 천 위에 그려짐
- 예제: `example_spec_figure_seated_front.json`(여성 누드), `example_spec_figure_male_seated_front.json`(남성 의상), `example_spec_figure_male_seated_front_nude.json`(남성 누드, 무릎 천)
- 앉은 자세 판정: 허벅지가 길이의 절반 넘게 관객 쪽으로 나온 다리만 무릎 윤곽, 위쪽 조명, 접힘, 부푼 바지를 받음

### 정면 걷기

`figure.pose.stride`로 관객 쪽으로 걸어오는 자세를 한 번에 정함. 정면 걷기는 대부분 깊이 변화(한 다리는 관객 쪽, 한 다리는 뒤쪽)라서 각도만으로는 보이지 않음

| 키 | 기본 | 설명 |
|---|---|---|
| `lead` | "left" | 앞으로 내딛는 다리(화면 기준) |
| `amount` | 1.0 | 보폭. 뼈를 줄이는 정도에 곱함 |
| `arms` | true | 팔 흔들기. 앞다리 쪽 팔은 뒤로, 반대 팔은 앞으로(팔꿈치를 살짝 굽혀 관객 쪽으로 짧아짐). 뒤로 간 손은 치마와 코트 뒤로 숨음 |

- 앞다리: 허벅지가 관객 쪽으로 조금 나오고 발을 디딤
- 뒷다리: 뒤꿈치를 들어 발목이 0.5 머리 단위 전후 올라가고 발이 짧게 보임. 윤곽선은 앞다리 뒤에 머묾
- `stride`가 있으면 두 다리 값은 `stride`가 정함. `reach`로 놓은 팔은 흔들지 않고 그대로 둠
- 바지와 치마, 코트는 선 자세와 같은 키를 사용
- 걷는 다리가 보이도록 전신 구도를 씀: 눈 높이 0.40이면 `head_unit` 0.034-0.036이 발까지 들어옴
- 예제: `example_spec_figure_front_walk.json`(여성), `example_spec_scene_snow_night.json`, `example_spec_scene_umbrella_rain.json`(걸어오는 커플)

### 측면 자세

`figure.view`가 "side"일 때는 `figure.profile_pose`를 사용

| 키 | 기본 | 설명 |
|---|---|---|
| `lean` | 0 | 몸 전체 기울기(도) |
| `arch` | 0 | 허리 아치(0-1). 가슴이 앞으로, 엉덩이가 뒤로 나옴 |
| `arm` | | 가까운 팔의 `upper`, `fore` 각도. 양수는 앞쪽으로 |
| `leg_near`, `leg_far` | | 가까운 다리와 먼 다리의 `thigh`, `shin` 각도. 먼 다리는 어둡게 뒤에 그려짐 |
| `hand` | "relaxed" | 손 자세 이름 |
| `arm_far`, `hand_far` | 없음 | 먼 쪽 팔의 `upper`, `fore` 각도와 손 자세. 몸 뒤에 어둡게 그려짐. 걷기에 사용 |
| `seat` | false | true면 의자에 앉은 자세. 엉덩이와 허벅지 아래가 의자 상판에서 납작해짐 |
| `wall` | 없음 | true 또는 {"width", "gap"}. 몸 뒤에 기둥을 세우고 그 모서리를 등, 엉덩이, 벽에 댄 발 중 가장 뒤쪽 점에 맞춤(`width` 4.5 머리 단위). 색은 `style.palette.wall` |
| `lift` | 0 | 발바닥 아래 바닥과 그림자까지의 거리(머리 단위). 점프, 뛰는 동작의 체공 |
| 다리의 `foot` | 0 | 발목에서 발을 돌리는 각도. 양수는 발끝이 아래로(뒤로 찬 발, 까치발) |
| 팔의 `reach`, `bend`, `front` | | 가까운 팔의 손 목표점. 지점 `chin`, `mouth`, `cheek`, `brow`, `crown`, `knee`, `ankle` 또는 {"at": [x, y]}, 장면에서는 {"mark": 이름, "of": 상대}(상대 측면 인물의 `nape`, `upper_back`, `lower_back`, `shoulder`, `hip`, `mouth` 등). `bend`는 "forward", "back", "down", "up". `front` true면 아래팔과 손이 얼굴 앞에 옴(턱 괴기), "arm"이면 위팔까지 자기 얼굴과 목 앞에 옴(상대 목을 두른 팔) |

- 측면 머리는 옆얼굴 전용 윤곽을 사용하며 `hair.length`, `hair.wave`, `hair.tip_split`이 적용됨
    + 옆얼굴 비례: 눈은 콧등에서 안쪽으로 들어간 아몬드형(위 눈꺼풀 선이 굵고 속눈썹 끝이 뒤로 뻗음), 입술과 턱은 코끝보다 뒤로 물러남, 귀 앞에 구레나룻
    + 앞모습의 `hair.bangs`가 있으면 정수리에서 이마 위로 넘어오는 앞머리 갈래를 그림
    + 남성은 짧은 머리 윤곽을 사용하므로 `hair.length`가 적용되지 않음
- 측면 앉은 자세 값
    + 다리: 가까운 다리 `thigh` 84-86, `shin` 4-8, 먼 다리 `thigh` 78-80, `shin` -6 - -10
    + 팔: `upper` 10-16, `fore` 72-76 (손이 허벅지 위에 놓임)
    + `lean` 앞으로 숙임 양수, 뒤로 젖힘 음수
    + 바닥: `figure.floor` {"at_feet": true}
- 예제: `example_spec_figure_seated_side.json`(여성), `example_spec_figure_male_seated_side.json`(남성)
- 측면 걷기 값: 가까운 다리 `thigh` 22, `shin` 4, 먼 다리 `thigh` -16, `shin` -30, 가까운 팔 `upper` -22, 먼 팔 `upper` 24, `fore` 38, `lean` 2 (예제 `example_spec_figure_male_walk.json`)
- 측면 각도는 몸 기준. 몸을 `lean`만큼 기울이면 화면에서 본 뼈 각도는 (설정 각도 - `lean`)
- 측면 동작 값

| 동작 | 값 | 예제 |
|---|---|---|
| 뛰기 | `lean` 12, `lift` 0.6, 가까운 다리 `thigh` 67 `shin` -13 `foot` 20, 먼 다리 `thigh` -20 `shin` -125 `foot` 60, 가까운 팔 `upper` -40 `fore` 40, 먼 팔 `upper` 55 `fore` 130, 손 `fist` | `example_spec_figure_side_run.json` |
| 점프 | `lean` -6, `lift` 2.4, 두 팔 `upper` 145-160 `fore` 165-172, 다리 `thigh` 4-24 `shin` -86 - -100 `foot` 34-40 | `example_spec_figure_male_side_jump.json` |
| 웅크려 앉기 | `lean` 30, 다리 `thigh` 128-135 `shin` 15-18 `foot` -8 - -10, 팔 `reach` {"mark": "knee", "offset": [0.7, 1.3]} `bend` "forward" | `example_spec_figure_side_crouch.json` |
| 무릎 꿇고 앉기 | `lean` 2, 다리 `thigh` 68-70 `shin` -90 `foot` 172(발등을 바닥에), 팔 `upper` 6 `fore` 48(손을 허벅지에), 맨발은 `shoes` false | `example_spec_scene_picnic_kneel.json` |
| 다리 꼬고 앉기 | `seat` true, `lean` -4, 위에 얹는 가까운 다리 `thigh` 94 `shin` 12 `foot` 25, 아래 다리 `thigh` 84 `shin` -4, 팔 `upper` 8 `fore` 60(손을 무릎에) | `example_spec_scene_cross_legs.json` |
| 벽에 기대어 서기 | `wall` true, `lean` -6, `arch` 0.6, 벽에 댄 가까운 다리 `thigh` 36 `shin` -88 `foot` 88, 디딤 다리 `thigh` 6 `shin` -4, 팔 `upper` -8 `fore` -10(손을 벽 쪽으로) | `example_spec_scene_lean_wall.json` |

- 허벅지를 앞으로 30도 넘게 올리면(앉은 자세 제외) 엉덩이 윤곽이 펴짐
- 무릎을 140도 넘게 접으면(무릎 꿇기) 바지 다리를 허벅지와 정강이 두 관으로 나누어 접힌 안쪽까지 덮음
- 측면 치마와 원피스 아랫단은 서 있는 몸 기준으로 수직으로 떨어짐. 앉거나 무릎 꿇는 측면 자세에는 바지나 반바지가 자연스러움
- 팔을 18도 넘게 든 측면 긴소매는 어깨 위까지 소매가 덮음
- 측면 인물도 앞모습과 같은 의상 키를 사용. 측면 손에 물건을 들 때는 `holds`의 키를 "near"로 지정(예제 `example_spec_figure_side_holding.json`)

### 어깨 너머 돌아보기

뒷모습(`figure.view` "back") 인물에 `figure.look_back` true 또는 {"side": "left"}

- 몸은 뒷모습으로, 머리는 옆얼굴로 그림. 코, 입술, 턱이 윤곽선 위에 놓여 어깨 너머로 돌린 얼굴이 잘리지 않음
    + 기본은 화면 오른쪽(인물의 오른 어깨)으로 돌아봄. "left"면 반대
    + 옆얼굴 머리는 눈 기준 0.30 머리 단위 돌아보는 쪽, 0.20 아래에 놓여 뒷모습 목이 턱과 귀 밑으로 이어짐
    + 긴 머리는 뒤통수에서 등 위로 흘러내리고, 포니테일과 앞머리도 옆얼굴 규칙을 따름
- 값: `pose.yaw_deg` 0, `roll_deg` 4-8(돌아보는 어깨 쪽으로 고개를 숙임)
- 앞얼굴을 30도 넘게 돌리면 얼굴이 머리 윤곽 밖으로 밀려 잘려 보이므로 돌아보기에는 쓰지 않음
- 예제: `example_spec_scene_look_back.json`(벚꽃길에서 돌아보기)

### 누운 자세

측면 인물을 90도 돌린 좌표계에서 그린 뒤 되돌려 눕힘. 광원과 배경도 같은 좌표계로 돌려 넣으므로 장면의 빛과 맞음

| 키 | 설명 |
|---|---|
| `figure.lying.face` | "up"(등을 대고 누움, 머리 왼쪽) 또는 "down"(엎드림, 머리 오른쪽). 반대 방향은 `pose.mirror` |
| `figure.lying.ground` | 몸이 닿는 바닥 높이(화면 높이 비율, 기본 0.80). 몸의 가장 낮은 점(등 또는 팔꿈치와 허벅지)을 여기에 맞춤 |

- `figure.view` "side"와 함께 사용. `profile_pose`의 각도는 선 자세 기준으로 해석
    + 누운 몸의 위쪽(화면 위)은 "up"이면 몸 앞쪽, "down"이면 몸 뒤쪽
- `pose.head_center`, `pose.head_unit`은 완성 그림 기준
- 등을 대고 누우면 가슴 돌출이 0.8배로 줄어듦. 몸 아래 바닥에 접촉 그림자
- 배경이 없으면 화풍 배경색 위에 `ground`부터 바닥색을 칠함. 배경 피사체(해변, 방 등)와 함께 쓰면 그 위에 누움
- 자세 값
    + 누워서 무릎 세우기: 가까운 다리 `thigh` 55 `shin` -40 `foot` -20, 먼 다리 곧게, 팔 `upper` 20 `fore` 45(손을 허벅지에)
    + 엎드려 팔꿈치 괴기: `lean` -25, 다리 `thigh` -25와 `shin` -70 - -100(발을 들어 올림), 팔 `upper` 65 `fore` 155, 머리 `roll_deg` -55
- 머리카락은 몸 쪽으로 흘러 바닥에 깔림. 긴 머리 엎드린 자세는 포니테일이나 단발이 자연스러움
- 예제: `example_spec_figure_lying_back.json`, `example_spec_figure_lying_front.json`, `example_spec_scene_beach_lying.json`

### 의상

| 키 | 설명 |
|---|---|
| `figure.clothes.dress` | 민소매 원피스. `strap_outer`, `strap_inner`(어깨끈 위치), `neck_level`(목선 깊이), `hem_level`(치마 끝 높이, 9.3은 무릎 위), `hem_half`(치마 끝 반폭), `folds`(주름 수), `fold_depth` |
| `figure.clothes.shirt` | 티셔츠, 셔츠. `ease`(여유), `neck_half`(목둘레 반폭), `neck_level`(목선 높이), `hem_level`(밑단 높이), `sleeve`(소매 길이: 0-1은 위팔 비율, 1-2는 아래팔까지, 1.9는 손목 위), `group`(팔레트, 기본 `cloth`) |
| `figure.clothes.pants` | 바지와 벨트. `waist_level`, `hem_drop`(발목 아래로 내려오는 길이), `leg_widths` [엉덩이, 무릎, 밑단], `length`(1은 긴바지, 0.42는 반바지) |
| `figure.clothes.skirt` | 치마. `waist_level`(기본 3.55), `hem_level`, `hem_half`, `folds`, `fold_depth`, `group`(기본 `skirt`) |
| `figure.clothes.jacket`, `coat` | 셔츠 위 덧옷. `ease`, `hem_level`(6.7은 재킷, 7.0을 넘으면 퍼지는 코트 자락), `hem_half`, `button_level`(앞트임 V의 끝), `buttons`, `sleeve`, `group`(기본 `jacket`) |
| `figure.clothes.jeogori` | 한복 저고리. `ease`, `hem_level`(여성 1.95, 남성 5.4), `sleeve`, `sleeve_hang`(소매 아래로 처지는 배래, 머리 단위), `goreum_length`(옷고름 길이), `trim_group`(깃과 고름 팔레트, 기본 `goreum`) |
| `figure.clothes.chima` | 한복 치마. `top_level`(가슴 위, 기본 0.95), `hem_half`, `hem_drop`(발목 아래 길이), `folds` |
| `figure.clothes.baji` | 한복 바지. `waist_level`, `leg_widths` [엉덩이, 무릎, 대님 위, 대님] |
| `figure.clothes.drape` | 골반을 감싼 천(고전 인체 습작 관례). `top_level`, `bottom_level`, `knot`(매듭 쪽, -1 왼쪽, 1 오른쪽), `slant`(매듭 쪽이 길게 처지는 정도) |
| `figure.clothes.hoodie` | 후드티. 목 둘레에 접혀 놓인 후드(뒷모습은 등 위의 후드), 캥거루 주머니, 끈, 골지 밑단과 소매. `ease`(기본 0.16), `hem_level`(기본 5.0), `sleeve`(기본 1.96), `group`(기본 `hoodie`). true면 기본값 |
| `figure.clothes.swimsuit` | 원피스 수영복. 파인 목선과 어깨끈, 높게 파인 다리선, 뒷모습은 깊게 파인 등. `neck_level`(1.05), `strap_aside`(0.70), `leg_cut`(다리선이 골반 아래로 올라가는 양, 0.55), `back_level`(등 파임, 2.6), `group`(기본 `swim`) |
| `figure.clothes.underwear` | 속옷. 여성은 어깨끈 브라(가슴을 덮는 컵, 밑밴드, 컵 위 밝은 테두리)와 팬티(허리 밝은 띠, 앞 리본), 남성은 드로즈(짧고 붙는 다리, 넓은 고무 허리띠). `bottom_level`(여성 팬티 허리선, 기본 4.7), 남성은 바지 키(`waist_level` 4.95, `length` 0.24, `leg_widths`), `group`(기본 `underwear`). true면 기본값. 정면, 뒷모습, 측면 공통 |
| `figure.clothes.bikini` | 비키니. 홀터넥 삼각 컵과 밑밴드, 낮은 하의. `bottom_level`(하의 허리선, 기본 4.9), `group`(기본 `swim`) |
| `figure.clothes.trunks` | 남성 수영 바지. 허벅지 중간 길이, 허리띠 자리에 허리끈 매듭. 바지 키(`waist_level` 4.85, `length` 0.32, `leg_widths`)를 그대로 받음, `group`(기본 `swim`) |
| `figure.clothes.shoes` | true면 발을 구두 색으로 칠함 |
| `figure.clothes` | null이면 누드 습작 |

- 높이(`*_level`)는 몸통 척추를 따라 잰 머리 단위. 4.85는 허리띠, 5.45는 골반, 6.5는 가랑이
- 남성 프리셋은 `shirt`, `pants`, `shoes`를 켜고 `dress`를 null로 둠
    + 남성 누드는 `{"shirt": null, "pants": null, "shoes": false}`. 골반을 천으로 두르려면 `drape`를 함께 지정
- 칠하는 순서(안에서 밖): 속옷, 수영복, 비키니, 천, 바지, 수영 바지, 한복 바지, 치마, 한복 치마, 셔츠, 원피스, 후드티, 저고리, 재킷, 코트, 가방과 목도리. 그다음 팔을 옷 위에 다시 놓고 소매를 칠함
- 후드티를 남성에게 입힐 때는 기본 티셔츠를 끔: `{"shirt": null, "hoodie": true}`. 수영 바지는 `{"shirt": null, "pants": null, "shoes": false, "trunks": true}`
- 수영복은 몸에 밀착: 몸의 굴곡을 그대로 따르고, 헐렁한 옷처럼 가슴에서 늘어지지 않음
- 색: 원피스와 티셔츠 `style.palette.cloth`, 바지 `pants`(`belt` 포함, 여성 기본 청바지 색), 치마 `skirt`, 재킷과 코트 `jacket`(`button` 포함), 저고리 `jeogori`, 한복 치마 `chima`, 한복 바지 `baji`, 깃과 고름 `goreum`, 동정 `dongjeong`, 천 `drape`, 후드티 `hoodie`(`string` 끈 색 포함), 수영복 `swim`(`string` 포함), 속옷 `underwear`(`trim` 테두리, `band` 남성 허리띠 포함, 남성 프리셋은 짙은 회색), 구두 `shoe`, 의자 `seat`, 컵 `cup`(`drink` 포함), 책 `book`(`pages` 포함)
- 무늬(줄무늬, 체크, 물방울)는 위 팔레트 묶음 어디에나 `pattern`을 넣어 입힘(`references/spec.md`의 무늬)
- 소품(안경, 모자, 목도리, 가방)은 최상위 `accessories` 키(`references/spec.md`의 accessories)
- 의상 예제: `example_spec_figure_shirt_skirt.json`, `example_spec_figure_coat.json`, `example_spec_figure_male_jacket.json`, `example_spec_figure_male_shorts.json`, `example_spec_figure_hanbok.json`, `example_spec_figure_male_hanbok.json`, `example_spec_figure_side_hanbok.json`, `example_spec_figure_hoodie.json`(후드티, 모자, 가방), `example_spec_figure_side_hoodie.json`(측면 후드티, 비니, 안경), `example_spec_figure_swimsuit.json`(줄무늬 수영복, 챙 넓은 모자), `example_spec_figure_bikini.json`(물방울 비키니), `example_spec_figure_male_trunks.json`(줄무늬 수영 바지, 캡), `example_spec_figure_patterns.json`(줄무늬 셔츠, 체크 치마, 목도리)
- 누드 습작 예제

| 파일 | 내용 |
|---|---|
| `example_spec_figure_nude.json` | 여성 정면, 무릎 위 구도, 손을 허리에 얹은 콘트라포스토 |
| `example_spec_figure_back.json` | 여성 뒷모습 |
| `example_spec_figure_side.json` | 여성 측면, 허리 아치 |
| `example_spec_figure_male_nude.json` | 남성 정면, 골반 천 |
| `example_spec_figure_male_back.json` | 남성 뒷모습 |
| `example_spec_figure_male_side.json` | 남성 측면, 가까운 다리를 앞으로 내딛은 구도 |
| `example_spec_figure_male_seated_front_nude.json` | 남성 정면 앉은 자세, 무릎 천 |

### 표현 강도

`style.body_render`

| 키 | 설명 |
|---|---|
| `figure_level`, `figure_spread` | 몸 그림자의 양과 경계 폭. `figure_level`을 올리면 그림자가 넓어짐 |
| `cloth_level` | 옷 그림자의 양 |
| `skin_sheen` | 피부 광택. 0은 무광 |
| `accent` | 쇄골, 배꼽, 무릎 등 해부학 강조의 농도. 0은 생략. 선화 화풍의 남성은 가슴근 아래선, 복근, V선을 획으로 추가 |
| `top_light` | 앉은 정면 허벅지 윗면의 위쪽 조명 농도. 기본 0.55, 회화풍 0.8 |

## 장면 합성 (backdrop, companions)

초상과 전신 인물의 설정에 넣는 키. 배경을 먼저 그리고, 동반 인물을 그린 뒤, 주 인물을 맨 앞에 그림

| 키 | 설명 |
|---|---|
| `backdrop.subject` | 배경으로 쓸 피사체(`city`, `landscape`, `beach`, `park`, `sakura`, `rooftop`, `fireworks`, `cafe`, `room`, `bedroom`, `bathroom`, `desk`, `still_life`, `figure` 등). 화면 크기는 주 인물을 따름 |
| `backdrop.spec` | 배경 피사체의 설정. `light`를 비우면 주 인물의 광원을 사용 |
| `backdrop.place` | "horizon"이면 모든 인물의 눈을 배경의 지평선에 맞춤(도시, 풍경, 카페, 방). 서 있는 성인은 카메라 눈높이와 같기 때문 |
| `backdrop.blur` | 배경 흐림(화면 폭 대비). 0.006 전후면 초상 뒤 흐린 배경 |
| `backdrop.fade` | {"color", "amount"}. 배경을 한 색 쪽으로 물려 인물을 띄움 |
| `companions` | 다른 인물 설정의 목록. 각 항목에 `subject`(기본 `figure`), `sex`, `pose.head_center`, `pose.head_unit` 등. 먼 인물이 먼저 그려짐 |
| `grade` | {"color", "amount"}. 인물에 배경 빛의 색조를 입힘(야경은 푸른 보라 0.3 전후, 밤의 방은 따뜻한 주황 0.18 전후) |
| `weather` | {"kind": "rain", "snow", "petals"}. 야외 배경이면 인물 앞까지 비, 눈, 꽃잎이 내리고, 실내 배경(카페, 방)이면 창밖에만 내림 |
| `pose.horizon_drop` | "horizon" 배치에서 이 인물의 눈만 화면 높이 비율만큼 내림(키 작은 사람, 기대는 고개) |
| `props` | 여러 인물이 함께 쓰는 소품 목록(아래 절) |
| 동반 인물의 `lift` | 이 인물의 부위를 뒤에 그린 인물 위에 다시 올림(아래 절) |

- 배경 위에서는 바닥면을 새로 칠하지 않고 발밑 그림자만 더함(`figure.floor`가 있을 때)
- 인물 크기는 `head_unit`으로 정함. 눈이 지평선에 있으면 크기가 곧 거리
- 전신이 화면에 들어가는 기준: 눈 높이 0.40이면 `head_unit` 0.044, 0.42이면 0.040 전후
- 그리는 순서는 `companions` 목록 순서, 주 인물이 맨 마지막(맨 앞)
- 좌우 반전(`pose.mirror`)한 인물의 `head_center` x는 반전 전 기준. 화면 x 0.67에 세우려면 0.33
- 예제: `example_spec_scene_city_night.json`, `example_spec_scene_pair.json`, `example_spec_portrait_city_bokeh.json`, `example_spec_scene_cafe.json`(비 오는 날 카페 속 인물), `example_spec_scene_room_night.json`(밤의 방), `example_spec_portrait_cry_rain.json`(비 오는 밤거리의 우는 초상)

### 인물끼리의 접촉

- 손잡기: 두 인물의 손이 같은 화면 지점을 겨눔. `reach` {"at": [x, y]}, `bend` "straight", 손 `grip`(위에 오는 손)과 `relaxed`
    + 나중에 그린 인물의 손이 위에 놓임
- 상대 몸에 손 얹기: `reach` {"mark": "shoulder_right", "of": "main", "offset": [-0.1, 0.0]}
    + 장면이 상대 인물을 먼저 세워 지점을 읽고 화면 위치로 바꿈
    + 서로를 겨누는 두 팔은 순환이 되므로 손잡기는 같은 `at` 지점을 사용
- 앞뒤 엇갈림: 동반 인물의 `lift`에 다시 올릴 부위를 적음
    + "hand_<side>", "forearm_<side>"(아래팔과 손, 소매), "arm_<side>"(팔 전체)
    + {"part": "forearm_right", "from": 0.7}은 아래팔의 70% 지점부터 손까지만 올림
    + 올리는 범위는 그 인물이 실제로 칠한 화소로 한정. 부위 밖 띠에서는 윤곽선만 따라옴(아래보다 어두운 화소만 올림)
    + 동반 인물의 `lift_under_head` true면 올린 부위가 뒤에 그린 인물의 얼굴과 앞머리 아래로 지나감
- 어깨동무: 안는 사람을 동반 인물로 먼저 그리고 팔을 상대의 먼 어깨로 `straight`로 뻗음. `hand` 10 전후로 손가락이 어깨 앞으로 늘어지게 하고 `lift` {"part": "forearm_right", "from": 0.7}, `lift_under_head` true
    + 팔은 상대의 목과 등 뒤로 지나가고 먼 쪽 머리카락 아래에서 소매 끝과 손만 다시 나옴
    + `from` 0.7 전후로 소매 끝과 손만 올려 팔이 머리카락 아래에서 나오게 함
- 팔에 손 얹기(팔짱): 손 주인을 동반 인물로 두고 `reach` {"mark": "elbow_right", "of": "main", "offset": [0.3, -0.3]}, `bend` "down", `foreshorten` [1.0, 0.6], `toward` [0, 1], `hand` 80, `lift` {"part": "forearm_left", "from": 0.5}
    + 두 인물 머리 사이를 화면 폭 0.17 전후로 띄우면 팔이 펴져 손이 소매 밖으로 나옴
- 기대기: 기대는 사람의 `roll_deg`를 상대 쪽으로(왼쪽 상대면 음수), `figure.neck_shift` 0.5-0.8로 몸을 반대로 비키고 `figure.pose.neck_lean` -0.3 전후, `horizon_drop` 0.02 전후
- 서로를 향해 몸을 돌리면(`turn` ±10-15) 투샷이 자연스러워짐
- 예제: `example_spec_scene_beach.json`(손잡기, 손 흔들기), `example_spec_scene_snow_night.json`(걸으며 어깨동무, 기대기), `example_spec_scene_umbrella_rain.json`(우산 쓰고 걸으며 팔에 손 얹기), `example_spec_scene_bench.json`(벤치에서 손잡기와 기대기)

### 여러 인물 장면 (단체 사진, 건배, 춤, 셀카)

- 정면 인물의 `arm_left`는 화면 왼쪽 팔, `arm_right`는 화면 오른쪽 팔. 가운데를 향해 손을 뻗을 때는 화면 왼쪽 인물은 `arm_right`, 오른쪽 인물은 `arm_left`
- 팔꿈치 방향(`bend`)의 "out"은 그 팔 쪽 바깥, "in"은 몸 가운데. 화면 오른쪽 인물의 `arm_left`에서 "out"은 무리 가운데를 향함
- 그리는 순서: 남의 어깨에 팔을 두르는 사람을 먼저(동반 인물 앞쪽), 그 팔이 지나가는 사람을 나중에 그리고 `lift`로 손만 다시 올림
- 넷이 정면으로 설 때 가로 화면(1600x1200) 기준 `head_unit` 0.030, 사람 사이 화면 폭 0.16 전후. 손 목표가 팔 길이(머리 단위 6 전후)를 넘으면 팔이 다 펴진 자리에서 멈춤

| 장면 | 구성 | 예제 |
|---|---|---|
| 세 친구 단체 사진 | 가운데 인물(동반 인물 0)이 두 팔 `reach` {"mark": "shoulder_left", "of": 1}과 {"mark": "shoulder_right", "of": "main"}, `bend` "straight", `lift` 두 손(`"hand_left"`, `"hand_right"`), `lift_under_head` true, 소매 1.6. 양옆 인물은 바깥 손 V 사인(`reach` {"mark": "cheek_left", "offset": [-1.15, 0]}, `foreshorten` [0.45, 1], `toward` [-1, 0], 손 `peace`) | `example_spec_scene_friends_photo.json` |
| 넷이 건배 | 네 사람이 가운데 쪽 손에 `holds` {"kind": "glass"}, 손 `grip`, 팔 `reach` {"at": 머리 위 지점}. 안쪽 두 사람은 잔이 맞닿게 자기 어깨 바로 위로, 바깥 두 사람은 자기 머리와 이웃 머리 사이 위로 | `example_spec_scene_toast_party.json` |
| 커플 댄스 | 측면 남자의 가까운 팔과 정면 여자의 팔이 같은 머리 위 지점(`at`)을 겨눠 손을 맞잡음. 여자의 다른 팔은 옆으로 펼치고(`upper` 62 `fore` 40), 넓은 원피스 단(`hem_half` 3.2, `folds` 7) | `example_spec_scene_dance_rooftop.json` |
| 셀카 | 두 얼굴을 가까이(사이 화면 폭 0.18), `roll_deg`를 서로 쪽으로. 한 사람은 화면 밖 아래 구석으로 팔을 뻗어(`reach` {"at": [0.06, 0.93]}, `foreshorten` [1.0, 0.7]) `holds` {"kind": "phone"}, 다른 사람은 V 사인 | `example_spec_scene_selfie_fireworks.json` |

### 포옹과 입맞춤 (측면)

마주 선 측면 인물 두 명. 상대 몸을 감싼 가까운 팔이 상대 앞(관객 쪽)에 보임

- 배치: 한 사람은 오른쪽을 보고, 다른 사람은 `pose.mirror` true로 왼쪽을 봄. 나중에 그리는 주 인물의 팔은 그대로 상대 위에 놓임
- 입맞춤
    + 두 사람 모두 `expression` "kiss"
    + 고개: 키 큰 쪽은 상대 쪽으로 숙이고(거울 인물은 `roll_deg` 양수 18 전후), 작은 쪽은 들어 올림(-14 전후)
    + 두 사람의 입 지점(`mouth`)이 겹치도록 `head_center` x를 맞추고, 발바닥(`soles`)이 같은 바닥에 오도록 `horizon_drop`을 맞춤
- 허리 감싸기(주 인물): 팔 `reach` {"mark": "lower_back", "of": 0, "offset": [-0.25, 0]}, `bend` "down", 손 `relaxed`
- 목 두르기(동반 인물): 팔 `reach` {"mark": "upper_back", "of": "main", "offset": [-0.35, 1.3]}, `bend` "up", `front` "arm"
    + 동반 인물의 `lift` ["arm_near"], `lift_under_head` true: 상대 위로 팔 전체를 다시 올리되 상대 얼굴과 머리카락 아래로 지나감
    + 손 목표를 상대 등 위쪽에서 아래로 내릴수록 팔꿈치가 낮아져 상대 턱 아래 목 앞에 놓임
- 까치발: 다리 `foot` 25-30
- 측면 표시 지점 추가: `mouth`, `nape`(목 뒤), `upper_back`(견갑), `lower_back`(허리 뒤)
- 예제: `example_spec_scene_embrace.json`(밤의 침실, 속옷 차림), `example_spec_scene_embrace_bath.json`(욕실)

### 장면 소품 (props)

여러 인물이 함께 쓰는 소품. 장면이 인물들을 재서 크기와 위치를 정하고 맨 먼저 그리는 인물의 배경 단계에 그림

| `kind` | 키 | 설명 |
|---|---|---|
| `bench` | `on`(기본 모든 인물), `backrest`(기본 true), `overhang`(엉덩이 밖으로 나가는 길이, 머리 단위 2.0) | 정면으로 앉은 인물들의 엉덩이부터 무릎까지 걸친 긴 벤치와 등받이. 인물의 `figure.seat`는 null |
| `table` | `on`, `elbow_of`(이 인물의 팔꿈치 높이에 상판), `above_seat`(상판 높이, 의자 위 머리 단위 3.4), `x`(화면 비율), `radius`(머리 단위 2.7), `cups`(컵 위치 목록, 중심에서 머리 단위) | 측면으로 앉은 인물들 사이의 원형 카페 탁자. 무릎 사이 가운데에 섬 |

- 앉은 높이는 카메라 눈높이보다 낮으므로 카페 장면은 배경 카메라 `horizon_y`를 앉은 눈높이에 맞추고 머리 단위를 작게(0.028 전후, 1600x1200)
- 예제: `example_spec_scene_bench.json`, `example_spec_scene_cafe_date.json`

### 우산

`figure.holds`의 {"kind": "umbrella"}. 손에 쥔 손잡이부터 머리 위 덮개까지 세움

| 키 | 기본 | 설명 |
|---|---|---|
| `radius` | 4.4 | 덮개 반지름(머리 단위). 두 사람을 덮으려면 4.4 전후 |
| `rise` | 4.9 | 손에서 덮개 테두리까지 높이(머리 단위) |

- 아래에서 올려다본 돔, 부채꼴 끝단 사이로 보이는 안쪽 면, 살, 갈고리 손잡이와 꼭지
- 머리를 그린 뒤 그리므로 덮개가 머리카락과 동반 인물 위에 놓임. 우산을 든 인물을 주 인물로 둠
- 비가 오면 덮개와 그 아래 기둥 영역에 빗줄기가 내리지 않음(가장자리는 부드럽게 줄어듦). 회색빛과 안개는 그대로
- 손잡이를 두 얼굴 사이에 두려면 손 목표를 `at`으로 지정. 대가 얼굴을 가로지르지 않도록 두 머리 사이를 화면 폭 0.15 이상 띄움
- 가슴 높이에서 쥔 손: `bend` "down", `foreshorten` [1.0, 0.65], `toward` [0, 1], `front` true. 위팔은 몸 옆으로 내려와 팔꿈치가 옆구리에 오고 아래팔이 손잡이까지 올라감
    + 손 목표는 자기 어깨보다 화면 폭 0.05 전후 상대 쪽, 어깨보다 조금 아래
- 색: `style.palette.umbrella`(`base`, `shadow`, `light`, `line`, `inner` 안쪽 면, `shaft` 대)
- 예제: `example_spec_scene_umbrella_rain.json`

### 와인잔, 휴대폰, 담배

`figure.holds`의 {"kind": "glass"} 또는 {"kind": "phone"}. 손 자세는 `grip`

| `kind` | 키 | 설명 |
|---|---|---|
| `glass` | `drink`(술 색 "#A3263A" 기본 적포도주), `size` | 대를 쥔 와인잔. 주먹 위로 투명한 잔과 술, 아래로 받침 |
| `phone` | `turn`(기울기 도), `size` | 뒷면이 보이는 휴대폰(카메라 렌즈 2개). 셀카를 찍는 손 |
| `cigarette` | `point`(1 또는 -1, 불붙은 끝 방향), `lit`, `smoke`, `size` | 검지와 중지 사이에 낀 담배와 연기. 손 자세는 `relaxed`. 손가락 위에 놓여 손을 다시 올리지 않음 |

- 색: `style.palette.glass`(`base` 유리 색조, `light` 반사, `line`, `drink`), `style.palette.phone`(`base`, `shadow`, `line`, `lens`)

## hand (손)

| 키 | 설명 |
|---|---|
| `hands` | 손 목록. 항목마다 `pose`, `x`, `y`(손목 위치, 화면 비율), `size`(손 길이, 화면 높이 대비), `angle`(회전, 0은 손끝이 위), `mirror`(반대 손), `view`("back" 손등, "palm" 손바닥), `sex`, `width`(손 폭 배율) |
| `sex` | 모든 손의 기본 성별. "male"이면 넓은 손(`width` 1.15), 굵은 마디, 짧고 옅은 손톱, 손등 혈관 |

- 자세 이름: `open`(펼침), `relaxed`(이완), `victory`(V), `point`(가리킴)
- 새 자세는 `scripts/anatomy_hand.py`의 `POSES`에 손가락별 관절 굽힘 각도 3개, `spread`(벌림), `thumb`(엄지 접힘)을 추가
- 손바닥 시점은 엄지 쪽이 바뀌고 손금, 손목 주름, 살 둔덕을 그림(손톱 생략)
- 남성 손 예제: `example_spec_hand_male.json`

## still_life (정물)

위치와 크기는 화면 폭 대비 비율. 사물은 바닥 높이 순서로 뒤에서 앞으로 그려짐

| 키 | 설명 |
|---|---|
| `table.back_y`, `table.front_y` | 탁자 윗면의 뒤쪽과 앞쪽 가장자리 |
| `cloth` | 천의 `left`, `right`, `drop`(늘어진 길이), `folds`. 항목을 빼면 천 생략 |
| `objects` | 사물 목록 |

| `kind` | 필수 항목 | 선택 항목 |
|---|---|---|
| `bottle`, `vase`, `jar`, `cup` | `x`, `base_y`, `height`, `radius`, `group` | `gloss`, `shininess`, `label` {`top`, `bottom`} |
| `bowl` | `x`, `rim_y`, `radius`, `depth`, `group` | `fruit`: 그릇 중심 기준 `dx`, `dy`를 가진 `ball` 목록 |
| `ball` | `x`, `base_y`, `rx`, `ry`, `group` | `angle`, `stem`, `tips`(레몬 꼭지), `gloss` |
| `pear` | `x`, `base_y`, `height`, `radius`, `group` | `tilt_deg` |
| `ashtray` | `x`, `base_y`, `radius` | `butts`(꽁초 수), `lit`(테두리에 걸친 불붙은 담배), `smoke`, `group`(기본 `ashtray`, `ash` 색 포함) |
| `tea_glass` | `x`, `base_y`, `radius`, `height` | `handle`("right", "left"). 금속 받침(`holder`)에 끼운 유리잔 홍차(`tea`)와 숟가락 |
| `can` | `x`, `base_y`, `radius`, `height` | `group`(기본 `can`, `band` 띠 색 포함) |

- `group`은 `style.palette`의 색 묶음 이름. 새 색은 `base`, `shadow`, `deep`, `light`, `line`을 가진 묶음으로 추가
- 유리처럼 반짝이는 재질은 `gloss` 0.8 이상과 `shininess` 80 이상
- `wall_items` [{"kind": "window", "x0", "x1", "y0", "y1", "block_top", "columns", "lit"}]: 뒷벽의 밤 창문. 창밖에 맞은편 아파트 벽과 불 켜진 창 몇 개, 창틀과 창턱(색 `window`)
- 예제: `example_spec_still_life_kitchen_night.json`(밤의 부엌 식탁, `--style doomer`)

## desk (책상)

책상을 센티미터 단위 3차원 공간(X 오른쪽, Y 위, Z 안쪽)에 놓고 위에서 내려다보는 카메라로 투영

| 키 | 설명 |
|---|---|
| `camera` | `position` [x, y, z](cm), `pitch_deg`(내려다보는 각도), `focal`(화각), `center_x`, `center_y`(화면 중심) |
| `room` | `window_glow`(창 쪽 벽 밝기), `screen_spill`(화면 빛이 책상에 번지는 정도) |
| `desk` | `width`, `front_z`, `back_z`, `thickness`, `grain`(나뭇결 농도) |
| `objects` | 사물 목록. 공통 `kind`, `x`, `z`(cm) |

| `kind` | 항목 |
|---|---|
| `monitor` | `width`, `height`, `lift`(받침 높이), `foot`, `angle`, `on` |
| `laptop` | `width`, `depth`, `open_deg`(화면 열림 각도), `angle`, `on`, `keys` |
| `keyboard` | `width`, `depth`, `angle` |
| `mouse` | 없음 |
| `phone` | `width`, `depth`, `angle`, `on` |
| `mug` | `radius`, `height`, `steam` |
| `plant` | `radius`, `height`, `leaves` |
| `lamp` | `reach`(머리까지 가로 거리, 음수는 왼쪽), `height`, `on` |
| `notebook` | `width`, `depth`, `angle`(펜 포함) |

- 화면 내용은 단순한 앱 화면(상단 막대, 사이드바, 카드 2개, 글 줄)으로 그려짐. 색은 `style.palette.screen`
- 켜진 화면과 스탠드는 광원으로 처리되어 주변 책상을 밝힘
- 어두운 방은 `example_spec_desk_night.json`처럼 벽, 책상, 기기 색을 어둡게 바꾸고 `screen_spill`을 올림

## landscape (풍경)

세로 위치는 화면 높이 대비, 가로 위치는 화면 폭 대비 비율

| 키 | 설명 |
|---|---|
| `horizon_y` | 수면선 높이 |
| `sky` | `sun_x`, `sun_y`, `sun_r`, `clouds`(0-1, 구름 양), `birds`(새 수) |
| `ranges` | 먼 산부터 가까운 산 순서의 목록. `group`(색 묶음), `amplitude`(높이), `roughness`(0.4 완만, 0.6 험준), `snow`(설선), `forest`(숲 톱니 간격), `haze`(안개 농도) |
| `water` | `ripple`(반영 흔들림), `glitter`(햇빛 반짝임 수), `streaks`(잔물결 수) |
| `bank` | 앞 기슭의 `top_y`, `amplitude`, `dip`, `grass`, `rocks` [[x, 크기], ...] |
| `pines` | 침엽수 목록 [[x, 높이], ...] |

- 시간대는 `style.palette.sky`의 `top`, `middle`, `horizon` 3색으로 결정
- 산세는 `seed`로 바뀜

## beach (해변)

먼 곳부터 하늘, 수평선까지의 바다, 부서지는 파도 거품, 젖은 모래와 마른 모래, 야자수 순서로 칠함. 세로 위치는 화면 높이 비율, 가로 위치는 화면 폭 비율

| 키 | 설명 |
|---|---|
| `horizon_y` | 수평선 높이. `backdrop.place` "horizon"이면 서 있는 인물의 눈이 여기에 옴 |
| `sky` | `sun_x`, `sun_y`, `sun_r`, `clouds`(풍경과 같음) |
| `sea` | `shore_y`(물가 높이), `waves`(잔물결 수), `glitter`(햇빛 반짝임 수) |
| `sand` | `ripples`(바람 물결 자국 수) |
| `palms` | 야자수 목록 [[x, 밑동 y, 높이, 기울기], ...]. 높이는 화면 높이 비율, 기울기는 높이 대비 가로 이동 |

- 바다는 수평선 쪽이 짙고 물가로 오며 옅은 청록. 물가선은 완만하게 굽이침
- 젖은 모래 띠는 하늘빛을 받아 밝고, 거품선 위로 다음 파도의 옅은 선이 보임
- 색: `style.palette.sky`, `sea`(`deep`, `shallow`, `light`, `glitter`, `foam`), `sand`(`far`, `near`, `wet`, `shadow`), `palm`(`trunk`, `trunk_shadow`, `leaf`, `leaf_shadow`, `line`)
- 예제: `example_spec_scene_beach.json`, `example_spec_scene_beach_lying.json`(`backdrop.subject` "beach")

## city (도시)

거리를 미터 단위 3차원으로 배치한 뒤 투시 투영

| 키 | 설명 |
|---|---|
| `camera` | `vanish_x`, `horizon_y`(소실점 위치), `focal`(화각, 클수록 망원), `eye_height`(눈높이, m) |
| `street` | `road_half_width`, `building_line`(건물선까지 거리), `length`(거리 길이), `haze`, `building_depth` [최소, 최대], `building_height` [최소, 최대], `crosswalk_z`, `pole_spacing`, `tree_spacing` |
| `sky.clouds` | 구름 양(0-1) |

- 건물 배열은 `seed`로 바뀜

### 야경

| 키 | 기본 | 설명 |
|---|---|---|
| `night.on` | false | 야경 켜기 |
| `night.lit` | 0.45 | 불 켜진 창의 비율 |
| `night.shops` | 0.85 | 불 켜진 상점의 비율 |
| `night.stars` | 260 | 별 수 |
| `night.cars` | 3 | 차선마다 차 수(멀어지는 차는 미등, 다가오는 차는 전조등) |
| `night.wet` | 0.75 | 젖은 노면 반사 강도. 0은 마른 길 |

- 밤 색은 `style.palette.city_night`, `foliage_night`, `trunk_night`가 낮 색을 덮어씀
- 간판, 창, 가로등, 차 불빛은 빛 번짐을 만들고 노면에 세로로 번진 반사를 남김
- 색은 `style.palette.city`: `walls`(벽 색 목록), `awnings`, `signs`, `shade_tint`(그늘 색조), `haze`
- 해가 드는 쪽은 `light`의 x 부호로 결정

## park, sakura (공원과 벚꽃길)

서 있는 사람의 눈높이에서 본 야외 땅. 실내와 같은 센티미터 단위(X 오른쪽, Y 위, Z 안쪽)와 수평 카메라를 쓰므로 길이 지평선 위 한 소실점으로 모이고 나무가 거리에 따라 작아짐. 두 피사체는 같은 모듈(`scripts/subject_park.py`)을 쓰고 기본 구성만 다름

| 피사체 | 기본 구성 |
|---|---|
| `park` | 피크닉 잔디밭. 깎은 줄무늬 잔디, 들꽃, 앞쪽 풀잎, 먼 숲 띠, 띄엄띄엄 선 초록 나무, 체크무늬 돗자리와 바구니 |
| `sakura` | 벚꽃길. 지평선까지 뻗은 포장 산책로, 양쪽에 짝지어 선 벚나무가 머리 위에서 맞닿는 꽃 터널, 땅에 떨어진 꽃잎, 분홍빛 먼 숲 띠. 단독 렌더링은 날리는 꽃잎(`weather` "petals") 포함 |

| 키 | 기본 | 설명 |
|---|---|---|
| `camera` | `eye_height` 155, `horizon_y` 0.42(공원), 0.47(벚꽃길), `focal` 0.70-0.75 | 실내와 같은 카메라 |
| `sky` | | 풍경과 같은 하늘(`sun_x`, `sun_y`, `sun_r`, `clouds`) |
| `haze` | {"distance": 9000, "amount": 0.6} | 먼 나무를 하늘빛으로 덮는 정도(cm 거리) |
| `treeline` | | 지평선 위 먼 숲 띠 {"lift", "amplitude", "crown", "group"("treeline" 초록, "blossom_far" 분홍), "haze"} |
| `lawn` | | {"stripes"(깎은 줄 폭 cm, 0이면 없음), "blades"(앞쪽 풀잎 수), "flowers"(들꽃 수)} |
| `path` | 없음(벚꽃길 {"half_width": 180}) | 화면 앞에서 소실점까지 뻗는 포장길. 보도블록 이음매와 경계석 |
| `avenue` | 없음(벚꽃길) | 길 양쪽에 짝지어 심은 나무 {"kind"("sakura", "green"), "offset"(길가에서 줄기까지 cm), "first_z", "last_z", "spacing"} |
| `trees` | 공원 4그루 | 낱 나무 목록 [{"x", "z", "kind", "size"}] |
| `blanket` | 공원 | 돗자리 {"x", "z", "width", "depth", "turn_deg", "check"(체크 칸 cm)} |
| `basket` | 공원 | 뚜껑과 손잡이가 있는 바구니 {"x", "z", "turn_deg"} |
| `petals` | 없음(벚꽃길) | 땅에 떨어진 꽃잎 {"ground"(개수), "far"(흩어진 거리 cm)} |
| `time` | "day" | 낮에는 나무 그늘(얼룩진 빛)을 땅에 드리움 |

- 나무: 길 쪽으로 기운 줄기와 갈래 가지 위에 덩어리 여러 개로 된 둥근 지붕 모양 수관. 수관 안쪽 틈으로 가지와 하늘이 비침. 벚꽃은 밝은 꽃송이 무리와 짙은 그늘 틈을 얹음
- 무릎 꿇거나 앉은 인물을 돗자리에 올릴 때는 카메라를 낮춤(`eye_height` 100 전후)과 인물의 `horizon_drop`(눈이 카메라보다 낮은 만큼)
- 색: `sky`, `treeline`, `blossom_far`, `lawn`(`far`, `near`, `stripe`, `shadow`, `blade`, `blade_light`), `path`(`base`, `far`, `seam`, `kerb`), `blossom`, `foliage`(`base`, `shadow`, `light`, `line`), `trunk`, `blanket`(`white`, `check`, `deep`), `basket`, `basket_lid`, `petal`, `flower`
- 예제: `example_spec_scene_friends_photo.json`(벚꽃길 단체 사진), `example_spec_scene_look_back.json`(벚꽃길 돌아보기), `example_spec_scene_picnic_kneel.json`(돗자리에 무릎 꿇고 앉기)

## rooftop, fireworks (노을 옥상과 불꽃놀이 강변)

`scripts/subject_skyline.py`. 서 있는 사람의 눈높이에서 본 도시 스카이라인. 건물 앞면이 화면과 나란한 직사각형이어서 층층이 겹친 건물 줄로 깊이를 만듦

| 피사체 | 기본 구성 |
|---|---|
| `rooftop` | 노을. 보라에서 금빛으로 넘어가는 하늘, 건물 사이로 지는 해, 해 가까이 금빛으로 물든 긴 구름, 역광의 어두운 건물과 윗면 테두리 빛, 콘크리트 타일 바닥, 유리 난간, 머리 위 전구 줄, 화분 |
| `fireworks` | 밤의 강변. 별, 불꽃 4발, 불을 켠 고층 건물, 건물과 불꽃을 비추고 빛을 아래로 길게 늘이는 강, 돌 포장 산책로와 난간 |

| 키 | 설명 |
|---|---|
| `time` | "sunset" 또는 "night" |
| `sky` | `sun_x`, `sun_y`, `sun_r`(화면 비율), `clouds`(0-1), `stars`(밤 별 수) |
| `fireworks` | 불꽃 목록 [{"x", "y", "r"(화면 비율), "color", "kind", "rays", "tail"}]. `kind` "trail"(빛줄기 국화), "dots"(별 알갱이 모란), "willow"(늘어지는 버들). `tail` true면 올라가는 꼬리 |
| `skyline` | 먼 줄부터 건물 줄 목록 [{"z"(cm), "height"(바닥 기준 꼭대기 높이 범위 cm), "width", "gap", "haze", "base"}]. 일부 건물은 위층이 들어간 층계 모양이나 안테나(밤에는 붉은 항공등) |
| `lit` | 불 켜진 창 비율(노을 0.12, 밤 0.5 기본) |
| `river` | 강 {"z0", "z1"(건너편 둑 cm), "level"(수면 높이 cm), "ripple", "waves"} |
| `floor` | {"kind": "roof" 또는 "promenade", "tile"(cm)} |
| `railing` | {"z", "wall"(아래 벽 높이 cm), "height"(손잡이 높이), "posts"(기둥 간격), "glass"(기둥 사이 유리)} |
| `lights` | 전구 줄 [{"from": [x, y, z], "to": [x, y, z], "sag", "bulbs"}] |
| `plants` | 바닥 화분 [{"x", "z", "radius", "height"}] |

- 노을의 바닥에는 해 쪽에서 관객 쪽으로 따뜻한 빛길, 밤의 바닥에는 불꽃 색이 옅게 물듦
- 인물을 세우면 노을 빛은 `grade` {"color": "#FFB98A", "amount": 0.22}, 불꽃놀이는 {"color": "#B9A8E8", "amount": 0.2} 전후가 어울림
- 지평선을 바꾸면 해와 불꽃의 `y`도 함께 옮겨야 건물에 가리지 않음
- 색: `sky`(`top`, `middle`, `low`, `horizon`, `glow`, `sun`, `cloud`, `cloud_warm`, `cloud_lit`, `night_top`, `night_middle`, `night_low`), `city`와 `city_night`(`face`, `shade`, `haze`, `base`, `glass`, `window_lit`, `rim`, `beacon`), `water`, `floor`, `railing`(`wall`, `cap`, `metal`, `shine`, `glass`), `lights`
- 예제: `example_spec_scene_dance_rooftop.json`(노을 옥상의 춤), `example_spec_scene_selfie_fireworks.json`(불꽃놀이 셀카)

## panelka, outskirts (판넬 아파트 단지와 외곽 들판)

`scripts/subject_blocks.py`. 두머 감성의 무대. 공원, 옥상과 같은 센티미터 수평 카메라를 써서 인물을 지평선에 세울 수 있음

| 피사체 | 기본 구성 |
|---|---|
| `panelka` | 밤의 단지 마당. 세 방향의 9-12층 판넬 아파트(패널 이음매, 빗물 얼룩, 창 격자 중 일부만 불 켜짐, 텔레비전 빛 창, 발코니, 현관등), 눈 덮인 땅과 밟힌 길, 전봇대와 처진 전선, 나트륨 가로등과 빛 웅덩이, 앙상한 자작나무, 그네. 단독 렌더링은 눈(`weather` "snow") 포함 |
| `outskirts` | 해 질 녘 도시 외곽. 마른 풀밭과 흙길, 지평선까지 줄지은 송전탑과 처진 전선 세 가닥, 멀리 늘어선 아파트, 지평선의 따뜻한 빛, 까마귀 |

| 키 | 설명 |
|---|---|
| `time` | "night" 또는 "dusk" |
| `camera` | 실내와 같은 카메라(`horizon_y`, `focal`, `eye_height`, `x`) |
| `sky` | `clouds`(0-1, 낮게 깔린 층운), `stars` |
| `haze` | {"distance", "amount"}. 먼 건물을 하늘빛으로 덮는 정도 |
| `ground` | `snow`(true 눈, false 마른 풀), `path`([[x, z], ...] 길 중심선), `width`(길 폭 cm), `ruts`(바퀴 자국 x 목록), `stalks`(풀 줄기 수) |
| `blocks` | 건물 목록. {"face": "front", "z", "x0", "x1"}은 관객을 향한 벽, {"face": "side", "x", "z0", "z1"}은 안쪽으로 뻗는 옆벽. 공통 `floors`(층 수), `lit`(불 켜진 창 비율, 밤 0.18), `balconies`(발코니 있는 열 비율), `doors`(현관 수, 밤에 현관등), `salt`(창 배치 난수) |
| `poles`, `wires` | 전봇대 [{"x", "z", "height"}]. 이웃 전봇대 사이와 화면 밖으로 전선이 처짐(`wires.sag`, `wires.count`) |
| `lamps` | 가로등 [{"x", "z", "height", "arm"(1 오른쪽, -1 왼쪽으로 뻗은 팔)}]. 밤에 머리가 빛나고 땅에 빛 웅덩이 |
| `birches` | 자작나무 [{"x", "z", "height"}]. 흰 줄기의 검은 무늬와 재귀 가지 |
| `swing` | 그네 {"x", "z"}. 끄려면 null |
| `pylons` | 송전탑 줄 {"x", "z0", "spacing", "count", "height", "drift", "sag"} |
| `crows` | {"perched": 전선 위 까마귀 수, "flying": 나는 까마귀 수} |

- 단지 사이 거리: 옆벽 건물을 길 양쪽에 차례로 두고 `ground.path`를 곧은 넓은 길로, `ruts`로 바퀴 자국(예제 `example_spec_panelka_street.json`)
- 인물 배치: 전신이 화면에 들어가는 기준은 1200x1600에서 눈 높이 0.38-0.40과 `head_unit` 0.036, 1600x1200에서 0.40과 0.019. 세계관 설정샷처럼 멀리 작게 세울 때는 카메라 `focal` 0.45와 `head_unit` 0.0065
- 색: `sky`(`night_*`, `dusk_*`, `haze_*`), `ground`(`snow_*`, `grass_*`, `path`, `path_dirt`, `rut`, `stalk`, `stalk_light`), `block`(`wall`, `shade`, `day`, `glass`, `lit`, `lit_amber`, `tv`, `balcony`, `door`), `lamp`(`head`, `pool`, `glow`), `pole`(`base`, `wire`, `metal`, `crow`), `birch`(`bark`, `mark`, `twig`)
- 예제: `example_spec_scene_doomer_man.json`, `example_spec_scene_doomer_woman.json`, `example_spec_scene_doomer_pair.json`, `example_spec_scene_doomer_world.json`, `example_spec_panelka_street.json`

## cafe, room, bedroom, bathroom (실내)

서 있는 사람의 눈높이에서 본 실내. 방은 센티미터 단위 상자(X 오른쪽, Y 위, Z 안쪽)이고 카메라가 수평으로 바라보므로 안쪽으로 뻗는 선이 모두 지평선 위 한 소실점으로 모임. 네 피사체는 같은 모듈(`scripts/interior.py`)을 쓰고 기본 구성만 다름

| 피사체 | 기본 구성 |
|---|---|
| `cafe` | 거리가 보이는 창, 카운터와 에스프레소 머신, 원탁, 의자, 펜던트 조명, 메뉴판, 선반 |
| `room` | 거실. 커튼 창, 소파, 책장, 러그, 낮은 탁자, 스탠드, 화분 |
| `bedroom` | 침실(기본 밤). 머리판이 있는 침대(베개, 접어 내린 이불), 협탁 2개와 탁상 스탠드, 왼쪽 벽 커튼 창, 침대 위 액자, 러그, 화분 |
| `bathroom` | 욕실(기본 낮). 허리 높이까지 벽 타일, 바닥 타일, 욕조, 세면대와 거울, 벽등, 유리 샤워 칸, 수건걸이 |

| 키 | 기본 | 설명 |
|---|---|---|
| `camera.eye_height` | 150 | 카메라 높이(cm). 서 있는 성인의 눈높이 |
| `camera.horizon_y` | 0.46 | 지평선(소실점) 높이, 화면 높이 비율. 인물을 세울 때 `backdrop.place` "horizon"과 함께 조정 |
| `camera.focal` | 0.62 | 초점 거리(화면 폭 비율). 작을수록 넓게 보임 |
| `camera.center_x`, `camera.x` | 0.5, 0 | 소실점의 가로 위치, 카메라의 좌우 위치(cm) |
| `room.width`, `room.height`, `room.depth` | 640, 300, 600(카페), 620, 270, 600(방) | 방 크기(cm). 카메라는 앞쪽 가운데 |
| `room.floor` | "tiles"(카페, 욕실), "planks"(방, 침실) | 바닥: 체크 타일(`tile` 크기) 또는 마루(`plank` 폭) |
| `room.wall_tiles` | 없음(욕실은 {"height": 130, "size": 30}) | 세 벽을 바닥부터 `height`(cm)까지 `size` 크기 타일로 덮음 |
| `time` | "day" | "night"면 방이 어두워지고 창밖은 밤 풍경, 켠 조명이 방을 데움 |
| `weather` | 없음 | {"kind": "rain" 또는 "snow"}. 창밖에만 보임 |
| `items` | 피사체별 | 가구와 벽 장식 목록(아래 표) |

| `kind` | 위치 키 | 그 밖의 키 |
|---|---|---|
| `window` | `wall`("back", "left", "right"), `a0`, `a1`(뒷벽은 X 범위, 옆벽은 Z 범위), `y0`, `y1` | `panes` [열, 행], `view`("street" 건물, "trees" 나무), `curtains`, `frame`(창틀 두께 cm) |
| `frame` | 창과 같음 | 액자와 추상화 |
| `menu` | 창과 같음 | 분필 메뉴판 |
| `shelf` | `a0`, `a1` | `levels`(선반 높이 목록 cm). 병과 컵이 놓인 벽 선반 |
| `counter` | `a0`, `a1`, `z`(앞면) | `depth`, `height`, `machine`(에스프레소 머신), `cups` |
| `table` | `x`, `z` | `radius`, `height`(74 카페, 45 거실 탁자), `cups` |
| `chair` | `x`, `z` | `angle`(0은 등받이가 안쪽, 180은 등받이가 앞쪽) |
| `stool` | `x`, `z` | `height`, `radius` |
| `sofa` | `x`, `z`(앞면) | `width`, `depth`, `angle` |
| `bookshelf` | `x`, `z`(앞면) | `width`, `height`, `depth`, `shelves` |
| `rug` | `x`, `z`(앞 가장자리) | `width`, `depth` |
| `plant` | `x`, `z` | `radius`, `height`, `leaves` |
| `floor_lamp` | `x`, `z` | `height`, `on`(기본은 밤에만 켬) |
| `pendant` | `x`, `z` | `drop`(천장에서 내려온 길이), `radius`, `on` |
| `bed` | `x`, `z`(발치) | `width`(160), `length`(205), `headboard`(머리판 높이 115), `duvet_share`(이불이 덮는 길이 비율 0.70). 뒷벽에 머리판을 붙임 |
| `nightstand` | `x`, `z`(앞면) | `width`, `depth`, `height`(55). 서랍 하나 |
| `table_lamp` | `x`, `z`, `y`(놓인 높이) | `on`(기본은 밤에만 켬) |
| `bathtub` | `x`, `z`(앞면) | `width`(170), `depth`(75), `height`(55). 테두리 안 욕조와 수전 |
| `vanity` | `x`, `z`(앞면) | `width`, `depth`, `height`(82). 문 두 짝 수납장, 상판, 세면볼, 수전 |
| `shower` | `a0`, `a1`(X 범위), `z`(유리면) | `height`(200). 뒷벽 샤워기와 앞의 유리 칸막이 |
| `mirror` | 창과 같음 | 얇은 금속 테두리와 비친 빛 줄기 |
| `sconce` | `wall`, `a`, `y` | `on`(기본 켬). 벽등 |
| `towel` | 창과 같음 | 걸이에 걸린 수건(띠 무늬) |

- 바닥 위 사물은 먼 것부터 그려 앞뒤가 저절로 맞음. 러그는 항상 맨 아래
- 인물이 설 자리(카메라 앞 2m 안쪽)는 비워 두는 편이 좋음. 기본 구성의 사물은 Z 220 이후에 있음
- 색: `room_wall`(`base` 뒷벽, `shadow`, `ceiling`, `line`), `room_floor`(`base`, `shadow`, `alt` 타일, `line`, `cast` 그림자), `room_trim`(창틀, 걸레받이), `outside`(창밖 낮과 밤 색, `sun` 바닥의 햇빛), `desk`(나무 상판), `counter`, `chair`, `sofa`, `shelf_wood`, `books`, `rug`(`border`, `motif`), `curtain`, `board`(`chalk`), `art`, `jars`, `lamp`(`bulb` 전구 빛), `shade`, `mug`, `device`, `leaf`, `pot`
    + 침실: `bed_wood`(침대 틀, 협탁), `headboard`, `sheet`, `duvet`, `pillow`
    + 욕실: `room_tile`, `porcelain`(욕조, 세면대), `vanity`, `metal`(수전, 테두리), `mirror`(`top`, `bottom`, `gleam`), `glass`(`opacity`), `towel`(`stripe`)
- 카메라를 옆으로 옮기면(`camera.x`) 가운데 선 인물 뒤의 침대가 옆으로 드러남(포옹 예제는 -110)
- 예제: `example_spec_cafe_night_rain.json`, `example_spec_room_snow.json`, `example_spec_bedroom_day.json`, `example_spec_bathroom_night.json`, `example_spec_scene_cafe.json`, `example_spec_scene_room_night.json`, `example_spec_scene_embrace.json`(침실), `example_spec_scene_embrace_bath.json`(욕실)

## weather (날씨)

설정 최상위의 `weather`. 피사체 어디에나 넣을 수 있음

| 키 | 기본 | 설명 |
|---|---|---|
| `kind` | | "rain"(회색빛, 옅은 안개, 비스듬한 빗줄기), "snow"(밝은 안개, 먼 곳은 작고 또렷하고 가까운 곳은 크고 흐린 눈송이), "petals"(날리는 벚꽃잎. 여러 각도로 돈 분홍 타원, 먼 곳은 작고 또렷하고 가까운 곳은 크고 흐림) |
| `amount` | 1.0 | 빗줄기, 눈송이 양과 색조 변화의 강도 |
| `wind` | 12 | 빗줄기 기울기(도) |

- 야외 피사체(도시, 풍경 등)와 그 위에 세운 인물은 그림 전체에 적용. 인물 앞으로도 비나 눈이 내림
- 실내(카페, 방)와 실내를 배경으로 한 인물은 창 유리 안에만 적용
- 우산을 든 인물이 있으면 우산과 그 아래에는 빗줄기와 눈송이가 내리지 않음
- 예제: `example_spec_city_rain.json`, `example_spec_landscape_snow.json`, `example_spec_cafe_night_rain.json`, `example_spec_room_snow.json`, `example_spec_scene_friends_photo.json`(꽃잎)
