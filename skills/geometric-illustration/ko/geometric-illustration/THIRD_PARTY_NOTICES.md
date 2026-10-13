# Third-Party Notices

geometric-illustration
Copyright (C) 2026 Em Dash Smoker

This program is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version (SPDX: GPL-3.0-or-later). This program is distributed
in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the full license text in `LICENSE`.

## Rendered images

Images you render with this program are not covered by the GNU GPL. They contain no part of the
program's code.

Additional permission under section 7 of the GNU GPL version 3: you may use, copy, modify,
distribute and sell images produced by running this program, for any purpose including commercial
use, under terms of your choice. You have no obligation to release source code for such images or
to license them under the GPL. This permission covers rendered images only. The program, its source
code and modified versions of it remain under GPL-3.0-or-later.

## Runtime dependencies (not included)

This package bundles no third-party code, binaries, fonts or image files. It imports the packages
below at run time, and the user installs them separately
(`pip install numpy opencv-python-headless`). Their own licenses apply to them.

| Component | Tested versions | License | Source |
|---|---|---|---|
| Python standard library | 3.11, 3.13 | PSF-2.0 | https://docs.python.org/3/license.html |
| NumPy | 2.4, 2.5 | BSD-3-Clause (with 0BSD, MIT, Zlib and CC0-1.0 parts) | https://numpy.org/doc/stable/license.html |
| OpenCV (`opencv-python-headless`) | 4.13, 5.0 | Apache-2.0 (OpenCV), MIT (packaging scripts) | https://github.com/opencv/opencv-python#licensing |
| FFmpeg (shipped inside every `opencv-python` wheel) | | LGPL-2.1 | https://github.com/opencv/opencv-python/blob/master/LICENSE-3RD-PARTY.txt |

All of these licenses are compatible with GPL-3.0-or-later. Apache-2.0 is not compatible with
GPL-2.0-only, so this project does not offer a GPLv2-only option. If you redistribute this project
together with these packages (for example in a container image), include their license files.

## Data

Body proportion targets in `scripts/rig_anatomy.py`, `scripts/rig_hand.py`,
`scripts/check_proportions.py` and `references/anatomy.md` are values derived from the ANSUR II
anthropometric survey (U.S. Army, 2012). ANSUR II is a work of the U.S. federal government and is
in the public domain in the United States (17 U.S.C. 105). No raw survey files are included.

- Penn State OpenLab, ANSUR II dataset: https://www.openlab.psu.edu/ansur2/
- Gordon, C. C. et al. (2014), 2012 Anthropometric Survey of U.S. Army Personnel: Methods and
  Summary Statistics, Technical Report NATICK/TR-15/007:
  http://tools.openlab.psu.edu/publicData/ANSURII-MFR.pdf

## Methods and publications

The code below was written for this project. It follows the published methods named here;
no code was copied from these sources.

- Oil style (`scripts/painterly.py`): Hertzmann, A. (1998), Painterly Rendering with Curved Brush
  Strokes of Multiple Sizes, SIGGRAPH.
- Watercolor style (`scripts/painterly.py`): Bousseau, A., Kaplan, M., Thollot, J., Sillion, F. (2006),
  Interactive Watercolor Rendering with Temporal Coherence and Abstraction, NPAR.
- Brush texture (`scripts/painterly.py`): Cabral, B., Leedom, L. (1993), Imaging Vector Fields Using
  Line Integral Convolution, SIGGRAPH.
- Mannequin silhouettes (`scripts/mannequin.py`): exact 2D distance to an uneven capsule, after the
  distance function articles of Inigo Quilez (https://iquilezles.org/articles/distfunctions2d/).
- Figure construction from spheres and cones follows the drawing methods of Andrew Loomis and
  George Bridgman.
