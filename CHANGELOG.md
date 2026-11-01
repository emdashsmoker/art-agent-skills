# Changelog

Dates are in UTC.

날짜는 UTC 기준으로 표기

<!--
Changelog rules
- (Timing) Record each pull request right after it is merged into main.
- (Scope) Check all main history since the last commit that changed CHANGELOG.md and record every merge that is still missing.
- (History command) TZ=UTC git log --first-parent --date=format-local:%Y-%m-%d origin/main
- (Date) Use the UTC date of the merge commit in YYYY-MM-DD format.
- (Date order) Keep the newest date at the top.
- (Entry unit) Write one entry for each change that users can notice.
- (Grouping) Combine same-day pull requests on the same topic into one entry and list every pull request number.
- (Splitting) Split a pull request that contains unrelated changes into separate entries.
- (Skill header) Group the entries of each date under ### headers named after the folders under skills/. Use ### Common for repository-wide changes and changes that apply to every skill. Repeat a change that applies to several skills under each of their headers.
- (Entry order) Put the Common header first and sort the other headers by skill folder name. List the entries under each header in pull request order.
- (English entries) List the English entries first under each header with the "-" bullet.
- (Korean entries) Leave one blank line after the English entries and list the same changes in the same order with the "*" bullet so that they render as a separate list.
- (English format) - Description that starts with the change type verb (#PR number)
- (Korean format) * Korean noun-ending description that ends with the change type word (#PR number)
- (Korean style) Write each Korean entry in formal note style as a simple sentence (단문) with a noun ending. Keep one subject-predicate relation per entry, turn other clauses into noun phrases, and split an entry that carries two messages. Avoid colloquial expressions and placeholder nouns such as 것, 곳, 거, 셈 and 부분.
- (Change types) Added (추가), Changed (변경), Fixed (수정), Removed (삭제), Action needed (필요)
- (Include) Changes to skill outputs, usage steps, or installation.
- (Exclude) Typo and wording fixes, demo image replacements, README changes unrelated to installation, internal refactoring without behavior changes, and commits that only change CHANGELOG.md.
- (Push) Commit on top of the latest main and push directly to main.
-->

## 2026-11-01

### image-gen
- Changed when the references are read: defects.md after every generation before the check, and postprocess.md as well when the answers use post-processing (#26)
- Changed the visual check to name defect types with example lists, take a second look at each fragile part enlarged on its own, and keep a one-line record per image that lists the enlarged files (#26, #30)
- Changed the candidate mode procedures into references/candidates.md, read only when the candidate generation answer is not 1x (#27)
- Added a body count item to the visual check with standard counts such as 5 fingers per hand, 5 toes per foot, 2 arms, 2 legs, and 4 legs for a four-legged animal, recorded as numbers per part, with all five digits as the ideal for exposed hands and feet and a note that hands touching the floor, the body, clothing, hair, and the like are easy to miss (#28, #30, #31)
- Added a face defect item to the visual check with placement criteria for the eyes, nose, and mouth (#28)
- Added body distortion of large parts (including melting into another body part, except twists the pose explains), distorted machine structures, and distorted building forms to the visual check examples (#28, #29, #30)
- Changed shape judgment to one rule that treats a difference no visible cause explains, and any unsure case, as a defect for every subject including objects and buildings, with occlusion limited to something visibly covering the part and unintended darkness, blur, or out-of-focus areas not counted as occlusion (#28, #30)
- Changed the slight-blur exception and the uncounted distant figures to apply only to the background (#30)
- Added an upfront workaround item to the pre-generation questions: off (default), optimize (keeps the subject and scene and removes, hides, or frames out defect-prone parts), and maximum (keeps only the message and may replace the subject after a confirmation), recorded by preflight.py as a required --upfront-workaround answer (#32)
- Added a visual check item that treats a typical diffusion model defect, a visually wrong part, or staging the user asked for that did not appear as a defect, even outside the list (#32)
- Added a prompt rule that replaces proper nouns, technical terms, and rare words the model may not know with a similar common object or spells out their look with 2 or 3 simple shapes, materials, or colors, and reports each rewrite on delivery (#32)
- Changed the content policy to match the other non-diffusion image generation skills (#33)
- Added pose rules to the workarounds that prefer simple static poses, avoid staging that is harder to draw, and place hands where a remaining defect is easy to trim (#34)

* 생성 직후 점검 전의 defects.md 읽기와 후처리 사용 시 postprocess.md 읽기로 참조 문서 읽기 시점 변경 (#26)
* 예시 목록을 붙인 결함 유형 항목, 취약 부위별 단독 확대 확인, 확대 파일을 적는 이미지별 한 줄 기록을 담은 눈 점검 방식 변경 (#26, #30)
* 1배 이외 후보 생성 답의 경우에만 읽는 references/candidates.md로 후보 모드 절차 분리 변경 (#27)
* 부위별 숫자 기록, 드러난 손발의 정확한 다섯 개 묘사 목표, 닿은 손(바닥, 몸, 옷, 머리카락 등)의 결함 주의, 신체 개수 기준(사람의 한 손 손가락 5개, 한 발 발가락 5개, 팔 2개, 다리 2개, 네발 동물의 다리 4개 등)을 담은 눈 점검 항목 추가 (#28, #30, #31)
* 눈코입 배치 기준을 포함한 얼굴 결함 눈 점검 항목 추가 (#28)
* 큰 부위의 신체 왜곡(다른 신체 부위와의 섞임 포함, 자세로 설명되는 비틀림 제외), 기계 구조의 왜곡, 건물 형태의 왜곡에 대한 눈 점검 예시 추가 (#28, #29, #30)
* 보이는 원인으로 설명되지 않는 차이와 애매한 경우를 사물과 건물까지 모든 피사체의 결함으로 보는 단일 형태 판정 원칙과 앞을 덮은 물체만 인정하는 가림 기준(의도하지 않은 어둠, 흐림, 아웃포커스 제외)으로 변경 (#28, #30)
* 약한 흐림 예외와 원경 인물 개수 생략 예외의 적용 대상을 배경 인물로 변경 (#30)
* 미사용(기본값), 최적화(피사체와 장면 유지 상태의 결함 부분 제거, 가림, 프레임아웃), 최대 우회(메시지만 유지, 확인 후 피사체 교체 가능) 선택지와 preflight.py 필수 답(--upfront-workaround) 기록을 담은 첫 프롬프트 우회 질의 항목 추가 (#32)
* 목록 밖의 확산모델 전형 결함, 시각적으로 어색한 부분, 요청한 연출의 미반영을 결함으로 보는 눈 점검 항목 추가 (#32)
* 모델이 모를 수 있는 고유명사, 전문용어, 드문 단어에 대한 흔한 사물 대체, 단순한 구성요소(모양, 재질, 색 2-3개) 묘사, 전달 시 원래 단어 알림을 담은 프롬프트 규칙 추가 (#32)
* 다른 비확산 이미지 생성 스킬과 같은 기준으로 콘텐츠 정책 변경 (#33)
* 단순한 정적 자세 우선, 그리기 어려운 연출 회피, 결함이 남아도 트림하기 쉬운 손 위치를 담은 우회 자세 기준 추가 (#34)

### image-gen-addon-codeformer
- Changed the CodeFormer license consent to one line in the pre-generation questions instead of a question right before the first installation (#34)
- Added a "Do not use" choice to the face restoration strength item for users who decline the license or have a commercial purpose (#34)
- Fixed the question numbering example and the recommended combination for delegated answers that left out image-gen's upfront workaround item (#34)
- Fixed the stepwise strength lowering that could run with defect post-processing set to workarounds only (#34)
- Fixed the always-on scope to choose w from the face in the generated original (#34)
- Fixed the non-photographic style rule that left out image-gen's handling for environments that cannot show images (#34)

* 생성 전 질의의 한 줄 안내로 CodeFormer 라이선스 동의 시점 변경 (#34)
* 라이선스 미동의 사용자와 상업 목적 사용자를 위한 얼굴 복원 강도 항목의 사용 안 함 선택지 추가 (#34)
* image-gen 첫 프롬프트 우회 항목이 누락된 질의 번호 예시와 위임 권장 조합 수정 (#34)
* 결함 후처리가 우회만 자동인 경우에도 진행될 수 있던 단계 강도 낮추기 수정 (#34)
* 생성 원본 얼굴 기준의 상시 적용 w 결정 방식 수정 (#34)
* 이미지 표시 수단이 없는 환경의 image-gen 처리를 누락한 비사진 화풍 규칙 수정 (#34)

## 2026-10-31

### image-gen
- Added candidate generation that makes more candidates than the target count at once and adopts from them (#24)
- Added a user pick that chooses candidates by number from a numbered contact sheet (#24)
- Added a question about deleting the spare candidates that were not picked (#24)
- Changed the pre-generation questions to leave out choices that need a preview where images cannot be shown to the user (#24)
- Changed the limits of the automatic candidate multiplier (a 3x cap and a total under 10 images) into recommended criteria (#25)

* 목표 장수보다 많은 후보를 한 번에 만들어 고르는 후보 생성 기능 추가 (#24)
* 번호를 붙인 모아보기에서 후보를 고르는 사용자 선택 추가 (#24)
* 고르지 않은 여분 후보의 삭제 여부 질의 추가 (#24)
* 이미지 표시 수단이 없는 환경의 미리보기 선택지 제외를 위한 생성 전 질의 변경 (#24)
* 후보 배수 자동 판단의 한도(3배 상한, 총 10장 미만)를 권장 기준으로 변경 (#25)

### image-gen-addon-codeformer
- Changed the question numbering example to include the new candidate items of image-gen (#24)

* image-gen 후보 항목을 반영한 질의 번호 예시 변경 (#24)

## 2026-10-27

### geometric-illustration
- Fixed the Korean spec-reference.md table that ended before the line.weight row on GitHub (#22)

* GitHub 화면에서 line.weight 행이 표 밖으로 밀려나던 한국어판 spec-reference.md 표 오류 수정 (#22)

### pastel-picturebook
- Fixed the side placeholders in lift part names that GitHub hid in pipeline.md and subjects.md (#22)

* GitHub 화면에서 lift 부위 이름의 side 자리 표시자가 사라지던 pipeline.md, subjects.md 표기 오류 수정 (#22)

### soft-diorama
- Fixed the tree row of the api.md table that lost its description column on GitHub (#22)

* GitHub 화면에서 api.md 표 tree 행의 설명 열이 사라지던 오류 수정 (#22)

### vinyl-cel
- Fixed the yaw row of the English api.md table that lost the text after the absolute value bars on GitHub (#22)

* GitHub 화면에서 영어판 api.md 표 yaw 행의 설명 일부가 사라지던 오류 수정 (#22)

## 2026-10-18

### image-gen
- Added a step that attaches the GitHub repositories before downloading weights (#16)
- Fixed face restoration installs that stopped when basicsr failed to build on newer Python (#18, #19)

* 가중치 다운로드 전 GitHub 저장소 연결 단계 추가 (#16)
* 최신 Python 환경의 basicsr 빌드 실패로 얼굴 복원 설치가 중단되는 오류 수정 (#18, #19)

### image-gen-addon-codeformer
- Added a step that attaches the GitHub repositories before downloading weights (#16)
- Fixed the face helper downloading the detection and parsing weights again into the package folder (#18)

* 가중치 다운로드 전 GitHub 저장소 연결 단계 추가 (#16)
* 얼굴 보조 모듈이 검출 및 파싱 가중치를 패키지 폴더에 중복 다운로드하는 오류 수정 (#18)

## 2026-10-17

### Common
- Added SHA256SUMS.txt files with the checksums of the install packages to each skill folder (#14)
- Added a README note on building a dependency skill with offline-deps-builder where network access is blocked (#15)

* 스킬 폴더별 설치용 패키지의 체크섬을 담은 SHA256SUMS.txt 파일 추가 (#14)
* 네트워크 차단 환경에서 offline-deps-builder로 의존성 스킬을 생성하는 README 안내 추가 (#15)

## 2026-10-14

### cel-glow-atelier
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### clay-cel-canvas
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### geometric-illustration
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### maquette-painter
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### paper-stage
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### polygon-cel
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### soft-diorama
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### tableau-vivant
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

### vinyl-cel
- Changed the English edition skill name to the Korean edition name (#11)

* 영어판 스킬 이름을 한국어판 스킬 이름과 동일하게 변경 (#11)

## 2026-10-13

### Common
- Added the first public release with the Korean and English editions of the skills

* 한국어판 및 영어판 스킬을 담은 최초 공개 버전 추가
