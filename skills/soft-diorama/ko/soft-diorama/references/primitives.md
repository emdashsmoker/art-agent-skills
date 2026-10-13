# 기본 도형으로 대상 설계하기

리그에 없는 대상(사물, 동물, 건물, 전신 인물 등)을 그리는 방법. 동작하는 전체 예시는 `scripts/examples/still_life.py`와 `landscape_lake.py`.

## 목차

1. 설계 순서
2. 형태 만들기
3. 입체감 주기
4. 질감과 무늬
5. 선
6. 공간감
7. 복잡한 형상 다루기

## 1. 설계 순서

1. 대상을 부위로 나눈다. 부위 하나가 마스크 하나가 된다 (꽃병 = 몸통 + 띠 + 하이라이트)
2. 부위를 뒤에서 앞 순서로 나열한다
3. 부위마다 `blob`(덩어리) 또는 `ribbon`(길쭉한 것)을 고른다
4. 부위마다 함수 1개로 묶는다: 마스크 생성 → `paint_form` → 추가 그림자와 하이라이트
5. 마감 없이 `cv.save()`로 형태부터 확인하고, 형태가 맞은 뒤 마감을 붙인다

## 2. 형태 만들기

```python
# 덩어리: 제어점 5-10개면 충분하다. 점이 많을수록 울퉁불퉁해진다
body = cv.blob([(400, 470), (560, 640), (520, 830), (380, 830), (340, 640)])

# 좌우 대칭: 오른쪽 절반만 정의하고 뒤집어 붙인다
right = [(48, 470), (52, 505), (98, 610), (128, 715), (108, 800), (72, 838)]
outline = [(450 + x, y) for x, y in right] + [(450 - x, y) for x, y in reversed(right)]
vase = cv.blob(outline)

# 길쭉한 것: 중심선 2-4점 + 폭 + 프로파일
stem = cv.ribbon([(450, 800), (470, 600), (440, 420)], 8, [1.0, 0.8, 0.6])
petal = cv.ribbon([(300, 300), (380, 290)], 50, [0.35, 1.0, 0.75])     # 꽃잎, 잎, 깃털
leaf = cv.ribbon([(200, 500), (250, 470), (300, 480)], 36, 'taper')

# 각진 것: smooth=False
roof = cv.blob([(100, 400), (300, 250), (500, 400)], smooth=False)

# 구멍과 조합
ring = cv.ellipse(500, 500, 120) * (1 - cv.ellipse(500, 500, 80))     # 도넛
cup = np.maximum(body, handle)                                        # 합치기
visible = shape * (1 - front_object)                                  # 앞 물체에 가린 부분 제거
```

반복되는 형태(꽃잎, 기와, 비늘)는 반복문에서 각도나 위치만 바꿔 같은 `ribbon`을 찍는다.

## 3. 입체감 주기

```python
LIGHT = (-0.7, -0.7)

# 가장 빠른 길: 칠 + 형태 그림자 + 외곽선 + 테두리 빛
cv.paint_form(vase, '#7fb0c4', LIGHT, shadow=0.22, soft=6, line_width=2.4, rim=0.5)

# 바닥에 드리운 그림자: 물체보다 먼저, 빛 반대쪽으로 길게
ground = cv.ellipse(560, 838, 190, 26)
cv.tint(blur(ground, 10), shadow_of('#8f6650', 1.4), 'multiply', 0.8)

# 물체가 다른 물체에 드리우는 그림자
cv.tint(shading.cast(lid, pot, offset=(8, 14), soft=3), shadow_of(pot_color), 'normal', 0.8)

# 광택: 빛 쪽에 가늘고 밝은 띠를 screen으로
shine = cv.ribbon([(405, 560), (392, 640), (398, 720)], 14, 'taper')
cv.tint(blur(shine, 3) * vase, '#ffffff', 'screen', 0.7)

# 둥근 덩어리의 명암 경계 (공, 과일, 구름)
cv.tint(shading.form_shadow(ball, LIGHT, threshold=0.55, soft=0.03), shadow_of(color), 'normal', 0.9)

# 면 전체의 완만한 밝기 변화
cv.tint(wall * cv.linear((0, 0), (900, 800)), '#d9c6bd', 'normal', 0.6)
```

