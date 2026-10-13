# 외부 구성 요소와 출처

스킬 패키지에는 모델 가중치, 실행 파일, 외부 패키지가 들어 있지 않다. 모두 실행할 때 각 배포처에서 실행 환경으로 받는다. 받은 파일은 각 배포처의 라이선스를 따른다. 아래 표의 라이선스는 배포처가 밝힌 값이며, 사용 전에 원문을 확인한다.

## 모델

| 용도 | 구성 요소 | 배포처 | 라이선스 |
|---|---|---|---|
| 표준 프리셋 | DreamShaper 8 LCM | https://huggingface.co/Lykon/dreamshaper-8-lcm | CreativeML OpenRAIL-M |
| 경량 프리셋 | SDXS-512-DreamShaper | https://huggingface.co/IDKiro/sdxs-512-dreamshaper | OpenRAIL++-M |
| 플랫 프리셋 | tiny-sd | https://huggingface.co/segmind/tiny-sd | CreativeML OpenRAIL-M |
| 정밀 프리셋 확산 모델 | FLUX.2 [klein] 4B, GGUF Q4_0 변환본 | https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF | Apache-2.0 |
| 정밀 프리셋 텍스트 인코더 | Qwen3-4B, GGUF Q4_K_M 변환본 | https://huggingface.co/unsloth/Qwen3-4B-GGUF | Apache-2.0 |
| 정밀 프리셋 VAE | FLUX.2 [klein] 4B VAE | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | Apache-2.0 |
| 부위 다시 그리기 | Stable Diffusion 1.5 Inpainting | https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting | CreativeML OpenRAIL-M |
| 부위 다시 그리기 가속 | LCM-LoRA SD 1.5 | https://huggingface.co/latent-consistency/lcm-lora-sdv1-5 | OpenRAIL++-M |
| 화질 보정 | Real-ESRGAN realesr-general-x4v3, realesr-animevideov3 | https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0 | BSD-3-Clause |
| 얼굴 복원 | GFPGAN v1.3 | https://github.com/TencentARC/GFPGAN/releases/tag/v1.3.0 | Apache-2.0 |
| 얼굴 탐지와 영역 분할 | facexlib 보조 가중치 | https://github.com/xinntao/facexlib/releases | MIT |

- OpenRAIL 계열 라이선스는 모델과 산출물의 사용에 제한 조항(부속서의 사용 제한 목록)을 둔다. 스킬 사용자는 이 조항을 지켜야 한다.
- GFPGAN 저장소의 라이선스는 Apache-2.0이며, 저장소 안의 일부 제3자 구성 요소에는 다른 라이선스가 붙어 있다고 밝힌다. 이 스킬은 사용자 정의 CUDA 연산이 필요 없는 clean 구조(`arch="clean"`)로만 추론한다.
- tiny-sd는 가중치를 PyTorch pickle 형식으로 배포한다. diffusers와 transformers는 이 파일을 텐서만 읽는 방식으로 적재한다.
- 화질 보정과 얼굴 복원, 정밀 프리셋 실행 파일은 스크립트에 적힌 SHA-256과 대조한 뒤 쓴다. Hugging Face 모델은 정밀 프리셋에서 고정 리비전으로 받는다.

## 실행 파일

| 용도 | 구성 요소 | 배포처 | 라이선스 |
|---|---|---|---|
| 정밀 프리셋 실행 | stable-diffusion.cpp 사전 빌드 CLI(릴리스 master-881-17860c0, 리눅스 x86_64) | https://github.com/leejet/stable-diffusion.cpp/releases/tag/master-881-17860c0 | MIT |

## 파이썬 패키지

| 패키지 | 설치 경로 | 라이선스 |
|---|---|---|
| torch, torchvision | PyTorch CPU 인덱스 | BSD-3-Clause 계열(torch는 여러 오픈소스 라이선스의 조합) |
| diffusers, transformers, accelerate, safetensors, peft, huggingface_hub | PyPI | Apache-2.0 |
| Pillow | PyPI | MIT-CMU |
| numpy | PyPI | BSD-3-Clause 계열 |
| gfpgan, basicsr | PyPI | Apache-2.0 |
| facexlib | PyPI | MIT(PyPI 표기는 Apache-2.0) |
| opencv-python | PyPI | Apache-2.0 |

## 안전 검사기

생성 파이프라인은 diffusers의 안전 검사기를 끄고 실행한다. 안전 검사기는 별도 모델(약 1.2GB)을 더 받아야 하고, 걸린 결과를 통째로 검은 이미지로 바꾼다. 대신 점검 단계에서 요청하지 않은 노출을 눈으로 확인하고 부위 다시 그리기로 옷감을 덮는다. 결과를 거르지 않은 채 공개 서비스에 그대로 노출하는 용도로는 쓰지 않는다.
