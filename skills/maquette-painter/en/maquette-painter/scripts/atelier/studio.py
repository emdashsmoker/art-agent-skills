"""Studio: the working loop around a scene (rough -> buffers -> final -> style sheet).

A scene script defines   build(canvas, light, brief)   and calls   studio.run(build, brief, "name.png").
The same build then serves every stage, so the rough and the final can never drift apart.

  python scene.py --rough            small fast render + 3-value check: judge composition first
  python scene.py --buffers          structure buffers: find which stage a defect comes from
  python scene.py                    final render in the brief's style, with health numbers
  python scene.py --styles a,b,c     the same picture in several styles, on one sheet
  python scene.py --out other.png --style oil --light rembrandt --scale 1.5 --seed 3

build may return {"views": [...], "light": Light, "style_params": {style: {medium parameter: value}}}:
views are checked for hands and feet, light replaces the brief's light, and style_params tunes the
medium of the named style only (a pastel paper colour, a stronger bloom) wherever that style is rendered.
"""
import argparse
import time
from pathlib import Path

import numpy as np

from . import compose, qa
from .core import save
from .media import render
from .styles import STYLES, light as make_light, paint

ROUGH_SCALE = 0.5


def _stage(build, brief, scale, light_name):
    canvas = brief.canvas()
    if scale:
        canvas = type(canvas)(canvas.width, canvas.height, scale=scale, seed=brief.seed)
    light = make_light(light_name) if light_name else brief.light()
    result = build(canvas, light, brief)
    if isinstance(result, dict) and "light" in result:
        light = result["light"]
    return canvas, light, result if isinstance(result, dict) else {}


def run(build, brief, output="picture.png", argv=None):
    """Run a scene in the mode chosen on the command line. Returns the saved path."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rough", action="store_true")
    parser.add_argument("--buffers", action="store_true")
    parser.add_argument("--styles", default="")
    parser.add_argument("--style", default="")
    parser.add_argument("--light", default="")
    parser.add_argument("--scale", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", default=output)
    args = parser.parse_args(argv)
    if args.seed is not None:
        brief.seed = args.seed
    if args.style:
        brief.style = args.style
    problems = brief.validate()
    if problems:
        raise SystemExit("brief problems:\n  " + "\n  ".join(problems))
    out = Path(args.out)
    started = time.time()

    if args.rough:
        canvas, light, _ = _stage(build, brief, args.scale or ROUGH_SCALE, args.light)
        image = render(canvas, "cel", light, bands=2)
        sheet = qa.sheet([image, compose.value_check(image), compose.guides(image)], ["rough", "3 values", "thirds"],
                         columns=3, cell_width=520)
        path = out.with_name(out.stem + "_rough.png")
    elif args.buffers:
        canvas, light, _ = _stage(build, brief, args.scale or ROUGH_SCALE, args.light)
        sheet, path = qa.buffers(canvas, light), out.with_name(out.stem + "_buffers.png")
    elif args.styles:
        names = [n.strip() for n in args.styles.split(",") if n.strip()]
        unknown = [n for n in names if n not in STYLES]
        if unknown:
            raise SystemExit(f"unknown styles {unknown}; choose from {sorted(STYLES)}")
        images = []
        for name in names:
            canvas, light, extra = _stage(build, brief, args.scale or 0.75, args.light)
            images.append(paint(canvas, name, light, params=extra.get("style_params", {}).get(name)))
        sheet, path = qa.sheet(images, names, columns=min(len(names), 3), cell_width=560), out.with_name(out.stem + "_styles.png")
    else:
        canvas, light, extra = _stage(build, brief, args.scale, args.light)
        sheet = paint(canvas, brief.style, light, params=extra.get("style_params", {}).get(brief.style),
                      extra_finish=brief.finish_passes())
        path = out
        print("image check:", qa.check_image(sheet))
        for view in extra.get("views", []):
            print("anatomy check:", qa.check_figure(view))
    save(np.clip(sheet, 0, 1), path)
    print(f"saved {path} ({time.time() - started:.1f}s)")
    return path
