"""Shared pieces for scene paintings: time-of-day skies, sun, moon, stars, clouds, rain, ridges,
haze, wet-ground light reflections and foliage.

Why: landscape and city paintings share the same sky and atmosphere. Aerial
perspective (far things fade toward the horizon color and lose contrast) is
what makes a flat stack of silhouettes read as deep space, so every scene
element passes its color through `haze` with a depth value.

Time of day (spec `scene.time`) is one table row per preset: sky colors here,
element colors in each scene module, and a few switches (FX) that turn on the
effects a painter would add for that light: a sun path on water, lit windows
and street lamps, a moon and stars, rain and its reflections on wet ground.

Coordinates are pixels; sizes are given as fractions of the canvas so a
scene can be rendered at any resolution.
"""
import numpy as np

import geom
from raster import hex_rgb, mix
from scene import Drawable

DUSK = {
    'zenith': '#1F2A55', 'upper': '#3E447F', 'middle': '#9A6A93', 'lower': '#EE8D66', 'horizon': '#FFD28E',
    'sun': '#FFF6DE', 'sun_glow': '#FFB874', 'cloud_top': '#56507F', 'cloud_lit': '#F6A07D',
    'cloud_rim': '#FFD9A8', 'haze': '#E8A291',
}


SKIES = {
    'dusk': DUSK,
    'day': {'zenith': '#2C6BC0', 'upper': '#4C8CD6', 'middle': '#7DB2E6', 'lower': '#B4D5F0', 'horizon': '#E2EEF5',
            'sun': '#FFFFF6', 'sun_glow': '#FFF6DA', 'cloud_top': '#FFFFFF', 'cloud_lit': '#B9C6D8',
            'cloud_rim': '#FFFFFF', 'haze': '#C6DAEA', 'moon': '#F4F2E6', 'star': '#FFFFFF', 'rain': '#FFFFFF'},
    'golden': {'zenith': '#3A6AAE', 'upper': '#7AA0CE', 'middle': '#E2C4A0', 'lower': '#F6B266', 'horizon': '#FFE09C',
               'sun': '#FFF8E2', 'sun_glow': '#FFCF78', 'cloud_top': '#A7A3C6', 'cloud_lit': '#FFC486',
               'cloud_rim': '#FFE8B6', 'haze': '#EEC89E', 'moon': '#F4F2E6', 'star': '#FFFFFF', 'rain': '#FFFFFF'},
    'blue_night': {'zenith': '#0A1232', 'upper': '#15225A', 'middle': '#2A3E84', 'lower': '#4A62A8',
                   'horizon': '#8C98CE', 'sun': '#FFFFFF', 'sun_glow': '#8C98CE', 'cloud_top': '#1A234E',
                   'cloud_lit': '#3A4A88', 'cloud_rim': '#7484C4', 'haze': '#4C5C98', 'moon': '#F2F0DE',
                   'star': '#E8ECFF', 'rain': '#FFFFFF'},
    'rain_night': {'zenith': '#11161F', 'upper': '#18202C', 'middle': '#232C3A', 'lower': '#3A3F4C',
                   'horizon': '#6A6258', 'sun': '#FFFFFF', 'sun_glow': '#6A6258', 'cloud_top': '#1A202A',
                   'cloud_lit': '#353B48', 'cloud_rim': '#4E5462', 'haze': '#3C434F', 'moon': '#F2F0DE',
                   'star': '#FFFFFF', 'rain': '#B8C4D4'},
    # overcast winter night: low cloud lit from below by the town's sodium lamps (warm horizon glow)
    'snow_night': {'zenith': '#161B24', 'upper': '#1F2530', 'middle': '#2C323E', 'lower': '#454652',
                   'horizon': '#7A6658', 'sun': '#FFFFFF', 'sun_glow': '#7A6658', 'cloud_top': '#1E242E',
                   'cloud_lit': '#3C3F4A', 'cloud_rim': '#5A5A64', 'haze': '#4A4E5A', 'moon': '#F2F0DE',
                   'star': '#FFFFFF', 'rain': '#C8D0DC', 'snow': '#E8EDF4'},
}
DUSK.update({'moon': '#F6F0DA', 'star': '#FFF4E0', 'rain': '#FFFFFF'})
for _sky in SKIES.values():
    _sky.setdefault('snow', '#FFFFFF')

