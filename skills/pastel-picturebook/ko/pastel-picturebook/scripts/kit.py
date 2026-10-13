"""Kit: painting helpers shared by every subject (figure, still life, city, landscape).

Built on the same Scene as the portrait painter, so each helper follows the
style's shading mode (cel / soft / grain) and ink setting automatically.
"""
import cv2
import numpy as np

import relief
from patterns import apply_pattern
from raster import blur, ellipse, fill, mask_box, mix, multiply, noise, over, rgb, smooth, stroke_many, taper

# Contours shorter than this many pixels are specks, not outlines.
MIN_CONTOUR_POINTS = 24
# Every n-th contour pixel becomes a control point of the smoothed outline.
CONTOUR_STEP = 6
# Margin (px) kept around a part when shading it, so edge normals see their neighbours.
SHADE_PAD = 6


def contours(mask, level=0.5):
    """Outlines of a mask as smoothed closed paths, longest first."""
    binary = (mask > level).astype(np.uint8)
    found, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    paths = []
    for contour in sorted(found, key=len, reverse=True):
        if len(contour) < MIN_CONTOUR_POINTS:
            continue
        points = contour[::CONTOUR_STEP, 0, :].astype(np.float64)
        paths.append(smooth(points, samples=4, closed=True))
    return paths


def ink_edges(scene, mask, width, group="line", name="main", clip=None, opacity=1.0):
    """Ink the outline of a mask (no-op in lineless styles)."""
    if not scene.lines_on:
        return
    for path in contours(mask):
        scene.ink(path, width, group, name, np.ones(len(path)), opacity, clip)


def ink_tube(scene, part, width, group="line", name="main", start=0.15, end=1.0, clip=None, opacity=1.0):
    """Ink a tube's outline only between two positions along it.

    Why: a finger or limb grows out of a larger form; its outline must stop
    where it merges, or a line would cut across the join.
    """
    if not scene.lines_on:
        return
    height, width_px = scene.size
    for path in contours(part.mask):
        cols = np.clip(path[:, 0].astype(int), 0, width_px - 1)
        rows = np.clip(path[:, 1].astype(int), 0, height - 1)
        wanted = (part.along[rows, cols] >= start) & (part.along[rows, cols] <= end)
        if not wanted.all():
            # Start the closed outline at a gap, so no wanted run wraps around its end.
            first_gap = int(np.argmin(wanted))
            wanted, path = np.roll(wanted, -first_gap), np.roll(path, -first_gap, axis=0)
        breaks = np.flatnonzero(np.diff(wanted.astype(int)) != 0) + 1
        for run, run_wanted in zip(np.split(path, breaks), np.split(wanted, breaks)):
            if run_wanted[0] and len(run) > 4:
                scene.ink(run, width, group, name, taper(len(run), 0.25, 0.25), opacity, clip)


def shade_solid(scene, part, group, level=0.30, spread=0.5, gloss=0.0, shininess=40.0, extra_shadow=None, clip=None,
                seam_blur=1.2, flush=0.0):
    """Colour one relief Part: base, form shadow from its own height, optional highlight.

    `extra_shadow` adds cast shadows (0..1 field); `clip` limits where the part is painted;
    `seam_blur` (px) smooths the surface first, melting the joins of a body built from many parts;
    `flush` tints the band between light and shadow with the group's "blush" tone, as light
    passing through skin does.
    Works inside the part's bounding box only, so small parts cost little.
    """
    mask = part.mask if clip is None else part.mask * clip
    box = mask_box(mask, pad=SHADE_PAD + int(3 * seam_blur))
    if box is None:
        return mask
    height = np.ascontiguousarray(part.height[box], np.float32)
    shadow = relief.shadow_amount(height, scene.fig.light, level, spread, seam_blur)
    if extra_shadow is not None:
        shadow = np.maximum(shadow, extra_shadow[box])
    tones = scene.style["palette"][group]
    amount = scene.edge(shadow, box)
    color = mix(rgb(tones["base"]), rgb(tones["shadow"]), amount[..., None])
    if "deep" in tones:
        deep = scene.edge(np.clip(shadow * 2.0 - 1.0, 0.0, 1.0) * 0.999, box)
        color = mix(color, rgb(tones["deep"]), (deep * amount)[..., None])
    if flush > 0 and scene.shade_on:
        band = 4.0 * amount * (1.0 - amount)
        color = mix(color, rgb(tones["blush"]), (band * flush)[..., None])
    target = scene.image[box]
    target += (color - target) * mask[box][..., None]
    if "pattern" in tones:
        apply_pattern(scene, mask, group)
    if gloss > 0 and scene.shade_on:
        shine = relief.specular(height, scene.fig.light, shininess)
        shine = shine if scene.cel else blur(shine, scene.px(0.01))
        shine = scene.speckle(shine, box) if scene.mode == "grain" else shine
        target += (1.0 - target) * rgb(tones["light"]) * (shine * mask[box] * gloss)[..., None]
    return mask


