# 후처리: 얼굴 복원, 부위 다시 그리기

형태가 무너지기 쉬운 피사체의 대응 3단계와 얼굴 복원 상시 적용에서 읽는 문서다. 후처리는 결함 부위만 다시 그리고 나머지 영역은 원본 그대로 둔다. 원래 의도를 지키는 대신 설치 용량과 시간이 든다.

## 도구

| 결함 | 도구 | 스크립트 | 추가 내려받기 |
|---|---|---|---|
| 얼굴 흐림(눈동자, 속눈썹, 치아) | GFPGAN v1.3 | face_fix.py | 패키지 약 0.6GB, 가중치 약 0.6GB |
| 얼굴 뒤틀림(비대칭, 이목구비 위치 왜곡) | GFPGAN v1.3, 남으면 부위 다시 그리기 | face_fix.py, region_fix.py | 위와 같음, 부위 다시 그리기 모델 |
| 옷과 착용물의 작은 결함, 정밀 사물 | SD 1.5 인페인팅 | region_fix.py | 모델 약 2.3GB |
| 손가락 개수와 모양(사용을 고른 경우, 따로 드러난 손) | SD 1.5 인페인팅 강도 0.85 | region_fix.py | 위와 같음 |

아래 결함은 후처리의 기본 대상에서 뺀다.

- 손가락 결함: 다시 그리기의 실제 효과가 낮다. 가장자리 트림과 대응 2단계 우회를 다 쓴 뒤, 생성 전 질의에서 사용을 고른 경우에만 한 번 적용한다.
- 동물 얼굴과 배경 군중: 복원 효과가 확인되지 않았다. 대응 1, 2, 4단계로 대응한다.
- 팔다리 개수와 상체, 하체의 연결 붕괴: 부위를 다시 그려도 자세를 새로 짤 수 없다. 대응 1단계와 4단계로 대응한다.

## 결함 후처리 방침

인물이나 정밀 사물이 나오는 요청은 첫 생성 전에 방침을 한 번 묻는다. 답은 같은 대화의 다음 생성에도 그대로 쓰고, 사용자가 바꾸면 그다음 결함부터 새 값을 쓴다.

- 후처리 자동(`auto`): 대응 2단계를 다 쓰면 묻지 않고 3단계에 들어가 결함이 풀린 결과를 채택한다. 의존성 설치 동의도 이 답에 포함된다.
- 우회만 자동(`bypass`): 3단계를 건너뛰므로 후처리 의존성을 설치하지 않는다. 가장자리 트림은 설치가 없으므로 트림 답이 허용이면 쓸 수 있다.
- 결함마다 질의(`ask`): 3단계에 들어갈 때마다 도구와 진입 여부를 묻는다.

## 얼굴 복원 범위

인물이 나오는 요청은 같은 질의에서 결함 시에만, 상시, 미사용 중 하나를 고른다. 이 항목은 결함 후처리 방침과 따로 움직인다. 512px 산출물은 결함으로 보이지 않는 얼굴도 눈동자와 치아가 흐리므로, 결함과 상관없이 복원을 원하는 경우가 있다.

- 결함 시에만(`defect`): 얼굴 결함이 보일 때만 결함 후처리 방침에 따라 3단계에서 적용한다.
- 상시(`always`): 인물이 나오는 모든 산출물에 생성 직후 얼굴 복원을 한 번 적용하고, 복원본으로 눈 점검을 한다. 재생성한 결과에도 똑같이 적용한다. 결함 후처리 방침이 우회만 자동이어도 얼굴 복원 의존성은 설치한다. 부위 다시 그리기는 우회만 자동이면 설치하지 않는다. 처리 순서는 생성, 얼굴 복원, 화질 보정이다.
- 미사용(`off`): 얼굴 복원 의존성을 설치하지 않는다. 얼굴 결함은 대응 1, 2, 4단계로 대응한다. 미사용은 얼굴 복원에만 해당하므로 옷, 착용물, 정밀 사물의 부위 다시 그리기는 결함 후처리 방침대로 한다.

비사진 화풍(플랫 벡터, 선화, 셀 채색 등)은 질의에서 미사용을 권장으로 표시한다. 얼굴 복원 도구는 실제 사진 얼굴로 학습되어 복원한 부위만 사진처럼 바뀌고 채색된 머리카락과 어긋난다. 이런 화풍에서 복원을 쓰기로 했다면 자동 모드와 상시 적용에서도 복원 전후를 나란히 보여 주고 채택 여부를 묻는다.

