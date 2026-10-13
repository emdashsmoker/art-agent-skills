---
name: geometric-illustration
description: "구와 원뿔로 세운 마네킹, 1점 투시 핀홀 카메라, 평면 다면체 소품을 numpy와 OpenCV로 계산해 그리는 일러스트 스킬. 확산모델과 이미지 생성 API 없이 구조선, 선화, 밑색, 음영, 후보정의 작화 공정을 코드로 밟는다. 결과물의 맛은 고요한 기하학이다. 또렷한 잉크 실루엣, 남색과 회청색의 차분한 바탕, 창문과 가로등의 호박색 불빛 몇 점, 키 라이트 하나, 자세를 잡고 멈춰 선 인물. 남녀 인물(바스트업부터 넓은 설정샷까지, 2-3인 투샷), 소실점으로 빨려 드는 거리, 층층이 겹친 풍경, 탁자 위 정물을 애니메 셀, 소프트 일러스트, 유화, 수채와 색보정 룩으로 JSON 명세 1개에서 같은 결과로 재현한다. 명세 필드는 references/spec-reference.md, 모듈 구조와 확장 절차는 references/pipeline.md, 인체 비례와 형태 검수는 references/anatomy.md, 화풍 렌더러와 색보정은 references/styles.md를 읽는다. '코드로 그림 그려줘', '확산모델 없이 일러스트', '애니메풍 캐릭터를 코드로', '절차적 배경', '코드로 야경', '코드로 정물화', '투샷 일러스트', 'draw with code', 'procedural illustration' 요청과 이미지 생성 도구가 없는 환경의 인물화, 배경화 요청에 반드시 이 스킬을 사용할 것."
license: GPL-3.0-or-later. Rendered images are not covered by the GPL (additional permission in THIRD_PARTY_NOTICES.md). Complete terms in LICENSE
---

# 코드 일러스트

실제 작화 공정을 코드로 이식하여 그림을 그리는 스킬. 확산모델, 이미지 생성 API, 3D 소프트웨어를 사용하지 않는다.

## 작동 원리

그림 1장은 아래 7단계를 거친다. 각 단계는 사람이 그리는 순서와 1:1로 대응한다.

| 작화 공정 | 코드 단계 | 담당 모듈 |
|---|---|---|
| 기획 | JSON 명세 작성 | `config.py` |
| 구조선 | 머리 프레임, 관절 스켈레톤, 원근 카메라 | `frames.py`, `rig_anatomy.py`, `scene_city.py` |
| 형태 | 구체와 원뿔로 쌓는 마네킹(Loomis, Bridgman 방식), 몸에 맞춘 3D 의상, 평면과 원기둥 소품 | `mannequin.py`, `rig_hand.py`, `rig_anatomy.py`, `garment3d.py`, `garment_kit.py`, `outfits.py`, `scene_props.py` |
| 선화 | 가변 폭 스트로크, 실루엣선, 앞뒤 가림 윤곽선 | `geom.py`, `mannequin.py`, `scene.py` |
| 밑색 | 재질 그룹별 단색과 그라데이션 | `scene.py` |
| 음영 | 깊이장 법선, 자기 그림자, 캐스트 섀도, 디자인된 그림자 | `mannequin.py`, `scene.py` |
| 후보정 | 화풍별 레이어 합성, 그림 전체 색보정(룩) | `styles.py`, `painterly.py`, `looks.py` |

핵심 설계는 "레이어 분리"다. 리그와 장면 모듈은 선화, 밑색, 법선, 그림자, 하이라이트 레이어만 산출한다. 화풍 렌더러는 같은 레이어를 다르게 합성한다. 따라서 대상을 바꾸지 않고 화풍만 바꿀 수 있다.

