# 화풍

화풍 목록, 조정 파라미터, 미술사조 재현법, 문제 처방

## 지정 방법

```json
"style": "watercolor"
"style": {"name": "oil", "impasto": 1.0, "saturation": 1.1}
```

- 같은 장면을 여러 화풍으로 비교: `python scripts/render.py spec.json -o sheet.png --styles anime,gouache,oil`
- 화풍 고유의 마감(`bloom`, `grain` 등)은 `post`로 덮어쓸 수 있음

## 셀화 계열

| 이름 | 설명 | 권장 조명 |
| --- | --- | --- |
| `anime` | TV 애니메 셀화. 2톤, 채색선, 얼굴 그림자 단순화 | `front`, `loop`, `three_quarter` |
| `anime_film` | 극장판 리얼계 셀화. 3톤, 가는 암색 선, 절제된 채도, 필름 그레인 | `rim`, `rembrandt`, 야간 |
| `webtoon` | 세미실사 웹툰. 부드러운 톤 경계, 그라데이션, 가는 채색선, 광채 | `rim`, `three_quarter` |
| `comic` | 서양 코믹스. 굵은 검정 선, 망점 그림자 | `side`, `rembrandt` |
| `manga` | 흑백 만화 펜선. 검은 머리와 어두운 옷은 먹, 그림자는 스크린톤 | `side`, `front` |
| `lineart` | 선화만 | 무관 |

| 파라미터 | 기본 | 효과 |
| --- | --- | --- |
| `shadow_threshold` | 0.40 | 그림자 영역의 넓이. 높일수록 그림자가 넓음 |
| `deep_threshold` | 없음 | 2단 그림자(3톤)의 경계 |
| `shadow_tint`, `skin_shadow_tint` | 자동 | 그림자 색 배율. 피부는 따뜻한 분홍 기본 |
| `band_softness` | 0.012 | 톤 경계의 부드러움. 0.1이면 웹툰풍 |
| `face_smooth` | 2.6 | 얼굴 그림자 단순화. 4-5면 애니메 얼굴 |
| `quiet_face` | false | 얼굴 안쪽의 코와 볼 선을 생략하고 윤곽과 이목구비만 그림. `anime` 기본 true |
| `relief_lines` | 0 | 근육 홈(복근, 가슴 아래)을 따라 가는 선. 그림자 쪽에서 진함. `anime` 기본 0.45 |
| `face_lift` | 0 | 얼굴 중간톤을 밝혀 빛 반대편에만 그림자를 남김. `anime` 기본 0.45 |
| `gradient` | 0 | 톤 아래 은은한 입체 그라데이션 |
| `highlight_threshold`, `rim_light` | 없음, 0 | 하이라이트 톤, 윤곽광 |
| `gloss_highlight`, `gloss_threshold` | 0.8, 0.16 | 윤기 있는 재질(유리, 입술, 광택 피부)에 그리는 밝은 면의 세기와 넓이 |
| `line_width` | 1.6 | 선 굵기(픽셀). 0이면 선 없음 |
| `colored_lines` | 0.6 | 0은 단색 선, 1은 면 색을 따르는 채색선 |
| `line_taper`, `line_wobble` | 0 | 선의 강약, 손떨림 |
| `thin_in_light` | 0.5 | 밝은 쪽 선을 가늘게 |
| `halftone_shadows` | false | 그림자를 망점으로 |
| `saturation` | 1.0 | 채도 |
| `background_blur` | 0 | 배경 흐림. 인물 분리 |

## 평면 계열

| 이름 | 설명 |
| --- | --- |
| `flat` | 플랫 벡터, 스톡 일러스트. 외곽선 없음, 은은한 그림자 1단, 입자 그라데이션 |
| `woodblock` | 우키요에 목판화. 제한된 먹색, 균일한 주선, 하늘의 바림, 나뭇결 |

- `flat` 파라미터: `shadow_strength` 0.16, `pastel` 0.12, `grain` 0.06, `line_width` 0, `blob [x, y, 반경]`과 `blob_color`(주제 뒤 유기적 도형)
    + 스톡 일러스트는 `plain_color` 배경에 `blob`을 넣고 조명은 `soft`
- `woodblock` 파라미터: `line_width` 1.7, `bokashi` 0.55, `bokashi_color`, `grain` 0.35, `misregister` 1.2, `palette`(색 목록), `palette_softness` 0.18

