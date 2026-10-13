"""Landscape: sky, mountain ranges, a lake with reflections, a wooded shore, pines.

Depth is built the way a landscape painter does it: bands painted far to near,
each nearer band darker, more saturated and less veiled by haze. Vertical
positions in the spec are fractions of the canvas height, horizontal ones of
its width.
"""
import cv2
import numpy as np

import kit
import relief
from figure import Figure
from painter import Scene, run_hook
from raster import blur, ellipse, fill, mix, noise, over, rgb, screen, smoothstep, stroke_many, taper

UNIT_SHARE = 0.19
FOCUS = {"sky": 0.05, "range": 0.35, "water": 0.3, "shore": 0.5, "bank": 0.45, "pine": 0.65}
# Shadow facets on a mountain lean away from the lamp by this many px per px of depth.
FACET_LEAN = 0.55
# The reflection is squeezed vertically, as water foreshortens what it mirrors.
REFLECTION_SQUEEZE = 0.82


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light),
                 seed=spec["seed"], spec=spec)
    fig.focus = np.full(fig.size, FOCUS["sky"], np.float32)
    return fig


def note_focus(scene, mask, level):
    scene.fig.focus = np.where(mask > 0.5, level, scene.fig.focus).astype(np.float32)


def grid(scene):
    height, width = scene.size
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    return rows, cols


# ---------------------------------------------------------------------- sky
def paint_sky(scene):
    """Gradient, sun with its glow, and clouds lit from below by the low sun."""
    spec, tones = scene.fig.spec["sky"], scene.style["palette"]["sky"]
    height, width = scene.size
    horizon = scene.fig.spec["horizon_y"]
    stops = [(0.0, tones["top"]), (horizon * 0.55, tones["middle"]), (horizon, tones["horizon"]), (1.0, tones["horizon"])]
    scene.image[:] = kit.vertical_gradient(scene.size, stops)
    sun = (spec["sun_x"] * width, spec["sun_y"] * height)
    radius = spec["sun_r"] * width
    if scene.shade_on:
        halo = blur(fill(scene.size, ellipse(sun, radius * 5, radius * 5, 48)), radius * 3.5)
        screen(scene.image, rgb(tones["glow"]), halo, 0.75)
    over(scene.image, rgb(tones["sun"]), fill(scene.size, ellipse(sun, radius, radius, 48)))
    paint_clouds(scene, sun)


