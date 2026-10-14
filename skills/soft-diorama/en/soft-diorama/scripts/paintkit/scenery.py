"""Background elements: sky, clouds, bokeh, light, leaves, petals, washes.

Paint these before the subject. To push a background out of focus, blur
`cv.color` (paintkit.blur) right before drawing the subject.
"""
import cv2
import numpy as np

from . import config, geometry, raster
from .color import light_of, mix, rgb, shadow_of


def _rng(seed):
    return np.random.default_rng(config.DEFAULT_SEED if seed is None else seed)


def sky(cv, top='#4f86d9', bottom='#cfe6f7', horizon_y=None):
    """Vertical sky gradient from the top edge down to horizon_y (default: canvas bottom)."""
    horizon_y = cv.height if horizon_y is None else horizon_y
    field = cv.linear((0, 0), (0, horizon_y))
    cv.fill(cv.full(), cv.ramp(field ** 0.8, top, bottom))


def clouds(cv, y_range, color='#ffffff', coverage=0.45, scale=260.0, edge=10.0, opacity=0.9, seed=None):
    """Soft streaky cloud layer (cirrus, haze) between y_range=(top, bottom).

    For puffy anime clouds use cumulus()/cloud_bank() instead.
    edge: softness of the cloud boundary in px.
    """
    y0, y1 = y_range
    streaks = raster.noise_field(cv.size, scale, 5, seed, stretch=(3.0, 0.8))
    ys = np.arange(cv.height, dtype=np.float32)[:, None]
    center, half = 0.5 * (y0 + y1), 0.5 * (y1 - y0)
    envelope = np.clip(1.0 - np.abs((ys - center) / half) ** 2, 0.0, 1.0)
    level = 1.0 - coverage
    mask = raster.smoothstep(streaks, level - 0.06, level + 0.10) * envelope
    mask = raster.blur(mask, edge * 0.3)
    cv.tint(mask, color, 'normal', opacity)
    return mask


def cumulus(cv, center, width, height, color='#ffffff', shade='#b9cdec', light=(-0.5, -1.0),
            puffs=22, edge=1.0, opacity=1.0, seed=None):
    """One puffy cloud built from overlapping circles, flat underneath.

    Two tones, as in anime backgrounds: the whole shape in the shade color,
    then a copy of every puff nudged toward the light in the lit color.
    """
    rng = _rng(seed)
    cx, base_y = center
    lx, ly = light[0] / np.hypot(*light), light[1] / np.hypot(*light)
    dark, lit = [], []
    for _ in range(puffs):
        t = rng.uniform(-1.0, 1.0)
        envelope = (1.0 - t * t) ** 0.6
        r = height * rng.uniform(0.22, 0.48) * (0.35 + 0.65 * envelope)
        x = cx + t * width * 0.5
        y = base_y - r * rng.uniform(0.3, 0.9) - height * 0.35 * envelope * rng.uniform(0.0, 1.0)
        dark.append(geometry.ellipse_points(x, y, r * 1.15, r, 0.0, 40))
        lit.append(geometry.ellipse_points(x + lx * r * 0.22, y + ly * r * 0.30, r * 0.98, r * 0.80, 0.0, 40))
    floor = (np.arange(cv.height, dtype=np.float32)[:, None] < base_y + height * 0.04).astype(np.float32)
    body = raster.blur(cv.polygon(*dark) * floor, edge)
    top = raster.blur(cv.polygon(*lit) * floor, edge) * body
    cv.tint(body, shade, 'normal', opacity)
    cv.tint(top, color, 'normal', opacity)
    # Bounce light warms the underside slightly so the shade is not a flat sticker.
    cv.tint(body * (1.0 - top) * cv.linear((0, base_y - height), (0, base_y)) ** 2, mix(shade, color, 0.5),
            'normal', 0.5 * opacity)
    return body


