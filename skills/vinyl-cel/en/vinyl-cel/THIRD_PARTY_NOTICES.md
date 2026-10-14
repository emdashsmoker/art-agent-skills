# Notices

## vinyl-cel

Copyright (C) 2026 Em Dash Smoker

vinyl-cel is free software: you can redistribute it and/or modify it under the terms of the GNU General
Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
option) any later version (SPDX: `GPL-3.0-or-later`). It is distributed WITHOUT ANY WARRANTY. The full
license text is in `LICENSE`.

### Output exception

As an additional permission under section 7 of the GNU GPL version 3, the images and any other output you
produce by running vinyl-cel are yours to use, modify, publish and sell for any purpose, without
attribution and without applying the GPL to them. The copyright holder claims no rights in that output.
The rendered images shipped with the skill (`assets/`) count as output in this sense and may be used the
same way.

This permission covers the output only. The skill itself, including scene scripts copied or adapted from
its examples, stays under the GPL when you convey it.

## What this skill contains

Every file in this skill was written for it or rendered by its own code: the Python package
`scripts/codeillust`, the example scenes, the self-test, the instructions (`SKILL.md`, `references/`) and
the reference images in `assets/`. No third-party source code, binaries, fonts or images are bundled.

## What it needs at run time

The scripts import the packages below. They are installed separately by the user
(`pip install numpy opencv-python`) and are not redistributed with this skill. Their own licenses
apply to them; each is compatible with GPL-3.0-or-later.

| Component | Used for | License | Copyright | Project |
|---|---|---|---|---|
| NumPy | Arrays and all numeric work | BSD-3-Clause | Copyright (c) 2005-2025, NumPy Developers | https://numpy.org |
| OpenCV (the `cv2` module) | Drawing, warping, blurring, image files | Apache-2.0 (OpenCV 4.5.0 and later) | The OpenCV authors and contributors (see the LICENSE and COPYRIGHT files of OpenCV) | https://opencv.org |
| opencv-python (the pip package that ships `cv2`) | Installing OpenCV | MIT for the packaging scripts | Copyright (c) Olli-Pekka Heinisuo | https://github.com/opencv/opencv-python |
| Python standard library | `dataclasses`, `pathlib`, `argparse` and others | PSF-2.0 | Copyright (c) Python Software Foundation | https://www.python.org |

- OpenCV releases before 4.5.0 were under BSD-3-Clause, which is also compatible.
- The opencv-python wheels carry further libraries of their own (for example FFmpeg under LGPL-2.1).
  Their notices are in `LICENSE-3RD-PARTY.txt` inside the installed package. They concern anyone who
  redistributes those wheels, not this skill, which only imports `cv2`.

## Note for redistributors

If you bundle NumPy or OpenCV together with this skill (for example in a container image or a packaged
app), include their license texts and notices alongside it, as their licenses require.
