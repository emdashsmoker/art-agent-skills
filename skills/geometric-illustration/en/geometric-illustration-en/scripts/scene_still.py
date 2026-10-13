"""Still life: bottle, jug and fruit on a draped table in warm window light at dusk
(set 'classic'), or one of the modern sets in scene_modern (spec scene.set).

Composition: a classic triangle (tall bottle at the back left, jug at the
back right, fruit spilling forward over the drape), seen slightly from above
so the table plane recedes. The objects are mannequin solids (surfaces of
revolution are chains of tapered cylinders), which gives real form shading,
overlaps, contours and specular highlights; the table, wall and drape are
designed shapes. Light comes from a window at the upper left.
"""
import numpy as np

import geom
import mannequin as M
import scene_modern
from frames import BodyFrame
from palette import darken, line_color
from raster import hex_rgb, mix
from scene import Drawable

PALETTE = {
    'wall_top': '#5B4A3F', 'wall_low': '#2E2522', 'window_light': '#F3C48E', 'table': '#7A4E33',
    'table_edge': '#4E3022', 'grain': '#5E3A27', 'drape': '#3E5A78', 'drape_light': '#6E8EAE',
    'bottle': '#2E5E44', 'jug': '#E6D8BE', 'jug_band': '#3E5A78', 'apple': '#B8323A', 'apple_blush': '#E3A542',
    'lemon': '#E8C547', 'grape': '#5A3768', 'stem': '#4A3A26', 'gloss': '#FFF4E0',
}
LIGHT = [-0.65, -0.55, 0.55]
PITCH = -0.38                    # camera looks down on the table
TABLE_FRONT, TABLE_BACK = 1.5, -1.8
JUG = (0.55, -1.05)                                     # x, z of the jug axis on the table
JUG_PROFILE = [(0.0, 0.28), (0.35, 0.44), (0.85, 0.42), (1.25, 0.26), (1.45, 0.21), (1.62, 0.27)]
UNIT_FRAC = 1 / 7.0


def _pal(spec):
    over = spec.get('scene', {}).get('palette') or {}
    pal = dict(PALETTE)
    pal.update(over)
    out = {k: hex_rgb(v) for k, v in pal.items()}
    if 'drape' in over and 'drape_light' not in over:      # keep the cloth's lit side in the same hue
        out['drape_light'] = mix(out['drape'], np.ones(3, np.float32), 0.35)
    return out


def _view(p):
    return M.rotate_view(np.asarray(p, float), 0.0, PITCH)


def _project(frame, pts):
    return frame.map(np.array([_view(p)[:2] for p in pts]))


def _solids_in_view(solids):
    return M.view_solids(solids, 0.0, PITCH)


def revolve(cx, cz, profile):
    """Surface of revolution standing on the table: profile = [(height, radius), ...] from the bottom up."""
    pts = [(cx, -hgt, cz) for hgt, _ in profile]
    return M.chain(pts, [r for _, r in profile])


def _objects(pal):
    """(name, world pieces, material group, gloss, base color) for every object on the table."""
    jug = M.Piece('jug', revolve(JUG[0], JUG[1], JUG_PROFILE), k=0.08)
    arc = [(JUG[0] + 0.24 + 0.30 * np.sin(t), -0.95 - 0.42 * np.cos(t), JUG[1]) for t in np.linspace(0.15, np.pi - 0.35, 9)]
    handle = M.Piece('handle', M.chain(arc, [0.05] * 9), k=0.08, parent='jug', attach_k=0.03, attach_n=9)
    bottle = M.Piece('bottle', revolve(-1.15, -0.85, [(0.0, 0.30), (1.55, 0.31), (1.95, 0.13), (2.55, 0.095),
                                                      (2.62, 0.115), (2.70, 0.10)]), k=0.05)
    apple_a = M.Piece('apple_a', [M.sphere((-0.25, -0.27, 0.35), 0.29), M.sphere((-0.25, -0.40, 0.35), 0.25)], k=0.08)
    apple_b = M.Piece('apple_b', [M.sphere((0.42, -0.25, 0.75), 0.27), M.sphere((0.42, -0.37, 0.75), 0.23)], k=0.08)
    lemon = M.Piece('lemon', [M.sphere((1.28, -0.23, 0.16), 0.23), M.cone((1.02, -0.20, 0.21), (1.54, -0.24, 0.10), 0.15, 0.14),
                              M.sphere((0.88, -0.19, 0.24), 0.05), M.sphere((1.68, -0.25, 0.07), 0.045)], k=0.12)
    g = pal['gloss']
    return [('bottle', [bottle], 'glass', (g, 60, 0.95), pal['bottle']),
            ('jug', [jug, handle], 'ceramic', (g, 40, 0.8), pal['jug']),
            ('apple_a', [apple_a], 'fruit', (g, 30, 0.75), pal['apple']),
            ('apple_b', [apple_b], 'fruit', (g, 30, 0.75), mix(pal['apple'], pal['apple_blush'], 0.35)),
            ('lemon', [lemon], 'lemon', (g, 25, 0.6), pal['lemon'])]


