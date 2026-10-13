# 예제 사양

각 파일은 그대로 렌더 가능. 가까운 예제를 복사해 수정하는 방식이 가장 빠름

```bash
python scripts/render.py examples/portrait_anime.json -o out.png
```

| 파일 | 장르 | 화풍 | 볼 만한 설정 |
| --- | --- | --- | --- |
| `portrait_anime.json` | 인물 흉상 | `anime` | `woman_anime`, `reach`의 `lay`로 손바닥을 가슴에 펴서 얹음, 손 모양 `rest` |
| `classical_venus.json` | 고전 인체 습작 | `classical` | 자세 `venus`, 어두운 배경과 `old_master` 조명 |
| `figure_study_odalisque_oil.json` | 기대 누운 인체 습작 | `classical` | 자세 `recline`, `daybed`와 `cloth`, 인물 높이 지정 |
| `figure_study_anime.json` | 애니메풍 인체 습작 | `anime` | `woman_anime`, 광택 피부(`skin_gloss`) |
| `figure_study_back_watercolor.json` | 뒷모습 인체 습작 | `watercolor` | 자세 `look_over_shoulder`, 카메라 `yaw` 158 |
| `film_cel_agent.json` | 인물과 도시 야경 | `anime_film` | `city` 야간, `tactical` 의상, 낮은 시점 |
| `webtoon_evening.json` | 세미실사 인물 | `webtoon` | 윤곽광, `post.grade` |
| `hanbok_ink_wash.json` | 인물과 여백 | `ink_wash` | 한복, 여백 구도(`fill`, `offset`) |
| `kimono_woodblock.json` | 인물과 정원 | `woodblock` | 기모노, 배에 얹은 손(`lay`), 벚나무 숲 지정 |
| `seaside_walk_watercolor.json` | 2인 장면 | `watercolor` | `pairs`의 `hold_hands`로 손잡고 걷기, 직접 카메라 |
| `couple_dance_classical.json` | 커플 댄스 | `classical` | `pairs`의 `dance`, 실내 촛불 분위기 |
| `stock_office_flat.json` | 스톡 일러스트 | `flat` | 앉은 자세, 사무 사물, `blob` 배경 |
| `still_life_oil.json` | 정물 | `oil` | `on`으로 탁자 위 배치 |
| `modern_desk_digital.json` | 현대 정물 | `digital` | 모니터(`screen: code`), 키보드, 휴대폰, 책장, 벽시계 |
| `living_room_night.json` | 실내 야경 | `anime_film` | TV(`screen: game`) 빛을 받는 인물, 소파, 낮은 주광과 `glow` |
| `lake_watercolor.json` | 풍경 | `watercolor` | 설산과 호수 반사, 숲 덩어리, 전경 액자 나무 |
| `city_night_street.json` | 도시 풍경 | `anime_film` | 밤거리, 네온, 젖은 노면 |
| `garden_impressionist.json` | 풍경 속 인물 | `impressionist` | 작은 인물, 벤치 |
| `pencil_figure_study.json` | 인체 습작 | `pencil` | 남성 체형, 측면 조명 |
| `classical_david.json` | 고전 남성 인체 습작 | `classical` | `man_classical`, 자세 `david`, `perizoma` |
| `figure_study_male_anime.json` | 애니메풍 남성 인체 습작 | `anime` | `man_anime`, `muscle_definition`, 낮은 시점 |
| `male_back_watercolor.json` | 남성 뒷모습 | `watercolor` | `man_athletic`, `undercut`, `stubble` |
| `portrait_bearded_oil.json` | 수염 난 남성 초상 | `oil` | `man_mature`, `full_beard`, 정장 |
| `webtoon_suit_city.json` | 도시 속 남성 | `webtoon` | `hands_in_pockets`, 정장 색 지정(`colors`), `stubble`, 해 질 녘 도시, 인도 위 배치 |
| `doomer_man.json` | 두머 남성 | `doomer` | `estate` 밤, 가로등 뒤에 선 인물, `hoodie_jeans`와 `beanie`, 자세 `smoke`와 손에 든 `cigarette` |
| `doomer_woman.json` | 두머 여성 | `doomer` | `estate_street` 밤, `bus_stop` 안에 앉은 인물, `long_coat` |
| `doomer_pair.json` | 두머 투샷 | `doomer` | 단지 마당 벤치, `sit_smoke`, 서로 다른 쪽을 보는 두 사람, 얼굴을 밝히는 무형 광원(`lights`) |
| `doomer_establishing.json` | 두머 설정샷 | `doomer_mono` | `estate` 해질녘, 마당을 가로지르는 작은 인물, 전신주 |
| `doomer_city.json` | 두머 도시 | `doomer` | `estate_street` 밤, 차도와 횡단보도, 나트륨 가로등 행렬 |
| `doomer_landscape.json` | 두머 풍경 | `doomer_mono` | 흐린 겨울 벌판, `power_line`, 먼 `panel_block`과 침엽수 띠 |
| `doomer_still.json` | 두머 정물 | `doomer` | 매달린 알전구(`lightbulb`의 `cord`), `ashtray`, `radio`, 엎어 둔 휴대폰 |
| `comic_desert_duel.json` | 대결 투샷 | `comic` | 사막 해질녘, 마주 선 `fight_stance` 두 명이 카메라 쪽으로 살짝 돎(`facing`에 좌표), 로우 앵글, `fit: "people"` |
| `manga_farewell_hug.json` | 이별 포옹 | `manga` | `pairs`의 `hug`, 흰 배경 한 칸, 뒤쪽 비스듬한 `medium` 구도, 검은 옷과 머리는 먹 |
| `gouache_picnic.json` | 소풍 군상 | `gouache` | 3명이 돗자리(`cloth`) 둘레에 앉고 1명은 앞에 기대 누움, `facing`에 좌표, 하이 앵글, 인물과 사물 이름으로 `fit` |
| `impasto_cafe_talk.json` | 카페 대화 | `impasto` | 원탁과 의자, 앉아서 컵을 든 손(`held_by`), 어깨 너머 구도 |
| `baroque_candle_reading.json` | 촛불 독서 | `baroque` | `read_seated`와 펼친 `book`, `candle` 빛, `fit`에 인물과 촛불 |
| `pointillist_lakeside_park.json` | 호숫가 공원 | `pointillist` | 손잡고 걸어가는 뒷모습(`pairs` `facing` 180), 풀밭에서 책 읽는 인물 |
| `expressionist_leap.json` | 도약 | `expressionist` | `jump`, 로우 앵글과 더치 틸트(`roll`) |
| `pastel_dance_rehearsal.json` | 연습실 댄스 | `pastel` | `pairs`의 `dance`와 `distance`, 몸 푸는 세 번째 인물 |
| `charcoal_studio_trio.json` | 모델 셋 습작 | `charcoal` | 서기, 무릎 꿇기, 기대 앉기. `chiton`, `perizoma`, 인체 습작 |
| `pen_office_meeting.json` | 회의실 | `pen` | 책상, 사무 의자, 노트북, 차트 화면(`tv` `screen: chart`), 서서 가리키는 발표자 |
| `pen_wash_park_bench.json` | 벤치의 노부부 | `pen_wash` | 앉은 `arm_around`, `man_elder`와 `woman_elder`, 앞이 트인 `long_coat` |
| `watercolor_loose_beach_play.json` | 해변 공놀이 | `watercolor_loose` | `run`, `jump`, `arms_up`, 공중의 `ball`(`at` 높이), 수영복 3종 |
| `lineart_fashion_lineup.json` | 의상 라인업 | `lineart` | 5명 나란히, 의상 5종과 자세 5종 |
| `anime_film_dusk_phone.json` | 휴대폰 보는 두 사람 | `anime_film` | `hand_on_shoulder`, `look_at_phone`과 손에 든 `phone`, 해 질 녘 도시 |
| `digital_portrait_closeup.json` | 근접 초상 | `digital` | `closeup`, `man_mature`, `short_beard`, `rembrandt` 조명 |
| `anime_friends_trio.json` | 어깨동무 3명 | `anime` | `groups`의 `arm_around`, 벚나무 정원, 군상 허리 구도(`fit: "people"`, `shot: "cowboy"`) |
