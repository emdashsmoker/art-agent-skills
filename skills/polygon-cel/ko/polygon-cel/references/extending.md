# 엔진 확장 가이드

## 적용 시점
- 스펙 허용값으로 요청을 표현할 수 없을 때만 코드 확장
    + 예시: 새 의상(카디건, 트렌치코트), 새 헤어(트윈테일), 새 배경(꽃밭)
- 확장 코드는 `scripts/codeillust/` 모듈에 추가하고 스펙 허용값(spec.py ENUMS)에 등록

## 핵심 자료구조

### Layer (scene.py)
- 그림 1장은 Layer 목록이며 목록 순서가 곧 앞뒤 가림 순서
- 주요 필드

| 필드 | 의미 |
|---|---|
| name | 고유 이름 (clip, cut, 캐스트 섀도 참조 키) |
| material | SKIN, HAIR, CLOTH는 음영 계산, FLAT은 단색, INK는 스트로크, GLOW는 부드러운 빛 |
| polys | 캔버스 좌표 폐곡선 목록 (합집합 채움) |
| strokes | [(척추 점열, 폭 배열)] 가변 폭 스트로크 |
| clip, cut | 다른 레이어 이름 또는 태그의 마스크와 교집합, 차집합 (먼저 처리된 레이어는 자기 clip, cut이 반영된 최종 마스크 사용) |
| line | LineSpec(폭 px, root, root_fade, hide) 외곽선, hide 마스크 안쪽 구간은 선 생략 |
| shade | ShadeSpec(inflate, normal_map, cast_tags, cast_dist, threshold, gradient, rim, spec, spec_edge, form) |
| opacity | 0이면 보조 마스크 전용 레이어 (clip, cut 재료) |
| blend, feather | 합성 방식, 마스크 흐림 |
| tags | 역할 태그, 캐스트 섀도와 clip, cut의 참조 대상 |

### 법선 맵 (shapes.py)
- `ShadeSpec.normal_map`은 `(y0, y1, x0, x1) -> (h, w, 3)` 단위 법선을 돌려주는 함수
    + 지정하면 inflate 대신 사용, 렌더러는 레이어 bbox 범위만 요청
- 제공 함수

| 함수 | 용도 |
|---|---|
| sphere_normals(cx, cy, rx, ry) | 과일, 꽃송이 |
| revolution_normals(cx, ys, rs) | 꽃병, 병, 컵 (revolution_outline이 ys, rs도 반환) |
| plane_normals(n) | 벽, 테이블, 건물 면 |
| height_normals(w, h, scale, strength, seed, base) | 초원, 거친 지면 |
| mask_normals(polys, w, h, radius, noise, scale, seed) | 산맥, 나뭇잎 덩어리, 구름 |
| teardrop_normals(cx, cy, rx, ry, top_reach, top_flat) | 가슴 (아래는 구, 위는 점점 평평) |
| ellipsoid_normals(cx, cy, rx, ry, rot) | 회전된 근육 덩어리 |

- 법선 좌표: x 오른쪽, y 아래, z 관객 방향

### 시스템이 참조하는 태그

| 태그 | 의미 |
|---|---|
| head | 얼굴, 목에 그림자를 드리우는 대상 |
| hair_front, bangs, cap, sidelock | 앞쪽 헤어, 얼굴과 옷에 그림자 |
| hair_back | 뒷머리 |
| garment, garment_top | 의상, 목 주변 의상(칼라 등) |
| body, hand, legs, forearm | 피부 부위 |
| skirt, pants, shoes | 하의와 신발 |
| blush_hatch | 셀화 전용 볼 해칭 (다른 화풍에서 제거) |
| sleeve | 소매, 앞쪽 팔뚝과 손은 첫 sleeve 레이어 직전에 삽입 |
| front, behind, raised, behind_head | 팔뚝과 손의 배치 그룹 (behind_head는 뒷머리보다 먼저 그림) |
| front_only | 뒷모습에서 제외할 앞판 전용 레이어 |
| seat | 앉은 인물 뒤의 의자, 스툴, 침대 (투샷에서는 인물 패스보다 먼저 그리는 무대 패스로 이동) |
| focus | 화풍 처리에서 주제로 취급 (수채화는 plain, gradient 배경에서 focus 밖을 종이로 페이드) |
| object, wall, tabletop, cloth, ground, building, foliage | 장면 주제의 그림자 참조 대상 |