얼굴이 탐지되지 않은 산출물(뒷모습, 멀리 있는 인물)은 입력과 같은 화소로 저장되므로 그대로 정상 산출물로 쓴다.

## 얼굴 복원 사용법

GFPGAN v1.3은 눈동자와 속눈썹의 흐림을 선명하게 되살린다. 눈의 위치가 뒤틀린 얼굴은 원본을 따라가므로 비대칭이 일부 남는다. 얼굴 이외의 영역과 손은 원본 그대로 둔다.

```
PY scripts/face_fix.py in.png out_face.png
```

- 뒤틀림이 GFPGAN 뒤에도 남으면 부위 다시 그리기로 얼굴 상자를 다시 그린다. 이 경우도 한 번만 적용하고 전후를 비교한다.
- 가중치는 첫 사용 때 GitHub 릴리스에서 받고 SHA-256으로 확인한다. 보조 모델(얼굴 탐지, 얼굴 영역 분할)은 facexlib가 캐시 폴더 안에 받는다.

## 부위 다시 그리기

산출물 전체는 마음에 드는데 결함 한 곳만 남은 경우 그 부위만 다시 그린다. 대상 예는 끊긴 안경테, 사라진 끈, 요청하지 않은 성기나 여성 유두 노출, 엉킨 바큇살이다.

- 이어 그리기: 끊긴 테나 중간에 사라진 끈처럼 기존 형태를 잇는 보정은 강도 0.65를 쓴다. 0.85로 올리면 형태가 겹쳐 그려져 더 나빠진다.
- 덮어 그리기: 드러난 피부를 옷감으로 가리기, 짧은 소매 늘리기처럼 피부 위에 다른 재질을 올리는 보정은 강도 1.0을 쓴다. 강도가 낮으면 원본 색을 따라가 재질이 바뀌지 않는다.
- 얼굴 뒤틀림 보정은 강도 0.65에서 시작한다. 상자는 얼굴 윤곽에 맞춰 잡고 머리카락은 되도록 뺀다. 상자 안의 머리카락과 조명도 새로 그려지므로 원본과 색이 달라질 수 있다.
- 상자 좌표는 grid_measure.py의 눈금으로 잰다. 이어 그리기는 결함 부위만 좁게 잡는다. 덮어 그리기는 이어 붙일 옷감이 양옆에 보이도록 넓게 잡는다.
- 상자 안의 부속 요소(흙받이, 손에 쥔 물건)는 사라지므로 상자에 넣지 않는다.
- 프롬프트에는 결과 상태만 적는다. 예: `thin gold metal sunglasses frame, round lens rim continuing into a straight temple arm, photorealistic`. 지울 대상은 적지 않는다.
- 모델 입력은 이미지의 짧은 변 이내의 정사각형 영역이다. 가로로 긴 트림 작업본에서 상자가 그 영역보다 길면 region_fix.py가 `BOX_TOO_LARGE`로 멈춘다. 이때는 상자를 나눠 실행한다.

```
PY scripts/region_fix.py in.png out_region.png 387,173,460,267 "thin gold metal sunglasses frame, round lens rim continuing into a straight temple arm, photorealistic" 42           # 이어 그리기, 강도 기본값 0.65
PY scripts/region_fix.py in.png out_region.png 313,260,377,347 "white cotton t-shirt sleeve fabric covering the upper arm, soft fabric folds, photorealistic" 42 1.0      # 덮어 그리기
PY scripts/region_fix.py in.png out_region.png 117,167,227,267 "a natural open human hand with five fingers, palm facing the camera, photorealistic" 42 0.85          # 손가락, 사용을 고른 경우
```

## 손가락 다시 그리기

결함 후처리 방침이 후처리 자동이나 결함마다 질의인 인물 요청은 같은 질의에서 사용 여부를 고른다. 권장은 미사용이고, 효과가 낮다는 점을 선택지보다 먼저 알린다. 따로 펼친 손에서 손가락 개수는 고쳐졌지만 손의 크기와 자세가 원본과 달라진 사례가 있다.

