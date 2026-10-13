# 화풍

## 세 화풍의 차이

| 항목 | `anime` | `illust` | `painterly` |
|---|---|---|---|
| 외곽선 | 가는 색선 | 없음 | 없음 |
| 명암 경계 | 또렷한 2단 | 또렷한 2단, 약함 | 연속 계조 |
| 직접 넣은 그림자와 빛 | 모양 그대로 | 모양 그대로 | 가장자리가 풀림 |
| 형태 그림자의 폭 | `bulge` 그대로 | `bulge` 그대로 | `bulge`의 2.2배 |
| 가장자리 | 매끈 | 손으로 자른 듯 흔들림 | 실루엣은 깨끗하고 면 안쪽은 붓 자국 |
| 질감 | 옅은 입자 | 종이 색, 얼룩, 인쇄 입자 | 납작붓 자국, 붓털 결, 물감 요철, 캔버스 결 |
| 빛 처리 | 블룸, 확산광 | 없음 | 밝은 면에 따뜻한 빛 추가 |
| 1024px 렌더링 시간 | 6초 | 4초 | 14초 |

## 고르는 기준

| 요청에 담긴 말 | 화풍 |
|---|---|
| 애니, 만화, 셀화, 선이 깔끔한, 캐릭터 설정화 | `anime` |
| 일러스트, 그림책, 포스터, 표지, 플랫, 과슈, 리소 | `illust` |
| 회화, 유화, 인상파, 붓 터치, 임파스토 | `painterly` |

말이 없으면 인물은 `anime`, 풍경은 `painterly`를 먼저 시도한다.

## 화풍별 작화 요령

### anime

- 선이 품질을 좌우한다
    + 최종본은 2048px로 그리고 `downscale=2`로 저장한다
- 그림자 모양을 직접 설계한다
    + 머리카락 아래, 턱 아래, 깃 아래의 드리운 그림자 3개가 기본이다
- 하이라이트는 작고 또렷하게 넣는다
    + 눈, 머리카락 윤기, 입술, 금속

### illust

- 선이 없으므로 색 면의 대비로 형태를 구분한다
    + 맞닿는 두 부품의 명도를 뚜렷이 다르게 정한다
- 세부를 줄이고 면을 키운다
- 가는 획은 입자에 묻히므로 3 단위 이상의 굵기로 쓴다

### painterly

- 명도 차이를 넓게 잡는다
    + 붓질이 세부를 뭉개므로 큰 명암 덩어리가 형태를 전달한다
- 초점 영역을 반드시 지정한다
    + 얼굴 전체에 0.6, 눈과 입에 1.0을 준다
    + 정물의 사물과 인물의 몸에는 0.6-0.7을 준다
    + 지정하지 않은 곳은 큰 붓 자국으로 남는다
- 붓질은 색이 비슷한 영역 안에서만 칠해진다
    + 실루엣은 깨끗하게 남고 면 안쪽에만 붓 자국이 생긴다
    + 맞닿은 두 면의 색 차이가 작으면 경계가 붓질에 묻힌다
- 1 단위 굵기의 가는 획은 사라진다

## 새 화풍 만들기

`Style`은 불변 데이터 클래스다. 기존 화풍에서 값만 바꿔 파생한다.

```python
from dataclasses import replace
from atelier import ANIME

BOLD_INK = replace(ANIME, name="bold-ink", line_width=1.8, line_local_color=0.0, ink="#111111")
art = Art(BOLD_INK, ...)
```

| 필드 | 뜻 |
|---|---|
| `shade_mode` | `ShadeMode.CEL` 또는 `ShadeMode.SOFT` |
| `shade_strength` | 그림자 색이 적용되는 세기 |
| `form_scale` | `bulge`에 곱하는 배율 |
| `softness` | 직접 넣은 그림자와 빛의 가장자리를 푸는 반경 |
| `line_opacity` | 0이면 외곽선과 `art.line()`이 생략됨 |
| `line_width` | 모든 선 굵기의 배율 |
| `line_local_color` | 0이면 잉크 색만, 1이면 부품 색을 어둡게 한 색만 사용 |
| `ink` | 잉크 색 |
| `finish` | `Finish.ANIME`, `Finish.ILLUST`, `Finish.PAINTERLY` 중 후보정 선택 |

후보정의 세기는 `scripts/atelier/finish.py` 상단의 상수로 조절한다.

| 상수 | 효과 |
|---|---|
| `BLOOM_STRENGTH` | 애니메풍의 빛 번짐 |
| `WOBBLE_AMPLITUDE` | 일러스트풍의 가장자리 흔들림 |
| `SPECKLE_AMOUNT`, `ILLUST_GRAIN` | 일러스트풍의 입자 |
| `BRUSH_RADII` | 회화풍의 붓 크기 (큰 붓에서 작은 붓 순) |
| `BRUSH_ERROR_THRESHOLD` | 낮추면 작은 붓질이 늘어 세밀해짐 |
| `BRUSH_EDGE_TOLERANCE` | 높이면 붓질이 색 경계를 넘어 번짐 |
| `IMPASTO_AMOUNT` | 물감 요철의 세기 |

## 분위기 층

화풍 마감 뒤에 한 번 더 씌우는 색 보정이다. 세 화풍 어디에나 씌운다 (`scripts/atelier/mood.py`).

```python
from atelier.mood import doomer
art.grade = doomer          # compose("final")과 save()가 마감 뒤에 적용
```

- `art.grade`의 기본값은 `None`이다. 비워 두면 그림이 바뀌지 않는다
- 분위기 1개는 `grade(image, ppu, rng) -> image` 함수 1개다. 0-1 RGB 배열을 받아 돌려준다
- `GRADES`에 이름으로 모아 둔다
- `doomer`: 늦은 밤의 차갑고 빛바랜 사진

| 상수 | 효과 |
|---|---|
| `DOOMER_SATURATION` | 남기는 색의 비율 |
| `DOOMER_SHADOW`, `DOOMER_HIGHLIGHT`, `DOOMER_SPLIT` | 어두운 곳은 푸른 회색으로, 밝은 곳은 바랜 종이색으로 기울임 |
| `DOOMER_FADE`, `DOOMER_CONTRAST` | 검정을 들어 올려 빛바랜 필름처럼 만듦 |
| `DOOMER_VIGNETTE`, `DOOMER_VIGNETTE_START` | 모서리를 어둡게 함 |
| `DOOMER_GRAIN`, `DOOMER_GRAIN_SIZE` | 덩어리진 필름 입자 |

- 회화풍은 붓질이 가는 선과 작은 점을 덮는다
    + 전선, 송전탑, 잔가지는 `scenes.keep_fine_lines(art)`로 초점에 넣는다
    + 눈송이는 `scenes.snowfall()`이 초점에 넣는다
- 장면도 같은 분위기로 고른다
    + 밤, 눈, 나트륨 가로등의 주황 빛, 불이 드문 창, 검은 옷, 담배 연기
    + 예제: `examples/doomer.py` 7종 (남성, 여성, 투샷, 세계관 컷, 도시화, 풍경화, 사물화)
