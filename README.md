# art-agent-skills

Agent Skills that make creative pictures such as illustrations, paintings and photorealistic portraits. Every skill ships as a Korean original and an English translation.

일러스트, 회화, 실사풍 인물처럼 창작용 그림을 만드는 에이전트 스킬 모음입니다. 모든 스킬은 한국어 원본과 영어 번역본을 함께 제공합니다.

<details>
<summary>English</summary>

## Skills

### Diffusion-based

- [`image-gen`](skills/image-gen/): Generates images with local diffusion models on the CPU, then fixes defects with edge trimming, face restoration, region redrawing and upscaling. [Samples](skills/image-gen/demo/)
- [`image-gen-addon-codeformer`](skills/image-gen-addon-codeformer/): Add-on that brings CodeFormer into the face restoration step of `image-gen`.

### Non-diffusion

These skills finish a picture without diffusion models, following the principles of perspective, proportion, shading and color and the painting process written into each skill. Each skill takes its name from its painting style.

- [`cel-glow-atelier`](skills/cel-glow-atelier/): Computes all shading from one light vector for cel-shaded pictures with spreading rim light and bloom. [Samples](skills/cel-glow-atelier/demo/)
- [`clay-cel-canvas`](skills/clay-cel-canvas/): Sets volume and shadow on a 3-D clay mannequin, then lays 2-D cel color over it. [Samples](skills/clay-cel-canvas/demo/)
- [`dollhouse-maker`](skills/dollhouse-maker/): Sets smooth dolls with inflated silhouettes in a one-point-perspective model room, like a dollhouse with one wall open. [Samples](skills/dollhouse-maker/demo/)
- [`flat-painterly`](skills/flat-painterly/): Stages jointed mannequins and perspective boxes, then paints them with brushwork for a still-frame look. [Samples](skills/flat-painterly/demo/)
- [`geometric-illustration`](skills/geometric-illustration/): Builds forms from spheres and cones and draws them in hand-drawing order, with crisp ink silhouettes on calm navy tones. [Samples](skills/geometric-illustration/demo/)
- [`maquette-painter`](skills/maquette-painter/): Paints as if from a lit 3-D maquette, with clear form and cast shadows. [Samples](skills/maquette-painter/demo/)
- [`paper-stage`](skills/paper-stage/): Stacks and inflates curve-cut paper pieces into a paper stage with stage light and film grain. [Samples](skills/paper-stage/demo/)
- [`pastel-picturebook`](skills/pastel-picturebook/): Works through sketch, flat color, shading and inking for pastel picture-book art with clear colors, thin lines and tidy cel shading. [Samples](skills/pastel-picturebook/demo/)
- [`polygon-cel`](skills/polygon-cel/): Lays bold colored line art, two-tone cel shading and a calm muted palette over polygon forms built from formulas. [Samples](skills/polygon-cel/demo/)
- [`soft-diorama`](skills/soft-diorama/): Uses swelling ribbon lines, crescent cel shadows and soft volume for pictures like small stage sets. [Samples](skills/soft-diorama/demo/)
- [`tableau-vivant`](skills/tableau-vivant/): Poses a parametric human body on a 3-D stage and paints it as a still scene with held-breath poses and stage light. [Samples](skills/tableau-vivant/demo/)
- [`vinyl-cel`](skills/vinyl-cel/): Lights forms made of spheres, ellipsoids and distance functions from a depth map for round, smooth, vinyl-figure cel art. [Samples](skills/vinyl-cel/demo/)

## Installation

Each skill folder holds the install packages, a checksum file, the source folders and sample pictures.

```
skills/vinyl-cel/
├── vinyl-cel-ko.skill    Korean install package
├── vinyl-cel-en.skill    English install package
├── SHA256SUMS.txt        SHA-256 checksums of the packages
├── ko/vinyl-cel/         Korean source
├── en/vinyl-cel/         English source
└── demo/                 sample pictures
```

