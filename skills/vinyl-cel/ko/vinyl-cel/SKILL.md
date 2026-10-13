---
name: vinyl-cel
description: 비닐 피규어처럼 둥글고 매끈한 인물과 사물을 셀 음영과 색 선화로 칠하는 코드 작화 스킬. 구, 타원체, 부호 거리 함수로 형태를 빚고 깊이 지도로 조명하여 정면이 열린 무대 세트 같은 디오라마 장면을 PNG로 그린다. 마감은 애니메(2단 셀 음영과 림라이트), 일러스트(연속 음영과 종이 입자), 회화(다층 붓질과 물감 요철) 가운데 고른다. 필름 같은 색보정 프리셋을 어느 마감 위에나 덧입힐 수 있다. 생성 모델 없이 numpy와 opencv만 쓰므로 같은 시드는 같은 그림을 만든다. 초상, 모든 각도의 3D 인물(남녀 4체형, 27개 자세, 13벌 의상), 현대 사물과 가구, 거실, 사무실, 카페, 침실, 가로등과 전선이 있는 눈 내린 밤거리, 풍경, 도시, 정물을 지원한다. 참조 문서는 references/subjects.md(소재별 구성과 한계), references/pipeline.md(공정 원리와 디자인 방향 문서 양식), references/api.md(좌표계와 모듈 함수), references/styles.md(화풍과 색보정 상수), references/qa.md(검수 항목과 증상별 처방)이다. 사용자가 "코드로 그림 그려줘", "확산모델 없이 캐릭터 그려줘", "피규어 같은 셀화", "디오라마 일러스트", "캐릭터 턴어라운드", "포즈 시트", "의상 시트", "카페 장면", "침실 장면", "눈 내리는 밤거리 그림", "애니메풍 이미지를 코드로", "procedural illustration", "/vinyl-cel" 등을 요청하거나 이미지 생성 모델을 쓸 수 없는 환경에서 그림이 필요하면 반드시 이 스킬을 사용할 것. 차트, 도식, 아이콘, 로고 제작에는 사용하지 않는다.
license: GPL-3.0-or-later, Copyright (C) 2026 Em Dash Smoker. Images rendered with the skill are free of GPL conditions (output exception). Terms in LICENSE and THIRD_PARTY_NOTICES.md
---

# 비닐 셀화(vinyl-cel)

코드만으로 인물, 풍경, 도시, 정물을 그리는 스킬. 산출물은 PNG 파일이며 동일 입력과 동일 시드는 동일 파일을 만든다.

## 전제

- 이미지 생성 모델, 생성형 API, 외부 네트워크 호출을 사용하지 않음
    + 본 스킬의 존재 이유가 코드 기반 작화이므로 생성 모델 호출은 과제 자체를 무효화함
- 의존성은 `numpy`와 `opencv-python` 2개
    + 작업 시작 시 import 가능 여부를 먼저 확인하고 없으면 설치
- 지원 소재는 10종이며 소재마다 출발점이 되는 예제 장면이 있음(아래 표)
    + 2D 인물 리그는 초상(정면에서 반측면, yaw 절대값 0.3 이내)과 정면 입상 전신
    + 3D 인물은 모든 각도(정면, 3/4, 측면, 뒷모습)와 서기, 걷기, 달리기, 앉기, 무릎 꿇기, 눕기를 지원하며 남녀 성인 4체형에 의상을 갈아입히는 구조
    + 3D 장면은 현대 사물 22종(유리컵, 케이블, 재떨이, 카세트 포함), 가구 15종(침대, 라디에이터 포함), 실내 4종(거실, 사무실, 카페, 침실)을 인물과 하나의 원근 카메라로 묶음
    + 야외 3D 장면은 패널 아파트, 땅(눈밭, 도로), 하늘, 거리 소품 5종, 날씨(안개, 눈)를 같은 카메라로 묶고 가로등 빛이 땅과 인물을 함께 비춤
    + 동물, 곡예 자세(물구나무, 공중회전), 두 인물이 맞닿는 자세(포옹, 업기)는 리그에 없으므로 요청받으면 한계를 먼저 알리고 확장 여부를 질의

## 작동 원리

- 그림은 공정의 누적이며 각 공정은 규칙으로 기술 가능
    + 밑색, 음영, 선화는 하나의 도형 마스크에서 파생되므로 `painter.part()` 호출 1회가 3개 공정을 수행
