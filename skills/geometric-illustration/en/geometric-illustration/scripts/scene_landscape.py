"""Landscape painting: mountain lake, at dusk or another time of day (spec scene.time).

Composition (back to front, as a landscape painter blocks it in):
sky and sun -> cloud banks -> far ridge (most haze) -> mid ridge with a warm
rim on the sun side -> lake with mirrored ridges and a sun path -> dark
foreground shore, framing pines and grass. Value steps from light (far) to
dark (near) carry the depth; the only warm accents are the sun, its path on
the water and the rims. Other times swap the colors and the light source:
a high sun scatters glints on the water, a low golden sun lays a path, the
blue hour hangs a moon with stars over a lit village on the far shore, and
a rainy night dissolves the ridges in mist with rain rings on the lake, a
snowy night turns the shore trees into birches under falling snow.

Sites (spec scene.site): 'lake' is the composition above; 'outskirts' is an open
field at the edge of a town, a power line receding to the blocks and chimneys
on the horizon, birches in front.
"""
import numpy as np

import geom
import scene_common as C
from raster import mix
from scene import Drawable

PALETTES = {
    'dusk': {'ridge_far': '#7B6C9E', 'ridge_mid': '#45406E', 'ridge_rim': '#FFB38A', 'hill': '#2B2C4A',
             'shore': '#1E2034', 'water_top': '#F2B78C', 'water_deep': '#2C2F57', 'pine': '#191A2C',
             'tree': '#3A3A5E', 'grass': '#2F3150', 'glitter': '#FFE6B8', 'ripple': '#C7A0B8', 'village': '#FFC878'},
    'day': {'ridge_far': '#8CA6C8', 'ridge_mid': '#5B7C7A', 'ridge_rim': '#E8F0D0', 'hill': '#4C7A4C',
            'shore': '#3A5C34', 'water_top': '#A6CCEA', 'water_deep': '#2E5E8A', 'pine': '#22422C',
            'tree': '#3E6E3A', 'grass': '#5A8A40', 'glitter': '#FFFFFF', 'ripple': '#DCEEF8', 'village': '#F0E8D8'},
    'golden': {'ridge_far': '#A08CB0', 'ridge_mid': '#6C5E6E', 'ridge_rim': '#FFC47C', 'hill': '#5C5A3C',
               'shore': '#3A3422', 'water_top': '#F6D096', 'water_deep': '#3C486A', 'pine': '#2A281E',
               'tree': '#5E5A2E', 'grass': '#7A7036', 'glitter': '#FFF0C2', 'ripple': '#ECCCA2', 'village': '#FFD088'},
    'blue_night': {'ridge_far': '#3A4A82', 'ridge_mid': '#222D5C', 'ridge_rim': '#8C9CDA', 'hill': '#1A2248',
                   'shore': '#10142C', 'water_top': '#5A6AAA', 'water_deep': '#121A3E', 'pine': '#0B0F26',
                   'tree': '#171F46', 'grass': '#1B2348', 'glitter': '#EEF0FF', 'ripple': '#6A78B8', 'village': '#FFCE80'},
    'rain_night': {'ridge_far': '#3E4552', 'ridge_mid': '#2B313A', 'ridge_rim': '#5A6070', 'hill': '#21272E',
                   'shore': '#151A1F', 'water_top': '#4C5462', 'water_deep': '#1A2029', 'pine': '#0E1217',
                   'tree': '#1A2229', 'grass': '#1F272C', 'glitter': '#D8D2C0', 'ripple': '#7A8290', 'village': '#FFC070'},
    'snow_night': {'ridge_far': '#4A505E', 'ridge_mid': '#363C48', 'ridge_rim': '#6E7480', 'hill': '#7E8694',
                   'shore': '#A8B0BE', 'water_top': '#6E7686', 'water_deep': '#3E4552', 'pine': '#141A20',
                   'tree': '#2A2E36', 'grass': '#4A505A', 'glitter': '#E8E0D0', 'ripple': '#8A92A0', 'village': '#FFB060',
                   # outskirts site
                   'field_far': '#5E6472', 'field_near': '#A3ABB9', 'drift': '#C2C9D4', 'path': '#7A8190',
                   'pylon': '#20242C', 'birch': '#D9DCE0', 'birch_mark': '#2A2E36', 'town': '#3A3F4C',
                   'town_lit': '#FFB060', 'chimney': '#454A56', 'beacon': '#FF4A3A'},
}
PALETTE = PALETTES['dusk']
LIGHTS = {'dusk': [-0.75, -0.05, 0.45],          # low sun on the left, slightly toward the viewer
          'day': [-0.45, -0.75, 0.50], 'golden': [-0.80, -0.20, 0.45],
          'blue_night': [0.35, -0.60, 0.35], 'rain_night': [0.0, -0.70, 0.50], 'snow_night': [0.20, -0.70, 0.45]}