```python
# 부피가 중요한 대상(과일, 병, 그릇, 천, 살결): 연속적인 둥근 음영
cv.paint_volume(apple, '#c8342c', LIGHT, bulge=55, depth=1.2, gloss=0.55)
cv.paint_volume(bottle, '#2f5a48', LIGHT, bulge=38, depth=1.4, gloss=0.8)
```

- `paint_form`은 경계가 분명한 셀 음영, `paint_volume`은 부드러운 회화 음영이다. 화풍에 맞춰 고른다
- `bulge`는 가장자리에서 얼마나 깊이 둥글어지는지(px). 폭의 절반이면 공이나 원통, 작으면 가장자리만 둥근 납작한 덩어리
- `shadow`는 형태 크기 대비 그림자 폭. 납작한 것 0.1, 둥근 것 0.2-0.3
- `soft`는 화풍에 맞춘다. 애니메 1, 일러스트와 수채 4-8

## 4. 질감과 무늬

```python
# 줄무늬, 격자: 좌표 배열로 만들고 부위 마스크로 자른다
xs = np.arange(cv.width, dtype=np.float32)[None, :] * np.ones((cv.height, 1), np.float32)
stripes = ((xs // 24) % 2 == 0).astype(np.float32)
cv.tint(stripes * shirt, '#3f5f8a', 'multiply', 0.8)

# 나뭇결, 돌, 천의 얼룩: 잡음을 늘려서 곱한다
grain = cv.noise(scale=40, octaves=3, seed=3, stretch=(8, 1))
cv.tint(smoothstep(grain, 0.45, 0.6) * table, shadow_of(table_color, 0.6), 'normal', 0.4)

# 점무늬, 별, 눈송이: 작은 타원을 난수로 흩뿌린다
rng = np.random.default_rng(5)
dots = cv.polygon(*[geometry.ellipse_points(rng.uniform(0, 900), rng.uniform(0, 600), 4, 4, 0, 12) for _ in range(80)])
cv.tint(dots * sky_mask, '#ffffff', 'screen', 0.9)
```

`geometry`는 `from paintkit import geometry`.

## 5. 선

```python
cv.outline(mask, 2.5, '#5a4a48')                       # 외곽선: 굵기가 자동으로 변한다
cv.ink([(120, 300), (180, 280), (240, 300)], 2.0, '#5a4a48', 'taper')   # 내부 선 1획
cv.ink(points, 1.8, color, 'in', clip=mask)            # 부위 안으로만
```

- 선 색은 검정보다 그 면의 어두운 색을 쓴다. `adjust(color, lightness=-0.38)`
- 내부 선은 외곽선보다 가늘게 한다
- 선 없는 화풍(유화)에서는 `line_width=0`으로 두고 명암으로 형태를 구분한다

## 6. 공간감

- 겹침: 앞 물체가 뒤 물체를 가리게 배치한다. 가장 강한 깊이 단서다
- 크기와 위치: 먼 것은 작게, 수평선 가까이
- 색: 먼 것은 밝고 푸르고 채도가 낮다. `mix(color, sky_color, 0.4)`
- 초점: 먼 배경을 그린 뒤 `cv.color = blur(cv.color, 2)`. 전경 장식은 `leaves(blur_px=6)`처럼 흐리게
- 접지: 바닥과 닿는 곳에 그림자를 깐다

## 7. 복잡한 형상 다루기

- 인물 전신과 손은 리그가 있다 (`references/fullbody.md`). 원근이 있는 건물, 도로, 바닥 무늬는 평면으로 그려 `cv.paste`로 붙인다 (`references/city.md`)
- 절반 크기 캔버스에서 실루엣만 단색으로 먼저 그려 본다. 실루엣이 읽히지 않으면 세부를 넣어도 읽히지 않는다
- `inspect_render.py --grid`로 좌표를 읽어 제어점을 옮긴다
- 관절이 있는 대상(팔, 다리, 동물)은 관절 위치를 점으로 먼저 정하고 그 사이를 `ribbon`으로 잇는다
    + 폭 프로파일로 근육의 굵기 변화를 준다: 팔뚝 `[0.8, 1.0, 0.7]`
    + 손은 장갑 모양 덩어리 1개와 엄지 1개로 단순화한다
- 한 번에 한 부위씩 추가하고 렌더로 확인한다. 여러 부위를 한꺼번에 넣으면 어긋난 곳을 찾기 어렵다
- 정확한 비례가 필요한 대상은 기준 길이 1개(머리 높이, 바퀴 지름 등)를 상수로 두고 나머지를 그 배수로 적는다
