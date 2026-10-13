#!/usr/bin/env python3
"""Free-form scene example: lake at dusk, built only from paintkit primitives.

Shows the general recipe for subjects the portrait rig does not cover:
back-to-front layers, each part = smooth path -> mask -> base fill ->
mask-derived light -> optional line, then one finishing pass.

Usage: python landscape_example.py out.png [anime|illust|painterly]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from paintkit import backdrop as bd  # noqa: E402
from paintkit import core as pk  # noqa: E402
from paintkit import finish as fn  # noqa: E402
from paintkit import light as lt  # noqa: E402

WIDTH, HEIGHT = 1500, 1000
HORIZON_Y = 600
LIGHT = lt.light_vector(azimuth_deg=150, elevation_deg=25)   # low sun, upper left
SUN = (430, 470)
SKY_TOP, SKY_LOW = "#2f3f7a", "#f6b98a"
RIDGES = [  # (base y, roughness px, color) far to near: farther = lighter and hazier
    (575, 110, "#a79cc4"),
    (595, 80, "#7672a8"),
    (615, 50, "#3f4178"),
]


def ridge_polygon(base_y: float, roughness: float, seed: int) -> np.ndarray:
    """Mountain silhouette: a noise-driven skyline closed along the bottom."""
    rng = np.random.default_rng(seed)
    xs = np.linspace(-50, WIDTH + 50, 16)
    ys = base_y - roughness * rng.uniform(0.1, 1.0, len(xs)) ** 1.5
    skyline = pk.spline(np.stack([xs, ys], 1), n=10)
    return np.vstack([skyline, [[WIDTH + 50, HEIGHT], [-50, HEIGHT]]])


def paint_sky(canvas: pk.Canvas) -> None:
    sky = canvas.layer("sky")
    bd.gradient(sky, SKY_TOP, SKY_LOW)
    bd.glow(sky, SUN, 520, "#ffe2b0", 0.85)
    sun = pk.fill_mask(canvas.shape, pk.ellipse(SUN[0], SUN[1], 46, 46))
    sky.paint(pk.blur(sun, 2.0), "#fff6dc")
    clouds = pk.smoothstep(0.52, 0.80, pk.noise(canvas.shape, 420, seed=4, octaves=4))
    band = 1.0 - pk.linear_ramp(canvas.shape, (0, 120), (0, 520))
    sky.paint(clouds * band, "#f7c7b0", 0.55)


def paint_ridges(canvas: pk.Canvas) -> None:
    layer = canvas.layer("ridges")
    for index, (base_y, roughness, color) in enumerate(RIDGES):
        mask = pk.fill_mask(canvas.shape, ridge_polygon(base_y, roughness, seed=10 + index))
        layer.paint(mask, color)
        # Rim of sunlight on the slopes that face the sun.
        layer.paint(lt.rim(mask, LIGHT, 5.0, 2.0), "#ffd9a8", 0.55)
        # Haze: each ridge fades toward the horizon, separating the depth planes.
        haze = pk.linear_ramp(canvas.shape, (0, base_y - 40), (0, HORIZON_Y + 30)) * mask
        layer.paint(haze, SKY_LOW, 0.35)


def paint_lake(canvas: pk.Canvas) -> None:
    flat = canvas.flatten()
    layer = canvas.layer("lake")
    water = np.zeros(canvas.shape, np.float32)
    water[HORIZON_Y:] = 1.0
    # A reflection is the scene above the horizon, flipped and darkened.
    mirrored = np.zeros_like(flat)
    span = min(HEIGHT - HORIZON_Y, HORIZON_Y)
    mirrored[HORIZON_Y:HORIZON_Y + span] = flat[HORIZON_Y - span:HORIZON_Y][::-1]
    layer.paint(water, mirrored * 0.82 + pk.rgb("#1d2450") * 0.18)
    rng = np.random.default_rng(7)
    ripples = []
    for _ in range(140):
        y = HORIZON_Y + rng.uniform(0.02, 1.0) ** 1.6 * (HEIGHT - HORIZON_Y)
        x = rng.uniform(0, WIDTH)
        half = rng.uniform(20, 120) * (0.4 + (y - HORIZON_Y) / (HEIGHT - HORIZON_Y))
        path = np.array([[x - half, y], [x, y + rng.uniform(-1.5, 1.5)], [x + half, y]])
        ripples.append((pk.resample(path, 12), pk.taper(12, rng.uniform(1.5, 4.0), head=0.0, tail=0.0)))
    layer.paint(pk.stroke_mask(canvas.shape, ripples) * water, "#ffe9c8", 0.35)
    glitter = pk.radial_ramp(canvas.shape, (SUN[0], HORIZON_Y + 150), 300, aspect=2.2) * water
    layer.paint(glitter, "#ffd9a0", 0.45)


def foliage_clusters(rng) -> list:
    """Canopy as clusters of small blobs; one big blob would read as a balloon."""
    clusters = []
    for cx, cy, spread in ((1150, 470, 70), (1290, 430, 80), (1060, 380, 60), (1200, 330, 75),
                           (1350, 330, 65), (1120, 270, 55), (1270, 240, 60)):
        clusters.append([pk.ellipse(cx + rng.normal(0, spread * 0.5), cy + rng.normal(0, spread * 0.35),
                                    rng.uniform(0.45, 0.8) * spread, rng.uniform(0.35, 0.6) * spread,
                                    rot_deg=rng.uniform(-25, 25)) for _ in range(7)])
    return clusters


def paint_tree(canvas: pk.Canvas) -> None:
    layer = canvas.layer("tree")
    ground = pk.fill_mask(canvas.shape, pk.spline([[820, 1000], [960, 930], [1200, 900], [1500, 915],
                                                   [1500, 1000]], closed=True))
    lt.paint_form(layer, ground, "#2a2f45", "#161a2c", LIGHT, radius=30, softness=0.2)
    trunk = pk.resample(pk.spline([[1195, 930], [1205, 780], [1180, 620], [1210, 430]]), 40)
    trunk_mask = pk.stroke_mask(canvas.shape, (trunk, pk.taper(40, 44, head=1.0, tail=0.35, peak=0.0)))
    lt.paint_form(layer, trunk_mask, "#3a2a35", "#1c1424", LIGHT, radius=18, softness=0.15)
    for start, tip in (((1196, 600), (1090, 430)), ((1200, 540), (1320, 400))):
        branch = pk.resample(pk.spline([start, ((start[0] + tip[0]) / 2, start[1] - 60), tip]), 24)
        layer.paint(pk.stroke_mask(canvas.shape, (branch, pk.taper(24, 16, head=1.0, tail=0.2, peak=0.0))), "#2a1e2c")
    clusters = foliage_clusters(np.random.default_rng(21))
    # Back to front: one dark mass first, then each cluster with its own light.
    whole = pk.fill_mask(canvas.shape, [blob for cluster in clusters for blob in cluster])
    layer.paint(whole, "#232b3a")
    for cluster in clusters:
        mask = pk.fill_mask(canvas.shape, cluster)
        lt.paint_form(layer, mask, "#56633f", "#2b3540", LIGHT, radius=26, threshold=0.18, softness=0.12)
        layer.paint(lt.rim(mask, LIGHT, 7.0, 2.5), "#ffcf8a", 0.75)


def finish(image: np.ndarray, style: str) -> np.ndarray:
    if style == "painterly":
        image = fn.painterly(image, radii=(24, 12, 6, 3), seed=3)
        return fn.canvas_weave(fn.grade(image, 1.06, 1.08), 0.04)
    image = fn.bloom(fn.diffusion(image, 12, 0.25), 0.78, 20, 0.4)
    image = fn.grade(image, 1.05, 1.10, "#28306a", "#ffe9c4", 0.12)
    return fn.grain(fn.vignette(image, 0.25), 0.012)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "landscape.png"
    style = sys.argv[2] if len(sys.argv) > 2 else "painterly"
    canvas = pk.Canvas(WIDTH, HEIGHT)
    paint_sky(canvas)
    paint_ridges(canvas)
    paint_lake(canvas)
    paint_tree(canvas)
    pk.save(finish(canvas.flatten(), style), out)
    print(f"[ok] {out} style={style}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
