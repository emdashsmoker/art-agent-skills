# 장면 빌더 참조

도시와 자연 풍경을 `background` 연산 목록으로 조립하는 방법. 모든 위치와 크기는 캔버스 비율(x는 가로, y와 크기는 세로 기준)이므로 해상도와 무관함.

## 목차

- 기본 규칙
- 하늘
- 땅과 자연
- 도시
- 도시 연산 (두머)
- 실내
- 인물과 원근 맞추기
- 조립 예시
- 화풍 마감

## 기본 규칙

- 먼 것부터 그림 : 하늘, 능선, 수면, 땅, 가까운 나무 순
- 깊이는 3가지로 표현 : 멀수록 작게, 옅게(대기), 채도 낮게
- 광원은 spec의 `light` 1개를 모든 연산이 공유
- 인물 없는 장면은 `"subject": "none"` 지정
- 같은 연산을 여러 번 써서 층을 쌓음 (능선 2-3겹, 나무 여러 그루)
- 모양이 마음에 들지 않으면 `seed`만 바꿔 재렌더

## 하늘

| type | 주요 키 (기본값) | 설명 |
|---|---|---|
| `sky` | `top`, `bottom`, `horizon`(0.6) | 수평선에서 `bottom` 색에 도달하는 그라데이션 |
| `sun` | `center`([0.3, 0.42]), `radius`(0.03), `color`, `glow_color`, `glow_radius`(0.35), `glow_opacity`(0.75) | 해 또는 달 |
| `stars` | `count`(240), `bottom`(0.6), `color`, `seed` | 별 |
| `clouds` | `color`, `shadow`, `coverage`(0.45), `top`(0.04), `bottom`(0.5), `scale`(0.30), `stretch`(2.4), `opacity`, `seed` | 윗면이 밝고 아랫면이 어두운 구름 띠 |

- 시간대는 하늘 2색으로 결정
    + 낮 : #6fa8dc 에서 #dbeaf7
    + 해 질 녘 : #3b3f7a 에서 #f4a57a
    + 밤 : #0b0f2a 에서 #2a2f66

## 땅과 자연

| type | 주요 키 (기본값) | 설명 |
|---|---|---|
| `ridge` | `base`(0.62), `height`(0.18), `color`, `shadow`, `haze`, `haze_strength`(0.45), `snow`, `snow_depth`(0.25), `period`(0.45), `roughness`(0.55), `seed` | 산 능선. `shadow`는 광원 반대쪽 사면, `haze`는 산기슭으로 번지는 대기색, `snow`는 설산 |
| `tree_line` | `base`(0.66), `height`(0.06), `color`, `haze`, `density`(70), `pointed`(true), `seed` | 먼 숲 띠 |
| `water` | `top`(0.62), `bottom`(1.0), `tint`, `tint_strength`(0.22), `ripple_color`, `ripples`(140), `seed` | 이미 그려진 위쪽 풍경을 비추는 수면 |
| `ground` | `top`(0.7), `color`, `far_color`, `roll`(0.03), `seed` | 완만한 땅 |
| `grass` | `top`(0.72), `bottom`(1.0), `colors`, `count`(1400), `length`(0.035), `seed` | 풀잎, 가까울수록 길게 |
| `flowers` | `top`(0.75), `bottom`(1.0), `colors`, `count`(260), `size`(0.006), `seed` | 들꽃 점 |
| `tree` | `base`([0.7, 0.9]), `height`(0.45), `foliage`, `foliage_shadow`, `trunk`, `rim`, `seed` | 활엽수 1그루 |
| `pine` | `base`([0.5, 0.9]), `height`(0.3), `color`, `shadow`, `seed` | 침엽수 1그루 |

- 능선은 뒤쪽일수록 밝고 푸르게, `haze`에는 하늘의 수평선 색을 사용
- `water`는 능선과 숲을 그린 뒤, 땅과 가까운 나무를 그리기 전에 배치
- 가까운 나무는 화면 가장자리에 두어 시선을 안쪽으로 모음

## 도시

| type | 주요 키 (기본값) | 설명 |
|---|---|---|
| `skyline` | `base`(0.62), `height`(0.2), `color`, `window_color`, `lit`(0.3), `seed` | 먼 빌딩 실루엣 |
| `street` | `horizon`(0.5), `vanish_x`(0.5), `time`("dusk"), `seed`, `wet`, `eye`(1.6), `cars`(0), `people`(0) | 1점 투시 거리 전체 |

