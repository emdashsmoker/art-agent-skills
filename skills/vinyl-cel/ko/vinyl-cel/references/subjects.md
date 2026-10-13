# 소재별 안내

## 목차

- 3D 인물
- 현대 사물과 실내 장면
- 야외 장면과 두머 세트
- 광원 장면
- 전신 인물
- 손
- 풍경화
- 도시 풍경
- 정물화
- 화풍과 소재의 궁합

## 3D 인물

- (출발점) 턴어라운드 `examples/turnaround3d.py`, 자세 `examples/pose_sheet3d.py`, 의상 `examples/outfits3d.py`, 완성 장면 `examples/beach_pair3d.py`
- (구성) `Figure3D`가 얼굴 데이터(`Character`), 체형(`Build`), 자세(`Pose3D`), 머리 모양(`Hair3D`), 의상(`Outfit3D`), 카메라를 묶음
    + 길이 단위는 머리 높이이며 원점은 골반, y는 아래, z는 정면 시점의 관찰자 쪽
    + 좌우 이름은 정면 시점의 화면 기준이므로 `right`는 정면에서 화면 오른쪽(+x)
    + `position`은 골반의 캔버스 위치, `ground`를 주면 바닥에 닿는 부위가 그 높이에 오도록 인물을 내림
    + 바닥에 닿는 부위는 `figure3d.ground_points()`가 정함: 선 자세와 앉은 자세는 발바닥, 눕기와 무릎 꿇기는 가장 낮게 처진 신체와 옷 부위(뒤통수, 등, 발뒤꿈치, 무릎, 발등)
- (카메라) `yaw` 0은 정면, 양수는 인물의 앞면을 화면 오른쪽으로 돌림, π/2는 측면, π는 뒷모습
    + `pitch` 기본 0.16은 약간 내려다보는 시점이며 발등이 보임, 0은 수평 시점
- (얼굴) 머리가 화면에 대해 돌아간 각도로 얼굴 표현을 고름
    + `abs(yaw) <= 0.85`는 초상 리그의 눈, 코, 입, 눈썹을 얼굴 앞면에 붙임
    + `abs(yaw) <= 2.05`는 옆얼굴의 눈 1개와 입선, 그 너머는 뒤통수이므로 얼굴을 그리지 않음
    + 여성은 `adult_face()`, 남성은 `male_face()`(가는 눈, 낮은 눈썹, 긴 하관, 어두운 홍채, 짙은 피부)
    + `male_face()`는 속눈썹을 가늘게 하고 바깥 끝 꼬리를 없앰(`lash_weight` 0.55, `lash_flicks` False), 눈썹을 굵게(`brow_weight` 1.65), 홍채를 작게(`iris_scale` 0.88), 입술색과 볼 홍조를 약하게(`lip_tint` 0.30, `blush_strength` 0.35) 함
- (체형) `Build(sex, shoulders, bust, waist, hips, thighs, limbs, muscle)`
    + `FEMALE_AVERAGE`, `FEMALE_GLAMOUR`(가슴 1.32, 허리 0.84, 골반 1.12, 허벅지 1.06)
    + `MALE_SLIM`(어깨 1.12, 근육 0.25), `MALE_ATHLETIC`(어깨 1.26, 팔다리 굵기 1.20, 근육 1.0, 복근)
    + 몸통은 `rig3d.TRUNK` 단면표(사타구니에서 목까지 10개 단면), 팔다리는 `ARM`, `LEG` 조절점과 반지름
    + 가슴, 대흉근, 엉덩이, 삼각근, 승모근은 별도 타원체이며 승모근이 목에서 어깨로 내려가는 사선을 만듦
- (자세) `Pose3D`는 관절별 국소 회전 `(rx, ry, rz)`와 손 자세, 손을 목표점에 놓는 `Reach`를 묶음
    + 아래를 향한 뼈는 `rx` 양수가 뒤로 감, 따라서 무릎은 `rx` 양수로 굽고 다리와 팔을 앞으로 들 때는 음수
    + 위를 향한 뼈(척추, 목, 머리)는 `rx` 양수가 앞으로 숙임, `ry`는 뼈를 축으로 비틂, `rz` 양수는 화면 왼쪽으로 기울임
    + 팔꿈치는 `rx` 음수로 굽으며 양수를 주면 과신전이 됨
    + `Reach(target=(관절, 국소 좌표), pole=팔꿈치가 향할 방향, fingers=손가락 방향, palm=손바닥 방향)`
    + `fingers`와 `palm`은 가슴 기준 방향이며 손목 굽힘은 `rig3d.WRIST_LIMIT`(1.25라디안)에서 멈춤
    + 목표가 팔 길이 밖이면 팔을 편 채 목표 쪽을 가리킴, 앉기의 무릎처럼 먼 목표는 허벅지 중간으로 옮김
    + 새 자세는 `rig3d.pose(head=(...), reach={"right": Reach(...)}, hands={"right": FIST})`로 만들고 `POSES`에 등록
    + 바닥 자세는 골반 회전으로 몸 전체를 눕힘: `pelvis=(-1.52, 0, 0)`은 등을 대고 눕기(머리가 -z), `(π/2, 0, 0)`은 엎드리기(머리가 +z)
    + 바닥 자세는 높이를 따로 정하지 않으며 배치할 때 가장 낮은 부위가 바닥에 닿음, 여러 부위가 함께 닿도록 골반과 고관절 각도를 미세 조정(`selftest`의 floor 항목)