인체와 손, 과일 같은 부드러운 형태는 구체와 원뿔(구-스윕 입체)로 만든 마네킹이다. 구-스윕 입체는 정사영 후에도 구-스윕 형태를 유지하므로 실루엣, 깊이, 윤곽선이 닫힌 수식으로 계산된다. 몸통은 폭과 두께가 다른 타원 단면 사슬 1개로 만든다. 발은 타원체를 촘촘히 이은 스윕으로 만들어 정면에서 봐도 형태가 무너지지 않는다. 손가락과 발가락은 끝으로 갈수록 가늘어지는 관이다. 옷은 같은 몸에 3D로 입힌다. 몸에 붙는 옷은 해당 몸 부위를 옷 두께만큼 부풀린 입체, 바지와 소매는 팔다리를 감싼 관, 스커트는 엉덩이에 걸쳐 떨어지는 천 면이라 자세가 바뀌어도 몸을 따른다. 노트북, 컵, 접시 같은 단단한 물체는 평면 다면체와 원기둥 소품으로 그려 면마다 하나의 명암을 받는다. 메시와 3D 패키지는 없다.

## 주제

| `subject` | 내용 | 권장 캔버스 |
|---|---|---|
| `portrait` | 의상을 입은 인물. `character.sex`로 여성, 남성, `character.build`로 체형 선택. `framing`으로 바스트업, 상반신, 전신, 설정샷(`wide`) 선택. `characters` 목록이면 2-3인 투샷. `background.type: scene`이면 도시나 풍경 위에 인물 합성 | 1024 x 1280, 전신 1024 x 1600, 투샷 1280 x 1600 |
| `figure_study` | 성인 인체 습작. 여성, 남성 각 포즈 4종 | 입상 1024 x 1600, 와상 1600 x 1024 |
| `still_life` | 정물. `scene.set`: `classic`(병, 주전자, 과일, 천), `desk`(노트북, 머그, 램프, 화분), `cafe`(라테, 케이크, 아이스 음료), `gaming`(모니터, RGB 키보드, 헤드셋), `kitchen`(받침에 끼운 찻잔, 카세트 라디오, 창밖 눈 내리는 단지) | 1400 x 1050 |
| `cityscape` | 1점 투시 거리. `scene.site`: `street`(상가 대로, 기본), `panel`(패널 아파트 단지와 맨가지 가로수). `scene.time`으로 시간대 선택 | 1600 x 1000 |
| `landscape` | `scene.site`: `lake`(산과 호수, 기본), `outskirts`(교외 들판, 송전탑 행렬, 자작나무, 지평선의 단지와 굴뚝). `scene.time`으로 시간대 선택 | 1600 x 1000 |

시간대(`scene.time`): `dusk` 황혼(기본), `day` 맑은 낮, `golden` 골든아워, `blue_night` 블루아워 야경, `rain_night` 비 오는 밤, `snow_night` 눈 내리는 밤(나트륨 가로등, 눈 쌓인 길과 바퀴 자국). 시간대마다 하늘, 광원, 물체 색, 효과(해 길, 달과 별, 창문과 가로등, 비, 눈, 젖은 도로 반사)가 함께 바뀐다.

색보정(`look`): `none`(기본), `doomer`(채도를 낮추고 그림자를 차갑게, 주황 불빛만 채도 유지, 바랜 검정, 필름 그레인, 비네트). 화풍 렌더가 끝난 그림 전체에 1회 적용된다.

## 인체 습작

`figure_study` 주제는 고전 회화의 아카데믹 인체 습작 포즈 4종을 남녀 각각 그린다.

- 몸 비례는 미 육군 인체 측정 자료(ANSUR II 여성, 남성)를 애니메 일러스트 체형으로 보정한 성인 값으로 고정된다(`references/anatomy.md`).
- 현재 몸 모델에는 가슴 표시와 골반 세부 형태가 구현되어 있지 않다. 골반 주변은 내부 선을 그리지 않는다. 남녀 동일하다.
- 포즈 4종은 자세, 손, 머리카락, 천이 가슴과 골반을 가리는 고전 구도다.

### (내용 제한) 미성년자 노출과 성행위

