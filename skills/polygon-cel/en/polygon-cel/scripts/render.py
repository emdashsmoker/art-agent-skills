#!/usr/bin/env python3
"""Render an illustration from a JSON scene spec.

Usage:
  python render.py spec.json -o out.png [--quality draft|final] [--style NAME] [--passes DIR]
  python render.py --print-defaults
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codeillust import pipeline, spec as spec_mod  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", help="scene spec JSON file")
    ap.add_argument("-o", "--out", default="illustration.png")
    ap.add_argument("--quality", choices=spec_mod.ENUMS["quality"])
    ap.add_argument("--style", choices=spec_mod.ENUMS["style"])
    ap.add_argument("--passes", help="directory for intermediate passes")
    ap.add_argument("--print-defaults", action="store_true", help="print the full default spec and exit")
    args = ap.parse_args()
    if args.print_defaults:
        print(json.dumps(spec_mod.DEFAULT_SPEC, indent=2, ensure_ascii=False))
        return 0
    if not args.spec:
        ap.error("spec file is required")
    with open(args.spec, encoding="utf-8") as f:
        user = json.load(f)
    if args.quality:
        user["quality"] = args.quality
    if args.style:
        user["style"] = args.style
    try:
        pipeline.render(user, args.out, args.passes)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