- (자세 목록) `rig3d.POSES` 27종
    + 서기: `stand`, `a_pose`, `contrapposto`, `hand_on_hip`, `arms_crossed`, `wave`, `point`, `think`, `hands_behind`, `cheer`, `peace`, `hands_in_pockets`
    + 움직임: `walk`, `run`(앞으로 기운 상체, 주먹 쥔 팔 흔들기, 디딤발 1개가 바닥)
    + 앉기와 바닥: `sit`, `kneel`(무릎 꿇고 선 자세, 발등이 바닥), `kneel_sit`(무릎 꿇고 발 위에 앉기, 손은 허벅지), `lie_back`(등을 대고 눕기), `lie_front`(엎드려 팔꿈치를 짚고 턱을 괸 자세, 무릎을 굽혀 발이 위로)
    + 기기 사용: `sit_type`, `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug`, `sit_game`
    + 담배: `stand_smoke`(왼손은 주머니, 오른손은 담배), `sit_smoke`(가슴 앞에 든 담배), `props3d.held_cigarette()`와 함께 사용
    + `hands_in_pockets`는 손가락이 엉덩이 안쪽으로 향하므로 바지류(`jeans`, `trousers`, `hot_pants`, `swim_trunks`)와 함께 사용, 바지가 손을 덮고 주머니 부풂(`wardrobe3d.pocket_hands`)을 만듦
    + 엉덩이를 덮는 상의(티셔츠, 셔츠, 후드티, 재킷)는 손 위를 덮는 주머니 부풂을 만들고 긴 소매는 손목 위에서 끝나 그 안으로 들어감(`tuck_into_pocket`), 후드티는 손을 앞주머니에 넣은 모습
- (좌우 반전) `rig3d.mirrored(자세)`는 좌우를 맞바꾼 자세를 반환
    + 측면 구도에서 손동작을 카메라 쪽 손으로 옮길 때 사용(`mirrored(rig3d.HAND_ON_HIP)`)
    + 회전은 x축 성분 유지, y와 z 성분 반전, 손 목표점과 손 방향은 x 좌표 반전
- (손) `HandPose3D(curl, spread, thumb_out, thumb_curl)`, 프리셋 `RELAXED`, `OPEN`, `FIST`, `POINTING`, `HOLDING`, `PEACE`, `RUN_HAND`, `POCKET_GRIP`, `CUPPED`, `SMOKE_GRIP`
    + 손가락은 마디 3개의 구 사슬이므로 쥔 손과 브이 손을 모든 각도에서 표현
- (머리카락) `Hair3D`는 두피층, 덩어리(`cap`, `lobes`), 앞머리 리본, 옆머리, 뒷머리 판, 포니테일, 짧은 머리 뾰족 다발로 구성
    + 두피층은 두개골보다 5% 큰 타원체이며 얼굴 앞 개구부와 `scalp_drop`(옆 머리선), `nape`(뒷머리선) 아래를 잘라냄
    + 짧은 남성 머리는 `scalp_drop`을 귀 위로 올려 귀와 구레나룻이 보임
    + 가닥선과 광택 띠는 표면에 붙인 선(데칼)이며 긴 뒷머리에도 가닥선이 내려감
    + 긴 뒷머리 끝은 길이가 다른 가닥 5개로 갈라짐(`Hair3D.tips`, `LONG_HAIR`는 `BACK_TIPS`), 가닥은 뒷머리 판과 같은 부품이라 경계에 부풂이 생기지 않음
    + 옆머리와 얼굴 옆 머리는 끝으로 갈수록 얇아져 뾰족하게 끝남(`LOCK_TIP_THICKNESS`)