# what each time of day switches on: sun 'horizon' | 'low' | 'high' | None, low-sun rim light on
# clouds and ridges, lit-window fraction, street lamps, moon, star density, rain, wet ground,
# falling snow and snow on the ground
FX = {
    'dusk': dict(sun='horizon', rim=True, windows=0.38, lamps=True, moon=False, stars=0.0, rain=False, wet=False,
                 snow=False),
    'day': dict(sun='high', rim=False, windows=0.0, lamps=False, moon=False, stars=0.0, rain=False, wet=False,
                snow=False),
    'golden': dict(sun='low', rim=True, windows=0.10, lamps=False, moon=False, stars=0.0, rain=False, wet=False,
                   snow=False),
    'blue_night': dict(sun=None, rim=False, windows=0.62, lamps=True, moon=True, stars=1.0, rain=False, wet=False,
                       snow=False),
    'rain_night': dict(sun=None, rim=False, windows=0.55, lamps=True, moon=False, stars=0.0, rain=True, wet=True,
                       snow=False),
    'snow_night': dict(sun=None, rim=False, windows=0.30, lamps=True, moon=False, stars=0.0, rain=False, wet=False,
                       snow=True),
}
TIMES = tuple(FX)


def scene_time(spec):
    t = spec.get('scene', {}).get('time', 'dusk')
    if t not in FX:
        raise ValueError(f"unknown scene time '{t}' (use {', '.join(TIMES)})")
    return t


def scene_palette(defaults, overrides, time='dusk'):
    """Sky colors of the time of day, then the scene's element colors for that time, then the spec."""
    pal = dict(SKIES[time])
    pal.update(defaults[time] if time in defaults else defaults)
    pal.update(overrides or {})
    return {k: hex_rgb(v) for k, v in pal.items()}


def haze(rgb, depth, pal):
    """Aerial perspective: depth 0 = foreground color, 1 = fully dissolved into the horizon haze."""
    return mix(rgb, pal['haze'], float(np.clip(depth, 0, 1)) * 0.85)


def rect(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)


def sky(w, h, horizon_y, pal):
    stops = [(0.0, pal['zenith']), (0.35, pal['upper']), (0.62, pal['middle']), (0.85, pal['lower']),
             (1.0, pal['horizon'])]
    return Drawable('sky', 'sky', -100, fill=[rect(0, 0, w, horizon_y + 2)], gradient=(stops, (0, 0), (0, horizon_y)),
                    casts=False, receives=False)


def sun(cx, cy, r, pal, clip=None):
    glow = geom.ellipse(cx, cy, r * 9, r * 6, 96)
    halo = geom.ellipse(cx, cy, r * 2.6, r * 2.6, 64)
    disc = geom.ellipse(cx, cy, r, r, 64)
    return [Drawable('sun_glow', 'emissive', -95, fill=[glow], color=pal['sun_glow'], opacity=0.55, feather=r * 3.5,
                     casts=False, receives=False, clip=clip),
            Drawable('sun_halo', 'emissive', -94, fill=[halo], color=pal['horizon'], opacity=0.8, feather=r * 0.9,
                     casts=False, receives=False, clip=clip),
            Drawable('sun', 'emissive', -93, fill=[disc], color=pal['sun'], feather=r * 0.08,
                     casts=False, receives=False, clip=clip)]


