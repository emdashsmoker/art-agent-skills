# 확장과 한계

카탈로그 밖의 형태와 화풍을 만드는 방법, 엔진의 현재 한계, 발전 방향

## Python API

사양 파일로 표현하기 어려운 장면은 Python으로 직접 구성. 작업 디렉터리에서 `scripts`를 경로에 추가

```python
import sys; sys.path.insert(0, "scripts")
from atelier.scene import Scene
from atelier.styles import render_style
from atelier import spec, props

scene = Scene(width=832, height=1040, seed=7)
scene.set_studio(top=(0.12, 0.10, 0.08), bottom=(0.20, 0.15, 0.11), glow=(0.40, 0.32, 0.22))
figure = scene.add_figure("a", preset="woman", pose={"preset": "stand", "reach.R": "heart"},
                          hair={"style": "bob", "bangs": "side", "color": "black"}, outfit="chiton")
scene.add_prop("column", at=(1.2, 0.8, 0), height=3.0)
scene.set_camera(subject="a", shot="cowboy", yaw=-15)
scene.set_light("rembrandt", mood="old_master")
frame = scene.frame()                       # 형태 층 완성. 화풍을 바꿔도 다시 만들 필요 없음
spec.save(render_style(frame, "classical"), "out.png")
```

- 몸이 닿는 투샷은 `scene.add_pair("hug", a={...}, b={...})`. `a`, `b`는 `add_figure` 인자
- 3명 이상이 옆 사람과 닿는 줄은 `scene.add_group("arm_around", members=[{...}, {...}, {...}])`
- 풍경 속 인물만 담는 카메라는 `scene.set_camera(fit="people", shot="cowboy")`
- `scene.frame()`은 한 번만 호출하고 `render_style`을 여러 화풍으로 반복 호출 가능
- 사양 파일에서 출발하려면 `scene = spec.build_scene(spec.load("spec.json"))` 후 장면에 요소를 추가

### 인물에 사물 붙이기

```python
scene.add_prop("wine_glass", held_by="a:hand.R")      # 손에 쥠 (컵, 병은 세워서, 책과 휴대폰은 손바닥 위에)
centre, normal, fingers = figure.palm("R")            # 손바닥 중심, 손바닥이 향하는 방향, 손가락 방향 (월드 좌표)
wrist = figure.bone_head("wrist.R")                   # 뼈 위치 (월드 좌표)
point = figure.landmark("heart", offset=0.03)         # 신체 지점 (월드 좌표)
```

- 새 사물을 손바닥 위에 눕혀 들게 하려면 `props.HOLD_STYLES`에 `"이름": "rest"` 추가

### 직접 만든 형태 추가

```python
import numpy as np
from atelier import props

# 회전체: 옆모습 윤곽 [(반지름, 높이), ...]
goblet = props.lathe([(0.04, 0), (0.005, 0.02), (0.005, 0.10), (0.05, 0.16)], "goblet")
scene.add_mesh(goblet.transformed(props.transform((0.3, 0, 0.74))), color=(0.8, 0.7, 0.3))

# 기본 도형: box, sphere, cylinder, cone, plane, tube(경로를 따라가는 관), torus, blob(울퉁불퉁한 덩어리)
arch = props.tube([[np.cos(t) * 1.2, 0, 1.2 + np.sin(t) * 1.2] for t in np.linspace(0, np.pi, 24)], 0.12, "arch")
scene.add_mesh(arch, color=(0.85, 0.83, 0.78))
```

- 복잡한 사물은 기본 도형 여러 개의 조합으로 구성. 같은 `part` 이름을 주면 외곽선이 하나의 물체로 그려짐
- 재질 이름이 `.flame`, `.screen`, `.bulb`로 끝나면 스스로 빛나는 면으로 처리. 이 면은 주변도 자동으로 비춤
- 보이지 않는 광원은 `scene.add_light(at, color, power, direction)`
- 둥근 모서리 기기는 `modern.rounded_slab(size, radius, material, axis)`로 제작. `axis="y"`는 정면(-Y)을 향해 선 판

### 표면 요철 추가

페인터가 `g["bump"]`에 높이(미터, 바깥쪽이 양수)를 더하면 조명 전에 법선이 기울어짐. 모든 화풍에서 빛 방향에 맞는 음영이 생김

```python
def dimples(g, albedo, glow_rgb, glow_alpha):
    mask = material_mask(g, "ball.ball")
    local = g["attrs"]["tpl"]
    pits = (np.sin(local[..., 0] * 300) * np.sin(local[..., 2] * 300) > 0.7) * mask
    g["bump"] = g.get("bump", 0.0) - pits * 0.001

scene.painters.append(dimples)
```

### 표면 무늬 추가

표면색은 "페인터" 함수가 화면 공간에서 칠함. 버퍼의 좌표를 읽어 색을 바꾸는 함수를 등록