- 둥근 형태가 겹치는 소재는 높이 지도로 합쳐서 조명
    + `Relief`가 팔다리, 손가락, 과일을 부풀려 하나의 표면으로 만들고 음영, 서로 드리우는 그림자, 가림 선을 계산
- 원근은 투영으로 계산
    + 지형은 높이 지도를 카메라로 투영, 거리는 평면 텍스처를 1점 투시로 변환
- 비례는 리그에 내장
    + 장면 스크립트는 데이터와 관절 각도만 바꾸므로 얼굴과 인체 비례가 무너지는 실수를 구조적으로 차단
- 3D 인물은 해석적 깊이 렌더러로 깊이 지도를 만든 뒤 같은 `Relief`로 조명
    + 몸, 머리카락, 옷이 모두 타원체와 구 사슬이므로 카메라 각도만 바꾸면 같은 인물이 모든 방향에서 그려짐
    + 손이 목표점에 닿는 자세는 역운동학이 팔 각도를 계산하므로 어떤 체형에도 맞음
    + 바닥에 닿는 부위는 가장 낮은 신체 부위로 계산하므로 선 인물, 누운 인물, 무릎 꿇은 인물이 같은 배치 함수로 바닥에 놓임
    + 끈과 띠는 몸통 표면 밖으로 밀어낸 경로를 따르므로 어느 각도에서도 끊기지 않음
    + 얼굴의 눈, 입, 눈썹은 2D 초상 리그를 얼굴 앞면에 붙여 그리므로 애니메 얼굴의 인상이 유지됨
- 각진 현대 사물은 부호 거리 함수로 기술하고 화소마다 광선을 진행시켜 깊이를 구함
    + 모서리 둥근 상자, 판, 원기둥, 원뿔대, 고리와 그 조합이 노트북, 모니터, 머그컵, 책상을 만듦
    + 같은 깊이 지도가 같은 `Relief`를 거치므로 사물과 인물의 화풍이 일치
    + 투명한 유리는 불투명 공정 뒤 별도 버퍼로 그려 뒤에 있는 것이 비쳐 보이게 합성
- 장면은 공통 카메라 1개와 깊이 버퍼 1개로 그림
    + 인물, 가구, 사물이 서로 가리므로 책상이 다리를 가리고 손이 자판 위에 놓임
    + 카메라 거리를 지정하면 원근 투영, 지정하지 않으면 v4와 같은 정사영
    + 실내의 벽과 바닥은 같은 카메라로 투영한 평면 그림이므로 가구와 소실 방향이 맞음
- 품질은 렌더 후 확인하는 횟수에 비례
    + 좌표만으로는 매력을 판단할 수 없으므로 매 수정마다 미리보기를 렌더하여 직접 열어 확인

## 공정

1. (기획) 디자인 방향 문서를 먼저 작성
    + 핵심 메시지 1개, 구도, 팔레트, 광원 방향, 화풍을 확정, 양식은 `references/pipeline.md`
2. (점검) `python scripts/selftest.py` 실행
    + 전 항목 PASS 확인 후 진행
3. (작도) 소재에 맞는 예제 장면을 작업 폴더로 복사하여 수정
    + 초상은 `scripts/scene_template.py`, 그 외는 `scripts/examples/`의 해당 파일
    + 인물은 `Character` 데이터, 배경과 소품은 `compose()` 함수
    + 복사한 스크립트는 환경변수 `CODEILLUST_HOME`(본 스킬의 `scripts` 폴더 경로)으로 툴킷을 찾음
4. (미리보기) `CODEILLUST_HOME=<스킬>/scripts python <scene>.py --style <화풍> --preview --out out/`
    + 2-10초 소요, `_overview.png`가 함께 생성되고 얼굴이 있으면 `_face.png`도 생성
5. (검수) 생성된 검수용 이미지를 직접 열어 `references/qa.md` 기준으로 점검
    + 결함 발견 시 데이터나 상수를 고친 뒤 4단계 반복, 결함이 없을 때까지 지속
6. (최종) `--preview` 없이 렌더하여 긴 변 2133픽셀 PNG 산출
    + 화풍당 5-50초 소요(도시 장면이 가장 김)
    + 3D 인물은 1명당 미리보기 약 2초, 최종 5-15초(캔버스가 클수록 김)이므로 19명이 든 자세 시트는 최종 화풍당 5-7분
    + 실내 장면은 미리보기 8-12초, 최종 화풍당 40-120초
    + 야외 장면은 미리보기 4-30초, 최종 화풍당 15-40초(자작나무가 많을수록 김)

