# 장면

배경, 사물, 카메라, 조명의 지정 방법

## 사물 카탈로그

| 분류 | 이름 (색을 바꿀 수 있는 부품) |
| --- | --- |
| 정물 그릇 | `vase`, `amphora`, `bottle`, `wine_glass`(glass), `bowl`, `plate`, `mug`, `teapot` |
| 과일 | `apple`, `orange`, `lemon`, `peach`, `pear`, `grapes` |
| 소품 | `book`(book, pages), `candle`(candle, brass, flame), `flower`(petal, stem, flower_heart), `cloth`, `ball`, `sword`(steel, brass, grip), `lamp`(lamp_base, lamp_shade), `lightbulb`(bulb, metal) |
| 가구 | `table`, `round_table`, `chair`, `stool`, `bench`, `desk`, `daybed`(frame, mattress, bolster) |
| 컴퓨터, 화면 | `monitor`(monitor, stand, screen), `laptop`(laptop, keys, pad, screen), `tablet`(tablet, screen), `phone`(phone, screen), `tv`(monitor, stand, screen), `keyboard`(keyboard, keys), `mouse`(mouse, wheel), `pc_tower`(case, led, vent) |
| 기기 | `headphones`(earcup, cushion, band), `game_controller`(controller, stick), `camera`(camera, lens, lens_ring), `speaker`(speaker, cone, surround), `desk_lamp`(lamp_base, lamp_arm, lamp_shade) |
| 생활 소품 | `takeaway_cup`(cup, sleeve, lid), `wall_clock`(clock_face, clock_rim, hands), `potted_plant`(pot, leaf) |
| 현대 가구 | `office_chair`(upholstery, chrome), `sofa`(sofa, cushion, legs), `bookshelf`(shelf, 책은 시드별 색) |
| 건축, 야외 | `pedestal`(stone), `column`(stone), `wall`, `rock`, `crate`, `barrel` |
| 거리 | `car`(car, car_glass, headlight, taillight), `street_lamp`(metal, bulb), `bus_stop`(concrete, glass, bench, bulb, screen) |
| 단지 | `panel_block`(panel, roof, canopy, rail, glazing, metal. 조립식 판넬 아파트 동), `power_line`(pole, insulator, wire. 전신주 행렬과 처진 전선) |
| 두머 소품 | `cigarette`(filter, paper, ember. 불씨가 빛남), `ashtray`(glass, butt, ash), `radio`(카세트 라디오) |
| 나무 (`trees` 또는 `forest`) | `broadleaf`, `pine`, `cypress`, `birch`, `bare`, `palm`, `sakura` (trunk, foliage) |

- 재질마다 광택이 다름. 유리, 유약, 금속, 과일 껍질에는 하이라이트가 생기고 `wine_glass`는 뒤가 비쳐 보임
- 나무 재질에는 나뭇결, 과일에는 색 얼룩이 자동으로 들어감
- `wine_glass`의 `wine`은 채움 정도 0-1. `cloth`의 `drop`은 앞 가장자리 아래로 늘어지는 길이. 천의 앞 가장자리를 탁자 앞 가장자리에 맞춰 배치
- `daybed`의 윗면 높이는 `height + 0.13`. 기대 누운 인물은 `position` z를 이 값으로 지정
- 옵션 예: `table`은 `width`, `depth`, `height`. `chair`는 `seat_height`. `column`은 `height`, `radius`. `cloth`는 `width`, `depth`, `drop`. `crate`는 `size`. `rock`은 `radius`
- `flame`, `screen`, `bulb` 부품은 스스로 빛나는 재질로 처리
- 화면이 있는 사물은 `screen`으로 내용을 고름: `desktop`(창과 작업 표시줄), `code`(코드 편집기), `video`(영상 한 장면), `chart`(대시보드), `game`(게임 화면), `off`(꺼진 검은 화면)
    + 기본값: `monitor`는 `desktop`, `laptop`은 `code`, `tablet`과 `tv`는 `video`, `phone`은 `desktop`
