# 엔진 API

## 목차

- 좌표와 단위
- Scene
- Part
- Line과 Stroke
- Ribbon과 곡선 도구
- 이어지는 도형
- 색 도구
- 화풍과 재질
- 붓질 패스
- 후보정
- 배경
- 검수 도구
- 조정 상수

## 좌표와 단위

- 좌표는 픽셀, x는 오른쪽, y는 아래쪽이 양의 방향
- 색은 `"#rrggbb"` 문자열 또는 0..1 범위 RGB
- 각도는 라디안, 화면에서 시계 방향이 양의 방향
    + `FigurePose`만 도(degree) 단위 사용
- 빛 벡터 `light=(x, y, z)`는 표면에서 광원을 향하는 방향, z는 관찰자 쪽
    + 좌상단 앞쪽 광원 예시는 `(-0.48, -0.58, 0.66)`
    + 측광으로 입체감을 강조하는 예시는 `(-0.74, -0.42, 0.52)`

## Scene

```python
scene = Scene(width=1024, height=1280, light=(-0.48, -0.58, 0.66), seed=0)
scene.set_background(color_or_image)      # 색 또는 (h, w, 3) 이미지
scene.add(part, [part, ...], ...)         # 추가 순서가 곧 뒤에서 앞 순서
img = scene.render("anime")               # 0..1 float RGB 반환
img, buffers = scene.render(style, return_buffers=True)   # flat, normals, focus 버퍼 동시 반환
save(img, "out.png")
```

- 렌더링 순서는 마스크 계산, 도형별 명암과 그림자, 선, 화풍 마감 순
- `return_buffers`의 `flat`은 마감 전 그림이며 결함 위치 추적에 사용

## Part

도형 1개. `polys` 또는 `ribbon` 중 1개를 지정한다.

| 필드 | 기본값 | 의미 |
|---|---|---|
| `name` | 필수 | 이름, `clip` 대상 지정에 사용 |
| `color` | 필수 | 고유색 |
| `polys` | None | 닫힌 다각형 목록, 합집합으로 채움 |
| `ribbon` | None | `Ribbon` 객체 |
| `material` | `"matte"` | 재질 이름, 아래 재질 표 참조 |
| `shade` | True | False는 입체 명암 없이 평면 채색 |
| `bulge` | 1.0 | 다각형 도형의 볼록한 정도, 낮을수록 평평 |
| `flatness` | 1.0 | 리본 단면의 납작한 정도, 1은 원통 |
| `gradient` | None | `((x, y), 색, (x, y), 색)` 선형 그러데이션 채색 |
| `line` | None | 외곽선 `Line` |
| `strokes` | [] | 세부 선 `Stroke` 목록 |
| `clip` | None | 이름 또는 그룹 이름(목록 가능), 해당 도형 내부로 제한 |
| `fade_t` | None | 리본 전용, `(t0, t1)` 시작부 서서히 나타남, `(t0, t1, t2, t3)` 끝부 서서히 사라짐 추가 |
| `erase` | [] | `[(다각형, 흐림 px)]` 부드러운 구멍 |
| `blur` | 0 | 가장자리 흐림 px, 볼터치와 보조 음영에 사용 |
| `alpha` | 1.0 | 불투명도 |
| `blend` | `"normal"` | `normal`, `multiply`, `screen`, `add` |
| `cast` | 0 | 아래 도형에 드리우는 그림자 거리 px |
| `receive` | True | 드리운 그림자 수용 여부 |
| `group` | `""` | 같은 그룹끼리는 서로 그림자를 드리우지 않음 |
| `focus` | 0 | 붓질 패스에서 세밀하게 그릴 정도 0..1 |
| `light_bias` | 0 | 양수는 밝은 쪽, 음수는 그림자 쪽으로 명암 이동 |
| `accent` | False | 칠한 하이라이트 표시, 하이라이트가 없는 화풍(`highlight` 0, `poster`)에서는 생략 |
| `depth` | None | 가구의 무대 깊이(m), `Set.arrange`가 인물과 정렬할 때 사용, None은 벽과 바닥처럼 항상 뒤 |

- `clip`은 앞서 추가된 도형만 참조 가능
- `clip`, `under`, `shape_with`, `merge`는 이름, 그룹, 태그로 도형을 찾으므로 한 장면에서 같은 이름을 쓰는 도형끼리 섞임
    + 같은 모듈로 만든 인물이나 사물을 여러 개 놓을 때는 이름에 고유 접두어를 붙임(인물은 `FigureSpec.ident`)
