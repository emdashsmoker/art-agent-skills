"""Cityscape painting: a street in one-point perspective, at dusk or another time (spec scene.time).

Composition: the vanishing point sits on the horizon slightly below the
canvas center, where the sun has just set behind a hazy skyline. Building
walls on both sides recede toward it, utility wires and street lamps repeat
the perspective rhythm, and the warm lights (windows, lamps, signs) are the
only saturated accents against cool backlit walls.

A tiny pinhole camera (height above the street, focal length) turns street
coordinates (meters) into pixels, so every facade, window grid and lamp is
placed in consistent perspective. The same camera mirrors lights in the wet
street on a rainy night: a light at height H reflects at the point -H below
the ground plane, which is why its streak points straight at the viewer.

Times of day: a clear day lights the facades facing the sun and lays the
left buildings' shadow across the road; the golden hour sets the sun in the
street's gap; the blue hour switches every lamp, sign and window on under a
deep blue sky; the rainy night adds rain and mirrors the lights in the road;
the snowy night grays the sky, lays snow with wheel ruts on the road and lights
the street with orange sodium lamps.

Sites (spec scene.site): 'street' is the shop-lined avenue above; 'panel' sets
the same camera in a housing estate of prefabricated panel blocks (panel seams,
balcony slabs, stairwell windows) behind front yards with bare trees.
"""
from dataclasses import dataclass

import numpy as np

import geom
import scene_common as C
from palette import darken
from raster import mix
from scene import Drawable

PALETTES = {
    'dusk': {'wall_a': '#3B3F66', 'wall_b': '#4A4670', 'wall_c': '#33395A', 'wall_front': '#252845',
             'roof_rim': '#F2A27F', 'window_lit': '#FFCB7A', 'window_dark': '#272B48', 'sign_a': '#FF7A8A',
             'sign_b': '#7FE0E6', 'sign_c': '#FFD36E', 'road': '#2E2F4A', 'road_far': '#7A6A8E', 'walk': '#46466A',
             'line': '#D9CDB8', 'pole': '#1C1D30', 'lamp': '#FFE0A8', 'lamp_pool': '#FFB86E', 'skyline': '#6F6694'},
    'day': {'wall_a': '#B7AEA4', 'wall_b': '#C8B9A4', 'wall_c': '#A6ADB8', 'wall_front': '#8C888C',
            'roof_rim': '#F4F4F0', 'window_lit': '#BCD6EE', 'window_dark': '#5A6A80', 'sign_a': '#D85A6A',
            'sign_b': '#46A8BA', 'sign_c': '#DDB04C', 'road': '#646670', 'road_far': '#A6AEBC', 'walk': '#9A968E',
            'line': '#F4F0E6', 'pole': '#3A3A42', 'lamp': '#E6E6DE', 'lamp_pool': '#FFFFFF', 'skyline': '#98A8C0'},
    'golden': {'wall_a': '#7A6878', 'wall_b': '#8A7074', 'wall_c': '#6A6480', 'wall_front': '#4A4258',
               'roof_rim': '#FFC47A', 'window_lit': '#FFD27A', 'window_dark': '#3E3A52', 'sign_a': '#E86A78',
               'sign_b': '#5EC0C8', 'sign_c': '#F0C058', 'road': '#56505E', 'road_far': '#D6A890', 'walk': '#7A6A72',
               'line': '#F0D8B8', 'pole': '#2A2430', 'lamp': '#F0E0C0', 'lamp_pool': '#FFB86E', 'skyline': '#A08AA0'},
    'blue_night': {'wall_a': '#252D58', 'wall_b': '#2D3362', 'wall_c': '#21284C', 'wall_front': '#151936',
                   'roof_rim': '#5A6AB2', 'window_lit': '#FFD08A', 'window_dark': '#191E3E', 'sign_a': '#FF6A8A',
                   'sign_b': '#6AE6F0', 'sign_c': '#FFD86A', 'road': '#1D2144', 'road_far': '#485290',
                   'walk': '#293056', 'line': '#B6B6C8', 'pole': '#0D0F24', 'lamp': '#FFE6B0', 'lamp_pool': '#FFB86E',
                   'skyline': '#384688'},
    'rain_night': {'wall_a': '#2A2E37', 'wall_b': '#33363F', 'wall_c': '#262A33', 'wall_front': '#181B22',
                   'roof_rim': '#4A505C', 'window_lit': '#FFC878', 'window_dark': '#1B1F28', 'sign_a': '#FF6A7E',
                   'sign_b': '#62DCE6', 'sign_c': '#FFD064', 'road': '#181B22', 'road_far': '#4A4E5A',
                   'walk': '#272B33', 'line': '#8E9096', 'pole': '#0D0F13', 'lamp': '#FFE0A8', 'lamp_pool': '#FFB060',
                   'skyline': '#3A3E4A'},
    # winter night: grey concrete, snow on the ground lit orange by sodium lamps
    'snow_night': {'wall_a': '#585E6B', 'wall_b': '#626570', 'wall_c': '#525866', 'wall_front': '#3E434E',
                   'roof_rim': '#6E7280', 'window_lit': '#FFB566', 'window_dark': '#262B35', 'sign_a': '#E86A5A',
                   'sign_b': '#6AC8D0', 'sign_c': '#F0C060', 'road': '#7C8392', 'road_far': '#4E5462',
                   'walk': '#9AA1AE', 'line': '#C8CCD4', 'pole': '#14171D', 'lamp': '#FFD08A', 'lamp_pool': '#FF9A40',
                   'skyline': '#3E4350', 'window_cool': '#9DB4D6', 'seam': '#3A3F4A', 'yard': '#A6ADBA',
                   'tree': '#1E2228', 'rut': '#5E6472'},
}
PALETTE = PALETTES['dusk']
LIGHTS = {'dusk': [0.0, -0.25, -0.6],          # sun just set behind the street: everything facing us is backlit
          'day': [-0.60, -0.70, 0.35], 'golden': [0.0, -0.15, -0.70],
          'blue_night': [0.0, -0.50, 0.30], 'rain_night': [0.0, -0.60, 0.40], 'snow_night': [0.0, -0.65, 0.40]}
