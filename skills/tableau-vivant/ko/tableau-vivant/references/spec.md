# 사양 파일 필드

`spec.json`의 전체 구조. 생략한 필드는 기본값 적용

## 좌표와 단위

- 길이 단위는 미터, 각도 단위는 도
- 월드 축: X는 화면 오른쪽(인물 기준 왼쪽), Y는 화면 안쪽(인물의 등 방향), Z는 위
    + 기본 인물은 원점에 서서 -Y 방향(카메라 쪽)을 바라봄
    + 카메라는 기본적으로 -Y 쪽에서 +Y 쪽을 바라봄
- 색은 0-1 범위 RGB 배열. 예: `[0.86, 0.25, 0.22]`

## 최상위 구조

```json
{
  "canvas": {},
  "environment": {},
  "figures": [],
  "pairs": [],
  "groups": [],
  "props": [],
  "trees": [],
  "lights": [],
  "camera": {},
  "light": {},
  "style": "anime",
  "post": {}
}
```

## canvas

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `aspect` | `"4:5"` | 가로:세로 비율 |
| `detail` | `"standard"` | `draft` 640, `standard` 1024, `fine` 1536, `max` 2048 (긴 변 픽셀) |
| `width`, `height` | 없음 | 직접 지정 시 `aspect`보다 우선. 8의 배수 권장 |
| `seed` | 7 | 머리카락, 붓질, 지형, 구름의 난수. 바꾸면 변주 |
| `supersample` | 2 | 선과 가장자리 품질. `draft`는 1 |

## environment

`type`에 따라 필드가 달라짐

### plain_color

| 필드 | 기본값 |
| --- | --- |
| `color` | `[1, 1, 1]` |

### studio

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `top`, `bottom` | 밝은 회색 | 배경지 위쪽과 아래쪽 색 |
| `glow` | 없음 | 주제 뒤 은은한 빛의 색 |
| `floor` | true | 바닥과 드리운 그림자 |
| `floor_color` | `bottom`과 동일 | 바닥 색 |

### room

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `wall`, `floor` | 베이지, 갈색 | 벽과 바닥 색 |
| `depth` | 3.0 | 원점에서 뒷벽까지 거리 |
| `width` | 7.0 | 옆벽 사이 거리 |
| `sides` | true | 옆벽 유무. 옆에서 비스듬히 보는 실내 구도에서 배경이 비지 않음 |

### landscape

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `preset` | `"meadow"` | `meadow`, `hills`, `mountain_lake`, `seaside`, `forest`, `desert`, `snow`, `garden`, `city`, `plain` |
| `time` | `"day"` | `day`, `golden_hour`, `sunset`, `dawn`, `overcast`, `dusk`, `night` |
| `ground` | 프리셋값 | `grass`, `meadow`, `sand`, `snow`, `rock`, `dirt`, `asphalt` |
| `hills` | 프리셋값 | 언덕 높이 |
| `mountains` | 프리셋값 | 먼 산의 높이. 0이면 없음 |
| `mountain_start` | 0.30 | 산이 시작되는 거리 비율 |
| `water_level` | 없음 | 수면 높이. 지형이 이보다 낮은 곳이 물 |
| `basin` | 없음 | `[깊이, 반경, 거리]` 호수 분지 |
| `shore` | 없음 | `[거리, 기울기]` 바다로 내려가는 해안 |
| `clouds` | 0.45 | 하늘에서 구름이 덮는 비율 0-1 |
| `ridges` | 3 | 지평선의 먼 능선 겹 수 |
| `haze_distance` | 120 | 대기 원근이 짙어지는 거리. 작을수록 안개 |
| `snow_line` | 없음 | 이 높이 위는 눈 |
| `flat_radius` | 6 | 원점 주변 평지 반경 |
| `sun_azimuth_deg` | 자동 | 해의 방위. 생략 시 주제를 앞쪽 비스듬히 비춤 |
| `sun_side` | `"behind"` | 해의 위치: `behind`, `front`, `left`, `right` |
| `tufts`, `rocks` | 프리셋값 | 전경 풀 다발 개수, 바위 개수 |
| `path` | 프리셋값 | `true`는 기본 오솔길, 또는 지면 좌표 목록 `[[x, y], ...]`, `null`은 없음 |
| `forest` | 프리셋값 | `{count, kinds, area: [x0, x1, y0, y1], min_distance, height: [min, max], clearing, grouping}`. `grouping` 0-1은 나무를 숲 덩어리로 모음. `null`이면 나무 없음 |
| `city` | `city` 프리셋만 | `{count, length, height: [min, max], cars, lamps, neon, wet, skyline}` |

- 호수와 바다는 수면 반사를 자동 계산
- `landscape`를 쓰면 조명 방향은 해의 위치를 따름. `light.azimuth`를 지정하면 덮어씀

## figures

배열. 인물 1명당 객체 1개. 상세는 `figures.md`

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `name` | `"figure"` | 고유 이름. 카메라 `subject`와 색 지정에 사용 |
| `preset` | `"woman"` | 체형과 얼굴 프리셋 |
| `phenotype` | 프리셋값 | 체형 축 덮어쓰기 |
| `face` | 프리셋값 | 얼굴과 신체 모핑 덮어쓰기 |
| `expression` | `"neutral"` | 프리셋 이름 또는 표정 단위 객체 |
| `pose` | `"stand"` | 프리셋 이름 또는 자세 객체 |
| `hair` | `"long_straight"` | 이름 또는 `{style, bangs, part, color, density, length_scale, wind}` |
| `outfit` | `"nude"` | 프리셋 이름 또는 의상 객체 배열 |
| `colors` | 없음 | `{의상 id: 색}` |
| `skin` | `"light"` | 이름 또는 색 |
| `look` | 프리셋값 | 화장과 눈 설정 |
| `beard` | `"none"` | 수염 이름 또는 `{style, color}` |
| `stylize` | 프리셋값 | 얼굴 양식화: `none`, `semi`, `anime`, `chibi` |
| `position` | `[0, 0, 0]` | 발 위치. 지형 위에서는 높이가 자동 보정 |
| `hat` | 없음 | `"beanie"` 또는 `{style, color}` |
| `facing` | 0 | 몸의 방향. 양수는 인물 기준 왼쪽으로 회전. 각도 대신 바라볼 사물 이름, 인물 이름, `[x, y]` 지정 가능 |

