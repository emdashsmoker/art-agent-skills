# Third-party notices

polygon-cel
Copyright (C) 2026 Em Dash Smoker

polygon-cel is licensed under the GNU General Public License, version 3 or (at your option) any later version
(SPDX: GPL-3.0-or-later). The full license text is in `LICENSE`.

## Additional permission for rendered output

Additional permission under GNU GPL version 3 section 7, granted by the copyright holder:
Images and other files produced by running this software are not covered by this License,
even when they reproduce shapes defined in the software. You may use, license, and
distribute such output under any terms you choose.

## Runtime dependencies

This skill does not include or redistribute any third-party code. The libraries below are installed separately
by the user (`pip install -r scripts/requirements.txt`) and remain under their own licenses. All of them are
compatible with GPL-3.0-or-later.

| Package | Required version | License | Project |
|---|---|---|---|
| numpy | >=1.24 | BSD-3-Clause (wheels also bundle components under 0BSD, MIT, Zlib, CC0-1.0) | https://numpy.org |
| opencv-python-headless | >=4.8 | Apache-2.0 (wheels also bundle third-party components, including LGPL-licensed FFmpeg) | https://github.com/opencv/opencv-python |
| skia-python | >=87.5 | BSD-3-Clause (built on Skia, BSD-3-Clause) | https://github.com/kyamagu/skia-python |

- Licenses were read from the installed package metadata and license files (numpy 2.4.4,
  opencv-python-headless 4.13.0.92, skia-python 144.0.post2)
- Apache-2.0 is compatible with GPL version 3 but not with GPL version 2, which is why this skill uses version 3
  or later

## Published methods

Some rendering steps implement methods described in published papers. No code was copied from these works;
they are listed for credit.

- Aaron Hertzmann (1998), Painterly Rendering with Curved Brush Strokes of Multiple Sizes (painterly style)
- Adrien Bousseau et al. (2006), Interactive Watercolor Rendering with Temporal Coherence and Abstraction
  (watercolor pigment density model)
- Scott F. Johnston (2002), Lumo: Illumination for Cel Animation (normals from mask distance fields)
