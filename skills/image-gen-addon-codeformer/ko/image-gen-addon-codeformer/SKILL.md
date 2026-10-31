---
name: image-gen-addon-codeformer
description: "image-gen 스킬의 얼굴 복원에 CodeFormer를 더하는 애드온. 설치되어 있으면 image-gen의 생성 전 질의에 얼굴 복원 강도 항목을 넣고, 비대칭이나 이목구비 위치가 어긋난 얼굴을 CodeFormer로 고치도록 image-gen의 얼굴 복원 절차를 바꾼다. image-gen 스킬로 인물이 나오는 이미지를 만들거나 얼굴 보정, 얼굴 복원, 얼굴 뒤틀림 수정을 할 때 이 애드온이 설치되어 있으면 image-gen과 함께 반드시 로드할 것. image-gen 스킬이 없으면 동작하지 않는다. CodeFormer는 비상업 용도로만 쓸 수 있는 라이선스(S-Lab License 1.0)로 배포되므로 설치 전에 사용자 동의를 받는다."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE.md
---

# image-gen 애드온: CodeFormer 얼굴 복원

이 애드온은 image-gen 스킬의 얼굴 복원을 확장한다. image-gen은 GFPGAN으로 흐린 얼굴을 선명하게 하지만, 눈의 위치가 어긋나거나 좌우가 비대칭인 얼굴은 원본을 따라가 결함이 일부 남는다. CodeFormer는 학습해 둔 얼굴 부품 사전(codebook)으로 얼굴을 다시 구성하므로 비대칭과 이목구비 위치 왜곡도 고친다. 충실도 가중치 w가 낮을수록 대칭 복원이 강해지고, 높을수록 원본 인상을 지킨다.

아래 규칙은 image-gen과 함께 로드되었을 때 image-gen의 해당 규칙을 바꾼다. 바꾸지 않은 규칙은 image-gen을 그대로 따른다.

## 사용 조건

CodeFormer는 S-Lab License 1.0으로 배포된다. 이 라이선스는 비상업 목적의 사용과 재배포만 허용하고, 상업 목적이면 저작자와 따로 협의하라고 적고 있다. 처음 설치하기 전에 사용자에게 이 조건을 한 줄로 알리고 설치해도 되는지 묻는다. 사용자가 동의하지 않거나 상업 목적이라고 답하면 이 애드온을 쓰지 않고 image-gen만으로 진행한다.

- 원문: https://github.com/sczhou/CodeFormer/blob/master/LICENSE
- 패키지: codeformer-pip(https://github.com/kadirnar/codeformer-pip), 같은 라이선스를 표기한다.

## 바뀌는 규칙

### 생성 전 질의

image-gen의 얼굴 복원 범위 항목 바로 뒤에 얼굴 복원 강도 항목을 넣는다. 뒤 항목의 번호는 하나씩 밀린다. 다른 항목의 조건 안내에 적힌 뒤 항목 번호도 밀린 번호로 적는다(예: 후보 선택의 "6번이 a가 아닐 때만"은 "7번이 a가 아닐 때만").

- 묻는 조건: 인물이 나오고, 얼굴 복원이 실제로 돌 수 있는 조합이다. 얼굴 복원 범위가 미사용이면 묻지 않는다. 얼굴 복원 범위가 결함 시에만이고 결함 후처리가 우회만 자동이면 복원이 돌지 않으므로 묻지 않는다.
- 사용자가 강도를 직접 말했으면 묻지 않는다.
- 위임 발화의 권장 조합에서 이 항목의 권장은 단계다.

질의 예시(image-gen 예시의 4번 뒤에 넣는다):

> 5. [얼굴 복원 강도] 4번이 c가 아니고, 3번 b와 4번 a를 함께 고르지 않은 경우에만 해당합니다.
>    a) 적극: 처음부터 w=0.0으로 한 번에 고칩니다. 얼굴 인상이 원본과 달라질 수 있습니다
>    b) 단계: w=0.5로 시작하고 결함이 남으면 0.25, 0.0 순으로 낮춥니다

답을 받으면 image-gen의 preflight.py를 실행한 직후 이 애드온의 기록 스크립트를 실행한다. image-gen의 기록을 다시 쓸 때마다 이 기록도 다시 실행한다.

```
PY scripts/preflight_codeformer.py --out ./outputs --face-strength stepwise --user-reply "1-b, 2-c, 3-a, 4-b, 5-b, 6-a, 7-d, 8-b, 9-c"
```