## 소재별 출발점

| 소재 | 예제 장면 | 핵심 모듈 | 방식 |
|---|---|---|---|
| 상반신 초상 | `scene_template.py` | `figure`, `rig_face`, `rig_hair`, `rig_body` | 마스크 레시피 |
| 전신 인물(정면) | `examples/full_body.py`, `examples/swimwear_beach.py` | `rig_figure`, `rig_hand` | 관절 골격과 입체 렌더러 |
| 옷 갈아입히기 베이스(정면) | `examples/dressup_base.py` | `rig_figure` | 같은 몸에 의상 레이어 교체 |
| 3D 인물 턴어라운드 | `examples/turnaround3d.py` | `figure3d`, `rig3d`, `head3d`, `wardrobe3d` | 3D 깊이 렌더러, 카메라 yaw만 변경 |
| 3D 자세 시트 | `examples/pose_sheet3d.py` | `rig3d` | 관절 회전과 역운동학 |
| 3D 의상 시트(남녀) | `examples/outfits3d.py` | `wardrobe3d` | 몸을 띄운 옷 레이어 |
| 3D 완성 장면 | `examples/beach_pair3d.py` | `figure3d`, `background` | 배경 위에 3D 인물 2명 |
| 손 | `examples/hand_study.py` | `rig_hand` | 손바닥과 마디, 입체 렌더러 |
| 풍경화 | `examples/landscape_lake.py` | `terrain`, `scenery`, `background` | 높이 지도 지형 투영 |
| 도시 풍경 | `examples/city_dusk.py` | `city`, `background` | 1점 투시와 입면 텍스처 |
| 정물화 | `examples/still_life.py` | `stilllife`, `relief` | 회전체와 구, 입체 렌더러 |
| 현대 사물 시트 | `examples/props_sheet3d.py` | `props3d`, `sdf3d` | 각진 형태, 발광 화면 |
| 현대 정물(책상) | `examples/desk_setup3d.py` | `props3d`, `furniture3d`, `interior` | 사물을 책상 상판 기준점에 배치, 맞춤 방 |
| 책상 앞 인물 | `examples/desk_worker3d.py` | `scene3d`, `interior.office` | 앉은 인물과 책상을 한 깊이 버퍼에 |
| 거실 장면 | `examples/living_game3d.py` | `interior.living_room`, `props3d.held_*` | 소파의 두 인물, 컨트롤러와 머그컵 |
| 카페 장면 | `examples/cafe3d.py` | `interior.cafe`, `props3d.held_phone` | 휴대전화를 든 치마 입은 앉은 인물, 유리컵 |
| 침실 장면 | `examples/bedroom3d.py` | `interior.bedroom`, `furniture3d.bed` | 침대에 엎드린 인물, 가장 낮은 부위로 접지 |
| 밤의 책상 | `examples/night_desk.py` | `outdoor.draw_lit_room`, `grade` | 노트북 화면빛과 스탠드가 비추는 작업하는 여성, 세로 |
| 오후의 창가 | `examples/sunny_reading.py` | `draw_lit_room`, `window(..., "golden")` | 늦은 햇살이 드는 소파의 여성, 가로 |
| 노을 벤치 | `examples/dusk_bench.py` | `outdoor.World`, `golden_hour` | 해 질 녘 단지 벤치의 두 사람, 세로 |
| 해변 노을 | `examples/beach_sunset.py` | `background.beach`, `night_lighting` | 해 지는 바닷가를 걷는 두 사람, 가로 |
| 두머 남성 | `examples/doomer_man.py` | `outdoor`, `street3d`, `grade` | 가로등 밑 담배 피우는 남성, 세로 |
| 두머 여성 | `examples/doomer_woman.py` | `street3d.bus_stop`, `held_phone` | 버스 정류장의 헤드폰 낀 여성, 세로 |
| 두머 투샷 | `examples/doomer_pair.py` | `street3d.bench`, `birch` | 벤치에 앉아 창을 보는 두 사람의 뒷모습, 가로 |
| 두머 설정샷 | `examples/doomer_establishing.py` | `outdoor.panel_block`, `wires_between` | 해 질 녘 단지 원경과 작은 인물, 가로 |
| 두머 도시화 | `examples/doomer_city.py` | `outdoor.road_texture`, `World(wet=True)` | 젖은 대로의 1점 투시와 트롤리 전선, 세로 |
| 두머 풍경화 | `examples/doomer_landscape.py` | `power_pole`, `OVERCAST`, `doomer_day` | 흐린 날 눈밭의 전봇대 행렬, 가로 |
| 두머 사물화 | `examples/doomer_still.py` | `ashtray`, `tea_glass`, `cassette_player`, `radiator` | 밤 창턱 정물, 가로 |

