"""Backgrounds. Each function fills canvas.rgb before the subject is drawn."""
import numpy as np

from . import shading
from .config import rgb
from .geometry import Taper, ellipse, lock, ribbon, width_profile

PUFF_RADIUS = (0.07, 0.11)         # share of cloud width: minimum, random extra
PUFF_SQUASH = 0.92                 # puffs are slightly wider than tall
PUFF_SHADE_BAND = (0.10, 0.50)     # where a puff turns from light to shadow (-1 lit .. 1 away)
DEEP_TONE_START = 0.55             # share of cloud height above the base where deep blue begins
DEEP_TONE_STRENGTH = 0.75
SHORE_WAVE_UNITS = 26.0            # how far the waterline wanders
BOKEH_RADIUS = (18.0, 70.0)        # canvas units
BOKEH_OPACITY = (0.18, 0.50)
BASE_SAG = 0.06                    # share of cloud height the base may sag


def vertical_gradient(canvas, top_color, bottom_color, curve=1.0):
    _, ys = canvas.grid()
    ramp = (ys / canvas.units_height)[..., None] ** curve
    canvas.rgb = (np.asarray(top_color) * (1 - ramp) + np.asarray(bottom_color) * ramp).astype(np.float32)


def gradient_stops(canvas, stops):
    """Vertical gradient through several colours. stops: [(share of height 0..1, colour), ...] top to bottom."""
    _, ys = canvas.grid()
    share = ys / canvas.units_height
    positions = [position for position, _ in stops]
    channels = [np.interp(share, positions, [color[channel] for _, color in stops]) for channel in range(3)]
    canvas.rgb = np.stack(channels, axis=2).astype(np.float32)


def summer_sky(canvas, clouds, light, zenith=rgb("#2C7BD8"), horizon=rgb("#BFEAF8"),
               cloud_light=rgb("#FFFFFF"), cloud_shadow=rgb("#C3D8F5"), cloud_deep=rgb("#8FB2E6"),
               focus_blur=1.6):
    """Blue sky with cumulus. clouds: [(base_center, width, height, puff_count), ...]
    The artist places each cloud; only the puffs inside it are random."""
    vertical_gradient(canvas, zenith, horizon, curve=0.85)
    cumulus_clouds(canvas, clouds, light, (cloud_light, cloud_shadow, cloud_deep))
    canvas.rgb = shading.blur(canvas.rgb, canvas.px(focus_blur))


def cumulus_clouds(canvas, clouds, light, colors):
    """Add cumulus to whatever sky is already painted. colors: (lit, shadow, deep shadow)."""
    layer = np.ones_like(canvas.rgb)
    for base_center, width, height, puff_count in clouds:
        alpha = _cumulus(canvas, layer, base_center, width, height, puff_count, light, colors)
        canvas.blend(alpha, layer)


def stars(canvas, count, bottom_y, color=(1.0, 1.0, 0.95)):
    """Sparse stars above bottom_y, fading toward it."""
    rng = canvas.rng
    for _ in range(count):
        center = (rng.uniform(0, canvas.units_width), rng.uniform(0, bottom_y) * rng.random())
        size = rng.uniform(0.9, 2.2)
        canvas.blend(canvas.soft_ellipse(center, size, size), color, rng.uniform(0.4, 0.95))


def _cumulus(canvas, layer, base_center, width, height, puff_count, light, colors):
    """One cloud as a heap of individually lit puffs on a flat base, the way
    background painters block cumulus: far lobes first, near (lower) lobes last."""
    cloud_light, cloud_shadow, cloud_deep = colors
    rng = canvas.rng
    away = -np.asarray(light[:2]) / (np.linalg.norm(light[:2]) + 1e-9)
    puffs = []
    for _ in range(puff_count):
        across = rng.uniform(-1.0, 1.0)
        dome = (1.0 - across * across) ** 0.7
        up = rng.uniform(0.0, 1.0) ** 0.8
        radius = (PUFF_RADIUS[0] + PUFF_RADIUS[1] * rng.random()) * width * (0.45 + 0.55 * dome * (1 - 0.5 * up))
        puffs.append((base_center[0] + across * width / 2, base_center[1] - up * dome * height, radius))
    puffs.sort(key=lambda puff: puff[1])

    xs, ys = canvas.grid()
    alpha = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for center_x, center_y, radius in puffs:
        region = _region(canvas, center_x, center_y, radius)
        if region is None:
            continue
        dx = (xs[region] - center_x) / radius
        dy = (ys[region] - center_y) / (radius * PUFF_SQUASH)
        edge = 1.5 / canvas.px(radius)
        inside = shading.smoothstep(1.0 + edge, 1.0 - edge, np.sqrt(dx * dx + dy * dy))
        depth = shading.linear_ramp(ys[region], base_center[1] - height * DEEP_TONE_START, base_center[1])
        shade = shading.smoothstep(PUFF_SHADE_BAND[0], PUFF_SHADE_BAND[1], dx * away[0] + dy * away[1])
        color = cloud_light * (1 - shade[..., None]) + cloud_shadow * shade[..., None]
        deep = (shade * depth)[..., None] * DEEP_TONE_STRENGTH
        color = color * (1 - deep) + cloud_deep * deep
        layer[region] = layer[region] * (1 - inside[..., None]) + color * inside[..., None]
        alpha[region] = np.maximum(alpha[region], inside)
    return alpha * (1.0 - shading.smoothstep(base_center[1], base_center[1] + BASE_SAG * height, ys))