LIGHT = LIGHTS['dusk']
SUN_Y = {'horizon': -0.01, 'low': -0.10}      # sun height over the horizon (canvas fraction), seen in the street gap
DAY_SHADE, DAY_LIT = 0.72, 1.08                # facade value: facing away from / toward a high side sun
DAY_SHADOW_W = 5.5                             # meters of road shaded by the buildings on the sun side
WET_OPACITY = 0.65                             # strength of light reflections on the wet street
HORIZON = 0.56
STREET_HALF, WALK = 4.5, 2.5         # meters
CAM_H = 1.6
SITES = ('street', 'panel')          # a shopping street | a housing estate of prefabricated panel blocks
PANEL_YARD = 9.0                     # meters of snowy yard between the sidewalk and the blocks
PANEL_DEPTH = 12.0                   # meters from the facade to the back of a block
PANEL_FLOOR, PANEL_BAY = 2.8, 3.2    # meters: storey height, window spacing along the facade
PANEL_FLOORS = (9, 9, 9, 12, 5)      # storeys of the blocks, drawn at random
PANEL_LENGTH, PANEL_GAP = (46.0, 72.0), (9.0, 16.0)
PANEL_STAIR = 5                      # every this many bays a stairwell column of half-landing windows
PANEL_BACK_ROW = 38.0                # meters behind the first row: taller blocks in the haze
PANEL_COOL = 0.18                    # share of lit windows lit by a television (cool) instead of a lamp


@dataclass
class Camera:
    vx: float
    vy: float
    f: float

    def p(self, x, y, z):
        """Street coordinates (x right, y up, z away) -> pixels."""
        return np.array([self.vx + self.f * x / z, self.vy + self.f * (CAM_H - y) / z])

    def quad(self, pts):
        return np.array([self.p(*q) for q in pts])


CLOUDS = [(0.18, 0.12, 0.40, 0.05), (0.78, 0.18, 0.46, 0.06), (0.50, 0.30, 0.30, 0.035)]
OVERCAST = [(0.15, 0.06, 0.70, 0.08), (0.75, 0.08, 0.80, 0.09), (0.45, 0.22, 0.70, 0.06)]


