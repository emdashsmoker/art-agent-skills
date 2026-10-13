# 화풍 렌더러

4개 화풍은 같은 레이어를 입력받는다. 차이는 합성 방식뿐이다.

공통 규칙:
- 그룹 `bg`, `lash`, `brow`, `sky`, `emissive`, `scenery`, `screen`은 음영을 받지 않는다(디자인된 색 또는 자체 발광).
- 그룹 `body`(마네킹 인체)의 그림자는 화풍 합성 전에 정리된다(`styles.simplify_shadow`).
    + 그림자 사이의 좁은 빛 틈은 회색조 닫힘 연산으로 메운다(`SHADOW_SIMPLIFY`)
    + 그림자에 둘러싸인 작은 빛 섬은 밝은 중심부(`LIT_CORE`)로 찾아 둘레 테두리(`ISLAND_HALO`)까지 그림자로 합친다(`SHADOW_HOLE_AREA`)
    + 실루엣을 따라가는 얇은 명암 경계 띠는 실제 형태이므로 열림 연산으로 지우지 않는다
    + 애니메 셀에서 몸의 자기 그림자 경계는 디자인 그림자보다 좁은 폭으로 끊는다(`BODY_SHAPE_EDGE`)
- 그룹 `bg`, `sky`는 배경(backdrop)으로 취급된다. 유화는 배경을 따로 크게 칠하고, 수채는 배경 가장자리에 종이 여백을 남긴다.
- 마네킹 형태(몸, 손, 정물)는 깊이 기반 법선과 자기 그림자, 블린 광택을 레이어로 넘긴다. 화풍은 이를 그대로 사용한다.

## 목차
- 애니메 셀
- 소프트 일러스트
- 유화
- 수채
- 색보정 룩
- 공통 튜닝 순서

## 애니메 셀 (`styles.render_anime`)

디지털 셀 작화의 레이어 스택(밑색, 곱하기 그림자, 스크린 하이라이트, 선화)을 그대로 재현한다.

- 그림자 = 형태 음영, 캐스트 섀도, 디자인된 그림자 도형 3개의 최댓값
    + 형태 음영은 법선 내적이 `cel_threshold`보다 작은 곳에 1-2px 안티앨리어싱 경계로 적용
    + 머리카락에만 2단 셀(더 깊은 그림자)을 추가하여 층감을 표현
- 하이라이트는 빛을 받는 면에서만 단단한 경계로 표시
- 선화는 마지막에 덮음

튜닝 지점:
- 그림자 면적: 명세 `cel_threshold.<그룹>`
- 그림자 색: 명세 `shadow_tint.<그룹>`
- 경계 부드러움: `styles.CEL_EDGE`

## 소프트 일러스트 (`styles.render_illustration`)

라이트 노벨 표지 계열의 부드러운 채색이다.

- 형태 음영을 0.4 폭의 그라데이션으로 전환
- 캐스트 섀도 주변에 넓은 블러를 약하게 더해 접촉 그림자 표현
- 광원 반대편 실루엣에 림 라이트(명세 `light.rim_color`, `light.rim_strength`)
- 선화 불투명도 0.85, 밝은 부분 블룸, 그림자 남보라 및 하이라이트 크림 색조 보정, 미세 그레인

공용 함수 `styles.soft_shaded`가 선화 이전 단계까지 담당하며 유화도 이 함수를 재사용한다.

## 유화 (`painterly.render_oil`)

Hertzmann(1998) 다중 크기 곡선 붓터치 알고리즘을 바탕으로 4개 공정을 추가했다.

1. 바탕칠: 화면 평균색을 어둡게 한 단색 바탕
2. 배경 블로킹: 캔버스 폭 기준 큰 붓 3단계(`OIL_BG_BRUSHES`, 장면은 더 작은 `OIL_SCENE_BG_BRUSHES`)로 배경만 칠함
3. 인물 밑칠과 붓터치: 재질 경계 안에서만 흐린 밑색을 깐 뒤 머리 폭 기준 붓 4단계(`OIL_FIG_BRUSHES`)로 덮음
    + 붓터치는 구조 텐서 방향장을 따라 휘어지며 재질 경계에서 멈춤(외곽 오려내기)
    + 가장 가는 붓은 피부와 이목구비에만 사용
