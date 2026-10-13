"""paintkit.urban: post-Soviet residential scenery for the doomer look.

Prefab panel apartment blocks, power lines, street lamps, snow, fog bands and
leafless trees. Like scenery.py, every builder paints onto one Layer and takes
positions and sizes as fractions of the canvas (x of the width, y and sizes of
the height), so the ops plug into a spec's `background` and `foreground`.

The look rests on one contrast: a cold, repetitive grid (window rows, panel
seams, wires) against a few small warm lights (lit windows, sodium lamps).
"""
from __future__ import annotations

import numpy as np

from . import core as pk
from . import light as lt

OPS = ("panel_blocks", "power_lines", "streetlamp", "snow", "fog", "bare_tree")
DEFAULT_LIGHT = lt.light_vector(140.0, 30.0)

# -- panel blocks ---------------------------------------------------------------
# wall: concrete; seam: panel joints; glass: dark window; lit: share of windows with light on;
# lit_colors: warm lamps with an occasional cold TV glow; haze: what distance fades toward.
BLOCK_TIMES = {
    "day": dict(wall="#b8b7b0", seam="#8e8d87", glass="#5f6b78", lit=0.0,
                lit_colors=("#d6d2c4",), haze="#c8ccd2", glow=0.0),
    "dusk": dict(wall="#7a7c88", seam="#5a5c68", glass="#262a38", lit=0.32,
                 lit_colors=("#f2c66b", "#ffb35a", "#efd9a0", "#f2c66b", "#8fb4e0"), haze="#8f8798", glow=0.35),
    "night": dict(wall="#363a48", seam="#262934", glass="#12151e", lit=0.28,
                  lit_colors=("#f2c66b", "#ffb35a", "#efd9a0", "#f2c66b", "#7fa6d8"), haze="#1c2030", glow=0.55),
}
WINDOW_W, WINDOW_H = 0.46, 0.46        # window size in bay width and floor height
BALCONY_SHARE = 0.30                   # share of bay columns with balconies
GLAZED_SHARE = 0.45                    # share of balconies closed in with glass
ENTRANCE_EVERY = 6                     # bays between entrance doors
ANTENNA_COUNT = 3
SIDE_WINDOW_COLUMNS = 3
SIDE_MAX_REACH = 0.8                   # share of the way to the vanishing point a side wall may span


def _quad_point(quad, u, v) -> np.ndarray:
    """Bilinear point in a quad given as (top-left, top-right, bottom-right, bottom-left)."""
    tl, tr, br, bl = (np.asarray(p, np.float32) for p in quad)
    top = tl + (tr - tl) * u
    bottom = bl + (br - bl) * u
    return top + (bottom - top) * v


def _quad_rect(quad, u0, v0, u1, v1) -> np.ndarray:
    return np.array([_quad_point(quad, u0, v0), _quad_point(quad, u1, v0), _quad_point(quad, u1, v1),
                     _quad_point(quad, u0, v1)], np.float32)


def _fade(color, haze_color, amount: float) -> np.ndarray:
    return pk.mix(color, haze_color, float(np.clip(amount, 0.0, 1.0)))