- 소재별 구성 요소와 조정 요령은 `references/subjects.md`
- 얼굴 인상은 프리셋과 머리 비율로 고름
    + `adult_face()`는 하관이 길고 눈이 작은 성숙한 인상, 남성은 `male_face()`, 기본 얼굴은 큰 눈의 애니메 인상
    + `head_scale` 1.0은 사실적 비례, 1.08-1.15는 애니메식 큰 머리
- 미성년자의 누드와 성적 묘사는 그리지 않음
    + 대상은 이차성징 이전의 신체로 묘사한 인물, 18세 미만으로 명시된 인물
    + 큰 눈, 큰 머리 비율, 앳된 얼굴, 의상 같은 화풍 요소만으로는 미성년으로 판정하지 않음
- 예제는 `scripts/examples/` 안에서는 그대로 실행되며 다른 폴더로 복사한 경우 `_toolkit.py`도 함께 복사

## 장면 스크립트

```python
from dataclasses import replace
from codeillust import background
from codeillust.character import Outfit, default_character, default_palette, short_bob_hair
from codeillust.config import Material, rgb
from codeillust.figure import draw_character

palette = replace(default_palette(),
                  hair=Material(base=rgb("#2B3150"), shadow=rgb("#161A30"), line=rgb("#0C0E1C"),
                                accent=rgb("#4A5480"), light=rgb("#6E7DB0")),
                  hair_highlight=rgb("#9FB4E8"))
CHARACTER = replace(default_character(), palette=palette, hair=short_bob_hair(),
                    outfit=Outfit.LONG_SLEEVE_TOP, yaw=0.20, smile=0.9)

def compose(painter):            # 뒤에서 앞으로 그림
    background.bokeh_dusk(painter.canvas)
    draw_character(painter, CHARACTER)
```

- 인물 조정은 `Character`와 `Palette` 필드 교체로 수행
    + 전체 필드와 좌표계는 `references/api.md`
- 그림자 색은 재질마다 별도로 지정
    + 피부는 붉은 쪽, 흰 옷은 푸른 쪽으로 색상을 옮겨야 탁해지지 않음
- 광원은 `run_cli(..., light=(x, y, z))` 또는 `studio.render(..., light=...)`로 장면마다 지정
    + x는 오른쪽, y는 아래, z는 관찰자 쪽이며 기본값은 좌상단 앞(`DEFAULT_LIGHT`)
    + 역광은 z를 음수로(예: 길 끝의 노을을 등진 인물 `(0.10, -0.45, -0.89)`), 인물은 그늘 색이 되고 윗면 가장자리만 빛남
    + 바닥 그림자는 광원 반대쪽으로 기울며 광원이 낮을수록 길어짐
- 배경은 화풍의 표면과 맞춰 선택
    + 애니메는 `summer_sky`, 일러스트는 `flat_graphic`, 회화는 `studio_backdrop`, 야경은 `bokeh_dusk`

## 3D 인물

```python
from codeillust import background, head3d, rig3d, wardrobe3d
from codeillust.character import adult_face, default_character, male_face
from codeillust.figure3d import Figure3D, draw_figure3d

HER = Figure3D(character=adult_face(default_character()), build=rig3d.FEMALE_GLAMOUR,
               pose=rig3d.POSES["hand_on_hip"], hair=head3d.LONG_HAIR,
               outfit=wardrobe3d.OUTFITS["tank_top_jeans"], position=(500, 600), head_height=128,
               yaw=0.45, ground=1250)           # yaw 0 정면, π/2 측면, π 뒷모습

def compose(painter):
    background.beach(painter.canvas, painter.light, 540, 860)
    draw_figure3d(painter, HER)                 # 여러 명이면 뒤에 선 인물부터 그림
```