- 미성년자의 노출과 성행위 묘사는 그리지 않는다. 이 스킬의 유일한 내용 제한이다.
- 판단 기준은 몸의 묘사다.
    + 이차성징 이전의 몸(아동의 머리 대 몸 비율, 발달 전 가슴과 골반, 아동 체형)을 그리는 요청
    + 미성년 나이나 아동 신분을 명시한 인물
- 화풍, 큰 눈, 동안 인상만으로는 판단하지 않는다.
- 코드 구현: 몸 비례는 성인 값으로 고정된다. `figure_study` 주제의 얼굴 파라미터는 `rig_figure_study.ADULT_FACE` 범위로 보정된다. 이 보정은 렌더 결과에만 적용된다.

## 의존성

- Python 3.9 이상
- `numpy`, `opencv-python-headless` 2종
    + 검증 버전: Python 3.11, numpy 2.4, OpenCV 4.13 / Python 3.13, numpy 2.5, OpenCV 5.0
    + 설치 예시: `pip install numpy opencv-python-headless`
    + conda 환경이면 `conda install numpy` 후 `pip install opencv-python-headless`

의존성 설치를 다른 모든 단계보다 먼저 수행한다. 렌더러는 GPU, 네트워크, 폰트를 사용하지 않는다.

## 빠른 시작

```bash
cd scripts
python render.py --out portrait.png                                         # 기본 인물, 애니메 셀, 바스트업
python render.py --out portrait.png --style oil                             # 화풍만 교체
python render.py --spec ../assets/examples/landscape_dusk_oil.json --out land.png
python render.py --spec ../assets/examples/city_rain_night_watercolor.json --out rain.png   # 시간대 예시
python render.py --spec ../assets/examples/still_desk_anime.json --out desk.png            # 현대 정물 예시
python render.py --spec ../assets/examples/male_suit_illustration.json --out male.png      # 남성 인물 예시
python render.py --spec ../assets/examples/turn_back_turtleneck_watercolor.json --out back.png   # 뒷모습
python render.py --spec ../assets/examples/seated_turtleneck_anime.json --out seated.png         # 의자에 앉기
python render.py --spec ../assets/examples/group_hold_hands_anime.json --out pair.png            # 투샷
python render.py --spec ../assets/examples/scene_city_track_illustration.json --out city.png     # 야경 속 인물
python render.py --spec ../assets/examples/doomer_establishing_anime.json --out doomer.png      # 두머 설정샷
python render.py --spec my.json --out out.png --stages stages/              # 공정별 단계 이미지 + 공정 시트
```

- `--style`: `anime` | `illustration` | `oil` | `watercolor`
- `--stages`: `1_construction`, `2_lineart`, `3_flats`, `4_shading`, `5_final`, `process_sheet.png` 저장
- 명세의 오타 키는 stderr 경고로 보고된다. 잘못된 열거값은 사용 가능한 값 목록과 함께 오류로 종료된다.
- 소요 시간(1024 x 1280 기준): 애니메, 일러스트, 수채 2-5초, 유화 6-15초. 장면과 현대 정물은 3-8초
- 렌더 1회의 최대 메모리는 약 0.4-0.9 GB다. 여러 장을 병렬로 렌더할 때는 동시 실행 수를 사용 가능한 메모리(GB) 이하로 둔다

## 워크플로우

### 1단계 (기획) 요청을 명세로 번역

- 요청에서 주제, 화풍, 프레이밍 또는 포즈, 인상, 색을 추출
- 기본값과 다른 필드만 JSON에 기록
    + 모든 필드와 범위는 `references/spec-reference.md` 참조
- 인물 인상 키워드는 아래 번역표를 출발점으로 사용

