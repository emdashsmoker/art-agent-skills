"""Modern still lifes (spec scene.set): a desk at work, a cafe table, a gaming setup,
a night kitchen.

Composition follows the classic still life: a triangle of masses on a table seen from
slightly above, one key light, and a few saturated accents against a quiet ground.
What changes is the light source: an evening desk lamp, afternoon window light in a
cafe, screens plus RGB strips in a dark gaming room, where emissive surfaces are
the brightest values and the main light sits low and cool, and a single warm bulb in a
late kitchen with a snowy panel-block night in the window.

Hard objects (laptop, phone, keyboard, monitor, cups, plates, cans) are flat-faced or
cylindrical props (scene_props); soft or organic ones (mouse, headset, earbud case,
strawberry, lamp arm) are mannequin solids. Screen content is drawn as emissive insets
on the display faces.
"""
import numpy as np

import geom
import mannequin as M
import scene_common as C
import scene_props as P
from palette import darken, lighten, line_color
from raster import hex_rgb, mix
from scene import Drawable

SETS = ('desk', 'cafe', 'gaming', 'kitchen')
TABLE_FRONT, TABLE_BACK = 2.2, -1.8
UNIT_FRAC, CENTER_Y = 1 / 5.8, 0.66         # closer framing than the classic set: devices need the detail

PALETTES = {
    'desk': {'wall_top': '#4C4239', 'wall_low': '#2A2320', 'table': '#6E4C34', 'table_edge': '#46301F',
             'grain': '#57392A', 'lamp_light': '#FFD39A', 'laptop': '#B9BCC4', 'laptop_key': '#3A3D45',
             'editor': '#1E2230', 'mug': '#4F7A86', 'coffee': '#3A2418', 'phone': '#2A2C33',
             'wallpaper_a': '#3B4A8C', 'wallpaper_b': '#C26E9A', 'lamp': '#2E3138', 'pot': '#B5674A',
             'soil': '#3A2A20', 'leaf': '#3D6B3A', 'leaf_edge': '#C9C26A', 'cover': '#8A3B3B', 'pages': '#EFE6D2',
             'pen': '#1E1F24', 'gloss': '#FFF4E0', 'steam': '#FFFFFF'},
    'cafe': {'wall_top': '#E8D9C2', 'wall_low': '#A88E72', 'window': '#F6E7CC', 'frame': '#5A4232',
             'table': '#E9E4DC', 'table_edge': '#B8B0A4', 'vein': '#B9B2AA', 'cup': '#F3F0EA', 'latte': '#C6966A',
             'foam': '#F6E8D2', 'plate': '#FAF9F5', 'sponge': '#E6C487', 'frosting': '#F7EFE4',
             'cream': '#FFF6E8', 'berry': '#D23A3A', 'fork': '#C9CCD2', 'glass': '#DCEAF0', 'coffee_milk': '#B88A62',
             'milk': '#EADCC8', 'ice': '#F2FAFF', 'straw': '#4C8C5C', 'phone': '#E8E2DA', 'wallpaper_a': '#F2B58A',
             'wallpaper_b': '#7A9AC8', 'case': '#F7F7F4', 'gloss': '#FFFFFF', 'bokeh': '#FFE0A6'},
    'gaming': {'wall_top': '#1C1C34', 'wall_low': '#0D0E1A', 'table': '#25262F', 'table_edge': '#16171E', 'grain': '#2C2D37',
               'monitor': '#1E1F26', 'game_sky_a': '#2C1D52', 'game_sky_b': '#F07A62', 'game_hill': '#3A2A5E',
               'game_near': '#1A1430', 'hud': '#7CF2E0', 'hp': '#FF4A6A', 'keyboard': '#1B1C23', 'pad': '#121318',
               'mouse': '#22232A', 'headset': '#2B2C34', 'can': '#1E8A5A', 'can_label': '#E6F04A',
               'can_top': '#C9CCD2', 'gloss': '#E8E8FF', 'screen_spill': '#8C7CFF'},
    'kitchen': {'wall_top': '#3E4A52', 'wall_low': '#2A3036', 'table': '#7E6A5A', 'table_edge': '#4E4038',
                'check': '#4E3E34', 'window_night': '#1A212C', 'window_haze': '#5A4A4A', 'block': '#262C38',
                'block_far': '#353C4A', 'block_lit': '#FFB566', 'block_cool': '#9DB4D6', 'lamp_pool': '#FF9A40',
                'frame': '#D8D6CE', 'sill': '#BDB9AF', 'glass': '#C8D4DA', 'tea': '#6E3416', 'holder': '#B8A27A',
                'spoon': '#C9CCD2', 'player': '#2E3034', 'player_face': '#3C3F45', 'grille': '#16171A',
                'dial': '#FFB566', 'cassette': '#E8E4DA', 'label': '#C85A3A', 'reel': '#2A2A2E',
                'gloss': '#FFF2DC', 'steam': '#FFFFFF', 'snow': '#E8EDF4', 'lamp_light': '#FFC98A'},
}
LIGHTS = {'desk': [0.55, -0.65, 0.50],      # desk lamp on the right
          'cafe': [-0.60, -0.50, 0.45],     # afternoon window behind the left
          'gaming': [0.10, -0.55, 0.70],    # soft overhead and screen light from the front
          'kitchen': [0.45, -0.70, 0.50]}   # one warm bulb above the right; the window adds no light at night
RGB_PHASE = 0.62                            # start hue of the RGB gradients (violet -> cyan -> green ...)
CHECK = 0.42                                # oilcloth square size (table units)
WINDOW_LIT, WINDOW_COOL = 0.24, 0.07        # share of lit warm and lit cool windows in the blocks outside


def build_modern(set_name, spec, frame, w, h, rng, fb, view_pieces, pitch):
    if set_name not in SETS:
        raise ValueError(f"unknown still-life set '{set_name}' (use classic, {', '.join(SETS)})")
    over = spec.get('scene', {}).get('palette') or {}
    pal = {k: hex_rgb(v) for k, v in {**PALETTES[set_name], **over}.items()}
    view = P.View(frame, pitch)
    lw = max(frame.unit * 0.012, 1.2) * spec['line']['weight']
    light = LIGHTS[set_name]
    reach = np.array([-np.sign(light[0]) * 0.75, 0.0, -0.45])     # shadows fall away from the light
    ctx = dict(view=view, frame=frame, w=w, h=h, pal=pal, lw=lw, rng=rng, fb=fb, view_pieces=view_pieces,
               reach=reach)
    out = {'desk': _desk, 'cafe': _cafe, 'gaming': _gaming, 'kitchen': _kitchen}[set_name](ctx)
    return out, light


def _z(view, p):
    return 5 + view.depth(p)


def _shadow(c, name, pts, opacity=0.8):
    return P.cast_shadow(name, c['view'], pts, c['reach'], c['frame'].px(0.06), ('table',), opacity)


def _mannequin(c, name, group, pieces, color, gloss=None, z=None):
    res = c['fb'].build(name, group, z if z is not None else _z(c['view'], pieces[0].solids[0].a),
                        c['view_pieces'](pieces), color=color, line_color=line_color(color), gloss=gloss)
    return res.drawables if res is not None else []


# ---------------------------------------------------------------- rooms