def build_cityscape(spec, w, h, rng):
    time = C.scene_time(spec)
    fx = C.FX[time]
    site = spec.get('scene', {}).get('site') or 'street'
    if site not in SITES:
        raise ValueError(f"unknown cityscape site '{site}' (use {', '.join(SITES)})")
    pal = C.scene_palette(PALETTES, spec.get('scene', {}).get('palette'), time)
    hy = HORIZON * h
    cam = Camera(0.5 * w, hy, 0.62 * w)
    out = [C.sky(w, h, hy, pal)]
    if fx['sun'] in SUN_Y:
        out += C.sun(0.5 * w, hy + SUN_Y[fx['sun']] * h, 0.03 * w, pal)
    if fx['moon']:
        out += C.moon(0.70 * w, 0.14 * h, 0.014 * w, pal)
    if fx['stars']:
        out += C.stars(w, hy, rng, pal, fx['stars'] * 0.5)
    for i, (cx, cy, cw, ch) in enumerate(OVERCAST if fx['rain'] or fx['snow'] else CLOUDS):
        out += C.cloud(f'cloud_{i}', cx * w, cy * h, cw * w, ch * h, rng, pal, z=-90 + i * 0.1,
                       sun_x=0.5 * w if fx['rim'] else None)
    out += _skyline(cam, w, hy, pal, rng, fx)
    out += _street(cam, w, h, hy, pal, fx)
    if fx['sun'] == 'high':
        out += _day_shadow(cam, pal)
    for side in (-1, 1):
        if site == 'panel':
            blocks, spans = _panel_blocks(cam, side, pal, rng, fx)
            out += _yard(cam, side, hy, h, pal) + blocks + _yard_trees(cam, side, pal, rng, spans)
        else:
            out += _buildings(cam, side, pal, rng, fx)
        out += _lamps(cam, side, pal, fx)
    out += _wires(cam, pal)
    out += _cars(cam, pal, rng, fx)
    if fx['rain']:
        out += C.rain(w, h, rng, pal, count=1100)
    if fx['snow']:
        out += C.snow(w, h, rng, pal)
    return out, LIGHTS[time], w * 0.12


def _day_shadow(cam, pal):
    """The buildings on the sun side shade a long band of the road as one dark plane."""
    a = -(STREET_HALF + WALK)
    band = cam.quad([(a, 0.16, 1.2), (a + WALK + DAY_SHADOW_W, 0.01, 1.2), (a + WALK + DAY_SHADOW_W, 0.01, 400),
                     (a, 0.16, 400)])
    return [Drawable('street_shadow', 'scenery', -56.5, fill=[band], color=mix(pal['road'], pal['window_dark'], 0.5),
                     opacity=0.55, casts=False, receives=False)]


def _reflection(cam, name, x, y, z, width, color, zorder, ground='road'):
    """Mirror image of a light in the wet street: from the ground point to the point -y below it."""
    top, bottom = cam.p(x, 0.0, z), cam.p(x, -y * 0.8, z)
    return C.light_streak(name, top[0], top[1], bottom[1], width, color, zorder, [ground], WET_OPACITY)


def _skyline(cam, w, hy, pal, rng, fx):
    polys, lights = [], []
    x = 0.36 * w
    while x < 0.64 * w:
        bw = rng.uniform(0.012, 0.03) * w
        bh = rng.uniform(0.02, 0.09) * w
        polys.append(C.rect(x, hy - bh, x + bw, hy + 2))
        for _ in range(int(bh * bw / 120)):
            lx, ly = rng.uniform(x + 1, x + bw - 2), rng.uniform(hy - bh + 2, hy - 2)
            lights.append(C.rect(lx, ly, lx + 1.6, ly + 1.6))
        x += bw * rng.uniform(0.7, 1.1)
    col = C.haze(pal['skyline'], 0.45, pal)
    out = [Drawable('skyline', 'scenery', -85, fill=polys, fill_mode='each', color=col, casts=False, receives=False)]
    if fx['windows'] > 0:
        out.append(Drawable('skyline_lights', 'emissive', -84.9, fill=lights, fill_mode='each', color=pal['window_lit'],
                            opacity=0.8, clip=['skyline'], casts=False, receives=False))
    return out