| 인상 | 조정 필드 |
|---|---|
| 시크, 차가운 | `face.jaw_sharpness` 0.8-0.9, `eyes.tilt` 0.08-0.14, `mouth.smile` 0.1-0.25, `blush` 0.2 |
| 부드러운, 귀여운 | `eyes.size` 1.2-1.3, `eyes.tilt` 0.0, `face.jaw_sharpness` 0.5, `blush` 0.45 |
| 우아한, 성숙한 | `eyes.openness` 0.85, `eyes.lash_weight` 1.2, `brows.angle` 0.2, `mouth.lip_strength` 0.8 |
| 밝은, 상냥한 | `mouth.smile` 0.5-0.7, `brows.angle` 0.1, `eyes.gaze` 정면 [0, 0] |

- 성별: `character.sex`를 `male`로 두면 남성 체형, 얼굴, 짧은 머리, 남성 의상 기본값이 함께 적용된다. 인상 조정은 아래 표의 필드를 그대로 쓴다
- 체형(`character.build`): 여성 `standard`, `slender`(슬렌더), `fuller`(볼륨형), `athletic`(탄탄한), 남성 `standard`, `slim`, `athletic`(근육형). 모두 실제 성인 체형 범위 안의 변형이며 의상은 체형을 따라 입혀진다
- 얼굴 프리셋(`character.face_preset`): `soft`, `sharp`, `mature`, `gentle`(처진 눈매), `cool`(가는 눈매), `bold`(진한 이목구비). 성인 얼굴 범위 안에서만 바뀐다
- 표정(`character.expression`): `smile`, `laugh`(감은 눈, 벌린 입), `neutral`, `surprised`, `serious`, `sad`
- 머리 모양(`character.hair.style`): `long`, `updo`, `short`, `bob`, `ponytail`, `medium`, `side_part`, `slicked`(넘긴 머리), `two_block`, `hime`(히메컷), `center_part`(가운데 가르마), `shoulder`(어깨 길이), `crop`(짧은 일자 앞머리)
- 프레이밍(`framing`): `bust`, `upper_body`, `full_body`, `wide`(설정샷: 전신 인물이 화면 높이의 약 1/3, 발은 화면 아래 10% 위). 설정샷은 `character.head.x`로 인물을 1/3 지점에 둔다
- 인물 포즈(`character.pose.preset`): `relaxed`, `hand_on_hip`, `hair_touch`(머리 넘기기), `chin_rest`(턱 괴기), `arms_crossed`(팔짱), `hands_in_pockets`(주머니), `walking`(걷기), `look_back`(뒤돌아보기), `lean_wall`(기둥에 기대기), `seated`(의자에 앉기)
    + `pose.turn`: 몸 회전. `front`, `three_quarter`, `side`, `three_quarter_back`, `back`, 앞에 `-`를 붙이면 반대쪽, 숫자는 라디안
    + `pose.look`: `auto`(얼굴이 몸을 따라 돌고 크게 돌면 뒤통수), `face`(어깨 너머로 얼굴), `away`(뒤통수)
    + `pose.custom`: 팔다리 손목, 발목 목표와 흉곽, 골반 회전을 직접 지정
- 의상(`character.outfit.type`): `turtleneck_sleeveless`(터틀넥과 스커트, 여성 기본), `bikini`, `innerwear`, `crop_hotpants`(크롭탑과 핫팬츠), `tee_jeans`(티셔츠와 청바지, 남성 기본), `suit`(정장), `hoodie_joggers`(후드티와 조거), `swim_trunks`(수영 반바지, 남성 전용), `shirt_slacks`(셔츠와 슬랙스), `knit_coat`(니트와 벨트 롱코트), `polo_shorts`(폴로와 치노 반바지), `tank_shorts`(싱글렛과 러닝 반바지), `denim_jacket`(청재킷과 티셔츠), `track_suit`(트레이닝복). 남성은 비키니, 속옷, 터틀넥 스커트, 크롭탑을 제외한 10종을 지원한다. 의상마다 기본 색과 신발이 있고 `palette`로 색만 바꾼다
    + `outfit.hat`: `none`(기본), `beanie`(접힌 단 니트 비니, 색 `palette.hat`). 모자는 머리카락 위에 그려 앞머리와 옆머리는 단 아래로만 보인다
    + `outfit.shoes`: 의상 기본 신발 대신 `pumps`, `sneakers`, `oxfords`, `none` 지정(눈길의 여성 코트 차림에 플랫 구두 등)