def _facade(layer, quad, floors: int, bays: int, tone: dict, haze: float, lit: float, rng, shade: float,
            balconies: bool, entrances: bool):
    """Windows, seams, balconies and stains on one wall given as a quad."""
    shape = layer.a.shape
    haze_color = tone["haze"]
    wall = _fade(pk.adjust(tone["wall"], value=shade), haze_color, haze)
    seam = _fade(pk.adjust(tone["seam"], value=shade), haze_color, haze)
    glass = _fade(tone["glass"], haze_color, haze)
    face = pk.fill_mask(shape, [quad])
    layer.paint(face, wall)
    # Weathering: dark streaks run down from the roof and under the balconies.
    streaks = pk.noise(shape, max(shape[0] * 0.01, 2.0), seed=int(rng.integers(1 << 30)), octaves=2)
    streaks = pk.blur(streaks, 1.0) * pk.noise(shape, shape[0] * 0.08, seed=int(rng.integers(1 << 30)), octaves=1)
    layer.paint(face * pk.smoothstep(0.35, 0.75, streaks), pk.adjust(wall, value=0.82), 0.35 * (1.0 - haze))
    joints = []
    for f in range(1, floors):
        joints.append((np.array([_quad_point(quad, 0.0, f / floors), _quad_point(quad, 1.0, f / floors)]), 1.0))
    for b in range(0, bays + 1, 2):
        joints.append((np.array([_quad_point(quad, b / bays, 0.0), _quad_point(quad, b / bays, 1.0)]), 1.0))
    width = max(shape[0] * 0.0012, 0.8)
    layer.paint(pk.stroke_mask(shape, [(pk.resample(p, 8), width) for p, _ in joints]) * face, seam, 0.6)
    dark, lit_groups, glow = [], {}, []
    colors = tone["lit_colors"]
    balcony_cols = set()
    if balconies:
        for b in range(bays):
            if rng.random() < BALCONY_SHARE:
                balcony_cols.add(b)
    slabs, glazed, rails = [], [], []
    for f in range(floors):
        for b in range(bays):
            u0, u1 = (b + 0.5 - WINDOW_W / 2) / bays, (b + 0.5 + WINDOW_W / 2) / bays
            v0, v1 = (f + 0.22) / floors, (f + 0.22 + WINDOW_H) / floors
            if entrances and f == floors - 1 and b % ENTRANCE_EVERY == ENTRANCE_EVERY // 2:
                continue                                  # the entrance door takes this window's place
            rect = _quad_rect(quad, u0, v0, u1, v1)
            if rng.random() < lit:
                key = int(rng.integers(len(colors)))
                lit_groups.setdefault(key, []).append(rect)
                glow.append(rect)
            else:
                dark.append(rect)
            if b in balcony_cols and f < floors - 1:
                bu0, bu1 = (b + 0.08) / bays, (b + 0.92) / bays
                front = _quad_rect(quad, bu0, (f + 0.62) / floors, bu1, (f + 1.0) / floors)
                (glazed if rng.random() < GLAZED_SHARE else slabs).append(front)
                rails.append(np.array([_quad_point(quad, bu0, (f + 1.0) / floors),
                                       _quad_point(quad, bu1, (f + 1.0) / floors)]))
    if dark:
        layer.paint(pk.fill_mask(shape, dark), glass)
    for key, rects in lit_groups.items():
        layer.paint(pk.fill_mask(shape, rects), _fade(colors[key], haze_color, haze * 0.45))
    if glow and tone["glow"] > 0:
        # Lit windows bleed into the night air around them.
        halo = pk.blur(pk.fill_mask(shape, glow), max(shape[0] * 0.006, 1.5))
        layer.paint(halo, _fade(colors[0], haze_color, haze * 0.45), tone["glow"] * 0.5)
    if slabs:
        layer.paint(pk.fill_mask(shape, slabs), _fade(pk.adjust(tone["wall"], value=shade * 0.9), haze_color, haze))
    if glazed:
        layer.paint(pk.fill_mask(shape, glazed), _fade(pk.mix(tone["glass"], "#9aa8b8", 0.35), haze_color, haze))
    if rails:
        layer.paint(pk.stroke_mask(shape, [(pk.resample(r, 6), width * 1.4) for r in rails]),
                    _fade(pk.adjust(tone["seam"], value=0.7), haze_color, haze), 0.8)
    if entrances:
        doors, lamps = [], []
        for b in range(ENTRANCE_EVERY // 2, bays, ENTRANCE_EVERY):
            doors.append(_quad_rect(quad, (b + 0.18) / bays, (floors - 0.62) / floors, (b + 0.82) / bays, 1.0))
            canopy = _quad_rect(quad, (b - 0.05) / bays, (floors - 0.72) / floors, (b + 1.05) / bays,
                                (floors - 0.64) / floors)
            doors.append(canopy)
            lamps.append(_quad_point(quad, (b + 0.5) / bays, (floors - 0.78) / floors))
        layer.paint(pk.fill_mask(shape, doors), _fade(pk.adjust(tone["seam"], value=0.6), haze_color, haze))
        if tone["glow"] > 0:
            radius = max(shape[0] * 0.012, 3.0)
            for point in lamps:
                layer.paint(pk.radial_ramp(shape, point, radius), _fade(colors[0], haze_color, haze * 0.4), 0.9)
    return face


def panel_blocks(layer: pk.Layer, blocks=None, time: str = "night", vanish=(0.5, 0.45), light=None,
                 seed: int = 0) -> np.ndarray:
    """Prefab apartment blocks, listed far to near. Each block:
    x [left, right] of the front wall, base (ground line), top (roof line), floors, bays (window
    columns, default from the proportions), side (width of a side wall receding toward `vanish`,
    signed: + shows the right side, - the left), haze (0 near, 1 lost in the distance), lit
    (share of lit windows, default by `time`), balconies and entrances (true/false)."""
    if time not in BLOCK_TIMES:
        raise ValueError(f"unknown panel_blocks time '{time}', expected one of {list(BLOCK_TIMES)}")
    tone = BLOCK_TIMES[time]
    light = DEFAULT_LIGHT if light is None else np.asarray(light, np.float32)
    height, width = layer.a.shape
    rng = np.random.default_rng(seed)
    vx, vy = vanish[0] * width, vanish[1] * height
    allowed = {"x", "base", "top", "floors", "bays", "side", "haze", "lit", "balconies", "entrances"}
    blocks = blocks or [{"x": [0.2, 0.8], "base": 0.75, "top": 0.25}]
    union = np.zeros(layer.a.shape, np.float32)
    for block in blocks:
        unknown = set(block) - allowed
        if unknown:
            raise ValueError(f"unknown panel_blocks block keys {sorted(unknown)}; allowed: {sorted(allowed)}")
        x0, x1 = block["x"][0] * width, block["x"][1] * width
        base, top = block["base"] * height, block["top"] * height
        floors = int(block.get("floors", 9))
        floor_h = (base - top) / floors
        bays = int(block.get("bays", max(round((x1 - x0) / (floor_h * 1.15)), 2)))
        haze = float(block.get("haze", 0.0))
        lit = float(block.get("lit", tone["lit"]))
        # Walls facing the light are brighter; the front wall faces the viewer.
        front_shade = 0.80 + 0.20 * max(float(light[2]), 0.0)
        side = float(block.get("side", 0.0))
        if side:
            near_x = x1 if side > 0 else x0
            # A side wall seen in perspective never reaches past the vanishing point.
            far_x = near_x + float(np.clip(side * width, -abs(vx - near_x) * SIDE_MAX_REACH,
                                           abs(vx - near_x) * SIDE_MAX_REACH))

            def toward(y, x):            # the side wall's edges run toward the vanishing point
                t = (x - near_x) / ((vx - near_x) or 1.0)
                return y + (vy - y) * t
            quad = [(near_x, top), (far_x, toward(top, far_x)), (far_x, toward(base, far_x)), (near_x, base)]
            if side < 0:
                quad = [quad[1], quad[0], quad[3], quad[2]]
            facing = np.sign(side) * float(light[0])
            side_shade = 0.62 + 0.30 * max(facing, 0.0)
            union = np.maximum(union, _facade(layer, quad, floors, SIDE_WINDOW_COLUMNS, tone, haze, lit, rng,
                                              side_shade, False, False))
        quad = [(x0, top), (x1, top), (x1, base), (x0, base)]
        union = np.maximum(union, _facade(layer, quad, floors, bays, tone, haze, lit, rng, front_shade,
                                          block.get("balconies", True), block.get("entrances", True)))
        # Roof: a darker parapet and a few antennas against the sky.
        parapet = np.array([[x0, top - floor_h * 0.12], [x1, top - floor_h * 0.12], [x1, top], [x0, top]])
        layer.paint(pk.fill_mask(layer.a.shape, [parapet]), _fade(pk.adjust(tone["seam"], value=0.8), tone["haze"],
                                                                  haze))
        masts = []
        for _ in range(ANTENNA_COUNT):
            ax = rng.uniform(x0 + (x1 - x0) * 0.1, x1 - (x1 - x0) * 0.1)
            tall = floor_h * rng.uniform(0.8, 1.6)
            masts.append((np.array([[ax, top - floor_h * 0.1], [ax, top - tall]]), 1.0))
            bar = floor_h * rng.uniform(0.25, 0.45)
            masts.append((np.array([[ax - bar, top - tall * 0.8], [ax + bar, top - tall * 0.8]]), 1.0))
        layer.paint(pk.stroke_mask(layer.a.shape, [(pk.resample(p, 6), max(height * 0.0012, 0.8)) for p, _ in masts]),
                    _fade(tone["seam"], tone["haze"], haze), 0.9)
    return union


# -- power lines ------------------------------------------------------------------
POLE_KINDS = ("wood", "pylon")
WIRE_SAG = 0.06                        # sag at mid span, in share of the span length


def _pole_shape(kind: str, x, base, tall) -> tuple:
    """(strokes [(path, width)], attachment points) of one pole in pixels."""
    if kind == "wood":
        top = base - tall
        arm = tall * 0.14
        strokes = [(np.array([[x, base], [x, top]]), tall * 0.022),
                   (np.array([[x - arm, top + tall * 0.05], [x + arm, top + tall * 0.05]]), tall * 0.014)]
        points = [(x - arm * 0.85, top + tall * 0.04), (x, top + tall * 0.04), (x + arm * 0.85, top + tall * 0.04)]
        return strokes, points
    # Lattice pylon: tapered legs, cross bracing and two cross arms.
    half_base, half_top = tall * 0.11, tall * 0.025
    top = base - tall
    legs = [np.array([[x - half_base, base], [x - half_top, top]]), np.array([[x + half_base, base], [x + half_top, top]])]
    strokes = [(leg, tall * 0.008) for leg in legs]
    levels = np.linspace(0.0, 1.0, 7)
    for a, b in zip(levels[:-1], levels[1:]):
        la, lb = (legs[0][0] + (legs[0][1] - legs[0][0]) * t for t in (a, b))
        ra, rb = (legs[1][0] + (legs[1][1] - legs[1][0]) * t for t in (a, b))
        strokes += [(np.array([la, rb]), tall * 0.004), (np.array([ra, lb]), tall * 0.004),
                    (np.array([lb, rb]), tall * 0.004)]
    points = []
    for level, span in ((0.70, 0.30), (0.88, 0.22)):
        y = base - tall * level
        strokes.append((np.array([[x - span * tall, y], [x + span * tall, y]]), tall * 0.008))
        for side in (-1.0, 1.0):          # insulator strings hang from the arm ends
            end = np.array([x + side * span * tall * 0.9, y])
            strokes.append((np.array([end, end + [0.0, tall * 0.05]]), tall * 0.006))
            points.append((end[0], end[1] + tall * 0.05))
    return strokes, points


def power_lines(layer: pk.Layer, poles=None, kind: str = "wood", color="#262830", haze_color="#9aa0aa",
                sag: float = WIRE_SAG, extend: bool = True, seed: int = 0) -> np.ndarray:
    """Poles given as [x, base, height] (fractions), listed along the line; wires hang between
    neighbors with a sag. Smaller poles are farther away and fade toward `haze_color`.
    extend: the wires run on past the nearer (taller) end pole out of the frame."""
    if kind not in POLE_KINDS:
        raise ValueError(f"unknown power_lines kind '{kind}', expected one of {list(POLE_KINDS)}")
    height, width = layer.a.shape
    shape = layer.a.shape
    poles = poles or [[0.2, 0.8, 0.4], [0.6, 0.7, 0.2], [0.85, 0.65, 0.1]]
    tallest = max(p[2] for p in poles)
    shapes = []
    for x, base, tall in poles:
        strokes, points = _pole_shape(kind, x * width, base * height, tall * height)
        shapes.append((strokes, points, tall / tallest))
    mask = np.zeros(shape, np.float32)
    for strokes, _, scale in shapes:
        pole = pk.stroke_mask(shape, [(pk.resample(p, 6), max(w, 0.8)) for p, w in strokes])
        layer.paint(pole, _fade(color, haze_color, (1.0 - scale) * 0.7))
        mask = np.maximum(mask, pole)
    wires = []
    for (_, a_points, a_scale), (_, b_points, b_scale) in zip(shapes[:-1], shapes[1:]):
        for pa, pb in zip(a_points, b_points):
            pa, pb = np.asarray(pa, np.float32), np.asarray(pb, np.float32)
            t = np.linspace(0.0, 1.0, 24)[:, None]
            line = pa + (pb - pa) * t
            line[:, 1] += np.linalg.norm(pb - pa) * sag * 4.0 * (t[:, 0] * (1.0 - t[:, 0]))
            wires.append((line, max(height * 0.0011 * (a_scale + b_scale) / 2, 0.7)))
    if extend and len(shapes) >= 2:
        # Only the nearer (taller) end runs out of frame: the far end vanishes into the haze.
        first, last = (shapes[0], shapes[1]), (shapes[-1], shapes[-2])
        (_, near, _), (_, nxt, _) = first if shapes[0][2] >= shapes[-1][2] else last
        for pa, pb in zip(near, nxt):
            pa, pb = np.asarray(pa, np.float32), np.asarray(pb, np.float32)
            direction = (pa - pb) / (np.linalg.norm(pa - pb) or 1.0)
            end = pa + direction * width * 1.5
            t = np.linspace(0.0, 1.0, 24)[:, None]
            line = pa + (end - pa) * t
            line[:, 1] += np.linalg.norm(end - pa) * sag * 0.5 * (t[:, 0] * (1.0 - t[:, 0]))
            wires.append((line, max(height * 0.0011, 0.7)))
    if wires:
        layer.paint(pk.stroke_mask(shape, wires), color, 0.9)
    return mask


# -- street lamp ------------------------------------------------------------------
def streetlamp(layer: pk.Layer, base=(0.7, 0.85), height: float = 0.45, arm: float = -1.0, color="#ffb35a",
               pole="#24262e", glow: float = 0.7, pool: bool = True, on: bool = True) -> np.ndarray:
    """Pole with a curved arm and a lamp head; lit, it throws a glow, a soft cone and a pool
    of light on the ground. arm: -1 the arm reaches left, +1 right."""
    shape = layer.a.shape
    h, w = shape
    bx, by = base[0] * w, base[1] * h
    tall = height * h
    top = by - tall
    reach = tall * 0.16 * arm
    arm_path = pk.spline(np.array([[bx, top + tall * 0.08], [bx, top], [bx + reach * 0.6, top - tall * 0.02],
                                   [bx + reach, top + tall * 0.01]], np.float32))
    head = np.array([bx + reach, top + tall * 0.03], np.float32)
    strokes = [(pk.resample(np.array([[bx, by], [bx, top + tall * 0.08]], np.float32), 8),
                np.linspace(tall * 0.024, tall * 0.014, 8).astype(np.float32)),
               (pk.resample(arm_path, 16), max(tall * 0.008, 1.0))]
    mask = pk.stroke_mask(shape, strokes)
    lamp = pk.fill_mask(shape, pk.ellipse(head[0], head[1], tall * 0.04, tall * 0.014))
    layer.paint(np.maximum(mask, lamp), pole)
    if on:
        if pool:                          # light pooled on the ground below the head
            spot = pk.radial_ramp(shape, (head[0], by), tall * 0.45, aspect=0.18)
            layer.paint(spot, color, 0.35 * glow)
        cone = pk.fill_mask(shape, [np.array([head + [-tall * 0.03, 0], head + [tall * 0.03, 0],
                                              [head[0] + tall * 0.30, by], [head[0] - tall * 0.30, by]])])
        fall = pk.linear_ramp(shape, head, (head[0], by))
        layer.paint(pk.blur(cone, tall * 0.04) * (1.0 - fall), color, 0.18 * glow)
        layer.paint(pk.radial_ramp(shape, head, tall * 0.5), color, 0.35 * glow)
        layer.paint(pk.radial_ramp(shape, head, tall * 0.12), pk.mix(color, "#ffffff", 0.5), 0.8 * glow)
        layer.paint(pk.fill_mask(shape, pk.ellipse(head[0], head[1] + tall * 0.008, tall * 0.03, tall * 0.008)),
                    pk.mix(color, "#ffffff", 0.7))
    return mask


# -- weather ------------------------------------------------------------------------
def snow(layer: pk.Layer, count: int = 600, size=(0.002, 0.009), top: float = 0.0, bottom: float = 1.0,
         color="#f2f4f8", opacity: float = 0.85, wind: float = 12.0, seed: int = 0) -> np.ndarray:
    """Falling snow: many small sharp flakes and a few big soft ones (close to the lens).
    size: flake radius range (share of the height); wind: streak angle in degrees from vertical."""
    shape = layer.a.shape
    h, w = shape
    rng = np.random.default_rng(seed)
    radius = (size[0] + (size[1] - size[0]) * rng.random(count) ** 3) * h
    xs = rng.uniform(0, w, count)
    ys = rng.uniform(top * h, bottom * h, count)
    near = radius > (size[0] + (size[1] - size[0]) * 0.55) * h
    flakes = np.zeros(shape, np.float32)
    for group, blur in ((~near, 0.4), (near, 2.2)):
        polys = [pk.ellipse(x, y, r * 0.9, r * 1.25, rot_deg=wind, n=10) for x, y, r in
                 zip(xs[group], ys[group], radius[group])]
        if not polys:
            continue
        mask = pk.fill_mask(shape, polys, ss=1)
        mask = pk.blur(mask, max(float(np.median(radius[group])) * blur, 0.5))
        layer.paint(np.clip(mask * 1.6, 0.0, 1.0), color, opacity * (0.7 if blur > 1 else 1.0))
        flakes = np.maximum(flakes, mask)
    return flakes


def fog(layer: pk.Layer, top: float = 0.5, bottom: float = 0.9, color="#9aa0aa", opacity: float = 0.5) -> np.ndarray:
    """Fog lying low: clear above `top`, densest at `bottom` and below."""
    shape = layer.a.shape
    h, w = shape
    ramp = pk.smoothstep(0.0, 1.0, pk.linear_ramp(shape, (0, top * h), (0, bottom * h)))
    layer.paint(ramp, color, opacity)
    return ramp


# -- trees --------------------------------------------------------------------------
BRANCH_DEPTH = 6
TRUNK_SHARE = 0.62                     # trunk length in tree heights; limbs leave it along the way
LIMBS = 7                              # limbs growing out of the trunk
MIN_TWIG_PX = 0.45                     # branches thinner than this stop forking
LENGTH_RATIO = (0.55, 0.72)            # child branch length over its parent
WIDTH_RATIO = 0.58                     # child branch width over its parent
BIRCH_BARK, BIRCH_MARK = "#e6e3dc", "#2c2a2e"


def bare_tree(layer: pk.Layer, base=(0.7, 0.9), height: float = 0.45, color="#2e2a2c", birch: bool = False,
              lean: float = 0.0, spread: float = 1.0, light=None, seed: int = 0) -> np.ndarray:
    """Leafless tree: a tapering trunk with limbs along its upper part, each limb forking again
    and again into a fine crown of twigs. birch: white trunk with dark marks."""
    shape = layer.a.shape
    h, w = shape
    rng = np.random.default_rng(seed)
    size = height * h
    start = np.array([base[0] * w, base[1] * h], np.float32)
    trunk_strokes, limb_strokes = [], []

    def segment(point, angle, length, width):
        bend = rng.uniform(-10, 10)
        mid = point + np.array([np.sin(np.deg2rad(angle + bend * 0.5)), -np.cos(np.deg2rad(angle + bend * 0.5))],
                               np.float32) * length * 0.5
        end = mid + np.array([np.sin(np.deg2rad(angle + bend)), -np.cos(np.deg2rad(angle + bend))],
                             np.float32) * length * 0.5
        return pk.resample(pk.spline(np.array([point, mid, end])), 8)

    def grow(point, angle, length, width, level):
        path = segment(point, angle, length, width)
        limb_strokes.append((path, np.linspace(width, width * 0.7, len(path)).astype(np.float32)))
        if level >= BRANCH_DEPTH or width < MIN_TWIG_PX:
            return
        for _ in range(int(rng.integers(2, 4))):
            origin = path[int(rng.uniform(0.5, 1.0) * (len(path) - 1))]
            # Branches turn outward but keep reaching up, as crowns of leafless trees do.
            turn = rng.uniform(15, 40) * spread * rng.choice([-1.0, 1.0])
            child = angle + turn - 0.25 * (angle + turn - lean)
            grow(origin, child, length * rng.uniform(*LENGTH_RATIO), width * WIDTH_RATIO, level + 1)

    trunk = pk.resample(pk.spline(np.array([start, start + [size * 0.02, -size * TRUNK_SHARE * 0.5],
                                            start + [size * np.sin(np.deg2rad(lean)) * TRUNK_SHARE,
                                                     -size * TRUNK_SHARE]], np.float32)), 24)
    trunk_width = size * 0.035
    trunk_strokes.append((trunk, np.linspace(trunk_width, trunk_width * 0.35, len(trunk)).astype(np.float32)))
    for i in range(LIMBS):
        at = 0.35 + 0.65 * (i + rng.uniform(0.0, 0.8)) / LIMBS
        index = min(int(at * (len(trunk) - 1)), len(trunk) - 1)
        side = 1.0 if i % 2 else -1.0
        angle = lean + side * rng.uniform(25, 55) * spread
        width = trunk_width * (1.0 - at * 0.6) * 0.45
        grow(trunk[index], angle, size * (0.40 - 0.18 * at), width, 1)
    grow(trunk[-1], lean + rng.uniform(-8, 8), size * 0.32, trunk_width * 0.3, 1)
    trunk_mask = pk.stroke_mask(shape, trunk_strokes)
    limbs = pk.stroke_mask(shape, limb_strokes)
    if birch:
        layer.paint(limbs, color, 0.95)
        light = DEFAULT_LIGHT if light is None else np.asarray(light, np.float32)
        lt.paint_form(layer, trunk_mask, BIRCH_BARK, pk.adjust(BIRCH_BARK, value=0.7), light, radius=size * 0.02,
                      softness=0.2)
        marks = []
        normals = pk.normals(trunk)
        widths = trunk_strokes[0][1]
        for i in range(1, len(trunk) - 1):
            for _ in range(2):
                if rng.random() < 0.6:
                    half = widths[i] * 0.5 * rng.uniform(0.3, 0.9)
                    center = trunk[i] + normals[i] * widths[i] * rng.uniform(-0.35, 0.35) \
                        + (trunk[i + 1] - trunk[i]) * rng.uniform(0.0, 1.0)
                    marks.append((np.array([center - normals[i] * half, center + normals[i] * half], np.float32),
                                  max(widths[i] * 0.10, 0.8)))
        if marks:
            layer.paint(pk.stroke_mask(shape, [(pk.resample(p, 4), wd) for p, wd in marks]) * trunk_mask,
                        BIRCH_MARK, 0.85)
    else:
        layer.paint(np.maximum(trunk_mask, limbs), color)
    return np.maximum(trunk_mask, limbs)