### 좌표 변환
- `rig.head(P3)`: 두상 좌표 3D (x, y, z) → 캔버스 px, yaw, pitch, roll 반영
- `rig.head2(P2)`: 이미 투영된 두상 2D → 캔버스 px, roll만 반영
- `rig.body(P3)`, `body.to_canvas(P2, z)`: 신체 좌표 → 캔버스 px
- `OutfitBuilder.C(P)`: 신체 좌표 2D에 몸통 앞면 깊이(front_z)를 붙여 변환
- `rig.orient`: 리그 전체 회전각(도), 두상과 신체 변환 마지막 단계에 적용 (눕기 -90)
- `props.View(origin, unit, yaw)`: 사물 좌표(x 오른쪽, y 위, z 안쪽) → 캔버스 px, 경사 정사영 `Y = yb - (y + z * 0.30) * unit`
- 옆모습 `ProfileBuilder.Hc`, `Bc`: 두상, 신체 좌표 2D에 facing 방향 부호를 곱해 변환 (x는 바라보는 방향)
- `rig.body_local(C)`: 캔버스 px → 신체 좌표 2D (z = 0 평면, body2의 역변환), 투샷 접촉 팔을 상대 좌표에서 자기 좌표로 옮길 때 사용
- 치수는 전부 H(두상 높이) 단위로 작성하고 px 상수를 쓰지 않음

## 레이어 스택 순서 (character.build_layers)
- (sit) 좌석, (lie) 침대 위 그림자, (full, wide) 발밑 그림자
- (behind_head 배치) 팔뚝 피부, 손, 소매
- 뒷머리 (뒷모습에서는 의상 위로 이동)
- (behind 배치) 팔뚝 피부, 뒤쪽 소매
- (waist, full) 다리 피부
- 몸 피부 (목, 몸통, 팔 합집합), arms_mask 보조 레이어
- 쇄골 (노출 의상)
- (waist, full) 하의, 신발, (정면 sit) 무릎 아래 그림자
- 상의 몸판, (front 배치) 팔뚝 피부와 손, 소매, 칼라, 디테일
    + 손은 손바닥, 쥔 물건(hold), 손가락 순서로 그림 (캔, 휴대폰은 엄지 뒤 물건, 손 전체 순서)
- 손을 덮는 레이어 (후디 주머니)
- 몸 소품 (목걸이)
- 얼굴, 볼 홍조, 코, 입, 눈
- 헤어 캡, 정수리 다발(비니 착용 시 생략), 앞머리, 옆머리
- 눈썹 (앞머리 위로 비치는 애니메 관례)
- 헤어 광택 링, 머리 소품
- (raised 배치) 팔뚝 피부, 손, 아래쪽 소매
- 쥔 물건의 효과 (휴대폰 화면 빛, 담배 연기와 불씨 빛)
- view side는 `profile.build_layers`의 별도 스택 사용: 좌석, 뒷머리, 먼 쪽 팔다리, 몸 피부(가슴, 둔근), 하의, 신발, 상의 몸판, 가까운 팔과 손, 소매와 앞쪽 끈, 얼굴, 귀, 눈, 옆머리 다발, 헤어 덩어리와 가닥선

## 투샷과 단체 렌더 구조 (duo.py, pipeline.render_figures)
- `duo.plan(spec, W, H)`가 그림 순서(뒤에서 앞)의 `Figure` 목록 반환 (인원 제한 없음)
    + `_rows`: 인물별 줄 번호, `_ranks`: 줄 안의 왼쪽부터 순서, `_offsets`: 줄별 이웃 간격 누적과 뒷줄 엇갈림, `_place`: 두상 높이, 두정부, 중심 x, 줄별 축소와 상승, 캔버스 맞춤 축소
    + 그림 순서는 place.depth(기본값 줄 번호)가 큰 인물부터
    + Figure: 인물별 spec(character 교체), Rig, characters 인덱스, 공개 영역(reveal), 상대 위치, 공개 제외 영역(reveal_cut)