def cloud_bank(cv, y_range, count=6, size=(260, 620), color='#ffffff', shade='#b9cdec', light=(-0.5, -1.0),
               edge=1.0, seed=None):
    """Several cumulus clouds scattered in a band; larger ones sit lower (closer)."""
    rng = _rng(seed)
    y0, y1 = y_range
    spots = sorted((rng.uniform(0.0, 1.0), rng.uniform(-0.1, 1.1)) for _ in range(count))
    for index, (depth, x_fraction) in enumerate(spots):
        width = size[0] + (size[1] - size[0]) * depth
        cumulus(cv, (x_fraction * cv.width, y0 + (y1 - y0) * depth), width, width * rng.uniform(0.32, 0.46),
                color, shade, light, puffs=int(14 + 14 * depth), edge=edge, seed=(seed or 0) * 100 + index)


def bokeh(cv, count=40, colors=('#fff2c9', '#ffd1e0', '#cfe9ff'), radius=(14, 60), region=None,
          opacity=0.35, softness=0.18, seed=None):
    """Out-of-focus light discs. softness: edge blur as a fraction of each radius."""
    rng = _rng(seed)
    x0, y0, x1, y1 = region or (0, 0, cv.width, cv.height)
    for _ in range(count):
        r = rng.uniform(*radius)
        cx, cy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        disc = raster.blur(cv.ellipse(cx, cy, r, r), max(r * softness, 0.8))
        ring = disc * (1.0 - 0.35 * raster.blur(cv.ellipse(cx, cy, r * 0.8, r * 0.8), r * 0.15))
        cv.tint(ring, colors[rng.integers(len(colors))], 'screen', opacity * rng.uniform(0.4, 1.0))


def sun_glow(cv, center, radius, color='#fff3d0', opacity=0.8):
    """Soft luminous haze around a light source."""
    field = cv.radial(center, radius)
    cv.tint(field ** 2.2, color, 'screen', opacity)
    cv.tint(field ** 0.9, color, 'screen', opacity * 0.35)


def light_rays(cv, origin, angle_deg=70.0, spread_deg=50.0, count=7, length=None, color='#fff6dc',
               opacity=0.22, seed=None):
    """Fan of soft light shafts from `origin` (can be off-canvas)."""
    rng = _rng(seed)
    length = length or 1.6 * max(cv.width, cv.height)
    rays = cv.empty()
    for _ in range(count):
        a = np.radians(angle_deg + rng.uniform(-0.5, 0.5) * spread_deg)
        w = np.radians(rng.uniform(1.0, 4.5))
        p1 = (origin[0] + length * np.cos(a - w), origin[1] + length * np.sin(a - w))
        p2 = (origin[0] + length * np.cos(a + w), origin[1] + length * np.sin(a + w))
        rays = np.maximum(rays, cv.polygon(np.array([origin, p1, p2])) * rng.uniform(0.4, 1.0))
    fade = 1.0 - cv.radial(origin, length * 0.85) ** 0.5
    cv.tint(raster.blur(rays, 10.0) * (1.0 - fade), color, 'screen', opacity)


def horizon_sea(cv, horizon_y, far='#8fc3e8', near='#2f6fb0', sparkle=0.5, seed=None):
    """Sea from horizon_y to the bottom edge with sun glitter streaks."""
    rng = _rng(seed)
    region = cv.polygon(np.array([(0, horizon_y), (cv.width, horizon_y), (cv.width, cv.height), (0, cv.height)]))
    cv.fill(region, cv.ramp(cv.linear((0, horizon_y), (0, cv.height)) ** 0.6, far, near))
    streaks = []
    for _ in range(int(120 * sparkle)):
        depth = rng.uniform(0.0, 1.0) ** 1.8
        y = horizon_y + 4 + depth * (cv.height - horizon_y)
        x = rng.uniform(0, cv.width)
        half = rng.uniform(6, 26) * (0.3 + depth)
        streaks.append(([(x - half, y), (x + half, y)], 1.2 + 3.0 * depth, 'taper'))
    if streaks:
        cv.tint(cv.ribbons(streaks) * region, '#ffffff', 'screen', 0.55)
    return region