LIGHT = LIGHTS['dusk']
HORIZON = 0.56                         # waterline as a fraction of canvas height
SUN_X = 0.34
SUN_PLACE = {'horizon': (SUN_X, -0.035, 0.028), 'low': (0.30, -0.17, 0.024), 'high': (0.80, -0.47, 0.020)}
MOON = (0.60, 0.22, 0.016)             # x, y as canvas fractions, radius as a width fraction
MIST = {'rain_night': 0.35, 'snow_night': 0.30}   # extra haze on the ridges
SITES = ('lake', 'outskirts')          # a mountain lake | the snowy edge of a town: field, birches, power line
OUT_HORIZON = 0.62                     # outskirts: the field's far edge as a fraction of canvas height
PYLONS = 6                             # outskirts: power-line towers receding toward the town
PYLON_NEAR = (0.10, 0.99, 0.62)        # x, base y, height (canvas fractions) of the nearest tower
PYLON_FAR_X = 0.72                     # where the line meets the horizon (width fraction)


CLOUDS = [(0.20, 0.17, 0.42, 0.06), (0.72, 0.12, 0.50, 0.05), (0.55, 0.30, 0.38, 0.04), (0.10, 0.36, 0.30, 0.03),
          (0.86, 0.33, 0.30, 0.035)]
OVERCAST = [(0.15, 0.07, 0.70, 0.09), (0.70, 0.05, 0.80, 0.10), (0.45, 0.22, 0.90, 0.08), (0.05, 0.28, 0.60, 0.06),
            (0.92, 0.26, 0.60, 0.07)]