def cloud(name, cx, cy, width, height, rng, pal, z=-90, sun_x=None):
    """Flat-bottomed cumulus bank: overlapping ellipses, lit from below by the low sun."""
    blobs = []
    n = rng.integers(5, 9)
    for i in range(n):
        t = (i + 0.5) / n
        bx = cx + (t - 0.5) * width + rng.uniform(-0.05, 0.05) * width
        bw = width / n * rng.uniform(1.0, 1.7)
        bh = height * rng.uniform(0.45, 1.0) * (1 - abs(t - 0.5) * 0.9)
        blobs.append(geom.ellipse(bx, cy - bh * 0.35, bw, bh, 40))
    base = rect(cx - width * 0.55, cy - height * 0.05, cx + width * 0.55, cy + height * 0.12)
    stops = [(0.0, pal['cloud_top']), (0.55, mix(pal['cloud_top'], pal['cloud_lit'], 0.5)), (1.0, pal['cloud_lit'])]
    out = [Drawable(name, 'sky', z, fill=blobs + [base], fill_mode='each',
                    gradient=(stops, (0, cy - height * 1.1), (0, cy + height * 0.15)), feather=1.2,
                    casts=False, receives=False)]
    if sun_x is not None:   # lit rim along the cloud's outline on the side facing the low sun
        d = np.array([sun_x - cx, height * 3.0])
        d = d / np.linalg.norm(d) * max(height * 0.12, 2.0)
        shifted = [poly - d for poly in blobs + [base]]
        out.append(Drawable(name + '_rim', 'sky', 0, fill=blobs + [base], fill_mode='each', kind='highlight',
                            hl_color=pal['cloud_rim'], opacity=0.75, clip_vis=[name], subtract=shifted, feather=0.8))
    return out


def moon(cx, cy, r, pal):
    """Moon disc with a soft halo; the cool counterpart of the sun for night skies."""
    return [Drawable('moon_glow', 'emissive', -95, fill=[geom.ellipse(cx, cy, r * 6, r * 6, 64)], color=pal['moon'],
                     opacity=0.18, feather=r * 3.0, casts=False, receives=False),
            Drawable('moon', 'emissive', -93, fill=[geom.ellipse(cx, cy, r, r, 48)], color=pal['moon'],
                     feather=r * 0.08, casts=False, receives=False)]


def stars(w, horizon_y, rng, pal, density):
    """Sparse stars, denser and brighter toward the zenith (the horizon glow hides the faint ones)."""
    n = int(220 * density * w / 1600)
    dots = []
    for _ in range(n):
        y = horizon_y * rng.random() ** 1.8 * 0.85
        r = rng.uniform(0.5, 1.4) * (1.3 if rng.random() < 0.08 else 1.0)
        dots.append(geom.ellipse(rng.uniform(0, w), y, r, r, 8))
    return [Drawable('stars', 'emissive', -99, fill=dots, fill_mode='each', color=pal['star'], opacity=0.85,
                     casts=False, receives=False)] if dots else []


def rain(w, h, rng, pal, count=900, slant=0.18):
    """Falling rain: thin slanted streaks over the whole picture, longer and brighter when near."""
    streaks = []
    for _ in range(int(count * w * h / (1600 * 1000))):
        near = rng.random() ** 2
        ln = h * (0.015 + 0.05 * near)
        x, y = rng.uniform(-0.1 * w, w), rng.uniform(-0.05 * h, h)
        p = np.array([[x, y], [x + ln * slant, y + ln]])
        streaks.append(geom.stroke_polygon(p, (0.6 + 1.2 * near) * geom.taper(2, 0.0, 0.0)))
    return [Drawable('rain', 'emissive', 60, fill=streaks, fill_mode='union', color=pal['rain'], opacity=0.32,
                     casts=False, receives=False)]


SNOW_COUNT = 1400                  # flakes per 1600 x 1000 px
SNOW_NEAR = 0.12                   # share of flakes close to the eye: large and soft