- 평면 세부(눈동자, 무늬, 하이라이트)는 `shade=False, material="flat"` 조합 사용

## Line과 Stroke

```python
Line(width=2.2, color=None, taper=True, shade_gain=0.7, paths=None, caps=(False, False), alpha=1.0)
Stroke(path, width=1.6, color=None, taper=(True, True), alpha=1.0, clip=False, feature=True)
```

- `Line`은 도형의 외곽선
    + `color=None`은 화풍의 잉크색과 고유색을 섞어 자동 결정
    + `shade_gain`은 빛 반대쪽 선을 굵게 하는 비율
    + `paths`는 전체 외곽 대신 지정한 구간만 선으로 그림
    + `caps`는 리본의 시작과 끝 마구리에 선을 그릴지 여부
    + `taper`는 True, False 또는 `(시작, 끝)` 튜플
- `Stroke`는 도형에 속한 자유 선
    + `width`는 단일 값 또는 구간별 배열
    + `feature=True`는 모든 화풍에서 그림(속눈썹, 입선), False는 선 없는 화풍에서 생략(가닥선)
    + `clip=True`는 소속 도형 내부로 제한

## Ribbon과 곡선 도구

```python
Ribbon(axis, width_a, width_b=None, step=4.0, round_start=True, round_end=True)
```

- `axis`는 축 폴리라인, `width_a`와 `width_b`는 좌우 반폭
    + 폭은 단일 값, 배열, `[(t, 폭), ...]` 키 목록 중 1개 형식
    + 축이 화면 아래로 향할 때 A쪽이 화면 왼쪽
- `ribbon.side_a`, `ribbon.side_b`는 좌우 윤곽 폴리라인, `ribbon.axis`는 재표본화된 축
- `ribbon.cap(0)`, `ribbon.cap(1)`은 시작과 끝의 반원 마구리
- `ribbon.outline_paths(cap_start, cap_end)`는 선으로 그릴 경로 목록

| 함수 | 용도 |
|---|---|
| `catmull_rom(points, closed=False, samples=14)` | 제어점을 지나는 매끄러운 곡선 |
| `bezier(p0, p1, p2, p3, n=24)` | 3차 베지에 곡선 |
| `ellipse(cx, cy, rx, ry, rot=0, n=48)` | 타원 다각형 |
| `transform(p, scale, rotate, translate, origin, mirror)` | 확대, 회전, 이동, 좌우 반전 |
| `chaikin(p, iterations=2)` | 관절 사슬의 모서리 둥글림 |
| `offset_polygon(poly, distance)` | 매끄러운 닫힌 다각형 확장과 축소 |
| `resample(p, step=None, n=None)` | 호 길이 기준 균등 재표본화 |
| `profile(keys, t)` | `[(t, 값)]` 키 사이 단조 보간 |
| `lerp(a, b, t)` | 선형 보간 |

## 이어지는 도형

몸통에서 팔다리가 자라나는 형태는 도형마다 외곽선을 그리면 관절마다 선이 생긴다. 아래 필드로 여러 도형을 한 표면처럼 다룬다.

| 필드 | 의미 |
|---|---|
| `merge` | 같은 키를 가진 도형들을 한 표면으로 잉크 처리, 선 굵기와 색은 첫 도형의 `line`을 사용 |
| `joints` | `[(x, y, 반경)]` 이 도형이 다른 도형에서 자라나는 지점, 반경 안에서는 겹침선을 생략 |
| `grow_from` | `(도형 이름, 흐림 px)` 관절 반경 안에서 바탕 도형이 비쳐 보이도록 채색을 서서히 전환 |
| `shape_with` | 도형 이름 목록, 인접 도형과 한 덩어리로 부풀려 접합부의 테두리 음영 제거, 같은 덩어리의 도형끼리는 `bulge`도 같게 지정 |
| `tags` | 추가 키 목록, 다른 도형이 `clip`, `under`, `shape_with`에서 이 키로 참조 |
| `under` | 키 목록, 해당 도형들 아래에 놓여 그 영역이 가려짐(허리에 얹은 손 아래의 옷), 가려진 영역에는 잉크도 그리지 않음 |
| `fitted` | `clip`으로 잘린 모양 그대로 부풀리고 선을 그림, 몸에 붙는 옷에 사용 |

```python
body = Part("body", FUR, polys=[body_outline], material="hair", merge="cat", line=Line(3.0),
            shape_with=["leg"])
leg = Part("leg", FUR, ribbon=leg_ribbon, material="hair", merge="cat",
           joints=[(hip_x, hip_y, 40)], grow_from=("body", 6))
```