- 현대 사물 옵션: `monitor`와 `tv`는 `width`(화면 폭), `lift`(받침 높이). `tv`는 `feet`(false면 벽걸이). `phone`은 `lying`(false면 세움). `tablet`은 `upright`. `wall_clock`은 `time: [시, 분]`, `radius`. `bookshelf`는 `width`, `height`, `shelves`, `seed`. `sofa`와 `office_chair`는 `color`. `pc_tower`는 `light`(전면 조명 색)
- 벽시계는 `at`의 z가 걸리는 높이. 방(`room`)의 벽면은 원점에서 `depth - 0.1` 거리
- 단지 사물 옵션
    + `panel_block`: `floors`(층수, 9), `sections`(현관 수, 4), `lit`(불 켜진 창 비율. 낮 0, 밤 0.2-0.35), `seed`(창 배치). 정면(발코니, 현관)이 -y. 길이는 현관당 16m, 깊이 12m
    + `power_line`: `length`, `height`(전신주 높이 9), `span`(전신주 간격 32), `wires`(3)
    + `bus_stop`: 정면이 -y로 열림. `light`(false면 천장등 끔), `ad`(false면 광고판 없음). 뒷벽은 유리라 뒤 배경이 비침
    + `cigarette`: `lit`(false면 불 꺼진 담배), `length`. 손에 쥐려면 `"held_by": "a:hand.R"` (검지와 중지 사이)
    + `ashtray`: `butts`(꽁초 수), `cigarette`(false면 타는 담배 없음)
    + `lightbulb`: `cord`(천장에 매단 전선 길이 m). 지정하면 `at`이 천장 고리 위치이고 전구가 아래로 매달림
- 책상 정물은 모니터를 책상 뒤쪽 중앙에, 키보드와 마우스를 앞쪽에, 조명과 화분을 양 끝에 두면 안정적. 예: `modern_desk_digital.json`

### 배치 요령

- 탁자 위 사물은 `"on": "table"` 지정. `at`의 x, y는 월드 좌표, z는 탁자 윗면에서의 추가 높이
- 정물은 3-7개를 삼각형 구도로 배치
    + 큰 것(항아리)을 뒤쪽 한편에, 중간 것(병, 그릇)을 중앙에, 작은 것(과일)을 앞쪽에
    + 사물끼리 일부 겹치게 놓아야 깊이가 생김
- 그릇 안 과일은 `"on": "table"`에 z를 0.03 정도 더함
- 인물이 손에 든 사물은 `"held_by": "a:hand.R"`(한 손) 또는 `"a:hands"`(두 손). `figures.md`의 손에 든 사물 참조
- 의자나 인물을 탁자 쪽으로 돌리려면 `rotate_deg`나 `facing`에 `"table"`처럼 대상 이름을 지정
    + 마주 앉은 두 사람은 탁자 중심에서 각각 0.7 정도 떨어뜨려야 무릎이 탁자 밑에서 부딪히지 않음

## 환경별 요령

### studio

- 초상과 전신 인물의 기본 배경
- 배경색은 주제의 보색 또는 낮은 채도로 선택
    + 고전 유화: `top [0.12, 0.10, 0.08]`, `bottom [0.20, 0.15, 0.11]`, `glow [0.42, 0.33, 0.22]`
    + 밝은 애니메: `top [0.78, 0.86, 0.95]`, `bottom [0.93, 0.88, 0.90]`
    + 야간 분위기: `top [0.10, 0.12, 0.18]`, `bottom [0.18, 0.15, 0.22]`, `glow [0.34, 0.28, 0.44]`

### landscape 프리셋