def build_landscape(spec, w, h, rng):
    time = C.scene_time(spec)
    fx = C.FX[time]
    site = spec.get('scene', {}).get('site') or 'lake'
    if site not in SITES:
        raise ValueError(f"unknown landscape site '{site}' (use {', '.join(SITES)})")
    pal = C.scene_palette(PALETTES, spec.get('scene', {}).get('palette'), time)
    if site == 'outskirts':
        return _outskirts(w, h, pal, fx, rng), LIGHTS[time], w * 0.12
    hy = HORIZON * h
    out = [C.sky(w, h, hy, pal)]
    sx = sr = None
    if fx['sun']:
        fx_x, fy, fr = SUN_PLACE[fx['sun']]
        sx, sy, sr = fx_x * w, hy + fy * h, fr * w
        out += C.sun(sx, sy, sr, pal)
    if fx['moon']:
        mx, my, mr = MOON[0] * w, MOON[1] * h, MOON[2] * w
        out += C.moon(mx, my, mr, pal)
    if fx['stars']:
        out += C.stars(w, hy, rng, pal, fx['stars'])
    for i, (cx, cy, cw, ch) in enumerate(OVERCAST if fx['rain'] or fx['snow'] else CLOUDS):
        out += C.cloud(f'cloud_{i}', cx * w, cy * h, cw * w, ch * h, rng, pal, z=-90 + i * 0.1,
                       sun_x=sx if fx['rim'] else None)

    mist = MIST.get(time, 0.0)
    far_poly, far_line = C.ridge(rng, -0.05 * w, 1.05 * w, hy - 0.15 * h, 0.10 * h, rough=0.55, bottom=hy)
    mid_poly, mid_line = C.ridge(rng, -0.05 * w, 1.05 * w, hy - 0.07 * h, 0.15 * h, rough=0.5, bottom=hy)
    far_col = C.haze(pal['ridge_far'], 0.55 + mist, pal)
    out.append(Drawable('ridge_far', 'scenery', -80, fill=[far_poly],
                        gradient=(far_col, mix(far_col, pal['horizon'], 0.45), (0, hy - 0.16 * h), (0, hy)),
                        casts=False, receives=False))
    mid_col = C.haze(pal['ridge_mid'], 0.2 + mist, pal)
    out.append(Drawable('ridge_mid', 'scenery', -70, fill=[mid_poly],
                        gradient=(mid_col, mix(mid_col, pal['haze'], 0.35), (0, hy - 0.2 * h), (0, hy)),
                        casts=False, receives=False))
    if fx['rim'] or fx['moon']:
        rim = mid_line + np.array([0, 2.0])
        src = sx if fx['rim'] else mx
        lit = np.abs(rim[:, 0] - src) < 0.45 * w           # only the ridge facing the sun (or moon) catches light
        if lit.sum() > 2:
            rim_band = geom.stroke_polygon(rim[lit], 3.0 * geom.taper(int(lit.sum()), 0.1, 0.3))
            out.append(Drawable('ridge_rim', 'scenery', 0, fill=[rim_band], fill_mode='union', kind='highlight',
                                hl_color=pal['ridge_rim'], opacity=0.75 if fx['rim'] else 0.45,
                                clip_vis=['ridge_mid'], feather=0.8))

    hills = [np.array([[-0.05 * w, hy - 0.06 * h], [0.10 * w, hy - 0.09 * h], [0.24 * w, hy - 0.02 * h],
                       [0.30 * w, hy], [-0.05 * w, hy]]),
             np.array([[0.62 * w, hy], [0.74 * w, hy - 0.05 * h], [0.90 * w, hy - 0.11 * h],
                       [1.05 * w, hy - 0.09 * h], [1.05 * w, hy]])]
    hill_poly = [geom.catmull_rom(p, closed=True) for p in hills]
    out.append(Drawable('hills', 'scenery', -60, fill=hill_poly, fill_mode='each', color=C.haze(pal['hill'], 0.15, pal),
                        casts=False, receives=False))
    if fx['windows']:
        out += _village(w, h, hy, pal, rng, fx['windows'])
    out += _lake(w, h, hy, pal, rng, [(far_poly, far_col, 'ridge_far'), (mid_poly, mid_col, 'ridge_mid')]
                 + [(p, C.haze(pal['hill'], 0.15, pal), f'hill_{i}') for i, p in enumerate(hill_poly)])
    if fx['sun'] in ('horizon', 'low'):
        out += _light_path('sun_path', sx, sr, w, h, hy, pal['glitter'], rng, 0.85)
    elif fx['sun'] == 'high':
        out += _sparkles(w, h, hy, pal, rng)
    if fx['moon']:
        out += _light_path('moon_path', mx, mr * 1.6, w, h, hy, pal['glitter'], rng, 0.55)
    if fx['rain']:
        out += _rain_rings(w, h, hy, pal, rng)
    out += _foreground(w, h, hy, pal, rng, fx['snow'])
    if fx['rain']:
        out += C.rain(w, h, rng, pal)
    if fx['snow']:
        out += C.snow(w, h, rng, pal)
    return out, LIGHTS[time], w * 0.12


def _village(w, h, hy, pal, rng, amount):
    """Lit windows of a far-shore village at the waterline, each mirrored as a streak on the lake."""
    out, dots = [], []
    for k in range(int(26 * amount * 2)):
        x = rng.uniform(0.40, 0.64) * w if rng.random() < 0.75 else rng.uniform(0.05, 0.95) * w
        y = hy - rng.uniform(0.002, 0.016) * h
        r = rng.uniform(0.6, 1.5) * w / 1600
        dots.append(geom.ellipse(x, y, r, r * 0.8, 8))
        out.append(C.light_streak(f'village_reflect_{k}', x, hy + 1, hy + rng.uniform(0.02, 0.06) * h, r * 2.2,
                                  pal['village'], -44, ['lake'], 0.45))
    out.append(Drawable('village', 'emissive', -59, fill=dots, fill_mode='each', color=pal['village'],
                        casts=False, receives=False))
    return out


