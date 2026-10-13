"""Entry point a scene script calls: canvas -> compose -> finish -> file."""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

from . import finish
from . import grade as grading
from .canvas import Canvas
from .config import (CANVAS_UNITS_HEIGHT, CANVAS_UNITS_WIDTH, DEFAULT_LIGHT, DEFAULT_SEED,
                     FINAL_PX_PER_UNIT, PREVIEW_PX_PER_UNIT, STYLES, StyleName)
from .painter import Painter

REVIEW_MAX_SIDE_PX = 1000     # review images stay small enough to look at quickly
REVIEW_CROP_MARGIN = 0.18     # share of the part size added around a close-up
REVIEW_PARTS = ("face",)      # parts that get a full-resolution close-up
NO_GRADE = "none"


def render(compose, style, output_path, px_per_unit=FINAL_PX_PER_UNIT, seed=DEFAULT_SEED,
           light=DEFAULT_LIGHT, units_size=(CANVAS_UNITS_WIDTH, CANVAS_UNITS_HEIGHT),
           finishing=True, review=False, grade=None):
    """compose(painter) draws the scene back to front. Same inputs give the same file.

    grade: a colour grade (grade.GRADES name or grade.Grade) laid over the finished style.
    review=True also writes '<name>_overview.png' and one close-up per part in
    REVIEW_PARTS, so the result can be inspected by eye before it is delivered.
    """
    style = STYLES[StyleName(style)]
    canvas = Canvas(units_size[0], units_size[1], px_per_unit, seed)
    painter = Painter(canvas, style, light)
    compose(painter)
    if finishing:
        finish.apply(canvas, style, painter.light)
    for overlay in canvas.overlays:
        overlay(canvas)
    if finishing and grade is not None:
        grading.apply(canvas, grade)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    if review:
        write_review_views(canvas, output_path)
    return canvas


def run_cli(scene_name, compose, units_size=(CANVAS_UNITS_WIDTH, CANVAS_UNITS_HEIGHT), light=DEFAULT_LIGHT,
            description=None, grade=None):
    """Command line shared by every scene script: --style, --grade, --out, --preview, --seed.
    grade is the scene's default colour grade; --grade none turns it off."""
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--style", default="all", choices=[s.value for s in StyleName] + ["all"])
    parser.add_argument("--grade", default=grade or NO_GRADE, choices=[NO_GRADE] + list(grading.GRADES))
    parser.add_argument("--out", default="out", help="output directory")
    parser.add_argument("--preview", action="store_true", help="half-size render for the look-and-fix loop")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--no-review", action="store_true", help="skip the overview and close-up images")
    args = parser.parse_args()

    styles = [s.value for s in StyleName] if args.style == "all" else [args.style]
    px_per_unit = PREVIEW_PX_PER_UNIT if args.preview else FINAL_PX_PER_UNIT
    suffix = "_preview" if args.preview else ""
    for style in styles:
        started = time.time()
        path = Path(args.out) / f"{scene_name}_{style}{suffix}.png"
        render(compose, style, path, px_per_unit=px_per_unit, seed=args.seed, light=light,
               units_size=units_size, review=not args.no_review, grade=None if args.grade == NO_GRADE else args.grade)
        print(f"{path}  ({time.time() - started:.1f}s)")


def write_review_views(canvas, output_path):
    """Overview plus close-ups. Returns the written paths."""
    image = cv2.cvtColor(canvas.to_uint8(), cv2.COLOR_RGB2BGR)
    written = [_write_limited(image, output_path.with_name(output_path.stem + "_overview.png"))]
    for name in REVIEW_PARTS:
        region = _part_box(canvas.part(name))
        if region is not None:
            written.append(_write_limited(image[region], output_path.with_name(f"{output_path.stem}_{name}.png")))
    return written


def _part_box(mask):
    rows = np.flatnonzero(mask.max(axis=1) > 0.5)
    cols = np.flatnonzero(mask.max(axis=0) > 0.5)
    if rows.size == 0 or cols.size == 0:
        return None
    margin_y = int((rows[-1] - rows[0]) * REVIEW_CROP_MARGIN)
    margin_x = int((cols[-1] - cols[0]) * REVIEW_CROP_MARGIN)
    return (slice(max(0, rows[0] - margin_y), min(mask.shape[0], rows[-1] + margin_y)),
            slice(max(0, cols[0] - margin_x), min(mask.shape[1], cols[-1] + margin_x)))


def _write_limited(image, path):
    longest = max(image.shape[:2])
    if longest > REVIEW_MAX_SIDE_PX:
        scale = REVIEW_MAX_SIDE_PX / longest
        size = (int(image.shape[1] * scale), int(image.shape[0] * scale))
        image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    if not cv2.imwrite(str(path), image):
        raise IOError(f"could not write image: {path}")
    return path