def snow(w, h, rng, pal, count=SNOW_COUNT):
    """Falling snow: many small flakes far away and a few large soft ones close to the eye."""
    far, near = [], []
    for _ in range(int(count * w * h / (1600 * 1000))):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        if rng.random() < SNOW_NEAR:
            r = w * rng.uniform(0.0035, 0.007)
            near.append(geom.ellipse(x, y, r, r * rng.uniform(0.8, 1.0), 12))
        else:
            r = w * rng.uniform(0.0008, 0.0022)
            far.append(geom.ellipse(x, y, r, r, 8))
    out = [Drawable('snow_far', 'emissive', 60, fill=far, fill_mode='each', color=pal['snow'], opacity=0.75,
                    casts=False, receives=False)]
    if near:
        out.append(Drawable('snow_near', 'emissive', 60.1, fill=near, fill_mode='each', color=pal['snow'],
                            opacity=0.55, feather=w * 0.0025, casts=False, receives=False))
    return out


BIRCH = dict(trunk_len=0.55, spread=(0.15, 0.38), light_levels=2)   # tall pale trunk, upright limbs


def bare_tree(name, x, base_y, height, color, z, rng, trunk=None, marks=None, lean=0.0, depth=5,
              trunk_len=0.42, spread=(0.25, 0.6), light_levels=1):
    """Leafless tree (birch, poplar): a trunk forking into thinner and thinner twigs.
    trunk/marks: a light trunk color with dark bark marks (a birch, see BIRCH); the first
    `light_levels` segments take the trunk color, the twigs above stay dark."""
    twigs = []

    def grow(p, ang, length, width, level):
        q = p + length * np.array([np.sin(ang), -np.cos(ang)])
        mid = (p + q) / 2 + rng.uniform(-0.08, 0.08, 2) * length
        path = geom.catmull_rom(np.array([p, mid, q]))
        twigs.append((level, geom.stroke_polygon(path, width * geom.taper(len(path), 0.0, 0.35)), p, q))
        if level >= depth:
            return
        for k in range(2 if level < 2 else rng.integers(2, 4)):
            turn = rng.uniform(*spread) * (1 if k % 2 else -1)
            grow(q, ang + turn, length * rng.uniform(0.58, 0.75), width * 0.62, level + 1)

    base = np.array([x, base_y], float)
    grow(base, lean, height * trunk_len, height * 0.035, 0)
    light = trunk is not None
    n_light = light_levels if light else 1
    out = [Drawable(name, 'scenery', z, fill=[t for lv, t, _, _ in twigs if lv >= n_light], fill_mode='union',
                    color=color, casts=False, receives=False)]
    stem = [t for lv, t, _, _ in twigs if lv < n_light]
    out.append(Drawable(name + '_trunk', 'scenery', z + 0.001, fill=stem, fill_mode='union',
                        color=trunk if light else color, casts=False, receives=False))
    if light and marks is not None:                        # birch bark: short dark dashes across the pale wood
        dashes = []
        for lv, _, p, q in twigs:
            if lv >= n_light:
                continue
            seg = np.linalg.norm(q - p)
            for t in rng.uniform(0.05, 0.95, max(int(seg / (height * 0.06)), 2)):
                c = p + (q - p) * t
                half = height * 0.035 * (0.62 ** lv) * rng.uniform(0.4, 0.9)
                dashes.append(geom.stroke_polygon(np.array([c - [half, 0], c + [half * 0.6, 0]]),
                                                  max(height * 0.006 * 0.8 ** lv, 0.7) * np.ones(2)))
        out.append(Drawable(name + '_bark', 'scenery', z + 0.002, fill=dashes, fill_mode='union', color=marks,
                            clip=[name + '_trunk'], casts=False, receives=False))
    return out