def _light_path(name, cx, r, w, h, hy, color, rng, opacity):
    """Sun (or moon) path on the water: broken horizontal glints widening toward the viewer."""
    bottom = 0.86 * h
    dashes = []
    for k in range(70):
        t = (k / 70) ** 1.6
        y = hy + 3 + t * (bottom - hy - 6)
        half = r * (0.5 + 2.2 * t) * rng.uniform(0.3, 1.0)
        x = cx + rng.normal(0, r * (0.25 + 0.6 * t))
        dashes.append(geom.stroke_polygon(np.array([[x - half, y], [x + half, y]]), 1.0 + 2.5 * t))
    return [Drawable(name, 'emissive', -40, fill=dashes, fill_mode='union', color=color, opacity=opacity,
                     clip=['lake'], casts=False, receives=False)]


def _sparkles(w, h, hy, pal, rng):
    """Midday water: a high sun scatters small glints over the whole lake."""
    bottom = 0.86 * h
    glints = []
    for _ in range(140):
        t = rng.random()
        y = hy + 3 + t * (bottom - hy - 6)
        half = (0.002 + 0.008 * t) * w * rng.uniform(0.4, 1.0)
        x = rng.uniform(0, w)
        glints.append(geom.stroke_polygon(np.array([[x - half, y], [x + half, y]]), 0.8 + 1.6 * t))
    return [Drawable('glints', 'emissive', -40, fill=glints, fill_mode='union', color=pal['glitter'], opacity=0.8,
                     clip=['lake'], casts=False, receives=False)]


def _rain_rings(w, h, hy, pal, rng):
    """Rain on the lake: small flattened rings, larger toward the viewer."""
    bottom = 0.86 * h
    rings = []
    for _ in range(90):
        t = rng.random() ** 0.7
        y = hy + 4 + t * (bottom - hy - 8)
        rx = (0.002 + 0.008 * t) * w
        ring = geom.ellipse(rng.uniform(0, w), y, rx, rx * 0.22, 24)
        rings.append(geom.stroke_polygon(np.vstack([ring, ring[:1]]), 0.6 + 1.0 * t))
    return [Drawable('rain_rings', 'scenery', -41, fill=rings, fill_mode='union', color=pal['ripple'], opacity=0.45,
                     clip=['lake'], casts=False, receives=False)]


def _lake(w, h, hy, pal, rng, mirror):
    bottom = 0.86 * h
    out = [Drawable('lake', 'scenery', -50, fill=[C.rect(0, hy, w, bottom)],
                    gradient=([(0.0, pal['water_top']), (0.25, mix(pal['water_top'], pal['water_deep'], 0.55)),
                               (1.0, pal['water_deep'])], (0, hy), (0, bottom)),
                    casts=False, receives=False)]
    for i, (poly, col, name) in enumerate(mirror):          # reflections: mirrored about the waterline, darker
        flipped = poly.copy()
        flipped[:, 1] = 2 * hy - flipped[:, 1]
        out.append(Drawable(f'reflect_{name}', 'scenery', -49 + i * 0.1, fill=[flipped], color=mix(col, pal['water_deep'], 0.45),
                            opacity=0.8, clip=['lake'], feather=1.5, casts=False, receives=False))
    ripples = []
    for k in range(45):
        y = rng.uniform(hy + 4, bottom)
        t = (y - hy) / (bottom - hy)
        x = rng.uniform(0, w)
        half = rng.uniform(0.02, 0.08) * w * (0.4 + t)
        ripples.append(geom.stroke_polygon(np.array([[x - half, y], [x + half, y]]), 0.8 + 1.4 * t))
    out.append(Drawable('ripples', 'scenery', -41, fill=ripples, fill_mode='union', color=pal['ripple'], opacity=0.35,
                        clip=['lake'], casts=False, receives=False))
    return out