def _room(c, wall_light=None, grain=True, texture=True):
    view, w, h, pal, frame = c['view'], c['w'], c['h'], c['pal'], c['frame']
    back = view.px([(-6, 0, TABLE_BACK)])[0][1]
    front = view.px([(-6, 0, TABLE_FRONT)])[0][1]
    out = [Drawable('wall', 'bg', -100, fill=[np.array([[0, 0], [w, 0], [w, back + 2], [0, back + 2]], float)],
                    gradient=(pal['wall_top'], pal['wall_low'], (0, 0), (0, back)), casts=False, receives=True)]
    if wall_light is not None:
        cx, cy, color, opacity = wall_light
        out.append(P.glow('wall_light', (cx * w, cy * h), w * 0.45, h * 0.40, color, opacity, -99, w * 0.2))
    top = np.array([[0, back], [w, back], [w, front], [0, front]], float)
    out.append(Drawable('table', 'wood' if grain else 'marble', -60, fill=[top],
                        gradient=(darken(pal['table'], 0.78), pal['table'], (0, back), (0, front)),
                        normal_map=P.flat_normals(top, view.normal((0.0, -1.0, 0.0))), casts=False, receives=True))
    rng = c['rng']
    strokes = []
    for _ in range((26 if grain else 9) if texture else 0):
        z = TABLE_BACK + (TABLE_FRONT - TABLE_BACK) * rng.uniform(0, 1)
        if grain:
            pts = [(rng.uniform(-6, 2), 0, z), (rng.uniform(2, 6), 0, z + rng.uniform(-0.05, 0.05))]
        else:                                                       # marble veins wander diagonally
            x = rng.uniform(-4, 4)
            pts = [(x + k * 0.5 + rng.uniform(-0.2, 0.2), 0, z + k * 0.25 * rng.choice([-1, 1])) for k in range(5)]
        p = geom.resample(geom.catmull_rom(view.px(pts)), 24)
        strokes.append(geom.stroke_polygon(p, max(frame.px(0.007), 0.8) * geom.taper(24, 0.3, 0.3)))
    if strokes:
        out.append(Drawable('grain', 'wood' if grain else 'marble', -59.9, fill=strokes, fill_mode='union',
                            color=pal['grain'] if grain else pal['vein'], opacity=0.5, clip=['table'],
                            casts=False, receives=False))
    edge = np.array([[0, front], [w, front], [w, front + frame.px(0.30)], [0, front + frame.px(0.30)]], float)
    out.append(Drawable('table_edge', 'wood', -59, fill=[edge], color=pal['table_edge'], casts=False, receives=False,
                        strokes=[geom.stroke_polygon(np.array([[0, front], [w, front]]), frame.px(0.010))],
                        line_color=darken(pal['table_edge'], 0.6)))
    under = np.array([[0, front + frame.px(0.30)], [w, front + frame.px(0.30)], [w, h], [0, h]], float)
    out.append(Drawable('under', 'bg', -58.9, fill=[under], color=darken(pal['wall_low'], 0.6), casts=False,
                        receives=False))
    return out


# ---------------------------------------------------------------- shared props

def _handle(c, name, group, z, cx, cy, cz, r, color, side=1):
    """Cup handle: a thick arc on the side of the cup, drawn behind the body so its roots tuck in."""
    a = np.linspace(-1.2, 1.2, 16)
    pts = [(cx + side * (r * 0.55 + 0.13 * np.cos(t)), cy + 0.15 * np.sin(t), cz) for t in a]
    path = c['view'].px(pts)
    poly = geom.stroke_polygon(path, c['frame'].px(0.055) * np.ones(len(path)))
    return [Drawable(name, group, z - 0.01, fill=[poly], fill_mode='union', color=color, form_radius=c['frame'].px(0.03),
                     strokes=[geom.stroke_polygon(np.vstack([poly, poly[:1]]), c['lw'] * 0.8)], line_color=line_color(color))]


def _steam(c, name, x, y, z):
    view = c['view']
    out = []
    for k in range(2):
        pts = [(x + 0.06 * k + 0.07 * np.sin(t * 2.2 + k), y - t * 0.55, z) for t in np.linspace(0, 1, 8)]
        path = geom.resample(geom.catmull_rom(view.px(pts)), 24)
        out.append(Drawable(f'{name}_{k}', 'emissive', 40, fill=[geom.stroke_polygon(path, c['frame'].px(0.035) * geom.taper(24, 0.4, 0.6))],
                            fill_mode='union', color=c['pal'].get('steam', np.ones(3)), opacity=0.22,
                            feather=c['frame'].px(0.02), casts=False, receives=False))
    return out


def _phone(c, name, cx, cz, yaw, body, wall_a, wall_b, z_extra=0.0):
    view, lw = c['view'], c['lw']
    verts, u, v = P.table_box(cx, cz, 0.44, 0.04, 0.88, yaw)
    z = _z(view, (cx, 0, cz)) + z_extra
    out = P.solid(name, 'device', z, view, verts, P.BOX_FACES, body, lw)
    top = [verts[i] for i in P.BOX_FACES[P.TOP]]
    scr = P.inset(view, top, 0.06, 0.94, 0.04, 0.96)
    out.append(Drawable(f'{name}_screen', 'screen', z + 0.01, fill=[scr],
                        gradient=(wall_a, wall_b, tuple(scr[0]), tuple(scr[2])), casts=False, receives=False))
    clock = P.inset(view, top, 0.30, 0.70, 0.16, 0.22)
    card = P.inset(view, top, 0.12, 0.88, 0.40, 0.52)
    out.append(Drawable(f'{name}_ui', 'screen', z + 0.02, fill=[clock, card], fill_mode='each',
                        color=np.ones(3, np.float32), opacity=0.75, casts=False, receives=False))
    out.append(_shadow(c, name, verts))
    return out


# ---------------------------------------------------------------- desk at work

def _desk(c):
    view, pal, frame = c['view'], c['pal'], c['frame']
    lamp_head = np.array([1.12, -1.95, -0.95])
    lamp_mouth = np.array([0.80, -1.50, -0.72])
    pool = view.px([(0.55, 0, -0.35)])[0]
    out = _room(c, wall_light=(0.72, 0.30, pal['lamp_light'], 0.28))
    out.append(P.glow('lamp_pool', pool, frame.px(2.4), frame.px(1.0), pal['lamp_light'], 0.22, -58.5))
    out += _laptop(c, -0.30, -0.40, 0.16)
    out += _mug(c, 1.05, -0.45)
    out += _phone(c, 'phone', 0.85, 0.80, -0.38, pal['phone'], pal['wallpaper_a'], pal['wallpaper_b'])
    out += _lamp(c, (2.15, -1.05), lamp_head, lamp_mouth)
    out += _plant(c, -2.30, -1.15)
    out += _notebook(c, -1.95, 0.75)
    return out


def _laptop(c, cx, cz, yaw):
    view, pal, lw, rng = c['view'], c['pal'], c['lw'], c['rng']
    W, D, T, H, TILT = 1.9, 1.25, 0.07, 1.22, 0.24
    base, u, v = P.table_box(cx, cz, W, T, D, yaw)
    z = _z(view, (cx, 0, cz))
    out = P.solid('laptop_base', 'device', z, view, base, P.BOX_FACES, pal['laptop'], lw)
    top = [base[i] for i in P.BOX_FACES[P.TOP]]
    keys = []
    for row in range(5):
        for col in range(13):
            s0, t0 = 0.07 + col * 0.0662, 0.10 + row * 0.085
            keys.append(P.inset(view, top, s0, s0 + 0.055, t0, t0 + 0.068))
    out.append(Drawable('laptop_keys', 'device', z + 0.01, fill=keys, fill_mode='each', color=pal['laptop_key'],
                        normal_map=P.flat_normals(np.vstack(keys), view.normal((0, -1, 0))), casts=False, receives=False))
    pad = P.inset(view, top, 0.36, 0.64, 0.62, 0.92)
    out.append(Drawable('laptop_pad', 'device', z + 0.011, fill=[pad], color=darken(pal['laptop'], 0.92),
                        normal_map=P.flat_normals(pad, view.normal((0, -1, 0))),
                        strokes=[geom.stroke_polygon(np.vstack([pad, pad[:1]]), lw * 0.5)],
                        line_color=line_color(pal['laptop']), casts=False, receives=False))
    hinge = base[4]                                                     # back-left corner on the top face
    up = np.array([0.0, -np.cos(TILT), 0.0]) - v * np.sin(TILT)
    lid = P.box_verts(hinge - v * 0.05, u * W, up * H, v * 0.05)
    zl = z - 0.05
    out += P.solid('laptop_lid', 'device', zl, view, lid, P.BOX_FACES, pal['laptop'], lw)
    face = [lid[i] for i in (3, 2, 6, 7)]               # display side: bottom-left, bottom-right, top-right, top-left
    face = [face[0], face[1], face[2], face[3]]
    scr = P.inset(view, [face[0], face[1], None, face[3]], 0.04, 0.96, 0.05, 0.94)
    out.append(Drawable('laptop_screen', 'screen', zl + 0.01, fill=[scr], color=pal['editor'], casts=False, receives=False))
    side = P.inset(view, [face[0], face[1], None, face[3]], 0.04, 0.20, 0.05, 0.94)
    out.append(Drawable('laptop_sidebar', 'screen', zl + 0.011, fill=[side], color=lighten(pal['editor'], 0.06),
                        casts=False, receives=False))
    code_colors = [hex_rgb(x) for x in ('#7FB8F0', '#E6C07A', '#C792EA', '#8BD49C', '#F07A7A', '#A0A8C0')]
    lines = {k: [] for k in range(len(code_colors))}
    indent = 0
    for row in range(14):
        t = 0.88 - row * 0.058
        indent = int(np.clip(indent + rng.integers(-1, 2), 0, 3))
        s = 0.24 + indent * 0.04
        for _ in range(rng.integers(1, 4)):
            ln = rng.uniform(0.06, 0.20)
            if s + ln > 0.93:
                break
            lines[int(rng.integers(0, len(code_colors)))].append(
                P.inset(view, [face[0], face[1], None, face[3]], s, s + ln, t - 0.022, t))
            s += ln + 0.02
    for k, polys in lines.items():
        if polys:
            out.append(Drawable(f'code_{k}', 'screen', zl + 0.012, fill=polys, fill_mode='each', color=code_colors[k],
                                opacity=0.9, casts=False, receives=False))
    spill = view.px([(cx, -0.08, cz + 0.15)])[0]
    out.append(P.glow('laptop_spill', spill, c['frame'].px(1.1), c['frame'].px(0.45), hex_rgb('#9FB6FF'), 0.12, z + 0.02))
    out.append(_shadow(c, 'laptop', np.vstack([base, lid])))
    return out