def hills(cv, base_y, amplitude, color, scale=300.0, seed=None, edge=1.2):
    """A rolling ridge silhouette filled down to the bottom edge (stack several for depth)."""
    rng = _rng(seed)
    xs = np.linspace(0, cv.width, 96)
    profile = np.zeros_like(xs)
    for octave in range(4):
        freq = (2 ** octave) / scale
        profile += np.sin(xs * freq * 2 * np.pi + rng.uniform(0, 6.28)) / (2 ** octave)
    ridge = np.stack([xs, base_y + amplitude * profile / 1.9], axis=1)
    mask = cv.polygon(np.vstack([ridge, [(cv.width, cv.height), (0, cv.height)]]))
    cv.fill(raster.blur(mask, edge) if edge > 1.5 else mask, color)
    return mask


def leaves(cv, center, reach, count=60, colors=('#3f7d4f', '#5fa060', '#2d5d45'), size=38.0,
           blur_px=0.0, direction_deg=None, seed=None):
    """Cluster of pointed leaves around `center` (use at corners to frame the subject).

    blur_px > 0 puts the cluster out of focus (foreground framing).
    direction_deg: leaves point roughly this way; None = outward from the center.
    """
    rng = _rng(seed)
    order = np.argsort(rng.random(count))
    for index in order:
        angle = rng.uniform(0, 2 * np.pi)
        distance = reach * rng.uniform(0.0, 1.0) ** 0.7
        cx, cy = center[0] + distance * np.cos(angle), center[1] + distance * np.sin(angle)
        heading = np.degrees(angle) if direction_deg is None else direction_deg
        heading += rng.normal(0, 28)
        length = size * rng.uniform(0.6, 1.3)
        tip = (cx + length * np.cos(np.radians(heading)), cy + length * np.sin(np.radians(heading)))
        bend = rng.normal(0, 0.18) * length
        mid = (0.5 * (cx + tip[0]) - bend * np.sin(np.radians(heading)),
               0.5 * (cy + tip[1]) + bend * np.cos(np.radians(heading)))
        leaf = cv.ribbon([(cx, cy), mid, tip], length * rng.uniform(0.38, 0.5), 'taper')
        if blur_px > 0:
            leaf = raster.blur(leaf, blur_px)
        tone = rgb(colors[rng.integers(len(colors))])
        cv.fill(leaf, tone) if blur_px == 0 else cv.tint(leaf, tone, 'normal')
        vein = raster.blur(cv.ribbon([(cx, cy), mid, tip], length * 0.10, 'taper'), max(blur_px, 0.6))
        cv.tint(vein * leaf, light_of(tone, 1.2), 'normal', 0.6)


def petals(cv, count=40, color='#ffd3e2', size=16.0, region=None, blur_range=(0.0, 3.0), seed=None):
    """Drifting petals; larger ones are blurred more, as if closer to the lens."""
    rng = _rng(seed)
    x0, y0, x1, y1 = region or (0, 0, cv.width, cv.height)
    for _ in range(count):
        scale = rng.uniform(0.5, 1.8)
        petal = cv.ellipse(rng.uniform(x0, x1), rng.uniform(y0, y1), size * scale, size * scale * 0.55,
                           rng.uniform(0, 180))
        amount = blur_range[0] + (blur_range[1] - blur_range[0]) * (scale - 0.5) / 1.3
        petal = raster.blur(petal, amount) if amount > 0.3 else petal
        tone = mix(color, '#ffffff', rng.uniform(0.0, 0.5))
        cv.tint(petal, tone, 'normal', rng.uniform(0.65, 0.95))


def wash_backdrop(cv, colors=('#f3d9c9', '#c9dcea', '#e9e2f3'), scale=360.0, strength=1.0, seed=None):
    """Loose blended color fields - an abstract backdrop for portraits and watercolor."""
    seed = config.DEFAULT_SEED if seed is None else seed
    for index, tone in enumerate(colors):
        field = raster.noise_field(cv.size, scale, 3, seed + 31 * index)
        cv.tint(raster.smoothstep(field, 0.38, 0.72), tone, 'normal', strength * (0.9 if index == 0 else 0.7))


_RIDGE_WARP = 0.22          # share of `scale` by which mountain peaks shift sideways ...
_RIDGE_WARP_PERIOD = 2.7    # ... over this many `scale` lengths (not a whole number: no repeat)
_RIDGE_ENVELOPE = 0.45      # how much lower the lowest broad peaks are than the highest ...
_RIDGE_ENVELOPE_PERIOD = 3.3  # ... varying over this many `scale` lengths