- `street`는 한 번에 도로, 보도, 횡단보도, 양쪽 건물, 창문, 상점, 간판, 가로등을 그림
- `cars` : 도로 위 차량 수. 오른쪽 차로는 멀어지는 차(후미등), 왼쪽 차로는 다가오는 차(전조등)
    + 해 질 녘과 밤에는 등이 켜지고 젖은 노면에 비침
    + 3-6대가 적당하며 위치는 `seed`가 정함
- `people` : 보도 위 행인 수. 5-10명이 적당
    + 행인은 단순한 형태이며 먼 거리용 소품. 주인공은 전신 리그로 그림
    + 카메라가 눈높이(`eye` 1.6)면 모든 행인의 머리가 지평선에 걸림 (원근이 맞는다는 신호)
- 건물은 도로 쪽 면과 카메라 쪽 측면 모두에 창문이 그려짐
- 가까운 행인은 최상위 `extras`로 전신 리그를 써서 그림 (`figure-spec.md`의 배경 인물 절)
    + `"at": [x, z]` 미터 좌표로 놓으면 키와 원근에서 크기가 자동으로 맞음
    + 보도는 x 3.6-6.2 m (양쪽은 부호로 구분)
- `time` : `day`, `dusk`, `night`. 건물색, 창문 불빛, 가로등 점등이 함께 바뀜
- `wet` : 젖은 노면 반사 강도. 밤은 기본 0.35, 그 외 0
- `vanish_x` : 소실점의 가로 위치. 0.5에서 벗어나면 한쪽 건물이 크게 보임
- 하늘에 구름, 해, 별을 넣으려면 `sky`, `clouds`, `sun`, `stars`를 `street`보다 먼저 배치
    + `street`는 레이어가 비어 있을 때만 하늘을 직접 채움
- 밤과 해 질 녘은 `finish.bloom` 0.35-0.5로 불빛 번짐을 강화

## 도시 연산 (두머)

판형 아파트 단지, 전선, 가로등, 눈처럼 동유럽 겨울 도시의 쓸쓸한 분위기를 만드는 6개 연산. 인물 배경과 인물 없는 장면 모두에 씀.

| type | 주요 키 (기본값) | 설명 |
|---|---|---|
| `panel_blocks` | `blocks`, `time`("night"), `vanish`([0.5, 0.45]), `seed` | 판형 아파트 여러 동. 먼 동부터 나열 |
| `power_lines` | `poles`, `kind`("wood"), `color`, `haze_color`, `sag`(0.06), `extend`(true), `seed` | 기둥과 처진 전선 |
| `streetlamp` | `base`([0.7, 0.85]), `height`(0.45), `arm`(-1), `color`("#ffb35a"), `pole`, `glow`(0.7), `pool`(true), `on`(true) | 굽은 팔 가로등, 빛 번짐, 빛 원뿔, 바닥 빛 웅덩이 |
| `snow` | `count`(600), `size`([0.002, 0.009]), `top`(0), `bottom`(1), `color`, `opacity`(0.85), `wind`(12), `seed` | 내리는 눈. 큰 눈송이는 렌즈 가까이 있는 것처럼 흐림 |
| `fog` | `top`(0.5), `bottom`(0.9), `color`, `opacity`(0.5) | 낮게 깔린 안개 띠, `top` 위는 맑음 |
| `bare_tree` | `base`([0.7, 0.9]), `height`(0.45), `color`, `birch`(false), `lean`(0), `spread`(1), `seed` | 잎 진 나무 1그루, 잔가지까지 갈라짐 |

- `panel_blocks`의 블록 1개 키
    + `x` : [왼쪽, 오른쪽] 정면 벽의 가로 범위
    + `base`, `top` : 땅에 닿는 선과 지붕선의 높이
    + `floors`(9), `bays`(비율에서 자동) : 층수와 창 열 수
    + `side` : 측면 벽 폭(가로 비율). 양수는 오른쪽 측면, 음수는 왼쪽 측면이 `vanish`를 향해 줄어듦
    + `haze` : 0이면 가까움, 1이면 대기에 묻힘. 먼 동일수록 0.4-0.7
    + `lit` : 켜진 창 비율, 생략하면 `time`의 기본값 (밤 0.28, 해 질 녘 0.32, 낮 0)
    + `balconies`, `entrances` : 발코니와 1층 현관 (기본 true)