- 렌더 패스 순서
    + 배경 (장면 배경이면 장면 렌더)
    + 무대 패스: 두 인물의 seat 태그 레이어와 발밑 그림자 (이름 앞에 p0_, p1_ 접두어로 충돌 방지)
    + 인물 패스: 뒤 인물부터 앞 인물까지 1명씩 (앞 인물 커버리지가 이전 선화를 지움)
    + 공개 패스: reveal이 있는 인물을 다시 렌더하고 reveal 영역 안의 커버리지만 합성
- 화풍 처리 마스크는 패스마다 출력 해상도로 저장 후 앞 패스 커버리지로 가린 뒤 이름별 최대값으로 합침
- 단독 인물 스펙은 패스 1개로 v8과 같은 결과 (픽셀 차이 0)

### 접촉 포즈 추가
- duo.py에 `_<contact>(chars, rigs, sides, ...)` 작성
    + 상대 신체 좌표의 목표점을 `rig.body2`로 캔버스로 옮긴 뒤 `rig.body_local`로 자기 신체 좌표로 변환
    + `_local_arm`으로 팔 설정(elbow, wrist, forearm, hand, fingers, palm)을 만들어 `chars[i]["_arms"] = {side: arm}`에 저장
    + 팔꿈치 위치가 자유로우면 `_elbow`(2관절 역운동학) 사용
    + 상대 위에 보여야 하는 부위는 reveal 다각형, 상대 앞에 남아야 하는 부위는 reveal_cut 다각형으로 반환
- `_keep_posed_arm_outside`로 동작이 걸린 팔을 바깥 팔로 이동 (`FREE_ARMS`는 덮어써도 되는 팔 설정)
- spec.py `ENUMS["pair.contact"]`, `CONTACT_VIEWS`, `CONTACT_BLOCKED_POSES`, config.py `PAIR_SPACING` 등록

## 확장 레시피

### 상의 추가
- `OutfitBuilder`에 `_<type>(self, g)` 메서드 추가
    + 몸판: `self.cloth(name, self.torso(expand, hem), cut=("<목 구멍 보조>", "arms_mask"))`
    + 목 구멍: `self.neck_hole(name, depth, half)` 보조 레이어
    + 트임, 진동 등 개구부 보조 레이어는 `self.S(점열)`로 투영 (몸을 돌려도 몸통과 정렬)
    + 소매: `front, behind = self.sleeve_layers(prefix, expand)` 후 `g["back"] += behind`, `g["top"] += front`
    + 디테일: `self.ink(name, [(점열, 폭배율)], opacity)` (솔기, 주름, 단추 자리)
    + 반환값: `{"clavicles": 쇄골 노출 여부}`
- 새 의상 메서드는 wardrobe.py `WardrobeMixin`에 두면 outfit.py 비대화를 막음 (OutfitBuilder가 상속)
    + 몸에 붙는 드레스: `self.fitted_polys(ease, hem_y, with_torso)` (골반과 허벅지 볼록 껍질)
    + 앉은 자세 밑단: `self.hem(y)`가 무릎 위로 잘라 줌
- `DEFAULT_COLORS`, `DEFAULT_BOTTOM`, `DEFAULT_BOTTOM_MALE`, `TOP_HEM`에 기본값 등록
- 뒷모습 대응: 앞판 전용 레이어 이름을 outfit.py `FRONT_ONLY`에 추가하거나 `front_only` 태그 부여
- 옆모습 대응: profile.py `TOPS`에 (앞 목둘레 y, 뒤 목둘레 y, 밑단 y, 소매, 여유) 등록
- spec.py `ENUMS["character.outfit.type"]`에 이름 추가
    + 한 성별 전용이면 `FEMALE_ONLY_OUTFITS` 또는 `MALE_ONLY_OUTFITS`에도 등록
- 목둘레, 칼라 좌표는 여성 목 기준으로 작성 후 `self.nx(점열)`로 감싸 남성 목 굵기에 자동 대응
    + 진동(팔 구멍) 좌표는 `self.shoulder_dx`만큼 바깥으로 이동
    + 옷 위 가슴 음영은 `self.bust_form()` 재사용 (남성은 대흉근 강도로 자동 약화)

### 하의 추가
- `_<bottom>(self, g)` 메서드에서 `g["bottom"]`에 레이어 추가
    + 스커트류는 `self._skirt_layer(name, 오른쪽 윤곽점, color)` 재사용
    + 바지류는 `self.pants_layers(name, 허리 높이, 밑단 높이, 여유, 베벨, gap)` 재사용 (gap은 다리 사이 쐐기 폭)
    + 수영복 하의류는 `self.brief_layer(name, 오른쪽 윤곽점, color)` 재사용