- (의상) 옷은 몸 형태를 바깥으로 띄운 복사본이므로 어떤 체형과 자세에도 맞음
    + 두께 상수는 `TIGHT` 0.030, `FITTED` 0.040, `LOOSE` 0.055, `BULKY` 0.080(머리 높이)
    + `TIGHT`는 피부끼리 녹아 붙는 부풂(`body3d.SMOOTH_BLEND`/4 = 0.025)보다 커야 피부가 비치지 않음
    + 겹쳐 입는 옷은 `GARMENT_LAYERS`의 층 번호만큼 `LAYER_GAP`(0.02)씩 더 띄움
    + 하의 위에 입는 상의는 허리 아래에서 `FITTED` 이상으로 띄우고 허벅지 윗부분과 엉덩이 덮개를 자동 추가
    + 재킷의 V자 앞섶과 비키니의 다리 트임은 잘라내기 함수(`cut`)로 만듦, 여러 조각으로 된 형태는 조각을 합친 면에서 한 번에 자르므로 잘린 가장자리가 매끈함
    + 소매와 바짓단처럼 중간에서 끝나는 관은 평평한 단(`flat_hem`)으로 끝나므로 풍선처럼 부풀지 않음
    + 끈(비키니 홀터와 등끈, 컵 사이 연결끈)은 `over_skin()`이 경로를 촘촘히 나눈 뒤 몸통 표면(`ctx.skin()`, 팔다리 제외) 밖으로 밀어내므로 가슴, 쇄골, 목에 묻혀 끊기지 않음
    + 끈은 컵에서 실제로 보이는 모서리(`_cup_corner`)에서 시작하고 홀터는 목둘레(`rig3d.neck_path`)를 감음
    + 탱크톱과 원피스의 어깨끈은 피부를 따라 눕는 납작한 띠(`strap_over_skin`)이므로 어느 체형에서도 어깨에 붙음
    + 하의 위에 입는 상의는 몸통과 엉덩이 덮개가 한 평면 밑단(`hem_cut`)에서 끝나므로 앉은 자세에서도 밑단이 고름
    + 후드티의 후드는 등 위에 납작하게 놓인 별도 층이므로 뒷모습에서 후드 윤곽이 보임
    + 반바지류(다리 길이 0.45 미만)는 앞 중심 솔기가 생겨 치마와 구분됨
    + 치마는 허벅지가 들리면 허벅지를 따라 무릎 쪽으로 눕고(`_skirt_fall`), 앉은 자세에서도 허벅지 윗면을 덮음
    + 색은 슬롯(`top`, `bottom`, `outer`, `trim`, `accent`, `shoes`, `sole`, `outer_line`, `hat`, `gear`)마다 `Material`을 지정하며 의상이 쓰는 슬롯은 `OUTFITS`의 색 사전과 같음
- (새 의상 추가) `(ctx) -> Piece(solids, decals)` 함수를 `GARMENTS`에 등록하고 `OUTFITS`에 조합을 추가
    + 몸통은 `trunk(ctx, 시작, 끝, 두께, 슬롯)`, 팔은 `sleeve()`, 다리는 `leg()`, 가슴은 `chest_cover()`, 엉덩이는 `seat_cover()`
    + 시작과 끝은 몸통 위치(0 사타구니, 0.44 허리, 0.89 어깨, 1 목, `TRUNK_LANDMARKS`)
    + 솔기, 주머니, 단추는 `decal(점 목록, 굵기, 슬롯, 불투명도, on=보일 표면 슬롯)`
    + 겹쳐 입는 옷이면 `GARMENT_LAYERS`에 층 번호를 추가하고 `selftest.py`로 피부 비침을 확인
- (새 머리 모양) `replace(head3d.PONYTAIL_HAIR, ...)`로 앞머리 각도, 길이, 덩어리를 바꿈
- (한계) 머리카락이 매끈한 덩어리라서 2D 초상의 바람에 흩날리는 머리보다 단순함
    + 치마는 허벅지를 따라 눕는 단단한 형태이므로 걸을 때의 펄럭임과 주름은 표현하지 않음
    + 회화풍은 작은 얼굴에 가장 가는 붓(0.9 단위)을 쓰지만 머리 높이 60 미만이면 눈 형태가 단순해짐
    + 동물, 곡예 자세(물구나무, 공중회전), 두 인물이 맞닿는 자세(포옹, 업기)는 미지원

## 현대 사물과 실내 장면

- (출발점) 사물 목록 `examples/props_sheet3d.py`, 현대 정물 `examples/desk_setup3d.py`, 사무실 `examples/desk_worker3d.py`, 거실 `examples/living_game3d.py`, 카페 `examples/cafe3d.py`, 침실 `examples/bedroom3d.py`
- (구성) `SceneCamera` 1개가 월드 전체를 비추고 `Placed` 항목(인물, 사물, 가구)이 하나의 깊이 버퍼에 그려짐
    + 월드는 머리 높이 단위, 바닥 y = 0, y는 아래, 사물 치수는 `props3d.cm()`로 실측(책상 73cm, 노트북 32 x 22cm)
    + 사물 공간의 원점은 바닥면 중심, 정면은 +z(노트북과 모니터는 사용자 쪽, 소파와 의자는 앉는 사람이 보는 쪽)
- (카메라) `SceneCamera(target, origin, scale, yaw, pitch, distance)`
    + `distance`가 눈 거리(머리 높이)이며 실내는 12-20, 넓은 사물 시트는 26, None은 정사영
    + `yaw` 양수는 월드의 정면을 화면 오른쪽으로 돌림, 인물과 화면이 함께 보이도록 0.2-0.6 비켜 섬
    + 눈이 방 밖으로 나가면 그 벽은 생략되고 바닥은 벽 너머로 이어짐(`FLOOR_MARGIN`)
