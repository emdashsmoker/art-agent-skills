# 설정 매개변수

초상(`portrait`)과 전신 인물(`figure`)의 얼굴, 머리카락, 팔레트 설정. 설정 JSON에는 기본값과 다른 항목만 적는다. 병합 순서는 `assets/spec_default.json`, 화풍 파일의 `figure`, 피사체 파일, 성별 프리셋(`assets/sex_<성별>.json`), 사용자 설정 순서

## 목차

- 좌표 단위
- canvas, seed, light
- sex (성별)
- pose
- face
- eyes
- nose, mouth
- body, outfit
- hair
- expression (표정)
- look (개성)
- accessories (소품)
- style (팔레트, 무늬, 표현 강도)

## 좌표 단위

- 길이 단위는 머리 단위(1.0 = 얼굴 반폭)
- 원점은 두 눈의 중간, x는 화면 오른쪽, y는 아래쪽
- 화풍별 비례는 화풍 파일이 이미 덮어쓰므로 사용자 설정은 개성만 조정

| 기준 | anime | illust | paint |
|---|---|---|---|
| 턱끝 높이 `chin_y` | 1.22 | 1.26 | 1.30 |
| 눈 반폭 `half_width` | 0.255 | 0.245 | 0.222 |
| 코끝 높이 `tip_y` | 0.55 | 0.58 | 0.63 |
| 입 높이 `mouth.y` | 0.84 | 0.88 | 0.93 |

- 수채화와 연필은 `illust`, 흑백 만화와 픽셀 아트는 `anime`의 비례를 그대로 따름

## canvas, seed, light

| 키 | 기본 | 설명 |
|---|---|---|
| `canvas.width`, `canvas.height` | 1200, 1600 | 출력 픽셀 크기, 3:4 비율 권장 |
| `seed` | 7 | 머리카락 결, 질감, 붓질의 난수. 같은 값은 같은 그림 |
| `light` | [-0.55, -0.55, 0.63] | 광원을 향하는 벡터 (x, y, z). x 음수는 왼쪽, y 음수는 위, z는 정면 |

## sex (성별)

| 키 | 기본 | 설명 |
|---|---|---|
| `sex` | "female" | "male"이면 `assets/sex_male.json` 프리셋을 사용자 설정 앞에 병합 |

- 남성 프리셋 내용
    + 얼굴: 긴 얼굴(`chin_y` 1.34), 넓은 각진 턱(`jaw_width` 0.90, `chin_width` 0.24), 귀(`face.ears`)
    + 눈: 작은 눈, 낮고 굵은 일자 눈썹, 속눈썹 날개 없음
    + 목과 어깨: 굵은 목, 울대뼈(`body.adams_apple`), 넓은 어깨
    + 머리: 짧은 머리(`hair.style` "short"), 옆으로 넘긴 짧은 앞머리
    + 의상: 라운드넥 티셔츠(`outfit.cut` "crew"), 목걸이 없음
    + 화풍별 피부, 머리, 옷 색과 수염 자국(`face_render.stubble`)
    + 전신(`subject_figure`): 티셔츠, 긴바지, 구두. 원피스 해제
- 프리셋 값은 사용자 설정으로 덮어쓸 수 있음
    + 예: 남성의 긴 머리는 `hair.style` "long"과 `hair.length` 지정

## pose

| 키 | 기본 | 범위 | 설명 |
|---|---|---|---|
| `head_center` | [0.515, 0.375] | 0-1 | 눈 중간점의 화면 위치(가로, 세로 비율) |
| `head_unit` | 0.19 | 0.15-0.24 | 머리 단위의 크기(화면 폭 대비). 키우면 클로즈업 |
| `yaw_deg` | 12 | 0-18 | 고개 돌림. 18 초과는 윤곽 왜곡 발생. 3/4 전신의 작은 머리는 22까지 허용 |
| `roll_deg` | -4 | -8-8 | 고개 기울임 |
| `shoulder_roll_deg` | 2 | -5-5 | 어깨 기울임 |
| `mirror` | false | | 완성 그림의 좌우 반전. 반대 방향을 보게 할 때 사용 |
| `horizon_drop` | 0 | 0-0.1 | 장면 "horizon" 배치에서 이 인물의 눈만 내림(화면 높이 비율) |

## face

