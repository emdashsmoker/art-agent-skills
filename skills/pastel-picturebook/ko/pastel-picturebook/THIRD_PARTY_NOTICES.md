# Third-Party Notices

pastel-picturebook is free software distributed under the GNU General Public License, version 3 or (at your option) any later version (SPDX-License-Identifier: GPL-3.0-or-later). The full license text is in `LICENSE`. Output produced by running the skill is excluded from the license by the additional permission in `OUTPUT_EXCEPTION.md`.

Copyright (C) 2026 Em Dash Smoker

## Bundled third-party material

This package contains no third-party source code, fonts, images or other assets. All scripts, JSON settings and documents in it were written for this skill.

## Runtime dependencies (not bundled)

The scripts import the libraries below at run time. They are not included in this package. Users install them separately, and each one is governed by its own license.

| Component | License | Project |
|---|---|---|
| NumPy | BSD-3-Clause (NumPy distributions also contain parts under 0BSD, MIT, Zlib and CC0-1.0) | https://numpy.org |
| OpenCV, installed as `opencv-python` or `opencv-python-headless` | Apache-2.0 | https://opencv.org |
| Python standard library (`argparse`, `copy`, `dataclasses`, `importlib`, `json`, `pathlib`) | Python Software Foundation License Version 2 | https://www.python.org |

- The `opencv-python` wheels also ship further libraries under their own licenses, such as FFmpeg (LGPL-2.1) and, in the non-headless Linux and macOS wheels, Qt 5 (LGPL-3.0). The wheel's `LICENSE-3RD-PARTY.txt` lists them.
- Apache-2.0 is compatible with GPL-3.0 and not with GPL-2.0-only. This project is therefore licensed under version 3 or later.

## Generated images

Pictures rendered with this skill are covered by the additional permission in `OUTPUT_EXCEPTION.md`. The GPL does not apply to them, and you may use them freely, including for commercial purposes, without attribution.
