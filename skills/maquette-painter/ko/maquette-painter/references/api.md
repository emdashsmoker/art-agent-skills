# 저수준 API

## 목차
- 모듈 지도
- Canvas
- geom (경로)
- Gradient와 색
- 조명과 렌더
- studio와 qa
- 직접 그리기 요령

## 모듈 지도

| 모듈 | 역할 |
|---|---|
| `core` | Canvas(구조 버퍼), Light, Gradient, 색 유틸리티 |
| `geom` | 경로 생성 (곡선, 테이퍼 선, 도형, 불리언) |
| `figure`, `character`, `head`, `hair`, `wardrobe` | 인물 |
| `ensemble` | 여러 인물의 공유 공간, 인물 간 접촉, 겹침, 그림자 |
| `scenery`, `city`, `objects`, `props`, `sculpt` | 풍경, 도시, 정물, 현대 사물, 커스텀 덩어리 |
| `media`, `styles`, `finish` | 매체 렌더, 화풍 프리셋, 마감 |
| `brief`, `compose`, `palette` | 기획, 구도, 색 계획 |
| `studio`, `qa` | 실행 루프, 검수 도구 |

- 일반적인 임포트: `from atelier import Brief, Canvas, Gradient, Light, Figure, Hair, Ensemble, Sculpture, city, compose, geom, palette, qa, scenery, objects, props, wardrobe, studio, paint, light`

## Canvas

```python
canvas = Canvas(width, height, scale=1.0, seed=0, paper="#ffffff")     # 보통은 brief.canvas()로 생성
```

- width, height는 디자인 단위. 실제 픽셀은 scale 배
- 구조 버퍼: albedo(고유색), normal(형태), region(영역), depth(깊이), shadow(드리운 그림자), occlusion(접촉 그림자), soft(부드러운 재질), unlit(조명 제외), gloss(광택), line(선화), over(최종 강조), group(매체 그룹), focus(초점)

### 그리기 메서드

| 메서드 | 용도 |
|---|---|
| `add(shape, fill, region, ...)` | 불투명한 형태 1개 (고유색, 형태, 그림자, 외곽선) |
| `tint(shape, color, alpha, blur, clip)` | 고유색만 덧칠 (홍조, 무늬, 색 변화) |
| `shade(shape, amount, blur, clip)` | 그림자 형태를 직접 지정 (빛이 가려진 곳) |
| `occlude(shape, amount, blur, clip)` | 접촉 그림자 (빛 방향과 무관하게 어두운 틈, 닿는 자리) |
| `ink(shape, color, stroke, alpha, clip)` | 선화 층에 형태 또는 외곽선 추가 (화풍의 line_strength를 따르므로 선을 흐리게 하는 화풍에서는 옅어짐) |
| `stroke(points, width, color, start, end, peak, alpha, clip)` | 굵기가 변하는 펜 선 |
| `accent(shape, color, alpha, clip, blur)` | 매체 위에 또렷하게 남는 강조 (눈의 반사광, 반짝임, 가로등 빛무리, 연기). alpha와 blur 가장자리가 그 비율 그대로 섞임 |
| `focus_on(shape, amount, blur)` | 가장 세밀하게 그릴 영역 지정 |
| `mask(shape, clip)` | 경로의 영역 마스크 (clip으로 재사용) |
| `layer(depth, group)` | with 블록 안의 요소에 깊이와 매체 그룹 지정 |
| `region_mask(*names)` | 이름으로 영역 마스크 조회 |
| `grid()`, `noise(scale, octaves)` | 좌표 격자, 부드러운 노이즈 (넘파이 마스크 제작) |

### add의 인자

```python
canvas.add(shape, fill="#808080", region=None, form="flat", bulge=None, relief=1.0, normal=None,
           unlit=False, gloss=0.0, cast=None, outline=None, clip=None, alpha=1.0, depth=None, group=None,
           keep_normal=0.0, soft=0.0)
```

| 인자 | 의미 |
|---|---|
| shape | `geom` 경로 또는 캔버스 크기의 넘파이 마스크(0-1) |
| fill | 색상 코드, RGB 튜플, `Gradient`, 또는 캔버스 크기의 RGB 배열 |
| region | 영역 이름 (같은 이름은 같은 영역) |
| form | flat 평면, round 둥글게 부푼 형태 |
| bulge | round의 모서리 둥글림 반경. None이면 전체가 돔 형태 |
| relief | 입체감 강도 |
| normal | 평면의 방향 `(nx, ny, nz)` 또는 법선 맵 배열. 바닥은 `(0, -0.8, 0.6)`, 정면 벽은 `(0, 0, 1)` |
| unlit | True이면 조명을 받지 않고 칠한 색 그대로 (하늘, 발광체, 평면 디자인) |
| gloss | 광택 0-1 |
| cast | `(dx, dy, blur, strength)` 아래 층에 그림자를 드리움 |
| outline | 선폭 또는 `(선폭, 색)`. 색을 생략하면 채움색에서 추출 |
| clip | 이 경로 또는 마스크 안에만 그림 |
| keep_normal | 아래 형태의 입체를 유지하는 비율 (피부 위 무늬, 머리 위 가닥) |
| soft | 부드러운 재질 0-1 (빛이 더 깊이 감싸고 명암 경계에 따뜻한 기운, 피부와 구름) |

