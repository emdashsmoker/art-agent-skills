# 화풍, 조명, 매체, 마감

## 목차
- 사용법
- 화풍 프리셋
- 두머 화풍
- 조명 프리셋
- 매체 파라미터
- 마감 패스
- 프리셋에 없는 화풍 구성
- 색 계획 도구

## 사용법

```python
from atelier import paint, light, render, finish
image = paint(canvas, "watercolor", light("golden_hour"))                    # 프리셋 그대로
image = paint(canvas, "oil", scene_light, params=dict(radii=(20, 10, 5), impasto=1.0),
              extra_finish=[("vignette", dict(strength=0.3))])               # 파라미터 덮어쓰기와 마감 추가
image = render(canvas, "gouache", scene_light, groups={"figure": ("cel", dict(bands=3))})   # 매체 직접 지정
```

- `paint`는 화풍 프리셋의 매체로 렌더한 뒤 마감 패스를 순서대로 적용
- 장면 스크립트에서는 `build`의 반환 사전에 `style_params`를 넣어 그 장면에서만 매체 파라미터를 바꿈
    + `return {"views": [view], "style_params": {"pastel": dict(paper="#8e99ae", grain=0.45)}}`
    + 화풍 이름별로 적용되므로 `--styles`로 다른 화풍을 비교해도 해당 화풍에만 들어감
    + 예시: 눈 풍경의 밝은 청회색 파스텔지 (`scene_snow_forest.py`), 인상주의 붓 크기와 색 흔들림 축소 (`scene_beach_sunset.py`)
- `render`는 매체만 적용, `groups`로 레이어 그룹별 매체를 다르게 지정 가능
- `studio.run`에서는 `--style`, `--light`, `--styles` 옵션으로 같은 기능을 사용

## 화풍 프리셋

| 키 | 매체 | 얼굴 | 특징 |
|---|---|---|---|
| anime_cel | cel | anime | 2단 음영, 색 트레이스 선, 약한 확산광 |
| anime_film | gouache + cel | semi | 과슈 배경, 3단 음영 인물, 필름 합성 (확산광, 색수차, 그레인) |
| retro_anime | gouache + cel | anime | 검은 선, 딱딱한 그림자, 높은 채도, 굵은 그레인 |
| webtoon | cel | semi | 부드러운 음영 경계, 블룸 |
| manga | halftone (mono) | anime | 흑백 스크린톤 |
| flat_vector | flat | anime | 음영과 선 없는 평면 색 |
| flat_shadow | cel | anime | 선 없는 평면 색과 1단 그림자 |
| poster | gouache | semi | 3단 명도의 포스터 컬러 |
| storybook | watercolor | anime | 연필선 수채, 종이 여백 테두리 |
| pop_art | halftone | semi | 벤데이 점과 굵은 검은 선 |
| art_nouveau | woodblock | semi | 평면 색과 장식적 선, 바랜 종이 |
| renaissance | oil | classic | 가는 붓, 어두운 밑칠, 엄버 글레이즈, 균열 |
| baroque | oil | classic | 강한 명암 대비, 어두운 배경 |
| academic | oil | classic | 매끈한 붓질, 밝은 밑칠 |
| oil | oil | classic | 기본 유화 |
| impressionism | oil | classic | 짧고 두꺼운 붓질, 분할된 색 |
| post_impressionism | oil | classic | 길게 소용돌이치는 붓질, 높은 채도 |
| expressionism | oil | classic | 큰 붓, 과장된 색, 윤곽선 |
| fauvism | oil | classic | 원색에 가까운 채도 |
| pointillism | pointillism | classic | 색점 분할 |
| cubism | facets | classic | 면 분할, 차분한 색 |
| sumi_e | ink | semi | 수묵, 5단 농담, 여백 |
| ink_color | ink | semi | 수묵담채 |
| ukiyo_e | woodblock | semi | 평면 색, 보카시, 먹선 |
| minhwa | woodblock | semi | 한지 위 오방색 계열 평면 채색 |
| pencil | pencil | classic | 흑연 해칭 |
| colored_pencil | pencil | semi | 색연필 |
| charcoal | charcoal | classic | 번진 목탄 |
| pastel | pastel | classic | 유색지 위 파스텔 |
| watercolor | watercolor | semi | 투명 수채, 연필선 |
| watercolor_loose | watercolor | semi | 번짐이 큰 수채, 선 없음 |
| urban_sketch | watercolor | semi | 잉크 선과 수채 |
| doomer | gouache + cel | semi | 바랜 색, 청흑색 그림자, 나트륨등과 창빛의 번짐, 필름 그레인, 인물은 광원색이 스미는 2단 셀 |
| doomer_mono | gouache + cel | semi | 같은 세계의 흑백 복사본, 눌린 검정, 거친 토너 그레인 |