def _mug(c, cx, cz):
    view, pal, lw = c['view'], c['pal'], c['lw']
    z = _z(view, (cx, 0, cz))
    r0, r1, hgt = 0.24, 0.26, 0.58
    out = P.cylinder('mug', 'ceramic', z, view, cx, cz, 0.0, hgt, r0, r1, pal['mug'], lw, rim=0.035,
                     liquid=(pal['coffee'], 0.07))
    out += _handle(c, 'mug_handle', 'ceramic', z, cx + r1 * 0.9, -hgt * 0.52, cz, r1, pal['mug'], side=-1)
    out += _steam(c, 'mug_steam', cx - 0.05, -hgt - 0.08, cz)
    out.append(_shadow(c, 'mug', P.cylinder_points(cx, cz, 0, hgt, r0, r1)))
    return out


def _lamp(c, base_xz, head, mouth):
    view, pal, lw, frame = c['view'], c['pal'], c['lw'], c['frame']
    bx, bz = base_xz
    z = _z(view, (bx, 0, bz))
    out = P.cylinder('lamp_base', 'metal', z, view, bx, bz, 0.0, 0.07, 0.34, 0.32, pal['lamp'], lw)
    elbow = np.array([bx - 0.25, -1.40, bz - 0.25])
    arm = M.Piece('lamp_arm', M.chain([(bx, -0.07, bz), elbow, head], [0.045, 0.04, 0.04]), k=0.02)
    out += _mannequin(c, 'lamp_arm', 'metal', [arm], pal['lamp'], gloss=(pal['gloss'], 40, 0.6), z=z + 0.01)
    hull, opening = P.frustum_hull(view, head, 0.10, mouth, 0.33)
    out.append(Drawable('lamp_shade', 'metal', z + 0.02, fill=[hull], color=pal['lamp'], form_radius=frame.px(0.18),
                        strokes=[geom.stroke_polygon(np.vstack([hull, hull[:1]]), lw)], line_color=line_color(pal['lamp'])))
    out.append(Drawable('lamp_bulb', 'emissive', z + 0.03, fill=[opening], color=lighten(pal['lamp_light'], 0.5),
                        casts=False, receives=False))
    cen = opening.mean(axis=0)
    out.append(P.glow('lamp_halo', cen, frame.px(0.55), frame.px(0.45), pal['lamp_light'], 0.45, z + 0.031))
    out.append(_shadow(c, 'lamp', np.vstack([P.cylinder_points(bx, bz, 0, 0.07, 0.34, 0.32), [elbow, head]]), 0.6))
    return out


def _plant(c, cx, cz):
    view, pal, lw, rng, frame = c['view'], c['pal'], c['lw'], c['rng'], c['frame']
    z = _z(view, (cx, 0, cz))
    out = P.cylinder('pot', 'ceramic', z, view, cx, cz, 0.0, 0.50, 0.25, 0.31, pal['pot'], lw)
    out += P.cylinder('pot_rim', 'ceramic', z + 0.004, view, cx, cz, -0.48, 0.09, 0.335, 0.34, lighten(pal['pot'], 0.08), lw,
                      rim=0.04, liquid=(pal['soil'], 0.04))
    for k in range(7):
        a = rng.uniform(-0.55, 0.55)
        x0 = cx + rng.uniform(-0.15, 0.15)
        zz = cz + rng.uniform(-0.12, 0.15)
        tall = rng.uniform(1.0, 1.6)
        pts = [(x0, -0.55, zz), (x0 + a * 0.2 * tall, -0.55 - tall * 0.5, zz), (x0 + a * 0.55 * tall, -0.55 - tall, zz)]
        path = geom.resample(geom.catmull_rom(view.px(pts)), 30)
        wid = frame.px(0.11) * geom.taper(30, 0.0, 1.0, 0.0, 0.7)
        leaf = geom.stroke_polygon(path, wid)
        zk = z + 0.01 + (zz - cz) * 0.05
        out.append(Drawable(f'leaf_{k}', 'foliage', zk, fill=[leaf], fill_mode='union', color=mix(pal['leaf'], pal['leaf_edge'], rng.uniform(0, 0.15)),
                            form_radius=frame.px(0.05), strokes=[geom.stroke_polygon(np.vstack([leaf, leaf[:1]]), lw * 0.6)],
                            line_color=pal['leaf_edge']))
    out.append(_shadow(c, 'plant', P.cylinder_points(cx, cz, 0, 1.6, 0.25, 0.4), 0.6))
    return out


def _notebook(c, cx, cz):
    view, pal, lw = c['view'], c['pal'], c['lw']
    verts, u, v = P.table_box(cx, cz, 1.05, 0.07, 1.35, 0.12)
    z = _z(view, (cx, 0, cz))
    sides = {P.RIGHT: pal['pages'], P.FRONT: pal['pages'], P.BACK: pal['pages'], P.LEFT: darken(pal['cover'], 0.8)}
    out = P.solid('notebook', 'paper', z, view, verts, P.BOX_FACES, pal['cover'], lw, face_colors=sides)
    top = [verts[i] for i in P.BOX_FACES[P.TOP]]
    band = P.inset(view, top, 0.82, 0.88, 0.0, 1.0)
    out.append(Drawable('notebook_band', 'paper', z + 0.01, fill=[band], color=darken(pal['cover'], 0.6),
                        normal_map=P.flat_normals(band, view.normal((0, -1, 0))), casts=False, receives=False))
    a = P.face_point(top, 0.15, 0.20) + np.array([0, -0.03, 0])
    b = P.face_point(top, 0.70, 0.85) + np.array([0, -0.03, 0])
    pen = M.Piece('pen', [M.cone(a, b, 0.035, 0.035), M.cone(b, b + (b - a) * 0.08, 0.03, 0.008)], k=0.01)
    out += _mannequin(c, 'pen', 'metal', [pen], pal['pen'], gloss=(pal['gloss'], 50, 0.8), z=z + 0.02)
    out.append(_shadow(c, 'notebook', verts, 0.7))
    return out


# ---------------------------------------------------------------- cafe table

def _cafe(c):
    pal = c['pal']
    out = _room(c, wall_light=None, grain=False)
    out += _cafe_window(c)
    out += _latte(c, -0.60, 0.35)
    out += _cake(c, 0.95, 0.35)
    out += _iced(c, -1.85, -0.75)
    out += _phone(c, 'phone', 2.00, 1.05, 0.42, pal['phone'], pal['wallpaper_a'], pal['wallpaper_b'])
    case = M.Piece('earbuds', [M.cone((0.05, -0.12, 1.05), (0.42, -0.12, 1.12), 0.12, 0.12)], k=0.02)
    out += _mannequin(c, 'earbuds', 'device', [case], pal['case'], gloss=(pal['gloss'], 40, 0.9))
    out.append(_shadow(c, 'earbuds', [(0.05, -0.24, 1.05), (0.42, -0.24, 1.12), (0.05, 0, 1.05), (0.42, 0, 1.12)], 0.6))
    return out


