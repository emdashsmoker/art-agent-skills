# 장면 스펙 레퍼런스

## 구조 개요
- 스펙은 JSON 객체 1개
- 모든 필드에 기본값 존재, 필요한 필드만 기재
    + `{"style": "watercolor"}` 1줄로도 렌더 가능
- 전체 기본값 확인 명령: `python scripts/render.py --print-defaults`
- 허용값 밖의 값은 렌더 전에 오류와 허용 목록을 출력

## 최상위 필드

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| subject | character, still_life, landscape, city, interior | character | 주제 |
| canvas.width, canvas.height | 256-4096 | 1024, 1280 | 출력 해상도(px) |
| canvas.seed | 정수 | 7 | 헤어 다발 편차, 붓터치, 종이 질감의 난수 시드 |
| quality | draft, final | final | final은 2배 해상도로 렌더 후 축소 |
| framing | closeup, bust, waist, full, wide | bust | 구도 (closeup은 얼굴과 목이 화면을 채움, wide는 장면 속 작은 전신 인물의 원경 설정샷) |
| style | anime_cel, soft_illust, painterly, watercolor | anime_cel | 화풍 |
| characters | character 객체 2개 이상의 배열 | 없음 | 투샷과 단체 (있으면 character 대신 사용, 인원 제한 없음) |
| pair.contact | none, hand_hold, shoulder_arm | none | 투샷 접촉 포즈 (2명 전용) |
| pair.lead | 0, 1 | 0 | shoulder_arm에서 팔을 두르는 인물의 characters 인덱스 |
| pair.rows | 1-인원수 정수 | 1 | 단체의 줄 수 (2 이상이면 뒷줄이 작고 높게 서서 앞줄 머리 사이로 보임) |
| mood | none, doomer | none | 무드 프리셋 (색보정, 배경, 표정 기본값 묶음, 아래 mood 절 참조) |

- framing이 full이고 canvas 크기를 생략하면 캔버스가 960x1600으로 자동 설정
- framing이 wide이고 canvas 크기를 생략하면 캔버스가 1600x1000으로 자동 설정
- body.pose가 lie이고 canvas 크기를 생략하면 캔버스 1600x1000과 bed 배경이 자동 설정
- subject가 character 외 주제이고 canvas 크기를 생략하면 캔버스가 1280x960으로 자동 설정
- framing, character, background는 subject가 character일 때만 사용
- characters가 있으면 framing 기본값은 waist, 캔버스 기본값은 waist 1360x1024, full 1280x1600, wide 1600x1000
    + 맨 앞줄 인원 3명부터 1명당 가로 폭 추가 (waist 480px, full 420px, wide 120px), 최대 4096px

## character (인물)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| gender | female, male | female | 성별 (male은 남성 프리셋과 남성 골격 적용) |
| view | front, back, side | front | 시점 (back은 뒷모습, side는 옆모습 프로필) |
| facing | right, left | right | 옆모습이 바라보는 화면 방향 (view side 전용) |
| skin | hex | #F9E2D2 | 피부 기본색 |
| face_shape | oval, round, sharp, square | oval | 턱선 형태 (square는 각진 남성형 턱) |
| head_scale | 0.9-1.1 권장 | 1.0 | 두상 크기 배율 |
| head.yaw | -40-40 | 15 | 좌우 회전(도), 양수는 화면 오른쪽을 향함 |
| head.pitch | -15-15 권장 | 0 | 상하 끄덕임(도), 양수는 아래를 봄 |
| head.roll | -10-10 권장 | -3 | 고개 기울기(도) |
| body.yaw | -25-25 | 0 | 몸통 좌우 회전(도), 15-25는 3/4 구도 (먼 쪽 가슴이 몸 윤곽 밖으로 보임) |
| body.roll | -5-5 | 0 | 상체 기울기(도) |
| body.pose | relaxed, close, behind, pocket, wave, hand_on_hip, hands_on_hips, arms_crossed, chin_rest, hair_tuck, hands_behind_head, walk, lean, sit, lie | relaxed | 팔 포즈 또는 전신 자세 |
| body.stance | straight, contrapposto, wide, walk, lean, sit, lie | straight, 전신 자세는 같은 이름 | 다리 자세 (full 구도에서 보임) |
| body.seat | chair, stool, bed | chair | 앉는 자리 (pose sit 전용, bed는 침대 가장자리) |
| body.figure | slim, balanced, curvy, athletic | balanced | 체형 (curvy는 여성 전용, athletic은 남성 전용) |
| body.bust | small, medium, large, xlarge | medium | 가슴 크기 (여성 전용, large 이상은 옆 볼륨이 팔 앞으로 나옴) |
| body.muscle | 0-1 | slim 0.10, balanced 0.30, athletic 0.50 | 남성 근육 표현 강도 (0 매끈, 1 복근과 팔 근육이 가장 선명) |
| body.hands.right, body.hands.left | open, relaxed, flat, fist, point, peace | 포즈 기본값 | 손 제스처 (right는 화면 오른쪽 손) |
| body.hold.item | phone, can, cigarette | 없음 | 한 손에 쥔 물건 (view front 전용) |
| body.hold.side | right, left | right | 물건을 쥔 손 (화면 기준) |
| place.x | 0-1 | 자동 | 단독 인물의 캔버스 가로 위치 비율 (wide 구도에서 인물을 장면 한쪽에 둘 때 사용) |