- 체형은 `FEMALE_AVERAGE`, `FEMALE_GLAMOUR`, `MALE_SLIM`, `MALE_ATHLETIC`
- 자세는 `rig3d.POSES`의 27종
    + 서기, 콘트라포스토, 허리에 손, 팔짱, 걷기, 앉기(소품 `stool`), 손 흔들기, 가리키기, 생각하기, 뒷짐, 환호, 브이, A 자세
    + 달리기(`run`), 주머니에 손(`hands_in_pockets`, 바지류 의상과 함께), 무릎 꿇기(`kneel`), 무릎 꿇고 앉기(`kneel_sit`), 등 대고 눕기(`lie_back`), 엎드리기(`lie_front`)
    + 기기를 쓰는 자세 6종은 아래 "3D 장면", 담배 자세 2종은 "두머 세트" 참조
    + 바닥 자세도 `ground`(캔버스 바닥선)나 장면의 `Placed.at`만 주면 가장 낮은 부위가 바닥에 닿음
    + `rig3d.mirrored(자세)`는 좌우 반전 자세, 측면 구도에서 손동작을 카메라 쪽으로 옮길 때 사용
    + 주머니에 손(`hands_in_pockets`)은 바지류 의상과 조합, 후드티와 재킷은 소매가 상의 주머니로 들어감
- 의상은 `wardrobe3d.OUTFITS`의 13종이며 색은 `replace(outfit, colors={...})`로 교체
    + 여성: 크롭티와 핫팬츠, 후드티와 청바지, 후드티와 반바지, 탱크톱과 청바지, 원피스, 비키니, 티셔츠와 청바지
    + 남성: 셔츠와 바지, 수영 반바지, 정장(셔츠, 넥타이, 재킷)
    + 겨울: 패딩과 비니(`winter_beanie`), 패딩과 헤드폰(`winter_headphones`), 후드티와 비니(`hoodie_beanie`)
- 머리 모양은 `LONG_HAIR`, `BOB_HAIR`, `PONYTAIL_HAIR`, `MALE_SHORT_HAIR`, `MALE_MEDIUM_HAIR`
    + 긴 머리 끝은 길이가 다른 가닥으로 갈라지고 옆머리 끝은 뾰족하게 얇아짐
- 필드, 새 자세와 의상 추가 절차는 `references/subjects.md`의 "3D 인물"

## 3D 장면(현대 사물, 실내, 기기를 든 인물)

```python
from codeillust import interior, props3d, rig3d, scene3d
from codeillust.figure3d import Figure3D

room = interior.office()                                   # living_room(), office(), cafe(), bedroom()
desk, chair = room.places["desk"], room.places["chair"]
worker = Figure3D(character=..., pose=rig3d.SIT_TYPE, outfit=...)
camera = scene3d.SceneCamera(target=(-0.8, -3.3, -3.2), origin=(500, 660), scale=140, yaw=0.62, pitch=0.13,
                             distance=20.0)                # distance가 원근, None은 정사영

def compose(painter):
    interior.draw_room(painter, camera, room, [
        scene3d.seated(worker, chair),                     # 의자 좌석 기준점에 앉힘
        scene3d.on_top(props3d.laptop(screen="code"), desk, offset=(0.0, 0.0, 0.92))])
# 누운 인물: scene3d.Placed(Figure3D(pose=rig3d.LIE_FRONT, ...), at=scene3d.anchor(침대, "lie_front"))
# 배치 점검: scene3d.overlaps(room.items + 추가_항목)이 빈 목록이면 물체끼리 관통 없음
```

- 월드 단위는 머리 높이(23cm), 바닥은 y = 0, y는 아래, 사물 치수는 `props3d.cm()`로 실측 입력
- 사물은 `props3d`의 노트북, 모니터, 키보드, 마우스, 휴대전화, 태블릿, 헤드폰, 게임 컨트롤러, 머그컵, 종이컵, 유리컵(`drinking_glass`, 투명), 책, 책 더미, 스탠드 조명, 화분, TV, 케이블(`cable`, 점을 지나는 선), 담배, 재떨이, 차 유리잔, 카세트, 카세트 플레이어
- 가구는 `furniture3d`의 책상, 사무 의자, 소파, 낮은 수납장, 커피 테이블, 카페 테이블과 의자, 카운터, 책장, 펜던트 조명, 플로어 조명, 러그, 침대(`bed`, 베개별 눕기 기준점), 라디에이터, 창턱
- 화면 콘텐츠는 `screens`의 `desktop`, `code`, `video`, `chat`, `home`, `game`이며 모두 가상의 범용 화면
- 기기를 든 자세는 `sit_type`(타이핑), `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug`, `sit_game`
    + 손에 든 물체는 `Figure3D(props=(props3d.held_phone(),))`, `held_mug()`, `held_controller()`
