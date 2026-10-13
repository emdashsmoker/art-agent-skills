# 기획 선택지

사용자에게 제시할 선택지, 추천 기본값, 사양 반영 위치를 축별로 정리

## 질의 방법

- 미정 축만 골라 한 번에 묶어 질의
    + 축마다 선택지 3-5개와 추천 기본값 1개를 제시
    + 사용자가 요청에서 이미 밝힌 축은 다시 묻지 않음
- 사용자가 "알아서", "추천대로"라고 답하면 기본값을 적용하고 적용 내역을 1회 보고
- 축 사이 충돌은 질의 전에 정리
    + 예: 수묵화를 고르면 색감 축은 의미가 줄어듦. 해당 축은 질의에서 제외

## 축 1. 목적

| 선택지 | 캔버스 | 비고 |
| --- | --- | --- |
| 감상용 일러스트 (기본) | `aspect "4:5"` | 인물 중심 |
| 프로필, 아이콘 | `"1:1"` | 흉상 또는 얼굴 |
| 포스터, 표지 | `"2:3"` 또는 `"3:4"` | 전신, 여백 확보 |
| 배경화면 | `"16:9"` | 풍경 또는 인물을 한쪽에 배치 |
| 휴대폰 배경 | `"9:16"` | 세로 구도 |
| 스톡 일러스트 | `"1:1"` 또는 `"4:3"` | `flat` 화풍, 단색 배경 |
| 컨셉 시트, 습작 | `"3:4"` | `pencil`, `lineart`, `clay` |

## 축 2. 주제와 장르

| 장르 | 구성 요소 | 시작 예제 |
| --- | --- | --- |
| 인물 초상 | `figures` 1명, `studio` 또는 `plain_color` | `portrait_anime.json` |
| 전신 인물 | `figures`, 자세 프리셋 | `classical_venus.json`, `webtoon_evening.json` |
| 인물과 배경 | `figures`, `landscape` | `hanbok_ink_wash.json`, `kimono_woodblock.json` |
| 다인 장면 | `figures` 2명 이상. 몸이 닿는 투샷은 `pairs`, 3명 이상이 닿는 줄은 `groups`. 풍경 속 인물은 카메라 `fit: "people"` | `seaside_walk_watercolor.json`, `couple_dance_classical.json`, `anime_friends_trio.json`, `gouache_picnic.json` |
| 남성 인물 | 남성 프리셋, 수염, 남성 머리 모양 | `classical_david.json`, `figure_study_male_anime.json`, `portrait_bearded_oil.json`, `webtoon_suit_city.json` |
| 풍경 | `landscape` 프리셋 | `lake_watercolor.json`, `city_night_street.json` |
| 정물 | `room`, `props` | `still_life_oil.json`, 현대 정물 `modern_desk_digital.json` |
| 실내 장면 | `room`, 가구와 기기 | `living_room_night.json` |
| 스톡 아트 | `figures`, `props`, `plain_color` | `stock_office_flat.json` |

## 축 3. 화풍

| 계열 | 화풍 이름 | 어울리는 주제 |
| --- | --- | --- |
| 셀화 | `anime`, `anime_film`, `webtoon`, `comic`, `manga`, `lineart` | 캐릭터, 액션, 도시 |
| 평면 | `flat`, `woodblock` | 스톡 아트, 동양풍 인물과 풍경 |
| 물 매체 | `watercolor`, `watercolor_loose`, `ink_wash`, `gouache` | 풍경, 서정적 인물, 배경화 |
| 유화 | `oil`, `impasto`, `classical`, `baroque`, `impressionist`, `pointillist`, `expressionist` | 정물, 고전 인물, 풍경 |
| 건식 | `pastel`, `pencil`, `charcoal`, `pen`, `pen_wash` | 습작, 인체 연구 |
| 디지털 | `digital` | 세미실사 인물 |

- 기본값은 주제에 따라 결정
    + 캐릭터 인물은 `anime`, 사실적 인물은 `webtoon` 또는 `digital`, 고전 인체 습작은 `classical`
    + 풍경은 `watercolor` 또는 `gouache`, 정물은 `oil`, 스톡 아트는 `flat`
- 사용자가 화풍을 정하지 못하면 `--styles`로 3종 비교 시트를 먼저 제시

## 축 4. 인물

| 항목 | 선택지 | 기본값 |
| --- | --- | --- |
| 체형과 얼굴 | 여성: `woman`(날카로운 턱선), `woman_fuller`, `woman_slender`, `woman_soft`, `woman_athletic`, `woman_classical`, `woman_mature`, `woman_elder`, `woman_anime` / 남성: `man`, `man_athletic`, `man_slim`, `man_classical`, `man_mature`, `man_elder`, `man_anime` / `androgynous` | `woman` |
| 피부 | `porcelain`, `fair`, `light`, `medium`, `olive`, `tan`, `brown`, `dark`, `marble` | `light` |
| 머리 모양 | `long_straight`, `long_wavy`, `very_long`, `shoulder`, `long_male`, `bob`, `pixie`, `curly`, `afro`, `buzz`, `short_crop`, `textured_crop`, `side_part`, `undercut`, `slick_back`, `ponytail`, `low_ponytail`, `bun`, `chignon`, `man_bun`, `bald` | 여성 `long_straight`, 남성 `side_part` |
| 수염 | `none`, `stubble`, `short_beard`, `full_beard`, `goatee`, `mustache` | `none` |
| 얼굴 양식화 | `none`, `semi`, `anime`, `chibi` | 프리셋 기본값 |
| 앞머리 | `none`, `wispy`, `full`, `side`, `curtain`, `long` | `none` |
| 머리 색 | `black`, `dark_brown`, `brown`, `auburn`, `red`, `blonde`, `golden`, `platinum`, `gray`, `white`, `silver`, `blue`, `pink`, `purple`, `teal` | `dark_brown` |
| 눈 색 | `dark`, `brown`, `hazel`, `amber`, `green`, `blue`, `gray`, `violet`, `red` | `brown` |
| 표정 | `neutral`, `soft_smile`, `smile`, `serene`, `eyes_closed`, `serious`, `determined`, `sad`, `surprised`, `angry`, `melancholy`, `smirk` | `neutral` |
| 의상 | `references/figures.md`의 의상 표 | 주제에 맞춰 제안 |
| 자세 | `references/figures.md`의 자세 표 | `contrapposto` |

