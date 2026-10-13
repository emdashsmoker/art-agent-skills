"""CLI: JSON spec -> finished PNG (and optional process stages).

Usage:
    python render.py --spec my_spec.json --out portrait.png
    python render.py --spec my_spec.json --out portrait.png --stages stages_dir
    python render.py --out default.png --style oil          # default spec, override style

Pipeline (mirrors a painter's process):
    plan (spec) -> construction (guides) -> line art -> flat colors
    -> shading (form + cast + designed shadows) -> highlights -> style post-process
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import character  # noqa: E402
import config     # noqa: E402
import looks      # noqa: E402
import painterly  # noqa: E402
import raster     # noqa: E402
import styles     # noqa: E402
from scene import Resolver  # noqa: E402

STYLE_RENDERERS = {
    'anime': styles.render_anime,
    'illustration': styles.render_illustration,
    'oil': painterly.render_oil,
    'watercolor': painterly.render_watercolor,
}
GUIDE_COLOR = (0.35, 0.55, 0.85)
SHEET_THUMB_WIDTH = 384


def load_spec(path, style=None):
    user = {}
    if path:
        with open(path, encoding='utf-8') as f:
            user = json.load(f)
    base = config.deep_merge(config.DEFAULT_SPEC, config.preset_defaults(user))
    spec = config.deep_merge(base, user, warn=lambda m: print(f"[spec] warning: {m}", file=sys.stderr))
    if style:
        spec['style'] = style
    if spec['style'] not in STYLE_RENDERERS:
        raise ValueError(f"unknown style '{spec['style']}' (use {', '.join(STYLE_RENDERERS)})")
    return spec


def resolve_layers(spec):
    drawables, guides, pal, head = character.build_scene(spec)
    w, h = spec['canvas']['width'], spec['canvas']['height']
    light = styles.light_vector(spec)
    dist = spec['light']['cast_distance'] * head.unit
    offset = (-light[0] / np.hypot(light[0], light[1]) * dist, -light[1] / np.hypot(light[0], light[1]) * dist)
    layers = Resolver(w, h, offset).resolve(drawables, pal['background'][1])
    layers.guides = guides
    layers.unit = head.unit
    layers.kind = 'scene' if spec['subject'] in character.SCENES else 'figure'
    return layers, pal


def paint(layers, spec, pal):
    """Finished image: the style renderer, then the spec's color grade (look)."""
    return looks.apply_look(STYLE_RENDERERS[spec['style']](layers, spec, pal), spec)


def construction_image(layers):
    h, w = layers.flat.shape[:2]
    img = np.ones((h, w, 3), np.float32)
    canvas = (img * 255).astype(np.uint8)
    color = tuple(int(c * 255) for c in GUIDE_COLOR)
    for g in layers.guides:
        pts = np.round(np.asarray(g) * 16).astype(np.int32)
        cv2.polylines(canvas, [pts], False, color, 2, lineType=cv2.LINE_AA, shift=4)
    img = canvas.astype(np.float32) / 255
    sketch = layers.line_a[..., None] * 0.35
    return img * (1 - sketch) + np.array([0.3, 0.3, 0.35]) * sketch


def stage_images(layers, spec, pal, final):
    white = np.ones_like(layers.flat)
    line_only = styles.apply_lines(white, layers)
    for g in ('lash', 'brow'):          # solid ink shapes belong to the line art stage
        if g in layers.groups:
            line_only = line_only * (1 - layers.groups[g][..., None]) + layers.flat * layers.groups[g][..., None]
    flats = styles.apply_lines(layers.flat, layers)
    light = styles.light_vector(spec)
    lam = styles.lambert(layers, light)
    s, _ = styles.shadow_amount_cel(layers, lam, spec)
    shaded = styles.apply_lines(styles.multiply_shadow(layers.flat, styles.tint_map(layers, spec), s), layers)
    return [('1_construction', construction_image(layers)), ('2_lineart', line_only),
            ('3_flats', flats), ('4_shading', shaded), ('5_final', final)]


def save_sheet(stages, path):
    thumbs = []
    for _, img in stages:
        h, w = img.shape[:2]
        tw = SHEET_THUMB_WIDTH
        thumbs.append(cv2.resize(img, (tw, int(h * tw / w)), interpolation=cv2.INTER_AREA))
    gap = np.ones((thumbs[0].shape[0], 12, 3), np.float32)
    row = thumbs[0]
    for t in thumbs[1:]:
        row = np.hstack([row, gap, t])
    raster.save_png(path, row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--spec', help='JSON spec (fields override config.DEFAULT_SPEC)')
    ap.add_argument('--out', required=True, help='output PNG path')
    ap.add_argument('--style', help='override spec style: ' + ', '.join(STYLE_RENDERERS))
    ap.add_argument('--stages', help='directory for process stage images and a process sheet')
    args = ap.parse_args()

    t0 = time.time()
    spec = load_spec(args.spec, args.style)
    layers, pal = resolve_layers(spec)
    t1 = time.time()
    final = paint(layers, spec, pal)
    raster.save_png(args.out, final)
    print(f"[render] style={spec['style']} layers={t1 - t0:.1f}s style={time.time() - t1:.1f}s -> {args.out}")
    if args.stages:
        out_dir = Path(args.stages)
        out_dir.mkdir(parents=True, exist_ok=True)
        stages = stage_images(layers, spec, pal, final)
        for name, img in stages:
            raster.save_png(out_dir / f'{name}.png', img)
        save_sheet(stages, out_dir / 'process_sheet.png')
        print(f"[render] stages -> {out_dir}")


if __name__ == '__main__':
    main()