- 잉크는 합집합의 실루엣과 앞 도형이 뒤 도형 위를 지나는 경계에만 생성
- 묶음의 마지막 도형이 그려진 직후에 잉크를 그리므로 묶음 도형은 연속해서 추가
    + 묶음 사이에 끼어든 다른 그룹의 불투명 도형(선이 있고 `normal` 혼합, `alpha` 0.9 이상)은 그보다 앞선 묶음 도형의 잉크를 가림
    + 팔 바로 뒤에 쌓은 소매가 이 규칙으로 팔의 잉크 위에 놓임
    + 묶음과 같은 `group`의 도형(팔 끝의 손)은 가리지 않아 합집합 윤곽이 그 위에 그려짐
    + 끼어든 도형 위로 다시 지나는 뒤쪽 묶음 도형의 잉크는 유지
- 옷처럼 몸 위에 얹는 도형은 묶음 뒤에 추가하고 `clip`으로 몸 도형 이름을 지정
    + `clip`을 지정한 도형은 외곽선도 같은 영역으로 잘림
- 다각형 여러 개를 합친 독립 실루엣(반바지의 골반 띠와 다리 통)은 `merge`를 지정해 합집합 외곽만 잉크 처리

## 색 도구

| 함수 | 용도 |
|---|---|
| `rgb(value)` | 색 문자열을 0..1 배열로 변환 |
| `mix(a, b, t)` | 두 색 혼합 |
| `adjust(color, hue=0, sat=1, val=1)` | 색상 이동, 채도와 명도 배율 |
| `vertical_gradient(h, w, [(y비율, 색), ...])` | 세로 그러데이션 이미지 |
| `fbm(h, w, scale, octaves, seed, stretch)` | 0..1 프랙탈 노이즈, `stretch`는 가로 늘림 |
| `smoothstep(e0, e1, x)` | 부드러운 계단 함수, 역방향 경계 지원 |

## 화풍과 재질

```python
from codepaint import get_style, ANIME, ILLUST, PAINTERLY, WATERCOLOR, PENCIL, POSTER, NEON
style = get_style("illust", rim=0.8, line_scale=0.5)     # 프리셋에서 필드만 덮어쓰기
```

| 프리셋 | 명암 | 선 | 후보정 |
|---|---|---|---|
| `anime` | 단계 명암 | 어두운 선 | 확산광, 블룸, 입자 |
| `illust` | 부드러운 명암과 약한 경계 | 고유색 색선 | 확산광, 블룸, 종이결 |
| `painterly` | 연속 명암 | 선 없음 | 붓질 재도장, 캔버스결, 비네트 |
| `watercolor` | 밝은 연속 명암 | 가는 고유색 선 | `watercolor`, 종이결 |
| `pencil` | 회색조 연속 명암 | 흑연 선 | `pencil`, 종이결 |
| `poster` | 2단계 평면 명암, 하이라이트 없음 | 굵은 남색 선 | `posterize`, `halftone`, 종이결 |
| `neon` | 청보라 그늘, 자홍 주광 | 가는 어두운 선 | 야간 색보정, 강한 블룸, `chromatic`, 어두운 비네트 |

| Style 필드 | 의미 |
|---|---|
| `cel_mix` | 1은 단계 명암, 0은 연속 명암 |
| `cel_threshold`, `cel_edge` | 명암 경계 위치와 경계 부드러움 |
| `deep_threshold` | 2번째 어두운 단계 위치, None은 해제 |
| `soft_range` | 연속 명암에서 그림자와 빛에 대응하는 범위 |
| `ambient` | 모든 그림자에 곱하는 환경색 |
| `light_color`, `highlight` | 하이라이트 색과 강도 배율 |
| `key_tint` | 밝은 면에 곱하는 주광 색, 기본 (1, 1, 1), 네온은 자홍 |
| `cast_strength`, `cast_blur` | 드리운 그림자 농도와 흐림 px |
| `sss` | 피부 명암 경계의 붉은 번짐 |
| `rim`, `rim_color` | 역광 테두리 강도와 색 |
| `line_scale` | 외곽선 굵기 배율, 0은 선 없음 |
| `line_tint`, `ink` | 선색의 고유색 비율과 잉크색 |
| `painterly` | 붓질 패스 인자 dict, None은 붓질 없음 |
| `post` | 후보정 단계 목록 `[(이름, 인자 dict), ...]` |