def _cafe_window(c):
    """Big cafe window on the wall: bright panes, mullions and out-of-focus street lights (bokeh)."""
    view, pal, w, h, rng = c['view'], c['pal'], c['w'], c['h'], c['rng']
    back = view.px([(0, 0, TABLE_BACK)])[0][1]
    x0, x1, y0, y1 = 0.06 * w, 0.94 * w, 0.04 * h, back - 0.03 * h
    pane = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)
    out = [Drawable('window', 'bg', -99.5, fill=[pane], gradient=(pal['window'], mix(pal['window'], pal['wall_low'], 0.25),
                                                                   (0, y0), (0, y1)), casts=False, receives=True)]
    dots = []
    for k in range(26):
        r = rng.uniform(0.012, 0.035) * w
        cx, cy = rng.uniform(x0, x1), rng.uniform(y0 + 0.2 * (y1 - y0), y1)
        col = mix(pal['bokeh'], hex_rgb('#FFFFFF'), rng.uniform(0, 0.5))
        dots.append(Drawable(f'bokeh_{k}', 'emissive', -99.4, fill=[geom.ellipse(cx, cy, r, r, 32)], color=col,
                             opacity=rng.uniform(0.25, 0.55), feather=r * 0.25, clip=['window'], casts=False, receives=False))
    out += dots
    bars = [geom.stroke_polygon(np.array([[x, y0], [x, y1]]), 0.012 * w) for x in np.linspace(x0, x1, 4)]
    bars += [geom.stroke_polygon(np.array([[x0, y], [x1, y]]), 0.012 * w) for y in (y0, (y0 + y1) * 0.45, y1)]
    out.append(Drawable('mullions', 'bg', -99.3, fill=bars, fill_mode='union', color=pal['frame'], casts=False, receives=False))
    return out


def _latte(c, cx, cz):
    view, pal, lw = c['view'], c['pal'], c['lw']
    z = _z(view, (cx, 0, cz))
    out = P.disc('saucer', 'ceramic', z, view, cx, cz, 0.0, 0.50, 0.04, pal['cup'], lw, well=0.62)
    r0, r1, hgt = 0.19, 0.30, 0.40
    out += P.cylinder('cup', 'ceramic', z + 0.01, view, cx, cz, -0.04, hgt, r0, r1, pal['cup'], lw, rim=0.025,
                      liquid=(pal['latte'], 0.05))
    surf_y = -0.04 - hgt + 0.05
    heart = []                                          # latte art: stacked hearts shrinking toward the cup's back
    for k, (dz, s) in enumerate(((0.06, 0.15), (-0.03, 0.11), (-0.10, 0.07))):
        a = np.linspace(0, 2 * np.pi, 40, endpoint=False)
        hx = 16 * np.sin(a) ** 3 / 16
        hz = -(13 * np.cos(a) - 5 * np.cos(2 * a) - 2 * np.cos(3 * a) - np.cos(4 * a)) / 16
        heart.append(view.px(np.stack([cx + hx * s, np.full(40, surf_y - 0.001), cz + dz - hz * s], axis=1)))
    out.append(Drawable('latte_art', 'liquid', z + 0.02, fill=heart, fill_mode='each', color=pal['foam'],
                        clip=['cup_liquid'], feather=0.8, casts=False, receives=False))
    out += _handle(c, 'cup_handle', 'ceramic', z + 0.01, cx + r1 * 0.85, -0.04 - hgt * 0.55, cz, r1, pal['cup'], side=1)
    out.append(_shadow(c, 'latte', P.cylinder_points(cx, cz, 0, hgt + 0.04, 0.50, r1), 0.7))
    return out


def _cake(c, cx, cz):
    view, pal, lw = c['view'], c['pal'], c['lw']
    z = _z(view, (cx, 0, cz))
    out = P.disc('plate', 'ceramic', z, view, cx, cz, 0.0, 0.62, 0.035, pal['plate'], lw, well=0.72)
    base_y, hgt = -0.035, 0.40
    tri = [np.array([cx - 0.35, base_y, cz + 0.30]), np.array([cx + 0.05, base_y, cz - 0.40]),
           np.array([cx + 0.40, base_y, cz - 0.05])]
    verts = tri + [p + np.array([0, -hgt, 0]) for p in tri]
    faces = [[0, 1, 2], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]]
    colors = {1: pal['frosting'], 2: pal['sponge'], 4: pal['sponge'], 3: pal['frosting']}
    zc = z + 0.02
    out += P.solid('cake', 'food', zc, view, verts, faces, pal['sponge'], lw, face_colors=colors)
    for fi, (a, b) in ((2, (0, 1)), (4, (2, 0))):           # cream layers on the cut faces
        for frac in (0.36, 0.68):
            p = [verts[a] + np.array([0, -hgt * frac, 0]), verts[b] + np.array([0, -hgt * frac, 0]),
                 verts[b] + np.array([0, -hgt * (frac + 0.07), 0]), verts[a] + np.array([0, -hgt * (frac + 0.07), 0])]
            out.append(Drawable(f'cream_{fi}_{frac}', 'food', zc + 0.01, fill=[view.px(p)], color=pal['cream'],
                                clip=[f'cake_f{fi}'], casts=False, receives=False))
    top_c = np.mean(verts[3:], axis=0)
    berry = M.Piece('berry', [M.sphere(top_c + np.array([0.02, -0.10, 0.0]), 0.11),
                              M.sphere(top_c + np.array([0.02, -0.03, 0.0]), 0.12)], k=0.06)
    out += _mannequin(c, 'berry', 'fruit', [berry], pal['berry'], gloss=(pal['gloss'], 30, 0.8), z=zc + 0.02)
    fork = view.px([(cx + 0.55, -0.045, cz + 0.35), (cx + 0.02, -0.045, cz + 0.62)])
    tines = [view.px([(cx + 0.02 + dx, -0.045, cz + 0.62 + dx * 0.4), (cx - 0.16 + dx, -0.045, cz + 0.70 + dx * 0.4)])
             for dx in (-0.03, 0.0, 0.03)]
    polys = [geom.stroke_polygon(fork, c['frame'].px(0.05) * np.ones(2))] + \
            [geom.stroke_polygon(t, c['frame'].px(0.016) * np.ones(2)) for t in tines]
    out.append(Drawable('fork', 'metal', zc + 0.03, fill=polys, fill_mode='union', color=pal['fork'],
                        form_radius=c['frame'].px(0.02), strokes=[geom.stroke_polygon(np.vstack([p, p[:1]]), lw * 0.5) for p in polys],
                        line_color=line_color(pal['fork'])))
    out.append(_shadow(c, 'cake', np.vstack([P.cylinder_points(cx, cz, 0, 0.04, 0.62, 0.62), verts]), 0.7))
    return out