def _in_view(pieces):
    return [M.Piece(p.name, _solids_in_view(p.solids), p.k, p.parent, p.attach_k, p.attach_n) for p in pieces]


def _view_depth(pieces):
    """Nearer objects (larger z after the camera tilt) are drawn on top."""
    return float(np.mean([_view(s.a)[2] for s in pieces[0].solids]))


def build_still_life(spec, w, h, rng):
    set_name = spec.get('scene', {}).get('set', 'classic')
    unit = w * (UNIT_FRAC if set_name == 'classic' else scene_modern.UNIT_FRAC)
    frame = BodyFrame((w * 0.5, h * (0.60 if set_name == 'classic' else scene_modern.CENTER_Y)), unit)
    lw = max(unit * 0.012, 1.2) * spec['line']['weight']
    if set_name != 'classic':
        light = scene_modern.LIGHTS.get(set_name, LIGHT)
        fb = M.FormBuilder(frame, (h, w), light, lw)
        out, light = scene_modern.build_modern(set_name, spec, frame, w, h, rng, fb, _in_view, PITCH)
        return out, light, unit
    pal = _pal(spec)
    fb = M.FormBuilder(frame, (h, w), LIGHT, lw)
    out = _room(frame, w, h, pal, rng)
    for name, pieces, group, gloss, color in _objects(pal):
        z = 5 + _view_depth(pieces)
        res = fb.build(name, group, z, _in_view(pieces), color=color, line_color=line_color(color), gloss=gloss)
        out += res.drawables
        out += _contact_shadow(frame, pieces[0], name)
        if name == 'jug':
            out += _jug_band(frame, pal, z + 0.01) + _jug_mouth(frame, pal, z + 0.02)
    out += _grapes(fb, frame, pal, rng)
    out += _stems(frame, pal, lw)
    return out, LIGHT, unit


def _room(frame, w, h, pal, rng):
    back = _project(frame, [(-6, 0, TABLE_BACK)])[0][1]
    front = _project(frame, [(-6, 0, TABLE_FRONT)])[0][1]
    out = [Drawable('wall', 'bg', -100, fill=[np.array([[0, 0], [w, 0], [w, back + 2], [0, back + 2]], float)],
                    gradient=(pal['wall_top'], pal['wall_low'], (0, 0), (w * 0.6, back)), casts=False, receives=True)]
    win = geom.ellipse(w * 0.05, h * 0.05, w * 0.55, h * 0.45, 64)
    out.append(Drawable('window_light', 'emissive', -99, fill=[win], color=pal['window_light'], opacity=0.35,
                        feather=w * 0.12, casts=False, receives=False))
    top = np.array([[0, back], [w, back], [w, front], [0, front]], float)
    out.append(Drawable('table', 'wood', -60, fill=[top], gradient=(darken(pal['table'], 0.75), pal['table'], (0, back), (0, front)),
                        casts=False, receives=True))
    grain = []
    for k in range(26):
        z = TABLE_BACK + (TABLE_FRONT - TABLE_BACK) * rng.uniform(0, 1)
        x0, x1 = rng.uniform(-6, 2), rng.uniform(2, 6)
        p = _project(frame, [(x0, 0, z), (x1, 0, z + rng.uniform(-0.05, 0.05))])
        grain.append(geom.stroke_polygon(geom.resample(p, 20), max(frame.px(0.008), 0.8) * geom.taper(20, 0.3, 0.3)))
    out.append(Drawable('grain', 'wood', -59.9, fill=grain, fill_mode='union', color=pal['grain'], opacity=0.5,
                        clip=['table'], casts=False, receives=False))
    edge = np.array([[0, front], [w, front], [w, front + frame.px(0.35)], [0, front + frame.px(0.35)]], float)
    out.append(Drawable('table_edge', 'wood', -59, fill=[edge], color=pal['table_edge'], casts=False, receives=False,
                        strokes=[geom.stroke_polygon(np.array([[0, front], [w, front]]), frame.px(0.012))],
                        line_color=darken(pal['table_edge'], 0.6)))
    under = np.array([[0, front + frame.px(0.35)], [w, front + frame.px(0.35)], [w, h], [0, h]], float)
    out.append(Drawable('under', 'bg', -58.9, fill=[under], color=darken(pal['wall_low'], 0.7), casts=False, receives=False))
    out += _drape(frame, w, h, front, pal, rng)
    return out