def _street(cam, w, h, hy, pal, fx):
    far, near = 400.0, 1.2
    road = cam.quad([(-STREET_HALF, 0, near), (STREET_HALF, 0, near), (STREET_HALF, 0, far), (-STREET_HALF, 0, far)])
    out = [Drawable('road', 'scenery', -60, fill=[road], gradient=(pal['road_far'], pal['road'], (0, hy), (0, h)),
                    casts=False, receives=False)]
    for side in (-1, 1):
        a, b = side * STREET_HALF, side * (STREET_HALF + WALK)
        walk = cam.quad([(a, 0.15, near), (b, 0.15, near), (b, 0.15, far), (a, 0.15, far)])
        curb = cam.quad([(a, 0.0, near), (a, 0.15, near), (a, 0.15, far), (a, 0.0, far)])
        out += [Drawable(f'walk_{side}', 'scenery', -59, fill=[walk], gradient=(C.haze(pal['walk'], 0.6, pal), pal['walk'],
                                                                                (0, hy), (0, h)), casts=False, receives=False),
                Drawable(f'curb_{side}', 'scenery', -58.9, fill=[curb], color=mix(pal['walk'], pal['line'], 0.25),
                         casts=False, receives=False)]
    if fx['snow']:                                       # snow hides the markings: two pairs of wheel ruts
        ruts = [cam.quad([(x - 0.12, 0, near), (x + 0.12, 0, near), (x + 0.12, 0, far), (x - 0.12, 0, far)])
                for x in (-3.2, -1.6, 1.4, 3.0)]
        out.append(Drawable('road_ruts', 'scenery', -57, fill=ruts, fill_mode='each',
                            color=pal.get('rut', pal['road_far']), opacity=0.55, feather=1.5, clip=['road'],
                            casts=False, receives=False))
        return out
    dashes = []
    z = 2.0
    while z < 150:                                       # centre line: 3 m dashes, 3 m gaps
        dashes.append(cam.quad([(-0.08, 0, z), (0.08, 0, z), (0.08, 0, z + 3), (-0.08, 0, z + 3)]))
        z += 6
    for i in range(7):                                   # crosswalk near the viewer
        x0 = -STREET_HALF + 0.4 + i * 1.25
        dashes.append(cam.quad([(x0, 0, 2.2), (x0 + 0.6, 0, 2.2), (x0 + 0.6, 0, 4.4), (x0, 0, 4.4)]))
    out.append(Drawable('road_marks', 'scenery', -57, fill=dashes, fill_mode='each', color=pal['line'], opacity=0.75,
                        clip=['road'], casts=False, receives=False))
    return out


def _buildings(cam, side, pal, rng, fx):
    out = []
    x_wall = side * (STREET_HALF + WALK)
    z = 3.0
    walls = [pal['wall_a'], pal['wall_b'], pal['wall_c']]
    i = 0
    while z < 220:
        depth = rng.uniform(8, 18)
        height = rng.uniform(9, 26) * (1.0 if z < 60 else 0.8)
        z0, z1 = z, z + depth
        d = min(z0 / 160.0, 1.0)                         # aerial perspective by distance
        wall = walls[i % 3]
        if fx['sun'] == 'high':                          # left facades face away from the sun, right ones toward it
            wall = np.clip(wall * (DAY_SHADE if side < 0 else DAY_LIT), 0, 1)
        base = C.haze(wall, d * 0.9, pal)
        top = mix(base, pal['roof_rim'], 0.25)
        face = cam.quad([(x_wall, 0, z0), (x_wall, height, z0), (x_wall, height, z1), (x_wall, 0, z1)])
        name = f'bld_{side}_{i}'
        zorder = -50 + 30.0 / z0
        out.append(Drawable(name, 'scenery', zorder, fill=[face], gradient=(top, base, (0, face[:, 1].min()), (0, face[:, 1].max())),
                            strokes=[geom.stroke_polygon(np.vstack([face, face[:1]]), 1.0)],
                            line_color=mix(base, np.zeros(3), 0.45), casts=False, receives=False))
        front = cam.quad([(x_wall, 0, z0), (x_wall + side * 12, 0, z0), (x_wall + side * 12, height, z0), (x_wall, height, z0)])
        out.append(Drawable(name + '_front', 'scenery', zorder + 0.001, fill=[front],
                            color=C.haze(pal['wall_front'], d * 0.9, pal), casts=False, receives=False))
        rim = cam.quad([(x_wall, height, z0), (x_wall, height + 0.35, z0), (x_wall, height + 0.35, z1), (x_wall, height, z1)])
        out.append(Drawable(name + '_rim', 'scenery', zorder + 0.002, fill=[rim], color=C.haze(pal['roof_rim'], d * 0.6, pal),
                            casts=False, receives=False))
        out += _windows(cam, name, x_wall, z0, z1, height, zorder, d, pal, rng, fx['windows'])
        if rng.random() < 0.55 and z0 < 70:
            out += _sign(cam, name, side, x_wall, z0 + depth * 0.3, height, zorder, pal, rng, fx)
        z = z1 + rng.uniform(0.0, 1.5)
        i += 1
    return out


