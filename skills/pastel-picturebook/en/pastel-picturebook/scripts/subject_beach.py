"""Beach: sky, the sea out to the horizon, breaking foam, wet and dry sand, optional palms.

Bands are painted far to near as in the landscape: the sea deepens toward the horizon and pales
into shallow water at the shore, the shoreline wanders, the wet sand mirrors the sky. Vertical
positions are shares of the picture height, horizontal ones of its width.
"""
import numpy as np

import kit
from figure import Figure
from painter import Scene, run_hook
from raster import blur, mix, noise, over, rgb, screen, smooth, stroke, stroke_many, taper
from subject_landscape import paint_sky

UNIT_SHARE = 0.19
FOCUS = {"sky": 0.05, "sea": 0.3, "sand": 0.35, "palm": 0.6}
# Shoreline wander: amplitude (share of the height) and how many swells cross the picture.
SHORE_WANDER, SHORE_SWELLS = 0.012, 2.3
# Foam band thickness and the faint line of the next wave above it (shares of the height).
FOAM_WIDTH, NEXT_WAVE = 0.006, 0.022
WET_BAND = 0.055


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light), seed=spec["seed"], spec=spec)
    fig.focus = np.full(fig.size, FOCUS["sky"], np.float32)
    return fig


def note_focus(scene, mask, level):
    scene.fig.focus = np.where(mask > 0.5, level, scene.fig.focus).astype(np.float32)


def shoreline(scene):
    """Row (px) of the water's edge at every column."""
    height, width = scene.size
    spec = scene.fig.spec["sea"]
    cols = np.arange(width, dtype=np.float32)
    rng = np.random.default_rng(scene.fig.seed + 81)
    phase = rng.uniform(0, 2 * np.pi)
    wander = np.sin(cols / width * 2 * np.pi * SHORE_SWELLS + phase) + 0.4 * np.sin(cols / width * 2 * np.pi * 5.1 + 2 * phase)
    return spec["shore_y"] * height + SHORE_WANDER * height * wander


def paint_sea(scene, shore):
    """Deep water at the horizon to shallow turquoise at the shore, wave streaks, the sun's glitter."""
    spec, tones = scene.fig.spec, scene.style["palette"]["sea"]
    height, width = scene.size
    rows = np.arange(height, dtype=np.float32)[:, None] * np.ones((1, width), np.float32)
    horizon = spec["horizon_y"] * height
    sea = np.clip(rows - horizon + 0.5, 0, 1) * np.clip(shore[None, :] - rows + 0.5, 0, 1)
    depth = np.clip((rows - horizon) / np.maximum(shore[None, :] - horizon, 1.0), 0, 1)
    water = mix(rgb(tones["deep"]), rgb(tones["shallow"]), (depth ** 1.6)[..., None])
    over(scene.image, water, sea)
    if scene.shade_on:
        rng = np.random.default_rng(scene.fig.seed + 83)
        streaks = []
        for _ in range(spec["sea"].get("waves", 70)):
            fall = rng.random() ** 1.4
            y = horizon + 3 + fall * (spec["sea"]["shore_y"] * height - horizon - 6)
            x, half = rng.uniform(0, width), width * rng.uniform(0.015, 0.07) * (0.3 + fall)
            streaks.append((np.array([[x - half, y], [x + half, y]]), (0.8 + 2.0 * fall) * taper(2, 1.0, 1.0)))
        screen(scene.image, rgb(tones["light"]), stroke_many(scene.size, streaks) * sea, 0.45)
        sun_x = spec["sky"]["sun_x"] * width
        dashes = []
        for _ in range(spec["sea"].get("glitter", 160)):
            fall = rng.random() ** 0.8
            y = horizon + 3 + fall * (spec["sea"]["shore_y"] * height - horizon) * 0.9
            x = sun_x + rng.normal(0, width * (0.01 + 0.05 * fall))
            half = width * (0.003 + 0.012 * fall) * rng.uniform(0.5, 1.5)
            dashes.append((np.array([[x - half, y], [x + half, y]]), (1.0 + 1.6 * fall) * taper(2, 1.0, 1.0)))
        screen(scene.image, rgb(tones["glitter"]), stroke_many(scene.size, dashes) * sea, 0.8)
        haze = np.clip(1 - np.abs(rows - horizon) / (height * 0.006), 0, 1)
        screen(scene.image, rgb(tones["light"]), haze, 0.5)
    note_focus(scene, sea, FOCUS["sea"])


def paint_sand(scene, shore):
    """Wet sand mirroring the sky below the foam, then dry sand with grain and wind ripples."""
    tones = scene.style["palette"]["sand"]
    height, width = scene.size
    rows = np.arange(height, dtype=np.float32)[:, None] * np.ones((1, width), np.float32)
    below = np.clip(rows - shore[None, :] + 0.5, 0, 1)
    fall = np.clip((rows - shore[None, :]) / max(height * (1 - scene.fig.spec["sea"]["shore_y"]), 1.0), 0, 1)
    over(scene.image, mix(rgb(tones["far"]), rgb(tones["near"]), fall[..., None]), below)
    wet = below * np.clip(1 - (rows - shore[None, :]) / (WET_BAND * height), 0, 1)
    over(scene.image, rgb(tones["wet"]), wet, 0.85)
    if scene.shade_on:
        screen(scene.image, rgb(scene.style["palette"]["sea"]["light"]), wet * np.clip(1 - (rows - shore[None, :]) / (WET_BAND * height * 0.5), 0, 1), 0.35)
        grain = noise(scene.size, max(width * 0.002, 1.0), scene.fig.seed + 85, 2)
        over(scene.image, rgb(tones["shadow"]), np.clip((grain - 0.62) * 4.0, 0, 1) * below * (1 - wet), 0.25)
        rng = np.random.default_rng(scene.fig.seed + 87)
        ripples = []
        for _ in range(scene.fig.spec["sand"].get("ripples", 40)):
            depth = rng.random() ** 0.7
            y = scene.fig.spec["sea"]["shore_y"] * height + (WET_BAND + 0.02 + depth * 0.9) * (height - scene.fig.spec["sea"]["shore_y"] * height)
            x, half = rng.uniform(0, width), width * rng.uniform(0.02, 0.06) * (0.4 + depth)
            path = smooth(np.array([[x - half, y], [x, y - 0.004 * height * (0.5 + depth)], [x + half, y]]), samples=6)
            ripples.append((path, (0.8 + 1.4 * depth) * taper(len(path), 0.0, 0.0)))
        over(scene.image, rgb(tones["shadow"]), blur(stroke_many(scene.size, ripples), 0.8) * below * (1 - wet), 0.35)
    note_focus(scene, below, FOCUS["sand"])


