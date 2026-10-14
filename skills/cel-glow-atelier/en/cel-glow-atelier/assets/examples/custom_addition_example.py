#!/usr/bin/env python3
"""Mixed mode example: rig portrait + hand-made additions (necklace, hair clip).

`scene.build` paints the portrait into layers and returns before
flattening. Additions are positioned with the portrait's own frames
(head units / body units), so they follow tilt, turn and canvas size.

Usage: python custom_addition_example.py spec.json out.png
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from paintkit import core as pk  # noqa: E402
from paintkit import scene  # noqa: E402

GOLD, GOLD_DARK, GEM = "#e9c46a", "#9a7430", "#7fd1c7"


def add_necklace(canvas: pk.Canvas, portrait) -> None:
    """Chain and pendant on the chest, in body units (not affected by head tilt)."""
    layer = canvas.layer("necklace", above="outfit")
    chain = pk.resample(portrait.body.to(pk.spline([[-0.150, 0.800], [-0.070, 0.900], [0.0, 0.935],
                                                    [0.070, 0.900], [0.150, 0.800]])), 40)
    width = portrait.px(0.0045)
    layer.paint(pk.stroke_mask(canvas.shape, (chain, width * 1.8)), GOLD_DARK, 0.6)
    layer.paint(pk.stroke_mask(canvas.shape, (chain, width)), GOLD)
    center = portrait.body.to([0.0, 0.952])
    radius = portrait.px(0.016)
    layer.paint(pk.fill_mask(canvas.shape, pk.ellipse(center[0], center[1], radius * 1.25, radius * 1.45)), GOLD_DARK)
    layer.paint(pk.fill_mask(canvas.shape, pk.ellipse(center[0], center[1], radius, radius * 1.2)), GEM)
    layer.paint(pk.fill_mask(canvas.shape, pk.ellipse(center[0] - radius * 0.3, center[1] - radius * 0.4,
                                                      radius * 0.3, radius * 0.22)), "#ffffff", 0.9)
    # Keep jewelry off the hair that hangs in front of the chest.
    layer.erase(portrait.masks["hair_sides"])


def add_hair_clip(canvas: pk.Canvas, portrait, side: int) -> None:
    """Two-bar clip on the fringe, in head units (follows tilt and turn)."""
    layer = canvas.layer("hair_clip")          # no `above`: sits on top of the hair
    for offset in (0.0, 0.022):
        bar = np.array([[0.215 * side, -0.215 + offset], [0.300 * side, -0.170 + offset]])
        path = pk.resample(portrait.head.to(bar), 12)
        layer.paint(pk.stroke_mask(canvas.shape, (path, portrait.px(0.013))), GOLD_DARK)
        layer.paint(pk.stroke_mask(canvas.shape, (path, portrait.px(0.008))), GOLD)


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    canvas, portrait = scene.build(spec)
    add_necklace(canvas, portrait)
    # Put the clip on the near side: the side the face turns away from.
    near_side = -1 if spec.get("character", {}).get("head_turn", 0.0) >= 0 else 1
    add_hair_clip(canvas, portrait, near_side)
    pk.save(scene.finish(canvas, portrait, spec), sys.argv[2])
    print(f"[ok] {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