- (pose 선택) relaxed, close는 팔을 내리고 손을 허벅지 옆에 둠
- (pose 선택) wave는 화면 오른쪽 손을 얼굴 옆으로 들어 손바닥을 보임 (손과 소매가 헤어 위에 그려짐)
- (pose 선택) hand_on_hip, hands_on_hips는 손등이 보이게 허리에 손을 얹음
- (pose 선택) behind는 손을 등 뒤로 숨김
- (pose 선택) pocket은 후디 캥거루 주머니에 손을 넣음, 후디 외 의상에서는 behind로 자동 전환
- (제스처) arms_crossed는 가슴 아래 팔짱, chin_rest는 한 손으로 턱 괴기, hair_tuck은 한 손으로 귀 옆 머리 넘기기, hands_behind_head는 양손 머리 뒤 깍지
- (전신 자세) walk는 보폭과 팔 스윙, lean은 벽에 등을 기댄 채 한쪽 발을 벽에 붙인 자세, sit은 정면을 향해 앉은 자세, lie는 침대에 누워 한 팔을 머리 뒤에 둔 자세
- (전신 자세) pose를 walk, lean, sit, lie로 주면 stance가 같은 이름으로 자동 설정 (stance를 직접 주면 그 값이 우선)
- (sit) 앉은 인물은 서 있는 인물보다 짧으므로 full 구도에서 화면을 다시 채우도록 자동 확대
- (lie) 인물 전체를 90도 눕혀 그림
- (lie) 침대 시트 위에 인물 그림자가 자동 추가
- (stance 선택) contrapposto는 화면 왼쪽 다리에 체중, 골반 기울기와 반대쪽 다리 벌림
- 손은 3D 손바닥과 손가락 3마디 골격을 투영한 형태, 제스처만 바꾸면 손가락 모양이 바뀜
- wave와 peace 조합: `"body": {"pose": "wave", "hands": {"right": "peace"}}`
- (figure 대체) 여성에 athletic을 주면 balanced, 남성에 curvy를 주면 athletic으로 대체
- (3/4 구도) body.yaw와 head.yaw를 같은 방향으로 주면 자연스러움 (예: body.yaw 24, head.yaw 20)
- (여성 체형) curvy는 허리가 가장 잘록하고 골반과 허벅지가 가장 넓음
- (hold) 쥔 손의 팔 자세는 물건별로 고정되고 나머지 팔은 pose를 따름
    + phone은 가슴 앞에서 손바닥으로 휴대폰 뒷면을 받친 손 (관객에게 손등과 휴대폰 뒷면이 보임), 화면의 찬 빛이 손 주변을 밝힘
    + can은 배 높이에서 손등을 관객 쪽으로 두고 캔을 감싸 쥔 손
    + cigarette은 허리 옆으로 늘어뜨린 손의 손가락 사이에 끼운 담배, 연기가 몸 바깥쪽으로 흩어지며 올라감
    + phone과 can은 손가락이 물건의 먼 쪽 가장자리를 감아 돌아 둥근 관절로 끝남
    + 시선을 물건에 두려면 head.pitch 14-18과 eyes.gaze [x, 1.2], eyes.openness 0.45-0.5 조합
