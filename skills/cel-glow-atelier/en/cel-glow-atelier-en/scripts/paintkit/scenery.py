"""paintkit.scenery: landscape and city builders.

Every function paints onto one Layer and takes positions and sizes as
fractions of the canvas (x of the width, y and sizes of the height), so a
scene keeps its composition at any resolution and can be written as JSON.
Paint far things first: sky, then ridges, then ground, then near objects.

Depth is carried by three cues used throughout: far things are smaller,
paler (haze) and less saturated.
"""
from __future__ import annotations

import numpy as np

from . import core as pk
from . import light as lt

DEFAULT_LIGHT = lt.light_vector(140.0, 30.0)


def _grid(layer: pk.Layer):
    height, width = layer.a.shape
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    return height, width, yy, xx


def fractal_line(length: int, seed: int, period: float = 0.5, octaves: int = 5,
                 roughness: float = 0.55) -> np.ndarray:
    """1D fractal noise in [0, 1]; `period` is the largest feature as a share of `length`."""
    rng = np.random.default_rng(seed)
    x = np.arange(length, dtype=np.float32)
    total, weight_sum = np.zeros(length, np.float32), 0.0
    for octave in range(octaves):
        cell = max(period * length / (2 ** octave), 2.0)
        knots = rng.random(int(length / cell) + 3).astype(np.float32)
        pos = x / cell
        index = pos.astype(int)
        t = pos - index
        t = t * t * (3.0 - 2.0 * t)
        weight = roughness ** octave
        total += (knots[index] * (1.0 - t) + knots[index + 1] * t) * weight
        weight_sum += weight
    total /= weight_sum
    return (total - total.min()) / (np.ptp(total) + 1e-6)


# --------------------------------------------------------------------------
# Sky
# --------------------------------------------------------------------------
def sky(layer: pk.Layer, top, bottom, horizon: float = 0.6) -> pk.Layer:
    """Vertical gradient that reaches `bottom` color at the horizon."""
    height, width, _, _ = _grid(layer)
    ramp = pk.linear_ramp((height, width), (0, 0), (0, horizon * height))[..., None]
    return layer.paint(np.ones((height, width), np.float32), pk.rgb(top) * (1.0 - ramp) + pk.rgb(bottom) * ramp)


def sun(layer: pk.Layer, center=(0.3, 0.42), radius: float = 0.03, color="#fff6dc",
        glow_color="#ffe2b0", glow_radius: float = 0.35, glow_opacity: float = 0.75) -> pk.Layer:
    """Sun or moon disc with its glow."""
    height, width, _, _ = _grid(layer)
    cx, cy = center[0] * width, center[1] * height
    layer.paint(pk.radial_ramp((height, width), (cx, cy), glow_radius * height), glow_color, glow_opacity)
    disc = pk.fill_mask((height, width), pk.ellipse(cx, cy, radius * height, radius * height))
    return layer.paint(pk.blur(disc, max(radius * height * 0.05, 0.8)), color)


def stars(layer: pk.Layer, count: int = 240, bottom: float = 0.6, color="#ffffff", seed: int = 0) -> pk.Layer:
    height, width, _, _ = _grid(layer)
    rng = np.random.default_rng(seed)
    mask = np.zeros((height, width), np.float32)
    ys = (rng.random(count) ** 1.5 * bottom * height).astype(int)     # denser toward the top
    xs = (rng.random(count) * width).astype(int)
    mask[ys, xs] = rng.uniform(0.4, 1.0, count)
    mask = np.maximum(mask, pk.blur(mask, height * 0.0012) * 4.0)
    return layer.paint(np.clip(mask, 0.0, 1.0), color)


def clouds(layer: pk.Layer, color="#ffffff", shadow="#b9bfd6", coverage: float = 0.45, top: float = 0.04,
           bottom: float = 0.5, scale: float = 0.30, stretch: float = 2.4, opacity: float = 0.92,
           light=None, seed: int = 0) -> pk.Layer:
    """Cumulus band. Tops catch the light, undersides take the shadow color."""
    height, width, yy, _ = _grid(layer)
    light = DEFAULT_LIGHT if light is None else light
    narrow = pk.noise((height, max(int(width / stretch), 8)), scale * height, seed=seed, octaves=5)
    field = np.asarray(pk.blur(np.repeat(narrow, int(np.ceil(stretch)), axis=1)[:, :width], 1.5))
    if field.shape[1] < width:
        field = np.pad(field, ((0, 0), (0, width - field.shape[1])), mode="edge")
    mask = pk.smoothstep(1.0 - coverage - 0.06, 1.0 - coverage + 0.10, field)
    band = pk.smoothstep(top, top + 0.08, yy / height) * (1.0 - pk.smoothstep(bottom - 0.14, bottom, yy / height))
    mask = mask * band
    layer.paint(mask, color, opacity)
    depth = height * 0.035
    under = mask * pk.blur(pk.shift(mask, float(np.sign(light[0])) * -depth * 0.5, depth), height * 0.01)
    return layer.paint(under, shadow, opacity * 0.8)


# --------------------------------------------------------------------------
# Land
# --------------------------------------------------------------------------
def ridge(layer: pk.Layer, base: float = 0.62, height: float = 0.18, color="#6f7aa6", shadow=None,
          haze=None, haze_strength: float = 0.45, snow=None, snow_depth: float = 0.25,
          period: float = 0.45, roughness: float = 0.55, light=None, seed: int = 0) -> np.ndarray:
    """Mountain ridge. Returns its mask so later calls can build on it.

    shadow: color of the slopes facing away from the light (None = flat tone).
    haze: color the ridge fades into toward its foot (use the sky's horizon color).
    snow: color of the caps, laid on the upper `snow_depth` share of the ridge.
    """
    canvas_h, width, yy, xx = _grid(layer)
    light = DEFAULT_LIGHT if light is None else light
    skyline = (base - height * fractal_line(width, seed, period, roughness=roughness)) * canvas_h
    below = yy - skyline[None, :]
    mask = np.clip(below + 0.5, 0.0, 1.0)
    layer.paint(mask, color)
    span = height * canvas_h
    if shadow is not None:
        slope = np.gradient(pk.blur(skyline[None, :], canvas_h * 0.004)[0])
        away = (slope * -np.sign(light[0]) > 0).astype(np.float32)
        # Shear the lookup so shadow edges run down the slope diagonally, like real ridgelines.
        src = np.clip(xx + np.sign(light[0]) * below * 0.55, 0, width - 1).astype(int)
        facet = away[src] * (1.0 - pk.smoothstep(span * 0.25, span * 1.1, below))
        layer.paint(pk.blur(facet, canvas_h * 0.0015) * mask, shadow, 0.85)
    if snow is not None:
        cap_line = snow_depth * span * (0.55 + 0.9 * fractal_line(width, seed + 7, 0.08, octaves=3))
        cap = np.clip((cap_line[None, :] - below) / (canvas_h * 0.004), 0.0, 1.0) * mask
        layer.paint(cap, snow, 0.95)
    if haze is not None:
        fade = pk.smoothstep(span * 0.15, span * 1.2, below) * mask
        layer.paint(fade, haze, haze_strength)
    return mask