| 이름 | 내용 | 권장 시간대 |
| --- | --- | --- |
| `meadow` | 꽃이 핀 초원, 활엽수 | `day`, `golden_hour` |
| `hills` | 구릉, 활엽수와 사이프러스 | `day`, `overcast` |
| `mountain_lake` | 설산, 호수, 침엽수. 수면 반사 | `golden_hour`, `dawn` |
| `seaside` | 모래 해변과 바다, 야자수 | `sunset`, `day` |
| `forest` | 빽빽한 숲, 가까운 안개 | `day`, `overcast` |
| `desert` | 모래 언덕 | `sunset`, `day` |
| `snow` | 설원과 설산, 침엽수 | `dawn`, `overcast` |
| `garden` | 사이프러스와 벚나무가 있는 평지 정원 | `day`, `dawn` |
| `city` | 건물, 인도, 차선과 횡단보도, 가로등, 주차된 차, 원경 스카이라인. 밤에는 창과 간판에 불이 켜지고 젖은 노면이 빛을 반사 | `night`, `dusk`, `day` |
| `plain` | 나무 없는 평지 | 전체 |
| `estate` | 눈 덮인 판넬 아파트 단지 마당. 동 5개가 마당을 둘러싸고 길을 따라 나트륨 가로등 3개 | `night`, `dusk` |
| `estate_street` | 판넬 아파트 동 사이로 곧게 뻗은 차도, 양쪽 나트륨 가로등, 눈 덮인 보도 | `night`, `dusk` |

- 프리셋에는 전경 풀 다발(`tufts`), 바위(`rocks`), 오솔길(`path`)이 들어 있음. 개수를 바꾸거나 0과 `null`로 끌 수 있음
- `sun_side`: `behind`(기본, 주제를 앞에서 비춤), `front`(해가 화면 안에 들어오는 역광, 물 위에 윤슬), `left`, `right`
- 도시 옵션 `city`: `{count, height: [min, max], cars, lamps, neon, wet, skyline}`. 인물은 차도 중앙(원점)이나 인도(`x` ±6)에 배치
- 단지 옵션 `estate`: `{layout: courtyard | street, lit, lamps}`. `lit` 생략 시 시간대로 정함(밤 0.28, 해질녘 0.18)
    + `estate` 마당: 가로등은 x 3.2, y 3, 15, 27. 인물을 가로등 뒤 1-2m(y 4-5)에 두면 주황 불빛이 얼굴과 어깨에 떨어짐
    + `estate_street`: 차도 폭 9m(x ±4.6), 가로등은 x ±5.6에 22m 간격. 버스 정류장은 x 5.6, `rotate_deg` -90
    + 밤 장면은 `"light": {"key": 0.3, "ambient": 0.2}`로 달빛을 낮춰야 가로등 웅덩이와 창이 그림을 이끔
- 인물은 원점 근처에 배치. 원점 주변은 평지로 유지됨
- 풍경만 그릴 때는 카메라를 생략하면 프리셋 카메라 적용
- 인물이 있을 때 배경이 허전하면 `forest`의 `area`를 인물 뒤쪽(y 5-30)으로 좁혀 나무를 가깝게 배치
- 숲이 고르게 흩어져 단조로우면 `forest.grouping` 0.5-0.7로 덩어리와 빈터를 만듦
- 바다(`seaside`)는 해안선과 나란한 물결과 부서지는 흰 파도를 자동 생성
- 화면 가장자리에 큰 나무 1그루(`trees`)를 두면 전경 액자 구도가 생김. 예: `lake_watercolor.json`

## 카메라

### 인물 기준

```json
"camera": {"subject": "a", "shot": "bust", "yaw": -15, "pitch": 3, "offset": [-0.1, 0], "fill": 0.82}
```

| 필드 | 설명 |
| --- | --- |
| `shot` | `full`, `knee`, `cowboy`, `medium`, `bust`, `closeup`, `face`, `over_shoulder` |
| `yaw` | 인물 정면이 0. 양수는 카메라가 인물의 왼쪽으로 돌아감 |
| `pitch` | 카메라 높이 각. 양수는 위에서 내려다봄 |
| `offset` | 주제를 화면에서 옮김. `[-0.12, 0]`은 왼쪽 삼분할 선 |
| `fill` | 주제가 화면을 채우는 비율 |
| `fov` | 세로 화각. 생략 시 샷에 맞는 값 (전신 30, 얼굴 16) |
| `roll` | 화면 기울임(더치 틸트) 각도 |