def _drape(frame, w, h, front_y, pal, rng):
    """Cloth lying on the left of the table and hanging over the front edge in folds."""
    on_table = _project(frame, [(-6, 0, -0.2), (-2.4, 0, -0.5), (-0.6, 0, 0.1), (0.9, 0, 0.9), (1.3, 0, TABLE_FRONT),
                                (-6, 0, TABLE_FRONT)])
    xs = np.linspace(-0.1 * w, frame.map([[1.0, 0]])[0][0], 9)
    hem = [(x, h * 0.98 + rng.uniform(-0.03, 0.03) * h) for x in xs[::-1]]
    hang = np.vstack([[[xs[0], front_y], [xs[-1], front_y]], np.array(hem)])
    poly = geom.catmull_rom(np.vstack([on_table[:-1], hang[1:]]), closed=True, samples=10)
    out = [Drawable('drape', 'cloth', -55, fill=[poly], gradient=(pal['drape_light'], pal['drape'], (0, front_y - frame.px(1.2)),
                                                                   (frame.map([[1.5, 0]])[0][0], h)),
                    strokes=[geom.stroke_polygon(np.vstack([poly, poly[:1]]), frame.px(0.012))],
                    line_color=line_color(pal['drape']), form_radius=frame.px(0.5), casts=False, receives=True)]
    folds, shadows = [], []
    for x in xs[1:-1]:
        x2 = x + rng.uniform(-0.02, 0.02) * w
        path = geom.resample(geom.catmull_rom(np.array([[x, front_y + 2], [x + 4, front_y + (h - front_y) * 0.5], [x2, h]])), 24)
        folds.append(geom.stroke_polygon(path, frame.px(0.01) * geom.taper(24, 0.5, 0.0)))
        band = np.array([[x - 2, front_y], [x + 10, front_y + (h - front_y) * 0.5], [x2 + 16, h], [x2 - 4, h],
                         [x + 2, front_y + (h - front_y) * 0.5]])
        shadows.append(geom.catmull_rom(band, closed=True))
    for k in range(4):                                           # folds on the table top
        a = _project(frame, [(-5 + k * 1.1, 0, -0.1 + k * 0.1), (-4.2 + k * 1.2, 0, 1.2)])
        folds.append(geom.stroke_polygon(geom.resample(a, 16), frame.px(0.01) * geom.taper(16, 0.5, 0.5)))
    out.append(Drawable('drape_folds', 'cloth', -54.9, fill=folds, fill_mode='union', color=darken(pal['drape'], 0.6),
                        clip=['drape'], casts=False, receives=False))
    out += [Drawable(f'drape_shadow_{i}', 'cloth', 0, fill=[s], kind='shadow', clip_vis=['drape'], feather=frame.px(0.05),
                     opacity=0.7) for i, s in enumerate(shadows)]
    return out


