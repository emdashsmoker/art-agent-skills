# 화풍 레시피

화풍은 `scripts/codepainter/styles.py`의 `Style` 수치 묶음. 장면 코드는 화풍에게 선 굵기와 음영 방식을 물어서 그리므로 수치만 바꾸면 같은 장면이 다른 화풍으로 나온다.

## Style 항목

| 항목 | anime | illust | painterly | 의미 |
|---|---|---|---|---|
| `line_width` | 1.0 | 0.62 | 0.0 | 외곽선 굵기 배율, 0은 선 없음 |
| `line_tint` | 0.35 | 0.75 | 1.0 | 선 색이 조각 색을 닮는 정도 |
| `line_opacity` | 1.0 | 0.9 | 0.0 | 최종 합성 시 선 불투명도 |
| `edge_softness` | 0.015 | 0.10 | 0.22 | 그림자 경계 부드러움 |
| `shadow_threshold` | 0.30 | 0.30 | 0.34 | 그림자 시작 기준, 높을수록 그림자 넓음 |
| `shadow_depth` | 0.85 | 0.80 | 0.95 | 그림자 진하기 |
| `second_tone` | 0.0 | 0.45 | 0.55 | 더 어두운 2차 음영 |
| `gradient` | 0.10 | 0.45 | 0.70 | 부드러운 입체 그라데이션 |
| `cast_softness` | 0.0 | 3.0 | 6.0 | 드리운 그림자 번짐 |
| `rim` | 0.35 | 0.75 | 0.55 | 림라이트 |
| `highlight` | 1.0 | 0.85 | 0.6 | 하이라이트 |
| `blush` | 0.45 | 0.75 | 0.8 | 피부 홍조 |
| `strands` | 0.35 | 1.0 | 0.8 | 머리카락 가닥 밀도 |
| `terminator` | 0.0 | 0.6 | 0.8 | 피부 그림자 경계의 붉은 띠 |
| `shadow_tint` | 연보라 | 보라 | 짙은 보라 | 그림자 곱하기 색 |

## 조정

```python
style = get_style("anime", line_width=1.3, rim=0.0)       # 프리셋에서 일부 수치만 변경
```

- 프리셋 이름은 `finish`의 후보정 분기에 쓰이므로 변형 화풍도 기반 프리셋의 후보정을 따름
- 검증된 변형은 아래 표 참조

| 목표 | 설정 |
|---|---|
| 선이 굵은 만화풍 | `get_style("anime", line_width=1.4, highlight=0.8)` |
| 선 없는 플랫 포스터풍 | `get_style("anime", line_width=0.0, line_opacity=0.0, strands=0.0)` |
| 음영이 짙은 극화풍 | `get_style("anime", shadow_threshold=0.42, shadow_depth=1.0, second_tone=0.5)` |
| 맑고 옅은 수채 삽화풍 | `get_style("illust", shadow_depth=0.55, line_opacity=0.6, gradient=0.6)` |
| 선이 남은 회화풍 | `get_style("painterly", line_width=0.5, line_opacity=0.5)` |

## 후보정 구성

| 화풍 | `finish` 내부 순서 |
|---|---|
| anime | 확산광, 색 보정, 옅은 입자 |
| illust | 블룸, 확산광, 명부와 암부 색조, 종이 질감, 비네트, 입자 |
| painterly | 붓질 재도장, 색 보정, 비네트 |

- 강도를 직접 정하려면 `painting.flatten(style.line_opacity)` 결과에 `fx` 함수를 개별 적용

```python
image = painting.flatten(style.line_opacity)
image = fx.glow(image, radius=12, strength=0.10)
image = fx.grade(image, contrast=1.08, saturation=1.1, shadows=("#2a2a50", 0.12))
painting.save("out.png", fx.grain(image, 0.01))
```

## 회화풍 붓질

- 원리는 큰 붓에서 작은 붓 순서의 다층 도장
    + 각 층은 현재 캔버스와 원본의 색 차이가 큰 칸에만 붓질 추가
    + 붓질은 형태의 가장자리 방향을 따라 흐름
- 평평한 영역은 큰 붓 자국이 남고 세부가 있는 영역만 작은 붓으로 정리됨
    + 따라서 원본 그림의 명암과 색 덩어리가 분명할수록 결과가 좋음

| 옵션 | 기본값 | 효과 |
|---|---|---|
| `importance` | None | 값이 1인 영역은 가는 붓으로 정밀 묘사 |
| `detail` | 1.0 | 1 초과는 전체를 세밀하게, 1 미만은 거칠게 |
| `bristle` | 1.0 | 붓털 결 강도 |
| `impasto` | 1.0 | 물감 두께의 요철 강도 |
| `canvas` | 1.0 | 캔버스 직조 질감 강도 |
| `ground` | 자동 | 붓질 틈으로 비치는 바탕색 |
| `seed` | 0 | 붓질 배치 난수 |

