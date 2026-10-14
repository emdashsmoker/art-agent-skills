#!/usr/bin/env python3
"""Render a picture (bust portrait, full-body figure or scenery) from a JSON scene spec.

Usage:
    python render.py spec.json out.png [--stages sheet.png] [--preview preview.jpg]

--stages  also writes a 4-panel process sheet (guide, flats, shading, final).
--preview also writes a half-size JPEG, convenient for quick visual checks.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paintkit import core as pk  # noqa: E402
from paintkit import scene  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", help="scene spec JSON file")
    parser.add_argument("out", help="output image path (.png)")
    parser.add_argument("--stages", help="optional path for the process sheet")
    parser.add_argument("--preview", help="optional path for a half-size preview")
    args = parser.parse_args()

    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"[error] cannot read spec '{args.spec}': {error}", file=sys.stderr)
        return 2

    started = time.time()
    try:
        canvas, portrait = scene.build(spec)
        image = scene.finish(canvas, portrait, spec)
    except ValueError as error:           # misspelled keys / unknown option names
        print(f"[error] invalid spec: {error}", file=sys.stderr)
        return 2
    pk.save(image, args.out)
    print(f"[ok] {args.out}  style={spec.get('style', 'anime')}  {time.time() - started:.1f}s")
    if args.preview:
        pk.save(image[::2, ::2], args.preview)
        print(f"[ok] {args.preview}")
    if args.stages:
        pk.save(scene.process_sheet(spec), args.stages)
        print(f"[ok] {args.stages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