def _yard(cam, side, hy, h, pal):
    """The ground between the sidewalk and the blocks (snow on a winter night)."""
    a, b = side * (STREET_HALF + WALK), side * (STREET_HALF + WALK + PANEL_YARD + PANEL_DEPTH)
    q = cam.quad([(a, 0.15, 1.2), (b, 0.15, 1.2), (b, 0.15, 400.0), (a, 0.15, 400.0)])
    col = pal.get('yard', pal['walk'])
    return [Drawable(f'yard_{side}', 'scenery', -59.5, fill=[q], gradient=(C.haze(col, 0.6, pal), col, (0, hy), (0, h)),
                     casts=False, receives=False)]


def _panel_blocks(cam, side, pal, rng, fx):
    """Prefabricated panel blocks set back behind a yard: long slabs with a regular grid of windows,
    storey seams, balcony slabs and stairwell windows, a second row of taller blocks in the haze.
    Returns the drawables and the (z0, z1, zorder) span of each front block."""
    out, spans = [], []
    for row, x_off, z_start in ((0, 0.0, 6.0), (1, PANEL_BACK_ROW, 20.0)):
        x_wall = side * (STREET_HALF + WALK + PANEL_YARD + x_off)
        z, i = z_start, 0
        while z < 260:
            floors = int(rng.choice(PANEL_FLOORS)) + (4 if row else 0)
            length = rng.uniform(*PANEL_LENGTH)
            z0, z1, height = z, z + length, floors * PANEL_FLOOR + 0.6
            d = min(z0 / 180.0 + 0.25 * row, 1.0)
            zorder = (-50 if row == 0 else -54) + (30.0 if row == 0 else 3.0) / z0
            name = f'panel_{row}_{side}_{i}'
            out += _panel_block(cam, name, side, x_wall, z0, z1, height, floors, zorder, d, pal, rng, fx, row)
            if row == 0:
                spans.append((z0, z1, zorder))
            z = z1 + rng.uniform(*PANEL_GAP)
            i += 1
    return out, spans


