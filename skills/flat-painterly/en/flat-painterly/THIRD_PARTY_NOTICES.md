# Third-Party Notices

flat-painterly is licensed under the GNU General Public License, version 3 or (at your option) any later version (SPDX: `GPL-3.0-or-later`), with an additional permission for its output. `NOTICE.md` holds the copyright notice and the output exception. `LICENSE` holds the full license text.

This skill bundles no third-party code, binaries, fonts or images. Its scripts import the packages below at run time. Users install these packages separately, for example with pip. Each package keeps its own license terms.

| Package | License (SPDX) | Tested version | Source |
|---|---|---|---|
| NumPy | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 2.4.4 | https://github.com/numpy/numpy |
| opencv-python or opencv-python-headless | Apache-2.0 (OpenCV library), MIT (packaging scripts) | 4.13.0.92 | https://github.com/opencv/opencv-python |

## NumPy

- The NumPy license is BSD-3-Clause, Copyright (c) 2005-2025, NumPy Developers.
- Some components inside NumPy carry 0BSD, MIT, Zlib or CC0-1.0 terms.
- The installed package keeps every license text under `numpy-<version>.dist-info/licenses/`.

## OpenCV

- The OpenCV library is licensed under Apache-2.0.
- The opencv-python packaging scripts are licensed under MIT, Copyright (c) Olli-Pekka Heinisuo.
- The opencv-python wheels also redistribute other libraries under their own licenses. The installed package lists them in `cv2/LICENSE-3RD-PARTY.txt`. Examples:
    - FFmpeg under LGPL-2.1 in all opencv-python packages
    - Qt 5 under LGPL-3.0 in the non-headless Linux and macOS packages
    - OpenSSL libcrypto and libssl under the OpenSSL and SSLeay licenses in the Linux and macOS packages