| 키 | 기본 | 범위 | 설명 |
|---|---|---|---|
| `chin_y` | 1.22 | 1.10-1.40 | 눈에서 턱끝까지. 클수록 성숙한 인상 |
| `cheek_width` | 0.95 | 0.90-1.00 | 광대 폭 |
| `jaw_width` | 0.73 | 0.68-0.85 | 턱 모서리 폭. 작을수록 V라인 |
| `jaw_height` | 0.62 | 0.55-0.70 | 턱 모서리 높이(`chin_y` 대비) |
| `chin_width` | 0.11 | 0.09-0.18 | 턱끝 폭. 작을수록 뾰족 |
| `jaw_sharpness` | 0.85 | 0-1 | 턱 모서리에서 턱끝까지의 직선 정도. 1은 직선, 0은 둥근 볼살 |
| `ears` | false | | 귀 그리기. 짧은 머리에서 사용 |

## eyes

| 키 | 기본 | 범위 | 설명 |
|---|---|---|---|
| `center_x` | 0.47 | 0.42-0.50 | 눈 중심의 가로 위치 |
| `half_width` | 0.255 | 0.20-0.28 | 눈 반폭 |
| `open_up`, `open_down` | 0.15, 0.10 | 0.09-0.20, 0.06-0.13 | 눈 중심에서 위, 아래 눈꺼풀까지 |
| `tilt` | 0.10 | 0-0.15 | 눈꼬리 올림 |
| `lash_thickness` | 0.06 | 0.03-0.07 | 윗 속눈썹 두께 |
| `wing_length`, `wing_lift` | 0.16, 0.30 | | 눈꼬리 선의 길이와 들림 |
| `crease_gap` | 0.07 | | 쌍꺼풀 선과 눈꺼풀의 간격 |
| `brow_gap` | 0.37 | 0.27-0.42 | 눈과 눈썹의 간격 |
| `brow_slant` | 0.75 | 0.3-1.0 | 눈썹이 눈꼬리 기울기를 따르는 비율. 높으면 단호, 낮으면 온화 |
| `gaze_x`, `gaze_y` | -0.03, -0.035 | -0.06-0.06 | 시선 방향 |
| `iris_rx`, `iris_ry` | 0.145, 0.152 | | 홍채 반지름. `open_up + open_down`의 약 0.6배가 자연스러움 |
| `pupil_ratio` | 0.48 | 0.4-0.55 | 동공 크기(홍채 대비) |

## nose, mouth

| 키 | 기본 | 설명 |
|---|---|---|
| `nose.tip_y` | 0.55 | 코끝 높이 |
| `nose.width` | 0.11 | 콧볼 반폭 |
| `nose.protrusion` | 0.26 | 코 돌출. 고개를 돌렸을 때 코가 옆으로 이동하는 양 |
| `mouth.y` | 0.84 | 입 높이 |
| `mouth.half_width` | 0.215 | 입 반폭 |
| `mouth.lip_height` | 0.045 | 입술 두께 |
| `mouth.smile` | 0.012 | 입꼬리 올림. 0.03 이상은 미소, 음수는 내린 입꼬리 |
| `mouth.open` | 0 | 입 벌림(0-0.2). 벌리면 입안, 혀, 윗니가 보임 |

## body, outfit

| 키 | 기본 | 설명 |
|---|---|---|
| `body.neck_half_width` | 0.42 | 목 반폭 |
| `body.neck_pit_y` | 2.02 | 쇄골 사이 오목한 지점의 높이. `chin_y`와의 차이가 목 길이 |
| `body.shoulder_half_width` | 1.75 | 어깨 반폭 |
| `body.shoulder_y` | 2.24 | 어깨점 높이 |
| `body.adams_apple` | false | 울대뼈와 목빗근 선 |
| `outfit.cut` | "boat" | "boat"(어깨가 드러나는 넓은 목선 니트), "crew"(목을 두르는 라운드넥, 어깨까지 덮음) |
| `outfit.necklace` | true | false면 목걸이 생략 |
| `outfit.neckline_half_width` | 1.36 | 목선이 어깨에 걸치는 폭 |
| `outfit.neckline_dip_y` | 2.62 | 목선 가장 낮은 지점 |
| `outfit.ease` | 0.06 | 옷의 여유 폭 |
| `outfit.band_width` | 0.13 | 목선 골지 띠 두께 |
| `outfit.rib_spacing` | 0.085 | 니트 세로 골 간격 |

## hair