- (wide) 인물 키가 캔버스 높이의 약 40%인 원경 전신, 발은 화면 아래쪽 지면에 고정
    + 배경 장면이 주인공이므로 place.x 0.3-0.4 또는 0.6-0.7로 인물을 한쪽에 두고 시선 방향에 여백 확보

### view (시점)
- front: 기본 시점, head.yaw와 body.yaw로 3/4 측면까지 회전
- back: 몸을 뒤에서 본 모습, 얼굴은 head.yaw 방향으로 어깨 너머 돌아봄
    + head.yaw 25-35 권장 (0이면 얼굴 정면이 몸 뒤쪽 실루엣 위에 겹침)
    + 등 해부 구조 적용: 척추 홈, 견갑골, 여성 허리 보조개, 남성 승모근과 광배근, 둔근 볼륨
    + 앞판 전용 디테일(단추, 넥타이, 주머니, 지퍼)은 생략, 목둘레는 뒷목 높이로 올라감
    + 홀터 드레스는 등이 파인 형태, 원피스 수영복은 등 스쿱으로 전환
    + behind 포즈는 손을 허리 뒤에 모음
- side: 옆모습 전용 템플릿 (코, 입술, 턱이 얼굴 윤곽선 위에 위치)
    + 가슴과 둔근은 몸 실루엣의 일부로 그림, 상의는 가슴 끝에서 아래로 떨어짐
    + 지원 자세: relaxed, walk, sit (그 외 pose는 relaxed로 그림)
    + 의상은 목둘레, 밑단, 소매, 끈, 플레어 단위로 단순화 (단추, 프린트 같은 앞판 디테일 생략)
    + facing으로 바라보는 방향 선택

### gender (남성 프리셋)
- `"gender": "male"`은 기본값과 사용자 값 사이에 남성 프리셋을 끼워 넣음 (사용자 값이 항상 우선)

| 영역 | 남성 프리셋 값 |
|---|---|
| 얼굴 | face_shape square, face.length 1.10, nose defined, lips thin, skin #F3D6C2 |
| 눈 | shape sharp, size 0.96, openness 0.82, iris 0.92, lashes none, color #4A5A6E |
| 표정 | mouth neutral, blush 0, brows straight, brow_weight 2.3, brow_lift -0.12 |
| 헤어 | style short, bangs side_swept, color #3A3234, ears visible |
| 골격 | 역삼각형 몸통, 둥근 삼각근, 판형 대흉근, 복근 6분할, 굵은 팔다리, 목젖, 손과 발 1.22배, 넓은 다리 간격 |
| 의상 | type shirt, 하의 기본값은 jeans 또는 board_shorts |

- 남성 체형 3종: slim(마른 체형), balanced(표준 체형), athletic(어깨와 가슴이 가장 넓은 체형)
- 근육 표현 강도는 체형별 기본값을 따르고 body.muscle로 직접 조절 (예: `"body": {"figure": "athletic", "muscle": 0.8}`)
- 남성 금지 의상: offshoulder_dress, crop_top, bikini, one_piece, sports_bra, camisole, slip_dress, halter_dress, bottom bikini, pencil_skirt, dolphin_shorts
- 여성 금지 의상: shirtless

### face (얼굴 세부)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| length | 0.9-1.15 | 1.0 | 얼굴 세로 길이 (코, 입 위치도 비례 이동) |
| nose | small, button, defined | small | small은 콧날 그림자, button은 둥근 코끝, defined는 콧볼과 콧대 |
| lips | thin, natural, full | natural | thin은 윗선만, natural은 아랫입술 색, full은 큐피드 활과 입술 광택 |

