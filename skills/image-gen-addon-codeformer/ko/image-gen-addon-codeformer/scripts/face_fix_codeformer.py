"""Correct distorted faces with CodeFormer. A lower fidelity weight w restores symmetry more strongly.

WHY: GFPGAN sharpens soft faces but keeps misplaced eyes where they are. CodeFormer rebuilds
     the face from a learned codebook, so it also fixes asymmetry and misplaced features.
     Its detector accepts lower-confidence faces than image-gen's path, so a body part, a garment,
     or a pattern is now and then restored as a face. Every detection is reported with its box in
     input pixels, and --keep limits the restoration to the boxes the agent confirmed as faces.
HOW: codeformer-pip downloads its weights into ./CodeFormer/weights and writes ./output/out.png
     relative to the current folder at import time, so this script moves into a folder owned by
     the image-gen cache before importing it. Its face helper loads the detection and parsing
     weights again from a folder inside the installed package, so the helper's base folder is
     pointed at the same cache folder first. Inputs whose short side is under 512px are enlarged
     inside the package, the result is resized back so trim coordinates stay valid.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path

CACHE_ROOT = Path(os.environ.get("IMAGE_GEN_HOME", str(Path.home() / ".cache" / "image-gen"))).expanduser()
WORK_DIR = CACHE_ROOT / "codeformer"
FIXED_OUTPUT = WORK_DIR / "output" / "out.png"
# WHY: app.py saves into ./CodeFormer/weights, the face helper reads <ROOT_DIR>/weights, one folder serves both
HELPER_ROOT = WORK_DIR / "CodeFormer"
# WHY: same meaning as image-gen's exit codes, so its failure table applies to this add-on too
EXIT_QUERY_OR_ARGUMENT = 2
EXIT_MISSING_DEPENDENCY = 4
# WHY: 0.5 fixes most distortion and keeps the look of the person, 0.0 restores full symmetry but changes the look
DEFAULT_FIDELITY = 0.5


def argument_error(message):
    sys.stderr.write(message + "\n")
    sys.exit(EXIT_QUERY_OR_ARGUMENT)


def parse_fidelity(text):
    try:
        fidelity = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError("fidelity must be a number within 0.0-1.0")
    if not 0.0 <= fidelity <= 1.0:
        raise argparse.ArgumentTypeError("fidelity must be within 0.0-1.0")
    return fidelity


def parse_box(text):
    try:
        x0, y0, x1, y1 = (int(value) for value in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("box must be X0,Y0,X1,Y1 in pixels")
    if x1 <= x0 or y1 <= y0:
        raise argparse.ArgumentTypeError("box must satisfy X0<X1 and Y0<Y1")
    return x0, y0, x1, y1


def center_inside(box, keep_boxes):
    center_x, center_y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return any(x0 <= center_x <= x1 and y0 <= center_y <= y1 for x0, y0, x1, y1 in keep_boxes)


def limit_detections(helper_class, input_width, keep_boxes, report):
    """Wrap the helper's detection so only confirmed faces reach alignment and paste-back."""
    detect = helper_class.get_face_landmarks_5

    def detect_and_limit(helper, *args, **kwargs):
        detect(helper, *args, **kwargs)
        # WHY: the helper may have enlarged the input, boxes are reported in the caller's pixels
        scale = helper.input_img.shape[1] / input_width
        # WHY: the helper divides the whole detection row by its detection resize factor, score included
        resize = kwargs.get("resize")
        score_factor = max(1.0, resize / min(helper.input_img.shape[:2])) if resize else 1.0
        kept_faces, kept_landmarks = [], []
        for face, landmarks in zip(helper.det_faces, helper.all_landmarks_5):
            box = [int(round(float(value) / scale)) for value in face[:4]]
            restored = not keep_boxes or center_inside(box, keep_boxes)
            report.append({"box": box, "score": round(float(face[4]) * score_factor, 3), "restored": restored})
            if restored:
                kept_faces.append(face)
                kept_landmarks.append(landmarks)
        helper.det_faces, helper.all_landmarks_5 = kept_faces, kept_landmarks
        return len(kept_faces)

    helper_class.get_face_landmarks_5 = detect_and_limit


def restore(in_path, out_path, fidelity, keep_boxes):
    in_path, out_path = os.path.abspath(in_path), os.path.abspath(out_path)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(WORK_DIR)
    # WHY: find_spec checks the install without importing, the import itself downloads weights
    if importlib.util.find_spec("codeformer") is None:
        sys.stderr.write("codeformer-pip is not installed, see the installation section of SKILL.md\n")
        sys.exit(EXIT_MISSING_DEPENDENCY)
    import codeformer.facelib.utils.misc as helper_misc

    # WHY: without this the helper downloads the same 186MB again into the package folder,
    #      where neither --cleanup nor image-gen's cache.py can reach it
    helper_misc.ROOT_DIR = str(HELPER_ROOT)
    from codeformer.facelib.utils.face_restoration_helper import FaceRestoreHelper
    from PIL import Image

    size = Image.open(in_path).size
    detections = []
    limit_detections(FaceRestoreHelper, size[0], keep_boxes, detections)
    from codeformer.app import inference_app  # WHY: import after chdir, the import itself downloads weights

    inference_app(image=in_path, background_enhance=False, face_upsample=False, upscale=1, codeformer_fidelity=fidelity)
    shutil.copy(FIXED_OUTPUT, out_path)
    restored = Image.open(out_path)
    if restored.size != size:
        restored.resize(size, Image.LANCZOS).save(out_path)
    return detections


def cleanup():
    """Remove only the add-on's folder inside the image-gen cache."""
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    print("removed %s" % WORK_DIR)


def main():
    if sys.argv[1:] == ["--cleanup"]:
        cleanup()
        return
    parser = argparse.ArgumentParser(description="restore faces with CodeFormer, or remove its cache folder with --cleanup")
    parser.add_argument("in_path")
    parser.add_argument("out_path")
    parser.add_argument("fidelity", nargs="?", type=parse_fidelity, default=DEFAULT_FIDELITY, help="w within 0.0-1.0")
    parser.add_argument("--keep", type=parse_box, action="append", default=[],
                        help="X0,Y0,X1,Y1, restore only detections whose box centre lies inside, repeatable")
    args = parser.parse_args()  # WHY: argparse exits with 2 on a bad argument, the same code as image-gen
    if not os.path.isfile(args.in_path):
        argument_error("input image not found: %s" % args.in_path)
    started = time.time()
    detections = restore(args.in_path, args.out_path, args.fidelity, args.keep)
    # WHY: the package prints its own progress lines, the result stays on the last line
    print(json.dumps({"path": args.out_path, "w": args.fidelity,
                      "faces": sum(1 for item in detections if item["restored"]), "detections": detections,
                      "seconds": round(time.time() - started, 1)}))


if __name__ == "__main__":
    main()