| 키 | 기본 | 범위 | 설명 |
|---|---|---|---|
| `style` | "long" | | "long"(긴 머리), "short"(귀 위와 목덜미에서 끝나는 짧은 머리), "ponytail"(뒤로 묶어 늘어뜨린 머리, `length`가 꼬리 길이), "bun"(정수리 뒤 올림머리). 묶은 머리는 귀가 드러나고 모든 시점(정면, 뒷모습, 측면)에서 그려짐 |
| `part_x` | 0.32 | 0.1-0.45 | 가르마 위치 |
| `length` | 3.4 | 1.3-4.0 | 머리끝 높이. 1.5는 단발, 2.3은 어깨선, 3.4는 가슴선 |
| `volume` | 0.14 | 0.10-0.22 | 두상 위 부피 |
| `tip_locks` | 3 | 2-5 | 머리끝 갈래 수 |
| `tip_split` | 0.93 | 0.85-0.95 | 갈래가 갈라지기 시작하는 위치(머리 길이 비율). 작을수록 갈래가 깊음 |
| `band_y` | -0.80 | | 광택 띠의 높이 |
| `wave`, `waves` | 0.025, 1.4 | 0-0.08, 1-3 | 웨이브의 폭과 횟수 |
| `bangs.near`, `bangs.far` | 4, 2 | 0-6, 0-3 | 가르마 양쪽 앞머리 갈래 수. 0은 이마를 드러냄 |
| `bangs.length` | 0.72 | 0.5-0.85 | 앞머리 길이. 0.85는 눈에 닿음 |
| `bangs.width` | 0.14 | 0.08-0.18 | 갈래 굵기 |
| `bangs.seed` | 3 | | 갈래 길이와 굵기의 변주 |

## expression (표정)

| 이름 | 표정 | 바뀌는 설정 |
|---|---|---|
| `smile` | 미소 | 입꼬리 올림, 아래 눈꺼풀이 올라와 눈이 살짝 휨, 홍조 |
| `laugh` | 활짝 웃음 | 벌린 입과 윗니, 휘어 감긴 눈, 올라간 눈썹, 짙은 홍조 |
| `sad` | 슬픔 | 내린 입꼬리, 안쪽이 올라간 눈썹, 아래로 향한 시선 |
| `cry` | 눈물 | 슬픔에 살짝 벌린 입, 붉은 볼, 눈물 줄기 |
| `surprise` | 놀람 | 크게 뜬 눈, 작아진 동공, 올라간 눈썹, 동그랗게 벌린 입 |
| `angry` | 화남 | 안쪽이 내려온 눈썹, 가늘게 뜬 눈, 내린 입꼬리 |
| `wink` | 윙크 | 가까운 쪽 눈을 감은 호, 미소 |
| `kiss` | 입맞춤 | 두 눈을 감은 호, 옅은 미소, 진한 볼 홍조 |

- 형식: `"expression": "smile"` 또는 `{"name": "laugh", "amount": 0.6}`(`amount` 0-1은 중간 강도)
- 표정은 현재 얼굴 설정을 밀어내는 연산이라 화풍별 비례가 유지됨
- 사용자 설정에 직접 적은 값(예: `mouth.smile`)은 표정이 덮어쓰지 않음
- 측면 인물은 입꼬리 방향, 벌린 입, 감은 눈, 눈물을 반영
- 표정을 이루는 개별 설정
    + `eyes.closed`(0-1, 1은 감은 눈), `eyes.arch`(눈꺼풀이 위로 휘는 정도, 웃는 눈), `eyes.brow_inner`(눈썹 안쪽 올림, 음수는 찌푸림), `eyes.brow_raise`(눈썹 전체 올림), `mouth.open`
    + 한쪽 눈만 바꿀 때는 `eyes.near`, `eyes.far` 아래에 같은 키를 적음(윙크는 `eyes.near.closed` 1.0)
- 새 표정은 `assets/expressions.json`에 연산을 추가(`references/extending.md`)

## look (개성)

`look` 키 하나로 인물의 생김새를 바꿈. 각 항목은 선택

| 키 | 값 | 설명 |
|---|---|---|
| `face_shape` | `oval`(기본), `round`, `long`, `square`, `heart` | 얼굴형. 둥근 볼, 긴 얼굴, 각진 턱, 갸름한 턱의 하트형 |
| `eye_shape` | `almond`(기본), `big`, `narrow`, `droopy`, `cat` | 눈매. 큰 눈, 가는 눈, 처진 눈, 올라간 고양이 눈 |
| `hair_style` | `long`, `short`, `bob`, `ponytail`, `bun`, `curly` | 머리 모양. `bob`은 단발, `curly`는 부피 있는 곱슬 |
| `hair_color` | `black`, `dark_brown`, `brown`, `blonde`, `red`, `silver` | 머리색 팔레트 5색을 한꺼번에 교체 |
| `eye_color` | `dark_brown`, `brown`, `hazel`, `green`, `blue`, `gray` | 홍채 3색 교체 |
| `skin_tone` | `fair`, `light`(기준), `medium`, `tan`, `deep`, `dark` | 피부색. 화풍별 피부 팔레트를 기준색 대비 비율로 옮겨 화풍의 색감을 유지 |
| `freckles` | 0-1 | 코와 볼 위 주근깨의 양 |
| `moles` | [[x, y], ...] | 점의 위치(머리 단위, 눈 중간 원점). 예: [[0.35, 0.55]]는 화면 오른쪽 볼, 코끝 높이 |
| `identity` | 정수 또는 {"seed", "amount"} | 인물 시드. 턱, 눈, 코, 입, 가르마를 정해진 범위 안에서 조금씩 흔들어 같은 화풍 안에서도 다른 사람으로 만듦 |

