# 주제별 구성법

리그가 없는 주제를 기본 도형으로 구성하는 방법. 주제마다 `scripts/examples/`에 실행 가능한 기준 예제가 있으므로 가장 가까운 예제를 복사해 고치는 방식이 빠르다.

## 예제 목록

| 주제 | 예제 | 핵심 기법 |
|---|---|---|
| 인물 흉상 | `examples/portrait.py` | 흉상 리그, 과정 시트 |
| 전신, 인체 습작 | `examples/figure.py` | 전신 리그, 의상, 바닥 그림자, 앉기와 눕기 가구 |
| 투샷과 장면 | `examples/scene.py` | 구도 프리셋, 손 뻗기, 인물 순서, 장면 배경 4종 |
| 손 | `examples/hands.py` | 손 리그 |
| 정물 | `examples/still_life.py` | 회전체, 광택, 탁자 그림자 |
| 현대 사물 (책상) | `examples/desk.py` | 사투상 상자, 화면과 자판 매핑, 광원 번짐 |
| 도시 | `examples/city.py` | 1점 투시 벽, 창문 격자, 젖은 노면 |
| 풍경 (노을 호수) | `examples/landscape.py` | 산 능선, 수면 반영 |
| 풍경 (한낮 언덕) | `examples/meadow.py` | 뭉게구름, 나무, 대기 원근 |
| 두머 무드 7컷 | `examples/doomer.py` | 패널 아파트 면, 송전탑, 굴뚝 연기, 창턱 정물, 무드 보정 |

- 실행 형식은 `python examples/<이름>.py --style anime|illust|painterly --out out.png`
    + 두머 예제는 `python examples/doomer.py --cut man|woman|pair|establishing|city|landscape|still_life|all --out-dir 폴더`

## 정물

- 탁자 뒤 모서리 높이를 화면의 50-60%에 설정
    + 물체는 바닥선이 서로 다른 높이에 오도록 앞뒤로 배치
- 물레로 빚은 형태는 `geo.symmetric(profile, axis_x)`
    + profile은 축에서 오른쪽 윤곽까지의 거리와 높이를 위에서 아래로 나열
    + 병, 꽃병, 잔, 그릇, 배(과일)
- 과일은 `geo.ellipse`, 포도는 작은 타원을 아래쪽 것이 위를 덮도록 정렬
- 속이 보이는 그릇은 3단계로 그림
    + 안쪽 벽(입구 타원)을 어둡게 칠함
    + 담긴 물체를 그림
    + 입구선 아래의 앞면만 다시 덮음
- 물체마다 3가지 빛 표현을 적용
    + `paint_part`의 형태 음영
    + `styles.gloss`의 광택 점
    + `sh.ground_shadow`의 탁자 그림자 (곱하기 모드로 칠함)
- 유리는 빛 쪽에 긴 세로 반사 1줄, 반대쪽에 가는 반사 1줄
- 배경 벽은 주제보다 어둡게, `backdrop.window_light`로 빛의 출처를 암시

## 현대 사물

- 상자형 사물은 `geo.Oblique`의 사투상으로 배치
    + 좌표는 (가로 x, 뒤쪽 y, 높이 z), 평행한 모서리가 평행하게 유지되는 제도 방식
    + `Oblique(origin, across, back, up)`의 세 방향 벡터가 시점을 결정
- 상자 1개는 `DESK.box(x, y, z, 폭, 깊이, 높이)`로 윗면, 앞면, 옆면 사각형을 얻어 `objects.paint_box`로 칠함
    + 면마다 명도 1단계씩 차이를 두면 음영 계산 없이 입체가 읽힘
- 원통형 사물은 `objects.paint_cylinder(painting, center, radius, height, color, style, light, hollow=)`
    + 머그, 화분, 캔, 스탠드 받침
- 면 위의 세부는 `geo.quad_map(face)`에 0-1 좌표를 넘겨 배치
    + 화면 내용, 자판, 아이콘, 공책 줄
    + 둥근 모서리는 `geo.rounded_rect(x0, y0, x1, y1, radius)`
    + 격자는 `geo.grid_cells(columns, rows, margin, inset)`
- 기운 면은 네 모서리를 `Oblique.place`로 직접 지정
    + 예시 : 노트북 덮개는 경첩 2점과 뒤로 젖힌 윗변 2점
- 그리는 순서는 뒤쪽(y가 큰 것)부터
    + 사물마다 `sh.cast_shadow(mask, desk_top, offset)`을 곱하기 모드로 깔아 바닥에 붙임
- 화면과 조명은 광원으로 취급
    + 화면 마스크를 `sh.blur`로 번지게 해 스크린 모드로 얹으면 주변에 빛이 번짐
    + 조명은 `backdrop.glow`로 빛 웅덩이 표현
- 사물별 구성은 아래 표 적용

| 사물 | 구성 |
|---|---|
| 모니터 | 받침 상자, 기둥 상자, 얇은 본체 상자, 앞면에 화면 |
| 노트북 | 납작한 상자, 윗면에 자판 격자와 트랙패드, 기운 사각형 덮개 |
| 키보드 | 납작한 상자, 윗면에 둥근 키 격자 |
| 스마트폰 | 얇은 상자, 윗면에 둥근 화면과 아이콘 격자 |
| 마우스 | 기운 타원, 광택 점, 가운데 이음선 |
| 머그 | 원통, 손잡이는 `geo.tube`, 김은 흐린 `stroke` |
| 스탠드 | 원통 받침, `geo.tube` 팔, 사다리꼴 갓, `backdrop.glow` |

