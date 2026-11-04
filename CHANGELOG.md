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

## 2026-11-04

### image-gen-lite
- Added the image-gen-lite skill in Korean and English editions, a lite edition of image-gen that generates with the same local CPU presets and delivers the model's output as is, without edge trimming, face restoration, region redrawing, or upscaling (#46)
- Changed the composition so that it is no longer asked and is decided in order from a stated composition, a described setting or time of day (scene), and the intended use, falling back to an icon as image-gen does (#48)
- Changed the style so that it is no longer asked when unspecified, and the questions instead report one recommended style in one line, chosen for the request and the model, with digital painting as the fallback and another style accepted in the answer (#48)
- Added an automatic choice to the candidate multiplier item that picks 1x to 3x from defect-prone subjects, uses 1x with the precise preset, and is reported with a one-line reason before generation (#48)
- Added an automatic choice to the regeneration limit item that picks 0 to 3 from defect-prone subjects and a large use or a quality-first request, uses 1 or less with the precise preset and 0 when speed comes first, never picks unlimited, and is reported with a one-line reason before generation (#48)
- Changed the choice letters of the candidate multiplier item to automatic d) and custom e), and of the regeneration limit item to automatic d), custom e), and unlimited f), in the same order as image-gen (#48)

* image-gen과 같은 로컬 CPU 프리셋의 생성 결과를 가장자리 정리, 얼굴 복원, 부분 다시 그리기, 업스케일 없이 그대로 전달하는 경량판 image-gen-lite 스킬의 한국어판 및 영어판 추가 (#46)
* 질의 생략, 지정 구도, 직접 묘사한 배경이나 시간대(장면형), 사용처 순서의 판단, image-gen과 같은 도상형 기본값을 담은 구도 결정 방식 변경 (#48)
* 화풍 미지정 시 질의 생략, 요청과 모델에 맞춘 추천 화풍의 한 줄 안내, 디지털 페인팅 기본값, 답변 내 다른 화풍 지정을 담은 화풍 결정 방식 변경 (#48)
* 결함이 잦은 피사체 기준의 1-3배 결정, 정밀 프리셋의 1배 고정, 생성 전 근거 안내를 담은 후보 배수 자동 선택지 추가 (#48)
* 결함이 잦은 피사체, 큰 사용처나 품질 우선 요청 기준의 0-3회 결정, 정밀 프리셋의 1회 이하 제한, 속도 우선 시 0회, 무제한 제외, 생성 전 근거 안내를 담은 재생성 상한 자동 선택지 추가 (#48)
* image-gen과 같은 순서에 따른 후보 배수 선택지 기호(자동 d, 직접 입력 e)와 재생성 상한 선택지 기호(자동 d, 직접 입력 e, 무제한 f) 변경 (#48)

## 2026-11-03

### image-gen
- Added an automatic choice to the regeneration limit multiplier item that picks 1x to 3x from defect-prone subjects, a large use or a quality-first request, the estimated time per image, and any stated time limit, never picks unlimited, and is reported with a one-line reason before generation (#43)
- Changed the choice letters of the regeneration limit multiplier item to automatic d), custom e), and unlimited f), in the same order as candidate generation (#43)
- Added the preflight.py --regen-scale auto answer, which requires the decided whole-number multiplier in --regen-scale-resolved and a one-line reason in --regen-scale-reason (#43)
- Fixed the regeneration count, which runs read in different ways, so that prompt edits and seed changes for general defects always count separately from the stage limits, with one more generation for message, diagram, and unsubstituted scene requests that change the stand-in or element combination (#44)
- Fixed the pre-generation regeneration notice, which counted only the stage limits, to state the maximum regenerations for shape defects and for other defects separately with the maximum added time of using both, marked as an upper bound that is usually shorter and excluding checks and post-processing (#44)
- Fixed the automatic regeneration limit multiplier, which left general defect regenerations out of its maximum added time, so that a work time limit the user states now holds (#44)
- Fixed the pre-generation regeneration notice, which called the maximum added time an upper bound that is usually shorter, to say that the actual time may be shorter or longer because the time per image is estimated before generation (#45)

* 결함이 잦은 피사체, 큰 사용처나 품질 우선 요청, 장당 예상 시간, 작업 시간 한도 기준의 1-3배 결정, 무제한 제외, 생성 전 근거 안내를 담은 재생성 상한 배수 자동 선택지 추가 (#43)
* 후보 생성과 같은 순서에 따른 재생성 상한 배수 선택지 기호(자동 d, 직접 입력 e, 무제한 f) 변경 (#43)
* 결정 배수(--regen-scale-resolved)와 근거 한 줄(--regen-scale-reason)을 필수로 받는 preflight.py --regen-scale auto 답 추가 (#43)
* 단계 상한과 분리한 일반 결함의 프롬프트 수정과 seed 변경 횟수, 메시지 요청, 도해 요청, 치환 없는 장면형 요청의 1회 추가 생성을 담은 재생성 횟수 기준 수정 (#44)
* 형태 결함과 그 밖의 결함의 최대 재생성 횟수, 두 횟수를 모두 쓸 때의 최대 추가 시간, 상한 표기, 점검과 후처리 시간 제외 안내를 담은 생성 전 재생성 안내 수정 (#44)
* 일반 결함 재생성 시간을 포함한 재생성 상한 배수 자동 판단의 최대 추가 시간 계산 수정 (#44)
* 최대 추가 시간보다 짧거나 길 수 있는 실제 시간을 반영한 생성 전 재생성 안내의 시간 표기 수정 (#45)

## 2026-11-02

### image-gen
- Added a post-upscaling recheck that saves the 4x result with the new finalize.py --x4-out option and, before delivery, applies every visual check item again to that result, sending defects that existed before upscaling through the existing defect handling on the pre-upscaling image (#38)
- Removed the check of the final upscaling result for a waxy look, exaggerated nostril and lip edges, clumped hair, and lost texture, along with the question that asked the user to choose between that result and a plain enlargement (#38)
- Added a rule to the post-upscaling recheck that redoes the original-versus-restored comparison of a restored three-quarter view or profile face with the newly found defect counted, checks the side that was not adopted on a grid_measure.py enlargement, and reruns finalize.py and the recheck when the adopted image changes (#39)
- Added a required regeneration limit multiplier item to the pre-generation questions, placed before model choice with 1x (default), 2x, 3x, custom, and unlimited, which multiplies each stage limit, subtracts candidate pool swaps from the stage 1 limit, and is recorded by preflight.py as a required --regen-scale answer (#41)
- Added a choice at the regeneration limit to continue with a higher multiplier or unlimited, counting on from the attempts already used (#41)
- Added an unlimited option that follows the 3x path and then, without asking, keeps regenerating with the best result's prompt and a new seed until success, a user stop, or a runtime environment limit, with periodic one-line progress reports and an attempts.jsonl record in the output folder (#41)
- Added one definition of the best result, the attempt with the fewest remaining defect parts after trimming and stage 3 post-processing and, on a tie, the one closest to the original request, used wherever the best result is presented (#41)
- Changed the Korean documents, including the pre-generation question texts shown to users, to a formal style without colloquial wording or placeholder nouns (#42)

* finalize.py --x4-out의 4배 결과물 저장, 전달 전 눈 점검 항목 전체의 재적용, 보정 전부터 있던 결함의 기존 결함 대응을 담은 화질 보정 후 재점검 추가 (#38)
* 화질 보정 결과의 밀랍 질감, 콧구멍과 입술 경계 과장, 머리카락 뭉침, 질감 손실 확인과 단순 확대 안 비교 질의 삭제 (#38)
* 복원한 비정면 얼굴의 4배 재점검 결함을 포함한 원본과 복원본 비교 재진행, 채택하지 않은 쪽의 grid_measure.py 확대 확인, 채택본 변경 시 finalize.py와 재점검의 재실행을 담은 재비교 규칙 추가 (#39)
* 모델 선택 앞 배치, 단계별 상한의 배수 적용, 1단계 상한의 후보 풀 교체 횟수 차감, preflight.py 필수 답(--regen-scale) 기록을 담은 재생성 상한 배수 질의 항목(1배 기본값, 2배, 3배, 직접 입력, 무제한) 추가 (#41)
* 사용 횟수를 이어서 세는 배수 상향과 무제한 전환의 재생성 상한 도달 선택지 추가 (#41)
* 3배 경로 이후 질의 없는 가장 나은 결과 프롬프트의 seed 반복, 성공, 사용자 중단, 실행 환경 한계 기준의 종료, 주기적 한 줄 진행 안내, 출력 폴더의 attempts.jsonl 기록을 담은 무제한 운영 규칙 추가 (#41)
* 트림과 3단계 후처리 후 남은 결함 부위 수, 동수 시 원 요청과의 근접도를 기준으로 삼은 가장 나은 결과 단일 정의 추가 (#41)
* 구어 표현과 빈자리 명사 없는 격식체로 한국어판 생성 전 질의 문안과 문서 문체 변경 (#42)

### image-gen-addon-codeformer
- Added a rule that a retry with a lower w does not restore an image that was already restored, so that the recorded w reproduces the result (#39)
- Changed the recommended combination and the record script example to include the regeneration limit multiplier as item 11, with model choice moving to item 12 (#41)

* 기록한 w의 결과 재현을 위해 w를 낮춘 재복원에서 이미 복원한 이미지를 입력으로 쓰지 않는 규칙 추가 (#39)
* 재생성 상한 배수의 11번 배치와 모델 선택의 12번 이동을 반영한 권장 조합과 기록 스크립트 예시 변경 (#41)

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
- Fixed the pre-generation question texts that differed from the defect handling order, now with trimming and seed changes ahead of workarounds, lowered hands first in the optimize example, and the use of the image kept under maximum (#35)
- Changed the Korean and English documents, including the pre-generation question texts shown to users, to a formal style without colloquial wording (#36)
- Changed the English choice labels Candidate pick, Agent pick, User pick, and Free ratio too to Candidate selection, Agent selection, User selection, and Free ratio allowed (#36)
- Added a non-frontal face rule that, after each restoration of a three-quarter view or profile face, adopts whichever of the original and the restored image has fewer defects without asking, keeps the restored image on a tie, records the result, and adds a one-line notice to the face restoration scope question (#37)

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
* 우회보다 앞선 트림과 seed 변경, 최적화 예시의 내린 손 우선, 최대 우회의 쓰일 자리 유지를 담은 생성 전 질의 문구 수정 (#35)
* 구어 표현 없는 격식체로 생성 전 질의 문안과 문서 문체(한국어판, 영어판) 변경 (#36)
* Candidate selection, Agent selection, User selection, Free ratio allowed로 영어판 선택지 이름(Candidate pick, Agent pick, User pick, Free ratio too) 변경 (#36)
* 3/4 측면과 옆모습 얼굴의 복원마다 원본과 복원본 중 결함이 적은 쪽의 질의 없는 채택, 동점 시 복원본 유지, 비교 결과 기록, 얼굴 복원 범위 질의의 안내 한 줄을 담은 비정면 얼굴 규칙 추가 (#37)

### image-gen-addon-codeformer
- Changed the CodeFormer license consent to one line in the pre-generation questions instead of a question right before the first installation (#34)
- Added a "Do not use" choice to the face restoration strength item for users who decline the license or have a commercial purpose (#34)
- Fixed the question numbering example and the recommended combination for delegated answers that left out image-gen's upfront workaround item (#34)
- Fixed the stepwise strength lowering that could run with defect post-processing set to workarounds only (#34)
- Fixed the always-on scope to choose w from the face in the generated original (#34)
- Fixed the non-photographic style rule that left out image-gen's handling for environments that cannot show images (#34)
- Changed the Korean and English documents, including the face restoration strength question text, to a formal style without colloquial wording (#36)
- Changed the strength for non-frontal faces to stay at w=0.5 even with the aggressive strength, with a remaining defect moving to image-gen's next response stages instead of a lower w, and noted it in the face restoration strength question (#37)
- Added image-gen's non-frontal face comparison to CodeFormer restoration (#37)
- Changed the correction scope to exclude the natural asymmetry of a face angle, such as the far eye looking narrower (#37)

* 생성 전 질의의 한 줄 안내로 CodeFormer 라이선스 동의 시점 변경 (#34)
* 라이선스 미동의 사용자와 상업 목적 사용자를 위한 얼굴 복원 강도 항목의 사용 안 함 선택지 추가 (#34)
* image-gen 첫 프롬프트 우회 항목이 누락된 질의 번호 예시와 위임 권장 조합 수정 (#34)
* 결함 후처리가 우회만 자동인 경우에도 진행될 수 있던 단계 강도 낮추기 수정 (#34)
* 생성 원본 얼굴 기준의 상시 적용 w 결정 방식 수정 (#34)
* 이미지 표시 수단이 없는 환경의 image-gen 처리를 누락한 비사진 화풍 규칙 수정 (#34)
* 구어 표현 없는 격식체로 얼굴 복원 강도 질의 문안과 문서 문체(한국어판, 영어판) 변경 (#36)
* 적극 강도의 w=0.5 유지, 남은 결함의 image-gen 다음 대응 단계 진행, 얼굴 복원 강도 질의의 안내 문장을 담은 비정면 얼굴 강도 기준 변경 (#37)
* CodeFormer 복원에 대한 image-gen 비정면 얼굴 비교 규칙 적용 추가 (#37)
* 얼굴 각도로 생기는 자연스러운 비대칭(먼 쪽 눈이 좁아 보이는 현상 등)의 제외를 담은 보정 범위 변경 (#37)

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
