# 상반신 인물 리그 (paintkit.figure)

전신, 손, 전신 의상은 `references/fullbody.md`에 있다. 얼굴과 머리카락 설정(`FaceSpec`, `HairSpec`, `Look`)은 전신에서도 이 문서의 것을 그대로 쓴다.

상반신 인물을 매개변수로 그린다. 호출 1번으로 뒷머리, 몸, 옷, 얼굴, 앞머리를 뒤에서 앞 순서로 칠한다.

```python
from paintkit.figure import (ANIME, ILLUSTRATION, PAINTERLY, SKETCH, Look, BodySpec, Character,
                             FaceSpec, HairSpec, Head, Outfit, add_rim_light, draw_character)
masks = draw_character(cv, Character(head=Head((512, 480), 500), look=ANIME))
```

## 목차

1. 좌표계
2. Head
3. FaceSpec
4. HairSpec
5. BodySpec과 Outfit
6. Look
7. 돌려받는 마스크
8. 인상 조절
9. 구도
10. 소품과 무늬 추가
11. 한계

## 1. 좌표계

- 머리 단위: 정수리에서 턱까지 길이의 절반이 1. `head.unit`이 그 픽셀 값
- `y`: 정수리 -1, 눈 약 0.13, 코끝 0.44, 입 0.665, 턱끝 +1. 어깨 약 1.6, 가슴 약 2.6
- `phi`: 머리 둘레 각도. 0이 얼굴 정면, +90이 화면 오른쪽 옆면 (yaw 0 기준)
- `head.at(phi, y, lift=0, forward=0)`: 머리 표면의 점을 픽셀로 변환
    + `lift`: 표면에서 바깥으로 띄우는 비율 (머리카락 위는 0.10 안팎)
    + `forward`: 얼굴 정면 방향으로 내미는 거리 (코, 안경 다리)
- `head.path([(phi, y), ...])`: 여러 점을 한 번에 변환
- `head.facing(phi)`: 그 각도의 표면이 보는 사람을 향하는 정도 (1 정면, 0 옆, 음수 뒤)

얼굴 위의 모든 요소가 표면 좌표로 정의되어 있으므로 `yaw`를 바꾸면 위치와 폭 축소가 함께 따라온다.

## 2. Head

| 인자 | 의미 | 권장 범위 |
|---|---|---|
| `center` | 정수리와 턱의 중점 px | 세로 1280 캔버스에서 y 470-520 |
| `size` | 정수리에서 턱까지 px | 캔버스 높이의 35-42% |
| `yaw` | 고개 회전. 양수면 화면 오른쪽을 본다. 90은 옆얼굴, 180은 뒤통수 | 상반신 리그는 -40..40, 전신 리그는 -180..180 |
| `tilt` | 고개 기울임. 양수면 시계 방향 | -12..12 |
| `jaw` | 얼굴 아래쪽 폭 배율. 1보다 작으면 볼과 턱이 갸름해져 성숙한 인상 | 0.90..1.0 |

- `yaw`가 음수면 화면 오른쪽(`phi` 양수 쪽) 옆얼굴과 귀가 보인다
- 정면(`yaw=0`)보다 15-25도 돌린 쪽이 입체감이 좋다
- 40도를 넘기면 시선이 관객을 따라오지 않고 앞을 본다. 42도부터 코, 입술, 턱이 얼굴 윤곽 밖으로 튀어나와 옆얼굴 선이 생긴다
- 뒤로 돈 쪽 눈, 눈썹, 앞머리 가닥은 자동으로 숨는다. 얼굴이 완전히 돌아가면 머리카락이 머리 전체를 덮는다
- 짧은 머리(`length` 1 미만)는 옆과 뒤에서 목덜미까지 덮는다

## 3. FaceSpec

