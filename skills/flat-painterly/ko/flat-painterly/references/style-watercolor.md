# 수채화풍

흰 종이 위에 맑은 색을 겹쳐 올리고 물, 안료, 종이의 흔적을 입히는 화풍. 예제는 `examples/watercolor_robin.py`(새와 꽃), `watercolor_still_life.py`(정물), `watercolor_old_town.py`(펜과 담채 거리), `watercolor_hand_studies.py`(손 습작), `watercolor_street_walk.py`(손잡고 걸어오는 두 사람), `watercolor_doomer_block.py`(올려다본 패널 아파트), `watercolor_doomer_kitchen.py`(밤 부엌 사물화).

## 시각 특징

- 가장 밝은 곳은 칠하지 않고 남긴 종이
- 붓 자국 가장자리에 물감이 몰려 진한 테두리가 생김
- 한 붓 자국 안에서도 농도가 얼룩지고 종이 결에 안료가 가라앉음
- 색이 겹친 곳은 두 색이 섞여 어두워짐
- 그림이 화면을 꽉 채우지 않고 번진 배경이 불규칙하게 끝남

## 작업 순서

1. 흰 배경 캔버스에서 시작
2. 배경 번짐: 큰 `g.blob`을 `watercolor.wash(..., soft=30-50, rough=20)`으로 2-4개 겹침
    + 주제 뒤에 주제의 보색을 옅게 깔아 주제를 띄움
    + 번짐 안에 흰색을 낮은 불투명도로 찍어 물이 고였다 마른 자리를 만듦
    + `motifs.splatter`로 물감 방울을 뿌림
3. 주제의 밑칠: 실루엣 전체를 가장 밝은 색으로 칠함
    + 흰 부분은 종이색으로 남기고 그늘만 `form_shadow(soft=0.3)`과 `Blend.MULTIPLY`로 옅게 넣음
4. 겹칠: 짙은 색을 `Blend.MULTIPLY`로 쌓음
    + 두 색이 만나는 경계는 형태에 soft를 주어 서로 스미게 함
    + `canvas.mottle`로 같은 색의 짙은 얼룩을 추가
5. 마른 붓 세부: 눈, 부리, 잔가지, 꽃술처럼 가장 어둡고 또렷한 것을 마지막에 그림
6. `watercolor.render(canvas)` 적용

## wash 인자

| 인자 | 기본값 | 조절 |
|---|---|---|
| `opacity` | 0.85 | 배경은 0.45-0.75, 주제는 0.85-0.95 |
| `soft` | 6 | 젖은 종이의 번짐 폭. 또렷한 부품은 1.5-2.5, 배경은 30-50 |
| `rough` | 7 | 가장자리 흔들림. 작은 부품은 2-3 |
| `cover` | False | 뒤 물체가 비치면 안 되는 앞 물체에 True |

## 패스 인자

| 인자 | 기본값 | 조절 |
|---|---|---|
| `wobble` | 2.2 | 윤곽 흔들림. 작은 세부가 일그러지면 내림 |
| `bleed` | 0.55 | 전체 번짐. 올리면 부드럽고 내리면 또렷 |
| `turbulence` | 0.30 | 큰 얼룩의 세기 |
| `granulation` | 0.22 | 종이 결에 가라앉는 입자의 세기 |
| `edge` | 0.55 | 가장자리 테두리의 세기 |

## 색

- 밑그림의 색은 완성본보다 밝고 맑게 잡음
    + 패스의 테두리 고임과 곱하기 겹칠이 색을 짙게 만듦
- 고채도 색은 주제의 한 부분에만 쓰고 나머지는 물을 많이 탄 옅은 색으로 구성
- 최암부에는 짙은 갈색이나 남색을 사용

## 흔한 결함

| 증상 | 처방 |
|---|---|
| 뒤의 가지가 앞의 새를 뚫고 비침 | 앞 물체의 wash에 `cover=True` |
| 배경 번짐이 겹친 곳이 너무 어두움 | 배경 wash의 opacity를 낮추거나 겹침 면적을 줄임 |
| 벡터 그림처럼 딱딱함 | 큰 면의 soft와 rough를 올리고 `mottle`로 얼룩을 추가 |
| 전체가 흐릿함 | `bleed`를 내리고 마지막 세부를 soft 없이 그림 |
| 흰 물체의 형태가 안 보임 | 뒤에 배경 번짐을 깔고 그늘을 MULTIPLY로 옅게 넣음 |
| 건물과 기물의 직선이 흐물거림 | wash의 soft 1.5, rough 2.5로 줄이고 패스의 wobble을 1.4 이하로 낮춤 |

## 출처

> Bousseau, Kaplan, Thollot, Sillion(2006), Interactive watercolor rendering with temporal coherence and abstraction(https://dl.acm.org/doi/10.1145/1124728.1124751)

## 3차원 인물

- `character.paint_figure`로 칠한 인물은 선을 가늘고 옅게(`line_opacity` 0.55) 둔 Ink로 칠한 뒤 수채화 패스를 거침
    + 살과 옷은 맑은 밝은 색으로 두고 배경만 `wash`로 겹칠함
    + 패스의 wobble 1.6, bleed 0.65 안팎이면 인물 윤곽이 번지되 얼굴이 읽힘