def _iced(c, cx, cz):
    view, pal, lw, frame, rng = c['view'], c['pal'], c['lw'], c['frame'], c['rng']
    z = _z(view, (cx, 0, cz))
    r0, r1, hgt = 0.24, 0.29, 1.10
    level = 0.86
    out = P.cylinder('drink', 'liquid', z, view, cx, cz, -0.02, hgt * level, r0 * 0.94, r0 + (r1 - r0) * level - 0.02,
                     pal['coffee_milk'], lw * 0.0)
    out[0].gradient = (pal['coffee_milk'], pal['milk'], tuple(view.px([(cx, -0.02, cz)])[0]),
                       tuple(view.px([(cx, -hgt * level, cz)])[0]))
    out[0].strokes = []
    out[1].color = pal['milk']
    for k in range(3):
        ix, iz = cx + rng.uniform(-0.12, 0.12), cz + rng.uniform(-0.10, 0.10)
        ice, _, _ = P.table_box(ix, iz, 0.17, 0.15, 0.17, rng.uniform(0, 1.5), base_y=-hgt * level + 0.06)
        out += P.solid(f'ice_{k}', 'glass', z + 0.01 + k * 0.001, view, ice, P.BOX_FACES, pal['ice'], lw * 0.6, opacity=0.8)
    straw = view.px([(cx + 0.05, -hgt * 0.5, cz), (cx + 0.18, -hgt - 0.35, cz + 0.05)])
    out.append(Drawable('straw', 'device', z + 0.02, fill=[geom.stroke_polygon(straw, frame.px(0.06) * np.ones(2))],
                        fill_mode='union', color=pal['straw'], form_radius=frame.px(0.03),
                        strokes=[geom.stroke_polygon(straw, frame.px(0.075) * np.ones(2))], line_color=line_color(pal['straw'])))
    glass = P.cylinder('glass', 'glass', z + 0.03, view, cx, cz, 0.0, hgt, r0, r1, pal['glass'], lw, opacity=0.28)
    out.append(glass[0])                                    # the side only: an open glass has no lid
    rim = view.px([(cx + r1 * np.cos(t), -hgt, cz + r1 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 49)])
    out.append(Drawable('glass_rim', 'glass', z + 0.031, fill=None, strokes=[geom.stroke_polygon(rim, lw * 0.8)],
                        line_color=line_color(pal['glass'])))
    for k, s in enumerate((-0.62, -0.45)):                  # vertical highlights on the glass
        p = view.px([(cx + s * r1, -0.12, cz + 0.2), (cx + s * r1, -hgt + 0.08, cz + 0.2)])
        out.append(Drawable(f'glass_hl_{k}', 'emissive', z + 0.04, fill=[geom.stroke_polygon(p, frame.px(0.035 - k * 0.015) * np.ones(2))],
                            fill_mode='union', color=np.ones(3, np.float32), opacity=0.6, casts=False, receives=False))
    out.append(_shadow(c, 'iced', P.cylinder_points(cx, cz, 0, hgt, r0, r1), 0.45))
    return out


# ---------------------------------------------------------------- gaming setup

def _gaming(c):
    view, frame, w, h = c['view'], c['frame'], c['w'], c['h']
    out = _room(c, wall_light=None)
    back = view.px([(0, 0, TABLE_BACK)])[0][1]
    for k in range(12):                                    # RGB strip glow on the wall behind the desk
        x = (k + 0.5) / 12 * w
        out.append(P.glow(f'wall_rgb_{k}', (x, back - 0.10 * h), w / 12 * 1.3, 0.16 * h, P.hsv(RGB_PHASE + k / 12), 0.22, -99))
    strip = [view.px([(-6 + k, 0.0, TABLE_BACK), (-5 + k, 0.0, TABLE_BACK)]) for k in range(12)]
    for k, s in enumerate(strip):
        out.append(Drawable(f'desk_led_{k}', 'emissive', -59.5, fill=[geom.stroke_polygon(s, frame.px(0.04) * np.ones(2))],
                            fill_mode='union', color=P.hsv(RGB_PHASE + k / 12, 0.6), opacity=0.9, feather=frame.px(0.02),
                            casts=False, receives=False))
    out += _pad(c, 0.25, 0.55)
    out += _monitor(c, 0.0, -1.25)
    out += _keyboard(c, -0.35, 0.45)
    out += _mouse(c, 1.55, 0.55)
    out += _headset(c, -2.05, -0.90)
    out += _can(c, 2.25, -0.55)
    return out


def _pad(c, cx, cz):
    view, pal, lw, frame = c['view'], c['pal'], c['lw'], c['frame']
    verts, u, v = P.table_box(cx, cz, 4.2, 0.02, 1.65, 0.0)
    out = P.solid('pad', 'cloth', -58, view, verts, P.BOX_FACES, pal['pad'], lw * 0.6)
    top = [verts[i] for i in P.BOX_FACES[P.TOP]]
    edge = [P.face_point(top, s, t) for s, t in ((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))]
    for k in range(4):
        a, b = edge[k], edge[k + 1]
        for j in range(6):
            p = view.px([a + (b - a) * j / 6, a + (b - a) * (j + 1) / 6])
            out.append(Drawable(f'pad_led_{k}_{j}', 'emissive', -57.9, fill=[geom.stroke_polygon(p, frame.px(0.025) * np.ones(2))],
                                fill_mode='union', color=P.hsv(RGB_PHASE + (k * 6 + j) / 24), feather=frame.px(0.01),
                                casts=False, receives=False))
    return out


def _monitor(c, cx, cz):
    view, pal, lw, frame, rng = c['view'], c['pal'], c['lw'], c['frame'], c['rng']
    z = _z(view, (cx, 0, cz))
    base, _, _ = P.table_box(cx, cz + 0.15, 1.0, 0.04, 0.60, 0.0)
    neck, _, _ = P.table_box(cx, cz - 0.05, 0.14, 0.95, 0.08, 0.0, base_y=-0.04)
    W, H, T = 3.0, 1.65, 0.10
    scr, u, v = P.table_box(cx, cz - 0.12, W, H, T, 0.0, base_y=-0.62)
    out = P.solid('mon_base', 'device', z, view, base, P.BOX_FACES, pal['monitor'], lw)
    out += P.solid('mon_neck', 'device', z - 0.01, view, neck, P.BOX_FACES, pal['monitor'], lw)
    out += P.solid('monitor', 'device', z - 0.005, view, scr, P.BOX_FACES, pal['monitor'], lw)
    front = [scr[i] for i in (3, 2, 6, 7)]              # bottom-left, bottom-right, top-right, top-left of the display
    quad = [front[0], front[1], None, front[3]]
    zs = z
    disp = P.inset(view, quad, 0.015, 0.985, 0.03, 0.985)
    out.append(Drawable('display', 'screen', zs, fill=[disp], color=pal['game_sky_a'], casts=False, receives=False))
    sky = P.inset(view, quad, 0.015, 0.985, 0.30, 0.985)
    out.append(Drawable('game_sky', 'screen', zs + 0.001, fill=[sky], gradient=(pal['game_sky_a'], pal['game_sky_b'],
                        tuple(sky[3]), tuple(sky[0])), clip=['display'], casts=False, receives=False))
    sun_c = P.inset(view, quad, 0.62, 0.62, 0.42, 0.42)[0]
    out.append(P.glow('game_sun', sun_c, frame.px(0.16), frame.px(0.16), hex_rgb('#FFE6B0'), 0.95, zs + 0.002, frame.px(0.03)))
    for k, (base_t, amp, col) in enumerate(((0.42, 0.20, pal['game_hill']), (0.22, 0.16, pal['game_near']))):
        xs = np.linspace(0.015, 0.985, 40)
        ts = base_t + amp * (0.5 + 0.5 * np.sin(xs * (7 + 5 * k) + k * 1.3)) * rng.uniform(0.7, 1.0, 40)
        ridge = [P.face_point(quad, s, t) for s, t in zip(xs, ts)]
        ridge += [P.face_point(quad, 0.985, 0.03), P.face_point(quad, 0.015, 0.03)]
        out.append(Drawable(f'game_ridge_{k}', 'screen', zs + 0.003 + k * 0.001, fill=[view.px(ridge)], color=col,
                            clip=['display'], casts=False, receives=False))
    hud = [P.inset(view, quad, 0.04, 0.26, 0.90, 0.94), P.inset(view, quad, 0.04, 0.18, 0.86, 0.885)]
    out.append(Drawable('hud_hp', 'screen', zs + 0.01, fill=[hud[0]], color=pal['hp'], casts=False, receives=False))
    out.append(Drawable('hud_mp', 'screen', zs + 0.01, fill=[hud[1]], color=pal['hud'], casts=False, receives=False))
    mm = P.inset(view, quad, 0.86, 0.96, 0.78, 0.94)
    cen = mm.mean(axis=0)
    rad = np.ptp(mm[:, 0]) / 2
    disc = geom.ellipse(cen[0], cen[1], rad, rad, 32)
    out.append(Drawable('hud_map', 'screen', zs + 0.01, fill=[disc], color=mix(pal['game_near'], pal['hud'], 0.25),
                        strokes=[geom.stroke_polygon(np.vstack([disc, disc[:1]]), lw * 0.8)],
                        line_color=pal['hud'], casts=False, receives=False))
    ch = P.inset(view, quad, 0.5, 0.5, 0.5, 0.5)[0]
    cross = [geom.stroke_polygon(np.array([[ch[0] - 9, ch[1]], [ch[0] - 3, ch[1]]]), 1.6),
             geom.stroke_polygon(np.array([[ch[0] + 3, ch[1]], [ch[0] + 9, ch[1]]]), 1.6),
             geom.stroke_polygon(np.array([[ch[0], ch[1] - 9], [ch[0], ch[1] - 3]]), 1.6)]
    out.append(Drawable('crosshair', 'screen', zs + 0.011, fill=cross, fill_mode='union', color=pal['hud'],
                        casts=False, receives=False))
    spill = view.px([(cx, 0, cz + 1.2)])[0]
    out.append(P.glow('screen_spill', spill, frame.px(2.8), frame.px(0.9), pal['screen_spill'], 0.16, -57.5))
    return out