- 실내는 정면이 열린 무대이며 카메라가 벽 밖에 있으면 그 벽을 생략
- 앉은 인물에게도 치마류 의상을 입힐 수 있음(치마가 허벅지를 따라 무릎 쪽으로 누움)
- 상세 절차와 한계는 `references/subjects.md`의 "현대 사물과 실내 장면"

## 두머 세트(야외 장면과 색보정)

```python
from codeillust import outdoor, scene3d, street3d
M = outdoor.metres                                          # 미터를 머리 높이로

lamp = scene3d.Placed(street3d.street_lamp(), at=(M(1.6), 0.0, M(-1.6)), yaw=np.pi)   # 팔이 -x 쪽
world = outdoor.World(light=outdoor.NIGHT, sky=outdoor.NIGHT_SKY, fog=outdoor.FOG_NIGHT,
                      ground=outdoor.ground_plane(outdoor.snow_texture(rng, outdoor.NIGHT, M(400)), M(400)),
                      blocks=[outdoor.panel_block((0.0, M(-90)), M(110), 10, rng)],
                      lamps=[street3d.lamp_light(lamp)], items=[lamp, scene3d.Placed(man)],
                      snow=outdoor.SNOW_LIGHT)

def compose(painter):
    outdoor.draw_world(painter, camera, world, rng)         # 하늘, 땅, 빛 웅덩이, 건물, 인물, 전선, 안개, 눈
# 실행: python scene.py --grade doomer (기본값을 run_cli(..., grade="doomer")로 지정 가능)
```

- 분위기만 차용하며 특정 앨범 커버, 밈 캐릭터, 실재 건물을 재현하지 않음
- 빛은 `NIGHT`, `DUSK`, `OVERCAST` 3종이며 건물 벽, 불 켜진 창 비율, 눈 색, 인물의 환경광을 함께 정함
    + 가로등(`street3d.lamp_light`)은 원뿔 안의 땅과 인물을 같은 감쇠로 밝히고 전구와 화면은 밝기를 유지
    + 인물이 가로등 원뿔 밖에 서면 실루엣이 되므로 얼굴이 보여야 하면 등 바로 옆에 배치
- 거리 소품은 `street3d`의 가로등, 전봇대(`wires_between`으로 전선), 벤치, 버스 정류장(형광등 `shelter_light`), 자작나무
- 인물 소품은 비니(`beanie`), 패딩(`puffer`), 헤드폰(`headphones`), 손에 든 담배(`props3d.held_cigarette`, 연기 포함)와 자세 `stand_smoke`, `sit_smoke`
- 실내 소품은 재떨이, 차 유리잔, 카세트, 카세트 플레이어, 라디에이터, 창턱, 벽지(`interior.wallpaper`), 밤 창밖(`window(..., "panel_night", ...)`)
- 색보정은 `--grade doomer`(밤, 나트륨 주황과 청록 그늘), `doomer_day`(흐린 낮), `none`
    + 화풍 마감 뒤에 적용되므로 3개 화풍 모두와 조합
- 구도 잡기는 `camera.project(점)`으로 등 머리, 인물 발, 건물 지붕의 캔버스 좌표를 먼저 계산한 뒤 렌더
- 상세 절차와 한계는 `references/subjects.md`의 "야외 장면과 두머 세트"

## 광원 장면(조명과 따뜻한 색보정)

```python
from codeillust import interior, outdoor
screen = outdoor.Lamp(at=(0.0, -4.0, -3.4), color=rgb("#D2DEF8"), reach=cm(50), strength=0.85)   # 노트북 화면
desk_lamp = outdoor.Lamp(at=(-1.9, -4.8, -2.4), color=rgb("#FFC07A"), reach=cm(75), strength=1.15, cone=1.05)
view = interior.on_back_wall(shell, -3.2, 3.2, cm(225), cm(95),
                             interior.window(6.4, cm(130), "city_night", rng))    # 달 아래 빌딩

def compose(painter):
    outdoor.draw_lit_room(painter, camera, surfaces, [view], items, [screen, desk_lamp],
                          ambient=np.array([0.36, 0.34, 0.42]))
# 실행: python scene.py --style illust --grade cozy_night
```