- 투샷: `characters`에 인물 2-3명을 적고 `layout.type`(`side_by_side`, `facing`, `front_back`)과 `layout.interaction`(`none`, `hold_hands`)을 고른다. 인물마다 성별, 체형, 의상, 포즈, 표정, `palette`를 따로 둔다
- 인물 배경 합성: `background.type`을 `scene`, `background.scene`을 `cityscape` 또는 `landscape`로 두면 `scene.time`의 장면 위에 인물이 서고 장면의 빛 방향, 색조, 림 색을 받는다
- 인체 습작 포즈: `back_three_quarter`, `venus`, `reclining`, `seated`
- 장면: `scene.time`, `scene.site`(풍경, 도시)와 `scene.set`(정물)을 먼저 고르고, 색만 `scene.palette`로 덮어쓴다
- 두머 감성(동유럽 겨울밤의 쓸쓸한 정서): `scene.time` `snow_night`, `scene.site` `panel` 또는 `outskirts`, 정물은 `scene.set` `kitchen`, `look` `doomer`, 검정과 회색 옷에 `outfit.hat` `beanie`, 표정 `neutral` 또는 `sad`. 특정 앨범 표지나 로고를 재현하지 않고 분위기만 쓴다

### 2단계 (디자인 방향) 짧은 방향 문서 작성

- 렌더링 전에 5줄 내외의 방향을 정한다: 핵심 인상 1개, 색 체계(기조색 + 강조색 2개 이내), 시선 방향, 광원 방향, 배경 대비
    + 광원을 먼저 정하는 이유는 음영, 반사광, 배경 글로우 위치가 모두 광원에서 파생되기 때문
- 장면 주제는 시간대와 세트에 광원이 설계되어 있다. 빛의 성격은 `scene.time`, `scene.set`으로 고르고 색만 `scene.palette`로 바꾼다.
- 머리카락과 의상이 같은 어두운 색이면 실루엣이 합쳐진다. 둘 중 하나의 명도를 분리한다.

### 3단계 (렌더링) 공정 시트와 함께 출력

- 첫 렌더는 `--stages`를 붙여 공정별 결과를 확인
    + 인체 포즈는 `1_construction`에 관절 스켈레톤이 그려진다
- 화풍 비교가 필요하면 같은 명세로 `--style`만 바꿔 4회 렌더링

### 4단계 (검수) 렌더 이미지를 직접 열어 확인

- 전체 이미지와 얼굴, 손, 발 확대 크롭을 각각 확인한다. 축소 썸네일에서는 선 결함이 보이지 않는다.
- 손과 발만 따로 보려면 `python scripts/check_proportions.py --hands hands.png`로 제스처와 발 자세를 여러 방향에서 렌더한다.
- 결함 발견 시 아래 표의 조정 지점부터 수정한다.