def _region(canvas, center_x, center_y, radius):
    left = int(np.floor(canvas.px(center_x - radius))) - 2
    right = int(np.ceil(canvas.px(center_x + radius))) + 2
    top = int(np.floor(canvas.px(center_y - radius))) - 2
    bottom = int(np.ceil(canvas.px(center_y + radius))) + 2
    left, top = max(left, 0), max(top, 0)
    right, bottom = min(right, canvas.width), min(bottom, canvas.height)
    if left >= right or top >= bottom:
        return None
    return (slice(top, bottom), slice(left, right))


def sun_glow(canvas, center, radius, color=(1.0, 0.98, 0.9), strength=0.45):
    glow = canvas.soft_ellipse(center, radius, radius)[..., None] * strength
    canvas.rgb = 1 - (1 - canvas.rgb) * (1 - glow * np.asarray(color, dtype=np.float32))  # screen blend


def flat_graphic(canvas, base=rgb("#F6E7D8"), disc=rgb("#F2B8A0"), leaf=rgb("#8FB9A8"),
                 disc_center=(620.0, 470.0), disc_radius=360.0):
    """Poster-like backdrop: one large disc and a few leaf shapes."""
    canvas.rgb[:] = base
    canvas.blend(canvas.mask(ellipse(disc_center, disc_radius, disc_radius, samples=160)), disc)
    leaves = (((940.0, 1240.0), (700.0, 760.0), 120.0, 0.18), ((1010.0, 1100.0), (860.0, 640.0), 105.0, -0.12),
              ((60.0, 1300.0), (150.0, 880.0), 110.0, -0.2), ((-20.0, 1150.0), (40.0, 760.0), 90.0, 0.15),
              ((90.0, 60.0), (330.0, 210.0), 80.0, 0.2))
    for root, tip, width, bend in leaves:
        polygon, center = lock(root, tip, width, bend)
        canvas.blend(canvas.mask(polygon), leaf)
        canvas.blend(canvas.mask(_vein(center)), base, 0.45)


def _vein(center):
    return ribbon(center[2:-2], width_profile(len(center) - 4, 3.0, Taper.END))


def studio_backdrop(canvas, dark=rgb("#23261F"), warm=rgb("#6E5A3C"), glow_center=(300.0, 420.0)):
    """Old-master backdrop: dark ground with a warm pool of light behind the head."""
    canvas.rgb[:] = dark
    pool = canvas.soft_ellipse(glow_center, 620.0, 700.0)
    mottle = canvas.noise(180.0, octaves=4)
    canvas.blend(np.clip(pool * (0.55 + 0.6 * mottle), 0.0, 1.0), warm, 0.9)


def bokeh_dusk(canvas, top=rgb("#2B2A5A"), bottom=rgb("#F2A07B"),
               lights=(rgb("#FFD28A"), rgb("#FF9E7A"), rgb("#FFE9C4"), rgb("#C7A0FF")), count=46):
    """Out-of-focus city lights at dusk: a gradient with translucent discs."""
    vertical_gradient(canvas, top, bottom, curve=1.2)
    rng = canvas.rng
    for _ in range(count):
        center = (rng.uniform(0, canvas.units_width), rng.uniform(0.25, 1.0) * canvas.units_height)
        radius = rng.uniform(BOKEH_RADIUS[0], BOKEH_RADIUS[1])
        disc = shading.blur(canvas.mask(ellipse(center, radius, radius, samples=40)), canvas.px(2.5))
        color = lights[rng.integers(len(lights))]
        glow = disc[..., None] * rng.uniform(BOKEH_OPACITY[0], BOKEH_OPACITY[1]) * color
        canvas.rgb = (1 - (1 - canvas.rgb) * (1 - glow)).astype(np.float32)  # screen: lights add up


def beach(canvas, light, horizon_y, shore_y, clouds=(), sea=(rgb("#1E78B4"), rgb("#5CC4D8")),
          sand=(rgb("#F2DDB4"), rgb("#E0C090")), foam=rgb("#FFFFFF")):
    """Summer sky, sea from the horizon to the shore, then sand with a wet edge and foam line."""
    summer_sky(canvas, list(clouds), light, focus_blur=1.2)
    xs, ys = canvas.grid()
    sea_mask = shading.smoothstep(horizon_y - 0.8, horizon_y + 0.8, ys)
    depth = shading.linear_ramp(ys, horizon_y, shore_y)[..., None]
    canvas.blend(sea_mask, sea[0] * (1 - depth) + sea[1] * depth)
    glints = canvas.rng.normal(0.0, 1.0, (canvas.height, canvas.width)).astype(np.float32)
    glints = shading.blur(glints, canvas.px(1.0))
    glints = shading.smoothstep(0.55, 0.9, glints) * sea_mask * (1 - depth[..., 0]) ** 0.5
    canvas.blend(glints, foam, 0.55)
    wave = (canvas.noise(120.0, octaves=2) - 0.5) * SHORE_WAVE_UNITS
    sand_mask = shading.smoothstep(shore_y - 1.0, shore_y + 1.0, ys + wave)
    near = shading.linear_ramp(ys, shore_y, canvas.units_height)[..., None]
    canvas.blend(sand_mask, sand[1] * (1 - near) + sand[0] * near)
    wet = sand_mask * (1 - shading.smoothstep(shore_y + 6.0, shore_y + 40.0, ys + wave))
    canvas.blend(wet, sand[1] * 0.82, 0.6)
    canvas.blend(sand_mask * (1 - shading.smoothstep(shore_y, shore_y + 7.0, ys + wave)), foam, 0.85)