- 사용자가 취향을 밝혔다면 기본값을 그 취향으로 교체
- 18세 미만 인물은 옷을 입은 모습만. 노출, 속옷 차림, 성적 연출은 하지 않음 (엔진이 의상을 검사)

## 축 5. 구도

| 항목 | 선택지 | 기본값 |
| --- | --- | --- |
| 샷 | `full`(전신), `knee`, `cowboy`(허벅지 위), `medium`(허리 위), `bust`(흉상), `closeup`, `face`, `over_shoulder`(두 사람 대화) | 초상은 `bust`, 전신화는 `full` |
| 시점 높이 | `pitch` 음수(올려다봄. -15 이하는 지면 가까이에서 광각), 0-5(눈높이), 15 이상(내려다봄) | 3 |
| 기울임 | `roll` 각도(더치 틸트. 불안, 긴장감) | 0 |
| 방향 | `yaw` 0(정면), ±20(살짝 비낌), ±45(반측면), ±90(측면), 180(뒷모습) | -15 |
| 배치 | `offset` [x, y]. 화면 비율 단위. ±0.12 근처가 삼분할 | [0, 0] |
| 여백 | `fill` 0.6(여백 많음) - 0.9(꽉 참) | 0.82 |

## 축 6. 조명

| 프리셋 | 인상 | 어울리는 화풍 |
| --- | --- | --- |
| `three_quarter` (기본) | 자연스러운 입체감 | 전반 |
| `front`, `loop`, `butterfly` | 얼굴 그림자 최소, 화사함 | `anime`, `flat`, 뷰티 초상 |
| `rembrandt` | 한쪽 뺨에 삼각형 빛, 극적 | `classical`, `oil`, `baroque` |
| `side`, `split` | 강한 명암 분할 | `charcoal`, `comic`, 느와르 |
| `rim`, `back` | 윤곽 빛, 분위기 | `anime_film`, `webtoon`, `digital` |
| `soft`, `flat` | 그림자 약함 | `flat`, `watercolor` |
| `top`, `under` | 무대, 공포 | 특수 연출 |

- 분위기 색(`mood`): `neutral`, `warm`, `cool`, `candle`, `moon`, `old_master`, `pastel`, `neon`, `noir`
- 야외는 시간대가 조명을 결정: `day`, `golden_hour`, `sunset`, `dawn`, `overcast`, `dusk`, `night`

## 축 7. 색감

| 선택지 (`post.grade`) | 인상 |
| --- | --- |
| `natural` (기본) | 화풍 고유색 유지 |
| `warm`, `cool` | 색온도 이동 |
| `vivid`, `muted`, `pastel` | 채도 조절 |
| `monochrome`, `sepia`, `noir` | 단색 계열 |
| `vintage`, `cinematic`, `dreamy`, `neon` | 연출 |

- 개별 색은 직접 지정 가능
    + 의상 색은 `figures[].colors`, 사물 색은 `props[].colors`, 배경 색은 `environment`

## 축 8. 디테일

| 선택지 (`canvas.detail`) | 긴 변 | 용도 | 소요 시간 |
| --- | --- | --- | --- |
| `draft` | 640px | 시안, 화풍 비교 | 수 초 |
| `standard` (기본) | 1024px | 일반 감상 | 10-30초 |
| `fine` | 1536px | 인쇄, 얼굴 디테일 | 30-90초 |
| `max` | 2048px | 대형 출력 | 1-3분 |

> (소요 시간 기준) CPU 2코어 측정값. 유화 계열이 가장 느림

## 축 9. 배경

| 선택지 | 설명 |
| --- | --- |
| `plain_color` | 단색. 스톡 아트, 습작 |
| `studio` | 그라데이션 배경지와 바닥 그림자. 초상의 기본 |
| `room` | 벽과 바닥. 정물, 실내 인물 |
| `landscape` | `meadow`, `hills`, `mountain_lake`, `seaside`, `forest`, `desert`, `snow`, `garden`, `city`, `plain` |

## 디자인 방향 문서 양식

사양 작성 전에 아래 양식으로 `brief.md`를 작성

```markdown
# (그림 제목)

## 핵심 인상
- 보는 사람이 가장 먼저 느껴야 할 인상 1문장

## 구성
- (주제) 누가 또는 무엇이 어디에 있는가
- (구도) 샷, 시점, 화면 내 배치와 여백
- (시선 흐름) 시선이 처음 닿는 곳과 이동 경로

## 색과 톤
- (주조색) 화면을 지배하는 색 1-2개
- (강조색) 시선을 끄는 색 1개와 위치
- (명암) 밝은 그림인가 어두운 그림인가, 대비의 강도

## 빛
- 광원의 방향과 성격, 분위기 색

## 화풍
- 선택한 화풍과 선택 이유
- 조정할 파라미터와 의도

## 확정된 선택과 기본값 적용 내역
- 사용자가 정한 항목
- 기본값으로 채운 항목
```