| 인자 | 기본값 | 의미 |
|---|---|---|
| `skin` | `#ffe4d3` | 피부색 |
| `eye_color` | `#4f78b8` | 홍채색 |
| `eye_phi` | 27 | 눈 중심의 각도. 작을수록 미간이 좁다 |
| `eye_y` | 0.13 | 눈 높이 |
| `eye_half_width` | 13 | 눈 가로 반폭 (도) |
| `eye_half_height` | 0.105 | 눈 세로 반높이. 인상에 가장 큰 영향 |
| `eye_slant` | 0.06 | 양수면 눈꼬리가 올라간다 |
| `gaze` | (0, 0) | 시선 (-1..1 가로, -1..1 세로) |
| `eye_contact` | True | 고개를 돌려도 보는 사람과 눈을 맞춘다 |
| `lash_color`, `brow_color` | | 속눈썹색, 눈썹색 (머리색에 맞춘다) |
| `lip_color`, `lip_fullness` | `#e0787c`, 0.5 | 입술색, 0은 선만 1은 꽉 찬 입술 |
| `blush` | 0.35 | 홍조 세기 |
| `smile` | 0.4 | -1 찡그림 .. 1 미소 |
| `mouth_open` | 0 | 입 벌림 |
| `lashes` | 1.0 | 속눈썹 굵기. 0.7 미만이면 눈꼬리 속눈썹을 생략한다 (남성 0.4) |
| `brow_weight` | 1.0 | 눈썹 굵기. 클수록 눈썹이 곧아진다 (남성 1.6-1.8) |
| `brow_lift` | 0 | 눈썹 높이. 음수면 눈 쪽으로 내려와 인상이 짙어진다 |
| `brow_tilt` | 0 | 양수면 눈썹 안쪽 끝이 올라간다 (걱정, 슬픔). 음수면 안쪽 끝이 내려온다 (화남) |
| `lid` | 0 | 윗눈꺼풀 내림. 0 뜬 눈 .. 1 감은 눈. 음수면 눈을 크게 뜬다 (놀람) |
| `squint` | 0 | 아랫눈꺼풀 올림 0 .. 1. 웃을 때 볼이 밀어 올린 눈 |
| `mouth_corners` | 0 | 표정용 입꼬리. 양수 올림(웃음), 음수 내림(슬픔). `smile`보다 약 3배 크게 움직인다 |
| `mouth_width` | 1.0 | 입 너비 배율. 좁게 벌리면 동그란 입(놀람) |
| `teeth` | 0 | 벌린 입 위쪽에 보이는 윗니 0 .. 1 |

- `smile`은 평소 표정의 은은한 입꼬리, `mouth_corners`는 표정의 입꼬리다
- 얼굴 스타일 프리셋과 표정 프리셋은 `references/fullbody.md` 17절

## 4. HairSpec

| 인자 | 기본값 | 의미 |
|---|---|---|
| `color` | `#6b4a3a` | 머리색. 그림자색, 하이라이트색, 선색은 자동 파생 |
| `bangs` | `wispy` | `full` 일자, `wispy` 가벼운 앞머리, `side` 옆으로 넘김, `curtain` 가운데 가르마로 양쪽, `short` 짧게 옆으로 빗어 넘긴 앞머리 (남성), `parted` 가르마에서 갈라져 관자놀이로 떨어짐 (가르마 쪽이 짧아 이마가 ㅅ자로 보임), `back` 이마선에서 정수리 너머로 빗어 넘김 (올백), `spiky` 정수리에서 위로 뻗친 가닥과 뾰족한 앞머리, `none` 이마 드러냄 |
| `bangs_length` | -0.10 | 앞머리 끝의 y. -0.15 눈썹, 0.1 눈 |
| `part` | -20 | 가르마 위치 (phi). `side`는 가르마 반대쪽으로 넘어간다 |
| `length` | 2.9 | 뒷머리 끝의 y. 0.6 짧은 머리 (1 미만), 1.1-1.3 단발, 1.7 어깨, 3.0 가슴 |
| `side_length` | 1.25 | 얼굴 옆 가닥의 끝 y |
| `wave` | 0 | 0 생머리 .. 1 웨이브 |
| `fullness` | 1.0 | 뒷머리 폭 |
| `volume` | 0.10 | 두피에서 뜨는 정도 |
| `shine` | 1.0 | 정수리 하이라이트 띠. 수채와 유화는 0.4-0.6 권장 |
| `seed` | 7 | 가닥 배치 난수 |
| `tie` | `none` | 묶음머리. `ponytail` 높은 포니테일, `low_ponytail` 낮은 포니테일, `braid` 땋은 머리 한 갈래, `bun` 높은 번, `low_bun` 낮은 번(쪽머리), `half_up` 반묶음 |
| `tail_length` | 2.4 | 포니테일과 땋은 머리 끝의 y |
| `tie_color` | `#2b2629` | 머리끈 색 |
| `flow` | 0 | 포니테일과 땋은 머리가 뒤로 날리는 정도. 0 늘어짐 .. 1 수평 (달리기, 바람) |
| `fade` | 0 | 클리퍼로 짧게 친 부분의 밀도. 0 없음 .. 1 맨살. 그 부분은 두피가 비치는 차가운 회색이 된다 |
| `fade_line` | -0.35 | 옆과 뒤에서 클리퍼 컷이 시작되는 y. -1 이하면 머리 전체 (버즈컷) |