def _panel_block(cam, name, side, x, z0, z1, height, floors, zorder, d, pal, rng, fx, row):
    walls = [pal['wall_a'], pal['wall_b'], pal['wall_c']]
    base = C.haze(walls[rng.integers(0, 3)], d * 0.9, pal)
    lit_foot = mix(base, pal['lamp_pool'], 0.16 if fx['lamps'] else 0.0)   # sodium lamps light the lower storeys
    face = cam.quad([(x, 0, z0), (x, height, z0), (x, height, z1), (x, 0, z1)])
    out = [Drawable(name, 'scenery', zorder, fill=[face],
                    gradient=(darken(base, 0.88), lit_foot, (0, face[:, 1].min()), (0, face[:, 1].max())),
                    strokes=[geom.stroke_polygon(np.vstack([face, face[:1]]), 1.0)],
                    line_color=mix(base, np.zeros(3), 0.45), casts=False, receives=False)]
    gable = cam.quad([(x, 0, z0), (x + side * PANEL_DEPTH, 0, z0), (x + side * PANEL_DEPTH, height, z0), (x, height, z0)])
    out.append(Drawable(name + '_gable', 'scenery', zorder + 0.001, fill=[gable],
                        color=C.haze(pal['wall_front'], d * 0.9, pal), casts=False, receives=False))
    seam_col = C.haze(pal.get('seam', mix(base, np.zeros(3), 0.35)), d * 0.8, pal)
    seams = []
    width = max(cam.f * 0.05 / z0, 0.7)
    for f in range(1, floors):                                  # storey seams on the facade and the gable
        y = f * PANEL_FLOOR + 0.3
        seams.append(geom.stroke_polygon(np.array([cam.p(x, y, z0), cam.p(x, y, z1)]), np.full(2, width)))
        seams.append(geom.stroke_polygon(np.array([cam.p(x, y, z0), cam.p(x + side * PANEL_DEPTH, y, z0)]),
                                         np.full(2, width)))
    for k in range(1, int(PANEL_DEPTH / 3.0)):                  # vertical joints of the gable panels
        xx = x + side * k * 3.0
        seams.append(geom.stroke_polygon(np.array([cam.p(xx, 0, z0), cam.p(xx, height, z0)]), np.full(2, width)))
    out.append(Drawable(name + '_seams', 'scenery', zorder + 0.002, fill=seams, fill_mode='union', color=seam_col,
                        opacity=0.55, clip=[name, name + '_gable'], casts=False, receives=False))
    bays = int((z1 - z0 - 1.6) / PANEL_BAY)
    warm, cool, dark, slabs, stair, stair_dark = [], [], [], [], [], []
    for c in range(bays):
        za = z0 + 1.2 + c * PANEL_BAY
        stairwell = c % PANEL_STAIR == PANEL_STAIR // 2
        for f in range(floors):
            y0 = f * PANEL_FLOOR + 0.95
            if stairwell:                                       # half-landing windows sit between the storeys
                q = cam.quad([(x, y0 + 0.9, za + 0.3), (x, y0 + 2.0, za + 0.3), (x, y0 + 2.0, za + 1.1),
                              (x, y0 + 0.9, za + 1.1)])
                (stair if rng.random() < 0.6 else stair_dark).append(q)
                continue
            q = cam.quad([(x, y0, za), (x, y0 + 1.45, za), (x, y0 + 1.45, za + 1.5), (x, y0, za + 1.5)])
            r = rng.random()
            if r < fx['windows']:
                (cool if rng.random() < PANEL_COOL else warm).append(q)
            else:
                dark.append(q)
            if row == 0 and f > 0 and c % 4 in (1, 2):           # balcony slab below the window
                slabs.append(cam.quad([(x, y0 - 0.65, za - 0.3), (x, y0 - 0.05, za - 0.3), (x, y0 - 0.05, za + 1.8),
                                       (x, y0 - 0.65, za + 1.8)]))
    win_dark = C.haze(pal['window_dark'], d * 0.8, pal)
    if dark or stair_dark:
        out.append(Drawable(name + '_win_dark', 'scenery', zorder + 0.003, fill=dark + stair_dark, fill_mode='each',
                            color=win_dark, clip=[name], casts=False, receives=False))
    if slabs:
        out.append(Drawable(name + '_balconies', 'scenery', zorder + 0.0035, fill=slabs, fill_mode='each',
                            color=mix(base, seam_col, 0.6), clip=[name], casts=False, receives=False))
    for part, col in ((warm, pal['window_lit']), (cool, pal.get('window_cool', pal['window_lit'])),
                      (stair, mix(pal['window_lit'], np.ones(3), 0.35))):
        if part:
            out.append(Drawable(f'{name}_win_{len(out)}', 'emissive', zorder + 0.004, fill=part, fill_mode='each',
                                color=mix(col, pal['haze'], d * 0.5), clip=[name], casts=False, receives=False))
    return out


def _yard_trees(cam, side, pal, rng, spans):
    """Bare trees in the yard, each drawn just above the block it stands in front of."""
    out = []
    for k, z in enumerate((9.0, 17.0, 28.0, 43.0, 64.0)):
        z += rng.uniform(-2.0, 2.0)
        x = side * (STREET_HALF + WALK + rng.uniform(2.5, PANEL_YARD - 2.0))
        span = next((s for s in spans if s[0] <= z <= s[1]), None)
        zorder = (span[2] if span else -50 + 30.0 / z) + 0.05
        base, top = cam.p(x, 0.15, z), cam.p(x, rng.uniform(7.0, 11.0), z)
        out += C.bare_tree(f'tree_{side}_{k}', base[0], base[1], base[1] - top[1],
                           C.haze(pal.get('tree', pal['pole']), min(z / 160.0, 1.0) * 0.8, pal), zorder, rng,
                           lean=rng.uniform(-0.12, 0.12), depth=5)
    return out


def _windows(cam, name, x, z0, z1, height, zorder, d, pal, rng, lit_share):
    lit, dark = [], []
    floors = int((height - 3.5) / 3.0)
    cols = max(int((z1 - z0 - 1.0) / 2.2), 1)
    for f in range(floors):
        y0 = 3.5 + f * 3.0
        for c in range(cols):
            za = z0 + 0.8 + c * 2.2
            q = cam.quad([(x, y0, za), (x, y0 + 1.6, za), (x, y0 + 1.6, za + 1.3), (x, y0, za + 1.3)])
            (lit if rng.random() < lit_share else dark).append(q)
    out = []
    if dark:
        out.append(Drawable(name + '_win_dark', 'scenery', zorder + 0.003, fill=dark, fill_mode='each',
                            color=C.haze(pal['window_dark'], d * 0.8, pal), clip=[name], casts=False, receives=False))
    if lit:
        out.append(Drawable(name + '_win_lit', 'emissive', zorder + 0.004, fill=lit, fill_mode='each',
                            color=mix(pal['window_lit'], pal['haze'], d * 0.5), clip=[name], casts=False, receives=False))
    if lit_share == 0 and dark:                          # daylight: glass mirrors the sky in the upper panes
        sheen = [np.array([q[0], q[1], q[2], q[0] + (q[3] - q[0]) * 0.45]) for q in dark]
        out.append(Drawable(name + '_win_sky', 'scenery', zorder + 0.004, fill=sheen, fill_mode='each',
                            color=mix(pal['window_lit'], pal['haze'], d * 0.5), opacity=0.7, clip=[name],
                            casts=False, receives=False))
    return out