## 두머 화풍

구소련권 교외의 겨울밤을 바랜 사진처럼 그리는 화풍. 특정 음반 표지나 캐릭터를 옮기지 않고 일반적인 사물로 분위기를 구성함.

| 요소 | 도구 |
|---|---|
| 장소 | `city.building(kind="panel")` 패널 아파트, `city.pylon`과 `city.wires(painted=True)`, `city.chimney`, `scenery.bare_tree(birch=True)`, `city.struts`로 놀이터 철골 |
| 빛 | 나트륨등 `#ffb468`, 수은등 `#a4b4d4`, 창빛 (패널 입면이 밤에 무작위로 켬), 도시 불빛이 비치는 하늘 |
| 인물 | `Hair("beanie")`, `wardrobe.hoodie`, `turtleneck`, 긴 `coat`, `expression="tired"`, 입에 문 `props.cigarette`와 `props.smoke` |
| 날씨 | `weather("snow")` 2층, 진창 노면의 `wet_reflection` |

- doomer는 밤, doomer_mono는 흐린 낮이나 눈 오는 들판에 맞춤
    + doomer는 채도를 0.72로 낮추고 밝은 곳을 번지게 하므로 창빛과 가로등이 화면의 유일한 따뜻한 색으로 남음
    + doomer_mono는 대비 1.4의 흑백이므로 하늘과 눈밭을 밝게, 철탑과 나무를 어둡게 두어 실루엣으로 읽히게 함
- 인물 조명은 한쪽 가로등 1개를 주광으로 두고 반대쪽은 청흑색 그림자로 둠
    + 주광 색이 얼굴에 스미도록 `key_color=0.6`이 프리셋에 들어 있음
    + 뒷모습이나 역광 장면은 `rim`이 있는 조명을 쓰면 외곽에 가는 테가 생김 (`doomer_duo.py`)
- 어두운 화면에서 형태가 사라지지 않게 3단 명도를 러프에서 확인 (하늘, 건물, 창빛의 3층)
- 예제: `doomer_male.py`, `doomer_female.py`, `doomer_duo.py`, `doomer_establishing.py`, `doomer_city.py`, `doomer_landscape.py`, `doomer_still_life.py`

## 조명 프리셋

```python
light("rembrandt", azimuth=-45, elevation=38)      # 프리셋에 인자 덮어쓰기
```

| 키 | 방향과 성격 |
|---|---|
| studio | 왼쪽 위 45도, 중립 |
| soft_front | 정면에 가까운 부드러운 빛, 얼굴에 그림자가 적음 |
| rembrandt | 왼쪽 위 측면의 따뜻한 빛, 깊은 그림자 |
| side | 수평에 가까운 측광 |
| top | 머리 위 조명 |
| backlit | 역광, 윤곽광 |
| golden_hour | 낮고 따뜻한 빛, 보랏빛 그림자, 따뜻한 대기 |
| noon | 높은 해, 푸른 그림자 |
| overcast | 확산광, 약한 그림자 |
| blue_hour | 차가운 저조도 |
| night | 달빛 |
| candle | 낮고 붉은 근접광 |

- `Light` 인자

| 인자 | 의미 |
|---|---|
| azimuth | -90 왼쪽, 0 정면, 90 오른쪽, 150 이상은 뒤쪽 |
| elevation | 0 수평, 90 머리 위 |
| color, shadow_tint | 빛의 색, 그림자 쪽에 곱해지는 색 |
| wrap | 빛이 형태를 감싸는 정도 (클수록 부드러움) |
| shadow_strength | 드리운 그림자 강도 |
| haze, haze_strength | 대기색과 원경 흐림 강도 |
| rim | 윤곽광 강도 |
| bounce, bounce_color | 그림자 쪽으로 되돌아오는 반사광의 세기와 색 (명암 경계가 가장 어둡게 남음) |
| flush | 피부처럼 부드러운 재질의 명암 경계 안쪽에 도는 따뜻한 기운 |

