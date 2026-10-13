# 인물 spec 참조

`scripts/render.py`와 `paintkit.scene`이 받는 spec의 전체 키. 전신 전용 키는 `figure-spec.md`, 장면 연산은 `scenery.md` 참조. 길이 단위는 "머리 단위"(정수리에서 턱까지 = 1.0)이며 위치는 캔버스 비율(0-1)로 적음.

## 목차

- 최상위 키
- character
- palette
- placement
- light
- background와 foreground
- ambient
- style_overrides
- finish

## 최상위 키

| 키 | 기본값 | 설명 |
|---|---|---|
| `canvas` | [1200, 1500] | [가로, 세로] 픽셀 |
| `style` | "anime" | `anime`, `illust`, `painterly` |
| `seed` | 0 | 그레인과 붓 터치 난수 |
| `subject` | 자동 | `portrait` 흉상, `figure` 전신, `none` 장면만. `figure` 키가 있으면 전신 |
| `figure` | 없음 | 전신 포즈와 의상 (`figure-spec.md`) |
| `character` | {} | 인물 성별, 형태, 포즈 |
| `palette` | {} | 색 17개 |
| `placement` | {} | 인물 크기와 위치 |
| `light` | {} | 광원 방향 |
| `background` | 연한 그라데이션 | 배경 연산 목록, 순서대로 겹침 |
| `extras` | 없음 | 배경 속 다른 인물 목록, 전신 리그로 그림 (`figure-spec.md`) |
| `duo` | 없음 | 주인공과 함께 그릴 상대 인물과 두 사람의 관계, 전신 전용 (`figure-spec.md`의 투샷 절) |
| `foreground` | 없음 | 인물 앞에 그릴 연산 목록 (꽃잎 등) |
| `ambient` | 없음 | 인물 하반부에 얹는 장면 색 |
| `style_overrides` | {} | 화풍 렌더 설정 덮어쓰기 |
| `finish` | {} | 후보정 설정 덮어쓰기 |

## character