- A `.skill` file is a zip archive of the skill folder. Where only `.zip` uploads are accepted, rename the extension to `.zip`.
- To install from source, copy the folder named after the skill (for example `ko/vinyl-cel/`) into your agent's skills folder.
- The Korean and English editions share one skill name, so only one of them can be installed at a time.
- On claude.ai with access to outside addresses such as GitHub and Hugging Face blocked, or on a closed network, the skills cannot install their dependencies at run time. In that case, use [`offline-deps-builder`](https://github.com/emdashsmoker/biz-agent-skills/tree/main/skills/offline-deps-builder) in an environment with network access to build a dependency skill that holds the required files. Then load the dependency skill together with the original skill.

## Limitations

- Testing used Claude Opus 5.5 and Claude Fable 5.1. Results may differ with other models and environments.
- Testing did not cover every edge case, and some skills have had limited testing.
- Some skills may duplicate functions of other skills.
- The model uses the examples bundled in each skill as a reference for edge cases, so results may come out close to those examples or the demos.
- For results that do not resemble them, add an instruction such as `Do not make it similar to the examples or demos in the skill.` to your request.
- Every skill needs a code execution environment and network access.
- The skills use many tokens because the model reads long reference files and the images it renders over several rounds of checking.
- `image-gen` downloads several gigabytes of model files on first use and generates on the CPU, so each image takes time.

## Disclaimer

The skills come as they are, without any warranty. Correct operation in every environment is not guaranteed. The end user bears responsibility for using the skills and their output. The people in the `image-gen` demo images are fictional and generated by a model.

## License

[GPL-3.0-or-later](LICENSE). Copyright (C) 2026 Em Dash Smoker.

Each skill carries its own `LICENSE` and notice files. Under the output exception, the pictures you make with a skill are free of GPL terms. The sample pictures in the `demo/` folders are licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

The models that `image-gen` downloads keep their own licenses, listed in `references/components.md`. CreativeML OpenRAIL-M and OpenRAIL++-M restrict how the models and their output may be used. CodeFormer, which `image-gen-addon-codeformer` loads, is under the S-Lab License 1.0 and allows non-commercial use only.

</details>

<details>
<summary>한국어</summary>

## 스킬 목록

### 확산 모델 기반

- [`image-gen`](skills/image-gen/): 로컬 확산 모델을 CPU로 실행해 이미지를 생성하고 가장자리 정리, 얼굴 복원, 부분 다시 그리기, 업스케일로 결함을 보정합니다. [예시](skills/image-gen/demo/)
- [`image-gen-addon-codeformer`](skills/image-gen-addon-codeformer/): `image-gen`의 얼굴 복원 단계에 CodeFormer를 추가하는 애드온입니다.

### 비확산 모델 기반

원근, 비례, 명암, 색채 같은 조형 원리와 그리는 과정을 담은 스킬 지침에 따라 확산 모델 없이 그림을 완성합니다. 스킬 이름은 각 스킬의 화풍에서 따왔습니다.

- [`cel-glow-atelier`](skills/cel-glow-atelier/): 빛 벡터 하나로 모든 명암을 계산해 림라이트와 블룸이 번지는 셀 셰이딩 그림을 그립니다. [예시](skills/cel-glow-atelier/demo/)
- [`clay-cel-canvas`](skills/clay-cel-canvas/): 3D 점토 마네킹으로 양감과 그림자를 설정한 뒤 2D 셀 채색을 입힙니다. [예시](skills/clay-cel-canvas/demo/)
- [`dollhouse-maker`](skills/dollhouse-maker/): 실루엣을 부풀린 매끈한 인형과 1점 투시 모형 방으로 벽 한 면을 연 인형의 집 같은 그림을 만듭니다. [예시](skills/dollhouse-maker/demo/)
- [`flat-painterly`](skills/flat-painterly/): 관절 마네킹과 원근 상자로 무대를 구성한 뒤 붓질로 채색해 정지 화면 같은 회화풍 그림을 만듭니다. [예시](skills/flat-painterly/demo/)
- [`geometric-illustration`](skills/geometric-illustration/): 구와 원뿔로 형태를 구성한 뒤 손그림 순서대로 그려 선명한 잉크 실루엣과 차분한 남색 톤의 그림을 만듭니다. [예시](skills/geometric-illustration/demo/)
- [`maquette-painter`](skills/maquette-painter/): 조명을 비춘 3D 마케트를 참고해 채색하듯 형태와 그림자가 분명한 그림을 그립니다. [예시](skills/maquette-painter/demo/)
- [`paper-stage`](skills/paper-stage/): 곡선으로 오린 종이 조각을 앞뒤로 겹치고 부풀려 무대 조명과 필름 그레인이 있는 종이 무대 그림을 만듭니다. [예시](skills/paper-stage/demo/)
- [`pastel-picturebook`](skills/pastel-picturebook/): 밑그림, 밑색, 명암, 선화 공정을 거쳐 맑은 색, 가는 선, 단정한 셀 명암의 파스텔 그림책 그림을 그립니다. [예시](skills/pastel-picturebook/demo/)
- [`polygon-cel`](skills/polygon-cel/): 수식으로 만든 다각형 형태에 굵은 색 선화, 투톤 셀 명암, 차분한 저채도 색을 입힙니다. [예시](skills/polygon-cel/demo/)
- [`soft-diorama`](skills/soft-diorama/): 굵기가 변하는 리본 선, 초승달 모양 셀 그림자, 부드러운 양감으로 작은 무대 세트 같은 그림을 만듭니다. [예시](skills/soft-diorama/demo/)
- [`tableau-vivant`](skills/tableau-vivant/): 매개변수 인체를 3D 무대에 배치한 뒤 채색해 숨을 멈춘 듯한 포즈와 무대 조명의 정지 장면을 만듭니다. [예시](skills/tableau-vivant/demo/)
- [`vinyl-cel`](skills/vinyl-cel/): 구, 타원체, 거리 함수로 만든 형태를 깊이 맵으로 조명해 둥글고 매끈한 비닐 피규어 같은 셀 그림을 그립니다. [예시](skills/vinyl-cel/demo/)

## 설치

스킬 폴더마다 설치용 패키지, 체크섬 파일, 소스 폴더, 예시 그림이 들어 있습니다.

```
skills/vinyl-cel/
├── vinyl-cel-ko.skill    한국어판 설치용 패키지
├── vinyl-cel-en.skill    영어판 설치용 패키지
├── SHA256SUMS.txt        설치용 패키지 SHA-256 체크섬
├── ko/vinyl-cel/         한국어판 소스
├── en/vinyl-cel/         영어판 소스
└── demo/                 예시 그림
```

- `.skill` 파일은 스킬 폴더를 묶은 zip 파일입니다. `.zip` 파일만 올릴 수 있는 환경에서는 확장자를 `.zip`으로 변경해 업로드합니다.
- 소스로 설치할 때는 스킬 이름과 같은 폴더(예를 들어 `ko/vinyl-cel/`)를 에이전트의 스킬 폴더에 복사합니다.
- 한국어판과 영어판은 스킬 이름이 같아서 둘 중 하나만 설치할 수 있습니다.
- claude.ai처럼 GitHub, Hugging Face 등 외부 주소의 접근이 차단된 환경이나 폐쇄망에서는 스킬이 실행 중에 의존성을 설치할 수 없습니다. 이 경우 네트워크를 사용할 수 있는 환경에서 [`offline-deps-builder`](https://github.com/emdashsmoker/biz-agent-skills/tree/main/skills/offline-deps-builder)로 필요한 파일을 포함한 의존성 스킬을 사전에 생성합니다. 생성한 의존성 스킬은 원래 스킬과 함께 로드합니다.

## 한계

- 테스트는 Claude Opus 5.5와 Claude Fable 5.1에서 진행했습니다. 다른 모델과 실행 환경에서는 결과가 달라질 수 있습니다.
- 모든 예외 상황을 테스트하지는 못했습니다. 일부 스킬은 테스트가 충분하지 않습니다.
- 일부 스킬은 기능이 중복될 수 있습니다.
- 모델은 예외 상황을 처리할 때 스킬에 들어 있는 예제를 기준 자료로 참고합니다. 따라서 결과물이 예제나 데모와 비슷해질 수 있습니다.
- 예제를 닮지 않은 결과물이 필요하면 요청할 때 `스킬에 들어 있는 예제나 데모와 비슷하게 만들지 마세요` 같은 제외 지시를 함께 기재하기를 권장합니다.
- 모든 스킬은 코드 실행 환경과 네트워크 연결이 있어야 작동합니다.
- 스킬을 실행하면 토큰이 많이 소모됩니다. 모델이 긴 참고 문서와 여러 차례 렌더링한 확인용 그림을 읽기 때문입니다.
- `image-gen`은 처음 실행할 때 수 GB의 모델 파일을 내려받습니다. CPU로 생성하므로 이미지 한 장을 만드는 데 시간이 걸립니다.

## 면책 고지

이 저장소의 스킬은 어떠한 보증 없이 있는 그대로 제공합니다. 모든 환경에서 정상 작동을 보장하지 않습니다. 스킬 사용과 결과물에 대한 책임은 최종 사용자에게 있습니다. `image-gen` 예시 그림의 인물은 모델이 생성한 가상 인물입니다.

## 라이선스

[GPL-3.0-or-later](LICENSE)를 따릅니다. Copyright (C) 2026 Em Dash Smoker.

스킬마다 `LICENSE`와 고지 파일이 들어 있습니다. 출력물 예외 조항에 따라 스킬로 그린 그림은 GPL 조건 없이 사용할 수 있습니다. `demo/` 폴더의 예시 그림은 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.ko)을 따릅니다.

`image-gen`이 내려받는 모델은 각자의 라이선스를 따릅니다. 모델별 라이선스는 `references/components.md`에 정리되어 있습니다. CreativeML OpenRAIL-M과 OpenRAIL++-M은 모델과 생성물의 사용 범위를 제한합니다. `image-gen-addon-codeformer`가 불러오는 CodeFormer는 비상업적 용도만 허용하는 S-Lab License 1.0을 따릅니다.

</details>

## References

Thanks to the developers and contributors of these projects.

이 프로젝트들의 개발자와 기여자분들께 감사드립니다.

- [DreamShaper 8 LCM](https://huggingface.co/Lykon/dreamshaper-8-lcm)
- [SDXS-512-DreamShaper](https://huggingface.co/IDKiro/sdxs-512-dreamshaper)
- [tiny-sd](https://huggingface.co/segmind/tiny-sd)
- [FLUX.2 [klein] 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)
- [FLUX.2 [klein] 4B GGUF](https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF)
- [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B)
- [Qwen3-4B GGUF](https://huggingface.co/unsloth/Qwen3-4B-GGUF)
- [Stable Diffusion 1.5 Inpainting](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting)
- [LCM-LoRA SD 1.5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5)
- [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp)
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- [GFPGAN](https://github.com/TencentARC/GFPGAN)
- [facexlib](https://github.com/xinntao/facexlib)
- [CodeFormer](https://github.com/sczhou/CodeFormer)
- [Anny](https://github.com/naver/anny)
- [skia-python](https://github.com/kyamagu/skia-python)
