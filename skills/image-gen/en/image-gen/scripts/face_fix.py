"""Restore faces with GFPGAN v1.3, the rest of the image stays as it was.

WHY: faces in 512px diffusion output are often soft (pupils, lashes, teeth). Restoring
     only the face keeps the pose, clothes, and background of an image the user likes.
HOW: clean architecture, upscale=1, no background upsampler. Weights are checked by
     SHA-256. The helper models of facexlib download into relative folders, so the
     work happens inside the skill cache and never leaves files in the user's folder.
"""
import common  # noqa: F401

import hashlib
import os
import sys
import time
import urllib.request
from pathlib import Path

from common import CACHE_ROOT, EXIT_INTEGRITY_FAILURE, EXIT_MISSING_DEPENDENCY, fail, log

WEIGHT_URL = "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth"
WEIGHT_SHA256 = "c953a88f2727c85c3d9ae72e2bd4846bbaf59fe6972ad94130e23e7017524a70"
FACE_DIR = CACHE_ROOT / "face"
UPSCALE = 1
ARCH = "clean"
CHANNEL_MULTIPLIER = 2
DOWNLOAD_TIMEOUT_SECONDS = 300


def ensure_weights():
    FACE_DIR.mkdir(parents=True, exist_ok=True)
    path = FACE_DIR / WEIGHT_URL.rsplit("/", 1)[-1]
    if not path.exists():
        log("downloading %s" % path.name)
        request = urllib.request.Request(WEIGHT_URL, headers={"User-Agent": "image-gen"})
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            path.write_bytes(response.read())
    if hashlib.sha256(path.read_bytes()).hexdigest() != WEIGHT_SHA256:
        path.unlink()
        fail(EXIT_INTEGRITY_FAILURE, "SHA-256 mismatch for %s, file removed" % path.name)
    return path


def restore(in_path, out_path):
    try:
        import cv2
        from gfpgan import GFPGANer
    except ImportError as error:
        fail(EXIT_MISSING_DEPENDENCY, "face restoration packages missing (%s), see references/postprocess.md" % error)
    weights = ensure_weights()
    in_path, out_path = os.path.abspath(in_path), os.path.abspath(out_path)
    os.chdir(FACE_DIR)  # WHY: relative helper-model folders are created here
    restorer = GFPGANer(model_path=str(weights), upscale=UPSCALE, arch=ARCH,
                        channel_multiplier=CHANNEL_MULTIPLIER, bg_upsampler=None, device="cpu")
    image = cv2.imread(in_path, cv2.IMREAD_COLOR)
    faces, _, output = restorer.enhance(image, has_aligned=False, only_center_face=False, paste_back=True)
    cv2.imwrite(out_path, output if output is not None else image)
    return len(faces)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: face_fix.py IN_PATH OUT_PATH")
    started = time.time()
    faces = restore(sys.argv[1], sys.argv[2])
    # WHY: zero faces is a normal result for back views and distant figures, the image is copied unchanged
    print("%s faces=%d %.1f sec" % (sys.argv[2], faces, time.time() - started))


if __name__ == "__main__":
    main()
