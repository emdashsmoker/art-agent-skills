# Third-Party Notices

This skill is licensed under the GNU General Public License, version 3 or (at your option) any later version (SPDX: `GPL-3.0-or-later`). The full license text is in `LICENSE`. The copyright notice and an additional permission that frees the images you generate are in `NOTICE.md`.

## Bundled third-party material

None. The skill ships no third-party code, fonts, textures, photographs or datasets. The picture in `assets/gallery.jpg` was rendered by the skill's own engine.

## Runtime dependencies (not bundled)

The engine imports the packages below at run time. They are not included in this skill. Users install them separately, for example with `pip install numpy opencv-python-headless scipy skia-python`.

Each package is distributed under its own license. The table summarises the licenses found in the package metadata and license files of the versions this skill was tested with. The license files shipped inside each installed package are the authoritative source.

| Package | Tested version | License | Project |
|---|---|---|---|
| NumPy (`numpy`) | 2.5.3 | BSD-3-Clause, with bundled components under 0BSD, MIT, Zlib and CC0-1.0 | https://github.com/numpy/numpy |
| SciPy (`scipy`) | 1.18.1 | BSD-3-Clause, with bundled components under the licenses listed in the package's license files | https://github.com/scipy/scipy |
| OpenCV (`opencv-python-headless`) | 5.0.0.93 | Apache-2.0 for OpenCV and MIT for the opencv-python packaging. The wheel also redistributes FFmpeg under the GNU LGPL version 2.1 and other libraries listed in its `LICENSE-3RD-PARTY.txt` | https://github.com/opencv/opencv-python |
| skia-python (`skia-python`) | 144.0.post2 | BSD-3-Clause for the binding and for the Skia library it wraps | https://github.com/kyamagu/skia-python |