- 화면, 스탠드, 창으로 든 해, 노을처럼 이름 붙은 광원이 인물을 감싸는 일상 장면
    + 출발점은 밤의 책상, 오후의 창가, 노을 벤치, 해변 노을 예제
- 방 조명은 `outdoor.draw_lit_room`이 밤거리와 같은 식으로 처리
    + 벽과 사물은 환경광 비율만큼 색을 유지하고 등마다 거리 감쇠로 빛을 더함
    + 낮 장면은 환경광을 1 가까이 두고 창 앞에 넓은 따뜻한 등을 하나 놓아 해를 대신함
    + 창밖과 바닥의 해 조각은 `views`로 넘기므로 조명 뒤에 그려져 제 밝기를 유지
- 창밖 종류에 `city_night`(달 아래 불 켜진 빌딩)와 `golden`(낮은 해와 금빛 하늘)이 있음
- 색보정 `cozy_night`(남색 그늘, 텅스텐 빛), `late_sun`(청회색 그늘, 꿀색 빛), `golden_hour`(보라 그늘, 살구색 빛)는 채도를 0.9배 이상 유지하고 입자를 약하게 둠
- 구도는 얼굴 높이가 화면의 1/10-1/14인 중간 거리를 기준으로 잡음
    + 나무와 기둥은 원하는 캔버스 x에서 월드 x를 역산하여 머리 뒤를 비움(`dusk_bench.world_x`)
    + 아래를 보는 3/4 얼굴은 애니메 선화에서 코와 입 선이 이어지므로 `illust` 화풍을 권장
- 상세 절차와 한계는 `references/subjects.md`의 "광원 장면"

## 화풍

| 화풍 | 음영 | 선 | 마감 |
|---|---|---|---|
| `anime` | 2단 셀 음영 | 색 선화, 그늘 쪽이 굵음 | 림라이트, 블룸, 채도 보정 |
| `illust` | 연속 음영 | 선 없음 | 가장자리 흔들림, 종이 입자 |
| `painterly` | 연속 음영과 명암 대비 | 선 없음 | 다층 붓질 재구성, 물감 요철, 캔버스 결 |

- 색보정(`grade`)은 화풍 위에 얹는 별도 단계이며 `--grade`로 고름
- 내리는 눈은 마감 뒤에 그리는 덧그림(`canvas.overlays`)이므로 회화풍 붓질이 눈송이를 뭉개지 않음
- 화풍별 조정 상수와 새 화풍 추가 절차는 `references/styles.md`

## 새 부품

리그에 없는 소품은 `compose()` 안에서 같은 레시피로 추가한다. `scripts/codeillust/props.py`의 `bow()`가 견본이다.

```python
from codeillust.geometry import catmull_rom
hat_brim = catmull_rom([(180, 300), (470, 210), (760, 300), (470, 360)], closed=True)   # 캔버스 단위
painter.part("hat", painter.canvas.mask(hat_brim), palette.trim, roundness=0.4)
```

- 순서는 레이어 순서와 동일
    + 나중에 그린 부품이 먼저 그린 부품의 선을 덮으므로 뒤에 있는 것부터 그림
- 다른 부품 위에 떨어지는 그림자는 `painter.cast(가리는_마스크, 받는_마스크, 이동량)`으로 생성
    + 이동 방향은 광원의 반대편(기본 광원은 좌상단이므로 우하단)
    + 받는 부품을 아직 그리기 전이면 `part(..., casts=[그림자])`로 전달
    + 받는 부품이 이미 그려진 뒤면 `painter.glaze(그림자, 그림자_색, 농도)`로 덧칠한 다음 소품을 그림
- 머리에 붙는 소품은 `Head(character)`로 머리 단위 좌표를 캔버스 단위로 변환
    + 모자는 `flat()`, 얼굴에 붙는 것은 `on_face()`, 머리카락에 붙는 것은 `on_skull()`

## 입체 부품

둥근 형태는 `Relief`에 쌓은 뒤 한 번에 조명한다.