def _foreground(w, h, hy, pal, rng, winter=False):
    shore = np.array([[-0.05 * w, 0.80 * h], [0.20 * w, 0.83 * h], [0.45 * w, 0.85 * h], [0.70 * w, 0.82 * h],
                      [0.86 * w, 0.76 * h], [1.05 * w, 0.70 * h], [1.05 * w, 1.05 * h], [-0.05 * w, 1.05 * h]])
    out = [Drawable('shore', 'scenery', -30, fill=[geom.catmull_rom(shore, closed=True)],
                    gradient=(pal['hill'], pal['shore'], (0, 0.75 * h), (0, h)), casts=False, receives=False)]
    out.append(C.grass('grass', 0, w, 0.80 * h, 1.0 * h, pal['grass'], rng, 900, 0.045 * h, -29, ['shore']))
    out.append(C.grass('grass_lit', 0, 0.55 * w, 0.82 * h, 1.0 * h, mix(pal['grass'], pal['ridge_rim'], 0.35), rng, 160,
                       0.04 * h, -28.9, ['shore']))
    for i, (x, base, ht) in enumerate([(0.83, 0.80, 0.58), (0.92, 0.78, 0.70), (0.76, 0.82, 0.40), (1.0, 0.76, 0.50)]):
        out += C.pine(f'pine_{i}', x * w, base * h, ht * h, pal['pine'], -20 + i * 0.1, rng)
    if winter:                                   # a bare birch where the broadleaf tree stands in summer
        return out + C.bare_tree('birch_shore', 0.09 * w, 0.84 * h, 0.42 * h, pal['tree'], -21, rng,
                                 trunk=pal.get('birch', pal['shore']), marks=pal['pine'], lean=-0.06, **C.BIRCH)
    stem = geom.catmull_rom(np.array([[0.09 * w, 0.84 * h], [0.10 * w, 0.70 * h], [0.08 * w, 0.58 * h]]))
    trunk = geom.stroke_polygon(stem, 0.012 * w * geom.taper(len(stem), 0.0, 1.0, 0.5))
    out.append(Drawable('tree_trunk', 'scenery', -21, fill=[trunk], fill_mode='union', color=pal['pine'],
                        casts=False, receives=False))
    for i, (cx, cy, r) in enumerate([(0.07, 0.55, 0.10), (0.14, 0.50, 0.08), (0.02, 0.62, 0.07)]):
        out.append(C.foliage(f'leaves_{i}', cx * w, cy * h, r * w, pal['tree'], -19 + i * 0.1, rng, w * 0.05))
    return out


# ---------------------------------------------------------------- outskirts site

STEEL, STEEL_SHARE = np.array([0.20, 0.20, 0.22], np.float32), 0.75


def _outskirts_palette(pal):
    """Outskirts colors: the time's own entries, else derived from its lake palette (a dry field in summer)."""
    steel = mix(pal['pine'], STEEL, STEEL_SHARE)          # towers and bare twigs: near-neutral dark, faintly tinted
    derived = {'field_far': pal['hill'], 'field_near': pal['grass'], 'drift': mix(pal['grass'], pal['haze'], 0.3),
               'path': pal['shore'], 'pylon': steel, 'birch': mix(pal['glitter'], pal['shore'], 0.2),
               'birch_mark': steel, 'town': pal['ridge_mid'], 'town_lit': pal['village'],
               'chimney': pal['ridge_mid'], 'beacon': np.array([1.0, 0.29, 0.23], np.float32)}
    return {**derived, **{k: v for k, v in pal.items() if k in derived}}


