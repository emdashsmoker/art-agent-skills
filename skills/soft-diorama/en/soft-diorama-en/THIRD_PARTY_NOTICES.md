# Third-Party Notices

soft-diorama-en, the English edition of soft-diorama, is free software licensed under the GNU General Public License, version 3 or (at your option) any later version. The full license text is in `LICENSE`. The copyright notice and the exception for generated images are in `NOTICE.md`.

This file lists the third-party software and published work the skill depends on. The repository contains none of their code or binaries.

## Runtime dependencies

The user installs these packages separately with `pip install -r scripts/requirements.txt`.

| Package | Required version | License | Copyright | Upstream |
|---|---|---|---|---|
| NumPy | 1.24 or later | BSD-3-Clause (some bundled parts under 0BSD, MIT, Zlib and CC0-1.0) | Copyright (c) 2005-2025, NumPy Developers | https://github.com/numpy/numpy |
| OpenCV library, shipped inside the opencv-python wheel | 4.8 or later | Apache-2.0 | OpenCV contributors, see the upstream LICENSE | https://github.com/opencv/opencv |
| opencv-python packaging scripts | 4.8 or later | MIT | Copyright (c) Olli-Pekka Heinisuo | https://github.com/opencv/opencv-python |

Apache-2.0 is compatible with GPL version 3. Every license in the table is compatible with GPL-3.0-or-later.

### Binaries inside the OpenCV wheel

The opencv-python wheels contain more third-party binaries under their own licenses. Examples are FFmpeg (LGPL), Qt 5 in the non-headless builds (LGPL), OpenSSL, libpng and libwebp. The full list and license texts ship with each wheel in `cv2/LICENSE-3RD-PARTY.txt`.

Anyone who redistributes this skill together with an installed OpenCV wheel, for example in a container image, must also follow the terms in that file.

### Python standard library

The scripts also import standard library modules (`argparse`, `dataclasses`, `hashlib`, `pathlib`, `sys`). They come with the Python runtime under the Python Software Foundation License.

## Algorithm references

The watercolor pigment model in `scripts/paintkit/finish.py` follows the color formula described in the paper below. The implementation is original code written from the paper's description.

- Adrien Bousseau, Matt Kaplan, Joëlle Thollot and François X. Sillion. "Interactive Watercolor Rendering with Temporal Coherence and Abstraction." Proceedings of the 4th International Symposium on Non-Photorealistic Animation and Rendering (NPAR 2006).