- `time` : `day`, `dusk`, `night`. 벽색, 유리색, 창 불빛이 함께 바뀜
- 측면 벽은 소실점을 넘지 않도록 정면 폭과 소실점 거리의 0.8까지만 그려짐
- `power_lines`의 `poles` : [x, 바닥 y, 높이] 목록을 선을 따라 나열
    + 작은 기둥일수록 멀리 있는 것으로 보고 `haze_color` 쪽으로 옅어짐
    + `kind` : `wood`(나무 전신주와 가로대), `pylon`(격자 송전탑)
    + `extend` : 가장 큰(가까운) 끝 기둥에서 전선이 화면 밖으로 이어짐. 먼 끝은 그 기둥에서 끝남
- `streetlamp`의 `arm` : -1이면 팔이 왼쪽, 1이면 오른쪽. `on` false면 꺼진 가로등
- `snow`는 `background` 목록(먼 눈)과 최상위 `foreground` 목록(인물 앞 큰 눈)에 각각 넣으면 깊이가 생김
- `bare_tree`의 `birch` true는 흰 줄기와 검은 무늬. 흰 눈밭 앞에서는 묻히므로 어두운 숲이나 건물 앞에 둠
- 순서 : `sky`, `clouds`, 먼 `panel_blocks`, `ground`, 가까운 `panel_blocks`, `power_lines`, `streetlamp`, `bare_tree`, `fog`, `snow`
    + `ground`를 블록보다 먼저 그려야 블록 아래가 지면에 묻혀 땅에 선 것으로 보임
- 마감은 `finish.preset` `"doomer"` (`style-guide.md`의 두머 절)

### 눈 내리는 단지의 밤

```json
"background": [
  {"type": "sky", "top": "#121826", "bottom": "#3a3346", "horizon": 0.7},
  {"type": "ground", "top": 0.78, "color": "#c2c6ce", "far_color": "#8f95a2"},
  {"type": "panel_blocks", "time": "night", "vanish": [0.5, 0.6], "seed": 3, "blocks": [
    {"x": [0.05, 0.40], "base": 0.80, "top": 0.30, "floors": 12, "haze": 0.5},
    {"x": [0.55, 0.95], "base": 0.82, "top": 0.18, "floors": 14, "side": -0.06}
  ]},
  {"type": "power_lines", "kind": "wood", "poles": [[0.44, 0.97, 0.6], [0.48, 0.84, 0.25], [0.5, 0.81, 0.12]]},
  {"type": "streetlamp", "base": [0.8, 0.92], "height": 0.5},
  {"type": "bare_tree", "base": [0.25, 0.97], "height": 0.75},
  {"type": "fog", "top": 0.6, "bottom": 0.9, "color": "#2a2c3a", "opacity": 0.3},
  {"type": "snow", "count": 500}
]
```

- 전체 spec : `assets/examples/doomer_establishing.json` (설정샷), `assets/examples/doomer_city.json` (안뜰), `assets/examples/doomer_landscape.json` (겨울 들판과 송전탑), `assets/examples/doomer_male.json`, `assets/examples/doomer_female.json`, `assets/examples/doomer_duo.json`

## 실내

| type | 주요 키 (기본값) | 설명 |
|---|---|---|
| `room` | `floor`(0.70), `wall`, `floor_color`, `baseboard`, `window`("day"), `window_x`(0.24), `window_width`(0.28), `window_top`(0.12), `window_bottom`(0.55), `curtain`, `vanish_x`(0.5), `lamp`, `lamp_color`, `art`, `art_color`, `seed` | 침실과 거실용 실내 벽, 창, 나무 바닥 |

- `room`은 한 번에 벽, 걸레받이, 원근이 들어간 나무 바닥, 커튼 달린 창을 그림
- `floor` : 벽과 바닥이 만나는 선의 높이 (캔버스 세로 비율)
- `window` : `day`(밝은 하늘과 햇빛), `night`(밤하늘, 달, 별), `none`(창 없음)
    + `window_x`는 창의 가로 중심, `window_width`는 폭, `window_top`과 `window_bottom`은 위아래 끝