def _keyboard(c, cx, cz):
    view, pal, lw = c['view'], c['pal'], c['lw']
    verts, u, v = P.table_box(cx, cz, 2.4, 0.09, 0.82, -0.05, base_y=-0.02)
    z = _z(view, (cx, 0, cz))
    out = P.solid('keyboard', 'device', z, view, verts, P.BOX_FACES, pal['keyboard'], lw)
    top = [verts[i] for i in P.BOX_FACES[P.TOP]]
    for col in range(16):
        keys = []
        for row in range(6):
            s0, t0 = 0.03 + col * 0.0590, 0.06 + row * 0.148
            if row == 5 and 4 <= col <= 10:
                if col == 4:
                    keys.append(P.inset(view, top, s0, 0.03 + 11 * 0.0590 - 0.008, t0, t0 + 0.12))
                continue
            keys.append(P.inset(view, top, s0, s0 + 0.051, t0, t0 + 0.12))
        out.append(Drawable(f'keys_{col}', 'screen', z + 0.01, fill=keys, fill_mode='each',
                            color=mix(P.hsv(RGB_PHASE + col / 20), pal['keyboard'], 0.35), casts=False, receives=False))
    glow_c = view.px([(cx, 0, cz)])[0]
    out.append(P.glow('kb_underglow', glow_c, c['frame'].px(1.5), c['frame'].px(0.55), P.hsv(RGB_PHASE + 0.15), 0.25, -57.6))
    out.append(_shadow(c, 'keyboard', verts, 0.6))
    return out


def _mouse(c, cx, cz):
    pal = c['pal']
    body = M.Piece('mouse', [M.cone((cx, -0.10, cz - 0.22), (cx + 0.02, -0.12, cz + 0.16), 0.13, 0.17),
                             M.sphere((cx + 0.02, -0.09, cz + 0.20), 0.15)], k=0.08)
    out = _mannequin(c, 'mouse', 'device', [body], pal['mouse'], gloss=(pal['gloss'], 40, 0.7))
    stripe = c['view'].px([(cx - 0.05, -0.27, cz + 0.02), (cx + 0.06, -0.28, cz + 0.12)])
    out.append(Drawable('mouse_led', 'emissive', 9, fill=[geom.stroke_polygon(stripe, c['frame'].px(0.03) * np.ones(2))],
                        fill_mode='union', color=P.hsv(RGB_PHASE + 0.3), feather=c['frame'].px(0.01), casts=False, receives=False))
    out.append(_shadow(c, 'mouse', [(cx, -0.25, cz - 0.3), (cx, -0.25, cz + 0.32), (cx - 0.17, 0, cz), (cx + 0.19, 0, cz)], 0.6))
    return out


def _headset(c, cx, cz):
    view, pal, lw = c['view'], c['pal'], c['lw']
    z = _z(view, (cx, 0, cz))
    out = P.cylinder('stand_base', 'device', z, view, cx, cz, 0.0, 0.05, 0.36, 0.34, pal['headset'], lw)
    post, _, _ = P.table_box(cx, cz, 0.10, 1.50, 0.10, 0.0, base_y=-0.05)
    out += P.solid('stand_post', 'device', z + 0.001, view, post, P.BOX_FACES, pal['headset'], lw)
    top_y = -1.55
    arc = [(cx + 0.36 * np.sin(t), top_y + 0.36 * (1 - np.cos(t)), cz) for t in np.linspace(-1.4, 1.4, 17)]
    band = M.Piece('band', M.chain(arc, [0.05] * 17), k=0.01)
    cups = []
    for s, end in ((-1, arc[0]), (1, arc[-1])):
        a = np.array(end) + np.array([s * 0.05, 0.25, 0.0])
        cups.append(M.Piece(f'cup_{s}', [M.ellipse_cone(a - np.array([s * 0.05, 0, 0]), a + np.array([s * 0.05, 0, 0]),
                                                        0.21, 0.21, 0.21, 0.21, (0, 1, 0), (0, 1, 0))], k=0.02,
                            parent='band', attach_k=0.0, attach_n=0))      # one tree: FormBuilder draws from its root
        led = view.px([a + np.array([s * 0.08, 0.0, 0.08])])[0]
        out.append(P.glow(f'cup_led_{s}', led, c['frame'].px(0.05), c['frame'].px(0.12), P.hsv(RGB_PHASE + 0.5 + 0.1 * s),
                          0.9, z + 0.03, c['frame'].px(0.02)))
    out += _mannequin(c, 'headset', 'device', [band] + cups, pal['headset'], gloss=(pal['gloss'], 30, 0.5), z=z + 0.01)
    out.append(_shadow(c, 'headset', np.vstack([P.cylinder_points(cx, cz, 0, 1.9, 0.36, 0.5)]), 0.5))
    return out


def _can(c, cx, cz):
    view, pal, lw = c['view'], c['pal'], c['lw']
    z = _z(view, (cx, 0, cz))
    hgt, r = 0.62, 0.17
    out = P.cylinder('can', 'metal', z, view, cx, cz, 0.0, hgt, r * 0.92, r, pal['can'], lw, top_color=pal['can_top'])
    a = np.linspace(0, np.pi, 24)
    lo = [(cx + r * np.cos(t), -0.24, cz + r * np.sin(t)) for t in a]
    hi = [(cx + r * np.cos(t), -0.40, cz + r * np.sin(t)) for t in a[::-1]]
    out.append(Drawable('can_label', 'metal', z + 0.005, fill=[view.px(lo + hi)], color=pal['can_label'],
                        clip=['can_side'], casts=False, receives=False))
    out.append(_shadow(c, 'can', P.cylinder_points(cx, cz, 0, hgt, r, r), 0.7))
    return out


# ---------------------------------------------------------------- night kitchen

def _kitchen(c):
    pal, frame, view = c['pal'], c['frame'], c['view']
    out = _room(c, wall_light=(0.86, 0.20, pal['lamp_light'], 0.30), texture=False)
    out += _oilcloth(c)
    out += _kitchen_window(c)
    pool = view.px([(0.9, 0, 0.1)])[0]
    out.append(P.glow('bulb_pool', pool, frame.px(2.6), frame.px(1.1), pal['lamp_light'], 0.20, -58.5))
    out += _tea_glass(c, -0.95, 0.40)
    out += _cassette_player(c, 1.05, -0.70, -0.12)
    out += _cassette(c, 0.40, 1.20, 0.30)
    return out


def _oilcloth(c):
    """Checked oilcloth: every other square of a grid on the table plane, darker."""
    view, pal = c['view'], c['pal']
    squares = []
    for i, x in enumerate(np.arange(-6.0, 6.0, CHECK)):
        for j, z in enumerate(np.arange(TABLE_BACK, TABLE_FRONT + 0.4, CHECK)):
            if (i + j) % 2 == 0:
                squares.append(view.px([(x, 0, z), (x + CHECK, 0, z), (x + CHECK, 0, z + CHECK), (x, 0, z + CHECK)]))
    return [Drawable('oilcloth', 'wood', -59.9, fill=squares, fill_mode='each', color=pal['check'], opacity=0.45,
                     clip=['table'], casts=False, receives=False)]