def _sign(cam, name, side, x, z, height, zorder, pal, rng, fx):
    """Vertical sign board sticking out from the wall, glowing when the lamps are on."""
    y0 = rng.uniform(4.0, max(height - 6.0, 4.5))
    xo = x - side * 1.4
    q = cam.quad([(x, y0, z), (xo, y0, z), (xo, y0 + 4.5, z), (x, y0 + 4.5, z)])
    col = [pal['sign_a'], pal['sign_b'], pal['sign_c']][rng.integers(0, 3)]
    board = Drawable(name + '_sign', 'emissive', zorder + 0.006, fill=[q], color=mix(col, np.ones(3), 0.35),
                     strokes=[geom.stroke_polygon(np.vstack([q, q[:1]]), 1.2)], line_color=col,
                     casts=False, receives=False)
    if not fx['lamps']:
        board.color = mix(col, pal['wall_front'], 0.25)
        return [board]
    glow = geom.ellipse(q[:, 0].mean(), q[:, 1].mean(), np.ptp(q[:, 0]) * 1.4, np.ptp(q[:, 1]) * 0.8, 40)
    out = [Drawable(name + '_sign_glow', 'emissive', zorder + 0.005, fill=[glow], color=col, opacity=0.35,
                    feather=np.ptp(q[:, 0]) * 0.6, casts=False, receives=False), board]
    if fx['wet']:
        out.append(_reflection(cam, name + '_sign_wet', (x + xo) / 2, y0 + 2.2, z, np.ptp(q[:, 0]) * 0.8, col, -55,
                               ground=f'walk_{side}'))
    return out


def _lamps(cam, side, pal, fx):
    out = []
    x = side * (STREET_HALF + 0.4)
    for k, z in enumerate([4.0, 11.0, 18.0, 25.0, 32.0, 39.0, 46.0]):
        base, top = cam.p(x, 0.15, z), cam.p(x, 6.0, z)
        arm = cam.p(x - side * 1.2, 6.2, z)
        width = max(cam.f * 0.12 / z, 1.0)
        pole = geom.stroke_polygon(np.array([base, top, arm]), width)
        r = max(cam.f * 0.35 / z, 2.0)
        zorder = -50 + 30.0 / z + 0.01
        pool = cam.quad([(x - side * 1.2 - 2.2, 0.01, z - 2.0), (x - side * 1.2 + 2.2, 0.01, z - 2.0),
                         (x - side * 1.2 + 2.2, 0.01, z + 2.0), (x - side * 1.2 - 2.2, 0.01, z + 2.0)])
        pool = geom.ellipse(pool[:, 0].mean(), pool[:, 1].mean(), np.ptp(pool[:, 0]) / 2, np.ptp(pool[:, 1]) / 2, 40)
        out += [Drawable(f'lamp_pole_{side}_{k}', 'scenery', zorder, fill=[pole], fill_mode='union', color=pal['pole'],
                         casts=False, receives=False),
                Drawable(f'lamp_{side}_{k}', 'emissive', zorder + 0.002, fill=[geom.ellipse(*arm, r, r * 0.7, 24)],
                         color=pal['lamp'] if fx['lamps'] else mix(pal['lamp'], pal['pole'], 0.4),
                         casts=False, receives=False)]
        if fx['lamps']:
            out += [Drawable(f'lamp_pool_{side}_{k}', 'emissive', -56, fill=[pool], color=pal['lamp_pool'], opacity=0.45,
                             feather=r * 2.0, casts=False, receives=False),
                    Drawable(f'lamp_glow_{side}_{k}', 'emissive', zorder + 0.001,
                             fill=[geom.ellipse(*arm, r * 3, r * 3, 32)], color=pal['lamp_pool'], opacity=0.6,
                             feather=r * 1.6, casts=False, receives=False)]
        if fx['wet']:
            out.append(_reflection(cam, f'lamp_wet_{side}_{k}', x - side * 1.2, 6.2, z, r * 1.6, pal['lamp_pool'], -55))
    return out