### eyes (눈)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| color | hex | #4F7DB8 | 홍채색 |
| shape | almond, round, droopy, sharp | almond | 눈매 (droopy는 처진 눈, sharp는 올라간 눈) |
| size | 0.85-1.15 권장 | 1.0 | 눈 크기 |
| openness | 0.6-1.1 | 1.0 | 뜬 정도 |
| tilt | -5-8 | 3 | 눈꼬리 기울기(도) |
| gaze | viewer, forward, left, right, up, down, [x, y] | viewer | 시선, viewer는 고개 방향과 무관하게 관객 응시 |
| spacing | 0.9-1.1 | 1.0 | 미간 배율 |
| iris | 0.85-1.15 | 1.0 | 홍채 크기 배율 |
| lashes | none, light, normal, heavy | normal | 속눈썹 굵기와 끝 갈래 수 |
| crease | true, false | true | 쌍꺼풀 선 |

### expression (표정)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| mouth | smile, neutral, soft, pout, open_smile, open | smile | 입 모양 |
| blush | 0-1 | 0.35 | 볼 홍조 강도 |
| blush_color | hex | #F28C8C | 홍조색 |
| brows | soft, straight, raised, sharp | soft | 눈썹 형태 (raised는 곤란한 표정) |
| eye_smile | 0-1 | 0 | 아래 눈꺼풀을 올려 웃는 눈 표현 |
| brow_weight | 0.8-2.5 | 1.0 | 눈썹 두께 배율 |
| brow_lift | -0.2-0.2 | 0 | 눈썹 높이 (음수는 눈에 가깝게 내림) |

### hair (헤어)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| color | hex | #5A3C38 | 헤어 기본색 |
| style | long, bob, ponytail, short | long | 헤어스타일 (short는 목덜미 기장, 정수리 다발, 귀 앞 구레나룻) |
| bangs | full, side_swept, parted | side_swept | 앞머리 (full은 일자형 다발, parted는 가운데 가르마) |
| length | 두상 단위 | long 2.55, bob 1.08, short 0.72 | 뒷머리 길이 |
| wave | 0-1 | 0 | 웨이브 강도 |
| volume | 0.8-1.3 | 1.0 | 두피 위 헤어 두께 |
| part_side | 1, -1 | 고개 반대쪽 | 가르마 방향 (1은 화면 오른쪽) |
| ears | hidden, visible | hidden | 귀 노출 여부 |

### outfit (의상)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| type | knit_sweater, shirt, offshoulder_dress, hoodie, crop_top, bikini, one_piece, rash_guard, beach_shirt, tank_top, shirtless, sports_bra, camisole, slip_dress, halter_dress, tee, oversized_tee | knit_sweater | 상의 |
| variant | turtleneck, crew (니트), tank, tee (크롭티), triangle, bandeau (비키니), classic, cutout (원피스 수영복), plain, print (비치 셔츠), tie, bow (셔츠) | 의상별 첫 값 | 상의 세부 형태 |
| bikini_color | hex | #2F4F7A | 래시가드, 비치 셔츠와 함께 입는 비키니 색 |
| print_color | hex | #E38A5C | 비치 셔츠 print 무늬 색 |
| color | hex | 의상별 기본색 | 상의 색 |
| bottom | a_line_skirt, jeans, bikini, board_shorts, swim_briefs, boxer_briefs, leggings, joggers, slacks, pencil_skirt, dolphin_shorts, null | 상의별 기본값 | 하의 (원피스, 드레스는 null) |
| bottom_style | classic, high_leg, string | classic | 비키니 하의 형태 |
| bottom_color | hex | 하의별 기본색, 비키니는 상의 색 | 하의 색 |
| shoes | sneakers, boots, sandals, barefoot, heels, dress_shoes | 의상별 기본값 | 신발 |
| tie_color, bow_color | hex | #7A2E3A, #2F3542 | 셔츠 tie, bow 색 |
| shoe_color | hex | 신발별 기본색 | 신발 색 |