| 증상 | 원인 | 조정 |
|---|---|---|
| 얼굴 절반이 그림자 | 광원과 얼굴 회전 방향 충돌 | `light.direction` x 부호를 `head.yaw`와 반대로 |
| 앞머리가 눈을 가림 | 앞머리 길이 과다 | `hair.bang_length` 하향, `hair.bangs`를 `swept`로 |
| 먼 쪽 눈이 윤곽에 붙음 | 회전 과다 | `head.yaw` 절댓값 0.35 이하 |
| 손이 몸에서 떠 보임 | 손목 목표 위치 오차 | 포즈 함수의 `Limb.target`을 `--stages` 스켈레톤을 보며 이동 |
| 손가락이 뭉쳐 보임 | 제스처 굽힘 과다 | `rig_hand.GESTURES`의 손가락 굽힘 각도 축소 |
| 주먹이 벙어리장갑처럼 보임 | 첫마디 굽힘 과다 | 제스처의 MCP 굽힘을 줄이고 PIP 굽힘을 늘림 |
| 엄지가 막대처럼 튀어나옴 | 엄지 끝 목표가 손바닥에서 멂 | 제스처 `thumb` 목표를 손바닥 쪽(`n` -0.3에서 0)으로 당김 |
| 손목 옆에 둥근 혹 | 엄지 뿌리가 손목 밖 | `rig_hand.THUMB_BASE`의 v를 손목 반폭 안으로 |
| 발바닥이 기울어 보임 | `foot_dir`의 y 성분 | 서 있는 발은 y 0, 까치발과 하이힐은 `hand='point'` |
| 상의 가슴에 얼룩 같은 그림자 | 니트 법선 평활화 부족 | `garment3d.TOP_NORMAL_BLUR` 상향 |
| 니트 골이 구불거림 | 골 간격을 읽는 높이장의 잔물결 | `garment3d.RIB_HEIGHT_BLUR`, `RIB_SMOOTH` 상향 |
| 스커트가 원통처럼 보이거나 다리가 비침 | 밑단 폭 또는 여유 부족 | 명세 `skirt_flare` 조정, `garment3d.SKIRT_EASE` 상향 |
| 스커트 주름이 약하거나 과함 | 주름 깊이와 개수 | `garment3d.FOLD_DEPTH`, `FOLD_COUNT` 조정 |
| 소매나 바짓단이 몸을 베어 냄 | 팔다리 밑단 자르기 범위 과다 | `garment_kit.LIMB_CUT_REACH`, `LIMB_SIDE_REACH` 하향 |
| 목선 위로 옷이 기둥처럼 남음 | 목 원뿔까지 부풀림 | 레시피에서 `sleeved_top(..., neck=False)`(기본), 목선 높이 `NECK_BASE_Y` 확인 |
| 짧은 하의 아래로 천 조각이 매달림 | 몸통 아래 끝이 다리 사이로 내려옴 | `outfits.SHORTS_MAX` 확인(짧은 하의는 두 밑단을 잇는 선 아래를 자름) |
| 남성 어깨가 혹처럼 솟음 | 승모근 끝이 삼각근보다 낮음 | `rig_anatomy.BUILDS['male']`의 `GIRDLE_TOP`, `ARM_ATTACH_K` |
| 남성 골반 옆에 혹 | 허벅지 뿌리 공이 골반선 밖 | `BUILDS['male']`의 `THIGH_ROOT_R`, `HIP_LOCAL` 축소 |
| 새 체형의 골반선에 혹 | 허벅지 굵기 배율이 골반 폭 배율보다 큼 | `rig_anatomy.VARIANTS`의 `thigh_root`를 1.0 근처로, 골반 행 `width` 상향 후 `check_proportions.py` |
| 끈이 목이나 어깨 앞 피부에서 끊김 | 끈 경로가 그려진 윤곽 안에서 끝남 | 끈은 `garment_kit.strap`(3D 경로, 깊이와 향함으로 가림)으로 그린다. 목 고리는 `outfits.neck_fit_radius`가 그려진 목 윤곽에 맞춘다 |
| 돌린 몸에서 앞쪽 선(주머니, 라펠)이 등에 보임 | 선을 2D 점으로 그림 | 레시피에서 `ctx.paths`, `ctx.points`, `ctx.patch`를 쓴다(뒤쪽 선은 `back=True`) |
| 돌린 몸에서 컵이나 브리프가 등에 찍힘 | 앞면 윤곽만 있음 | `fitted_top`, `briefs`에 뒷면 윤곽(`back_rest`, `back_outline`)을 준다 |
| 돌린 몸에서 한쪽 바짓단 자르기가 다른 다리를 벰 | 2D 자르기 다각형 겹침 | `outfits.LIMB_FOOT_REACH`, `LIMB_FOOT_MARGIN` 확인(자르기를 해당 다리 영역으로 제한) |
| 주머니 손 주변에 피부 조각 | 손이나 아래팔이 옷 앞에 나옴 | `rig_figure.POCKET_WRIST`, `KANGAROO_WRIST`의 z를 옷 표면 안으로 |
| 투샷 인물이 화면 밖으로 나감 | 캔버스 폭 부족 | 캔버스 폭을 늘리거나 `layout.gap`을 줄인다. 배치는 폭에 맞춰 축소된다 |
| 상의 어깨가 퍼프 소매처럼 부풂 | 소매 여유 부족, 어깨 다리 부족 | 레시피의 소매 여유 상향, `outfits.BRIDGE_TOP` 확인 |
| 셔츠가 재킷 목선 옆으로 삐져나옴 | 겹마다 다른 목선 반지름 | `outfits.NECK_CUT_EASE` 상향 |
| 옷깃이 목 앞에 떠 보임 | 옷깃 안쪽 면이 목보다 앞 | 바스트업은 `rig_body.build_collar`의 `z_back`, 상반신과 전신은 `rig_figure.Z['collar_back']`을 목보다 뒤로 |
| 옷깃이 목을 덜 감쌈 | 옷깃 높이와 두께 | `garment3d.COLLAR_TOP_Y`(턱 쪽으로 올림), `COLLAR_EASE` 조정 |
| 발과 구두가 어긋남 | 구두 단면과 발 단면 불일치 | `rig_figure.SHOE_TOE_BOX`, `SHOE_WALL`을 `rig_anatomy.FOOT_SECTIONS`보다 조금 크게 |
| 몸 그림자가 지저분함 | 자기 그림자 길이 과다, 작은 빛 틈 | `mannequin.SHADOW_REACH` 하향, `styles.SHADOW_SIMPLIFY` 상향 |
| 몸이 통나무처럼 보임 | 몸통 단면 비례 | `rig_anatomy.TORSO_LOFT`의 허리 폭과 z 중심 조정 후 `check_proportions.py --sheet`로 회전 시트 확인 |
| 팔다리 윤곽이 울퉁불퉁함 | 반지름 프로파일의 급한 변화 | `rig_anatomy`의 `*_PROFILE` 값을 완만하게 조정, `check_proportions.py`의 변곡점 수 확인 |
| 팔다리 그림자 경계가 톱니 모양 | 스윕 분할 부족 | `rig_anatomy.LIMB_SEGMENTS` 상향 |
| 해부 표식이 빠지거나 엉뚱한 곳에 그려짐 | 표식 점이 표면에서 벗어남 | `rig_anatomy`의 표식 좌표를 표면 쪽으로 이동, `rig_figure_study.MARK_SURFACE_TOL` 확인 |
| 가리는 손의 외곽선이 없음 | 가림 구역 처리 | 손 조각 이름이 `hand_`로 시작하는지 확인(`mannequin.QUIET_KEEP`) |
| 유화 붓터치가 거칠게 번짐 | 붓 크기 과다 | `painterly.py`의 `OIL_FIG_BRUSHES` 축소 |
| 수채 얼룩이 과함 | 안료 변조 과다 | `painterly.py`의 `WC_TURBULENCE`, `WC_EDGE_DARKEN` 하향 |
| 모자 옆으로 머리카락이 솟음 | 머리 부피가 모자 돔보다 큼 | `rig_hat.HAIR_PRESS` 하향, `HAT_THICK` 상향 |
| 모자 단이 눈썹을 덮음 | 단 높이가 낮음 | `rig_hat.CUFF_FRONT_V`를 위(음수 쪽)로 |
| 비니가 머리카락과 합쳐 보임 | 모자와 머리 명도가 같음 | `palette.hat`을 머리보다 두 단계 밝게 |
| 두머 룩에서 피부가 잿빛 | 기본 채도 과소 | `looks.DOOMER`의 `saturation` 상향 |

