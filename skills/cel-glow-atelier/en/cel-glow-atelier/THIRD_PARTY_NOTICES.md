# Third-Party Notices

## Project license

Cel Glow Atelier, in its Korean and English editions (`cel-glow-atelier`).

Copyright (C) 2026 Em Dash Smoker

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

The full license text is in the `LICENSE` file next to this notice.

SPDX-License-Identifier: GPL-3.0-or-later

## Output exception

As an additional permission under section 7 of the GNU General Public License version 3, the copyright holder grants the following.

Images and other files that this program produces when you run it (the "Output") are not covered by the GNU General Public License. This applies even when the Output contains shapes, palettes, presets or other material generated from this program's built-in data. You may use, modify, distribute and license the Output for any purpose under terms of your choice.

This permission covers the Output only. The program itself, including its source code, documentation and example files, remains under GPL-3.0-or-later.

If you modify this program, you may extend this permission to your version, but you are not obligated to do so. If you do not wish to do so, delete this permission from your version.

## Bundled third-party material

None. This skill ships no third-party source files, fonts, images or model weights.

## Runtime dependencies

The scripts import the components below at runtime. Users install them separately. This skill does not redistribute them.

| Component | Imported as | License | Tested version | Project |
|---|---|---|---|---|
| Python | standard library modules | Python Software Foundation License Version 2 (full terms: run `license()` in Python) | 3.13.15 | https://www.python.org |
| NumPy (`numpy`) | `numpy` | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 2.5.3 | https://numpy.org |
| OpenCV (`opencv-python-headless`) | `cv2` | Apache-2.0 | 5.0.0.93 | https://github.com/opencv/opencv-python |

The binary wheels of NumPy and OpenCV include native libraries with their own licenses (for example OpenBLAS and the GCC runtime in NumPy, FFmpeg and OpenSSL in OpenCV). Those license texts are installed with each package:

- NumPy: `numpy-<version>.dist-info/licenses/`
- OpenCV: `opencv_python_headless-<version>.dist-info/LICENSE-3RD-PARTY.txt` and `cv2/LICENSE-3RD-PARTY.txt`