- `length < 1.7`이면 단발로 처리되어 끝이 안쪽으로 말린다
- `length < 1.0`이면 짧은 머리: 뒷머리가 두피를 따라 목덜미까지만 내려오고, 옆머리는 귀 위에서 끝나며 구레나룻이 생긴다. 머리선은 귀 위를 지나 귀 뒤로 내려가고 목덜미 가운데가 가장 낮다. 앞머리는 `short`가 어울린다
- 남성 얼굴과 머리 프리셋 `MALE_FACE`, `MALE_HAIR`는 `references/fullbody.md` 9절
- `curtain`은 `part=0`과 함께 쓴다
- `tie`가 `half_up` 이외면 모든 머리가 묶인다. 뒷머리 덩어리 없이 두피를 덮은 머리 위에 묶음 방향으로 빗은 결이 그려진다
    + 얼굴 옆 가닥은 `side_length` 0.5 이상일 때만 남는다. 0이면 깔끔하게 모두 묶은 머리
    + 꼬리와 번은 머리 뒤쪽이 관객을 향하면(옆모습부터 뒷모습) 몸과 머리 위에, 그 밖에는 몸 뒤에 그려진다
- `fade`의 경계선은 관자놀이 앞에서 얼굴 아래로 내려가므로 이마 쪽 머리선은 그대로 남는다. 0.3 넘게 치면 구레나룻도 사라진다
- 이름 붙은 헤어 24종은 `references/fullbody.md` 16절의 `hairstyle()`로 바로 쓴다

## 5. BodySpec과 Outfit

| BodySpec | 의미 |
|---|---|
| `turn` | 몸통 회전 (도). 고개와 같은 방향으로 절반쯤 주면 자연스럽다 |
| `lean` | 어깨 기울임 (도). 양수면 화면 오른쪽 어깨가 내려간다 |
| `shoulder_scale` | 어깨 폭 배율 |

| Outfit.kind | 모양 |
|---|---|
| `knit` | 라운드넥 니트 |
| `turtleneck` | 터틀넥 |
| `vneck` | 브이넥 상의. 쇄골이 보인다 |
| `camisole` | 끈 있는 상의. 어깨와 쇄골이 드러난다 |
| `offshoulder` | 오프숄더 |

`Outfit(kind, color, trim='', detail=1.0)`. `trim`은 깃과 끈의 색, `detail`은 볼륨 음영과 봉제선의 세기.

## 6. Look

| 프리셋 | 선 | 그림자 경계 | 짝이 되는 마감 |
|---|---|---|---|
| `ANIME` | 굵고 짙음 | 단단함 | `finish_anime` |
| `ILLUSTRATION` | 가늘고 연함 | 부드러움 + 얼굴 입체 음영 | `finish_illustration` |
| `SKETCH` | 연필 느낌 | 중간 | `finish_watercolor` |
| `PAINTERLY` | 없음 (속눈썹, 눈썹, 입선만 유지) | 부드러움 | `finish_oil` |

빛 방향이나 세기를 바꿀 때는 복사해서 쓴다.

```python
from dataclasses import replace
look = replace(ILLUSTRATION, light=(0.7, -0.8), shade_depth=1.2)
```

필드: `line_scale`(선 굵기 배율), `line_depth`(선의 어두운 정도), `line_opacity`, `shade_soft`(그림자 경계 흐림 px), `shade_depth`(그림자 진하기), `highlight`(하이라이트 세기), `light`(광원 방향), `light_height`(전신의 부피 음영에서 빛의 높이. 낮을수록 굴곡이 깊다).
`shade_depth=0, highlight=0`이면 밑색만 칠한 상태가 된다.

## 7. 돌려받는 마스크

`draw_character`의 반환값 dict.

| 키 | 영역 |
|---|---|
| `all` | 인물 전체 |
| `face` | 머리(피부) |
| `eyes` | 두 눈의 뜬 영역 |
| `front_hair`, `back_hair` | 앞머리 쪽, 뒷머리 |
| `tie` | 포니테일, 땋은 머리, 번 (묶음머리가 없으면 빈 마스크) |
| `cloth` | 옷 |
| `neck`, `torso` | 목, 어깨와 가슴(피부 기준 실루엣) |

용도 예

```python
add_rim_light(cv, masks['all'], look, color='#ffe2b0', width=6, opacity=0.8)   # 역광 테두리
cv.tint(masks['all'] * cv.linear((0, 700), (0, 1280)), '#2a2f55', 'multiply', 0.25)  # 아래쪽을 가라앉힘
detail = np.maximum(grow(masks['eyes'], 14), masks['face'] * 0.6)              # 유화의 세밀 영역
```

## 8. 인상 조절