def mountains(cv, base_y, height, color, jagged=0.5, scale=420.0, snow=None, light=(-0.5, -1.0), seed=None):
    """A mountain ridge: broad peaks with finer crags. snow = color for lit caps (optional).

    Returns the ridge mask. Stack 2-3 with lighter, bluer colors toward the back
    for aerial perspective.
    """
    rng = _rng(seed)
    xs = np.linspace(0, cv.width, 160)
    profile = np.zeros_like(xs)
    # Octaves at whole multiples of one frequency repeat every `scale` px (a row of identical peaks):
    # a slow warp spaces the peaks unevenly and a slow envelope gives them different heights.
    warped = xs + _RIDGE_WARP * scale * np.sin(xs / (_RIDGE_WARP_PERIOD * scale) * 2 * np.pi + rng.uniform(0, 6.28))
    envelope = 1.0 - _RIDGE_ENVELOPE * (0.5 + 0.5 * np.sin(xs / (_RIDGE_ENVELOPE_PERIOD * scale) * 2 * np.pi
                                                            + rng.uniform(0, 6.28)))
    for octave in range(5):
        weight = (0.34 + jagged * 0.22) ** octave
        phase = rng.uniform(0, 6.28)
        wave = np.sin(warped * (2 ** octave) / scale * 2 * np.pi + phase)
        if octave < 2:
            profile += weight * envelope * (1.0 - 2.0 * np.abs(wave))         # |sin| gives pointed peaks
        else:
            profile += weight * wave
    profile = (profile - profile.min()) / max(np.ptp(profile), 1e-6)
    ridge = np.stack([xs, base_y - height * profile], axis=1)
    mask = cv.polygon(np.vstack([ridge, [(cv.width, cv.height), (0, cv.height)]]))
    base = rgb(color)
    cv.fill(mask, base)
    # Faces turned from the light: offset shadow broken up by noise so it reads as rock planes.
    lx = light[0] / np.hypot(*light)
    shade = mask * (1.0 - raster.shift(mask, lx * height * 0.22, height * 0.10))
    crags = raster.smoothstep(raster.noise_field(cv.size, scale * 0.18, 3, (seed or 0) + 9, stretch=(0.6, 1.6)),
                              0.42, 0.50)
    cv.tint(np.maximum(shade, crags * mask * 0.55), shadow_of(base, 0.9), 'normal', 0.75)
    if snow is not None:
        top = raster.smoothstep(cv.linear((0, base_y - height * 0.45), (0, base_y - height)), 0.15, 0.55)
        cv.tint(top * mask * (1.0 - np.maximum(shade, crags * 0.8)), snow, 'normal', 0.95)
    return mask