4. 마감: 눈과 입술은 정밀 렌더를 65% 남기고(`OIL_DETAIL_KEEP`), 에지 밀도가 높은 곳(창문 격자, 손가락, 과일 테두리)은 40%를 남김(`OIL_BUSY_KEEP`). 이후 선 적분 합성(LIC)으로 붓털 자국, 명도 기반 임파스토 요철과 캔버스 직조 조명

튜닝 지점:
- 붓터치가 거칠면 `OIL_FIG_BRUSHES`를 줄이고, 매끈하면 키움
- 붓터치 수가 과하면 `OIL_ERROR_T`를 높임(색 지터보다 커야 무한 덧칠을 막음)
- 얼굴이 너무 회화적이면 `OIL_SKIN_KEEP`, `OIL_DETAIL_KEEP`를 높임
- 작은 디테일이 뭉개지면 `OIL_BUSY_KEEP`을 높임
- 소요 시간은 붓터치 수에 비례. 1024 x 1280 바스트업 약 12초, 1400 x 900 장면 약 8-12초

## 수채 (`painterly.render_watercolor`)

Bousseau 외(2006) 안료 밀도 모델을 바탕으로 수채의 물리 현상 5개를 흉내 낸다.

| 현상 | 구현 | 상수 |
|---|---|---|
| 투명 레이어 | 밑색을 10% 밝힌 뒤 그림자를 글레이즈로 곱함 | 코드 내 0.10, 0.85 |
| 가장자리 착색 | 각 재질 영역 경계 안쪽에 안료 밀도 증가 | `WC_EDGE_DARKEN` |
| 번짐 얼룩 | 저주파 노이즈로 밀도 변조 | `WC_TURBULENCE` |
| 입자 침전 | 고주파 노이즈로 밀도 변조 | `WC_GRANULATION` |
| 경계 흔들림 | 노이즈 변위로 영역 경계 왜곡 | `WC_WOBBLE_PX` |

추가 공정:
- 하이라이트는 물감을 걷어낸 종이색으로 표현
- 배경 워시는 불규칙한 여백을 남기고 멈춤
- 종이 섬유 질감, 연필 밑선(`WC_PENCIL`), 이목구비만 진한 선 보강

## 색보정 룩 (`looks.apply_look`)

명세 `look`은 화풍 렌더가 끝난 이미지 전체에 1회 적용된다. 레이어를 읽지 않으므로 4개 화풍에 같은 방식으로 걸린다.

`doomer`(`looks.DOOMER`) 처리 순서:
1. 채도를 `saturation`(0.46)까지 낮춘다. 붉은빛이 강하고(`warm_hue`) 밝은(`warm_value`) 화소는 `warm_saturation`(0.95)까지 채도를 남겨 가로등, 켜진 창, 백열등만 주황으로 남는다
2. 어두운 톤일수록 `shadow_tint`를 곱해 그림자를 푸르게 만든다. 따뜻한 불빛 화소는 제외한다
3. 대비를 `contrast`로 줄이고 검정을 `lift`(회청색)까지 띄워 바랜 필름처럼 만든다
4. 모서리를 `vignette`만큼 어둡게 하고 `grain` 세기의 휘도 노이즈를 `grain_blur`로 살짝 뭉쳐 더한다. 노이즈 시드는 `canvas.seed`에서 나온다

튜닝: 피부가 잿빛이면 `saturation` 상향, 불빛이 탁하면 `warm_value` 하한 하향, 그레인이 거칠면 `grain` 하향.

## 공통 튜닝 순서

1. 형태가 틀리면 리그(명세 `character.*`)부터 고친다. 화풍은 형태 결함을 가리지 못한다.
2. 명암이 틀리면 광원(`light.direction`)과 `cel_threshold`를 고친다.
3. 색이 틀리면 `palette`와 `shadow_tint`를 고친다.
4. 질감이 틀리면 화풍 상수를 고친다.

화풍 상수는 이미지 크기에 비례하도록 정의되어 있다. 유화 인물 붓은 머리 폭, 배경 붓은 캔버스 폭 기준이다.

## 참고 문헌

- Hertzmann, A. (1998). Painterly Rendering with Curved Brush Strokes of Multiple Sizes. SIGGRAPH.
- Bousseau, A., Kaplan, M., Thollot, J., Sillion, F. (2006). Interactive Watercolor Rendering with Temporal Coherence and Abstraction. NPAR.
- Cabral, B., Leedom, L. (1993). Imaging Vector Fields Using Line Integral Convolution. SIGGRAPH.
