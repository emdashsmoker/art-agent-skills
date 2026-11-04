# Notice

image-gen-lite
Copyright (C) 2026 Em Dash Smoker

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program in the file LICENSE. If not, see <https://www.gnu.org/licenses/>.

SPDX-License-Identifier: GPL-3.0-or-later

## Output exception

As an additional permission under section 7 of the GNU General Public License version 3, the copyright holder grants the following.

Files that this program produces when you run it, such as images and data (the "Output"), are not covered by the GNU General Public License. This applies even when the Output contains text, templates, layouts, styles or other material taken from this program.

This permission covers the Output only. The program itself, including its instructions and scripts, remains under GPL-3.0-or-later.

If you modify this program, you may extend this permission to your version, but you are not obligated to do so. If you do not wish to do so, delete this permission from your version.

## Models and third-party software

The skill package contains no model weights, executables or external packages. They are downloaded at run time from their publishers and keep their own licenses. The output exception above does not lift the use restrictions of those licenses.

| Use | Component | Publisher | License |
|---|---|---|---|
| Standard preset | DreamShaper 8 LCM | https://huggingface.co/Lykon/dreamshaper-8-lcm | CreativeML OpenRAIL-M |
| Light preset | SDXS-512-DreamShaper | https://huggingface.co/IDKiro/sdxs-512-dreamshaper | OpenRAIL++-M |
| Flat preset | tiny-sd | https://huggingface.co/segmind/tiny-sd | CreativeML OpenRAIL-M |
| Precise preset, diffusion model | FLUX.2 [klein] 4B, GGUF Q4_0 | https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF | Apache-2.0 |
| Precise preset, text encoder | Qwen3-4B, GGUF Q4_K_M | https://huggingface.co/unsloth/Qwen3-4B-GGUF | Apache-2.0 |
| Precise preset, VAE | FLUX.2 [klein] 4B VAE | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | Apache-2.0 |
| Precise preset, engine | stable-diffusion.cpp prebuilt CLI (master-881-17860c0; Linux x86_64, macOS arm64, Windows x64 CPU builds) | https://github.com/leejet/stable-diffusion.cpp | MIT |
| Python packages | torch, torchvision (BSD-3-Clause family), diffusers, transformers, accelerate, safetensors, peft, huggingface_hub (Apache-2.0), Pillow (MIT-CMU), numpy (BSD-3-Clause family) | PyTorch CPU index, PyPI | as listed |

- OpenRAIL licenses restrict how the model and its output may be used (the use-based restrictions in their attachments). Users of this skill must follow them.
- tiny-sd ships its weights as PyTorch pickle files. diffusers and transformers load them in weights-only mode.
- The generation pipeline runs with the diffusers safety checker disabled. It needs an extra 1.2GB model and replaces any flagged image with a black one. Content rules are in the minor-protection section of SKILL.md.