- `scripts/`는 이 애드온 폴더 안의 scripts 폴더 경로다. `PY`는 image-gen의 가상환경 파이썬이다.
- 강도 항목이 필요 없는 조합이면 `--face-strength` 없이 실행해 빈 값을 기록한다.

### 얼굴 도구 선택

| 얼굴 결함 | image-gen 단독 | 애드온 설치 후 |
|---|---|---|
| 흐림(눈동자, 속눈썹, 치아) | GFPGAN | GFPGAN |
| 뒤틀림(비대칭, 이목구비 위치 왜곡) | GFPGAN, 남으면 부위 다시 그리기 | CodeFormer(강도는 얼굴 복원 강도 답을 따름), 남으면 부위 다시 그리기 |
| 상시 적용 | GFPGAN | CodeFormer. 결함이 안 보이면 w=0.5, 결함이 보이면 얼굴 복원 강도의 시작값 |

- 단계 방침은 w=0.5에서 시작해 결함이 남으면 0.25, 0.0 순으로 낮춘다. w를 낮출수록 원본 인상이 바뀌지만 결함 해소가 우선이므로 결함이 남은 채 두지 않는다.
- w=0.0은 인상이 다른 사람처럼 바뀔 수 있다. 같은 인물이 여러 장에 나오면 비교해 확인한다.
- 비사진 화풍에서 복원 얼굴이 사진처럼 바뀌는 문제는 CodeFormer도 같다. image-gen의 규칙대로 전후를 나란히 보여 주고 채택 여부를 묻는다.
- 얼굴이 심하게 무너진 그림은 CodeFormer가 얼굴을 다시 구성하지 못하고 질감만 바꾸는 일이 있다. w=0.0까지 내려도 남으면 image-gen의 부위 다시 그리기로 넘어간다.
- 얼굴 이외의 영역과 손은 원본 그대로 둔다. 손 결함은 고치지 못한다.

```
PY scripts/face_fix_codeformer.py in.png out_face.png 0.5
```

- 짧은 변이 512px보다 작은 입력은 패키지 안에서 커진 채 저장되므로, 스크립트가 복원 뒤 입력 크기로 되돌린다. 트림 작업본의 크기와 눈금 좌표가 복원 전후로 유지된다.
- 채택 기록에 얼굴 복원 강도 방침과 사용한 w를 더한다.
- 종료 코드는 image-gen의 실패 대응 표를 따른다. 인자 오류와 입력 파일 누락은 2, codeformer-pip 미설치는 4다.

### 설치

얼굴 복원을 쓰기로 한 경우, 사용 조건에 동의를 받은 뒤 image-gen의 얼굴 복원 설치에 이어서 설치한다.

```
PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu codeformer-pip
PY <image-gen 폴더>/scripts/patch_basicsr.py
```

- CPU 인덱스를 함께 주는 이유는 image-gen의 얼굴 복원 설치와 같다.
- image-gen의 얼굴 복원을 설치할 수 없으면 이 애드온도 건너뛴다.
- codeformer-pip은 import할 때 현재 폴더 아래에 가중치(약 0.6GB)를 받고 결과를 `output/out.png`에 쓴다. 얼굴 보조 모듈은 검출 가중치와 분석 가중치를 패키지 설치 폴더에 한 번 더 받으려 한다. face_fix_codeformer.py는 image-gen 캐시 폴더 안의 `codeformer` 폴더로 옮겨 가고, import 전에 얼굴 보조 모듈의 기준 폴더도 같은 곳으로 지정한다. 가중치는 이 폴더 한 곳에만 저장된다. 사용자 폴더, 스킬 폴더, 가상환경에는 파일이 생기지 않는다.
- 가중치는 GitHub `sczhou/CodeFormer` 저장소의 릴리스에서 받는다. 세션에 GitHub 저장소를 연결하는 도구가 실행 환경에 있으면 첫 실행 전에 호출한다. 인자는 소유자 `sczhou`, 저장소 이름 `CodeFormer`를 각각 따로 전달한다. 도구 응답이 안내하는 접근 경로를 따른다. 도구가 없거나 호출이 거부되면 이 단계를 건너뛴다.

### 정리

```
PY scripts/face_fix_codeformer.py --cleanup
PY -m pip uninstall codeformer-pip
```

- `--cleanup`은 image-gen 캐시 폴더 안의 `codeformer` 폴더만 지운다. image-gen의 `cache.py delete all`도 이 폴더를 지운다.