```python
from codeillust.relief import FRONT, Relief
relief = Relief(painter.canvas)
relief.add("torso", torso_mask, skin, thickness=0.7)        # 같은 깊이는 이음매 없이 합쳐짐
relief.add("arm", arm_mask, skin, depth=FRONT)              # 앞에 놓이면 가림 선과 그림자가 생김
relief.render(painter)                                      # 화풍에 맞춰 셀 또는 연속 음영
```

- 가장자리 없는 부풂은 `swell()`, 가장자리 있는 부풂은 `bump()`, 패임은 `groove()`
- 표면에 붙는 천과 라벨은 `add(..., drape=True)`

## 검수

- 자동 점검(`selftest.py`)은 구조 결함만 검출
    + 두피 노출, 눈 위치 이탈, 팔다리 길이 보존, 소실점 수렴, 지형 구멍, 재현성, 화풍 간 차이를 확인
    + 3D 인물은 전 자세와 전 체형의 뼈 길이 보존, 손의 목표점 도달, 전 의상의 정면, 측면, 뒷모습에서 피부 비침 여부, 신장 7.5 머리, 뒷모습의 얼굴 숨김을 확인
    + 3D 장면은 먼 시점과 정사영의 일치, 각진 형태의 앞면 깊이, 전 사물과 가구의 렌더, 가림 순서, 화면 콘텐츠 위치, 손에 든 물체 위치, 앉은 자세의 좌석 높이 일치, 실내 벽면의 화면 채움을 확인
    + v7.3 항목은 따뜻한 색보정의 채도 유지와 재현성, 새 창밖 풍경의 어두운 밤하늘과 밝은 달, 방 조명에서 등 옆 벽의 밝기와 조명 뒤에 그린 창밖의 밝기 유지
    + v7 항목은 색보정의 채도 감소와 재현성, 화소와 월드 좌표의 왕복, 밤 조명에서 어두워지는 물체와 밝게 남는 불씨, 전선의 애자 연결, 비니의 정수리 덮음, 화소보다 가는 구 사슬의 빠른 렌더
    + v6.2 항목은 좁은 틈 메우기와 단단한 물체 구멍 보존, 주머니로 들어간 후드티 소매, 광원 반대쪽 바닥 그림자
    + v6.1 항목은 좌우 반전 자세의 대칭, 어깨끈의 어깨 밀착
    + v6 항목은 전 자세의 바닥 침투 없음, 누운 자세의 다점 접지, 물체 겹침 검출과 실내 4종의 무관통, 케이블 접지, 유리 투과, 비키니 끈의 피부 위 유지, 앉은 치마의 허벅지 덮음, 주머니 속 손가락, 회화풍 작은 얼굴의 붓 세밀도
- 매력과 완성도는 렌더 이미지를 직접 보고 판단
    + 증상별 처방은 `references/qa.md`

## 전달

- 최종 PNG와 장면 스크립트를 함께 전달
    + 스크립트가 있어야 제3자가 동일 그림을 재현
- 결과의 한계를 그대로 보고
    + 자동 점검 통과는 구조 정합을 뜻하며 그림의 매력을 보증하지 않음

## 참조 문서

- `assets/reference_sheet.jpg`: 초상 장면의 3개 화풍 결과, 완성 수준의 기준
- `assets/reference_subjects.jpg`: 전신, 손, 풍경, 도시, 정물 예제의 결과
- `assets/reference_3d.jpg`: 3D 인물 턴어라운드, 자세 시트, 의상 시트, 완성 장면의 결과
- `assets/reference_modern.jpg`: 현대 사물 시트, 책상 정물, 사무실, 거실, 카페, 침실 장면의 결과
- `assets/reference_doomer.jpg`: 두머 세트 7장면(남성, 여성, 투샷, 설정샷, 도시화, 풍경화, 사물화)과 화풍 변형의 결과
- `assets/reference_light.jpg`: 광원 장면 예제(밤의 책상, 오후의 창가, 노을 벤치, 해변 노을)의 결과
- `references/subjects.md`: 소재별 구성 요소, 조정 요령, 한계
- `references/pipeline.md`: 공정별 원리, 디자인 방향 문서 양식, 리그 확장 절차
- `references/api.md`: 좌표계, `Character` 필드, 모듈별 함수
- `references/styles.md`: 화풍별 레시피와 조정 상수
- `references/qa.md`: 검수 항목과 증상별 처방