- 나중에 그린 형태가 먼저 그린 형태를 덮음 (선화와 그림자 포함)
- 좌표는 x 오른쪽, y 아래쪽

## geom (경로)

| 함수 | 용도 |
|---|---|
| `runs([[p0, p1, ...], [...]])` | 부드러운 구간들의 연결. 구간 경계는 뾰족한 모서리 |
| `blob(points)` | 모든 점을 지나는 매끈한 닫힌 곡선 |
| `polygon(points)` | 직선 다각형 |
| `ellipse(cx, cy, rx, ry, angle)`, `rect(x0, y0, x1, y1, radius)` | 기본 도형 |
| `taper(points, width, start, end, peak)` | 가운데가 굵고 끝이 가는 붓 선의 외곽 경로 |
| `ribbon(points, widths)` | 지점마다 폭을 지정한 띠 (머리 가닥, 천) |
| `symmetric(half_points, axis_x)`, `mirror(points, axis_x)` | 좌우 대칭 |
| `offset`, `rotate`, `scale` | 경로 변환 |
| `union`, `intersect`, `subtract` | 경로 불리언 |
| `sample(points)` | 곡선 위의 점 목록 |

- `runs` 사용 예: 잎사귀는 두 구간 `[[밑, 옆1, 끝], [끝, 옆2, 밑]]`으로 끝이 뾰족해짐
- `taper`의 start, end는 양 끝에 남는 굵기 비율 (0 바늘 끝, 1 뭉툭)

## Gradient와 색

```python
Gradient.linear((x0, y0), (x1, y1), ["#색1", "#색2"])              # 균등 분할
Gradient.linear(p0, p1, [(0.0, "#색1"), (0.7, "#색2"), (1.0, "#색3")])
Gradient.radial((cx, cy), radius, ["#안", "#밖"])
```

- 색 표기: `"#rrggbb"`, 0-255 정수 튜플, 0-1 실수 튜플
- 유틸리티: `to_rgb`, `mix(a, b, t)`, `shift_hue(color, degrees)`, `trace_color(color)` (선화용 어두운 색)

## 조명과 렌더

| 함수 | 용도 |
|---|---|
| `Light(azimuth, elevation, color, shadow_tint, wrap, haze, haze_strength, rim, bounce, bounce_color, flush)` | 광원 |
| `light(name, **overrides)` | 조명 프리셋 |
| `paint(canvas, style, light, params, extra_finish)` | 화풍 프리셋 렌더와 마감 |
| `render(canvas, medium, light, groups, **params)` | 매체 직접 렌더 |
| `reference(canvas, light)` | 매체 없는 매끈한 기준 렌더 |
| `lightness(canvas, light)` | 픽셀별 밝기 0-1 |
| `save(image, path)` | PNG 저장 |

- 렌더는 캔버스를 변경하지 않으므로 같은 캔버스를 여러 매체로 렌더 가능
- 유화, 점묘는 무작위 붓질을 쓰므로 `seed`가 같아야 결과가 재현됨

## studio와 qa

| 도구 | 용도 |
|---|---|
| `studio.run(build, brief, output)` | 명령행 모드 처리 (`--rough`, `--buffers`, `--styles`, `--style`, `--light`, `--scale`, `--seed`, `--out`) |
| `qa.sheet(images, labels, columns)` | 여러 이미지를 한 장으로 |
| `qa.buffers(canvas, light)` | 구조 버퍼 시트 |
| `qa.zoom(image, x0, y0, x1, y1)` | 영역 확대 (비율 좌표 0-1) |
| `qa.check_figure(view)` | 손발 개수 점검 |
| `qa.check_image(image)` | 명도, 대비, 채도 통계 |
| `compose.value_check(image)` | 3단 명도 변환 |
| `compose.guides(image)` | 삼분할 가이드 덧그리기 (검수용) |

- `build`가 `{"views": [...], "light": Light, "style_params": {화풍: {매체 파라미터}}}` 사전을 반환하면 손발 점검, 조명 교체, 장면별 매체 조정에 사용됨

## 직접 그리기 요령

- 대상 분해 순서: 큰 실루엣 1개, 그 안의 색 영역, 명암을 만드는 형태, 마지막에 선과 강조
- 형태 선택

| 대상의 성격 | 도구 |
|---|---|
| 평평한 도형, 무늬, 표지판 | `canvas.add(경로, 색, form="flat")` |
| 둥근 단일 형태 (과일, 돌, 구름) | `canvas.add(경로, 색, form="round")` |
| 여러 덩어리가 겹치는 입체 (동물, 가구, 탈것) | `Sculpture` |
| 원근이 있는 상자형 (건물, 방) | `scenery.Perspective`, 거리는 `city` |
| 불규칙한 자연 형태 (지형, 숲) | 넘파이 마스크와 `canvas.noise` |

- 대칭 형태는 반쪽만 정의하여 `geom.symmetric`으로 완성
- 같은 요소가 여럿이면 시드 기반 난수로 크기와 위치를 조금씩 다르게 하여 반복감을 줄임
- 세부를 그리기 전에 `--rough`로 실루엣부터 확인
- 평면 요소를 입체 위에 얹을 때는 `clip`과 `keep_normal=1.0`을 함께 사용
- 발광체는 `unlit=True`인 밝은 형태와 마감의 `bloom` 조합으로 표현
- 유리와 물은 뒤 배경을 흐리게 칠한 `tint`와 가장자리 하이라이트 `accent`로 표현