```python
image = finish(painting, style, importance=masks["head"], detail=1.2, impasto=1.4)   # 두껍고 세밀한 유화
image = finish(painting, style, detail=0.7, bristle=0.5, canvas=0.3)                 # 거칠고 매끈한 과슈
```

- 붓 크기 구성은 `painterly.BRUSH_LAYERS`의 `BrushLayer(radius, threshold, steps, jitter, focus_only)` 목록
    + `layers=`에 다른 목록을 전달하면 교체 가능
    + `jitter`는 `threshold / 3` 미만으로 유지해야 붓질이 무한히 덧칠되지 않음

## 신규 화풍

```python
from codepainter.styles import Style
NOIR = Style(name="anime", line_width=1.2, line_tint=0.0, line_opacity=1.0, edge_softness=0.01,
             shadow_threshold=0.45, shadow_depth=1.0, second_tone=0.0, gradient=0.0, cast_softness=0.0,
             rim=0.6, highlight=0.7, blush=0.0, strands=0.2, terminator=0.0, shadow_tint=(0.35, 0.35, 0.45))
```

- `name`은 후보정 분기를 정하므로 `anime`, `illust`, `painterly` 중 1개 지정

## 두머 무드

스킬의 서명 화풍. 화풍 3종 어디에든 마지막에 덧입히는 무드다.

- 핵심 메시지 : 차갑고 끝없이 반복되는 콘크리트 세계 속 따뜻한 불빛 하나
- 판단 기준 : 차가운 반복 구조가 화면을 지배하고 유일한 따뜻한 빛이 시선을 붙잡는가

```python
from codepainter import fx, scenery, sets
painting = Painting(1536, 1024)
info = sets.SETS["panel_block"](painting, style, lamp=0.53)       # 흐린 하늘, 패널 아파트, 눈 덮인 마당, 나트륨등
scenery.snowfall(painting, 1400, seed=3)                          # 인물이 있으면 인물을 그린 뒤 호출
image = fx.doomer(finish(painting, style), seed=3)
```

| 요소 | 규칙 |
|---|---|
| 색 | 청회색 저채도 1계열, 강조색은 따뜻한 주황 1계열(켜진 창, 가로등, 낮은 해, 차 한 잔) |
| 빛 | 따뜻한 빛은 `mode="normal"`로 칠함, 밝은 눈 위에 `screen`으로 칠하면 흰색으로 날아가 무드 보정에서 탈색됨 |
| 건물 | `scenery.panel_facade`로 패널 이음매, 창 격자, 발코니, 계단실을 그림, 켜진 창은 15-30% |
| 인물 | 검은 옷(`look(..., outfit="doomer")`), 비니(`hat="beanie"`), 처진 눈과 내려간 시선(`head_tilt`), 화면 3분의 1 지점 |
| 날씨 | 흐린 하늘, 눈 덮인 땅과 회색 진창, `scenery.snowfall`, 앙상한 나무 `scenery.bare_tree` |

- `fx.doomer(image, seed, strength)` 순서 : 채도 낮춤, 청록 그늘과 바랜 명부, 검정 들어 올림, 비네트, 굵은 입자
    + `fx.warm_lights(image)`가 0인 곳은 채도 `fx.DOOMER["saturation"]`, 1인 곳은 `warm_saturation`
    + 따뜻한 빛 판정은 빨강에서 파랑을 뺀 값 `fx.WARM_EDGES`와 밝기 `fx.LIT_EDGES`, 피부는 일부만 색 유지
- 화풍 선택 기준
    + 인물 얼굴이 주인공이면 애니메나 일러스트, 공간과 공기가 주인공이면 회화풍
- 완성 예제 `scripts/examples/doomer.py`의 7컷

| 컷 | 화풍 | 구성 |
|---|---|---|
| `man` | 일러스트 | 단지 마당 가로등 옆 허리 컷, 비니와 후드티 |
| `woman` | 애니메 | 밤 단지 앞 흉상, 검은 터틀넥, 앞머리 |
| `pair` | 애니메 | 가로등을 사이에 두고 서로 반대쪽을 보는 두 사람 |
| `establishing` | 회화풍 | 두 동 사이 마당, 놀이터 철골, 가로등 아래 작은 뒷모습과 발자국 |
| `city` | 일러스트 | 높은 곳에서 본 아파트 열, 줄무늬 굴뚝과 연기, 전깃줄 |
| `landscape` | 회화풍 | 눈 들판, 자작나무, 지평선까지 이어진 송전탑, 낮은 해 |
| `still_life` | 회화풍 | 밤 부엌 창턱, 유리 찻잔과 금속 컵받침, 카세트, 유선 이어폰 |

- 특정 앨범 커버, 사진, 밈 캐릭터의 구도와 형태는 옮기지 않고 장르 요소만 조합