## 물 매체 계열

| 이름 | 설명 |
| --- | --- |
| `watercolor` | 투명 수채. 연필 밑그림, 가장자리 안료 고임, 종이 결 |
| `watercolor_loose` | 웻 온 웻. 큰 번짐, 밑그림 없음 |
| `ink_wash` | 수묵. 농담 3단, 강약 있는 필선, 안개, 낙관 |
| `gouache` | 불투명 수채. 애니메이션 배경화 질감 |

| `watercolor` 파라미터 | 기본 | 효과 |
| --- | --- | --- |
| `wash_levels` | (0.34, 0.66) | 그림자 겹칠 횟수와 경계 |
| `paper_white` | 0.86 | 이보다 밝은 곳은 종이 흰색으로 남김 |
| `edge_darkening` | 0.42 | 칠 가장자리의 안료 고임 |
| `granulation`, `turbulence` | 0.32, 0.28 | 종이 결 입자, 물 얼룩 |
| `bleed`, `wobble`, `simplify` | 1.6, 2.2, 3.0 | 번짐, 가장자리 떨림, 세부 단순화 |
| `pencil` | 0.30 | 연필 밑그림 농도 |
| `vignette_wash` | true | 단색 배경에서 주제 주변만 칠하고 종이 여백을 남김 |
| `background_wash` | 자동 | 주변 워시의 색 |

- `ink_wash` 파라미터: `levels`, `line_width` 2.2, `mist` 0.5, `dry_brush` 0.45, `color_hint` 0.12(담채), `seal` true, `paper_color`
    + 여백이 중요. 카메라 `fill`을 0.5-0.65로 낮추고 `offset`으로 주제를 한쪽에 배치

## 유화 계열

| 이름 | 설명 | 권장 조명 |
| --- | --- | --- |
| `oil` | 알라 프리마. 보이는 붓질, 따뜻한 바탕칠 | `rembrandt`, `three_quarter` |
| `impasto` | 두꺼운 물감, 나이프 터치 | `side` |
| `classical` | 르네상스, 아카데미 유화. 스푸마토, 글레이징, 바니시, 균열 | `rembrandt` + `old_master` |
| `baroque` | 테네브리즘. 어둠에서 떠오르는 인물 | `side`, `rembrandt` + `candle` |
| `impressionist` | 짧은 붓질, 분할된 색, 밝은 팔레트 | 야외 `day`, `golden_hour` |
| `pointillist` | 순색의 점 | 야외 |
| `expressionist` | 길고 굵은 붓질, 과장된 색, 소용돌이 | 자유 |
| `pastel` | 소프트 파스텔. 유색지, 종이 결에 걸리는 분필 | `soft` |

| `oil` 파라미터 | 기본 | 효과 |
| --- | --- | --- |
| `brush_radii` | (26, 12, 6, 3, 1.6) | 붓 크기 단계. 큰 붓에서 작은 붓 순서로 덧칠 |
| `stroke_length` | 9 | 붓질 길이 |
| `fidelity` | 0.35 | 얼굴과 손을 얼마나 정밀하게 마무리할지 |
| `color_jitter`, `hue_jitter` | 0.05, 0 | 붓질마다의 명도 변화, 색상 변화 |
| `impasto` | 0.5 | 물감 두께감 |
| `ground` | 갈색 | 바탕칠 색. 붓질 사이로 비침 |
| `along_form` | false | 붓 방향을 형태를 감싸는 쪽에서 따라가는 쪽으로 |
| `swirl` | 0.3 | 하늘과 배경 붓 방향의 소용돌이 정도 |
| `terminator_saturation` | 0.3 | 명암 경계의 채도 상승 |
| `contrast`, `saturation` | 1.0 | 관찰 대비와 채도 |
| `coverage`, `density` | 1.0 | 바탕 노출 정도, 붓질 밀도 |

| `classical` 파라미터 | 기본 | 효과 |
| --- | --- | --- |
| `finish` | 0.62 | 0은 거친 붓질, 1은 매끈한 아카데미 마감 |
| `sfumato` | 1.6 | 윤곽의 흐림 |
| `lost_edges` | 0.5 | 그림자 쪽 윤곽이 배경에 녹는 정도 |
| `chiaroscuro` | 1.2 | 명암 대비 |
| `umber` | 암갈색 | 그림자가 가라앉는 밑칠 색 |
| `glaze`, `varnish` | 호박색, 0.30 | 바니시의 황변 |
| `craquelure`, `vignette` | 0.35, 0.35 | 균열, 주변 어두움 |