- 옆모습 대응: profile.py `BOTTOMS`에 (허리 y, 밑단 y, 여유, 종류 pants|flare|fitted|brief) 등록

### 성별 골격 조정
- body.py `GENDER`에 어깨 관절, 목 폭, 손 배율, 복근 여부, 다리 간격 배율 등록
- 몸통 실루엣은 `FIGURES`(여성), `MALE_FIGURES`(남성)에 오른쪽 절반 점열로 등록
- 팔다리 폭 프로파일은 `LIMB_WIDTHS[성별]` (표본 수 자유, 근육 볼록은 표본 추가로 표현)
- 남성 근육은 musculature.py: 근육 1개는 돔 법선 피부 층 1개 (`_mass`), 경계선은 `border_lines`에 추가
- 가슴, 대흉근 형태는 body.py `bust_shape`, `crease`, `bust_normals` 3개 함수가 성별로 분기
- 얼굴, 눈, 헤어 기본값은 spec.py `MALE_PRESET`에서 조정 (사용자 값이 항상 우선)

### 헤어스타일 추가
- `HairBuilder`의 `back_layers`, `side_layers`에 스타일 분기 추가
    + 다발 1개: `self.clump_layer(name, 3D 제어점, 뿌리 폭, 폭 프로파일, tags)`
    + 두피 위 점: `self.S(x, y, lift)` (셸 표면 z 자동 계산)
    + 폭 프로파일: `blade`(앞머리형, 끝이 뾰족), `lock`(긴 다발형)
- `DEFAULT_LENGTH`와 spec.py ENUMS 등록
- 다발 폭은 대, 중, 소 리듬으로 불규칙 배치 (동일 폭 반복은 빗살처럼 보임)

### 팔 포즈와 손 제스처 추가
- body.py `ARMS`에 팔 설정 추가: elbow, wrist(화면 오른쪽 팔 기준 좌표), forearm 배치, hand 제스처, fingers 방향, palm 법선
- `POSES`에 (화면 오른쪽 팔, 화면 왼쪽 팔) 조합 등록
- hand.py `GESTURES`에 curl(마디별 굽힘 3개 × 손가락 4개), spread, thumb(abd, opp, curl) 등록
- spec.py ENUMS 등록

### 전신 자세 추가
- body.py `STANCES`에 다리 템플릿 등록: tilt, 화면 오른쪽 다리(R)와 왼쪽 다리(L)의 knee, ankle
    + `raised_foot`은 벽에 붙여 뒤로 젖힌 발 (정면에서 짧게 단축, 뒷모습에서는 숨김), `knee_caps`는 정면으로 단축된 허벅지의 무릎 캡
- `POSES`에 팔 조합, `POSE_STANCE`에 pose 이름과 stance 연결
- 리그 회전이 필요하면 character.py `make_rig`에서 orient 설정 (눕기 참조)
- 옆모습 지원은 profile.py `PROFILE_POSES`에 팔과 다리 관절 좌표 추가

### 현대 사물 추가
- props.py에 `def <kind>(kit, color, rng, **옵션)` 함수 작성 후 `PROPS`, `PROP_COLORS`, `PROP_YAW` 등록
    + 부품: `kit.box(part, origin, ex, ey, ez, color)`, `kit.rod`, `kit.dome`, `kit.revolution`, `kit.flat`
    + 화면이 있으면 `kit.screen(part, quad, theme, rng)`, `SCREEN_PROPS`에 등록
    + 부품은 뒤에서 앞 순서로 추가 (깊이 정렬 없음)
- still_life.py는 `props.PROPS`에 있는 type을 자동 인식, spec.md 표에 추가

### 실내 방 추가
- interior.py `RoomBuilder`에 방 이름 메서드 작성: `self.shell()`(벽, 바닥), `self.window`, `self.furniture_box`, `self.prop`
- `ROOMS`, `PALETTES` 등록, pipeline.py `SCENE_GRADE`에 (방, "day") 색조 등록
- spec.py ENUMS의 `interior.room`, `background.type`, character.py `GROUNDED_BACKGROUNDS` 등록