- (배치) 가구의 기준점을 따라 놓으면 높이와 방향이 맞음
    + `scene3d.on_top(물체, 책상, offset=(x, 0, z), yaw=회전)`은 상판 위, offset은 가구 기준 좌표
    + `scene3d.seated(인물, 의자)`는 좌석 위, 소파는 `seated(인물, 소파, "seat_1")`
    + 좌석 높이 `furniture3d.SEAT_TOP`은 앉은 자세에서 역산하므로 모든 앉은 자세가 같은 의자에 맞음
    + 인물의 `Placed.at`은 골반 아래 바닥점이며 가장 낮은 신체 부위가 그 높이에 닿음, 따라서 누운 인물은 침대 기준점 `anchor(침대, "lie_back")`이나 `"lie_front"`에 그대로 놓음
    + `lie_back_0`, `lie_back_1`은 베개별 위치(머리가 베개 위), `lie_front`는 침대 가운데이며 인물은 침대 발치 쪽을 봄
    + 사물을 이불 위에 놓을 때는 `on_top(물체, 침대, offset, key="duvet")`
- (배치 점검) `scene3d.overlaps(items)`가 사물과 가구끼리 공유하는 부피를 찾음
    + 반환값은 `Overlap(first, second, depth, volume)` 목록이며 부피가 큰 순서, 빈 목록이면 관통 없음
    + 1cm³ 이하의 접촉(다리가 러그를 누름, 상판 위 물체)은 허용, 얇은 물체도 잡도록 깊이가 아닌 부피로 판정
    + 인물은 검사하지 않음(앉기, 타이핑, 쥐기는 의도된 접촉)
- (사물) 각진 형태는 `sdf3d`의 상자, 판, 원기둥, 원뿔대, 고리와 그 조합
    + 새 사물은 `Prop3D(name, solids, screens, ...)`를 돌려주는 함수로 만들며 `props3d.laptop()`이 견본
    + 단단한 부품은 기본 그룹(`rigid`)이므로 맞닿아도 녹아 붙지 않고 경계선이 생김
    + 자판 같은 반복은 `Grid`, 컵의 속은 `Cut`, 손잡이는 `Torus(arc=...)`
- (유리) 투명한 부품은 `Prop3D.glass`에 담으며 불투명 공정이 끝난 뒤 2차로 합성(`props3d.finish_glass`)
    + 뒤에 있는 것이 비쳐 보이고, 윤곽 쪽으로 갈수록 색이 짙어지며, 빛을 향한 면에 단단한 반사광과 얇은 윤곽선이 생김
    + 깊이 버퍼에는 쓰지 않으므로 유리가 뒤의 물체를 가리지 않음, 음료 같은 속 내용물은 일반 `solids`로 그림
    + 견본은 `props3d.drinking_glass(fill=0.6)`
    + 굴절(뒤 배경의 왜곡)은 계산하지 않음
- (케이블) `props3d.cable(points, sag=0.0)`은 점을 지나는 매끈한 선이며 `Placed(케이블)`로 월드 좌표 그대로 놓음
    + 점은 케이블이 닿는 곳이며 축이 반지름만큼 위로 뜨므로 상판이나 바닥(y = 0) 위의 점이면 그 면에 놓임
    + 상판 모서리를 넘어 바닥으로 늘어뜨리는 경로는 `desk_setup3d.py`의 `charger_cable()`이 견본
- (화면) 화면 판에 물체 전용 재질을 주고 `Screen(corners, content, material)`을 등록
    + 조명 계산 뒤 화면 콘텐츠를 네 꼭짓점에 원근 변환으로 붙이고 바깥으로 빛 번짐을 더함
    + 프리셋(`screens.PRESETS`)은 가상의 범용 화면, 다른 화면은 `function(width, height, rng) -> RGB 이미지`로 전달
- (손에 든 물체) `held_phone`, `held_mug`, `held_controller`가 손 틀에 물체를 붙임
    + 자세가 손 방향을 정하므로 `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug`, `sit_game`과 짝지어 사용
    + 타이핑(`sit_type`)은 기본 책상과 좌석 높이, 골반 앞 약 1머리의 자판 위치를 가정(`desk_worker3d.py`의 `LAPTOP_DEPTH`)
    + 휴대전화를 보는 인물은 `replace(character, gaze=(0.0, 0.10))`로 시선을 내림
- (실내) `interior.living_room()`, `office()`, `cafe()`, `bedroom()`이 벽면, 가구, 소품을 갖춘 `Room`을 반환
    + `room.places`의 가구 이름으로 인물을 앉히고 사물을 올림
    + 맞춤 방은 `Shell`, `shell_surfaces`, `trims`, `on_back_wall` 등으로 직접 구성(`desk_setup3d.py`)
    + 벽의 창문은 바깥 풍경(하늘, 도시, 거리)과 바닥의 햇빛 자국을 함께 만듦