def paint_clouds(scene, sun):
    """Clouds: wide flat noise, thresholded; undersides nearest the sun catch its colour."""
    spec, tones = scene.fig.spec["sky"], scene.style["palette"]["sky"]
    height, width = scene.size
    rows, cols = grid(scene)
    horizon_px = scene.fig.spec["horizon_y"] * height
    wide = cv2.resize(noise((height // 2, width // 6), 46, scene.fig.seed + 21, 4), (width, height), interpolation=cv2.INTER_CUBIC)
    band = smoothstep(rows, height * 0.02, height * 0.12) * (1 - smoothstep(rows, horizon_px * 0.72, horizon_px * 0.95))
    density = np.clip((wide - (1.0 - spec["clouds"])) * 4.0, 0.0, 1.0) * band
    cloud = scene.edge(density) if scene.shade_on else (density > 0.5).astype(np.float32)
    over(scene.image, rgb(tones["cloud"]), cloud, 0.92)
    if scene.shade_on:
        under = np.clip(cloud - np.roll(cloud, -int(height * 0.012), axis=0), 0, 1)
        near_sun = np.exp(-((cols - sun[0]) ** 2 + (rows - sun[1]) ** 2) / (2 * (width * 0.33) ** 2))
        over(scene.image, rgb(tones["cloud_lit"]), scene.soften(under, 0.01) * (0.35 + 0.65 * near_sun), 0.95)
        core = scene.edge(np.clip(density * 1.6 - 0.75, 0, 1))
        over(scene.image, rgb(tones["cloud_shadow"]), core * (1 - near_sun * 0.6), 0.30)


# ---------------------------------------------------------------- mountains
def facet_shadow(scene, ridge, rows, cols, crag_seed):
    """Shadow amount on a mountain: faces sloping away from the lamp are dark.

    How: the ridge's own slope decides the facing, sampled further along the
    ridge the deeper a pixel lies below it, so shadows fall as slanted facets
    from each peak. A little noise breaks the facets into crags.
    """
    width = scene.size[1]
    gentle = blur(ridge.astype(np.float32)[None, :], width * 0.012)[0]
    slope = np.gradient(gentle)
    depth = np.clip(rows - ridge[None, :], 0, None)
    toward = np.sign(scene.fig.light[0])
    wobble = (noise(scene.size, width * 0.03, crag_seed, 3) - 0.5) * width * 0.05
    sample = np.clip(cols + toward * FACET_LEAN * depth + wobble, 0, width - 1).astype(np.int32)
    facing_away = -toward * slope[sample]
    return np.clip(facing_away * 3.0 + 0.5, 0.0, 1.0)


def paint_ranges(scene):
    """Mountain ranges far to near, each veiled by haze at its foot."""
    spec, tones = scene.fig.spec, scene.style["palette"]
    height, width = scene.size
    rows, cols = grid(scene)
    horizon_px = spec["horizon_y"] * height
    above_water = np.clip(horizon_px - rows + 0.5, 0, 1)
    for index, layer in enumerate(spec["ranges"]):
        ridge = kit.ridge_line(width, horizon_px - layer["lift"] * height, layer["amplitude"] * height,
                               layer["roughness"], scene.fig.seed + 31 * (index + 1))
        if layer.get("forest"):
            teeth = np.abs(np.sin(np.arange(width) * np.pi / layer["forest"])) * layer["forest"] * 0.9
            ridge = ridge - teeth * (0.6 + 0.4 * noise((1, width), 30, scene.fig.seed + 77 + index, 2)[0])
        mask = kit.below_line(scene.size, ridge) * above_water
        group = tones[layer["group"]]
        shadow = facet_shadow(scene, ridge, rows, cols, scene.fig.seed + 41 + index)
        color = mix(rgb(group["base"]), rgb(group["shadow"]), scene.edge(shadow)[..., None])
        if layer.get("snow") and scene.shade_on:
            depth = rows - ridge[None, :]
            line = layer["snow"] * layer["amplitude"] * height * (0.55 + 0.9 * noise(scene.size, width * 0.04, scene.fig.seed + 51, 3))
            snow = scene.edge(np.clip((line - depth) / (height * 0.02) + 0.5, 0, 1))
            lit = mix(rgb(tones["snow"]["base"]), rgb(tones["snow"]["shadow"]), scene.edge(shadow)[..., None])
            color = mix(color, lit, snow[..., None])
        if scene.shade_on:
            foot = smoothstep(rows, horizon_px - (layer["lift"] + layer["amplitude"] * 0.75) * height, horizon_px)
            color = mix(color, rgb(tones["sky"]["haze"]), (foot * layer["haze"])[..., None])
        over(scene.image, color, mask)
        kit.ink_edges(scene, mask, 2.0, layer["group"], "line")
        note_focus(scene, mask, FOCUS["shore"] if layer.get("forest") else FOCUS["range"])
        scene.fig.paths[f"ridge_{index}"] = np.column_stack([np.arange(0, width, 8), ridge[::8]])


# -------------------------------------------------------------------- water
def paint_water(scene):
    """Lake: the scene above mirrored and rippled, tinted, with the sun's glitter path."""
    spec, tones = scene.fig.spec, scene.style["palette"]["water"]
    height, width = scene.size
    rows, cols = grid(scene)
    horizon_px = spec["horizon_y"] * height
    below = np.clip(rows - horizon_px + 0.5, 0, 1)
    depth = np.clip((rows - horizon_px) / max(height - horizon_px, 1), 0, 1)
    swell = spec["water"]["ripple"] * width * depth
    phase = noise(scene.size, width * 0.05, scene.fig.seed + 61, 2) * 6.0
    map_x = cols + swell * np.sin(rows * 0.9 / (1.0 + 2.5 * depth) + phase)
    map_y = horizon_px - (rows - horizon_px) / REFLECTION_SQUEEZE
    mirrored = cv2.remap(scene.image, map_x.astype(np.float32), map_y.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT)
    mirrored = mix(mirrored, rgb(tones["deep"]), (0.25 + 0.45 * depth)[..., None])
    over(scene.image, mirrored, below)
    if scene.shade_on:
        rng = np.random.default_rng(scene.fig.seed + 63)
        sun_x = spec["sky"]["sun_x"] * width
        dashes = []
        for _ in range(spec["water"]["glitter"]):
            fall = rng.random() ** 0.7
            y = horizon_px + 4 + fall * (height - horizon_px) * 0.9
            x = sun_x + rng.normal(0, width * (0.012 + 0.07 * fall))
            half = width * (0.004 + 0.022 * fall) * rng.uniform(0.5, 1.5)
            dashes.append((np.array([[x - half, y], [x + half, y]]), (1.0 + 2.5 * fall) * taper(2, 1.0, 1.0)))
        screen(scene.image, rgb(tones["glitter"]), stroke_many(scene.size, dashes) * below, 0.85)
        streaks = []
        for _ in range(spec["water"]["streaks"]):
            fall = rng.random()
            y = horizon_px + 6 + fall * (height - horizon_px)
            x, half = rng.uniform(0, width), width * rng.uniform(0.02, 0.09) * (0.4 + fall)
            streaks.append((np.array([[x - half, y], [x + half, y]]), (0.8 + 1.6 * fall) * taper(2, 1.0, 1.0)))
        screen(scene.image, rgb(tones["light"]), stroke_many(scene.size, streaks) * below, 0.22)
        shoreline = np.clip(1 - np.abs(rows - horizon_px) / (height * 0.004), 0, 1)
        screen(scene.image, rgb(tones["light"]), shoreline, 0.35)
    note_focus(scene, below, FOCUS["water"])


# --------------------------------------------------------------- foreground
def pine_outline(x, base_y, tall, spread, tiers, rng):
    """Jagged outline of one pine: tiers of drooping boughs widening toward the ground."""
    left, right = [], []
    for tier in range(tiers):
        share = (tier + 1) / tiers
        y_tip = base_y - tall * (1 - share) + tall * 0.02
        reach = spread * (0.12 + 0.88 * share ** 0.85) * rng.uniform(0.85, 1.12)
        y_notch = y_tip - tall / tiers * rng.uniform(0.35, 0.55)
        tuck = reach * rng.uniform(0.40, 0.55)
        left += [(x - tuck, y_notch), (x - reach, y_tip)]
        right += [(x + tuck, y_notch), (x + reach * rng.uniform(0.9, 1.1), y_tip)]
    top = (x, base_y - tall)
    return np.array([top] + right + [(x + spread * 0.08, base_y), (x - spread * 0.08, base_y)] + left[::-1])


def paint_pines(scene, bank_line):
    """Foreground pines framing the view: dark masses, lighter on the lamp side."""
    spec, tones = scene.fig.spec["pines"], scene.style["palette"]["pine"]
    height, width = scene.size
    rng = np.random.default_rng(scene.fig.seed + 71)
    rows, cols = grid(scene)
    toward = np.sign(scene.fig.light[0])
    for x_share, tall_share in sorted(spec, key=lambda pine: pine[1]):
        x = x_share * width
        base_y = bank_line[int(np.clip(x, 0, width - 1))] + height * 0.02
        tall = tall_share * height
        outline = pine_outline(x, base_y, tall, tall * 0.19, max(int(tall / (height * 0.045)), 5), rng)
        mask = fill(scene.size, outline)
        lit_side = np.clip(0.5 - toward * (cols - x) / (tall * 0.16), 0, 1)
        clumps = noise(scene.size, width * 0.012, int(rng.integers(1 << 30)), 2)
        shadow = np.clip(lit_side * 0.9 + (clumps - 0.5) * 0.9, 0, 1)
        color = mix(rgb(tones["base"]), rgb(tones["shadow"]), scene.edge(shadow)[..., None])
        over(scene.image, color, mask)
        kit.ink_edges(scene, mask, 2.0, "pine", "line")
        note_focus(scene, mask, FOCUS["pine"])
        scene.fig.shapes[f"pine_{int(x)}"] = outline


def paint_bank(scene):
    """Near shore: a dark sloping bank with grass along its edge and a few rocks."""
    spec, tones = scene.fig.spec["bank"], scene.style["palette"]["bank"]
    height, width = scene.size
    rows, cols = grid(scene)
    dip = spec["dip"] * height * np.sin(np.linspace(0, np.pi, width)) ** 1.5
    line = kit.ridge_line(width, spec["top_y"] * height, spec["amplitude"] * height, 0.45, scene.fig.seed + 81) + dip
    mask = kit.below_line(scene.size, line)
    depth = np.clip((rows - line[None, :]) / (height * 0.10), 0, 1)
    clumps = noise(scene.size, width * 0.02, scene.fig.seed + 83, 3)
    shadow = np.clip(depth * 0.8 + (clumps - 0.5) * 0.8, 0, 1)
    over(scene.image, mix(rgb(tones["base"]), rgb(tones["shadow"]), scene.edge(shadow)[..., None]), mask)
    rng = np.random.default_rng(scene.fig.seed + 85)
    blades = []
    for x in rng.uniform(0, width, spec["grass"]):
        root = np.array([x, line[int(x)] + 3])
        tall = height * rng.uniform(0.008, 0.028)
        lean = rng.normal(0, 0.35)
        blades.append((np.array([root, root + [lean * tall * 0.5, -tall * 0.6], root + [lean * tall, -tall]]), 2.2 * taper(3, 1.0, 0.0, 0.0)))
    over(scene.image, rgb(tones["base"]), stroke_many(scene.size, blades))
    for x_share, size_share in spec["rocks"]:
        x, radius = x_share * width, size_share * width
        center = (x, line[int(x)] + radius * 0.25)
        rock = relief.ellipsoid(scene.size, center, radius, radius * 0.62, angle_deg=rng.uniform(-12, 12))
        kit.shade_solid(scene, rock, "rock", level=0.42, spread=0.4)
        kit.ink_edges(scene, rock.mask, 2.0, "rock", "line")
    kit.ink_edges(scene, mask, 2.0, "bank", "line")
    note_focus(scene, mask, FOCUS["bank"])
    scene.fig.paths["bank"] = np.column_stack([np.arange(0, width, 8), line[::8]])
    return line


def paint_birds(scene):
    """A few distant birds: the smallest marks give the sky its scale."""
    spec = scene.fig.spec["sky"]
    height, width = scene.size
    rng = np.random.default_rng(scene.fig.seed + 91)
    marks = []
    for _ in range(spec["birds"]):
        x, y = rng.uniform(0.15, 0.6) * width, rng.uniform(0.12, 0.34) * height
        span = width * rng.uniform(0.006, 0.012)
        marks.append((np.array([[x - span, y - span * 0.35], [x, y], [x + span, y - span * 0.45]]), 1.8))
    over(scene.image, rgb(scene.style["palette"]["pine"]["shadow"]), stroke_many(scene.size, marks), 0.8)


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    paint_sky(scene)
    run_hook(extras, "after_background", scene)
    paint_ranges(scene)
    paint_water(scene)
    paint_birds(scene)
    bank_line = paint_bank(scene)
    paint_pines(scene, bank_line)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