- 카메라는 바닥이나 지면 아래로 내려가지 않음
    + `pitch`를 크게 음수로 주면 지면 바로 위로 다가가 광각으로 올려다보는 로우 앵글이 됨
    + 그래도 담기지 않으면 각도를 줄임 (화각 상한 70)
- 어깨 너머 구도: `{"subject": "a", "shot": "over_shoulder", "over": "b", "side": "right"}`
    + `b`의 어깨 너머로 `a`의 얼굴을 봄. `side`는 화면에서 `b`의 어느 쪽 어깨 너머인지(`right`, `left`)
    + 가까운 사람의 뒷머리와 어깨가 화면 한쪽을, 얼굴이 반대쪽 삼분할 선을 차지
    + 두 사람이 서로 보게 하려면 `b`의 `facing`을 `"a"`로

### 직접 지정

```json
"camera": {"eye": [0.15, -1.75, 1.22], "target": [0.1, 0, 0.86], "fov": 34}
```

- 정물: 탁자 높이보다 0.4-0.5 위에서 1.5-2 떨어져 내려다봄
- 풍경: 눈높이 1.7에서 멀리 바라봄. 하늘을 넓히려면 `target`의 z를 높임
- 다인 장면: 인물들의 중간 지점을 `target`으로

### 구도 원칙

- 주제의 얼굴 또는 초점을 삼분할 교차점에 배치
- 시선 방향 쪽 여백을 더 넓게
- 전신은 발끝과 머리 위에 여백. 관절(무릎, 발목, 손목)에서 화면을 자르지 않음
- 올려다보는 시점(`pitch` 음수)은 위엄, 내려다보는 시점은 친근함 또는 왜소함

## 조명

| 프리셋 | 방위 | 높이 | 특징 |
| --- | --- | --- | --- |
| `three_quarter` | 42 | 36 | 기본. 입체감과 가독성의 균형 |
| `front` | 12 | 24 | 그림자 최소 |
| `loop` | 30 | 32 | 코 옆에 작은 그림자. 초상 표준 |
| `butterfly` | 0 | 55 | 코 밑 그림자. 뷰티 초상 |
| `rembrandt` | 58 | 44 | 어두운 뺨에 빛 삼각형. 환경광 낮음 |
| `side` | 88 | 18 | 얼굴 절반이 그림자 |
| `split` | 96 | 4 | 좌우 완전 분할 |
| `rim` | 150 | 30 | 뒤에서 비추는 윤곽광 |
| `back` | 175 | 22 | 역광 실루엣 |
| `top`, `under` | 15, 8 | 76, -42 | 정수리 조명, 아래 조명 |
| `soft`, `flat` | 35, 10 | 35, 30 | 환경광 높음. 그림자 약함 |

- 방위는 카메라 기준. 양수는 화면 오른쪽에서 비춤. 음수로 지정하면 왼쪽 광원
- `mood`는 빛과 그림자의 색
    + `neutral`, `warm`, `cool`, `candle`, `moon`, `old_master`, `pastel`, `neon`, `noir`
- 셀화 계열에서 얼굴 그림자가 지저분하면 `front` 또는 `loop`로 변경
- `ambient`를 낮추면 대비가 강해지고 높이면 평면적이 됨

### 빛나는 사물의 조명

- 화면, 전구, 촛불, 네온 간판, 가로등, 자동차 등은 주변을 스스로 비춤
    + 빛의 색은 발광체 색을 따름. 화면은 띄운 내용의 평균 색으로 비춤
    + 화면과 판형 조명은 앞쪽으로만 비추고 거리에 따라 약해짐
    + 밤 도시에서는 불 켜진 상점 창이 인도를 따뜻하게 비춤
- 세기는 `light.glow`로 조절. 밤 장면은 기본 3배, 해 질 녘은 2배
- 실내 야경은 주광 `key`를 0.3-0.4, `ambient`를 0.2 정도로 낮춰야 발광체 빛이 살아남. 예: `living_room_night.json`
- 보이는 광원 없이 빛만 필요하면 최상위 `lights` 배열 사용 (`spec.md`)
- 방의 벽은 주광 그림자를 만들지 않음. 무대 세트의 벽처럼 빛을 받기만 함