def _contact_shadow(frame, piece, name):
    """Cast shadow on the table: the footprint stretched away from the window light (world coordinates)."""
    base = np.mean([s.a for s in piece.solids], axis=0)
    base[1] = 0.0
    height = max(-min(s.a[1] - s.ra for s in piece.solids), 0.3)
    foot = max(s.ra for s in piece.solids)
    reach = np.array([height * 0.75, 0.0, -height * 0.45])
    pts = []
    for a in np.linspace(0, 2 * np.pi, 40, endpoint=False):
        p = base + np.array([np.cos(a) * foot, 0.0, np.sin(a) * foot * 0.8])
        if np.cos(a) > 0:
            p = p + reach * np.cos(a) ** 0.5
        pts.append(p)
    return [Drawable(f'{name}_cast', 'wood', 0, fill=[_project(frame, pts)], kind='shadow', clip_vis=['table', 'drape'],
                     feather=frame.px(0.06), opacity=0.85)]


def _grapes(fb, frame, pal, rng):
    pieces = [M.Piece('grape_stem', [M.cone((-1.85, -0.85, 0.75), (-1.75, -0.65, 0.78), 0.02, 0.02)])]
    k = 0
    for row in range(5):
        n = 5 - row
        for i in range(n):
            x = -1.95 + (i - (n - 1) / 2) * 0.19 + rng.uniform(-0.02, 0.02) + row * 0.03
            y = -0.55 + row * 0.15
            zz = 0.80 + rng.uniform(-0.08, 0.08) + (0.06 if (i + row) % 2 else 0)
            pieces.append(M.Piece(f'grape_{k}', [M.sphere((x, y, zz), 0.105 + rng.uniform(-0.01, 0.01))],
                                  parent='grape_stem', attach_k=0.0, attach_n=0))
            k += 1
    res = fb.build('grapes', 'fruit', 5 + _view_depth(pieces[1:]), _in_view(pieces), color=pal['grape'],
                   line_color=line_color(pal['grape']), gloss=(pal['gloss'], 35, 0.85))
    return res.drawables + _contact_shadow(frame, M.Piece('g', [s for p in pieces[1:] for s in p.solids]), 'grapes')


def _jug_band(frame, pal, z):
    """Painted blue band around the jug belly, following the form on the side facing the viewer."""
    a = np.linspace(-np.pi * 0.5, np.pi * 0.5, 40)
    top = _project(frame, [(0.55 + 0.47 * np.sin(t), -0.62, -1.05 + 0.47 * np.cos(t)) for t in a])
    bot = _project(frame, [(0.55 + 0.45 * np.sin(t), -0.48, -1.05 + 0.45 * np.cos(t)) for t in a[::-1]])
    return [Drawable('jug_band', 'ceramic', z, fill=[np.vstack([top, bot])], color=pal['jug_band'], clip=['jug'],
                     opacity=0.85, casts=False, receives=False)]


def _jug_mouth(frame, pal, z):
    """Opening of the jug seen from above: dark inside ellipse inside the rim."""
    top = JUG_PROFILE[-1][0]
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    inner = _project(frame, [(JUG[0] + 0.20 * np.cos(t), -top - 0.03, JUG[1] + 0.20 * np.sin(t)) for t in a])
    return [Drawable('jug_mouth', 'ceramic', z, fill=[inner], color=darken(pal['jug'], 0.35), clip=['jug'],
                     strokes=[geom.stroke_polygon(np.vstack([inner, inner[:1]]), frame.px(0.012))],
                     line_color=line_color(pal['jug']), casts=False, receives=False)]


def _stems(frame, pal, lw):
    out = []
    for name, (x, y, z) in (('apple_a', (-0.25, -0.62, 0.35)), ('apple_b', (0.42, -0.57, 0.75))):
        p = _project(frame, [(x, y + 0.04, z), (x + 0.03, y - 0.06, z), (x + 0.07, y - 0.13, z)])
        out.append(Drawable(f'{name}_stem', 'fruit', 7, fill=[geom.stroke_polygon(geom.resample(p, 10), lw * 1.6 * geom.taper(10, 0.0, 0.6, 0.5))],
                            fill_mode='union', color=pal['stem'], casts=False, receives=False))
    return out
