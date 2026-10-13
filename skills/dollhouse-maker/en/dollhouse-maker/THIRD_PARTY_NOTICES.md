# Third-Party Notices

## dollhouse-maker license

- dollhouse-maker is distributed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
- The full license text is in the top-level LICENSE file.
- The copyright notice and the additional permission for generated images are in the top-level NOTICE.md file.
- This repository contains only original source code and documentation. It does not bundle or redistribute any third-party code, binaries, fonts or images.

## Dependencies

- Users install the packages below separately through `scripts/requirements.txt`. Each package stays under its own license.
- Every license listed below is compatible with GPL-3.0.

| Package | Required version | License | Components included in the published wheels | Project |
|---|---|---|---|---|
| NumPy | >=1.24 | BSD-3-Clause | Source components under 0BSD, MIT, Zlib and CC0-1.0; OpenBLAS and LAPACK (BSD family), GCC runtime library (GPL-3.0-or-later WITH GCC-exception-3.1), libquadmath (LGPL-2.1-or-later) | https://numpy.org |
| SciPy | >=1.10 | BSD-3-Clause | OpenBLAS and LAPACK (BSD family), GCC runtime library (GPL-3.0-or-later WITH GCC-exception-3.1), libquadmath (LGPL-2.1-or-later) | https://scipy.org |
| opencv-python-headless | >=4.8 | Apache-2.0 for OpenCV itself, MIT for the packaging scripts | FFmpeg binaries (LGPL-2.1) | https://opencv.org, https://github.com/opencv/opencv-python |

## Finding the full license texts

- Each package ships its license texts in the `*.dist-info` directory of its install location.
- `pip show -f numpy scipy opencv-python-headless` lists where those files are.
- This notice was written in October 2026 from the install metadata of numpy 2.5.3, scipy 1.18.1 and opencv-python-headless 5.0.0.93.