| 재질 | 용도 | 특징 |
|---|---|---|
| `matte` | 일반 물체 | 중립 그림자 |
| `skin` | 피부 | 붉은 그림자, 경계 번짐, 약한 하이라이트 |
| `hair` | 머리카락, 털 | 한색 짙은 그림자 |
| `cloth` | 천 | 한색 그림자 |
| `gloss` | 금속, 유리, 젖은 표면 | 강한 하이라이트 |
| `flat` | 평면 세부 | 그림자 영향 없음 |

## 붓질 패스

```python
finish(img, style="painterly", normals=None, focus=None, seed=0)   # 붓질과 후보정을 한 번에 적용
paint(ref, normals=None, focus=None, seed=0, radii=None, scale=1.0, threshold=14, ground=None,
      relief=0.15, jitter=5, stroke_length=1.0, fidelity=0.75, detail_blend=0.40)
```

- `paint`는 기준 그림을 큰 붓에서 작은 붓 순서로 다시 칠함(Hertzmann 1998 방식)
- `scale`은 모든 붓 반경의 배율, 작을수록 세밀
- `normals`를 주면 붓질이 형태를 감싸는 방향으로 진행
- `focus`는 세밀하게 그릴 영역 지도, `Part.focus`가 자동 전달
- `fidelity`는 기준 그림에서 크게 벗어난 붓질을 되돌리는 강도
- `relief`는 물감 두께 음영 강도, 0은 평평한 물감
- `ground`는 바탕칠 색, 지정하지 않으면 그림 평균색 기반 난색

## 후보정

`post.apply(img, [(이름, 인자), ...], seed)` 형식으로 순서대로 적용한다.

| 효과 | 주요 인자 | 용도 |
|---|---|---|
| `bloom` | threshold, radius, strength | 밝은 곳 주변 빛 번짐 |
| `diffusion` | radius, strength | 화면 전체의 부드러운 확산광 |
| `grade` | contrast, saturation, shadows, highlights, gamma | 대비, 채도, 명부와 암부 색조 |
| `grain` | amount | 필름 입자 |
| `paper` | amount, scale | 종이결 |
| `canvas_weave` | amount, period | 캔버스 직조결 |
| `vignette` | strength, color | 가장자리 어둡게 |
| `edge_darken` | amount, radius | 수채 물감 고임 효과 |
| `watercolor` | wobble, flatten, bleed, pigment, hue_drift, granulation, wet_edge, lighten, border | 투명 수채: 세부를 물감 면으로 단순화, 흔들리는 경계, 번짐, 얼룩진 농도, 안료 입자, 가장자리 고임, 흰 종이 테두리 |
| `pencil` | spacing, length, strength, smudge, contour, paper_color, graphite | 연필 소묘: 명도 단계별 해칭 3방향, 문지른 흑연, 그려진 선은 국소 대비로 찾아 연필선 1개로 유지 |
| `posterize` | levels, chroma_step, keep_dark | 판화 색면: 명도와 색축을 거친 단계로 끊어 평면 잉크로 바꿈, 색상이 다른 면은 섞이지 않음, 가는 선은 어두운 잉크 1색 |
| `halftone` | cell, angle, strength, start | 어두운 면의 인쇄 망점, 어두울수록 큰 점 |
| `chromatic` | shift | 렌즈 색수차, 빨강은 바깥으로, 파랑은 안쪽으로 |

## 배경

| 함수 | 결과 |
|---|---|
| `backdrop.studio(h, w, center_color, edge_color, center, radius)` | 중심이 밝은 스튜디오 벽 |
| `backdrop.wash(h, w, colors, seed, scale, contrast)` | 색 3-4개가 번진 얼룩 바탕 |
| `backdrop.bokeh(img, count, radius, colors, alpha, seed, region)` | 초점 밖 빛망울 |
| `backdrop.light_beam(img, angle, width, strength, color)` | 대각선 빛줄기 |

## 검수 도구

| 함수 | 용도 |
|---|---|
| `review.preview(img, path, max_side=1200)` | 축소본 저장 |
| `review.zoom(img, path, box, scale=2.0)` | 지정 영역 확대 저장 |
| `review.sheet(images, path, columns, height)` | 여러 그림 비교 시트 |
| `review.stats(img)` | 평균 밝기, 대비, 백색과 흑색 뭉침 비율, 채도, 세부량 |

- `stats` 기준 예시는 대비 0.25 이상, 백색 뭉침 0.25 이하, 흑색 뭉침 0.35 이하

## 조정 상수

`codepaint/config.py`에 엔진 상수가 모여 있다. 마스크 표본 수, 부풀림 격자 크기, 선 최소 굵기, 붓 반경 기본값 등을 이 파일에서 조정한다.