- 그림자색은 빛의 보색 쪽으로 기울임 (따뜻한 빛에는 푸른 보라 그림자)
- 기준 렌더의 명암 단계: 밝은 면, 중간 톤, 명암 경계(core shadow), 반사광, 접촉 그림자(ambient occlusion)
    + 접촉 그림자는 주름, 겨드랑이, 사물이 닿는 자리처럼 빛 방향과 무관하게 어두운 곳
    + 직접 지정: `canvas.occlude(형태, 강도, blur, clip)`

## 매체 파라미터

### cel
| 인자 | 의미 |
|---|---|
| bands | 1 평면, 2 기본과 그림자, 3 깊은 그림자 추가 |
| soft | 음영 경계 폭 (0.015 또렷함, 0.13 에어브러시) |
| shadow_at, deep_at | 그림자가 시작되는 밝기 |
| simplify | 그림자 형태 단순화 정도 |
| shadow_tint, shadow_saturation | 그림자 색 |
| highlight | 광택 하이라이트 강도 |
| lines | trace (색 트레이스), black, sepia, none |
| key_color | 0-1, 밝은 쪽에 주광의 색을 섞는 정도 (기본 0은 고유색 유지, 나트륨등 아래 얼굴처럼 광원색이 필요할 때 0.5-0.7) |
| rim | 0-1, 조명의 `rim` 값으로 빛을 향한 외곽에 밝은 테를 그림 (역광 실루엣) |

### watercolor
| 인자 | 의미 |
|---|---|
| wetness | 번짐 정도 (0 또렷함, 1 매우 젖음) |
| edge_darkening | 물감이 가장자리에 고이는 정도 |
| granulation | 종이결에 안료가 가라앉는 정도 |
| bloom | 물 얼룩 |
| wobble_px | 손으로 그린 듯한 외곽 흔들림 |
| glazes | 그림자 겹칠 횟수 |
| reserve | 밝은 부분의 종이 여백 |
| lines | pencil, ink, none |
| border | 칠하지 않은 종이 테두리 폭 |

### oil
| 인자 | 의미 |
|---|---|
| radii | 붓 반지름 목록, 큰 것부터. 작은 값을 빼면 거친 그림 |
| threshold | 덧칠 기준 오차 (클수록 성긴 붓질) |
| length | 붓질 길이 (최소, 최대) |
| curvature | 붓질이 방향을 유지하는 정도 |
| jitter, hue_jitter | 붓질별 명도, 색상 흔들림 |
| swirl | 붓 방향의 소용돌이 |
| impasto | 물감 두께의 입체감 |
| ground | 밑칠 색 |
| vivid | 채도 배율 |
| line_strength | 밑그림 선이 그림에 남는 정도 |
| focus_radii | 초점 영역(얼굴)에만 쓰는 가는 붓 |

### gouache
| 인자 | 의미 |
|---|---|
| steps | 명도 단계 수 |
| soft | 단계 사이 섞임 |
| brush | 붓 자국 강도 |
| wobble_px | 외곽 흔들림 (건축물은 0.5 이하) |

### ink
| 인자 | 의미 |
|---|---|
| tones | 먹 농담 단계 |
| bleed | 번짐 |
| dry_brush | 갈필 |
| color | 담채 강도 (0 수묵, 0.5 담채) |
| mist | 원경이 여백으로 사라지는 정도 |

### pencil, charcoal, pastel
| 인자 | 의미 |
|---|---|
| spacing, layers | 해칭 간격과 겹 수 (pencil) |
| softness | 문지른 정도 |
| color | 0 흑연, 1 색연필 |
| paper | 종이색 (pastel은 유색지) |
| grain | 종이결 노출 (pastel) |

### woodblock, halftone, pointillism, facets
| 매체 | 주요 인자 |
|---|---|
| woodblock | bands, bokashi (상단 그라데이션), misregister (판 어긋남), mute (채도), paper |
| halftone | dot (점 간격), mono (흑백 스크린톤), vivid |
| pointillism | dot (점 크기), divide (색 분할 정도), passes |
| facets | cell (면 크기), mute, tilt (면 음영) |