- `lamp` : [x, y] 위치의 따뜻한 조명 번짐. 밤 장면의 분위기를 만듦
- `art` : [x, y, 가로, 세로]의 액자 그림. `art_color`가 그림의 주조색
- `vanish_x` : 바닥 널빤지가 모이는 소실점의 가로 위치
- 실내 인물은 `room`을 첫 연산으로 두고 바로 인물을 그림 (`sky`, `street` 불필요)
- 침대에 앉은 인물은 `figure.furniture` `bed`와 조합 (`figure_innerwear_room.json`)
- 밤 실내는 `window` `night`, `lamp`, `finish.bloom` 0.3, `shadow_tint`에 보라 계열이 잘 맞음

## 인물과 원근 맞추기

- 원리 : 지평선은 카메라 높이에 있는 모든 것을 지남
    + 카메라가 허리 높이면 지평선이 서 있는 사람의 허리를 지남
- 전신 인물 + 거리
    + `street.horizon` = `placement.pelvis`의 y (예 : 0.47)
    + `street.eye` = 0.9
- 상반신 또는 흉상 + 거리
    + `street.horizon` = 눈의 y, `street.eye` = 1.55
- 자연 풍경 배경은 지평선(`sky.horizon`, `ridge.base`)을 인물의 허리와 가슴 사이에 두면 안정적
- 실내 배경은 `room.floor`를 서 있는 인물의 무릎과 발목 사이에 두면 인물이 바닥에 선 것으로 읽힘
    + 상반신 구도(`thigh`, `knee`, `waist`)는 바닥이 화면 아래에 조금만 보이는 0.70-0.85
- 바닥이 보이면 `figure.ground_shadow`를 켬
- `ambient`에 배경의 어두운 색을 주면 인물 하반부가 장면에 섞임

## 조립 예시

### 산과 호수

```json
"background": [
  {"type": "sky", "top": "#4f7fc0", "bottom": "#f3d9b8", "horizon": 0.62},
  {"type": "clouds", "color": "#fff4e6", "shadow": "#c9a9b8", "seed": 11},
  {"type": "ridge", "base": 0.60, "height": 0.30, "color": "#8f9cc4", "shadow": "#6a7aa8", "haze": "#f3d9b8", "snow": "#ffffff", "seed": 3},
  {"type": "ridge", "base": 0.62, "height": 0.17, "color": "#5f7396", "shadow": "#44567a", "haze": "#e9cdb4", "seed": 8},
  {"type": "tree_line", "base": 0.625, "height": 0.045, "color": "#34503f"},
  {"type": "water", "top": 0.625, "tint": "#20406a"},
  {"type": "ground", "top": 0.86, "color": "#5f8a47", "far_color": "#7fa86a"},
  {"type": "grass", "top": 0.84},
  {"type": "pine", "base": [0.12, 0.93], "height": 0.42},
  {"type": "tree", "base": [0.86, 0.95], "height": 0.62, "rim": "#ffe9a8"}
]
```

### 밤거리

```json
"background": [
  {"type": "sky", "top": "#0b0f2a", "bottom": "#2a2f66", "horizon": 0.56},
  {"type": "stars", "count": 260, "bottom": 0.5},
  {"type": "street", "horizon": 0.56, "time": "night", "wet": 0.45, "seed": 7, "cars": 5, "people": 8}
]
```

- 전체 spec : `assets/examples/landscape_lake.json`, `assets/examples/city_night.json`, `assets/examples/city_day.json`, `assets/examples/city_crowd.json` (가까운 행인), `assets/examples/figure_city.json`, `assets/examples/male_figure_city.json`, `assets/examples/figure_showcase.json` (해변), `assets/examples/male_beach.json`, `assets/examples/figure_side_walk.json` (공원), `assets/examples/figure_innerwear_room.json` (밤 침실), `assets/examples/male_arms_crossed.json` (낮 거실)

## 화풍 마감

- 장면만 있는 그림도 `style`에 따라 마감이 달라짐
    + `painterly` : 풍경화에 가장 잘 어울림, `finish.radii` [22, 11, 5, 2.5] 권장
    + `illust` : 야경과 역광 장면, 블룸과 비네트
    + `anime` : 선명한 배경 미술 느낌
- 빌더에 없는 사물은 `references/paintkit-api.md`의 프리미티브로 추가