- 프리셋은 현재 값을 밀어내는 연산이고 사용자 설정에 직접 적은 값이 우선
- 같은 `identity`는 같은 얼굴을 재현. 여러 인물 장면에서 동반 인물마다 다른 값을 주면 얼굴이 겹치지 않음
- 프리셋 목록과 범위는 `assets/looks.json`

```json
{"look": {"face_shape": "round", "eye_shape": "big", "hair_style": "ponytail", "hair_color": "brown",
          "skin_tone": "tan", "freckles": 0.6, "identity": 12}, "expression": "smile"}
```

## accessories (소품)

설정 최상위의 `accessories`. 초상과 전신(정면, 뒷모습, 측면) 모두에서 그려짐. `true`는 기본값

| 키 | 하위 키 | 설명 |
|---|---|---|
| `glasses` | `shape`("round", "square"), `color`(테 색), `lens`(유리 반사 농도, 0.10) | 안경. 머리 방향을 따라 돌고, 다리는 머리카락 아래로 들어감. 뒷모습에서는 생략 |
| `hat` | `kind`("beanie", "cap", "wide"), `pompom`(비니 방울), `group`(팔레트, 기본 `hat`) | 모자. 비니, 야구 모자(뒷모습은 조절 끈 틈), 챙 넓은 모자(리본 띠). 챙의 그림자가 얼굴에 지고, 모자 밖으로 삐져나온 윗머리는 눌린 것으로 보고 지움 |
| `scarf` | `side`("left", "right"), `length`(늘어진 끝 길이, 기본 2.6), `group`(기본 `scarf`) | 목도리. 목을 두 번 감은 두 겹과 늘어진 두 끝(술 장식). 뒷모습은 감은 부분만 |
| `bag` | `side`("left", "right"), `group`(기본 `bag`) | 크로스백. 반대쪽 어깨에서 대각선 끈, 엉덩이 옆 가방(덮개와 잠금쇠). 초상은 끈만, 측면은 가까운 쪽 엉덩이 |
| `cigarette` | `side`("right", "left"), `lit`(기본 true), `smoke`(연기 높이 배율, 1.0) | 입꼬리에 문 담배. 관객 쪽 아래로 기울고 불붙은 끝에서 연기가 올라감. 정면 초상과 정면 전신만 |

- `side`는 정면 기준 화면 쪽. 뒷모습은 같은 사람 기준이라 화면에서 반대쪽에 보임
- 색: `style.palette`의 `hat`(`band` 리본 포함), `scarf`, `bag`(기본값은 `assets/accessories.json`). 안경은 `color`
- 가방과 목도리는 팔 아래, 옷 위에 그려짐
- 담배 색은 `style.palette.cigarette`(`paper`, `filter`, `ash`, `ember`, `smoke`)로 덮어씀(`scripts/smoking.py`의 `COLORS`가 기본)

## style

사용자 설정의 `style` 키는 화풍 파일을 덮어쓴다

### 팔레트

| 그룹 | 키 | 설명 |
|---|---|---|
| `skin` | `base`, `shadow`, `deep`, `light`, `blush` | 피부 기본, 그림자, 짙은 그림자, 하이라이트, 홍조 |
| `hair` | `base`, `shadow`, `light`, `line`, `deep` | 머리 기본, 그림자, 광택, 선, 가장 어두운 결. 눈썹과 속눈썹도 이 색을 사용 |
| `eye` | `white`, `white_shadow`, `iris`, `iris_dark`, `iris_light`, `pupil`, `catchlight` | 흰자, 흰자 그늘, 홍채 3단, 동공, 반사광 |
| `lip` | `upper`, `lower`, `shine`, `line` | 윗입술, 아랫입술, 윤기, 입술 사이 선 |
| `cloth` | `base`, `shadow`, `line` | 의상 |
| `line` | `main` | 피부 윤곽선 |
| `accent` | `metal`, `shine` | 목걸이 |
| `background` | `top`, `bottom`, `disc`, `disc_x`, `disc_y`, `disc_r`, `disc_blur`, `disc_opacity`, `mottle`, `bokeh`, `bokeh_color` | 상하 그라데이션, 원형 요소, 얼룩, 빛망울 |