| 키 | 기본값 | 권장 범위 | 효과 |
|---|---|---|---|
| `gender` | "female" | 2종 | `female`, `male`. 얼굴, 머리, 목과 어깨, 전신 체형, 손이 바뀜 |
| `jaw_sharpness` | 0.8 | 0-1 | 0 둥근 달걀형, 1 날카로운 V라인 |
| `face_width` | 1.0 | 0.9-1.1 | 얼굴 가로 배율 |
| `chin_length` | 1.0 | 0.9-1.15 | 입 아래 길이 배율 |
| `eye_width` | 0.190 | 0.16-0.21 | 눈 가로 |
| `eye_height` | 0.098 | 0.07-0.11 | 눈 세로, 작을수록 성숙한 인상 |
| `eye_spacing` | 0.172 | 0.16-0.185 | 중심선에서 눈 중심까지 거리 |
| `eye_tilt` | 0.012 | -0.01-0.025 | 양수는 눈꼬리 상승 |
| `iris_scale` | 1.0 | 0.85-1.15 | 홍채 크기 배율 |
| `gaze` | [0, 0] | 각 -1-1 | 눈동자 이동, x 양수는 화면 오른쪽 |
| `eyelid_open` | 1.0 | 0.55-1.0 | 눈 뜬 정도 |
| `brow_angle` | 0.006 | -0.012-0.015 | 양수는 눈썹 꼬리 상승 |
| `mouth_width` | 0.115 | 0.09-0.14 | 입 가로 |
| `smile` | 0.35 | -1-1 | 입꼬리 높이 |
| `lip_fullness` | 1.0 | 0.7-1.4 | 입술 두께 |
| `head_tilt` | -4.0 | -10-10 | 고개 기울임(도), 양수는 시계 방향 |
| `head_turn` | 0.0 | -2.5-2.5 | 얼굴 회전, 양수는 화면 오른쪽. 1이 약 14도, 2.5가 약 35도(반측면). 범위 밖 값은 2.5로 잘림 |
| `hair_style` | "long_straight" | 12종 | `long_straight`, `long_wavy`, `bob`, `short` 짧은 커트, `medium` 귀를 덮는 중간 길이, `slicked` 넘긴 짧은 머리, `layered` 정수리 볼륨과 뾰족한 결의 남성 레이어드 커트, `long_curly` 곱슬 롱(덩어리진 실루엣과 컬 질감), `layered_bob` 턱선 레이어드 단발, `two_block` 윗머리를 남기고 옆과 뒤를 짧게 친 투블럭, `perm` 볼륨과 잔 컬의 짧은 펌, `pixie` 귀가 드러나는 픽시컷 |
| `bangs` | "side_swept" | 6종 | `side_swept` 사선 앞머리, `see_through` 가는 시스루, `parted` 가르마 커튼뱅, `short_fringe` 이마 위 짧은 앞머리, `swept_back` 앞머리 없이 넘김, `layered` 한 방향으로 쓸린 날카로운 앞머리(눈썹을 스침) |
| `parting` | -0.10 | -0.15-0.15 | 가르마 x 위치 |
| `hair_seed` | 7 | 정수 | 머리카락 변형 난수 |
| `outfit` | "vneck" | 7종 | `vneck`, `turtleneck`, `blazer`, `offshoulder`, `crewneck` 라운드 니트, `shirt` 칼라 셔츠, `suit` 정장과 넥타이 |
| `skin_tone` | "default" | 7종 | `default` 성별 기본색, `fair`, `light`, `medium`, `tan`, `brown`, `deep` (밝은 톤에서 짙은 톤 순). `skin`, `skin_shadow`, `blush`, `lip`이 함께 바뀌고 `palette`에 적은 색이 우선 |
| `eye_shape` | "default" | 6종 | `default` 성별 기본 눈, `round` 둥근 눈, `almond` 아몬드형, `upturned` 눈꼬리가 올라간 눈, `droopy` 눈꼬리가 처진 눈, `monolid` 쌍꺼풀 선 없는 홑꺼풀 |
| `brow_shape` | "default" | 4종 | `default`, `straight` 일자, `arched` 아치형, `thick` 짙은 눈썹 |
| `nose_shape` | "default" | 3종 | `default`, `dot` 점 하나로 표현한 작은 코, `bridge` 콧날 선과 콧볼이 보이는 코 |
| `mouth_shape` | "default" | 3종 | `default`, `small` 작은 입, `heart` 윗입술 산이 뚜렷한 도톰한 입술 |
| `hat` | "none" | 2종 | `none`, `beanie` 니트 비니. 흉상과 전신의 정면, 반측면, 옆모습, 뒷모습 모두 지원. 비니 위로 솟은 머리카락은 지워지고 챙 아래 앞머리와 옆머리는 남음 |

### 반측면 (head_turn 1 초과)

- 14도를 넘는 회전에는 반측면 보정이 단계적으로 들어감 (14도 이하 결과는 그대로)
    + 가까운 쪽 : 머리 실루엣이 유지되고 뒤통수와 목덜미 머리가 드러남, 가까운 귀가 얼굴 위에 그려짐
    + 가까운 볼 : 볼 윤곽이 얼굴과 함께 절반쯤 안으로 돌아서 볼이 넓고 평평해지지 않음
    + 먼 쪽 : 광대에서 턱끝까지 둥근 볼 곡선을 다시 그림. 먼 쪽 눈꼬리, 코끝, 입꼬리 바깥에 볼 여백이 남아 코가 윤곽을 뚫지 않음
    + 볼 곡선의 둥근 정도 : `jaw_sharpness`가 낮을수록, 남성일수록 둥글어짐
    + 옆머리 : 가까운 쪽 옆머리는 귀 위를 덮은 채 얼굴 쪽으로 조금만 이동, 먼 쪽 긴 앞머리와 옆머리는 얼굴 뒤로 감
- 시선은 고개를 돌린 반대쪽 `gaze`(약 0.4-0.55)를 주면 관객을 바라봄
- 반측면 흉상 예 : `illust_three_quarter.json`

### 남성 기본값

`gender`가 `male`이면 spec에 적지 않은 키에 아래 값이 들어감. 적은 키는 그대로 유지됨.

