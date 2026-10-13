# Third-Party Notices

## This project

tableau-vivant, including its English edition tableau-vivant-en

Copyright (C) 2026 Em Dash Smoker

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program (the `LICENSE` file). If not, see <https://www.gnu.org/licenses/>.

SPDX-License-Identifier: GPL-3.0-or-later

The license covers every file of the skill: `SKILL.md`, `references/`, `examples/` and `scripts/`.

## Rendered images are not covered

Images you render with this skill are output of the program, and the GPL does not apply to them.

- The copyright holder claims no rights in them and attaches no conditions to them.
- You may use, modify, publish, sell or license them on any terms you choose.
- No attribution, notice or source code is required when you share them.
- This holds whether you render with the skill as published or with a version you modified.
- The body meshes and face data the renders are built from are CC0-1.0 (see "Data used through anny"), so they add no conditions either.

## Third-party material bundled with the skill

None. The skill contains only its own code, documentation and example specs. The packages below are downloaded from their own distributors when `scripts/install.sh` runs, and each keeps its own license.

## Runtime dependencies (installed separately, not bundled)

Versions are those the skill was tested with. `install.sh` pins only `anny`.

| Package | Tested version | License | Source |
| --- | --- | --- | --- |
| anny | 0.6.1 | Apache-2.0. Copyright (C) 2025 NAVER Corporation | https://github.com/naver/anny |
| torch (CPU build) | 2.14.1 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | https://github.com/pytorch/pytorch |
| numpy | 2.4.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | https://github.com/numpy/numpy |
| scipy | 1.17.1 | BSD-3-Clause | https://github.com/scipy/scipy |
| opencv-python-headless | 4.13.0.92 | Apache-2.0 (the wheel also bundles third-party libraries, listed in its `LICENSE-3RD-PARTY.txt`) | https://github.com/opencv/opencv-python |
| pillow | 12.2.0 | MIT-CMU | https://github.com/python-pillow/Pillow |
| numba | 0.68.0 | BSD-2-Clause | https://github.com/numba/numba |
| roma | 1.6.1 | BSD-3-Clause | https://github.com/naver/roma |
| safetensors | 0.8.0 | Apache-2.0 | https://github.com/huggingface/safetensors |
| trimesh | 5.1.0 | MIT | https://github.com/mikedh/trimesh |
| PyYAML | 6.0.3 | MIT | https://github.com/yaml/pyyaml |
| requests | 2.33.1 | Apache-2.0 | https://github.com/psf/requests |

## Data used through anny

| Data | Author | License | Use in this skill |
| --- | --- | --- | --- |
| `data/mpfb2`: MakeHuman assets adapted from MPFB2 (body mesh, helper meshes, textures) | MakeHuman community | CC0-1.0 | Body, clothing base meshes, face and skin masks |
| `data/faceunits01`: Face Units asset pack | Mika Suominen | CC0-1.0 | Facial expressions |
| `smplx` topology (downloaded on demand) | Distributed by NAVER LABS Europe for interoperability with SMPL-X | Non-commercial use only | Not used. The engine loads only the `anny-full` topology with the `makehuman` rig, so this data is never downloaded |

## Note for redistributors

- If you ship the skill together with its dependencies (for example in a container image), each dependency's license applies to its part of that bundle. Apache-2.0 packages require their `LICENSE` and `NOTICE` files to be kept.
- The `opencv-python-headless` wheel bundles FFmpeg (LGPL-2.1) and OpenSSL 1.1.1. The Free Software Foundation lists the OpenSSL 1.1.1 license as incompatible with the GPL. This matters only when the skill and that wheel are distributed together as one combined work.