def light_streak(name, x, top_y, bottom_y, width, color, z, clip, opacity=0.5):
    """Reflection of a light on wet ground or water: a vertical streak that fades downward."""
    pts = np.array([[x - width / 2, top_y], [x + width / 2, top_y], [x + width * 0.2, bottom_y], [x - width * 0.2, bottom_y]])
    return Drawable(name, 'emissive', z, fill=[pts], color=color, opacity=opacity, feather=max(width * 0.6, 1.0),
                    clip=clip, casts=False, receives=False)


def ridge(rng, x0, x1, base_y, amp, n=7, rough=0.55, bottom=None):
    """Mountain ridge by midpoint displacement; returns a closed polygon down to `bottom`."""
    pts = np.array([[x0, base_y], [x1, base_y]], float)
    scale = amp
    for _ in range(n):
        mids = (pts[:-1] + pts[1:]) / 2
        mids[:, 1] += rng.uniform(-1, 1, len(mids)) * scale
        out = np.empty((len(pts) + len(mids), 2))
        out[0::2], out[1::2] = pts, mids
        pts = out
        scale *= rough
    bottom = base_y + amp * 3 if bottom is None else bottom
    return np.vstack([pts, [[x1, bottom], [x0, bottom]]]), pts


def pine(name, x, base_y, height, color, z, rng, rim=None):
    """Conifer silhouette: stacked jagged tiers narrowing toward the tip."""
    tiers = []
    n = 7
    for i in range(n):
        t = i / n
        top = base_y - height * (0.15 + 0.85 * (i + 1) / n)
        bot = base_y - height * (0.05 + 0.85 * i / n)
        half = height * 0.22 * (1 - t) ** 0.9 + height * 0.02
        jag = rng.uniform(-0.15, 0.15, 6) * half
        tiers.append(np.array([[x, top], [x + half * 0.35 + jag[0], top + (bot - top) * 0.45],
                               [x + half * 0.55 + jag[1], top + (bot - top) * 0.55],
                               [x + half + jag[2], bot], [x - half + jag[3], bot],
                               [x - half * 0.55 + jag[4], top + (bot - top) * 0.55],
                               [x - half * 0.35 + jag[5], top + (bot - top) * 0.45]]))
    trunk = rect(x - height * 0.012, base_y - height * 0.12, x + height * 0.012, base_y)
    return [Drawable(name, 'scenery', z, fill=tiers + [trunk], fill_mode='each', color=color, casts=False,
                     receives=False)]


def foliage(name, cx, cy, radius, color, z, rng, frame_unit, n=14):
    """Broadleaf crown: clumps of leaf masses (pillow-shaded) on the given center."""
    blobs = []
    for _ in range(n):
        a = rng.uniform(0, 2 * np.pi)
        d = radius * np.sqrt(rng.uniform(0, 1)) * 0.75
        r = radius * rng.uniform(0.28, 0.45)
        blobs.append(geom.ellipse(cx + np.cos(a) * d, cy + np.sin(a) * d * 0.8, r, r * 0.85, 32))
    return Drawable(name, 'foliage', z, fill=blobs, fill_mode='each', color=color, form_radius=frame_unit * 0.6,
                    casts=False, receives=False)


def grass(name, x0, x1, y0, y1, color, rng, count, length, z, clip):
    """Grass blades as tapered strokes leaning slightly with the wind."""
    strokes = []
    for _ in range(count):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        k = (y - y0) / max(y1 - y0, 1)              # nearer blades are longer
        ln = length * (0.4 + 0.9 * k) * rng.uniform(0.6, 1.2)
        lean = rng.uniform(-0.25, 0.45) * ln
        path = geom.bezier((x, y), (x + lean * 0.2, y - ln * 0.5), (x + lean * 0.6, y - ln * 0.85), (x + lean, y - ln), 10)
        strokes.append(geom.stroke_polygon(path, (1.2 + 2.0 * k) * geom.taper(10, 0.0, 0.9)))
    return Drawable(name, 'scenery', z, fill=strokes, fill_mode='union', color=color, clip=clip,
                    casts=False, receives=False)