## 도시

- 소실점 1개를 먼저 정하고 모든 벽의 먼 모서리를 그 점으로 당김
    + `scenery.street_wall(base_near, vanishing, near, far, height)`가 벽 사각형 반환
    + `near`, `far`는 거리 방향 위치(0은 화면 앞, 1은 소실점)
- 건물은 먼 것부터 그려 가까운 건물이 덮게 함
    + 건물마다 높이와 색을 다르게 주어 스카이라인에 리듬 형성
- 창문은 `scenery.windows(painting, quad, columns, rows, lit_colors, lit=0.4)`
    + 내부에서 `geo.quad_map`이 원근 간격을 계산
    + 반환된 불 켜진 창 마스크는 노면 반사와 번짐에 재사용
- 간판, 문, 타일도 `geo.quad_map(quad)`에 0-1 좌표 사각형을 넘겨 배치
- 도로 표시는 소실점 직전에서 끊은 사각형에 매핑
    + 한 점으로 닫히는 사각형은 먼 변의 길이가 0이라 간격 계산이 무너짐
- 먼 도시는 `scenery.skyline`의 실루엣과 점 크기의 불빛으로 처리
- 밤과 황혼은 하늘 그라데이션, 창문 불빛, 가로등 `backdrop.glow` 3가지가 분위기를 결정

## 풍경

- 화면을 하늘, 원경, 중경, 근경 4층으로 나누고 먼 층부터 그림
- 대기 원근은 색으로 표현
    + 멀수록 밝게, 푸르게, 단순하게
    + 층 사이 발치에 지평선 색 안개를 옅게 깔아 층을 분리
- 층별 도형은 아래 표 적용

| 요소 | 도형 |
|---|---|
| 산, 언덕 | `scenery.ridge`, roughness 0.3은 언덕, 0.55는 바위산 |
| 줄구름, 새털구름 | `scenery.clouds`, softness 0.01은 선명, 0.07은 부드러움 |
| 뭉게구름 | `scenery.puffs`, 밑면이 평평한 덩어리 |
| 나무 수관, 덤불 | `scenery.foliage`, 잎 뭉치마다 음영 |
| 침엽수 | `scenery.conifer` |
| 풀, 꽃 | `scenery.blades`, `scenery.scatter` |
| 길, 강 | `geo.tube`, 먼 쪽 폭을 좁게 |
| 수면 | `scenery.reflect`, 반짝임은 `geo.needle` |

- 노을은 구름 밑면을 밝히고 한낮은 구름 윗면을 밝힘
    + 밑면 띠는 `cloud - sh.shift(cloud, 0, -14)`로 추출
- 세부는 근경에만 투입
    + 풀잎, 꽃, 나무껍질은 가장 가까운 층에만 그림
- 회화풍은 풍경에서 가장 효과가 큼
    + `importance` 없이 `finish(painting, style)`만으로 충분

## 동물과 사물

- 몸통, 머리, 다리, 꼬리를 각각 닫힌 곡선으로 그려 뒤에서 앞으로 쌓음
    + 다리와 꼬리는 `geo.tube`, 귀와 부리는 `geo.smooth`의 `corners`
- 여러 조각이 한 몸으로 이어져야 하면 마스크를 합쳐 1회만 외곽선 처리
    + `mask = sh.melt(np.maximum(a, b), 6)` 후 `painting.outline_mask(mask, width, color)`
- 눈은 타원 3겹(흰자 또는 홍채, 동공, 반사광)
- 털과 깃은 가장자리에만 `geo.lock`으로 삐침을 추가

## 두머 장면 부품

- 패널 아파트 면은 `scenery.panel_facade(painting, quad, floors, bays, ...)` 1회 호출
    + 2점 투시는 정면 사각형과 옆면 사각형을 같은 모서리로 이어 2회 호출, 옆면은 `shade=0.5` 안팎
    + 위에서 내려다본 단지는 정면, 지붕, 옆면 3개 사각형의 사투상 상자로 쌓고 먼 줄부터 그린 뒤 줄마다 안개색을 덧칠
- 송전탑은 위로 좁아지는 두 다리, 층마다 X자 가새, 위쪽 가로팔 2개, 가로팔 끝끼리 `scenery.wire`로 연결
    + 가로팔 폭은 탑 높이의 0.35-0.5배, 더 넓으면 십자가처럼 보임
- 굴뚝은 위로 좁아지는 띠 9개를 붉은색과 흰색으로 번갈아 칠하고 연기는 `scenery.puffs`를 바람 방향으로 키우며 이어 붙임
- 창 너머 풍경은 별도 `Painting`에 그려 유리 마스크로만 옮김, 직접 그리면 창틀 밖 벽까지 덮임
- 겨울 땅은 밝은 눈 위에 `fx.fbm` 진창 얼룩, 화면 아래로 갈수록 어스름, 발자국은 경로를 따라 좌우 번갈아 찍음