## 마감 패스

| 함수 | 용도 |
|---|---|
| `grade(image, contrast, saturation, temperature, exposure, gamma)` | 색보정 |
| `bloom(image, threshold, radius, strength)` | 밝은 부분의 빛 번짐 |
| `diffusion(image, radius, strength)` | 애니메 촬영 효과의 확산광 |
| `light_wash(image, direction, color, strength)` | 화면 전체의 방향성 빛 그라데이션 |
| `vignette(image, strength, softness)` | 가장자리 어둡게 |
| `glaze(image, color, strength)` | 전체에 투명한 색층 (고전 회화의 따뜻한 색조) |
| `grain(image, amount, size)` | 필름 그레인 |
| `craquelure(image, scale, strength)` | 오래된 유화의 균열 |
| `chromatic(image, pixels)` | 렌즈 색수차 |
| `seal(image, x, y, size)` | 낙관 |
| `mat(image, margin, color)` | 액자 여백 |

- 마감은 약하게 적용 (효과가 그림보다 먼저 보이면 과함)
- `paint(..., extra_finish=[("함수 이름", dict(인자))])`로 추가

## 프리셋에 없는 화풍 구성

- 가장 가까운 프리셋을 고른 뒤 3가지를 조정: 매체 파라미터, 조명, 마감
- 구성 예시

| 목표 | 구성 |
|---|---|
| 지브리풍 배경 | gouache (steps 5, soft 0.25), noon 조명, 채도 1.1 |
| 신카이풍 하늘 | cel 인물과 gouache 배경, golden_hour, bloom과 light_wash 강화 |
| 로코코 | academic에 pastel 팔레트, soft_front 조명 |
| 낭만주의 풍경 | oil (radii 20, 10, 5, 2.5), golden_hour, vignette 0.3 |
| 고흐풍 | post_impressionism에 swirl 0.5, 보색 팔레트 |
| 모네풍 | impressionism에 hue_jitter 0.05, overcast 조명 |
| 무하풍 | art_nouveau에 굵은 외곽선(line_width 증가), 원형 후광 도형 |
| 팝아트 초상 | pop_art에 원색 배경, vivid 1.8 |
| 느와르 | charcoal 또는 cel (bands 2)에 side 조명, noir 팔레트 |
| 사이버펑크 | anime_cel에 night 조명, 네온색 unlit 도형, bloom 강화 |
| 비 오는 밤 애니메 | retro_anime에 night 조명(shadow_tint 밝게), `weather("rain")` 2층, `wet_reflection`, finish glow |
| 촛불 명암 (테네브리즘) | baroque에 candle 계열 조명(elevation 5-10), 어두운 배경과 초 주변 벽의 빛무리, `objects.candle` |
| 동양화 채색 | ink_color에 color 0.7 |
| 판타지 컨셉 아트 | oil (focus_radii 유지), backlit 조명, bloom |

- 화풍의 본질은 구조 단계에서도 반영
    + 우키요에는 평면적 구도와 큰 여백, 아르누보는 곡선 장식과 원형 후광, 큐비즘은 정면과 측면의 동시 배치
- 새 조합은 `--styles`로 기존 프리셋과 나란히 렌더하여 비교

## 색 계획 도구

```python
from atelier import palette
palette.harmony("#2f8f8a", "analogous")        # 유사색 3개
palette.harmony("#c8553d", "complementary")    # 보색 쌍
palette.ramp("#6b8ec2", steps=5)               # 어두운 쪽은 차갑게, 밝은 쪽은 따뜻하게 변하는 명도 단계
palette.mute("#c8553d", 0.4)                   # 채도 낮추기
palette.NAMED["earth"]                         # 명명 팔레트
```

- 조합: monochrome, analogous, complementary, split, triad, tetrad
- 명명 팔레트: earth, impressionist, ukiyo, pastel, noir, sunset, forest, ocean, minhwa, doomer
- 배색 비율은 주조색 60, 보조색 30, 강조색 10 내외
- 강조색은 시선 지점에만 사용