| 키 | 남성 기본값 |
|---|---|
| 얼굴 | `jaw_sharpness` 0.85, `face_width` 0.95, `chin_length` 1.05, `head_tilt` -2 |
| 눈 | `eye_width` 0.182, `eye_height` 0.062, `eye_tilt` 0.014, `iris_scale` 0.80, `eyelid_open` 0.92 |
| 눈썹과 입 | `brow_angle` 0, `mouth_width` 0.125, `smile` 0.10, `lip_fullness` 0.45 |
| 머리와 의상 | `hair_style` "layered", `bangs` "layered", `parting` -0.06, `outfit` "shirt" |
| 색 | `skin` "#f6dccb", `skin_shadow` "#dca592", `blush` "#e9a497", `lip` "#c98d84" |

- 남성 얼굴은 각진 턱선과 광대 아래 음영, 눈썹뼈와 콧대 하이라이트로 입체를 만듦
- 남성 눈은 가늘고 긴 아몬드형이며 두꺼운 윗꺼풀선이 눈꼬리 밖까지 이어짐, 눈썹은 낮고 굵음
- 남성 목은 흉쇄유돌근 선과 옅은 후골로 표현, 홍조와 입술색은 옅음
- 귀는 `short`, `slicked`, `medium`, `layered`, `two_block`, `perm`, `pixie` 머리에서 보임
- 여성도 `short`, `slicked`, `layered` 머리와 `shirt`, `suit` 의상을 쓸 수 있음

## palette

| 키 | 용도 | 설계 요령 |
|---|---|---|
| `skin` | 피부 밑색 | 명도 높은 저채도 |
| `skin_shadow` | 피부 그림자 | 밑색보다 붉고 채도 높게 |
| `blush` | 볼, 눈가 홍조 | 분홍에서 산호색 |
| `lip` | 입술 | 홍조보다 진하게 |
| `hair` | 머리 밑색 | 주조색 후보 |
| `hair_shadow` | 머리 그림자 | 밑색 명도의 55-65% |
| `hair_light` | 머리 하이라이트 | 광원 색 쪽으로 이동한 밝은 색 |
| `iris` | 홍채 | 강조색 후보, 채도 높게 |
| `eye_white` | 흰자 | 회색이 약간 도는 흰색 |
| `line` | 선 기준색 | 짙은 갈색 또는 짙은 남색 |
| `cloth` | 주 의상 | |
| `cloth_shadow` | 주 의상 그림자 | 밝은 옷은 푸른 보라 쪽 |
| `cloth2` | 재킷(blazer, suit), 전신의 하의 | 그림자는 자동 산출 |
| `shoe` | 전신의 신발, 벨트 | |
| `accent` | 넥타이, 남성 속옷 밴드, 트레이닝 반바지 줄무늬 | 의상 색과 보색 관계면 시선이 모임 |
| `outer` | 전신의 재킷과 코트 (데님, 가죽, 롱코트) | 비우면 소재 색 |
| `hat` | 모자 (`character.hat`) | 기본 #2b2c33, 머리색과 명도 차이를 두면 경계가 읽힘 |

- `character.skin_tone` 프리셋은 `skin`, `skin_shadow`, `blush`, `lip` 4색을 한 번에 지정하며 여기 적은 색이 프리셋보다 우선

## placement

| 키 | 기본값 | 설명 |
|---|---|---|
| `head_height` | 0.413 | 머리 높이 / 캔버스 세로 |
| `eye_center` | [0.5, 0.36] | 두 눈 중점의 위치 (캔버스 비율), 흉상 전용 |
| `pelvis` | [0.5, 0.47] | 골반 중심의 위치, 전신 전용 (전신의 `head_height` 기본값은 0.115) |
| `shot` | 없음 | 전신 전용 구도 프리셋 `full`, `thigh`, `knee`, `waist`, `bust`. 크기와 위치를 자동 계산 |
| `x` | 0.5 | `shot`과 함께 쓰는 인물(투샷은 두 인물) 중심의 가로 위치 |

- `shot`은 `head_height`, `pelvis`와 함께 쓸 수 없고 흉상(`portrait`)에는 쓸 수 없음
- 프리셋별 자르는 위치는 `figure-spec.md`의 구도 절 참조

## light

| 키 | 기본값 | 설명 |
|---|---|---|
| `azimuth` | 135 | 광원 방향(도). 0 오른쪽, 90 위, 135 좌상단, 45 우상단 |
| `elevation` | 42 | 관객 쪽 기울기. 높을수록 정면광, 낮을수록 측면광 |

## background와 foreground