## 건식, 디지털 계열

| 이름 | 설명 | 주요 파라미터 |
| --- | --- | --- |
| `pencil` | 흑연 해칭 | `hatch_spacing` 5, `darkness` 0.85, `smudge` 0.25, `line_width` 1.3 |
| `charcoal` | 목탄. 거친 종이 | `darkness` 1.0 |
| `pen`, `pen_wash` | 펜 크로스해칭, 세피아 담채 | `hatch_spacing` 4, `wash` |
| `digital` | 세미실사 디지털 페인팅 | `smooth` 0.55, `stroke_opacity` 0.5, `edge_line` 0.35, `rim_light` 0.25, `skin_glow` 0.18 |
| `clay` | 밑그림 확인용 단순 음영 | 없음 |

## 두머 계열 (이 스킬의 시그니처)

포스트소비에트 포스트펑크 음반과 인터넷 두머 그림의 정서. 밤의 판넬 아파트 단지, 나트륨 가로등, 담배 불씨

| 이름 | 설명 | 권장 장면 |
| --- | --- | --- |
| `doomer` | 회청색으로 빠진 밤. 나트륨 가로등, 불 켜진 창, 불씨처럼 따뜻하고 밝은 것만 색을 지킴. 필름 입자, 주변부 감광 | `estate`, `estate_street` 밤, 알전구 부엌 |
| `doomer_mono` | 거친 입자의 흑백 필름 사진. 짙은 검정과 회색 하늘 | 해질녘 단지, 흐린 겨울 벌판 |

| 파라미터 | 기본 | 효과 |
| --- | --- | --- |
| `desaturate` | 0.6 | 따뜻하지 않은 색을 회색으로 빼는 정도 |
| `keep_warm` | 1.0 | 따뜻하고 밝은 색을 지키는 정도. 0이면 전부 빠짐 |
| `contrast` | 1.25 | `doomer_mono`의 흑백 대비 |

- 구성 요령
    + 인물은 작게, 반복되는 창문 격자는 크게
    + 따뜻한 빛은 1-2곳만. 가로등 하나, 불씨 하나
    + 달빛을 낮춤(`"light": {"key": 0.3, "ambient": 0.2}`)
    + 인물은 짙은 옷(`hoodie_jeans`, `long_coat`)에 `beanie`
- 예제: `doomer_man`, `doomer_woman`, `doomer_pair`, `doomer_establishing`, `doomer_city`, `doomer_landscape`, `doomer_still`
- 특정 음반 표지의 구도와 인물은 복제하지 않음. 분위기만 가져옴

## 미술사조와 장르 재현