- (한계) 문, 계단, 거울은 미제공
    + 유리는 투과와 반사광만 표현하며 굴절과 비친 상은 없음
    + 이불은 단단한 판이므로 몸을 덮은 이불과 구겨진 주름은 표현하지 않음, 누운 인물은 이불 위에 놓임

## 야외 장면과 두머 세트

- (출발점) 남성 `examples/doomer_man.py`, 여성 `doomer_woman.py`, 투샷 `doomer_pair.py`, 설정샷 `doomer_establishing.py`, 도시화 `doomer_city.py`, 풍경화 `doomer_landscape.py`, 사물화 `doomer_still.py`
- (분위기) 잠든 도시의 밤, 불 켜진 창 몇 개와 한 사람
    + 거대한 반복(같은 창, 줄지은 전봇대와 가로등) 앞에 작은 인물 1-2명
    + 탁한 청록 그늘, 나트륨 주황 빛, 바랜 검정, 낮은 채도는 색보정 `doomer`가 담당
    + 분위기만 차용하며 특정 앨범 커버, 밈 캐릭터, 실재 건물을 재현하지 않음
- (구성) `outdoor.World` 1개에 빛, 하늘, 안개, 땅, 건물, 등, 3D 항목, 전선, 눈을 담고 `draw_world`로 그림
    + 순서는 하늘, 땅, 땅의 빛 웅덩이, 젖은 반사, 건물(먼 것부터), 3D 항목(밤 조명), 전선, 연무, 내리는 눈
    + 거리는 `outdoor.metres()`로 미터 단위 입력(가로등 5.6-8m, 9층 패널 아파트 26m, 전봇대 간격 40m)
- (빛) `NIGHT`, `DUSK`, `OVERCAST`가 벽과 창, 눈 색, 인물의 환경광(`ambient`)을 함께 정함
    + 가로등 빛은 거리 제곱으로 줄고 갓이 있는 등은 원뿔(`cone`) 안만 비춤, 땅과 인물이 같은 식을 씀
    + 인물을 등 원뿔 안에 세우면 얼굴이 밝고 밖에 세우면 실루엣(투샷의 뒷모습이 견본)
    + 셀 음영 방향은 `run_cli(..., light=...)`를 등 쪽으로 맞춤(위에서 비추면 y를 크게)
    + 전구, 휴대전화 화면, 불씨, 연기는 밤 조명 뒤에 그리므로 어두운 장면에서도 밝음
- (카메라) 렌더 전에 `camera.project(점)`으로 등 머리, 인물 머리와 발, 건물 지붕의 캔버스 좌표를 계산하여 틀 안에 들어오는지 확인
    + 가로등 머리를 틀에 넣으려면 등을 인물보다 뒤에 두거나 낮은 마당 등(`street_lamp(cm(560), cm(110))`)을 사용
    + 건물이 화면을 다 덮으면 더 멀리 두어 하늘을 남김(설정샷 150-430m, 투샷 195m)
    + 1점 투시는 `yaw=0`, `pitch=0`, 길을 z 방향으로 놓음(도시화)
    + 화면 가장자리의 월드 방향은 `world_points`나 `plane_points`로 역산 가능
- (땅) 눈밭 `snow_texture(rng, light, extent, paths)`의 `paths`는 평면 좌표(0..extent)의 밟힌 길
    + 도로는 `road_texture(..., along="x"|"z")`, 젖은 도로는 `World(wet=True)`가 등빛 반사 줄기를 그림
- (건물) `panel_block(at, length, floors, rng, light, yaw)`는 입면 텍스처 4면과 지붕
    + 창은 층과 칸마다 하나, 불 켜진 창의 비율과 색은 빛 프리셋, `replace_light(NIGHT, lit_share=0.3)`로 조정
    + 건물을 길 양옆에 세우려면 왼쪽 `yaw=π/2`, 오른쪽 `yaw=-π/2`
- (거리 소품) `street3d`의 가로등, 전봇대와 전선, 벤치, 버스 정류장(유리 벽, 형광등), 자작나무
    + 앉히기는 실내와 같음: `scene3d.seated(인물, 벤치, "seat_1")`
    + 전선은 `wires_between(전봇대_목록)`, 트롤리 전선 같은 임의 전선은 `outdoor.catenary(a, b, sag)` 목록
- (인물) 겨울 의상 `winter_beanie`, `winter_headphones`, `hoodie_beanie`
    + 담배는 `props3d.held_cigarette()`와 자세 `stand_smoke`, `sit_smoke`, 연기는 자동
    + 시선을 올리는 뒷모습은 `replace(rig3d.SIT, rotations={**rig3d.SIT.rotations, "neck": (-0.10, 0, 0), "head": (-0.16, 0, 0)})`
- (실내 사물화) 벽은 `outdoor.light_plane(..., ambient=..., mask=draw_surface(...))`로 사물과 같은 밤 조명을 받음
    + 창밖(`window(..., "panel_night", ...)`)은 조명 뒤에 그려 바깥 창이 밝게 남음
