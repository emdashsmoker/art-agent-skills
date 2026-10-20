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
- (Skill tag) Use the folder name under skills/. Join two names with "and" in English and "및" in Korean. Separate three or more names with commas. Use (common) in English and (공통) in Korean for repository-wide changes.
- (Entry order) Put repository-wide entries first and sort the rest by skill folder name.
- (English entries) List the English entries first under each date with the "-" bullet.
- (Korean entries) Leave one blank line after the English entries and list the same changes in the same order with the "*" bullet so that they render as a separate list.
- (English format) - (skill tag) Description that starts with the change type verb (#PR number)
- (Korean format) * (skill tag) Korean noun-ending description that ends with the change type word (#PR number)
- (Change types) Added (추가), Changed (변경), Fixed (수정), Removed (삭제), Action needed (필요)
- (Include) Changes to skill outputs, usage steps, or installation.
- (Exclude) Typo and wording fixes, demo image replacements, README changes unrelated to installation, internal refactoring without behavior changes, and commits that only change CHANGELOG.md.
- (Push) Commit on top of the latest main and push directly to main.
-->

## 2026-10-18
- (image-gen) Fixed face restoration installs that stopped when basicsr failed to build on newer Python (#18, #19)
- (image-gen and image-gen-addon-codeformer) Added a step that attaches the GitHub repositories before downloading weights (#16)
- (image-gen-addon-codeformer) Fixed the face helper downloading the detection and parsing weights again into the package folder (#18)

* (image-gen) 최신 Python 환경의 basicsr 빌드 실패로 얼굴 복원 설치가 중단되는 오류 수정 (#18, #19)
* (image-gen 및 image-gen-addon-codeformer) 가중치 다운로드 전 GitHub 저장소 연결 단계 추가 (#16)
* (image-gen-addon-codeformer) 얼굴 보조 모듈이 검출 및 파싱 가중치를 패키지 폴더에 다시 내려받는 오류 수정 (#18)

## 2026-10-17
- (common) Added SHA256SUMS.txt files with the checksums of the install packages to each skill folder (#14)
- (common) Added a README note on building a dependency skill with offline-deps-builder where network access is blocked (#15)

* (공통) 스킬 폴더별 설치용 패키지의 체크섬을 담은 SHA256SUMS.txt 파일 추가 (#14)
* (공통) 네트워크 접근이 차단된 환경에서 offline-deps-builder로 의존성 스킬을 만드는 README 안내 추가 (#15)

## 2026-10-14
- (cel-glow-atelier, clay-cel-canvas, geometric-illustration, maquette-painter, paper-stage, polygon-cel, soft-diorama, tableau-vivant, vinyl-cel) Changed the English edition skill names to the Korean edition names (#11)

* (cel-glow-atelier, clay-cel-canvas, geometric-illustration, maquette-painter, paper-stage, polygon-cel, soft-diorama, tableau-vivant, vinyl-cel) 영어판 스킬 이름을 한국어판 스킬 이름과 같게 변경 (#11)

## 2026-10-13
- (common) Added the first public release with the Korean and English editions of cel-glow-atelier, clay-cel-canvas, dollhouse-maker, flat-painterly, geometric-illustration, image-gen, image-gen-addon-codeformer, maquette-painter, paper-stage, pastel-picturebook, polygon-cel, soft-diorama, tableau-vivant and vinyl-cel

* (공통) cel-glow-atelier, clay-cel-canvas, dollhouse-maker, flat-painterly, geometric-illustration, image-gen, image-gen-addon-codeformer, maquette-painter, paper-stage, pastel-picturebook, polygon-cel, soft-diorama, tableau-vivant, vinyl-cel 스킬의 한국어판 및 영어판을 담은 최초 공개 버전 추가