### 장면 주제 추가
- `scripts/codeillust/<주제>.py`에 `build(spec, W, H, light, seed) -> (layers, background, light)` 구현
- 파이프라인은 subject 이름으로 모듈을 불러옴, spec.py `ENUMS["subject"]`에 등록
- 주제 레이어에 focus 태그를 붙여 화풍 처리 대상 지정

### 배경 추가
- background.py `make_background`에 분기 추가, `DEFAULTS`와 ENUMS 등록
- 배경은 인물보다 저대비, 저디테일 유지

### 손 소품 추가
- handheld.py `HOLD_ARMS`에 쥔 팔 설정 등록: elbow, wrist(화면 오른쪽 팔 기준), forearm, hand, fingers, palm, wrist_shift
- `<item>_layers(body, side)` 작성 후 `BUILDERS` 등록
    + 반환값은 (mid, late): mid는 손바닥과 손가락 사이, late는 인물 전체 위에 그림
    + 손등이 관객을 향하는 물건은 레이어에 `BEHIND_HAND_TAG`를 붙여 손바닥과 손가락보다 먼저 그림
    + 이 경우 팔 설정은 hand "grip"으로 두고 fingers는 물건 앞면을 가로지르는 방향, palm은 물건을 향하는 방향으로 지정
    + 물건 위치는 `_knuckle_anchor(body, side, offset)`로 손가락 뿌리 관절 기준 계산 (손 크기 배율 자동 반영)
    + 엄지가 물건의 먼 면에 닿으면 팔 설정에 `"thumb_behind": True`를 넣어 엄지를 물건 뒤에 그림
    + 그 외 물건의 위치는 `_anchor(body, side, offset)`로 손목 기준 신체 좌표에서 계산 (화면 왼쪽 손은 x 부호 반전)
    + 신체 좌표 다각형은 `body.to_canvas(poly, Z_FRONT)`로 캔버스에 투영
- spec.py `ENUMS["character.body.hold.item"]` 등록

### 무드 추가
- spec.py `MOODS`에 이름별 spec(후보정, 장면 기본값), background(인물 배경), character(인물 기본값) 등록
- 고유 색보정이 필요하면 post.py `grade`에 분기를 추가하고 `ENUMS["post.grade"]` 등록
- `ENUMS["mood"]` 등록, 무드 값은 사용자 스펙 아래에 깔리므로 사용자 값이 항상 우선

### 화풍 추가
- styles.py에 `StyleName`, `PRESETS`(Style), `POST_DEFAULTS`, `DROP_TAGS` 등록
- `finish()`에 분기 추가: 입력은 채색 패스, 선화 패스(rgb, alpha), 레이어 마스크
- spec.py ENUMS["style"] 등록

## 주의 사항
- 보조 마스크: neck_mask, torso_mask, upper_arm_mask, arms_mask (끈, 튜브 상의, 소매 자르기에 사용)
- 여성은 bust_mask가 추가되고 upper_arm_mask, arms_mask에서 가슴 영역이 빠짐 (소매는 `self.bust_cut`으로 가슴을 비움)
- 레이어 이름 중복 금지 (마스크 저장소 키 충돌), 투샷과 단체는 인물별 패스 분리로 인물 간 중복 허용
- 남성 근육 층을 추가하면 `musculature.strength(body)`를 불투명도에 곱해 body.muscle 조절을 따르게 함
- 마스크는 raster.MaskStore에 bbox 단위 uint8로 저장, 읽을 때마다 전체 캔버스 float 배열 생성 (레이어 수백 개 장면의 메모리 절감)
- 보조 레이어는 opacity 0, 화풍 처리의 인물 마스크에서 자동 제외
- clip에 자기 자신이 가진 태그를 넣으면 자기 마스크와 교집합이 되어 무효
- clip에 이름을 여러 개 넣으면 그 마스크들의 합집합과 교집합이 됨
    + 여러 마스크의 교집합이 필요하면 보조 레이어(opacity 0)에 먼저 clip을 걸어 만든 뒤 그 이름을 참조
- 캐스트 섀도는 스택에서 위에 있는 레이어만 드리움, 순서를 먼저 확인
- polys가 2개 이상이거나 clip, cut이 있으면 선화는 최종 마스크 윤곽에서 추출
- 확장 후 `python scripts/selftest.py`와 draft 렌더로 확인