### 5단계 (전달) 결과 전달

- 최종 PNG와 사용한 명세 JSON을 함께 전달하여 재현 가능성을 확보
- 같은 명세와 같은 `canvas.seed`, `hair.seed`는 항상 같은 이미지를 산출한다.

## 확장

- 새 포즈, 해부 표식, 손 제스처, 의상, 장면, 시간대, 정물 세트, 화풍 추가 절차는 `references/pipeline.md` 참조
- 인체 비례의 출처, 환산식, 형태 설계(손과 발 포함), 검수 절차는 `references/anatomy.md` 참조. 인체 형태를 바꾸면 `python scripts/check_proportions.py`(비례 오차, 윤곽 혹, 손발 비율 검사)가 통과해야 한다
- 화풍 렌더러의 내부 파라미터와 튜닝 방법은 `references/styles.md` 참조
- 확장 시 원칙은 "리그와 장면은 도형만, 화풍은 합성만" 담당하는 분리를 유지하는 것

## 한계

- 얼굴은 정면에서 3/4 측면 사이(`face_yaw` -0.35에서 0.35)만 지원하며 완전한 측면 얼굴은 없다. 몸을 측면으로 돌려도 얼굴은 관찰자 쪽 3/4로 그려진다. 뒷모습은 뒤통수 또는 어깨 너머 얼굴 중 하나다
- 의상은 고정 디자인이며 길이와 색만 바꾼다. 천의 펄럭임과 바람은 스커트와 코트 자락에만 있다
- 카메라는 눈높이 정사영에 가까운 시점 1종이다. 내려다보기와 올려다보기는 없다
- 포즈는 사전 정의 10종과 관절 직접 지정이다. 손가락으로 물건 쥐기(소품)는 없다
- 투샷은 의상 인물 2-3명이다. 상호작용은 손잡기 1종이며 어깨동무, 포옹은 없다. 인체 습작은 투샷을 지원하지 않는다
- 배경 합성은 장면을 인물 뒤에 깐 것이다. 인물의 발이 장면의 원근 바닥 위치를 계산해 서는 것은 아니다
- 남성 비례 목표는 공개된 남성 요약 통계에서 추정한 값이다. 손발 크기와 엉덩이 두께는 설계값이다
- 장면 구도는 장소(`scene.site`)마다 1종이며 구성 요소 배치는 시드로만 변한다. 시간대 6종, 장소 도시 2종과 풍경 2종, 정물 세트 5종은 고정 프리셋이다.
- 수채는 배경 가장자리에 종이 여백을 남긴다. 밤 장면과 `doomer` 룩에서는 어두운 하늘 둘레에 흰 여백이 생겨 어울리지 않으므로 다른 화풍을 권한다.
- 유화는 작은 눈송이를 붓 자국으로 번지게 칠한다. 인물 위의 가까운 눈송이는 둥근 얼룩처럼 보일 수 있다.
- 모자는 비니 1종이다. 챙 모자, 후드 쓰기, 목도리는 없다.
- 손가락은 관절 단위로 표현된다. 손톱은 근접 구도(화면 6 px 이상)에서만 그려지고 손금, 관절 주름, 발톱은 없다.
- 발가락은 엄지와 나머지 4개로 모델링되지만 발가락을 따로 움직이는 제스처는 없다. 구두는 뾰족한 펌프스 1종이다.
- 인체 습작의 뒷모습 포즈에서도 얼굴은 정면 얼굴 리그로 그려 고개를 돌린 것처럼 보인다.
- 체형 변형의 비례 목표는 기본 체형 목표에 체형 배율을 곱한 구성 검사다. 새 조사 자료에서 온 값이 아니다.
- 확산모델 수준의 사실성은 목표가 아니다. 목표는 사람이 그린 공정을 재현 가능한 코드로 남기는 것이다.