def _outskirts(w, h, pal, fx, rng):
    """Edge of a town on a winter night: an open field, a footpath to the blocks on the horizon, a power line
    receding toward them, birches in the foreground. One-point depth from the line of towers."""
    pal = {**pal, **_outskirts_palette(pal)}
    hy = OUT_HORIZON * h
    out = [C.sky(w, h, hy, pal)]
    for i, (cx, cy, cw, ch) in enumerate(OVERCAST if fx['rain'] or fx['snow'] else CLOUDS):
        out += C.cloud(f'cloud_{i}', cx * w, cy * h, cw * w, ch * h, rng, pal, z=-90 + i * 0.1)
    out += _town(w, h, hy, pal, rng, fx)
    field = C.rect(-2, hy - 1, w + 2, h + 2)
    out.append(Drawable('field', 'scenery', -60, fill=[field],
                        gradient=(C.haze(pal['field_far'], 0.3, pal), pal['field_near'], (0, hy), (0, h)),
                        casts=False, receives=False))
    drifts = []
    for _ in range(14):                                         # soft swells in the snow, wider toward the viewer
        t = rng.random() ** 0.7
        y = hy + t * (h - hy)
        drifts.append(geom.ellipse(rng.uniform(0, w), y, w * (0.08 + 0.25 * t), h * (0.004 + 0.02 * t), 40))
    out.append(Drawable('drifts', 'scenery', -59, fill=drifts, fill_mode='each', color=pal['drift'], opacity=0.35,
                        feather=w * 0.01, clip=['field'], casts=False, receives=False))
    path = []
    for t in np.linspace(0, 1, 30):                             # footpath: from the bottom edge toward the town
        y = h + 2 - t * (h - hy)
        x = w * (0.46 + 0.06 * np.sin(t * 3.0) + 0.04 * t)
        path.append((x, y, w * (0.05 * (1 - t) ** 1.6 + 0.002)))
    left = [(x - hw, y) for x, y, hw in path]
    right = [(x + hw, y) for x, y, hw in path][::-1]
    out.append(Drawable('footpath', 'scenery', -58, fill=[np.array(left + right)], color=pal['path'], opacity=0.75,
                        feather=w * 0.004, casts=False, receives=False))
    out += _power_line(w, h, hy, pal)
    for i, (x, base, ht) in enumerate([(0.30, 0.70, 0.12), (0.22, 0.72, 0.15), (0.62, 0.68, 0.08)]):
        out += C.bare_tree(f'birch_far_{i}', x * w, base * h, ht * h, C.haze(pal['birch_mark'], 0.35, pal),
                           -50 + i * 0.1, rng, depth=4)
    for i, (x, base, ht, lean) in enumerate([(0.80, 1.02, 0.78, 0.04), (0.91, 1.04, 0.92, -0.05),
                                             (0.70, 0.98, 0.52, 0.08)]):
        out += C.bare_tree(f'birch_{i}', x * w, base * h, ht * h, pal['birch_mark'], -20 + i * 0.1, rng,
                           trunk=pal['birch'], marks=pal['birch_mark'], lean=lean, **C.BIRCH)
    if fx['rain']:
        out += C.rain(w, h, rng, pal)
    if fx['snow']:
        out += C.snow(w, h, rng, pal)
    return out