def ground(layer: pk.Layer, top: float = 0.7, color="#6c8f4e", far_color=None, roll: float = 0.03,
           seed: int = 0) -> np.ndarray:
    """Gently rolling ground from `top` to the bottom edge. Returns its mask."""
    canvas_h, width, yy, _ = _grid(layer)
    line = (top - roll * fractal_line(width, seed, 0.9, octaves=2)) * canvas_h
    mask = np.clip(yy - line[None, :] + 0.5, 0.0, 1.0)
    layer.paint(mask, color)
    if far_color is not None:
        fade = 1.0 - pk.smoothstep(top * canvas_h, top * canvas_h + (1.0 - top) * canvas_h * 0.7, yy)
        layer.paint(fade * mask, far_color, 0.85)
    return mask


def grass(layer: pk.Layer, top: float = 0.72, bottom: float = 1.0, colors=("#7fa35a", "#557a3d", "#a5c46f"),
          count: int = 1400, length: float = 0.035, seed: int = 0) -> pk.Layer:
    """Blades as short tapered strokes; nearer blades are longer (perspective)."""
    canvas_h, width, _, _ = _grid(layer)
    rng = np.random.default_rng(seed)
    for color in colors:
        strokes = []
        for _ in range(count // len(colors)):
            depth = rng.random() ** 0.7                       # 0 far ... 1 near
            x = rng.uniform(0, width)
            y = (top + (bottom - top) * depth) * canvas_h
            size = length * canvas_h * (0.25 + 0.9 * depth) * rng.uniform(0.6, 1.3)
            lean = rng.normal(0.0, 0.35) * size
            path = np.array([[x, y], [x + lean * 0.4, y - size * 0.6], [x + lean, y - size]], np.float32)
            strokes.append((path, pk.taper(3, max(size * 0.10, 1.2), head=1.0, tail=0.0, peak=0.0)))
        layer.paint(pk.stroke_mask(layer.a.shape, strokes), color, 0.9)
    return layer


def flowers(layer: pk.Layer, top: float = 0.75, bottom: float = 1.0, colors=("#ffffff", "#ffd45e", "#f08aa0"),
            count: int = 260, size: float = 0.006, seed: int = 0) -> pk.Layer:
    canvas_h, width, _, _ = _grid(layer)
    rng = np.random.default_rng(seed)
    for color in colors:
        dots = []
        for _ in range(count // len(colors)):
            depth = rng.random() ** 0.7
            radius = size * canvas_h * (0.3 + depth)
            dots.append(pk.ellipse(rng.uniform(0, width), (top + (bottom - top) * depth) * canvas_h,
                                   radius, radius * 0.8, n=10))
        layer.paint(pk.fill_mask(layer.a.shape, dots), color)
    return layer


def water(layer: pk.Layer, top: float = 0.62, bottom: float = 1.0, tint="#1d2450", tint_strength: float = 0.22,
          ripple_color="#ffffff", ripples: int = 140, seed: int = 0) -> np.ndarray:
    """Water that mirrors whatever is already painted above `top`. Returns its mask."""
    canvas_h, width, yy, _ = _grid(layer)
    y0, y1 = int(top * canvas_h), int(bottom * canvas_h)
    scene = layer.rgb()
    mask = np.zeros((canvas_h, width), np.float32)
    mask[y0:y1] = 1.0
    span = min(y1 - y0, y0)
    mirrored = np.zeros_like(scene)
    mirrored[y0:y0 + span] = scene[y0 - span:y0][::-1]
    mirrored[y0 + span:y1] = scene[0]
    layer.paint(mask, mirrored * (1.0 - tint_strength) + pk.rgb(tint) * tint_strength)
    rng = np.random.default_rng(seed)
    strokes = []
    for _ in range(ripples):
        depth = rng.uniform(0.02, 1.0) ** 1.6
        y = y0 + depth * (y1 - y0)
        x = rng.uniform(0, width)
        half = rng.uniform(0.012, 0.07) * canvas_h * (0.4 + depth)
        path = pk.resample(np.array([[x - half, y], [x, y + rng.uniform(-1.5, 1.5)], [x + half, y]]), 10)
        strokes.append((path, pk.taper(10, rng.uniform(1.2, 3.5) * canvas_h / 1000.0, head=0.0, tail=0.0)))
    layer.paint(pk.stroke_mask(layer.a.shape, strokes) * mask, ripple_color, 0.32)
    return mask


def tree(layer: pk.Layer, base=(0.7, 0.9), height: float = 0.45, foliage="#56633f", foliage_shadow="#2b3540",
         trunk="#3a2a35", rim=None, light=None, seed: int = 0) -> np.ndarray:
    """Broadleaf tree: trunk, two boughs and a canopy of leaf clusters. Returns the canopy mask."""
    canvas_h, width, _, _ = _grid(layer)
    light = DEFAULT_LIGHT if light is None else light
    rng = np.random.default_rng(seed)
    shape = layer.a.shape
    size = height * canvas_h
    bx, by = base[0] * width, base[1] * canvas_h
    trunk_path = pk.resample(pk.spline([[bx, by], [bx + size * 0.02, by - size * 0.28],
                                        [bx - size * 0.03, by - size * 0.50], [bx + size * 0.02, by - size * 0.72]]), 40)
    trunk_mask = pk.stroke_mask(shape, (trunk_path, pk.taper(40, size * 0.075, head=1.0, tail=0.3, peak=0.0)))
    lt.paint_form(layer, trunk_mask, trunk, pk.adjust(trunk, value=0.55), light, radius=size * 0.03, softness=0.15)
    for dx in (-0.20, 0.22):
        bough = pk.resample(pk.spline([[bx, by - size * 0.50], [bx + size * dx * 0.5, by - size * 0.62],
                                       [bx + size * dx, by - size * 0.74]]), 20)
        layer.paint(pk.stroke_mask(shape, (bough, pk.taper(20, size * 0.03, head=1.0, tail=0.2, peak=0.0))),
                    pk.adjust(trunk, value=0.75))
    centers = [(-0.10, -0.62, 0.15), (0.16, -0.67, 0.17), (-0.26, -0.76, 0.13), (0.02, -0.82, 0.16),
               (0.28, -0.82, 0.14), (-0.13, -0.93, 0.12), (0.14, -0.97, 0.13)]
    clusters = [[pk.ellipse(bx + (cx + rng.normal(0, s * 0.38)) * size, by + (cy + rng.normal(0, s * 0.26)) * size,
                            rng.uniform(0.38, 0.62) * s * size, rng.uniform(0.30, 0.48) * s * size,
                            rot_deg=rng.uniform(-25, 25)) for _ in range(10)] for cx, cy, s in centers]
    # Back to front: one dark mass first, then each cluster with its own light.
    canopy = pk.fill_mask(shape, [blob for cluster in clusters for blob in cluster])
    layer.paint(canopy, foliage_shadow)
    for cluster in clusters:
        mask = pk.fill_mask(shape, cluster)
        lt.paint_form(layer, mask, foliage, foliage_shadow, light, radius=size * 0.05, threshold=0.18, softness=0.12)
        if rim is not None:
            layer.paint(lt.rim(mask, light, size * 0.014, size * 0.005), rim, 0.75)
    # Loose leaf dabs break the smooth cluster edges.
    dabs = [pk.ellipse(bx + rng.uniform(-0.40, 0.42) * size, by - rng.uniform(0.52, 1.06) * size,
                       size * 0.016, size * 0.010, rot_deg=rng.uniform(0, 180), n=10) for _ in range(90)]
    near = np.clip(pk.blur(canopy, size * 0.03) * 3.0, 0.0, 1.0)
    layer.paint(pk.fill_mask(shape, dabs) * near, pk.mix(foliage, "#ffffff", 0.18), 0.85)
    return canopy


def pine(layer: pk.Layer, base=(0.5, 0.9), height: float = 0.3, color="#2f4a3c", shadow="#1b2c2a",
         light=None, seed: int = 0) -> np.ndarray:
    """Conifer as stacked ragged tiers."""
    canvas_h, width, _, _ = _grid(layer)
    light = DEFAULT_LIGHT if light is None else light
    rng = np.random.default_rng(seed)
    size = height * canvas_h
    bx, by = base[0] * width, base[1] * canvas_h
    tiers = []
    for index in range(6):
        t = index / 5.0
        top_y = by - size * (0.16 + 0.84 * (1.0 - t) ** 0.9) - size * 0.06
        low_y = by - size * (0.10 + 0.72 * (1.0 - t))
        half = size * (0.05 + 0.20 * t)
        edge = [[bx - half + (2 * half) * k / 6 + rng.uniform(-0.01, 0.01) * size,
                 low_y + (size * 0.025 if k % 2 else 0)] for k in range(7)]
        tiers.append(np.array([[bx, top_y]] + edge[::-1]))
    trunk = np.array([[bx - size * 0.018, by], [bx + size * 0.018, by], [bx + size * 0.012, by - size * 0.2],
                      [bx - size * 0.012, by - size * 0.2]])
    layer.paint(pk.fill_mask(layer.a.shape, trunk), pk.adjust(shadow, value=0.8))
    mask = pk.fill_mask(layer.a.shape, tiers)
    layer.paint(mask, color)
    side = pk.linear_ramp(layer.a.shape, (bx - np.sign(light[0]) * -size * 0.02, 0),
                          (bx - np.sign(light[0]) * size * 0.2, 0))
    layer.paint(mask * side, shadow, 0.8)
    return mask


def tree_line(layer: pk.Layer, base: float = 0.66, height: float = 0.06, color="#3d5a45", haze=None,
              density: int = 70, pointed: bool = True, seed: int = 0) -> np.ndarray:
    """Distant band of trees: one ragged silhouette."""
    canvas_h, width, _, _ = _grid(layer)
    rng = np.random.default_rng(seed)
    shapes = []
    for _ in range(density):
        x = rng.uniform(-0.02, 1.02) * width
        tall = height * canvas_h * rng.uniform(0.5, 1.0)
        half = tall * rng.uniform(0.22, 0.4)
        by = base * canvas_h
        if pointed:
            shapes.append(np.array([[x - half, by], [x, by - tall], [x + half, by]]))
        else:
            shapes.append(pk.ellipse(x, by - tall * 0.5, half * 1.4, tall * 0.6, n=16))
    band = np.array([[0, base * canvas_h - height * canvas_h * 0.25], [width, base * canvas_h - height * canvas_h * 0.25],
                     [width, base * canvas_h + 2], [0, base * canvas_h + 2]])
    mask = pk.fill_mask(layer.a.shape, shapes + [band])
    layer.paint(mask, color)
    if haze is not None:
        layer.paint(mask, haze, 0.35)
    return mask


# --------------------------------------------------------------------------
# City
# --------------------------------------------------------------------------
CITY_TIMES = {
    # walls: facade colors; lit: share of windows with light on; lamp: street lamps on;
    # dim: how far cars and people sink into the dark.
    "day": dict(sky_top="#6fa8dc", sky_low="#dbeaf7", walls=("#d9d2c5", "#c4bcb0", "#b7c2cc", "#e2d6c0", "#a9b4be"),
                shade=0.72, glass="#7f9db8", lit_glass="#cfe3f2", lit=0.0, road="#6e7078", walk="#a8a8a6",
                mark="#e9e6d8", haze="#dbeaf7", lamp=False, glow="#ffffff", dim=0.0),
    "dusk": dict(sky_top="#3b3f7a", sky_low="#f4a57a", walls=("#6a5f7c", "#5a5a82", "#7a6680", "#4f5378", "#665a6e"),
                 shade=0.62, glass="#3a3a5e", lit_glass="#ffd68a", lit=0.38, road="#3a3a52", walk="#56546e",
                 mark="#c9c2c8", haze="#f4a57a", lamp=True, glow="#ffcf8a", dim=0.30),
    "night": dict(sky_top="#0b0f2a", sky_low="#2a2f66", walls=("#1d2140", "#252a52", "#181b36", "#2a2850", "#1f2646"),
                  shade=0.70, glass="#12142c", lit_glass="#ffd98f", lit=0.50, road="#14162c", walk="#1e2040",
                  mark="#6f73a0", haze="#2a2f66", lamp=True, glow="#ffd9a0", dim=0.50),
}


def skyline(layer: pk.Layer, base: float = 0.62, height: float = 0.2, color="#4a4f7c", window_color=None,
            lit: float = 0.3, min_width: float = 0.025, max_width: float = 0.075, seed: int = 0) -> np.ndarray:
    """Far row of towers as one silhouette, optionally dotted with lit windows."""
    canvas_h, width, _, _ = _grid(layer)
    rng = np.random.default_rng(seed)
    shape = layer.a.shape
    blocks, windows = [], []
    x, by = -0.02 * width, base * canvas_h
    while x < width * 1.02:
        w = rng.uniform(min_width, max_width) * canvas_h
        tall = height * canvas_h * rng.uniform(0.25, 1.0) ** 1.3
        blocks.append(np.array([[x, by], [x, by - tall], [x + w, by - tall], [x + w, by]]))
        if rng.random() < 0.35:           # stepped crown or mast
            inset = w * rng.uniform(0.2, 0.35)
            crown = tall * rng.uniform(0.08, 0.2)
            blocks.append(np.array([[x + inset, by - tall], [x + inset, by - tall - crown],
                                    [x + w - inset, by - tall - crown], [x + w - inset, by - tall]]))
        if window_color is not None:
            step = max(canvas_h * 0.008, 4.0)
            for wy in np.arange(by - tall + step, by - step, step):
                for wx in np.arange(x + step * 0.6, x + w - step * 0.6, step):
                    if rng.random() < lit:
                        windows.append(np.array([[wx, wy], [wx + step * 0.45, wy], [wx + step * 0.45, wy + step * 0.5],
                                                 [wx, wy + step * 0.5]]))
        x += w * rng.uniform(0.85, 1.25)
    mask = pk.fill_mask(shape, blocks)
    layer.paint(mask, color)
    if windows:
        layer.paint(pk.fill_mask(shape, windows, ss=2), window_color, 0.9)
    return mask


class StreetView:
    """One-point perspective street: camera at eye height looking down the road.

    World units are meters: X across the street, Y up, Z away from the
    camera. A point projects to screen as vanish + (X, eye - Y) * focal / Z,
    which is all the perspective a street scene needs.
    """
    ROAD_HALF, WALK_WIDTH = 3.6, 2.6
    FLOOR, BAY = 3.3, 2.8                    # storey height and window spacing (m)
    NEAR, FAR = 3.0, 420.0

    def __init__(self, layer: pk.Layer, horizon: float, vanish_x: float, eye: float = 1.6):
        self.layer = layer
        self.h, self.w = layer.a.shape
        self.vx, self.vy = vanish_x * self.w, horizon * self.h
        self.focal = 0.9 * self.h
        self.EYE = eye                      # camera height above the road (m)
        self.facade_x = self.ROAD_HALF + self.WALK_WIDTH

    def project(self, x, y, z) -> np.ndarray:
        z = np.maximum(np.asarray(z, np.float32), 0.05)
        return np.stack([self.vx + np.asarray(x, np.float32) * self.focal / z,
                         self.vy + (self.EYE - np.asarray(y, np.float32)) * self.focal / z], axis=-1)

    def ground_quad(self, x0, x1, z0, z1) -> np.ndarray:
        return self.project([x0, x1, x1, x0], [0, 0, 0, 0], [z0, z0, z1, z1])

    def wall_quad(self, side, z0, z1, y0, y1) -> np.ndarray:
        x = self.facade_x * side
        return self.project([x, x, x, x], [y0, y0, y1, y1], [z0, z1, z1, z0])


def street(layer: pk.Layer, horizon: float = 0.5, vanish_x: float = 0.5, time: str = "dusk", seed: int = 0,
           wet: float | None = None, eye: float = 1.6, light=None, cars: int = 0, people: int = 0) -> pk.Layer:
    """Street between two rows of buildings, drawn in one-point perspective.

    time: "day", "dusk" or "night" (sets sky, wall, window and lamp colors).
    wet: strength of the road reflection (None = 0.35 at night, 0 otherwise).
    eye: camera height in meters. The horizon always cuts a standing person
    at this height, so for a full-body figure put `horizon` at the figure's
    pelvis and use eye=0.9; for a bust use the eye line and eye=1.55.
    cars, people: how many cars drive on the road and how many people walk
    on the pavements. Their places come from `seed`.
    Paint a sky first if you want clouds, sun or stars; this function only
    fills the sky gradient when the layer is still empty.
    """
    if time not in CITY_TIMES:
        raise ValueError(f"unknown time '{time}', expected one of {list(CITY_TIMES)}")
    tone = CITY_TIMES[time]
    light = DEFAULT_LIGHT if light is None else light
    view = StreetView(layer, horizon, vanish_x, eye)
    rng = np.random.default_rng(seed)
    shape = layer.a.shape
    if float(layer.a.max()) == 0.0:
        sky(layer, tone["sky_top"], tone["sky_low"], horizon)
    skyline(layer, base=horizon, height=0.16, color=pk.mix(tone["walls"][1], tone["haze"], 0.6),
            window_color=tone["lit_glass"] if tone["lit"] > 0 else None, lit=tone["lit"] * 0.5, seed=seed + 3)
    _paint_street_ground(view, tone)
    # Props draw from their own generator, so adding them leaves the building layout unchanged.
    prop_rng = np.random.default_rng(seed + PROP_SEED_OFFSET)
    for side in (-1, 1):
        _paint_block_row(view, tone, side, rng, light, prop_rng)
    _paint_traffic(view, tone, int(cars), int(people), prop_rng)
    if tone["lamp"]:
        _paint_lamps(view, tone)
    wet = (0.35 if time == "night" else 0.0) if wet is None else wet
    if wet > 0:
        road = pk.fill_mask(shape, view.ground_quad(-view.ROAD_HALF, view.ROAD_HALF, view.NEAR * 0.5, view.FAR), ss=2)
        scene = layer.rgb()
        rows = np.clip((2 * view.vy - np.arange(view.h)).astype(int), 0, view.h - 1)
        mirrored = scene[rows]
        mirrored = np.stack([pk.blur(mirrored[..., c], view.h * 0.006) for c in range(3)], axis=-1)
        layer.paint(road, mirrored, wet)
    return layer


def _paint_street_ground(view: StreetView, tone: dict) -> None:
    layer, shape = view.layer, view.layer.a.shape
    near, far = view.NEAR * 0.5, view.FAR
    edge = view.facade_x
    layer.paint(pk.fill_mask(shape, view.ground_quad(-edge - 60, edge + 60, near, far), ss=2), tone["walk"])
    layer.paint(pk.fill_mask(shape, view.ground_quad(-view.ROAD_HALF, view.ROAD_HALF, near, far), ss=2), tone["road"])
    # Distance fades the ground toward the haze at the horizon.
    fade = 1.0 - pk.smoothstep(view.vy, view.vy + view.h * 0.22, np.mgrid[0:view.h, 0:view.w][0].astype(np.float32))
    ground = (np.mgrid[0:view.h, 0:view.w][0] >= view.vy).astype(np.float32)
    layer.paint(fade * ground, tone["haze"], 0.55)
    dashes = [view.ground_quad(-0.08, 0.08, z, z + 3.0) for z in np.arange(4.0, 160.0, 7.5)]
    curbs = [view.ground_quad(side * view.ROAD_HALF - 0.09, side * view.ROAD_HALF + 0.09, near, far) for side in (-1, 1)]
    layer.paint(pk.fill_mask(shape, dashes + curbs), tone["mark"], 0.8)
    stripes = [view.ground_quad(x, x + 0.45, 6.2, 9.0) for x in np.arange(-view.ROAD_HALF + 0.3, view.ROAD_HALF - 0.4, 0.9)]
    layer.paint(pk.fill_mask(shape, stripes), tone["mark"], 0.75)


def _paint_block_row(view: StreetView, tone: dict, side: int, rng, light, prop_rng) -> None:
    """One side of the street, far buildings first so near ones overlap them."""
    layer, shape = view.layer, view.layer.a.shape
    plots, z = [], 9.0 + rng.uniform(0.0, 6.0)
    while z < 260.0:
        depth = rng.uniform(11.0, 26.0)
        plots.append((z, z + depth, rng.uniform(4, 15) * view.FLOOR, rng.integers(len(tone["walls"]))))
        z += depth + (rng.uniform(2.5, 5.0) if rng.random() < 0.18 else 0.0)     # an occasional side street
    facing_light = np.sign(light[0]) * side < 0          # this row's facades look toward the light
    for z0, z1, tall, tint in plots[::-1]:
        haze = float(np.clip((z0 - 25.0) / 230.0, 0.0, 0.85))
        wall = pk.mix(tone["walls"][tint], tone["haze"], haze)
        shaded = pk.mix(pk.rgb(tone["walls"][tint]) * tone["shade"], tone["haze"], haze)
        x_near = view.facade_x * side
        end_face = view.project([x_near, x_near + 40 * side, x_near + 40 * side, x_near], [0, 0, tall, tall],
                                [z0, z0, z0, z0])
        layer.paint(pk.fill_mask(shape, end_face, ss=2), pk.mix(wall, shaded, 0.5))
        if prop_rng.random() < END_WINDOW_SHARE:
            _paint_end_windows(view, tone, side, z0, tall, haze, prop_rng)
        layer.paint(pk.fill_mask(shape, view.wall_quad(side, z0, z1, 0.0, tall), ss=2), wall if facing_light else shaded)
        _paint_windows(view, tone, side, z0, z1, tall, haze, rng)
        if z0 < 70.0:                       # shop fronts and signs are readable only up close
            _paint_shop_fronts(view, tone, side, z0, z1, haze, rng)
            if rng.random() < 0.55 and tall > 4 * view.FLOOR:
                _paint_sign(view, tone, side, rng.uniform(z0 + 1.0, z1 - 1.0), haze, rng)


SIGN_COLORS = ("#ff5fa2", "#4fd6e8", "#ffd24d", "#7dff9c", "#ff8a4d")
SHOP_BAY = 5.5                              # shop width along the street (m)


def _paint_shop_fronts(view: StreetView, tone: dict, side: int, z0, z1, haze, rng) -> None:
    """Ground-floor shop windows, one per bay, each lit or dark on its own."""
    layer, shape = view.layer, view.layer.a.shape
    dark, lit = [], []
    for zb in np.arange(z0 + 0.7, z1 - 2.0, SHOP_BAY):
        quad = view.wall_quad(side, zb, min(zb + SHOP_BAY - 0.8, z1 - 0.5), 0.45, 2.85)
        (lit if rng.random() < min(tone["lit"] * 2.0, 0.85) else dark).append(quad)
    if dark:
        layer.paint(pk.fill_mask(shape, dark, ss=2), tone["glass"], 0.9 * (1.0 - haze))
    if lit:
        layer.paint(pk.fill_mask(shape, lit, ss=2), tone["lit_glass"], 0.95 * (1.0 - haze))


def _paint_sign(view: StreetView, tone: dict, side: int, z: float, haze: float, rng) -> None:
    """Vertical signboard sticking out over the pavement; glows after dark."""
    layer, shape = view.layer, view.layer.a.shape
    x0, x1 = view.facade_x * side, (view.facade_x - 1.1) * side
    low = rng.uniform(3.6, 6.0)
    board = view.project([x0, x1, x1, x0], [low, low, low + rng.uniform(2.5, 5.0), low + 4.0], [z, z, z, z])
    board[3, 1] = board[2, 1]
    color = SIGN_COLORS[rng.integers(len(SIGN_COLORS))]
    glowing = tone["lit"] > 0
    mask = pk.fill_mask(shape, board, ss=2)
    layer.paint(mask, color if glowing else pk.mix(color, tone["walls"][0], 0.55), 1.0 - haze)
    if glowing:
        center = board.mean(axis=0)
        layer.paint(pk.radial_ramp(shape, center, 3.0 * view.focal / z), color, 0.32 * (1.0 - haze))


def _paint_windows(view: StreetView, tone: dict, side: int, z0, z1, tall, haze, rng) -> None:
    layer, shape = view.layer, view.layer.a.shape
    pixels_per_bay = view.BAY * view.focal / z1
    if pixels_per_bay < 2.5:                # windows smaller than a few pixels only add noise
        return
    dark, lit = [], []
    floors = int(tall // view.FLOOR)
    for floor in range(1, floors):
        y0 = floor * view.FLOOR + 0.9
        for zb in np.arange(z0 + 0.9, z1 - view.BAY + 0.4, view.BAY):
            quad = view.wall_quad(side, zb, zb + view.BAY * 0.62, y0, y0 + view.FLOOR * 0.50)
            (lit if rng.random() < tone["lit"] else dark).append(quad)
    fade = 1.0 - haze
    if dark:
        layer.paint(pk.fill_mask(shape, dark, ss=2), tone["glass"], 0.85 * fade)
    if lit:
        layer.paint(pk.fill_mask(shape, lit, ss=2), tone["lit_glass"], 0.95 * fade)


def _paint_lamps(view: StreetView, tone: dict) -> None:
    layer, shape = view.layer, view.layer.a.shape
    x_post = view.ROAD_HALF + 0.5
    for z in np.arange(11.0, 150.0, 17.0):
        for side in (-1, 1):
            foot, top = view.project(x_post * side, 0.0, z), view.project(x_post * side, 6.2, z)
            head = view.project((x_post - 1.2) * side, 6.3, z)
            thick = max(0.16 * view.focal / z, 1.0)
            post = pk.stroke_mask(shape, [(np.array([foot, top]), thick), (np.array([top, head]), thick * 0.8)])
            layer.paint(post, pk.adjust(tone["walls"][0], value=0.5))
            radius = 2.6 * view.focal / z
            layer.paint(pk.radial_ramp(shape, head, radius), tone["glow"], 0.75)
            layer.paint(pk.radial_ramp(shape, head, radius * 0.22), "#ffffff", 0.9)
            pool = view.project((x_post - 1.2) * side, 0.0, z)
            layer.paint(pk.radial_ramp(shape, pool, radius * 1.6, aspect=0.28), tone["glow"], 0.30)


# --------------------------------------------------------------------------
# Street props: windows on building ends, cars, people
# --------------------------------------------------------------------------
PROP_SEED_OFFSET = 101
END_WINDOW_SHARE = 0.6                      # the rest are blank party walls
END_WINDOW_SPAN = 22.0                      # windows run this far along an end wall (m)
LANE_X = 1.8                                # lane center, measured from the road middle (m)
CAR_LENGTH, CAR_HALF, CAR_ROOF_HALF = 4.4, 0.90, 0.74
CAR_FLOOR, CAR_BELT, CAR_ROOF = 0.28, 0.88, 1.46        # heights: under the sills, window line, roof
WHEEL_RADIUS = 0.33
CAR_COLORS = ("#c8423c", "#e8e8ea", "#2f3a4f", "#d9b23c", "#5a7fa8", "#3c3f46", "#f2f0ea")
COAT_COLORS = ("#8a5a44", "#3f5673", "#b7a48a", "#7a3b46", "#4f6b57", "#2e2f3a", "#c9c4b8", "#b5544a")
HAIR_COLORS = ("#2a2226", "#4a3428", "#6b4a32", "#1c1c22", "#8a6a48")
PERSON_SKIN = "#e6bfa3"


def _paint_end_windows(view: StreetView, tone: dict, side: int, z0: float, tall: float, haze: float, rng) -> None:
    """Windows on the wall that faces the camera (seen above lower neighbors and across side streets)."""
    layer, shape = view.layer, view.layer.a.shape
    if view.BAY * view.focal / z0 < 2.5:
        return
    dark, lit = [], []
    x_near = view.facade_x * side
    for floor in range(1, int(tall // view.FLOOR)):
        y0 = floor * view.FLOOR + 0.9
        for offset in np.arange(1.0, END_WINDOW_SPAN, view.BAY):
            xa, xb = x_near + side * offset, x_near + side * (offset + view.BAY * 0.58)
            quad = view.project([xa, xb, xb, xa], [y0, y0, y0 + view.FLOOR * 0.5, y0 + view.FLOOR * 0.5], [z0] * 4)
            (lit if rng.random() < tone["lit"] * 0.8 else dark).append(quad)
    fade = 1.0 - haze
    if dark:
        layer.paint(pk.fill_mask(shape, dark, ss=2), tone["glass"], 0.8 * fade)
    if lit:
        layer.paint(pk.fill_mask(shape, lit, ss=2), tone["lit_glass"], 0.95 * fade)


def _paint_traffic(view: StreetView, tone: dict, cars: int, people: int, rng) -> None:
    """Scatter cars over the two lanes and people over the pavements, then paint far to near."""
    props = []
    lane_z = {1: 12.0 + rng.uniform(0.0, 10.0), -1: 14.0 + rng.uniform(0.0, 14.0)}
    for index in range(cars):
        lane = 1 if index % 2 == 0 else -1
        props.append((lane_z[lane], "car", lane, CAR_COLORS[rng.integers(len(CAR_COLORS))]))
        lane_z[lane] += CAR_LENGTH + rng.uniform(5.0, 24.0)
    for _ in range(people):
        side = 1 if rng.random() < 0.5 else -1
        x = side * (view.ROAD_HALF + rng.uniform(0.7, view.WALK_WIDTH - 0.5))
        props.append((7.0 + 70.0 * rng.random() ** 1.6, "person", x, int(rng.integers(1 << 30))))
    for z, kind, where, extra in sorted(props, key=lambda prop: -prop[0]):
        haze = float(np.clip((z - 25.0) / 230.0, 0.0, 0.85))
        if kind == "car":
            _paint_car(view, tone, where, z, extra, haze)
        else:
            _paint_person(view, tone, where, z, np.random.default_rng(extra), haze)


def _prop_tint(tone: dict, color, haze: float) -> np.ndarray:
    return pk.mix(pk.mix(color, tone["road"], tone["dim"]), tone["haze"], haze)


def _paint_car(view: StreetView, tone: dict, lane: int, z: float, color, haze: float) -> None:
    """A sedan as two stacked boxes. lane +1 drives away (tail lights), lane -1 comes closer (headlights)."""
    layer, shape = view.layer, view.layer.a.shape
    cx, z_end = LANE_X * lane, z + CAR_LENGTH
    inner = cx - CAR_HALF * lane                              # the side that faces the road middle
    body, side_body = _prop_tint(tone, color, haze), _prop_tint(tone, pk.rgb(color) * tone["shade"], haze)
    glass, rubber = _prop_tint(tone, "#2a3442", haze), _prop_tint(tone, "#17181d", haze)
    fade, meter = 1.0 - haze, view.focal / z
    # Cabin stations along the car, from the near end: window line start, roof start, roof end, window line end.
    stations = (0.45, 1.0, CAR_LENGTH - 2.1, CAR_LENGTH - 1.3) if lane > 0 else (1.3, 2.1, CAR_LENGTH - 1.0,
                                                                                 CAR_LENGTH - 0.45)
    belt_a, roof_a, roof_b, belt_b = (z + station for station in stations)

    def fill(polygons, tint, opacity=1.0):
        layer.paint(pk.fill_mask(shape, polygons, ss=2), tint, opacity)

    def side_poly(zs, ys):
        return view.project([inner] * len(zs), ys, zs)

    def across(half, y, depth):
        return view.project([cx - half, cx + half, cx + half, cx - half], y, [depth[0], depth[0], depth[1], depth[1]])

    contact = view.ground_quad(cx - CAR_HALF - 0.15, cx + CAR_HALF + 0.15, z - 0.25, z_end + 0.25)
    layer.paint(pk.blur(pk.fill_mask(shape, contact), max(0.14 * meter, 1.0)), "#05050a", 0.5 * fade)
    wheel_ring = np.linspace(0.0, 2 * np.pi, 20)
    end_wheels = [view.project([cx + sx * (CAR_HALF - 0.02), cx + sx * (CAR_HALF - 0.26)] * 2,
                               [0.0, 0.0, 2 * WHEEL_RADIUS, 2 * WHEEL_RADIUS], [z + 0.05] * 4)[[0, 1, 3, 2]]
                  for sx in (-1, 1)]
    fill(end_wheels, rubber)
    # Side: sill-to-belt panel, cabin with glass, two wheels.
    fill([side_poly([z, z_end, z_end, z], [CAR_FLOOR, CAR_FLOOR, CAR_BELT, CAR_BELT])], side_body)
    cabin_z, cabin_y = np.array([belt_a, roof_a, roof_b, belt_b]), np.array([CAR_BELT, CAR_ROOF, CAR_ROOF, CAR_BELT])
    fill([side_poly(cabin_z, cabin_y)], side_body)
    shrink_z = (cabin_z - cabin_z.mean()) * 0.84 + cabin_z.mean()
    fill([side_poly(shrink_z, np.array([CAR_BELT + 0.05, CAR_ROOF - 0.09, CAR_ROOF - 0.09, CAR_BELT + 0.05]))], glass)
    side_wheels = [side_poly(wz + np.cos(wheel_ring) * WHEEL_RADIUS, WHEEL_RADIUS + np.sin(wheel_ring) * WHEEL_RADIUS)
                   for wz in (z + 0.85, z_end - 0.85)]
    fill(side_wheels, rubber)
    # Top surfaces show only from a camera above them.
    if view.EYE > CAR_BELT:
        fill([across(CAR_HALF, [CAR_BELT] * 4, (z, z_end))], pk.mix(body, "#ffffff", 0.10))
    if view.EYE > CAR_ROOF:
        fill([across(CAR_ROOF_HALF, [CAR_ROOF] * 4, (roof_a, roof_b))], pk.mix(body, "#ffffff", 0.16))
    # Near end: panel, slanted window, lights, plate.
    fill([across(CAR_HALF, [CAR_FLOOR, CAR_FLOOR, CAR_BELT, CAR_BELT], (z, z))], body)
    slant = view.project([cx - CAR_HALF, cx + CAR_HALF, cx + CAR_ROOF_HALF, cx - CAR_ROOF_HALF],
                         [CAR_BELT, CAR_BELT, CAR_ROOF, CAR_ROOF], [belt_a, belt_a, roof_a, roof_a])
    fill([slant], body)
    center = slant.mean(axis=0)
    fill([(slant - center) * 0.84 + center], glass)
    lamp_on = tone["lamp"]
    lamp_color = ("#ff3528" if lamp_on else "#a8281f") if lane > 0 else ("#fff3cf" if lamp_on else "#dfe5ea")
    lamps = [view.project([cx + sx * (CAR_HALF - 0.05), cx + sx * (CAR_HALF - 0.46)] * 2, [0.60, 0.60, 0.78, 0.78],
                          [z] * 4)[[0, 1, 3, 2]] for sx in (-1, 1)]
    fill(lamps, lamp_color if lamp_on else _prop_tint(tone, lamp_color, haze), fade if lamp_on else 1.0)
    fill([across(0.26, [0.40, 0.40, 0.54, 0.54], (z, z))], _prop_tint(tone, "#e9e9e2", haze), 0.9)
    if lamp_on:
        reach = (0.8 if lane > 0 else 1.1) * meter
        for lamp in lamps:
            layer.paint(pk.radial_ramp(shape, lamp.mean(axis=0), reach), lamp_color, 0.75 * fade)
            layer.paint(pk.radial_ramp(shape, lamp.mean(axis=0), reach * 0.22), "#ffffff", 0.85 * fade)
        if lane < 0:                                           # headlights throw a pool on the road
            pool = view.project(cx, 0.0, max(z - 3.5, 1.0))
            layer.paint(pk.radial_ramp(shape, pool, 2.6 * meter, aspect=0.25), lamp_color, 0.22 * fade)


def _paint_person(view: StreetView, tone: dict, x: float, z: float, rng, haze: float) -> None:
    """A walker as a few simple shapes: legs, coat, arms, head and hair."""
    layer, shape = view.layer, view.layer.a.shape
    meter, tall = view.focal / z, rng.uniform(0.93, 1.06)
    coat = _prop_tint(tone, COAT_COLORS[rng.integers(len(COAT_COLORS))], haze)
    pants = _prop_tint(tone, ("#23252e", "#3a4258", "#4a4038")[rng.integers(3)], haze)
    skin, hair = _prop_tint(tone, PERSON_SKIN, haze), _prop_tint(tone, HAIR_COLORS[rng.integers(len(HAIR_COLORS))], haze)
    faces_camera, long_coat, long_hair = rng.random() < 0.5, rng.random() < 0.4, rng.random() < 0.5
    lifted = rng.choice([-1, 1])                               # which foot is off the ground mid-step

    def at(points):
        points = np.asarray(points, np.float32) * tall
        return view.project(x + points[:, 0], points[:, 1], np.full(len(points), z))

    def limb(points, width_from, width_to, tint):
        path = pk.resample(at(points), 10)
        widths = np.maximum(np.linspace(width_from, width_to, 10) * meter * tall, 1.0)
        layer.paint(pk.stroke_mask(shape, (path, widths)), tint)

    foot = view.project(x, 0.0, z)
    layer.paint(pk.radial_ramp(shape, foot, 0.42 * meter, aspect=0.3), "#05050a", 0.4 * (1.0 - haze))
    for leg in (-1, 1):
        limb([(leg * 0.085, 0.90), (leg * 0.09, 0.48), (leg * 0.10, 0.12 if leg == lifted else 0.03)], 0.17, 0.10, pants)
    hem = 0.52 if long_coat else 0.84
    torso = at([(-0.225, 1.40), (-0.13, 1.47), (0.13, 1.47), (0.225, 1.40), (0.19, hem), (-0.19, hem)])
    layer.paint(pk.fill_mask(shape, torso, ss=2), coat)
    for arm in (-1, 1):
        limb([(arm * 0.195, 1.36), (arm * 0.235, 1.10), (arm * 0.225, 0.86)], 0.085, 0.07, pk.rgb(coat) * 0.88)
        layer.paint(pk.fill_mask(shape, pk.ellipse(*at([(arm * 0.225, 0.82)])[0], 0.04 * meter, 0.05 * meter)), skin)
    limb([(0.0, 1.44), (0.0, 1.52)], 0.09, 0.09, skin)
    head_center, rx, ry = at([(0.0, 1.615)])[0], 0.098 * meter * tall, 0.118 * meter * tall
    head = pk.fill_mask(shape, pk.ellipse(*head_center, rx, ry), ss=2)
    layer.paint(head, skin)
    crown = pk.fill_mask(shape, pk.ellipse(head_center[0], head_center[1] - ry * 0.12, rx * 1.12, ry * 1.08), ss=2)
    if faces_camera:
        rows = np.mgrid[0:shape[0], 0:shape[1]][0].astype(np.float32)
        crown = crown * (rows < head_center[1] - ry * 0.25)   # hair stays above the face
    layer.paint(crown, hair)
    if long_hair:
        fall = at([(-0.105, 1.64), (-0.125, 1.36), (0.125, 1.36), (0.105, 1.64)])
        behind = pk.fill_mask(shape, fall, ss=2)
        layer.paint(behind * (1.0 - head) if faces_camera else behind, hair)


# --------------------------------------------------------------------------
# Interior
# --------------------------------------------------------------------------
ROOM_WINDOWS = ("day", "night", "none")
ROOM_GLASS = {"day": ("#8ec3ec", "#e2f1fb"), "night": ("#0e1830", "#2b3b68")}
ROOM_FRAME = "#f5f1ea"
ROOM_PLANK = 0.075            # floorboard width at the bottom edge (share of the canvas width)
ROOM_VANISH_RISE = 0.35       # vanishing point of the floorboards, above the floor line (share of height)


def room(layer: pk.Layer, floor: float = 0.70, wall="#e7dccd", floor_color="#a47a55", baseboard="#f3eee6",
         window: str = "day", window_x: float = 0.24, window_width: float = 0.28, window_top: float = 0.12,
         window_bottom: float = 0.55, curtain="#c9b49c", vanish_x: float = 0.5, lamp=None, lamp_color="#ffcf8a",
         art=None, art_color="#7d93b5", seed: int = 0) -> pk.Layer:
    """Interior for figures indoors (bedroom, living room): a wall with a curtained window
    (day or night), a wooden floor in perspective and a baseboard; optionally the warm
    glow of a lamp ([x, y]) and a framed picture ([x, y, width, height]). Canvas fractions."""
    if window not in ROOM_WINDOWS:
        raise ValueError(f"unknown room window '{window}', expected one of {ROOM_WINDOWS}")
    height, width, yy, xx = _grid(layer)
    shape = (height, width)
    floor_y = floor * height
    # Wall: lighter in the middle, darker toward the corners and the ceiling.
    edge = np.abs(xx / width - 0.5) * 2.0
    tone = 1.0 - 0.10 * edge ** 2 - 0.08 * np.clip(1.0 - yy / floor_y, 0.0, 1.0)
    layer.paint(np.ones(shape, np.float32), pk.rgb(wall)[None, None, :] * tone[..., None])
    if art is not None:
        _room_art(layer, shape, art, art_color)
    if window != "none":
        _room_window(layer, shape, window, window_x, window_width, window_top, window_bottom, floor_y, curtain, seed)
    _room_floor(layer, shape, floor_y, floor_color, vanish_x)
    board = pk.fill_mask(shape, np.array([[0, floor_y - 0.02 * height], [width, floor_y - 0.02 * height],
                                          [width, floor_y], [0, floor_y]], np.float32))
    layer.paint(board, baseboard)
    layer.paint(pk.fill_mask(shape, np.array([[0, floor_y - 0.0215 * height], [width, floor_y - 0.0215 * height],
                                              [width, floor_y - 0.019 * height], [0, floor_y - 0.019 * height]],
                                             np.float32)), pk.adjust(baseboard, value=0.8), 0.8)
    if window == "day":                       # sunlight lying on the floor in front of the window
        x0, x1 = (window_x - window_width / 2) * width, (window_x + window_width / 2) * width
        drift = (vanish_x * width - window_x * width) * 0.25
        patch = np.array([[x0, floor_y + 0.01 * height], [x1, floor_y + 0.01 * height],
                          [x1 + drift + 0.10 * width, floor_y + 0.20 * height],
                          [x0 + drift - 0.02 * width, floor_y + 0.20 * height]], np.float32)
        layer.paint(pk.blur(pk.fill_mask(shape, patch), 0.02 * height), "#fff4da", 0.35)
    if lamp is not None:
        center = (lamp[0] * width, lamp[1] * height)
        layer.paint(pk.radial_ramp(shape, center, 0.40 * height) ** 1.6, lamp_color, 0.45)
    return layer


def _room_window(layer, shape, window, cx, w, top, bottom, floor_y, curtain, seed):
    height, width = shape
    x0, x1, y0, y1 = (cx - w / 2) * width, (cx + w / 2) * width, top * height, bottom * height
    pane = pk.fill_mask(shape, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32))
    upper, lower = ROOM_GLASS[window]
    ramp = pk.linear_ramp(shape, (0, y0), (0, y1))[..., None]
    layer.paint(pane, pk.rgb(upper) * (1.0 - ramp) + pk.rgb(lower) * ramp)
    if window == "night":
        rng = np.random.default_rng(seed)
        dots = [(pk.ellipse(rng.uniform(x0, x1), rng.uniform(y0, y1), 1.2, 1.2), ) for _ in range(40)]
        layer.paint(pk.fill_mask(shape, [d[0] for d in dots]) * pane, "#ffffff", 0.8)
        moon = (x0 + (x1 - x0) * 0.7, y0 + (y1 - y0) * 0.25)
        layer.paint(pk.radial_ramp(shape, moon, 0.10 * height) * pane, "#a8b8e8", 0.5)
        layer.paint(pk.fill_mask(shape, pk.ellipse(moon[0], moon[1], 0.022 * height, 0.022 * height)), "#f4f1e0")
    else:
        layer.paint(pk.radial_ramp(shape, ((x0 + x1) / 2, y0 + (y1 - y0) * 0.3), 0.25 * height) * pane, "#ffffff", 0.4)
    bar = 0.012 * height
    frame = [np.array([[x0 - bar, y0 - bar], [x1 + bar, y0 - bar], [x1 + bar, y0], [x0 - bar, y0]]),
             np.array([[x0 - bar, y1], [x1 + bar, y1], [x1 + bar, y1 + bar * 1.8], [x0 - bar, y1 + bar * 1.8]]),
             np.array([[x0 - bar, y0], [x0, y0], [x0, y1], [x0 - bar, y1]]),
             np.array([[x1, y0], [x1 + bar, y0], [x1 + bar, y1], [x1, y1]]),
             np.array([[(x0 + x1) / 2 - bar / 2, y0], [(x0 + x1) / 2 + bar / 2, y0], [(x0 + x1) / 2 + bar / 2, y1],
                       [(x0 + x1) / 2 - bar / 2, y1]]),
             np.array([[x0, y0 + (y1 - y0) * 0.45 - bar / 2], [x1, y0 + (y1 - y0) * 0.45 - bar / 2],
                       [x1, y0 + (y1 - y0) * 0.45 + bar / 2], [x0, y0 + (y1 - y0) * 0.45 + bar / 2]])]
    layer.paint(pk.fill_mask(shape, [f.astype(np.float32) for f in frame]), ROOM_FRAME)
    # Curtains gathered at both sides, hanging in vertical folds from a rod to the floor.
    span = (x1 - x0) * 0.32
    rod_y = y0 - 0.045 * height
    _, _, yy, xx = _grid(layer)
    for left, right in ((x0 - span * 0.75, x0 + span * 0.35), (x1 - span * 0.35, x1 + span * 0.75)):
        drape = pk.fill_mask(shape, np.array([[left, rod_y], [right, rod_y], [right + span * 0.08, floor_y - 0.01 * height],
                                              [left - span * 0.10, floor_y - 0.01 * height]], np.float32))
        folds = 0.5 + 0.5 * np.cos((xx - left) / max(span * 0.18, 1.0) * np.pi)
        layer.paint(drape, curtain)
        layer.paint(drape * folds, pk.adjust(curtain, value=0.78), 0.55)
        layer.paint(drape * (1.0 - folds) ** 3, pk.mix(curtain, "#ffffff", 0.35), 0.35)
    rod = pk.fill_mask(shape, np.array([[x0 - span, rod_y - 0.004 * height], [x1 + span, rod_y - 0.004 * height],
                                        [x1 + span, rod_y + 0.004 * height], [x0 - span, rod_y + 0.004 * height]],
                                       np.float32))
    layer.paint(rod, "#5a4a3e")


def _room_floor(layer, shape, floor_y, color, vanish_x):
    height, width = shape
    floor = pk.fill_mask(shape, np.array([[0, floor_y], [width, floor_y], [width, height], [0, height]], np.float32))
    ramp = pk.linear_ramp(shape, (0, floor_y), (0, height))[..., None]
    base = pk.rgb(color)
    layer.paint(floor, base * (0.80 + 0.25 * ramp))
    vanish = np.array([vanish_x * width, floor_y - ROOM_VANISH_RISE * height], np.float32)
    strokes = []
    step = ROOM_PLANK * width
    for bottom_x in np.arange(-width, 2.0 * width, step):
        start = np.array([bottom_x, height], np.float32)
        t = (height - floor_y) / (height - vanish[1])          # where the line meets the floor line
        end = start + (vanish - start) * t
        strokes.append((pk.resample(np.array([start, end], np.float32), 8), 1.2))
    layer.paint(pk.stroke_mask(shape, strokes) * floor, pk.adjust(color, value=0.6), 0.35)


def _room_art(layer, shape, art, color):
    """Framed picture: a dark wood frame, a pale mat and a simple two-tone landscape inside."""
    height, width = shape
    x, y, w, h = art[0] * width, art[1] * height, art[2] * width, art[3] * height
    rect = lambda a, b, c, d: pk.fill_mask(shape, np.array([[a, b], [c, b], [c, d], [a, d]], np.float32))  # noqa: E731
    layer.paint(rect(x, y, x + w, y + h), "#4a3a2e")
    rim = 0.012 * height
    layer.paint(rect(x + rim, y + rim, x + w - rim, y + h - rim), "#f2ede4")
    inner = (x + rim * 2.5, y + rim * 2.5, x + w - rim * 2.5, y + h - rim * 2.5)
    layer.paint(rect(*inner), pk.mix(color, "#ffffff", 0.45))
    hill = np.array([[inner[0], inner[3]], [inner[0], inner[1] + (inner[3] - inner[1]) * 0.62],
                     [inner[0] + (inner[2] - inner[0]) * 0.45, inner[1] + (inner[3] - inner[1]) * 0.45],
                     [inner[2], inner[1] + (inner[3] - inner[1]) * 0.66], [inner[2], inner[3]]], np.float32)
    layer.paint(pk.fill_mask(shape, hill), color)