- (회화풍) 입면, 땅, 전선, 거리 소품은 세밀한 붓을 요청하므로(`keep_detail`) 창과 기둥이 뭉개지지 않음, 내리는 눈은 붓질 뒤에 그림
- (한계) 건물은 상자 입면이므로 발코니와 출입구는 그림이며 입체가 아님
    + 그림자는 바닥 그림자와 접촉 그림자뿐이며 가로등이 만드는 긴 그림자는 없음
    + 비, 물웅덩이의 비친 상, 차량은 미제공

## 광원 장면

- (출발점) 밤의 책상 `examples/night_desk.py`, 오후의 창가 `sunny_reading.py`, 노을 벤치 `dusk_bench.py`, 해변 노을 `beach_sunset.py`
- (분위기) 이름 붙은 광원 하나가 인물을 감싸는 따뜻한 일상
    + 주광 1개와 보색 보조광 1개를 둠(따뜻한 주광에 차가운 보조광, 또는 그 반대)
    + 색보정은 장면의 시간대에 맞춰 `cozy_night`, `late_sun`, `golden_hour` 가운데 고름
- (방 조명) `outdoor.draw_lit_room(painter, camera, surfaces, views, items, lamps, ambient)`로 그림
    + 밤 장면은 환경광 0.3-0.4에 화면(창백한 청색, 도달 50cm)과 스탠드(따뜻한 색, 원뿔 1.05)를 함께 둠
    + 낮 장면은 환경광 0.8-0.9에 도달 5머리의 넓은 따뜻한 등을 창 앞에 두어 해를 대신함
    + 창밖(`window(..., "city_night"|"golden")`)과 해 조각(`interior.sunlight`)은 `views`로 넘겨 조명 뒤에 그림
    + `facing`이 있는 면만 조명을 받으며 모서리 그늘처럼 `facing`이 없는 면은 칠한 그대로 남음
- (야외 노을) `outdoor.World`에 노을 하늘 단계와 `replace_light(DUSK, wall=..., ambient=...)`의 따뜻한 벽색을 줌
    + 땅은 `asphalt_texture(rng, extent, color=...)`의 따뜻한 회색이며 눈밭을 쓰지 않아 두머 인상을 줄임
    + 건물은 300m 이상 떨어뜨려 화면 위쪽에 하늘을 남김
- (해변) `background.beach` 위에 노을 하늘, 해, 해의 길을 덧칠하고 인물만 3D로 그림
    + 지평선은 `outdoor.horizon_y(camera)`로 맞추고 인물은 먼 곳의 따뜻한 등 1개를 쓴 `night_lighting`으로 데움
- (구도) 얼굴 높이가 화면의 1/10-1/14인 중간 거리에서 상반신 이상이 보이게 잡음
    + 나무와 기둥은 원하는 캔버스 x에서 월드 x를 역산하여 머리 뒤를 비움(`dusk_bench.world_x`, `camera.project` 이분 탐색)
    + 캔버스 단위와 미리보기 화소를 혼동하지 않음(미리보기는 0.8배)
- (화풍) 아래를 보는 3/4 얼굴은 `illust`가 깨끗하며 애니메 선화는 코와 입 선이 갈고리처럼 이어짐
- (의상) 걷는 자세의 치마는 다리 관절 회전을 0.55배로 줄여 앞 허벅지가 치마 밖으로 나오지 않게 함(`beach_sunset.STROLL`)
- (한계) 광원은 방향이 없는 점 광원이므로 얼굴의 빛 방향은 `run_cli(..., light=...)`의 셀 음영 방향으로 맞춤
    + 창으로 드는 빛줄기, 화면 반사, 물에 비친 인물은 미제공

## 전신 인물

- (출발점) 착의는 `scripts/examples/full_body.py`, 수영복은 `scripts/examples/swimwear_beach.py`
- (구성) `Figure`가 인물 데이터(`Character`), 자세(`Pose`), 체형(`BodyShape`), 의상, 골반 위치, 머리 높이 1개의 크기를 묶음
    + 길이 단위는 머리 높이(정수리에서 턱까지 = 1)이며 서 있는 인물은 약 7.5
    + 팔다리 길이는 상수이므로 자세는 관절 각도만 변경
- (얼굴 인상) `adult_face(character)`는 하관을 1.12배로 늘리고 눈을 줄인 성숙한 인상
    + 기본 얼굴은 큰 눈의 애니메 인상
    + `head_scale` 1.0은 사실적 비례, 1.15 이상은 애니메식 큰 머리
- (체형) `BodyShape(bust, waist, hips, thighs)`는 평균 성인 여성 대비 폭 배율
    + 프리셋은 `AVERAGE`, `SLENDER`, `HOURGLASS`(가슴 1.32, 허리 0.84, 골반 1.12, 허벅지 1.06)
    + 각 값은 0.8-1.4 범위에서 사용, 범위를 넘으면 형태가 무너짐
    + 가슴은 좌우를 중심선에서 잘라 따로 부풀리므로 커져도 가운데에 골이 남음
