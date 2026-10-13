# External components and sources

The skill package contains no model weights, executables, or external packages. They are all downloaded from their publishers to the runtime environment at run time. Each downloaded file follows its publisher's license. The licenses below are the ones the publishers state. Check the original text before use.

## Models

| Use | Component | Publisher | License |
|---|---|---|---|
| Standard preset | DreamShaper 8 LCM | https://huggingface.co/Lykon/dreamshaper-8-lcm | CreativeML OpenRAIL-M |
| Light preset | SDXS-512-DreamShaper | https://huggingface.co/IDKiro/sdxs-512-dreamshaper | OpenRAIL++-M |
| Flat preset | tiny-sd | https://huggingface.co/segmind/tiny-sd | CreativeML OpenRAIL-M |
| Precise preset diffusion model | FLUX.2 [klein] 4B, GGUF Q4_0 conversion | https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF | Apache-2.0 |
| Precise preset text encoder | Qwen3-4B, GGUF Q4_K_M conversion | https://huggingface.co/unsloth/Qwen3-4B-GGUF | Apache-2.0 |
| Precise preset VAE | FLUX.2 [klein] 4B VAE | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | Apache-2.0 |
| Region redrawing | Stable Diffusion 1.5 Inpainting | https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting | CreativeML OpenRAIL-M |
| Region redrawing speed-up | LCM-LoRA SD 1.5 | https://huggingface.co/latent-consistency/lcm-lora-sdv1-5 | OpenRAIL++-M |
| Final upscaling | Real-ESRGAN realesr-general-x4v3, realesr-animevideov3 | https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0 | BSD-3-Clause |
| Face restoration | GFPGAN v1.3 | https://github.com/TencentARC/GFPGAN/releases/tag/v1.3.0 | Apache-2.0 |
| Face detection and parsing | facexlib helper weights | https://github.com/xinntao/facexlib/releases | MIT |

- OpenRAIL licenses restrict how the model and its outputs may be used (the list of use restrictions in their attachment). Users of the skill must follow those terms.
- The GFPGAN repository is licensed under Apache-2.0 and states that some third-party components inside it carry other licenses. This skill runs inference only with the clean architecture (`arch="clean"`), which needs no custom CUDA operations.
- tiny-sd distributes its weights as PyTorch pickle files. diffusers and transformers load them in weights-only mode.
- Final upscaling weights, face restoration weights, and the precise preset executable are checked against the SHA-256 values in the scripts before use. The precise preset fetches its Hugging Face models at pinned revisions.

## Executable

| Use | Component | Publisher | License |
|---|---|---|---|
| Running the precise preset | stable-diffusion.cpp prebuilt CLI (release master-881-17860c0, Linux x86_64) | https://github.com/leejet/stable-diffusion.cpp/releases/tag/master-881-17860c0 | MIT |

## Python packages

| Package | Installed from | License |
|---|---|---|
| torch, torchvision | PyTorch CPU index | BSD-3-Clause family (torch combines several open source licenses) |
| diffusers, transformers, accelerate, safetensors, peft, huggingface_hub | PyPI | Apache-2.0 |
| Pillow | PyPI | MIT-CMU |
| numpy | PyPI | BSD-3-Clause family |
| gfpgan, basicsr | PyPI | Apache-2.0 |
| facexlib | PyPI | MIT (PyPI metadata says Apache-2.0) |
| opencv-python | PyPI | Apache-2.0 |

## Safety checker

The generation pipeline runs with the diffusers safety checker turned off. The checker needs a separate model (about 1.2GB) and replaces any flagged result with a black image. Instead, the check step looks for unrequested exposure and covers it with fabric through region redrawing. Do not use unfiltered results as they are in a public-facing service.