### 무늬 (pattern)

옷 색 묶음 어디에나 `pattern`을 넣으면 그 옷에 무늬가 입혀짐. 무늬는 이미 칠한 명암을 따라 주름에서 어두워짐

| 키 | 기본 | 설명 |
|---|---|---|
| `kind` | | "stripes"(줄무늬), "check"(체크), "dots"(물방울) |
| `color` | | 무늬 색 |
| `scale` | 0.35 | 무늬 반복 간격(머리 단위) |
| `angle` | 0 | 각도(도). 줄무늬 0은 세로, 90은 가로 |
| `width` | 0.35 | 반복 간격 중 무늬가 차지하는 비율(물방울은 지름 비율) |
| `opacity` | 0.9 | 무늬 농도 |

- 적용 묶음: 초상 니트와 전신 원피스, 셔츠 `cloth`, `skirt`, `pants`, `jacket`, `jeogori`, `chima`, `baji`, `drape`, `hoodie`, `swim`, 소품 `hat`, `scarf`, `bag`
- 예: `"style": {"palette": {"skirt": {"pattern": {"kind": "check", "color": "#7A2430", "scale": 0.55, "width": 0.3}}}}`

- 그림자 색은 명도와 색상을 함께 옮김
    + 피부 그림자는 붉은 쪽, 흰 옷 그림자는 푸른 쪽으로 옮기면 탁해지지 않음
- 머리색과 배경색은 명도 차이를 크게 둠
    + 실루엣이 그림의 첫인상을 결정

### 표현 강도

| 키 | 설명 |
|---|---|
| `shading` | `cel`, `soft`, `grain` 중 1개 |
| `line_scale` | 선 굵기 배율. 0은 선화 생략 |
| `soft_blur` | `soft`, `grain`의 명암 번짐 폭 |
| `grain_spread` | `grain`의 입자 전이 폭 |
| `hair_render` | 머리 그림자 조각 수, 광택 띠, 결 질감, 잔머리 수 |
| `face_render` | 얼굴 명암 기준, 홍조, 코 표현, 입술 농도, `stubble`(수염 자국 농도, 0은 생략) |
| `body_render` | 턱 아래 그림자 길이, 니트 골 농도. 전신은 `references/subjects.md`의 표현 강도 표 참조 |
| `eye_render` | 눈꺼풀 그늘, 홍채 테두리, 눈썹 굵기 |
| `finish` | 마감 단계 설정. 회화풍은 `layers`의 붓 반지름과 임계값으로 거칠기 조절, `glaze`(마지막 투명 덧칠 농도) |
| `base` | 바탕 화풍 이름. 그 화풍 설정 위에 이 파일을 덮어씀(수채화, 연필은 `illust`, 흑백 만화, 픽셀 아트는 `anime`) |

- 다른 매체 화풍의 `finish` 주요 값
    + 수채화: `flatten`(색 웅덩이 단계), `wobble`(가장자리 떨림 px), `edge_gain`, `wet_edge`(가장자리 진해짐), `density`, `bloom`(얼룩), `granulation`(입자), `speck`(지울 밝은 점 크기 px), `paper`, `paper_color`
    + 연필: `levels`(자동 계조 백분위), `gamma`(클수록 중간 톤이 밝음), `contrast`, `smudge`(문지른 바탕), `spacing`(해칭 간격 px), `angles`, `thresholds`(층마다 시작 어둡기), `hatch`, `line_gain`, `paper_color`, `lead_color`
    + 흑백 만화: `black`, `white`(먹과 종이 경계 밝기), `cell`(망점 간격 px), `angle`, `line_gain`, `paper_color`, `ink_color`
    + 픽셀 아트: `cells`(가로 칸 수), `colors`(색 수), `dither`(바이어 디더링 세기), `edge`(외곽선 칸이 되는 밝기 차), `outline`(외곽선 칸 밝기 배율)

- 회화풍 붓질을 거칠게: `finish.layers`에서 반지름 3과 1.6 층을 삭제
- 회화풍 붓질을 곱게: 각 층의 `threshold`를 낮춤
