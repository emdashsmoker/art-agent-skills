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
- (Korean style) Write each Korean entry as one short formal sentence in note style with a noun ending. Avoid colloquial expressions.
- (Change types) Added (추가), Changed (변경), Fixed (수정), Removed (삭제), Action needed (필요)
- (Include) Changes to skill outputs, usage steps, or installation.
- (Exclude) Typo and wording fixes, demo image replacements, README changes unrelated to installation, internal refactoring without behavior changes, and commits that only change CHANGELOG.md.
- (Push) Commit on top of the latest main and push directly to main.
-->

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
* 네트워크 접근이 차단된 환경에서 offline-deps-builder로 의존성 스킬을 생성하는 README 안내 추가 (#15)

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