def ground_shadow(scene, center, radius_x, radius_y, tone, opacity, softness=0.05, receiver=None, angle_deg=0.0):
    """Soft elliptical shadow a standing object throws on the surface under it."""
    if not scene.shade_on:
        return
    spot = fill(scene.size, ellipse(center, radius_x, radius_y, 48, angle_deg))
    spot = scene.soften(spot, softness)
    multiply(scene.image, rgb(tone), spot if receiver is None else spot * receiver, opacity)


def vertical_gradient(size, stops):
    """Image filled with a top-to-bottom colour ramp. stops = [(position 0..1, '#hex'), ...]."""
    height, width = size
    positions = np.array([stop[0] for stop in stops], np.float64)
    colors = np.array([rgb(stop[1]) for stop in stops])
    rows = np.linspace(0.0, 1.0, height)
    column = np.stack([np.interp(rows, positions, colors[:, k]) for k in range(3)], axis=1).astype(np.float32)
    return np.broadcast_to(column[:, None, :], (height, width, 3)).copy()


def ridge_line(width, base_y, amplitude, roughness, seed, octaves=6):
    """Height (y) of a jagged horizon for every x: summed noise, finer octaves weaker.

    `roughness` 0.4 = rolling hills, 0.6 = alpine crags.
    """
    rng = np.random.default_rng(seed)
    xs = np.arange(width)
    total = np.zeros(width)
    for octave in range(octaves):
        knots = 3 * 2 ** octave + 2
        values = rng.uniform(-1.0, 1.0, knots)
        total += np.interp(xs, np.linspace(0, width - 1, knots), values) * roughness ** octave
    total /= np.abs(total).max() + 1e-9
    return base_y - amplitude * (total * 0.5 + 0.5)


def below_line(size, line_y):
    """Mask of everything under a horizon given as y per x (antialiased)."""
    rows = np.arange(size[0], dtype=np.float32)[:, None]
    return np.clip(rows - np.asarray(line_y, np.float32)[None, :] + 0.5, 0.0, 1.0)


def speckle_texture(scene, mask, tone, cell, opacity, seed_offset=0):
    """Blotchy tonal variation inside a region (wood, stone, plaster, foliage)."""
    if not scene.shade_on:
        return
    cloud = noise(scene.size, cell, int(scene.fig.seed + seed_offset), 3)
    multiply(scene.image, rgb(tone), scene.soften(np.clip(cloud * 2 - 0.6, 0, 1), 0.0) * mask, opacity)


def sketch(fig):
    """Stage 1 image for any subject: every registered outline in pencil on paper."""
    image = np.empty(fig.size + (3,), np.float32)
    image[:] = rgb("#F3EEE4")
    lines = [(np.vstack([shape, shape[:1]]), 1.5) for shape in fig.shapes.values()]
    for path in fig.paths.values():
        lines += [(p, 1.5) for p in path] if isinstance(path, list) else [(path, 1.5)]
    over(image, rgb("#4B4A52"), stroke_many(fig.size, lines), 0.8)
    return image


def register(scene, name, mask):
    """Record a mask's outline in the figure so the sketch stage can show it."""
    found = contours(mask)
    if found:
        scene.fig.shapes[name] = found[0]