| 원하는 인상 | 조절 |
|---|---|
| 성숙한 성인 | `eye_half_height` 0.095-0.11, `eye_y` 0.10-0.13, `lip_fullness` 0.6 이상, `blush` 0.2-0.3, 앞머리 `side`/`curtain`/`none` |
| 또렷하고 화려함 | `eye_half_height` 0.115-0.125, `eye_half_width` 14, `eye_slant` 0.10 |
| 부드럽고 순함 | `eye_slant` 0.0-0.03, `smile` 0.5 이상, `blush` 0.4 |
| 차분하고 도회적 | `smile` 0.1-0.2, `eye_slant` 0.10, 어두운 머리, `turtleneck` |

- 눈이 커지고 얼굴 아래쪽에 놓일수록 어려 보인다. 성인 인물은 위 표의 범위를 유지한다
- 피부를 조금 짙게 하면(`#f7d6c2` 등) 밝은 배경과 블룸에서 얼굴이 날아가지 않는다

## 9. 구도

- 1024x1280 기준 `Head(center=(520, 500), size=500)`이 가슴 위 구도
- 머리 크기를 줄이면 몸이 더 보인다. 캔버스 아래 경계의 y는 `(캔버스 높이 - center.y) / head.unit`으로 계산한다
    + 경계가 가슴선(y 2.4-2.9)에 걸리면 어색하다. 어깨 아래(2.2 이하) 또는 가슴 아래(3.0 이상)에서 자른다
- 고개 방향 쪽에 여백을 더 준다 (yaw가 음수면 인물을 오른쪽으로 조금 옮긴다)

## 10. 소품과 무늬 추가

`draw_character` 뒤에 기본 도형으로 덧그린다. 아래 코드는 동작을 확인한 예시다.

```python
unit = head.unit
light = character.look.light

# 옷 무늬: 옷 마스크 안에만 줄무늬를 곱한다. 이미 칠한 음영은 그대로 남는다
ys = np.arange(cv.height, dtype=np.float32)[:, None] * np.ones((1, cv.width), np.float32)
stripes = ((ys // (0.11 * unit)) % 2 == 0).astype(np.float32)
cv.tint(stripes * masks['cloth'], '#3f5f8a', 'multiply', 0.85)

# 귀걸이: 보이는 쪽 귓불 아래 (yaw가 음수면 phi 양수 쪽)
lobe = head.at(96, 0.42, lift=0.02)
drop = cv.ellipse(lobe[0], lobe[1] + 0.10 * unit, 0.035 * unit, 0.06 * unit)
cv.paint_form(drop, '#e8c25a', light, shadow=0.3, line_width=1.5, rim=0.8)

# 머리핀: 머리카락 위에 얹으므로 lift를 준다
clip = cv.ribbon([head.at(40, -0.42, lift=0.11), head.at(58, -0.30, lift=0.11)], 0.07 * unit, 'flat')
cv.paint_form(clip, '#e2556b', light, shadow=0.3, line_width=1.6, rim=0.7)

# 안경: 렌즈 테 2개와 코걸이
eye_y = character.face.eye_y
rings = cv.empty()
for side in (-1, 1):
    ring = [head.at(side * (27 + 15 * np.cos(a)), eye_y + 0.02 + 0.15 * np.sin(a))
            for a in np.linspace(0, 2 * np.pi, 40)]
    cv.tint(cv.polygon(np.array(ring)), '#ffffff', 'screen', 0.12)          # 렌즈 반사
    rings = np.maximum(rings, cv.ribbon(ring + ring[:1], 3.2, 'flat', smooth=False))
bridge = [head.at(-12, eye_y - 0.02), head.at(0, eye_y - 0.05, forward=0.04), head.at(12, eye_y - 0.02)]
cv.ink_mask(np.maximum(rings, cv.ribbon(bridge, 3.0, 'flat')), '#3a2a2a')
```

머리카락 밑에 들어가야 하는 소품(목걸이 등)은 위치가 옷이나 피부 위이므로 그대로 덧그리면 된다. 머리카락에 가려져야 하면 `* (1 - masks['front_hair'])`로 잘라낸다.

## 11. 한계

- 이 리그는 가슴 위 구도 전용이다. 전신과 손은 `draw_figure`, `draw_hand`를 쓴다 (`references/fullbody.md`)
- 상반신 리그의 몸은 정면 기준이라 40도까지만 돌린다. 옆얼굴과 뒷모습은 전신 리그를 `framing()`으로 줌해서 그린다 (`references/fullbody.md` 6, 8절)
- 표정은 눈썹 기울기, 눈꺼풀, 시선, 입꼬리, 입 벌림, 윗니 범위에서 바뀐다. 웃으며 감은 눈(^^), 눈물, 땀방울 같은 만화 기호는 직접 그려야 한다
- 이 범위를 넘는 요청은 `references/primitives.md`의 방법으로 직접 설계한다
