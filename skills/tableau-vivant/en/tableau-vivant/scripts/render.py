#!/usr/bin/env python3
"""Render a picture spec.

  python render.py spec.json -o picture.png
  python render.py spec.json -o sheet.png --styles anime,watercolor,oil     (same scene, several styles)
  python render.py spec.json -o check.png --preview                         (fast clay check of pose and framing)
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                      # noqa: E402
from atelier import spec as specs       # noqa: E402

PREVIEW_SIZE = 512


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--styles", help="comma-separated style names; renders a side-by-side sheet")
    parser.add_argument("--preview", action="store_true", help="half-size clay render for checking pose and composition")
    args = parser.parse_args()
    spec = specs.load(args.spec)
    if args.preview:
        canvas = spec.setdefault("canvas", {})
        w, h, _ = specs.canvas_size(canvas)
        scale = PREVIEW_SIZE / max(w, h)
        canvas["width"], canvas["height"], canvas["supersample"] = int(w * scale), int(h * scale), 1
    started = time.time()
    scene = specs.build_scene(spec)
    frame = scene.frame()
    if args.preview:
        image = specs.paint(frame, {}, "clay")
    elif args.styles:
        image = np.concatenate([specs.paint(frame, spec, name.strip()) for name in args.styles.split(",")], axis=1)
    else:
        image = specs.paint(frame, spec)
    specs.save(image, args.output)
    print(f"saved {args.output} ({image.shape[1]}x{image.shape[0]}) in {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