def tree(cv, base, height, kind='round', leaf='#4f8f57', trunk='#6a4a3a', light=(-0.5, -1.0),
         line_width=0.0, seed=None):
    """A simple tree. kind: 'round' (leafy canopy of puffs) or 'pine' (stacked tiers)."""
    rng = _rng(seed)
    x, y = base
    lx, ly = light[0] / np.hypot(*light), light[1] / np.hypot(*light)
    trunk_mask = cv.ribbon([(x, y), (x + rng.normal(0, 0.02) * height, y - height * 0.45)],
                           height * 0.10, [1.0, 0.7, 0.4])
    cv.paint_form(trunk_mask, trunk, light, shadow=0.35, line_width=line_width)
    lit_color, dark_color = rgb(leaf), shadow_of(leaf, 1.1)
    if kind == 'pine':
        tiers = []
        for i in range(6):
            t = i / 5.0
            tier_y = y - height * (0.18 + 0.72 * t)
            half = height * 0.26 * (1.0 - 0.78 * t)
            tiers.append(np.array([(x - half, tier_y + height * 0.16), (x, tier_y - height * 0.14),
                                   (x + half, tier_y + height * 0.16), (x + half * 0.4, tier_y + height * 0.12),
                                   (x, tier_y + height * 0.14), (x - half * 0.4, tier_y + height * 0.12)]))
        canopy = cv.polygon(*tiers)
        cv.fill(canopy, lit_color)
        cv.tint(canopy * (1.0 - raster.shift(canopy, lx * height * 0.07, ly * height * 0.02)), dark_color, 'normal', 0.9)
    elif kind == 'round':
        # Three tones of leaf clumps: shaded mass, lit clumps nudged toward the light, small sunlit tips.
        dark, lit, tips = [], [], []
        for _ in range(26):
            angle, reach = rng.uniform(0, 2 * np.pi), rng.uniform(0.0, 1.0) ** 0.6
            r = height * rng.uniform(0.07, 0.15)
            px = x + np.cos(angle) * reach * height * 0.28
            py = y - height * 0.66 + np.sin(angle) * reach * height * 0.24
            dark.append(geometry.ellipse_points(px, py, r, r * 0.9, 0.0, 28))
            lit.append(geometry.ellipse_points(px + lx * r * 0.45, py + ly * r * 0.45, r * 0.74, r * 0.62, 0.0, 28))
            if rng.random() < 0.6:
                tips.append(geometry.ellipse_points(px + lx * r * 0.85, py + ly * r * 0.85, r * 0.36, r * 0.28, 0.0, 20))
        canopy = cv.polygon(*dark)
        cv.fill(canopy, dark_color)
        cv.tint(cv.polygon(*lit) * canopy, lit_color, 'normal')
        cv.tint(cv.polygon(*tips) * canopy, light_of(leaf, 1.6), 'normal', 0.9)
        under = canopy * cv.linear((0, y - height * 0.62), (0, y - height * 0.40))
        cv.tint(under, shadow_of(leaf, 1.8), 'normal', 0.55)
    else:
        raise ValueError(f'unknown tree kind: {kind}')
    if line_width > 0:
        cv.outline(canopy, line_width, shadow_of(leaf, 2.2))
    return np.maximum(canopy, trunk_mask)


def grass(cv, y_range, count=260, colors=('#5c9a4e', '#7fb45a', '#3f7a45'), blade=(18, 46), seed=None):
    """Blades of grass scattered in a band; taller toward the bottom (closer)."""
    rng = _rng(seed)
    y0, y1 = y_range
    groups = {index: [] for index in range(len(colors))}
    for _ in range(count):
        depth = rng.uniform(0, 1) ** 0.7
        x, y = rng.uniform(0, cv.width), y0 + (y1 - y0) * depth
        length = (blade[0] + (blade[1] - blade[0]) * depth) * rng.uniform(0.7, 1.2)
        lean = rng.normal(0, 0.35) * length
        points = [(x, y), (x + lean * 0.35, y - length * 0.6), (x + lean, y - length)]
        groups[int(rng.integers(len(colors)))].append((points, 2.0 + 3.5 * depth, 'in'))
    for index, strokes in groups.items():
        if strokes:
            cv.fill(cv.ribbons(strokes), colors[index])


def water_reflection(cv, water_y, depth=None, darken=0.25, ripple=6.0, tint='#2f5f8a', seed=None):
    """Mirror whatever is above water_y into the area below it, with ripples.

    Call after painting everything that should be reflected.
    """
    depth = depth or (cv.height - water_y)
    depth = int(min(depth, cv.height - water_y, water_y))
    source = cv.color[water_y - depth:water_y][::-1].copy()
    rows = np.arange(depth, dtype=np.float32)[:, None]
    cols = np.arange(cv.width, dtype=np.float32)[None, :]
    noise = raster.noise_field((cv.width, depth), 90.0, 3, seed, stretch=(4.0, 0.35)) - 0.5
    shift_x = noise * ripple * 2.0 * (0.4 + rows / depth * 1.6)
    warped = cv2.remap(source, cols + shift_x, rows + np.zeros_like(shift_x), cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT)
    warped = cv2.GaussianBlur(warped, (0, 0), sigmaX=1.2, sigmaY=2.5)
    fade = (rows / depth)[..., None] ** 0.8
    mixed = warped * (1.0 - darken) * (1.0 - 0.45 * fade) + rgb(tint) * (darken + 0.45 * fade * (1.0 - darken))
    cv.color[water_y:water_y + depth] = mixed