- 사용을 골라도 대응 1단계 seed 변경, 가장자리 트림, 대응 2단계 우회를 먼저 다 쓴다. 그 뒤 3단계에서 한 번만 적용한다.
- 결함이 남으면 강도나 seed를 바꿔 반복하지 않고 대응 4단계 구도 우회로 간다.
- 손 크기와 자세가 바뀌는 폭이 크므로 후처리 자동에서도 전후를 나란히 보여 주고 채택 여부를 묻는다.
- 대상은 다른 사물과 겹치지 않고 따로 드러난 손이다. 물건을 쥔 손과 겹친 두 손은 상자 안의 물건이 사라지므로 사용을 골랐어도 뺀다.
- 강도는 0.85다. 0.65에서는 손가락 개수 결함이 그대로 남고, 1.0에서는 손 전체가 다른 자세로 바뀌어 팔과의 연결이 어긋난다.
- 상자는 손가락 끝에서 손목 바로 앞까지 잡는다. 프롬프트는 결과 상태를 적는다.

## 결과 확인과 기록

- 후처리 결과는 원본과 나란히 열어 결함이 풀렸는지, 경계의 질감이 어긋나지 않는지, 화풍이 바뀌지 않았는지 확인한 뒤 채택한다.
- 스크립트의 강도와 설정값은 권장값이다. 값을 바꿨다면 바꾼 값과 이유를 채택 기록에 남긴다.
- 채택 기록에 결함 후처리 방침, 얼굴 복원 범위, 손가락 다시 그리기 선택, 도구, 강도, 상자 좌표, seed를 더한다.

## 설치

후처리를 쓰기로 한 경우에만 설치한다. 다른 후처리 작업보다 설치를 먼저 한다.

```
PY -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu gfpgan   # 얼굴 복원
PY scripts/patch_basicsr.py                                                                      # 설치 직후 한 번
```

- 부위 다시 그리기는 생성과 같은 패키지(diffusers, transformers, accelerate, peft, huggingface_hub)를 쓰므로 추가 설치가 없다. 첫 사용 때 모델만 내려받는다.
- 얼굴 복원 패키지를 설치할 때 CPU 인덱스를 `--extra-index-url`로 함께 준다. basicsr는 설치할 때 소스를 빌드하면서 별도 빌드 환경에 torch를 새로 받는데, 인덱스를 주지 않으면 CUDA용 torch와 관련 패키지를 수 GB 받아 디스크가 모자랄 수 있다. 같은 옵션으로 gfpgan이 요구하는 torchvision도 CPU용으로 맞춰진다.
- patch_basicsr.py는 torchvision에서 사라진 모듈 경로를 basicsr 패키지 안에서만 현재 경로로 바꾼다. 다른 패키지는 건드리지 않는다.

## 정리

후처리를 더 쓰지 않으면 캐시를 지운다.

```
PY scripts/cache.py delete face
PY scripts/cache.py delete inpaint
```

패키지까지 지우려면 `PY -m pip uninstall gfpgan basicsr facexlib`를 실행한다. 가상환경 안의 패키지만 지워진다.

## 검증 방법

도구나 패키지의 판을 바꾼 뒤에는 아래 프롬프트로 결함을 일부러 만들고, 도구를 적용해 전후를 비교한다. 같은 프롬프트와 seed에서도 모델과 패키지의 판에 따라 결함이 달라지므로, 결함이 나오지 않으면 seed를 바꿔 결함이 있는 표본을 찾는다.

| 확인할 도구 | 프롬프트 | 볼 점 |
|---|---|---|
| 얼굴 복원(뒤틀림) | a businessman pointing his finger toward the camera, arm extended forward, waist up shot, office at night, photorealistic | 비대칭이 줄고 인상이 유지되는지 |
| 얼굴 복원(흐림) | a young woman smiling, waist up portrait, office daylight, photorealistic | 눈동자와 치아가 선명해지는지 |
| 작은 얼굴과 손 | a construction worker in a safety vest holding a power drill, building site, full body, hands visible, photorealistic | 작은 얼굴의 복원 여부, 손과 공구 |
| 팔다리 연결 붕괴 | a gymnast in a handstand pose, one leg extended, gymnasium floor, full body, hands and feet visible, photorealistic | 후처리로 풀리지 않는 결함인지 |
| 손가락 다시 그리기 | a woman waving her open hand at the camera, waist up, bare hands visible, park daylight, photorealistic | 손가락 개수, 손 크기와 자세 변화 |
| 이어 그리기 | close up portrait of a woman wearing thin metal frame sunglasses, three quarter view, daylight street, photorealistic | 끊긴 테가 이어지는지, 겹쳐 그려지지 않는지 |
| 덮어 그리기 | a young woman in a plain white t-shirt standing on a daylight street, waist up, photorealistic | 소매가 옷감으로 늘어나는지, 이음매 |
| 정밀 사물 | a bicycle leaning against a brick wall, side view, full wheels visible, daylight, photorealistic | 바퀴 테와 바큇살이 정리되는지 |
