# 작업 흐름 상세

## 목차
- 기획 질의 요령
- 선택 항목 해설
- 아트 디렉션 문서
- 러프 판정 기준
- 수정 반복 절차
- 결과 보고 형식

## 기획 질의 요령

- 질의 전에 요청문에서 확정된 항목을 먼저 추출
    + 예시: "노을 지는 호수 수채화" 요청은 subject=landscape, style=watercolor, lighting=golden_hour가 확정
- 남은 항목 중 결과를 크게 바꾸는 항목만 질의
    + 우선순위는 화풍, 화면 비율(용도), 구도와 크롭, 조명, 색감 순
    + 머리색, 눈동자색 같은 세부 항목은 기본값을 적용하고 보고에 명시
- 선택지는 3-5개로 추려 기본값을 표시하여 제시
    + 전체 목록은 `python scripts/brief_menu.py`로 출력
- 사용자가 "알아서", "기본값으로"라고 답하면 추가 질의 없이 진행
- 화풍이 미정이면 러프 완료 후 `--styles`로 후보를 렌더하여 고르게 함

## 선택 항목 해설

| 항목 | 키 | 결정하는 내용 |
|---|---|---|
| 주제 | subject | 사용할 모듈과 기본 화면 비율 |
| 화풍 | style | 매체, 얼굴 작화 방식, 마감 패스 |
| 용도 | purpose | 화면 비율 (icon, poster, book_cover, wallpaper 등) |
| 화면 비율 | format | 캔버스 크기, auto이면 용도와 주제에서 결정 |
| 인물 크롭 | framing | face, bust, half, three_quarter, full |
| 구도 | composition | 주제 위치와 수평선 높이 |
| 인물 각도 | view | front, three_quarter, profile, back |
| 디테일 | detail | 1-5, 해상도 배율과 요소 밀도 |
| 색 조합 | palette | 색상환 조합 또는 명명 팔레트 |
| 색 온도, 채도, 명도 | temperature, saturation, key | 마감 단계의 색보정 |
| 조명 | lighting | 광원 방향, 색, 그림자색, 대기 |
| 분위기 | mood | 표정, 배색, 조명 선택의 기준 |
| 배경 | background | plain, simple, landscape, city, interior, abstract |
| 인물 설정 | sex, jaw, hair_style, fringe, hair_color, eye_color, beard, skin, expression, pose, outfit | 캐릭터 외형 |
| 마감 | finish | style_default, clean, film, glow, aged |

- `Brief`가 직접 처리하는 항목: 화면 비율, 디테일 배율, 조명, 얼굴 작화 방식, 캐릭터 생성(`brief.character()`), 색보정과 마감(`brief.finish_passes()`)
    + `sex="male"`이면 등신 0.15 추가, 머리를 지정하지 않으면 `crop`과 `side_part`, beard 값으로 수염 자국 적용
    + `hair_style="beanie"`이면 앞머리를 지정하지 않을 때 none 적용, `outfit`의 hoodie와 turtleneck은 두머 차림의 기본 묶음
- 장면 스크립트에서 반영할 항목: 구도, 배경, 색 조합, 분위기
    + 색 조합은 `palette.harmony(key, scheme)` 또는 `palette.NAMED[name]`으로 색을 뽑아 배경과 의상에 사용
    + 구도는 `compose.thirds(canvas)`, `compose.golden(canvas)`의 좌표에 주제를 배치

## 아트 디렉션 문서

- `brief.to_markdown()`의 출력을 `brief.md`로 저장
- 문서 구성: 핵심 메시지, 공간과 구조, 색상과 톤, 인물, 마감
- 기본값이 적용된 항목은 "(기본값)"으로 표시됨
- 문서에 직접 보완할 내용
    + 시선이 머물 지점 1곳
    + 명암 계획: 화면에서 가장 밝은 곳과 가장 어두운 곳
    + 색 계획: 주조색 1개, 보조색 1-2개, 강조색 1개

## 러프 판정 기준

- 구도: 주제가 의도한 위치(중앙 또는 삼분할 교점)에 있는가
- 크롭: 인물의 관절(손목, 무릎, 발목)에서 화면이 잘리지 않는가
- 3단 명도: 주제와 배경이 서로 다른 명도 덩어리로 분리되는가
- 시선 지점: 가장 강한 명도 대비가 시선 지점에 있는가
- 여백: 주제 주변과 화면 가장자리에 숨 쉴 공간이 있는가

## 수정 반복 절차

- 결함을 1개씩 특정하여 수정 (여러 수치를 동시에 바꾸면 원인 추적이 어려움)
- 수정 대상 단계 판단
    + 형태, 위치, 비례 문제는 `build`의 구조 코드
    + 명암 덩어리 문제는 조명(`--light`, `Light` 인자)
    + 질감, 번짐, 붓질 문제는 화풍 파라미터(`paint(..., params=...)`, 장면 스크립트는 `build` 반환값의 `style_params`)
    + 색감, 대비 문제는 마감 패스
- 구조를 고친 뒤에는 러프부터 다시 확인
- 반복 한도: 검수와 수정 3회 안에 수렴하지 않으면 사용자에게 현재 결과와 남은 결함을 공유하고 방향을 질의

## 결과 보고 형식

- 최종 이미지 파일
- 선택 내역: 사용자가 지정한 항목과 기본값으로 적용한 항목을 구분
- 재현 방법: 장면 스크립트 경로와 실행 명령, 시드
- 남은 한계가 있으면 1-2줄로 명시
