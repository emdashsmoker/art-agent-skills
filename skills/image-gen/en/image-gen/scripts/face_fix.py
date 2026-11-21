"""Restore faces with GFPGAN v1.3, the rest of the image stays as it was.

WHY: faces in 512px diffusion output are often soft (pupils, lashes, teeth). Restoring
     only the face keeps the pose, clothes, and background of an image the user likes.
     The face detector now and then takes a body part, a garment, or a pattern for a face
     and restores it as one. Every detection is reported with its box, and --keep limits
     the restoration to the boxes the agent confirmed as faces.
HOW: clean architecture, upscale=1, no background upsampler. Weights are checked by
     SHA-256. The helper models of facexlib download into relative folders, so the
     work happens inside the skill cache and never leaves files in the user's folder.
"""
import common  # noqa: F401

import argparse
import hashlib
import json
import os
import time
import urllib.request

from common import CACHE_ROOT, EXIT_INTEGRITY_FAILURE, EXIT_MISSING_DEPENDENCY, EXIT_QUERY_OR_ARGUMENT, fail, log

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


def limit_detections(helper, keep_boxes, report):
    """Wrap the helper's detection so only confirmed faces reach alignment and paste-back."""
    detect = helper.get_face_landmarks_5

    def detect_and_limit(*args, **kwargs):
        detect(*args, **kwargs)
        kept_faces, kept_landmarks = [], []
        for face, landmarks in zip(helper.det_faces, helper.all_landmarks_5):
            box = [int(round(float(value))) for value in face[:4]]
            restored = not keep_boxes or center_inside(box, keep_boxes)
            report.append({"box": box, "score": round(float(face[4]), 3), "restored": restored})
            if restored:
                kept_faces.append(face)
                kept_landmarks.append(landmarks)
        helper.det_faces, helper.all_landmarks_5 = kept_faces, kept_landmarks
        return len(kept_faces)

    helper.get_face_landmarks_5 = detect_and_limit


def restore(in_path, out_path, keep_boxes):
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
    detections = []
    limit_detections(restorer.face_helper, keep_boxes, detections)
    image = cv2.imread(in_path, cv2.IMREAD_COLOR)
    faces, _, output = restorer.enhance(image, has_aligned=False, only_center_face=False, paste_back=True)
    cv2.imwrite(out_path, output if output is not None else image)
    return len(faces), detections


def main():
    parser = argparse.ArgumentParser(description="restore faces with GFPGAN v1.3")
    parser.add_argument("in_path")
    parser.add_argument("out_path")
    parser.add_argument("--keep", type=parse_box, action="append", default=[],
                        help="X0,Y0,X1,Y1, restore only detections whose box centre lies inside, repeatable")
    args = parser.parse_args()
    if not os.path.isfile(args.in_path):
        fail(EXIT_QUERY_OR_ARGUMENT, "input image not found: %s" % args.in_path)
    started = time.time()
    faces, detections = restore(args.in_path, args.out_path, args.keep)
    # WHY: zero faces is a normal result for back views and distant figures, the image is copied unchanged
    print(json.dumps({"path": args.out_path, "faces": faces, "detections": detections,
                      "seconds": round(time.time() - started, 1)}))


if __name__ == "__main__":
    main()