```python
from atelier.shade import material_mask

def stripes(g, albedo, glow_rgb, glow_alpha):
    mask = material_mask(g, "a.dress")
    height = g["attrs"]["tpl"][..., 2]                # 신체 고정 좌표. 자세가 바뀌어도 무늬가 따라옴
    band = (np.floor(height / 0.04) % 2 == 0) & mask
    albedo[band] = (0.15, 0.2, 0.5)

scene.painters.append(stripes)
```

- `g["attrs"]["tpl"]`은 인물과 의상에서는 신체 고정 좌표, 사물에서는 사물 자체 좌표
- `g["position"]`은 월드 좌표, `g["normal"]`은 표면 방향, `g["uv"]`는 피부의 UV

### 새 화풍 추가

화풍은 `frame`을 받아 이미지를 돌려주는 함수. 기존 매체를 조합하는 방식이 가장 쉬움

```python
from atelier import media_cel, media_oil, media_common as mc, styles

def poster(F, **params):
    plan = media_cel.render_cel(F, line_width=0, shadow_threshold=0.5, saturation=1.3)
    return mc.quantize_to_palette(plan, [(0.95, 0.9, 0.8), (0.8, 0.2, 0.15), (0.1, 0.15, 0.3), (0.95, 0.7, 0.2)])

styles.STYLES["poster"] = dict(fn=poster, params={}, post={}, about="4색 포스터")
```

- 매체가 쓰는 재료: `F.albedo`(바탕색), `F.tone`과 `F.lit`(명암), `F.reference()`(관찰용 연속 톤 그림), `F.over_background()`(배경 합성), `F.focus`(중요도), `mc.outline()`(선), `media_oil.paint()`(붓질), `mc.paper_height()`(종이 결)

## 모듈 구성

| 모듈 | 역할 |
| --- | --- |
| `figure.py`, `poses.py`, `people.py`, `skin.py` | 인체 메시, 자세 언어와 역운동학, 인물 프리셋, 얼굴 채색 |
| `hair.py`, `garment.py` | 머리카락 생성, 의상 재단 |
| `props.py`, `landscape.py` | 사물, 지형과 하늘과 나무와 도시 |
| `scene.py`, `camera.py`, `spec.py` | 장면 조립, 카메라, 사양 해석 |
| `raster.py`, `gbuffer.py`, `shade.py`, `line.py` | 래스터화, 기하 버퍼, 조명, 외곽선 |
| `media_*.py`, `styles.py`, `post.py` | 매체, 화풍 등록부, 마감 |

## 현재 한계

| 영역 | 한계 | 우회 방법 |
| --- | --- | --- |
| 옷 주름 | 물리 시뮬레이션 없음. 세로 주름과 관절 주름을 형태로 생성 | `folds`와 `fold_count` 조정, 몸에 붙는 옷과 A라인 치마가 가장 안정적 |
| 넓은 소매, 망토 | 전용 형태 없음 | `ease`를 키운 상의로 근사, 또는 `props.tube`로 직접 제작 |
| 머리카락 | 다발 단위. 가닥 표현과 땋은 머리 없음 | 회화 화풍에서는 다발이 붓질로 자연스럽게 녹음 |
| 얼굴 | 데포르메는 `stylize`의 4단계까지 | `chibi` 이상의 2등신 비례는 몸 모핑과 함께 직접 구성 |
| 접촉 | 손가락이 사물 표면을 감싸는 정밀 접촉 미지원. `held_by`는 손바닥 기준 배치 | 짝이 맞는 자세(`hold_cup`, `read_book`, `look_at_phone`)와 함께 사용 |
| 신발 | 굽 없음 | `footwear`의 양말형 신발 |
| 질감 | 금속 반사, 유리 굴절, 천의 직조 없음 | 화풍의 붓질과 색으로 암시 |
| 풍경 | 풀잎, 나뭇잎 개별 표현 없음. 건물은 처마와 발코니가 있는 직육면체 계열 | 회화 화풍과 대기 원근으로 보완 |
| 해상도 | 긴 변 2048px 권장 상한 | 유화 계열은 `fine` 이상에서 시간이 길어짐 |

- 한계에 걸리는 요청은 가능한 근사를 제시하고 차이를 사용자에게 명시

## 발전 방향

- 형태 층: 천 시뮬레이션, 가닥 머리카락, 손의 접촉 해석, 건축과 탈것 카탈로그, 동물
- 매체 층: 붓질 단위 물리(물감 섞임, 물의 확산), 화가별 붓질 어휘
- 기획 층: 참고 이미지에서 자세와 구도 추출, 구도 자동 평가
- 형태가 기하로 확정되므로 각 개선은 손가락 수 같은 구조적 정확성을 해치지 않고 누적됨