- (여성 하의 기본값) 니트는 A라인 스커트, 셔츠, 후디, 크롭티, 탱크톱, 티셔츠는 청바지, 비키니, 래시가드, 비치 셔츠는 비키니 하의, 스포츠 브라는 레깅스, 캐미솔은 돌핀 쇼츠, 원피스, 드레스, 원피스 수영복, 오버사이즈 티는 없음
- (남성 하의 기본값) 니트, 셔츠, 후디, 탱크톱, 티셔츠는 청바지, 오버사이즈 티는 조거 팬츠, 래시가드, 비치 셔츠, shirtless는 board_shorts
- (신발 기본값) 수영복 계열 상의와 수영복, 속옷 하의, 홈웨어(camisole, oversized_tee)는 맨발, 드레스(slip_dress, halter_dress)는 heels, 슬랙스는 dress_shoes, 그 외는 sneakers
- (운동복) sports_bra는 넓은 밑밴드의 스포츠 브라, leggings는 발목 기장 밀착 레깅스, joggers는 밑단 고무줄 조거 팬츠
- (오피스룩) shirt의 variant tie는 넥타이, bow는 리본 블라우스, slacks와 pencil_skirt 위의 셔츠는 자동 턱인 (slacks는 벨트 포함)
- (파티 드레스) slip_dress는 가는 끈과 새틴 광택의 무릎 위 드레스, halter_dress는 목에 거는 끈과 뒤가 파인 드레스
- (홈웨어) camisole은 레이스 트림 캐미솔, oversized_tee는 엉덩이를 덮는 긴 티셔츠, dolphin_shorts는 옆트임 짧은 반바지
- tee는 남녀 공용 반팔 티셔츠
- beach_shirt는 단추를 푼 반팔 셔츠, 여성은 삼각 비키니 위에, 남성은 맨가슴 위에 겹쳐 입음
- tank_top은 남녀 공용 민소매, shirtless는 남성 전용 상의 탈의
- (남성 하의) board_shorts는 허벅지 중간 기장 보드 쇼츠와 옆선 줄무늬, 허리 끈
- (남성 하의) swim_briefs는 낮은 허리선 수영 브리프, boxer_briefs는 밴드 허리 박서 브리프
- 수영복과 속옷의 앞판은 매끈한 면으로 처리, 사타구니 형태는 강조하지 않음
- 하의와 신발은 waist, full 구도에서만 렌더
- 크롭티는 배꼽 위 기장, 청바지는 로우라이즈라 복부가 드러남 (스커트는 허리선이 높아 복부를 가림)
- (bottom_style) classic은 기본 브리프형, high_leg는 옆선이 골반 위로 올라간 형태, string은 작은 앞판과 끈, 골반 옆 리본
- view back에서 비키니 하의는 뒤판 형태로 그림 (classic, high_leg는 둔근 대부분을 덮는 뒤판, string은 작은 삼각 뒤판)
- 노출 의상에서는 몸통 원통 음영, 배꼽, 복부 중앙선, 서혜부 선, 가슴 아래 주름이 자동 적용
- 남성 노출 의상에서는 대흉근 아래 선, 복근 분할선, 옆구리 선, 목젖이 추가 적용
- 의상의 목둘레, 칼라, 진동은 남성의 굵은 목과 넓은 어깨에 맞춰 자동 확장