연산 객체의 목록. 위에서 아래 순서로 겹쳐 그림.

| type | 키 | 설명 |
|---|---|---|
| `gradient` | `top`, `bottom`, `angle`(90) | 2색 선형 그라데이션 |
| `glow` | `color`, `center`([0.5, 0.35]), `radius`(0.45, 세로 비율), `opacity`(0.6) | 부드러운 원형 빛 |
| `bokeh` | `colors`, `count`(26), `size`([30, 110]), `opacity`(0.35), `seed` | 아웃포커스 빛망울 |
| `wash` | `colors`, `scale`(0.32, 세로 비율), `seed` | 번지는 색면, 회화풍 배경용 |
| `light_shafts` | `color`, `count`(3), `angle`(62), `width`(0.10), `opacity`(0.3), `seed` | 사선 빛줄기 |
| `petals` | `color`, `count`(26), `size`([8, 26]), `seed` | 흩날리는 잎 모양 조각 |

- 하늘, 산, 물, 나무, 도시 거리, 실내, 두머 도시 연산(`sky`, `ridge`, `water`, `tree`, `street`, `room`, `panel_blocks`, `snow` 등 21종)은 `scenery.md` 참조

## ambient

| 키 | 기본값 | 설명 |
|---|---|---|
| `color` | 필수 | 배경 하단색 계열 권장 |
| `opacity` | 0.25 | 얹는 강도 |
| `from` | 0.55 | 시작 높이 (캔버스 세로 비율) |

## style_overrides

| 키 | anime | illust | painterly | 설명 |
|---|---|---|---|---|
| `shadow_softness` | 0.02 | 0.16 | 0.30 | 형태 음영 경계의 부드러움 |
| `cast_softness` | 0.0 | 0.012 | 0.02 | 투영 음영 흐림 |
| `shadow_strength` | 1.0 | 0.85 | 0.9 | 그림자 불투명도 |
| `face_shadow_level` | -0.10 | 0.05 | 0.18 | 클수록 얼굴 그림자 면적 확대 |
| `line_width` | 0.0045 | 0.003 | 0.0 | 외곽선 굵기, 0이면 선 없음 |
| `line_opacity` | 1.0 | 0.75 | 1.0 | 선 불투명도 |
| `line_variation` | 0.6 | 0.7 | 0.6 | 광원 쪽 선이 가늘어지는 정도 |
| `airbrush` | 0.5 | 1.0 | 1.0 | 홍조와 그라데이션 강도 |
| `hair_strands` | 1.0 | 1.3 | 0.6 | 머리카락 가닥선 밀도 |
| `hair_highlight` | "band" | "soft" | "soft" | `band` 톱니 띠, `soft` 흐린 띠, `none` |
| `eye_detail` | 1.0 | 1.0 | 0.8 | 홍채 결과 보조 하이라이트 |
| `rim_light` | 0.0 | 0.8 | 0.3 | 광원 쪽 가장자리 빛 |
| `lip_render` | "tint" | "full" | "full" | `tint` 옅은 색조, `full` 입술 형태 채색 |

## finish

| 키 | 설명 |
|---|---|
| `diffusion` | 확산 글로우 강도 (0-0.4) |
| `bloom` | 밝은 영역 번짐 강도 (0-0.5) |
| `contrast`, `saturation` | 1.0 기준 배율 |
| `shadow_tint`, `highlight_tint` | 어두운 영역과 밝은 영역에 입히는 색 |
| `tint_strength` | 색 입힘 강도 (0-0.25) |
| `vignette` | 주변부 어둡게 (0-0.4) |
| `grain` | 필름 그레인 (0-0.03) |
| `radii` | painterly 전용, 붓 반지름 목록 (큰 값에서 작은 값), 기본 [26, 13, 6, 3, 2] |
| `weave` | painterly 전용, 캔버스 결 강도 |
| `tilt` | 화면 기울기(도), 양수는 반시계 방향. 0이 기본, 3-8이 자연스러운 더치 앵글. 빈 모서리가 생기지 않도록 자동 확대 |
| `preset` | 이름 붙은 마감 묶음. 화풍 기본값 위에 얹히고 spec의 다른 `finish` 키가 프리셋보다 우선. 현재 `doomer` 1종 (`style-guide.md`의 두머 절) |