- (자세) 팔다리 각도는 수직 아래 방향 기준이며 양수가 화면 오른쪽
    + 기울임 값은 시계 방향이 양수이므로 양수는 화면 오른쪽을 낮춤
    + 제공 자세는 `STANDING`, `CONTRAPPOSTO`, `HAND_ON_HIP`, `ARM_RAISED`, `A_POSE`
    + `wrist_left`, `wrist_right`는 팔뚝 대비 손 각도이며 허리에 올린 손의 손가락을 아래로 돌릴 때 사용
    + 새 자세는 `dataclasses.replace(CONTRAPPOSTO, upper_arm_right=0.6, ...)`로 제작
- (콘트라포스토) 골반과 어깨를 반대로 기울이고 가슴을 체중 쪽으로 옮김
    + `hip_tilt` 0.10-0.15, `shoulder_tilt` -0.07 내외, `spine_lean` 0.10 내외가 자연스러운 범위
- (팔의 앞뒤) 몸이나 옷 위에 놓이는 팔은 `arm_left_in_front` 또는 `arm_right_in_front`를 True로 지정
    + 지정하지 않은 팔은 옷보다 먼저 그려져 치마 뒤로 들어감
- (의상 레이어) 의상은 몸을 완성한 뒤 그 위에 덧입히는 레이어이며 `OUTFITS`에 등록된 함수가 그림
    + 제공 의상은 `SUNDRESS`(몸판, 끈, 플레어 치마, 신발)와 `BIKINI`(삼각 상의, 하이컷 하의, 옆 매듭, 맨발)
    + 수영복 색은 `Figure.outfit_material`, 지정하지 않으면 팔레트의 `trim`
    + 같은 `Figure`에서 `outfit`만 바꾸면 옷이 바뀜(`examples/dressup_base.py`)
- (새 의상 추가) `FigureOutfit`에 값을 추가하고 `(relief, painter, figure, skeleton)`을 받는 함수를 `OUTFITS`에 등록
    + 몸을 따르는 천은 `relief.add(..., drape=True)`, 홈을 덮고 팽팽하게 펴지는 천은 `bridge`를 지정
    + 천 마스크에 `relief.visible("body")`를 곱하면 팔과 손 위로 번지지 않음
    + 독립된 형태로 서는 천(치마)은 자체 높이 지도와 `depth=FRONT`
    + 조명 뒤에 그릴 장식(매듭, 단추)은 함수를 반환하면 `draw_figure()`가 마지막에 호출
    + `selftest.py`가 등록 누락과 수영복 덮임 범위를 점검
- (한계) 정면 입상만 지원, 얼굴은 화면에서 작으므로 표정 전달이 약함

## 손

- (출발점) `scripts/examples/hand_study.py`
- (구성) 손바닥 1개, 손가락 4개(마디 3개씩), 엄지 1개
    + 길이 단위는 손 길이(손목에서 중지 끝까지 = 1)
    + 손 틀의 원점은 손목, +y는 손가락 방향, +x는 엄지 방향
- (자세) `HandPose`의 `spread`(벌림), `curl`(굽힘 0-1), `bend`(면 안에서의 휨), `thumb_angle`
    + 제공 자세는 `OPEN_HAND`, `RELAXED_HAND`, `VICTORY_HAND`
    + 굽힌 손가락은 보이는 길이가 줄어드는 방식으로 표현
- (방향) `HandView.PALM`은 손금, `HandView.BACK`은 손톱과 손등 관절을 그림
    + `mirror=True`는 반대쪽 손, `turn`은 손이 옆으로 돌아간 정도(1.0 정면, 0.66 측면에 가까움)
    + 손가락을 위로 향하게 하려면 틀의 회전을 π로 지정
- (마무리) `draw_hand()`가 돌려준 함수를 `relief.render()` 뒤에 호출해야 손톱과 손금이 그려짐
- (한계) 주먹, 물건을 쥔 손, 손가락이 서로 얽힌 자세는 미지원

## 풍경화

- (출발점) `scripts/examples/landscape_lake.py`
- (구성) 하늘, 지형, 물 반사, 전경(풀밭, 침엽수) 순으로 그림
    + `terrain.alpine_lake_heightmap()`이 먼 산맥, 호수 분지, 카메라 앞 둔덕을 가진 높이 지도를 생성
    + `terrain.colorize()`가 고도와 경사로 눈, 바위, 초지, 숲을 나누고 햇빛과 산 그림자를 계산
    + `terrain.render()`가 카메라에서 먼 쪽으로 깊이 단면을 훑으며 화면에 투영
- (카메라) `Camera(position, eye_height, horizon, focal)`
    + `eye_height`를 높이면 호수가 넓게 보임, `horizon`은 지평선의 캔버스 y, `focal`을 키우면 산이 커짐