def _face_disc(view, center, ex, ey, r, n=28):
    """Circle lying on a flat face (reel hubs, speaker rings): center plus r along the face axes."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return view.px(np.asarray(center) + r * (np.outer(np.cos(a), ex) + np.outer(np.sin(a), ey)))


def _kitchen_window(c):
    """Kitchen window at night: panel blocks with lit windows, a sodium glow below, snow, a white frame."""
    view, pal, w, h, rng = c['view'], c['pal'], c['w'], c['h'], c['rng']
    back = view.px([(0, 0, TABLE_BACK)])[0][1]
    x0, x1, y0, y1 = 0.05 * w, 0.58 * w, 0.05 * h, back - 0.045 * h
    pw, ph = x1 - x0, y1 - y0
    pane = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)
    out = [Drawable('window', 'bg', -99.5, fill=[pane], gradient=(pal['window_night'], pal['window_haze'], (0, y0), (0, y1)),
                    casts=False, receives=True)]
    blocks = ((-0.05, 0.50, 0.40, pal['block_far'], 0.034), (0.60, 1.05, 0.30, pal['block_far'], 0.034),
              (0.28, 0.98, 0.14, pal['block'], 0.052))
    for k, (s0, s1, top, col, cell) in enumerate(blocks):
        bx0, bx1, by0 = x0 + s0 * pw, x0 + s1 * pw, y0 + top * ph
        body = np.array([[bx0, by0], [bx1, by0], [bx1, y1], [bx0, y1]], float)
        out.append(Drawable(f'kblock_{k}', 'bg', -99.45 + k * 0.01, fill=[body], color=col, clip=['window'],
                            casts=False, receives=False))
        lit, cool, dark = [], [], []
        step = cell * w
        for yy in np.arange(by0 + step * 0.5, y1 - step * 0.3, step):
            for xx in np.arange(bx0 + step * 0.4, bx1 - step * 0.6, step):
                r = rng.random()
                win = np.array([[xx, yy], [xx + step * 0.55, yy], [xx + step * 0.55, yy + step * 0.5], [xx, yy + step * 0.5]])
                (lit if r < WINDOW_LIT else cool if r < WINDOW_LIT + WINDOW_COOL else dark).append(win)
        for tag, polys, color in (('dark', dark, darken(col, 0.7)), ('lit', lit, pal['block_lit']), ('cool', cool, pal['block_cool'])):
            if polys:
                out.append(Drawable(f'kblock_{k}_{tag}', 'emissive' if tag != 'dark' else 'bg', -99.445 + k * 0.01, fill=polys,
                                    fill_mode='each', color=color, opacity=0.9 if tag != 'dark' else 1.0, clip=['window'],
                                    casts=False, receives=False))
    glow = P.glow('street_glow', (x0 + 0.18 * pw, y1), pw * 0.45, ph * 0.22, pal['lamp_pool'], 0.35, -99.41)
    glow.clip = ['window']
    out.append(glow)
    for k, d in enumerate(C.snow(w, h, rng, pal)):                 # behind the frame, inside the pane
        d.z, d.clip = -99.3 + k * 0.01, ['window']
        out.append(d)
    t = 0.016 * w
    e = t * 0.8                                                     # casing half-width around the pane
    casing = np.array([[x0 - e, y0 - e], [x1 + e, y0 - e], [x1 + e, y1 + e], [x0 - e, y1 + e]])
    inner = np.array([[x0 + e, y0 + e], [x1 - e, y0 + e], [x1 - e, y1 - e], [x0 + e, y1 - e]])
    out.append(Drawable('window_casing', 'bg', -99.1, fill=[casing, inner], color=pal['frame'], casts=False, receives=False))
    rails = [geom.stroke_polygon(np.array([[x0 + pw * 0.5, y0], [x0 + pw * 0.5, y1]]), t),
             geom.stroke_polygon(np.array([[x0, y0 + ph * 0.30], [x1, y0 + ph * 0.30]]), t * 0.9),
             geom.stroke_polygon(np.array([[x0 + pw * 0.25, y0], [x0 + pw * 0.25, y0 + ph * 0.30]]), t * 0.7)]
    out.append(Drawable('window_frame', 'bg', -99.1, fill=rails, fill_mode='union', color=pal['frame'],
                        casts=False, receives=False))
    sill = np.array([[x0 - 0.03 * w, y1], [x1 + 0.03 * w, y1], [x1 + 0.03 * w, y1 + 0.02 * h], [x0 - 0.03 * w, y1 + 0.02 * h]])
    out.append(Drawable('window_sill', 'bg', -99.0, fill=[sill], color=pal['sill'], casts=False, receives=False,
                        strokes=[geom.stroke_polygon(np.vstack([sill, sill[:1]]), c['lw'] * 0.6)],
                        line_color=darken(pal['sill'], 0.6)))
    return out


def _tea_glass(c, cx, cz):
    """Tea glass in a metal holder: the holder hides the glass foot, the tea shows through the glass above."""
    view, pal, lw, frame = c['view'], c['pal'], c['lw'], c['frame']
    z = _z(view, (cx, 0, cz))
    hgt, r, hold, head = 0.70, 0.22, 0.42, 0.07           # head: empty glass above the tea
    rh = r * 1.10                                          # holder rim radius
    out = P.cylinder('tea_glass', 'glass', z, view, cx, cz, 0.0, hgt, r * 0.94, r, mix(pal['tea'], pal['glass'], 0.2), lw,
                     rim=0.015, liquid=(pal['tea'], head))
    front, back = np.linspace(0, np.pi, 24), np.linspace(np.pi, 2 * np.pi, 24)

    def ring(radius, y, a):
        return np.stack([cx + radius * np.cos(a), np.full(len(a), y), cz + radius * np.sin(a)], 1)

    empty = view.px(np.vstack([ring(r, -hgt, front), ring(r, -hgt + head, front[::-1])]))
    out.append(Drawable('tea_glass_empty', 'glass', z + 0.004, fill=[empty], color=pal['glass'], opacity=0.6,
                        clip=['tea_glass_side'], casts=False, receives=False))
    rim_back = view.px(np.vstack([ring(rh, -hold, back), ring(r, -hold, back[::-1])]))
    out.append(Drawable('holder_back', 'metal', z - 0.01, fill=[rim_back], color=darken(pal['holder'], 0.7),
                        casts=False, receives=False))
    out += [d for d in P.cylinder('holder', 'metal', z + 0.01, view, cx, cz, 0.0, hold, r * 1.02, rh, pal['holder'], lw)
            if not d.name.endswith('_top')]                 # open ring: the glass stands in it
    rr = r * 1.07
    lattice = [geom.stroke_polygon(view.px(ring(r * 1.03, y, front)), lw * 0.6) for y in (-0.07, -hold + 0.07)]
    for t0 in np.linspace(-0.3, np.pi, 10):
        for sgn in (1, -1):
            a = t0 + sgn * np.linspace(0, 0.45, 8)
            ys = np.linspace(-0.11, -hold + 0.11, 8)
            pts = np.stack([cx + rr * np.cos(a), ys, cz + rr * np.sin(a)], 1)
            lattice.append(geom.stroke_polygon(view.px(pts), lw * 0.45))
    out.append(Drawable('holder_filigree', 'metal', z + 0.012, fill=lattice, fill_mode='union', color=darken(pal['holder'], 0.55),
                        clip=['holder_side'], casts=False, receives=False))
    out += _handle(c, 'holder_handle', 'metal', z + 0.01, cx + r * 0.25, -hold * 0.5, cz, r, pal['holder'], side=1)
    for name, top_y, bottom_y, clip, alpha in (('tea_glass_shine', -hgt + 0.04, -hold - 0.03, 'tea_glass_side', 0.55),
                                                ('holder_shine', -hold + 0.03, -0.04, 'holder_side', 0.35)):
        shine = view.px([(cx + r * 0.55, bottom_y, cz + r * 0.8), (cx + r * 0.55, top_y, cz + r * 0.8)])
        out.append(Drawable(name, 'emissive', z + 0.015, fill=[geom.stroke_polygon(shine, frame.px(0.025) * np.ones(2))],
                            fill_mode='union', color=pal['gloss'], opacity=alpha, clip=[clip], casts=False, receives=False))
    a, b = np.array([cx + 0.06, -hgt + head, cz - 0.05]), np.array([cx + 0.22, -hgt - 0.34, cz - 0.12])
    spoon = M.Piece('spoon', [M.cone(a, b, 0.016, 0.016), M.sphere(b, 0.03)], k=0.01)
    out += _mannequin(c, 'spoon', 'metal', [spoon], pal['spoon'], gloss=(pal['gloss'], 50, 0.8), z=z + 0.02)
    out += _steam(c, 'tea_steam', cx - 0.04, -hgt - 0.10, cz)
    out.append(_shadow(c, 'tea', P.cylinder_points(cx, cz, 0, hgt, rh, r), 0.7))
    return out


def _cassette_player(c, cx, cz, yaw):
    """Radio-cassette recorder: tape door with a cassette inside, speaker, lit tuning dial, keys, antenna."""
    view, pal, lw, frame = c['view'], c['pal'], c['lw'], c['frame']
    W, H, D = 1.95, 0.95, 0.55
    verts, u, v = P.table_box(cx, cz, W, H, D, yaw)
    z = _z(view, (cx, 0, cz))
    out = P.solid('player', 'device', z, view, verts, P.BOX_FACES, pal['player'], lw)
    front = [verts[i] for i in (3, 2, 6, 7)]            # bottom-left, bottom-right, top-right, top-left
    quad = [front[0], front[1], None, front[3]]
    ex, ey = u, np.array([0.0, -1.0, 0.0])
    zf = z + 0.01
    panel = P.inset(view, quad, 0.03, 0.97, 0.06, 0.78)
    out.append(Drawable('player_panel', 'device', zf, fill=[panel], color=pal['player_face'],
                        normal_map=P.flat_normals(panel, view.normal(v)), casts=False, receives=False))
    door = P.inset(view, quad, 0.07, 0.47, 0.14, 0.70)
    out.append(Drawable('player_door', 'device', zf + 0.001, fill=[door], color=darken(pal['player'], 0.5),
                        strokes=[geom.stroke_polygon(np.vstack([door, door[:1]]), lw * 0.6)], line_color=pal['grille'],
                        casts=False, receives=False))
    tape = P.inset(view, quad, 0.10, 0.44, 0.20, 0.62)
    label = P.inset(view, quad, 0.12, 0.42, 0.44, 0.58)
    out.append(Drawable('player_tape', 'device', zf + 0.002, fill=[tape], color=pal['cassette'], opacity=0.8, clip=['player_door'],
                        casts=False, receives=False))
    out.append(Drawable('player_tape_label', 'device', zf + 0.003, fill=[label], color=pal['label'], opacity=0.8,
                        clip=['player_door'], casts=False, receives=False))
    hubs = [_face_disc(view, P.face_point(quad, s, 0.33), ex, ey, 0.05) for s in (0.20, 0.34)]
    out.append(Drawable('player_hubs', 'device', zf + 0.004, fill=hubs, fill_mode='each', color=pal['reel'],
                        clip=['player_door'], casts=False, receives=False))
    glare = P.inset(view, quad, 0.30, 0.38, 0.14, 0.70)
    out.append(Drawable('player_glare', 'emissive', zf + 0.005, fill=[glare], color=pal['gloss'], opacity=0.10,
                        clip=['player_door'], casts=False, receives=False))
    center = P.face_point(quad, 0.74, 0.42)
    R = 0.27
    ring = _face_disc(view, center, ex, ey, R, 48)
    out.append(Drawable('player_speaker', 'device', zf + 0.001, fill=[ring], color=darken(pal['player_face'], 0.8),
                        strokes=[geom.stroke_polygon(np.vstack([ring, ring[:1]]), lw * 0.7)], line_color=pal['grille'],
                        casts=False, receives=False))
    holes = [_face_disc(view, center + i * ex + j * ey, ex, ey, 0.011, 8)
             for i in np.arange(-R, R + 1e-6, 0.045) for j in np.arange(-R, R + 1e-6, 0.045) if i * i + j * j < (R * 0.9) ** 2]
    out.append(Drawable('player_grille', 'device', zf + 0.002, fill=holes, fill_mode='each', color=pal['grille'],
                        casts=False, receives=False))
    dial = P.inset(view, quad, 0.07, 0.93, 0.83, 0.93)
    out.append(Drawable('player_dial', 'emissive', zf + 0.001, fill=[dial], color=pal['dial'], opacity=0.85,
                        casts=False, receives=False))
    ticks = [P.inset(view, quad, s, s + 0.004, 0.85, 0.89) for s in np.arange(0.10, 0.91, 0.04)]
    ticks.append(P.inset(view, quad, 0.615, 0.622, 0.83, 0.93))
    out.append(Drawable('player_ticks', 'screen', zf + 0.002, fill=ticks, fill_mode='each', color=pal['grille'], opacity=0.8,
                        casts=False, receives=False))
    out.append(P.glow('player_dial_glow', dial.mean(axis=0), frame.px(0.95), frame.px(0.16), pal['dial'], 0.25, zf + 0.003))
    top = [verts[i] for i in P.BOX_FACES[P.TOP]]
    keys = [P.inset(view, top, 0.06 + k * 0.07, 0.115 + k * 0.07, 0.55, 0.88, lift=0.03, normal=(0, -1, 0)) for k in range(6)]
    out.append(Drawable('player_keys', 'device', z + 0.02, fill=keys, fill_mode='each', color=lighten(pal['player'], 0.35),
                        normal_map=P.flat_normals(np.vstack(keys), view.normal((0, -1, 0))),
                        strokes=[geom.stroke_polygon(np.vstack([q, q[:1]]), lw * 0.5) for q in keys], line_color=pal['grille'],
                        casts=False, receives=False))
    hl, hr = P.face_point(top, 0.18, 0.45), P.face_point(top, 0.72, 0.45)
    lift = np.array([0.0, -0.28, 0.0])
    handle = M.Piece('player_handle', M.chain([hl, hl + lift, hr + lift, hr], [0.04] * 4), k=0.04)
    base = P.face_point(top, 0.93, 0.30)
    tip = base + np.array([-0.45, -1.35, -0.15])
    antenna = M.Piece('player_antenna', [M.cone(base, tip, 0.022, 0.012), M.sphere(tip, 0.026)], k=0.01)
    out += _mannequin(c, 'player_handle', 'device', [handle], pal['player'], gloss=(pal['gloss'], 40, 0.5), z=z - 0.02)
    out += _mannequin(c, 'player_antenna', 'metal', [antenna], pal['spoon'], gloss=(pal['gloss'], 60, 0.8), z=z - 0.03)
    out.append(_shadow(c, 'player', np.vstack([verts, [hl + lift, hr + lift]])))
    return out


def _cassette(c, cx, cz, yaw):
    """Compact cassette lying flat: shell, label, window and two hubs on its top face."""
    view, pal, lw = c['view'], c['pal'], c['lw']
    verts, u, v = P.table_box(cx, cz, 0.84, 0.08, 0.54, yaw)
    z = _z(view, (cx, 0, cz))
    out = P.solid('cassette', 'device', z, view, verts, P.BOX_FACES, pal['cassette'], lw,
                  face_colors={P.FRONT: darken(pal['cassette'], 0.85), P.RIGHT: darken(pal['cassette'], 0.8)})
    top = [verts[i] for i in P.BOX_FACES[P.TOP]]
    up = view.normal((0, -1, 0))
    label = P.inset(view, top, 0.07, 0.93, 0.08, 0.72)
    stripe = P.inset(view, top, 0.07, 0.93, 0.12, 0.24)
    window = P.inset(view, top, 0.30, 0.70, 0.36, 0.58)
    foot = P.inset(view, top, 0.22, 0.78, 0.80, 0.96)
    for k, (name, poly, col) in enumerate((('label', label, pal['label']), ('stripe', stripe, lighten(pal['cassette'], 0.3)),
                                           ('window', window, pal['reel']), ('foot', foot, darken(pal['cassette'], 0.9)))):
        out.append(Drawable(f'cassette_{name}', 'device', z + 0.01 + k * 0.001, fill=[poly], color=col,
                            normal_map=P.flat_normals(poly, up), casts=False, receives=False))
    hubs = [_face_disc(view, P.face_point(top, s, 0.47) + np.array([0, -0.001, 0]), u, v, 0.06) for s in (0.24, 0.76)]
    out.append(Drawable('cassette_hubs', 'device', z + 0.015, fill=hubs, fill_mode='each', color=pal['cassette'],
                        normal_map=P.flat_normals(np.vstack(hubs), up),
                        strokes=[geom.stroke_polygon(np.vstack([q, q[:1]]), lw * 0.5) for q in hubs], line_color=pal['reel'],
                        casts=False, receives=False))
    out.append(_shadow(c, 'cassette', verts, 0.6))
    return out
