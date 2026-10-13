# 화풍 레시피

## 목차

- 공통 구조
- 애니메
- 일러스트
- 회화
- 색보정
- 새 화풍 추가

## 공통 구조

- 화풍은 `config.Style` 1개와 `finish.py`의 마감 함수 1개로 구성
    + `Style`은 그리는 도중의 음영 방식과 선을 결정
    + 마감 함수는 그림 전체의 표면(빛, 입자, 붓질)을 결정
- 장면 스크립트는 화풍 이름만 전달
    + 동일 작도가 3개 화풍으로 분기되므로 인물 데이터를 화풍마다 다시 만들지 않음

| `Style` 필드 | 의미 |
|---|---|
| `shade_mode` | `CEL`(2단) 또는 `SOFT`(연속) |
| `line_width` | 외곽선 굵기(캔버스 단위), 0이면 선 없음 |
| `line_opacity` | 외곽선 불투명도 |
| `shadow_edge` | 드리운 그림자 가장자리의 흐림(캔버스 단위) |
| `shadow_opacity` | 그림자 농도 |
| `cel_threshold` | 셀 그림자가 시작되는 빛의 비율 |
| `detail_line_opacity` | 머리카락 가닥과 옷주름의 농도 |

## 애니메

- (그리기) 2단 셀 음영, 색 선화, 톱니 모양 머리카락 광택
- (마감) `finish._finish_anime`
    + 인물 전체에 차가운 색의 부드러운 그라데이션(`AIRBRUSH_SHADE`, `AIRBRUSH_STRENGTH`)
    + 광원 쪽 실루엣에 림라이트(`RIM_SHIFT_UNITS`, `RIM_STRENGTH`)
    + 밝은 영역의 블룸(`BLOOM_THRESHOLD`, `BLOOM_RADIUS_UNITS`, `BLOOM_STRENGTH`)
    + 채도 보정과 미세 입자
- (조정) 선이 가늘면 `line_width`를 2.3에서 3.0으로, 그림자가 넓으면 `cel_threshold`를 0.80에서 0.72로

## 일러스트

- (그리기) 연속 음영, 선 없음, 매끈한 머리카락 광택, 입술을 면으로 표현
- (마감) `finish._finish_illust`
    + 저주파 노이즈로 가장자리를 1-2 단위 흔들어 손으로 자른 느낌 부여(`EDGE_WOBBLE_UNITS`)
    + 종이 섬유와 입자를 곱함(`PAPER_GRAIN`)
    + 채도를 소폭 낮춤
- (조정) 평면적 인상이 필요하면 `shadow_opacity`를 0.72에서 0.5로

## 회화

- (그리기) 일러스트와 동일한 연속 음영 원화
- (마감) `finish._finish_painterly`
    + 광원 반대편을 깊게 가라앉히는 명암 대비(`CHIAROSCURO_SHADE`, `CHIAROSCURO_STRENGTH`)
    + 감마와 따뜻한 색조로 유화의 중간 톤 확보(`PAINT_GAMMA`, `PAINT_WARMTH`)
    + `brushwork.paint()`가 원화를 붓질로 재구성
- (붓질 알고리즘) 큰 붓에서 작은 붓 순으로 6개 층(반지름 30, 15, 7.5, 3.6, 1.8, 0.9 단위)을 쌓음
    + 각 층은 원화를 붓 크기만큼 흐린 뒤 현재 그림과의 색 차이가 큰 곳에만 획을 놓음
    + 획은 밝기 기울기에 수직인 방향, 즉 윤곽을 따라 진행
    + 가장 가는 3개 층은 중요도 지도가 0.25, 0.80, 0.95 이상인 곳에만 적용(`DETAIL_FLOOR`)
    + 눈과 입은 중요도 1.0, 얼굴은 크기에 따라 0.5에서 1.0(`finish.SMALL_FACE_UNITS`): 보이는 얼굴 폭이 100 단위 이하면 1.0, 160 단위 이상이면 0.5
    + 따라서 장면 속 작은 인물도 가장 가는 붓으로 눈, 눈썹, 입을 그리고 큰 초상은 v5와 같은 붓질을 유지
    + 3D 장면의 손 크기 사물은 `Prop3D.detail` 0.85로 가장 가는 붓까지 받아 자판과 화면이 뭉개지지 않음
    + 획마다 물감 두께를 기록한 뒤 빛을 비춰 요철을 표현
- (조정) 상수는 `brushwork.py` 상단
    + 거친 그림은 `BRUSH_RADII_UNITS`의 마지막 값을 제거하고 `STROKE_STEPS`를 늘림
    + 요철은 `IMPASTO_STRENGTH`, 캔버스 결은 `CANVAS_WEAVE_STRENGTH`
- (출처) 다층 붓질 기법은 아래 논문의 방법을 따름

> Hertzmann(1998), Painterly Rendering with Curved Brush Strokes of Multiple Sizes, SIGGRAPH 98(https://dl.acm.org/doi/10.1145/280814.280951)

## 색보정

- 화풍 마감 뒤에 얹는 별도 단계(`grade.apply`)이며 3개 화풍 모두와 조합
    + 순서는 번짐(밝은 빛 둘레의 주황 헐레이션), 채도, 분할 톤(그늘과 밝은 곳의 색 기울기), 바램과 대비, 비네팅, 필름 입자
- 두머 프리셋은 `doomer`(밤)와 `doomer_day`(흐린 낮)
    + `doomer`: 채도 0.55배, 그늘 청록 `#1E4650`, 밝은 곳 주황 `#F2A866`, 검정 0.07 올림, 대비 0.88, 입자 0.034
    + `doomer_day`: 채도 0.45배, 그늘 `#2E4A50`, 밝은 곳 `#DCD8C8`, 검정 0.10 올림, 번짐 약함
- 따뜻한 프리셋은 `cozy_night`(방 안의 밤), `late_sun`(늦은 오후 창가), `golden_hour`(야외 노을)
    + 공통 값은 채도 0.92-0.95배, 검정 0.03 올림, 대비 0.96-0.97, 입자 0.014-0.016이며 필름 느낌만 남김
    + `cozy_night`: 그늘 남색 `#24305C`, 밝은 곳 `#FFD6A0`, 번짐 문턱 0.78
    + `late_sun`: 그늘 `#3A4E70`, 밝은 곳 `#FFDDA8`, 비네팅 0.22
    + `golden_hour`: 그늘 보라 `#3A3466`, 밝은 곳 `#FFC88C`, 번짐 문턱 0.88(밝은 얼굴은 번지지 않음)
- 장면 기본값은 `run_cli(..., grade="doomer")`, 명령행 `--grade none|doomer|doomer_day|cozy_night|late_sun|golden_hour`로 교체
- 새 색보정은 `grade.Grade(...)` 값을 만들어 `grade.GRADES`에 등록
- 내리는 눈처럼 붓질과 선이 건드리면 안 되는 효과는 `canvas.overlays`에 넣어 마감과 색보정 사이에 그림

## 새 화풍 추가

1. `config.StyleName`에 이름을 추가
2. `config.STYLES`에 `Style` 값을 추가
3. `finish.py`에 마감 함수를 작성하고 `apply()`의 분기에 연결
    + 분기에 없는 화풍은 오류를 내므로 누락이 드러남
4. `scene_template.py`의 `compose()`에 배경 분기를 추가
5. `selftest.py` 실행 후 미리보기 확인