def _town(w, h, hy, pal, rng, fx):
    """Panel blocks along the horizon with rows of lit windows, and a power station's two chimneys."""
    blocks, lights = [], []
    x = 0.30 * w
    while x < 0.92 * w:
        bw, bh = rng.uniform(0.03, 0.08) * w, rng.uniform(0.025, 0.07) * h
        blocks.append(C.rect(x, hy - bh, x + bw, hy + 2))
        rows, cols = max(int(bh / (h * 0.006)), 1), max(int(bw / (w * 0.0045)), 1)
        for r in range(rows):
            for c in range(cols):
                if rng.random() < fx['windows'] * 0.9:
                    lx = x + (c + 0.3) * bw / cols
                    ly = hy - bh + (r + 0.35) * bh / rows
                    lights.append(C.rect(lx, ly, lx + max(w * 0.0012, 1.0), ly + max(h * 0.0018, 1.0)))
        x += bw * rng.uniform(1.0, 1.6)
    col = C.haze(pal['town'], 0.5, pal)
    out = [Drawable('town', 'scenery', -80, fill=blocks, fill_mode='each', color=col, casts=False, receives=False)]
    if lights:
        out.append(Drawable('town_lights', 'emissive', -79.9, fill=lights, fill_mode='each', color=pal['town_lit'],
                            opacity=0.85, clip=['town'], casts=False, receives=False))
    stacks, beacons = [], []
    for cx in (0.25 * w, 0.285 * w):
        top = hy - 0.17 * h
        stacks.append(np.array([[cx - w * 0.006, hy + 1], [cx - w * 0.0035, top], [cx + w * 0.0035, top],
                                [cx + w * 0.006, hy + 1]]))
        beacons.append(geom.ellipse(cx, top + h * 0.004, w * 0.0022, w * 0.0022, 12))
    out.append(Drawable('chimneys', 'scenery', -79, fill=stacks, fill_mode='each',
                        color=C.haze(pal['chimney'], 0.45, pal), casts=False, receives=False))
    if fx['lamps']:
        out.append(Drawable('beacons', 'emissive', -78.9, fill=beacons, fill_mode='each', color=pal['beacon'],
                            casts=False, receives=False))
        smoke = [geom.ellipse(0.27 * w + k * w * 0.03, hy - 0.19 * h - k * h * 0.015, w * (0.02 + 0.012 * k),
                              h * (0.012 + 0.005 * k), 32) for k in range(5)]
        out.append(Drawable('smoke', 'scenery', -79.5, fill=smoke, fill_mode='each', color=pal['cloud_lit'],
                            opacity=0.35, feather=w * 0.01, casts=False, receives=False))
    return out


def _pylon_shape(x, base, height):
    """Lattice tower: tapering legs, two cross-arms, X bracing; returns stroke polygons and the arm tips."""
    half_b, half_t = height * 0.14, height * 0.03
    top = base - height
    lw = max(height * 0.012, 0.8)
    legs = [np.array([[x - half_b, base], [x - half_t, top]]), np.array([[x + half_b, base], [x + half_t, top]])]
    polys = [geom.stroke_polygon(p, np.full(2, lw)) for p in legs]
    tips = []
    for ay, reach in ((top + height * 0.12, 0.30), (top + height * 0.30, 0.24)):
        arm = np.array([[x - height * reach, ay], [x + height * reach, ay]])
        polys.append(geom.stroke_polygon(arm, np.full(2, lw * 0.8)))
        tips += [arm[0], arm[1]]
    for k in range(4):                                          # X bracing between the legs
        y0 = base - height * (0.08 + 0.22 * k)
        y1 = y0 - height * 0.2
        w0 = half_b + (half_t - half_b) * (base - y0) / height
        w1 = half_b + (half_t - half_b) * (base - y1) / height
        polys.append(geom.stroke_polygon(np.array([[x - w0, y0], [x + w1, y1]]), np.full(2, lw * 0.5)))
        polys.append(geom.stroke_polygon(np.array([[x + w0, y0], [x - w1, y1]]), np.full(2, lw * 0.5)))
    return polys, tips


def _power_line(w, h, hy, pal):
    """Towers receding to the horizon at even ground spacing (perspective scale 1/distance), wires sagging between."""
    nx, nb, nh = PYLON_NEAR
    towers, wires, prev = [], [], None
    for k in range(PYLONS):
        s = 1.0 / (1.0 + 1.6 * k)                              # 1/distance for evenly spaced towers
        x = (PYLON_FAR_X + (nx - PYLON_FAR_X) * s) * w
        base = hy + (nb * h - hy) * s
        polys, tips = _pylon_shape(x, base, nh * h * s)
        towers += polys
        if prev is not None:
            for a, b in zip(prev, tips):
                t = np.linspace(0, 1, 24)[:, None]
                pts = a + (b - a) * t + np.array([0.0, 1.0]) * (4 * t * (1 - t)) * np.linalg.norm(b - a) * 0.06
                wires.append(geom.stroke_polygon(pts, np.full(24, max(nh * h * s * 0.004, 0.7))))
        prev = tips
    return [Drawable('pylons', 'scenery', -40, fill=towers, fill_mode='union', color=pal['pylon'], casts=False,
                     receives=False),
            Drawable('pylon_wires', 'scenery', -39.9, fill=wires, fill_mode='union', color=pal['pylon'], casts=False,
                     receives=False)]