| 목표 | 구성 |
| --- | --- |
| 르네상스 누드, 비너스 | `woman_classical`, 자세 `venus` 또는 `contrapposto`, 긴 웨이브 금발, `nude` 또는 `chiton`, 어두운 `studio`에 `glow`, 조명 `rembrandt` + `old_master`, 화풍 `classical`, `look.flesh_variation` 0.6 |
| 오달리스크, 기대 누운 누드 | 자세 `recline`, 사물 `daybed`와 `cloth`, 인물 `position` z 0.47, 화풍 `classical` 또는 `oil` |
| 애니메풍 누드 | `woman_anime` 또는 `woman_curvy`, 자세 `arms_behind_head`나 `s_curve`, `look.skin_gloss` 0.4, 조명 `loop` + `pastel`, 화풍 `anime` 또는 `webtoon` |
| 고전 남성 누드, 다비드 | `man_classical`, 자세 `david`, 짧은 곱슬(`curly`, `length_scale` 0.45), `perizoma`, 어두운 `studio`, 조명 `rembrandt` + `old_master`, 화풍 `classical` |
| 애니메풍 남성 누드 | `man_anime` 또는 `man_athletic`, 자세 `arms_behind_head`나 `heroic`, `briefs`, `look.muscle_definition` 0.45, 조명 `loop`, 화풍 `anime` |
| 수염 난 남성 초상 | `man_mature`, `beard: full_beard`, `slick_back`, `suit`, 조명 `rembrandt`, 화풍 `oil` 또는 `classical` |
| 뒷모습 누드 | 자세 `look_over_shoulder`, 카메라 `yaw` 160, 화풍 `watercolor` 또는 `pastel` |
| 바로크 초상 | 조명 `side` + `candle`, 화풍 `baroque`, `ambient` 0.12 |
| 네덜란드 정물 | `room`(어두운 벽), `table`, `cloth`, 그릇과 과일, 조명 `rembrandt` + `old_master`, 화풍 `oil` 또는 `classical` |
| 인상주의 야외 | `meadow` 또는 `garden`, 시간 `day`, 화풍 `impressionist`, 인물은 작게 |
| 후기 인상주의 소용돌이 | 화풍 `expressionist`, `swirl` 1.0, 야간 풍경 |
| 점묘 | 화풍 `pointillist`, 야외, `canvas.detail` `fine` |
| 수묵 산수 | `hills` 또는 `mountain_lake`, 시간 `overcast`, `haze_distance` 60, 화풍 `ink_wash`, `mist` 0.7 |
| 수묵 인물, 미인도 | `hanbok`, `chignon`, 여백 많은 구도, 화풍 `ink_wash`, `color_hint` 0.2 |
| 우키요에 미인화 | `kimono`, `chignon`, `garden`에 `sakura`, 화풍 `woodblock` |
| 우키요에 풍경 | `seaside` 또는 `snow`, 시간 `dawn`, 화풍 `woodblock` |
| TV 애니메 캐릭터 | `woman_anime`, 조명 `loop` + `pastel`, 화풍 `anime` |
| 극장판 리얼계 셀화 | `woman_athletic` 또는 `woman`, `tactical`, `city` + `night`, 조명 `rim`, 화풍 `anime_film` |
| 비 온 뒤 밤거리 | `city` + `night`(젖은 노면과 네온 자동), 화풍 `anime_film` 또는 `gouache`, `post.bloom` 0.3 |
| 해질녘 바다 | `seaside` + `sunset`, `sun_side` `front`, 화풍 `watercolor` 또는 `oil` |
| 세미실사 웹툰 | `woman` 또는 `man_slim`, 조명 `rim` + `warm`, 화풍 `webtoon`, `post.grade` `cinematic` |
| 세미실사 일러스트 | 화풍 `digital`, 조명 `rembrandt` 또는 `rim`, `canvas.detail` `fine` |
| 스톡 일러스트 | `plain_color`, 사무 사물, 조명 `soft`, 화풍 `flat` + `blob` |
| 팝아트 | 화풍 `comic`, `post.grade` `vivid` |
| 느와르 | 조명 `split` + `noir`, 화풍 `charcoal` 또는 `comic`, `post.grade` `noir` |
| 인체 습작 | `plain_color`, 조명 `side`, 화풍 `pencil` 또는 `charcoal` |

## 문제와 처방

| 증상 | 처방 |
| --- | --- |
| 얼굴에 그림자 조각이 지저분함 (셀화) | 조명을 `front`나 `loop`로, `face_smooth` 4-5, `face_lift` 0.4-0.6, `shadow_threshold` 0.3 |
| 전체가 그림자에 잠김 | `light.azimuth`를 0-45로, `ambient`를 0.4 이상으로 |
| 선이 너무 많고 복잡함 | `crease_deg`를 50으로, `line_width`를 줄임 |
| 유화에서 얼굴이 뭉개짐 | `canvas.detail`을 `fine`으로, 샷을 더 가깝게, `fidelity` 0.6 |
| 유화 붓질이 너무 거침 | `brush_radii`를 작게, `color_jitter` 0.03, 또는 `classical`로 |
| 고전 유화가 흐릿함 | `finish` 0.8, `sfumato` 1.0, `chiaroscuro` 1.4 |
| 수채가 탁함 | `wash_levels`를 1단 `(0.5,)`으로, `saturation` 1.15, `lift` 0.2 |
| 수채 종이 여백이 없음 | `studio` 대신 `plain_color` 흰 배경, `vignette_wash` true |
| 배경이 주제와 경쟁함 | `background_blur`, `haze_distance` 감소, `post.vignette` |
| 색이 밋밋함 | `mood` 변경, `post.grade` `vivid` 또는 `cinematic`, 의상에 강조색 1개 |
| 주제가 작음 | 샷을 한 단계 가깝게, `fill` 0.9 |
| 그림이 단조로움 | `offset`으로 삼분할 배치, `yaw` ±20, 소품 또는 나무 추가 |