### accessories (소품)
- 배열로 지정: `["hairpin", "necklace", "earrings"]`
- hairpin은 가르마 쪽 앞머리에 핀 2개, 색상은 `character.hairpin_color`
- necklace는 체인과 펜던트, 쇄골이 드러나는 의상(셔츠, 오프숄더)에서 효과적
- earrings는 `hair.ears: "visible"`일 때만 렌더
- beanie는 이마 위까지 덮는 니트 모자 (접은 단과 골지 포함), 정수리 머리 다발을 숨기고 앞머리와 옆머리는 유지
    + 모자 색은 `character.beanie_color` (기본 #2E3038), 옆모습에도 적용

## characters (투샷, 단체)
- 인물 2명 이상을 배치하는 배열, 각 항목은 character와 같은 필드에 place를 추가
- 인원과 성별 조합 제한 없음
- 구도는 waist, full, wide 지원
- 각 인물의 pose lie는 지원하지 않음
- 접촉 포즈(pair.contact)는 2명이 한 줄로 설 때만 사용, 3명 이상은 나란히 서기와 앉기
- 무리가 캔버스보다 넓으면 인물 크기를 줄여 화면 안에 배치 (full은 지면 유지, waist는 가장 큰 인물의 두정부 유지)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| place.x | 0-1 | 자동 | 인물 중심의 캔버스 가로 위치 비율 |
| place.scale | 0.9-1.1 권장 | 1.0 | 키 배율 (남성 1.04-1.08 권장), 두 인물의 발은 같은 지면에 맞춤 |
| place.depth | 실수 | 줄 번호 | 큰 값이 뒤에 그려짐, 같으면 배열 순서대로 뒤에서 앞 |
| place.row | 0 이상 정수 | 자동 | 인물이 서는 줄 (0이 맨 앞줄) |

- (배치) place.x를 생략하면 이웃한 두 인물 간격을 두상 높이 단위로 자동 계산
    + 접촉 없음 1.95, hand_hold 2.05, shoulder_arm 1.15, 이웃 중 남성 1명당 0.25 추가, 모두 옆모습이면 1.85
- (배치) place.x를 생략하면 배열 순서대로 화면 왼쪽부터 배치
- (여러 줄) pair.rows를 주면 배열 앞쪽부터 맨 앞줄을 채움 (줄당 인원은 올림 나눗셈, 7명 2줄이면 앞 4명, 뒤 3명)
    + 뒷줄은 한 줄마다 0.93배 크기, 두상 높이 0.55배만큼 높은 지면에 서서 원근을 표현
    + 앞줄과 인원이 같은 뒷줄은 간격 절반만큼 옆으로 엇갈려 얼굴이 앞줄 머리 사이로 보임
    + 특정 인물의 줄은 place.row로 지정
- (고개) head.yaw를 생략하면 각 인물이 무리 중심을 향해 15도 회전, 홀수 인원의 가운데 인물은 정면
- (옆모습) view side이고 facing을 생략하면 무리 중심을 향함 (2명이면 마주 봄, 홀수 인원의 가운데 인물은 right)
- (hand_hold) 두 인물의 안쪽 손이 사이 지점에서 만남, 앞 인물의 손이 뒤 인물의 손가락을 감싸 쥠
    + view front, back 지원 (뒷모습으로 손잡고 걷는 구도 가능)
- (shoulder_arm) pair.lead 인물이 안쪽 팔로 상대의 어깨를 두름
    + 팔뚝이 상대의 목 뒤에서 나와 먼 쪽 어깨 위에 놓이고 손이 어깨 앞으로 늘어짐
    + 팔을 두르는 인물이 뒤에 서도록 그림 순서가 자동 결정
    + view front만 지원
- (접촉 공통) arms_crossed, sit, lie 포즈는 접촉 불가 (두 팔을 모두 쓰는 포즈)
- (접촉 공통) 안쪽 팔에 wave, chin_rest 같은 동작이 있으면 바깥 팔로 자동 이동
- 예시: 손잡은 커플 전신

```json
{"framing": "full", "pair": {"contact": "hand_hold"},
 "characters": [
   {"outfit": {"type": "offshoulder_dress", "shoes": "heels"}},
   {"gender": "male", "place": {"scale": 1.06}, "outfit": {"type": "shirt", "bottom": "slacks"}}],
 "background": {"type": "city", "city": {"time": "dusk"}}}
```

## still_life (정물화)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| wall | hex | #E6DCCB | 벽 색 |
| table | hex | #8A5A3C | 테이블 색 (반사광 색도 결정) |
| cloth | hex, null | #F2EEE6 | 테이블보 색, null이면 생략 |
| leaves | hex | #5E8A4A | 꽃 줄기와 잎 색 |
| objects | 배열 | 기본 6종 배치 | 사물 목록 |

- objects 항목 필드

| 필드 | 허용값 | 의미 |
|---|---|---|
| type | vase, bottle, cup, mug, jar, apple, orange, lemon, pear, laptop, monitor, keyboard, mouse, phone, headphones, lamp, books, plant | 사물 종류 |
| x | 0-1 | 가로 위치 (캔버스 폭 비율) |
| depth | 0-1 | 0은 테이블 뒤쪽, 1은 앞쪽 (그리는 순서와 크기도 결정) |
| scale | 0.6-1.4 | 크기 배율 |
| color | hex | 사물 색 |
| flowers | hex | vase, jar, bottle에 꽃을 꽂음 |
| liquid | hex | cup, mug 안 음료 색 |
| yaw | 도 | 현대 사물의 수평 회전 (사물별 기본값 존재) |
| screen | code, desktop, off | laptop, monitor, phone 화면 테마 (laptop 기본 code, 그 외 desktop) |
| leaves | hex | plant 잎 색 |

- 사물끼리 겹치면 depth가 큰 사물이 앞에 그려짐
- 3-6개가 적정, 가로 위치는 0.15-0.85 범위 권장
- 현대 사물은 다면체(상자, 막대, 돔) 조립체를 같은 경사 시점으로 투영하므로 윗면이 일관되게 보임
- 책상 정물은 monitor, laptop처럼 큰 사물을 depth 0.05-0.3, keyboard, mouse, phone, mug를 depth 0.5-0.7에 배치

## interior (실내)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| room | bedroom, office, cafe, pool, gym | bedroom | 방 종류 |
| wall, floor, accent | hex | 방별 팔레트 | 벽, 바닥, 강조색 |

- bedroom: 원목 바닥, 커튼 창, 침대, 협탁과 스탠드, 벽 액자
- office: 블라인드 창, 모니터와 키보드가 놓인 책상, 화분, 머그, 책장
- cafe: 메뉴 보드, 펜던트 조명, 카운터와 커피 머신, 원형 테이블
- pool: 하늘, 낮은 생울타리, 수영장 물과 잔물결, 파라솔, 선베드
- gym: 고무 매트 바닥, 거울 벽, 덤벨 랙, 벤치, 케틀벨
- 인물 배경으로 쓰면 인물 구도의 두상 크기에 맞춰 가구 축척을 자동 조정

## landscape (풍경화)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| time | day, sunset, misty, night | day | 시간대 (하늘, 광원, 산과 물 색 세트, night는 달, 별, 달빛 광원) |
| clouds | 0-5 | 3 | 적운 개수 |
| tree | true, false | true | 전경 나무 (광원 반대편에 배치) |
| flowers | hex | #F4F0E0 | 들꽃 색 |

- 구성은 고정: 하늘, 산맥 3겹(원경 설산, 중경 설산, 근경 침엽수 언덕), 호수와 반사, 초원
- 화면 구성 변화는 canvas.seed로 조정 (능선, 구름, 나무 형태가 바뀜)

## city (도시화)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| time | day, dusk, night | day | 시간대 (하늘, 광원, 창문 불빛 비율) |
| camera_x | -4-4 | -1.8 | 카메라 좌우 위치(m), 0이면 좌우 대칭 거리 |
| awning | hex | #5E7F6E | 상점 차양 색 |
| wires | true, false | false | 전봇대와 늘어진 전선 (거리 양쪽 전봇대, 길을 가로지르는 전선) |

- 1점 투시 거리 풍경: 건물 정면, 창문, 상점, 차양, 가로등, 원경 스카이라인
- 건물 높이와 색 배치는 canvas.seed로 바뀜

## lighting (조명)

| 필드 | 허용값 | 기본값 | 의미 |
|---|---|---|---|
| key | upper_left, upper_right, front, side_left, side_right, [x, y, z] | upper_left | 주광 방향 (화면 기준 x 오른쪽, y 아래, z 관객) |
| key_color | hex | #FFF4E6 | 주광색 |
| rim_color | hex | #FFE2B8 | 역광 테두리색 |
| rim_strength | 0-1 | 0.55 | 역광 강도 |
| rim_dir | [x, y] | 주광 반대편 | 역광 방향 |

- 주광 방향이 그림자 위치, 선 굵기 편차, 홍채 하이라이트 위치를 동시에 결정
- landscape와 city는 time 세트의 광원을 기본 사용, lighting.key를 upper_left 외 값으로 주면 그 방향을 사용

## background (배경)

| type | 기본 colors | 특징 |
|---|---|---|
| plain | [#E9EEF3] | 단색 |
| gradient | [상단, 하단] | 세로 그라데이션과 두상 뒤 은은한 광원 |
| sky | [상단 하늘, 하단 하늘, 구름] | 노이즈 기반 구름 |
| bokeh | [상단, 하단, 광원] | 야경 느낌의 원형 빛망울 |
| window | [벽 상단, 벽 하단, 햇빛] | 사선 창문 빛줄기와 창틀 |
| beach | [하늘 상단, 수평선 하늘, 바다, 모래] | 바다 수평선, 물결 반짝임, 파도선, 모래, 뭉게구름 |
| bed | [시트, 베개, 이불] | 위에서 내려다본 침대 시트, 베개, 이불 (pose lie 기본 배경) |
| bedroom, office, cafe, pool, gym | 없음 | 실내 장면을 인물 배경으로 렌더, `"interior": {...}`에 wall, floor, accent 사용 가능 |
| landscape | 없음 | 풍경화 장면을 인물 배경으로 렌더, `"landscape": {...}`에 landscape 필드 사용 (tree 기본값 false) |
| city | 없음 | 도시 거리 장면을 인물 배경으로 렌더, `"city": {...}`에 city 필드 사용 |

- landscape, city 배경은 장면의 광원을 인물에 그대로 적용
    + 노을, 해 질 녘, 밤에는 인물에 장면 색조와 역광을 입혀 합성 티를 줄임
- full 구도에서 beach, landscape, city, 실내 배경이면 발밑 그림자가 자동 추가
- watercolor 화풍에서 plain, gradient 배경은 인물 주변부터 종이 여백으로 바래고 그 외 배경은 장면을 유지
- 예시: `"background": {"type": "city", "city": {"time": "night"}}`

## post (후보정)
- 생략 시 화풍별 기본값 적용, 지정한 키만 덮어씀

| 필드 | 범위 | 의미 |
|---|---|---|
| light_wash | 0-1 | 광원 쪽 난색, 반대쪽 한색 글레이즈 |
| bloom | 0-1 | 밝은 영역 번짐 |
| grade | neutral, warm, cool, sunset, doomer | 스플릿 토닝 (doomer는 탈색, 남색 그림자, 바랜 암부) |
| grade_amount | 0-1 | 토닝 강도 |
| vignette | 0-0.4 | 외곽 어둡게 |
| grain | 0-0.02 | 필름 입자 |
| vibrance | 0-0.3 | 저채도 색 채도 보강 |

## mood (무드 프리셋)
- 여러 필드의 기본값을 묶어 한 번에 적용하는 프리셋, 사용자가 직접 준 값이 항상 우선
- doomer: 밤의 고독을 담은 차가운 저채도 그림 (빈 밤거리, 전선, 무표정한 지친 눈)

| 대상 | doomer 기본값 |
|---|---|
| post | grade doomer, grade_amount 1.0, grain 0.018, vignette 0.30, light_wash 0, vibrance 0 |
| background (인물) | 밤 도시 거리와 전선 (`{"type": "city", "city": {"time": "night", "wires": true}}`) |
| city, landscape | time night, city는 wires true |
| character | eyes.openness 0.80, expression mouth neutral, blush 0.06, eye_smile 0, brows soft |

- background를 직접 주거나 pose lie(침대 배경)이면 배경 기본값은 적용하지 않음
- 투샷과 단체는 characters의 모든 인물에 character 기본값 적용
- 어울리는 조합: 비니(accessories beanie), 어두운 후디, hold 소품, wide 원경, 창가 밤 실내(window 배경 어두운 색)
- 예시: 밤거리에서 담배를 든 비니 남성

```json
{"style": "anime_cel", "framing": "waist", "mood": "doomer",
 "character": {"gender": "male", "head": {"yaw": -12, "pitch": 4}, "eyes": {"openness": 0.72},
   "accessories": ["beanie"], "body": {"hold": {"item": "cigarette", "side": "left"}},
   "outfit": {"type": "hoodie", "color": "#2A2C34", "bottom": "jeans"}}}
```

## 팔레트 구성 요령
- 헤어, 의상, 배경 중 1개만 고채도로 두고 나머지는 저채도로 배치
- 배경은 의상색의 보색 또는 인접색 저채도가 인물 분리에 유리
- 헤어가 흑발이면 배경 명도를 높이고, 금발이나 은발이면 배경 명도를 낮춤
- 홍채색은 헤어색과 다른 색상환 영역을 고르면 시선이 눈으로 모임
- 피부색은 기본값 근처에서 명도만 조정 (#F9E2D2, #F3D2BE, #E8BFA3 등)
