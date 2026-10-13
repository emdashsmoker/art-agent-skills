# 서드 파티 고지

## dollhouse-maker 라이선스

- dollhouse-maker는 GNU General Public License v3.0 or later(GPL-3.0-or-later)로 배포함
- 라이선스 전문은 최상위 LICENSE 파일에 있음
- 저작권 표시와 생성 이미지에 대한 추가 허가는 최상위 NOTICE.md 파일에 있음
- 이 저장소에는 직접 작성한 소스 코드와 문서만 들어 있음. 서드 파티 코드, 바이너리, 글꼴, 이미지는 동봉하거나 재배포하지 않음

## 의존 패키지

- 아래 패키지는 사용자가 `scripts/requirements.txt`를 통해 별도로 설치함. 각 패키지에는 해당 패키지의 라이선스가 그대로 적용됨
- 아래 라이선스는 모두 GPL-3.0과 호환됨

| 패키지 | 요구 버전 | 라이선스 | 배포 휠에 포함된 구성요소 | 프로젝트 |
|---|---|---|---|---|
| NumPy | >=1.24 | BSD-3-Clause | 0BSD, MIT, Zlib, CC0-1.0 라이선스의 소스 구성요소, OpenBLAS와 LAPACK(BSD 계열), GCC runtime library(GPL-3.0-or-later WITH GCC-exception-3.1), libquadmath(LGPL-2.1-or-later) | https://numpy.org |
| SciPy | >=1.10 | BSD-3-Clause | OpenBLAS와 LAPACK(BSD 계열), GCC runtime library(GPL-3.0-or-later WITH GCC-exception-3.1), libquadmath(LGPL-2.1-or-later) | https://scipy.org |
| opencv-python-headless | >=4.8 | OpenCV 본체는 Apache-2.0, 패키징 스크립트는 MIT | FFmpeg 바이너리(LGPL-2.1) | https://opencv.org, https://github.com/opencv/opencv-python |

## 라이선스 원문 확인 방법

- 각 패키지는 설치 폴더의 `*.dist-info` 디렉터리에 라이선스 원문을 포함함
- `pip show -f numpy scipy opencv-python-headless` 명령으로 해당 파일 위치를 확인 가능
- 이 고지는 2026년 10월 기준 numpy 2.5.3, scipy 1.18.1, opencv-python-headless 5.0.0.93의 설치 메타데이터를 근거로 작성함