def _cars(cam, pal, rng, fx):
    """A few cars seen from behind (tail lights) and one oncoming (headlights)."""
    out = []
    for k, (x, z, away) in enumerate([(2.2, 14.0, True), (2.0, 34.0, True), (-2.3, 24.0, False), (2.4, 70.0, True)]):
        half, body_h, cab_h = 0.9, 0.85, 1.45
        body = cam.quad([(x - half, 0.25, z), (x + half, 0.25, z), (x + half, body_h, z), (x - half, body_h, z)])
        cab = cam.quad([(x - half * 0.8, body_h, z + 0.6), (x + half * 0.8, body_h, z + 0.6),
                        (x + half * 0.65, cab_h, z + 1.0), (x - half * 0.65, cab_h, z + 1.0)])
        wheels = [cam.quad([(x + sx * half * 0.95 - 0.12, 0.0, z), (x + sx * half * 0.95 + 0.12, 0.0, z),
                            (x + sx * half * 0.95 + 0.12, 0.35, z), (x + sx * half * 0.95 - 0.12, 0.35, z)]) for sx in (-1, 1)]
        zorder = -50 + 30.0 / z + 0.015
        d = min(z / 160.0, 1.0)
        col = C.haze(mix(pal['wall_front'], pal['pole'], 0.5), d, pal)
        out.append(Drawable(f'car_{k}', 'scenery', zorder, fill=[body, cab] + wheels, fill_mode='each', color=col,
                            casts=False, receives=False))
        light_col = pal['sign_a'] if away else pal['lamp']
        r = max(cam.f * 0.16 / z, 1.2)
        on = fx['lamps']
        for sx in (-1, 1):
            c = cam.p(x + sx * half * 0.72, body_h - 0.15, z)
            out.append(Drawable(f'car_{k}_light_{sx}', 'emissive', zorder + 0.002,
                                fill=[geom.ellipse(*c, r * 1.4, r * 0.8, 20)],
                                color=mix(light_col, np.ones(3), 0.4) if on else mix(light_col, col, 0.45),
                                casts=False, receives=False))
            if on:
                out.append(Drawable(f'car_{k}_glow_{sx}', 'emissive', zorder + 0.001,
                                    fill=[geom.ellipse(*c, r * 4, r * 2.5, 24)], color=light_col, opacity=0.45,
                                    feather=r * 2.0, casts=False, receives=False))
            if fx['wet']:
                out.append(_reflection(cam, f'car_{k}_wet_{sx}', x + sx * half * 0.72, body_h - 0.15, z, r * 1.5,
                                       light_col, zorder - 0.0005))
    return out


def _wires(cam, pal):
    """Utility poles on the left with three sagging wires running to the vanishing point."""
    out, wires = [], []
    x = -(STREET_HALF + 1.2)
    zs = [3.0, 13.0, 23.0, 33.0, 43.0, 53.0, 63.0]
    for k, z in enumerate(zs):
        base, top = cam.p(x, 0.15, z), cam.p(x, 10.5, z)
        width = max(cam.f * 0.25 / z, 1.0)
        bar = np.array([cam.p(x - 1.0, 9.6, z), cam.p(x + 1.4, 9.6, z)])
        out.append(Drawable(f'upole_{k}', 'scenery', -50 + 30.0 / z + 0.02,
                            fill=[geom.stroke_polygon(np.array([base, top]), width),
                                  geom.stroke_polygon(bar, width * 0.6)], fill_mode='union', color=pal['pole'],
                            casts=False, receives=False))
    for dx in (-0.9, 0.2, 1.3):
        for z0, z1 in zip(zs[:-1], zs[1:]):
            t = np.linspace(0, 1, 24)
            sag = 0.9 * 4 * t * (1 - t)
            pts = np.array([cam.p(x + dx, 9.6 - s, z0 + (z1 - z0) * tt) for tt, s in zip(t, sag)])
            wires.append(geom.stroke_polygon(pts, max(cam.f * 0.02 / z0, 0.8)))
    out.append(Drawable('wires', 'scenery', -50 + 30.0 / zs[0] + 0.03, fill=wires, fill_mode='union', color=pal['pole'],
                        casts=False, receives=False))
    return out