def paint_foam(scene, shore):
    """White foam along the water's edge and the faint crest of the next wave beyond it."""
    tones = scene.style["palette"]["sea"]
    height, width = scene.size
    cols = np.arange(width, dtype=np.float32)
    rng = np.random.default_rng(scene.fig.seed + 89)
    lace = 1.0 + 0.6 * blur(rng.random(width).astype(np.float32)[None, :], 3.0)[0]
    edge = np.column_stack([cols, shore - FOAM_WIDTH * height * 0.3])
    over(scene.image, rgb(tones["foam"]), stroke(scene.size, edge, FOAM_WIDTH * height * lace * 0.5), 0.95)
    crest = np.column_stack([cols, shore - NEXT_WAVE * height + 0.004 * height * np.sin(cols / width * 17.0)])
    over(scene.image, rgb(tones["foam"]), stroke(scene.size, crest, FOAM_WIDTH * height * 0.25 * lace), 0.55)


# Fronds of a palm crown: direction of each (degrees, 0 = toward +x, -90 = up), and their serration count.
FROND_TURNS = (-172, -140, -105, -75, -40, -8, 168)
LEAFLETS = 11


def palm_shapes(scene, x, base_y, tall, lean):
    """Trunk path and fronds (mid-rib path, half-widths) of one palm in pixels: fronds rise, arch over and droop.

    A frond is stroked along its rib rather than filled as an outline, so a frond that curls over itself has no holes.
    """
    height = scene.size[0]
    width = scene.size[1]
    base = np.array([x * width, base_y * height])
    top = base + np.array([lean * tall * height, -tall * height])
    trunk = smooth(np.array([base, base + (top - base) * 0.5 + [-lean * 0.15 * tall * height, 0], top]), samples=10)
    reach = tall * height * 0.40
    fronds = []
    for turn in FROND_TURNS:
        rad = np.deg2rad(turn)
        across, up = np.cos(rad), np.sin(rad)
        # Rising first along its own direction, then bending down under its weight.
        middle = top + reach * 0.55 * np.array([across, up - 0.15])
        tip = top + reach * np.array([across * 1.0, up * 0.35 + 0.45 + 0.25 * abs(across)])
        spine = smooth(np.array([top, middle, tip]), samples=10)
        along = np.linspace(0.0, 1.0, len(spine))
        # Leaflets: the edge is cut into teeth that sweep toward the tip.
        teeth = 0.15 + 0.85 * np.abs(np.sin(along * np.pi * LEAFLETS))
        half = 0.034 * tall * height * np.sin(np.pi * np.clip(along * 1.05, 0, 1)) ** 0.7 * teeth
        fronds.append((spine, half))
    return trunk, fronds


def paint_palms(scene):
    """Palms leaning over the beach: a ringed, tapering trunk and a crown of drooping fronds."""
    tones = scene.style["palette"]["palm"]
    height = scene.size[0]
    for x, base_y, tall, lean in scene.fig.spec.get("palms", []):
        trunk, fronds = palm_shapes(scene, x, base_y, tall, lean)
        widths = 0.018 * tall * height * 4 * taper(len(trunk), 1.0, 0.55, 0.0) + 0.012 * tall * height
        body = stroke(scene.size, trunk, widths)
        over(scene.image, rgb(tones["trunk"]), body)
        if scene.shade_on:
            for k in range(4, len(trunk) - 2, 3):
                ring = np.array([trunk[k] - [widths[k] * 0.5, 0], trunk[k] + [widths[k] * 0.5, -widths[k] * 0.15]])
                over(scene.image, rgb(tones["trunk_shadow"]), stroke(scene.size, ring, 1.6) * body, 0.7)
        kit.ink_edges(scene, body, 1.6, "palm", "line")
        leaves = np.zeros(scene.size, np.float32)
        # One frond at a time, each over the last with its own outline, so the crown reads as separate leaves.
        for k, (spine, half) in enumerate(fronds):
            leaf = stroke(scene.size, spine, 2.0 * half)
            tone = mix(rgb(tones["leaf_shadow"]), rgb(tones["leaf"]), 0.55 + 0.45 * (k % 2)) if scene.shade_on else rgb(tones["leaf"])
            over(scene.image, tone, leaf)
            kit.ink_edges(scene, leaf, 1.2, "palm", "line")
            leaves = np.maximum(leaves, leaf)
        note_focus(scene, np.maximum(body, leaves), FOCUS["palm"])


def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    paint_sky(scene)
    run_hook(extras, "after_background", scene)
    shore = shoreline(scene)
    paint_sea(scene, shore)
    paint_sand(scene, shore)
    paint_foam(scene, shore)
    paint_palms(scene)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