- (물) `scenery.reflect_water()`가 먼 호숫가를 축으로 장면을 뒤집어 물에 비춤
- (전경) `scenery.grass()`는 지면과 풀잎과 꽃, `scenery.pine()`은 층층이 쌓은 침엽수
    + 나무를 화면 양끝에 세우면 시선이 중앙의 산으로 모임
- (다른 지형) 새 지형은 높이 지도를 만드는 함수를 추가
    + 높이 지도는 1024 x 1024, y축이 카메라에서 멀어지는 방향
- (한계) 활엽수, 건물, 바다의 파도는 미제공

## 도시 풍경

- (출발점) `scripts/examples/city_dusk.py`
- (구성) 하늘, 먼 스카이라인, 도로, 건물, 간판, 젖은 노면 반사, 가로등, 빛 번짐 순
    + 월드 단위는 미터, x는 길 건너 방향, y는 위, z는 카메라에서 멀어지는 방향
    + `StreetCamera(vanishing_point, focal, eye_height)`가 투영을 담당
- (건물) `Building(side, near, depth, height, wall, lit_share, shop)`
    + 입면을 평면 텍스처로 만든 뒤 사각형으로 투시 변환하므로 창문 간격이 원근에 맞게 좁아짐
    + 건물 높이를 들쭉날쭉하게 주어야 하늘과 만나는 선이 살아남
- (젖은 노면) 하늘과 건물을 지면선 아래로 뒤집어 그린 층을 도로에 겹침
    + 뒤집을 때 건물마다 자신의 지면선을 축으로 삼으므로 반사 위치가 기하학적으로 맞음
- (빛) 창문과 간판은 발광 마스크를 돌려주며 `city.bloom()`이 번짐을 추가
- (시간대) `SKY_STOPS`, `HAZE`, `lit_share`를 바꿔 낮, 저녁, 밤을 전환
- (한계) 1점 투시만 지원, 사람과 차량은 미제공, 옥상과 지붕 형태는 평지붕만 가능

## 정물화

- (출발점) `scripts/examples/still_life.py`
- (구성) 방(벽과 탁자), 천, 뒤쪽 물체, 앞쪽 과일, 탁자 그림자, 조명, 꼭지와 잎 순
- (회전체) 병과 주전자와 배는 `lathe_object()`에 반지름 윤곽 `[(t, 반지름), ...]`을 전달
    + t는 위에서 아래로 0-1, `base_roundness`와 `top_roundness`가 양끝의 둥근 정도를 결정
- (과일) `round_fruit()`은 사과와 오렌지, `tilted_ellipse_fruit()`은 레몬, `grapes()`는 포도송이
    + `gloss`는 광택, `mottle`은 색 얼룩, `pores`는 껍질의 오돌토돌함
- (그림자) 물체를 모두 추가한 뒤 `table_shadow(relief, 밑점, 반폭)`을 호출
    + 맨 탁자와 천 위에만 떨어지고 물체 위에는 떨어지지 않음
    + 물체가 서로에게 드리우는 그림자는 `relief.render()`가 계산
- (배치) 뒤 물체의 밑점 y를 작게, 앞 물체의 밑점 y를 크게 두어야 탁자 위에 놓인 것으로 보임
- (한계) 투명한 유리의 굴절, 금속의 반사, 꽃은 미제공

## 화풍과 소재의 궁합

| 소재 | 가장 잘 맞는 화풍 | 이유 |
|---|---|---|
| 초상, 전신 | 애니메, 일러스트 | 선과 평면 색이 얼굴의 단순한 형태와 맞음 |
| 3D 인물 시트 | 애니메 | 셀 음영과 가림 선이 각도별 형태를 가장 또렷하게 보여줌 |
| 손 | 일러스트 | 연속 음영이 마디의 둥근 형태를 드러냄 |
| 풍경 | 회화, 애니메 | 붓질이 지형의 잔무늬를 덮고 큰 형태를 살림 |
| 도시 | 애니메 | 빛 번짐과 선명한 창문이 저녁 분위기를 만듦 |
| 정물 | 회화 | 명암 대비와 붓질이 고전 정물의 인상을 줌 |
| 현대 정물 | 애니메, 일러스트 | 각진 형태와 발광 화면이 선과 평면 색에서 또렷함 |
| 실내 장면 | 일러스트, 애니메 | 벽면 텍스처와 햇빛 자국이 연속 음영과 어울림, 회화는 작은 얼굴에 가는 붓을 자동 배정 |

- 인물이 없는 장면은 애니메와 일러스트의 차이가 작음
    + 두 화풍의 차이는 주로 인물의 선과 음영에서 나오기 때문
- 회화풍에서 세밀한 붓이 필요한 영역은 `canvas.importance`(0-1 지도)로 지정
    + 장면의 손 크기 사물은 `Prop3D.detail`(기본 0.85)이 자동으로 가는 붓을 지정, 가구는 0.3
- 서로 떨어진 대상을 여러 개 그린 장면은 `canvas.shade_subject_as_one = False`로 지정
    + 기본값은 대상 전체를 하나의 덩어리로 보고 광원 반대편을 어둡게 함