## pairs

배열. 몸이 닿는 두 사람(손잡기, 어깨동무, 포옹, 댄스). `{kind, a, b, at, facing, distance}`. 상세는 `figures.md`의 두 사람 자세

## groups

배열. 한 줄로 서서 옆 사람과 차례로 닿는 3명 이상(어깨동무, 손잡은 줄). `{kind, members, at, facing, spacing}`. 상세는 `figures.md`의 여러 사람 줄

## props

배열. 종류와 옵션은 `scenes.md`

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `kind` | 필수 | 카탈로그 이름 |
| `name` | `kind`와 동일 | 다른 사물이 `on`으로 참조하는 이름 |
| `at` | `[0, 0, 0]` | 위치 |
| `on` | 없음 | 이 이름의 사물 윗면에 올림. `at`의 z는 추가 높이 |
| `rotate_deg` | 0 | 수직축 회전. 각도 대신 향할 사물 이름, 인물 이름, `[x, y]` 지정 가능 |
| `scale` | 1.0 | 크기 배율 |
| `colors` | 없음 | `{부품 이름: 색}` |
| `held_by` | 없음 | `"인물:hand.R"`, `"인물:hand.L"`, `"인물:hands"`. 그 손에 쥠. `at`과 `on`은 무시 |

- 손에 들지 않은 사물은 인물보다 먼저 배치됨. 인물의 `facing`이 사물 이름을 참조할 수 있음

## trees

배열. 개별 나무. `{kind, at: [x, y], height}`

## lights

배열. 보이는 광원 없이 빛만 더할 때 사용 (화면 밖 조명, 창에서 들어오는 빛, 바위 뒤 모닥불)

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `at` | 필수 | 빛의 위치 |
| `color` | 따뜻한 흰색 | 빛의 색 |
| `power` | 1.0 | 세기. 1m 거리 밝기가 약 `power` |
| `direction` | 없음 | 지정하면 그쪽으로만 비춤 |
| `softening` | 0.3 | 가까운 곳이 과하게 밝아지지 않도록 하는 반경(미터) |

- 화면, 전구, 촛불, 네온, 가로등, 자동차 등은 별도 지정 없이 스스로 주변을 비춤

## camera

세 가지 방식 중 하나

| 방식 | 필드 |
| --- | --- |
| 인물 기준 | `subject`(인물 이름), `shot`, `yaw`, `pitch`, `fill`, `offset`, `fov`, `roll`. 어깨 너머는 `shot: "over_shoulder"`, `over`, `side` |
| 직접 지정 | `eye: [x, y, z]`, `target: [x, y, z]`, `fov` |
| 전체 맞춤 | `fit: "all"`, `yaw`, `pitch`, `fill` |
| 인물 맞춤 | `fit: "people"` 또는 인물과 사물 이름 목록, `shot`, `yaw`, `pitch`, `fill`. 풍경 속 군상과 투샷 |

- 생략 시 인물이 1명이면 그 인물 전신, 2명 이상이거나 `pairs`, `groups`가 있으면 전원을 담는 구도, 풍경 프리셋만 있으면 프리셋 카메라
- 풍경 프리셋에서 `fit: "all"`은 지형과 건물까지 담아 인물이 작아짐. 사람을 담으려면 `fit: "people"`
- 인물 맞춤의 `shot`은 각 인물을 그 높이에서 자름. 예: `"cowboy"`는 군상의 허벅지 위
- `fov`는 세로 화각. 샷이 좁을수록 자동으로 망원 적용

## light

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `preset` | `"three_quarter"` | `scenes.md`의 조명 표 |
| `mood` | `"neutral"` | 빛과 그림자의 색 |
| `azimuth` | 프리셋값 | 카메라 기준 방위. 0은 정면광, 90은 화면 오른쪽 측면광, 180은 역광 |
| `elevation` | 프리셋값 | 높이 각 |
| `key`, `ambient`, `rim` | 프리셋값 | 주광, 환경광, 윤곽광 세기 |
| `light_color`, `shadow_color` | `mood`값 | 직접 지정 |
| `glow` | 시간대값 | 빛나는 사물이 주변을 비추는 세기. 기본 1, 해 질 녘 2, 밤 3. 0이면 끔 |

## style

- 문자열이면 화풍 이름
- 객체이면 `{"name": "oil", ...파라미터}`. 파라미터는 `styles.md`

## post

| 필드 | 설명 |
| --- | --- |
| `grade` | 색감 프리셋 이름 |
| `contrast`, `saturation`, `brightness` | 기본 보정 |
| `temperature` | 양수는 따뜻하게, 음수는 차갑게 |
| `shadows_tint`, `highlights_tint` | 어두운 곳과 밝은 곳에 넣을 색 |
| `bloom`, `bloom_threshold` | 밝은 곳의 빛 번짐 |
| `grain`, `vignette`, `sharpen`, `fade` | 입자, 주변 감광, 선명도, 바랜 느낌 |
| `border`, `border_color` | 여백 테두리 (짧은 변 대비 비율) |
