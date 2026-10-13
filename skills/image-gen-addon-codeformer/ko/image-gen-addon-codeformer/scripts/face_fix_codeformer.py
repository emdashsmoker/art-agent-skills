"""Correct distorted faces with CodeFormer. A lower fidelity weight w restores symmetry more strongly.

WHY: GFPGAN sharpens soft faces but keeps misplaced eyes where they are. CodeFormer rebuilds
     the face from a learned codebook, so it also fixes asymmetry and misplaced features.
HOW: codeformer-pip downloads its weights into ./CodeFormer/weights and writes ./output/out.png
     relative to the current folder at import time, so this script moves into a folder owned by
     the image-gen cache before importing it. Inputs whose short side is under 512px are enlarged
     inside the package, the result is resized back so trim coordinates stay valid.
"""
import os
import shutil
import sys
import time
from pathlib import Path

CACHE_ROOT = Path(os.environ.get("IMAGE_GEN_HOME", str(Path.home() / ".cache" / "image-gen"))).expanduser()
WORK_DIR = CACHE_ROOT / "codeformer"
FIXED_OUTPUT = WORK_DIR / "output" / "out.png"
# WHY: 0.5 fixes most distortion and keeps the look of the person, 0.0 restores full symmetry but changes the look
DEFAULT_FIDELITY = 0.5


def restore(in_path, out_path, fidelity):
    in_path, out_path = os.path.abspath(in_path), os.path.abspath(out_path)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(WORK_DIR)
    from codeformer.app import inference_app  # WHY: import after chdir, the import itself downloads weights
    from PIL import Image

    inference_app(image=in_path, background_enhance=False, face_upsample=False, upscale=1, codeformer_fidelity=fidelity)
    shutil.copy(FIXED_OUTPUT, out_path)
    size = Image.open(in_path).size
    restored = Image.open(out_path)
    if restored.size != size:
        restored.resize(size, Image.LANCZOS).save(out_path)


def cleanup():
    """Remove only the add-on's folder inside the image-gen cache."""
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    print("removed %s" % WORK_DIR)


def main():
    if sys.argv[1:] == ["--cleanup"]:
        cleanup()
        return
    if len(sys.argv) < 3:
        sys.exit("usage: face_fix_codeformer.py IN_PATH OUT_PATH [FIDELITY 0.0-1.0] | --cleanup")
    fidelity = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_FIDELITY
    if not 0.0 <= fidelity <= 1.0:
        sys.exit("fidelity must be within 0.0-1.0")
    started = time.time()
    restore(sys.argv[1], sys.argv[2], fidelity)
    print("%s w=%.2f %.1f sec" % (sys.argv[2], fidelity, time.time() - started))


if __name__ == "__main__":
    main()
