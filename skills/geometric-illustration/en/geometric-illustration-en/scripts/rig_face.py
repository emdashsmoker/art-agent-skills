"""Face rig: contour, ears, eyes, brows, nose, mouth, blush.

Why: the face carries the expression, so every feature is a small parametric
recipe that mirrors how an anime illustrator constructs it (lid curves, iris
oval, catchlights, colored line weights).
All coordinates are head units (head width = 1, origin = skull center, y down).
"""
import numpy as np

import geom
from palette import darken, lighten, saturate, line_color
from scene import Drawable

Z = dict(ear=4.0, face=5.0, blush=5.2, lips=5.4, eye_white=6.0, iris=6.1, iris_light=6.2,
         pupil=6.25, catch=6.4, lash=7.0, mouth=6.5, brow=7.5, brow_over=12.0, metal=8.5)

CONTOUR_SAMPLES = 160


def map_points(frame, pts):
    """pts: iterable of (u, v, z) where z is a float, 'surface' or None (silhouette)."""
    return np.vstack([frame.map([p[:2]], z=p[2]) for p in pts])


# ---------------------------------------------------------------- contour

def face_contour(face):
    """Control points of the face outline from left temple to right temple via the chin."""
    cheek, jaw_u, jaw_v = face['cheek'], face['jaw_width'], face['jaw_height']
    chin_v, chin_w = face['chin_length'], face['chin_width']
    bulge = (1 - face['jaw_sharpness']) * 0.045
    half = [
        (0.49, -0.08, None),
        (cheek, 0.12, None),
        (cheek - 0.012, 0.25, None),
        (jaw_u, jaw_v, 0.05),
        ((jaw_u + chin_w) / 2 + bulge, (jaw_v + chin_v) / 2 + 0.035, 0.33),
        (chin_w, chin_v - 0.012, 0.55),
    ]
    left = [(-u, v, z) for (u, v, z) in half]
    return left + [(0.0, chin_v + 0.004, 0.58)] + half[::-1]


def build_face(frame, spec, pal, lw):
    face = spec['face']
    ctrl = face_contour(face)
    outline = geom.catmull_rom(map_points(frame, ctrl), samples=24)
    skull_top = frame.map([(0.40, -0.40), (0.0, -0.53), (-0.40, -0.40)], z=None)
    face_poly = np.vstack([outline, geom.catmull_rom(np.vstack([outline[-1], skull_top, outline[0]]))[1:-1]])

    contour = geom.resample(geom.sub_path(outline, 0.06, 0.94), CONTOUR_SAMPLES)
    t = np.linspace(0, 1, len(contour))
    weight = (0.45 + 0.55 * np.exp(-((t - 0.5) / 0.28) ** 2)) * geom.taper(len(contour), 0.12, 0.12, 0.15)
    skin_line = line_color(pal['skin'])
    drawables = [Drawable('face', 'skin', Z['face'], fill=[face_poly], color=pal['skin'],
                          strokes=[geom.stroke_polygon(contour, lw * 1.25 * weight)],
                          line_color=skin_line, form_radius=frame.px(0.09), casts=False)]
    guides = [frame.map(geom.ellipse(0, 0, 0.5, 0.5, 64), z=None), outline]
    return drawables, guides, outline


# The head from behind: skull sides down past the ears to the jaw corners, narrowing into the
# neck. The hair covers the top; below the hairline this is what shows.
BACK_HEAD = [(0.50, -0.10), (0.49, 0.10), (0.46, 0.27), (0.38, 0.38), (0.28, 0.45), (0.24, 0.62),
             (-0.24, 0.62), (-0.28, 0.45), (-0.38, 0.38), (-0.46, 0.27), (-0.49, 0.10), (-0.50, -0.10)]


def build_back_head(frame, pal, lw):
    """Head outline seen from behind (skin under the hair); only its sides are inked."""
    top = [(0.5 * np.cos(a), -0.02 - 0.52 * np.sin(a)) for a in np.linspace(np.pi, 0, 15)][1:-1]
    poly = geom.catmull_rom(frame.map(np.array(BACK_HEAD + top), z=None), closed=True)
    skin_line = line_color(pal['skin'])
    strokes = []
    for s in (-1, 1):
        side = geom.catmull_rom(frame.map(np.array([(s * u, v) for u, v in BACK_HEAD[:6]]), z=None))
        strokes.append(geom.stroke_polygon(side, lw * 1.1 * geom.taper(len(side), 0.2, 0.6)))
    return [Drawable('face', 'skin', Z['face'], fill=[poly], color=pal['skin'], strokes=strokes,
                     line_color=skin_line, form_radius=frame.px(0.09), casts=False)]


def build_ears(frame, pal, lw, metal_style):
    out = []
    skin_line = line_color(pal['skin'])
    for s in (-1, 1):
        shape = [(0.462, 0.02), (0.525, -0.012), (0.556, 0.075), (0.546, 0.19), (0.516, 0.285),
                 (0.488, 0.300), (0.466, 0.27)]
        pts = frame.map([(s * u, v) for u, v in shape], z=-0.05)
        poly = geom.catmull_rom(pts, closed=True)
        inner = geom.catmull_rom(frame.map([(s * 0.50, 0.06), (s * 0.528, 0.11), (s * 0.517, 0.205)], z=-0.05))
        out.append(Drawable(f'ear_{s}', 'skin', Z['ear'], fill=[poly], color=pal['skin'],
                            strokes=[geom.stroke_polygon(poly, lw * 0.8),
                                     geom.stroke_polygon(inner, lw * 0.6 * geom.taper(len(inner), 0.3, 0.3))],
                            line_color=skin_line, form_radius=frame.px(0.03), casts=False))
        if metal_style != 'none':
            out += _earring(frame, s, pal, lw, metal_style)
    return out


def _earring(frame, s, pal, lw, style):
    """Drop earring hangs straight down in screen space (gravity ignores head roll)."""
    lobe = frame.map([(s * 0.505, 0.292)], z=-0.05)[0]
    drop = frame.px(0.10 if style == 'drop' else 0.0)
    gem_r = frame.px(0.022)
    chain = np.array([lobe, lobe + [0, drop * 0.5], lobe + [0, drop]])
    gem = geom.ellipse(lobe[0], lobe[1] + drop + gem_r * 1.25, gem_r, gem_r * 1.35, 36)
    metal = pal['metal']
    return [Drawable(f'earring_chain_{s}', 'metal', Z['metal'], fill=[geom.stroke_polygon(chain, lw * 0.55)],
                     color=metal, casts=False, receives=False, fill_mode='union'),
            Drawable(f'earring_gem_{s}', 'metal', Z['metal'] + 0.01, fill=[gem], color=metal,
                     strokes=[geom.stroke_polygon(np.vstack([gem, gem[:1]]), lw * 0.45)],
                     line_color=darken(metal, 0.4), casts=False, form_radius=gem_r * 0.9)]


# ---------------------------------------------------------------- eyes

UPPER_LID = [(-0.50, 0.12), (-0.38, -0.25), (-0.15, -0.48), (0.12, -0.53), (0.36, -0.37), (0.53, -0.06)]
LOWER_LID = [(0.53, -0.06), (0.42, 0.24), (0.16, 0.42), (-0.16, 0.40), (-0.42, 0.27), (-0.50, 0.12)]
LASH_WING = [(0.61, -0.07), (0.69, -0.17)]
EYE_ASPECT = 0.60   # open eye height / width


class EyeSpace:
    """Eye-local coordinates: x toward the outer corner, y down, both in eye widths."""

    def __init__(self, frame, cx, cy, side, width, tilt, aspect):
        self.frame, self.cx, self.cy, self.s = frame, cx, cy, side
        self.w, self.tilt, self.aspect = width, tilt, aspect

    def uv(self, local, lid_space=True):
        p = np.atleast_2d(np.asarray(local, float)).copy()
        if lid_space:
            p[:, 1] *= self.aspect
        a = -self.tilt
        x = p[:, 0] * np.cos(a) - p[:, 1] * np.sin(a)
        y = p[:, 0] * np.sin(a) + p[:, 1] * np.cos(a)
        return np.stack([self.cx + self.s * x * self.w, self.cy + y * self.w], axis=1)

    def screen(self, local, lid_space=True):
        return self.frame.map(self.uv(local, lid_space), z='surface')


def _profile(n, knots):
    t = np.linspace(0, 1, n)
    k = np.asarray(knots, float)
    return np.interp(t, k[:, 0], k[:, 1])


CLOSED_ARCH = 0.22            # a closed smiling eye: the lash line arches up by this (eye widths)


def closed_eye(frame, side, eyes, pal, lw):
    """A smiling closed eye: one arched lash line (the anime 'happy eye')."""
    es = EyeSpace(frame, side * eyes['spacing'], eyes['height'], side, 0.205 * eyes['size'], eyes['tilt'], 1.0)
    xs = np.linspace(-0.48, 0.58, 9)
    arch = [(x, 0.05 - CLOSED_ARCH * (1 - ((x - 0.05) / 0.55) ** 2)) for x in xs]
    path = geom.resample(geom.catmull_rom(es.screen(arch, lid_space=False)), 60)
    widths = lw * 2.2 * eyes['lash_weight'] ** 0.5 * _profile(60, [(0, 0.15), (0.3, 0.8), (0.7, 1.0), (1, 0.2)])
    return [Drawable(f'lash_{side}_closed', 'lash', Z['lash'], fill=[geom.stroke_polygon(path, widths)],
                     color=pal['lash'], casts=False, receives=False, fill_mode='union')], es


def build_eye(frame, side, eyes, pal, lw, light_x):
    if eyes.get('shape', 'open') == 'closed':
        return closed_eye(frame, side, eyes, pal, lw)
    aspect = EYE_ASPECT * eyes['openness']
    es = EyeSpace(frame, side * eyes['spacing'], eyes['height'], side, 0.205 * eyes['size'],
                  eyes['tilt'], aspect)
    tag = f'{side}'
    upper = geom.catmull_rom(es.screen(UPPER_LID))
    lower = geom.catmull_rom(es.screen(LOWER_LID))
    opening = np.vstack([upper, lower[1:-1]])
    white_name, iris_name = f'eye_white_{tag}', f'iris_{tag}'
    eye = pal['eye']
    out = [Drawable(white_name, 'eye_white', Z['eye_white'], fill=[opening], color=pal['sclera'],
                    casts=False)]

    # iris and pupil, authored as true ovals in eye space (not lid space)
    gx, gy = eyes['gaze']
    ic = np.array([0.03 + gx * 0.18, 0.02 + gy * 0.12])
    iris = es.screen(geom.ellipse(ic[0], ic[1], 0.27, 0.355, 64), lid_space=False)
    top, bottom = es.screen([ic + [0, -0.30], ic + [0, 0.30]], lid_space=False)
    out.append(Drawable(iris_name, 'iris', Z['iris'], fill=[iris],
                        gradient=(darken(eye, 0.42), lighten(saturate(eye, 0.25), 0.18), top, bottom),
                        strokes=[geom.stroke_polygon(np.vstack([iris, iris[:1]]), lw * 0.75)],
                        line_color=darken(eye, 0.28), clip=[white_name], casts=False))
    glow = es.screen(geom.ellipse(ic[0], ic[1] + 0.15, 0.17, 0.12, 48), lid_space=False)
    out.append(Drawable(f'iris_glow_{tag}', 'iris', Z['iris_light'], fill=[glow],
                        color=lighten(saturate(eye, 0.4), 0.30), opacity=0.85, feather=frame.px(0.004),
                        clip=[white_name, iris_name], casts=False))
    pupil = es.screen(geom.ellipse(ic[0], ic[1] - 0.02, 0.105, 0.155, 48), lid_space=False)
    out.append(Drawable(f'pupil_{tag}', 'iris', Z['pupil'], fill=[pupil], color=darken(eye, 0.16),
                        clip=[white_name], casts=False))

    # catchlights sit on the light side for both eyes
    lx = -1.0 if light_x < 0 else 1.0
    main = ic + [lx * 0.10 * side, -0.14]      # local x flips with side, so multiply by side
    second = ic + [-lx * 0.12 * side, 0.15]
    for i, (c, r) in enumerate([(main, (0.088, 0.072)), (second, (0.036, 0.032))]):
        shape = es.screen(geom.ellipse(c[0], c[1], r[0], r[1], 32), lid_space=False)
        out.append(Drawable(f'catch_{tag}_{i}', 'iris', Z['catch'] + i * 0.01, fill=[shape],
                            color=np.ones(3, np.float32), clip=[white_name], casts=False, receives=False))

    # upper lid shadow on the eyeball (multiply layer)
    shadow_local = [(x, y + 0.30 + 0.06 * np.cos(np.pi * x)) for x, y in UPPER_LID[::-1]]
    lid_shadow = np.vstack([upper, geom.catmull_rom(es.screen(shadow_local))])
    out.append(Drawable(f'lid_shadow_{tag}', 'eye_white', 0, fill=[lid_shadow], kind='shadow',
                        clip_vis=['eye_white', 'iris'], feather=frame.px(0.003)))

    out += _lashes(es, eyes, pal, lw, tag)
    crease_local = [(x * 0.92, y - 0.23 - 0.05 * (1 - abs(x))) for x, y in UPPER_LID[1:]]
    crease = geom.resample(geom.catmull_rom(es.screen(crease_local)), 40)
    out.append(Drawable(f'crease_{tag}', 'skin', Z['lash'], fill=None,
                        strokes=[geom.stroke_polygon(crease, lw * 0.55 * geom.taper(40, 0.35, 0.3))],
                        line_color=line_color(pal['skin'])))
    return out, es


def _lashes(es, eyes, pal, lw, tag):
    lash_color = pal['lash']
    weight = lw * 2.6 * eyes['lash_weight']
    ctrl = [(x, y - 0.035) for x, y in UPPER_LID[1:]] + LASH_WING
    ctrl = [(UPPER_LID[0][0] + 0.02, UPPER_LID[0][1] - 0.02)] + ctrl
    path = geom.resample(geom.catmull_rom(es.screen(ctrl)), 90)
    widths = weight * _profile(len(path), [(0, 0.15), (0.25, 0.45), (0.6, 0.9), (0.8, 1.0), (0.92, 0.55), (1, 0.0)])
    polys = [geom.stroke_polygon(path, widths)]
    # outer lash spikes: direction is given in eye space and converted to a screen offset
    origin = es.screen([[0.5, 0.0]], False)[0]
    for root_t, direction, length in [(0.76, (0.45, -1.0), 0.12), (0.88, (0.85, -0.6), 0.11)]:
        d = np.asarray(direction) / np.linalg.norm(direction) * length
        root = path[int(root_t * (len(path) - 1))]
        tip = root + es.screen([[0.5 + d[0], d[1]]], False)[0] - origin
        mid = (root + tip) / 2 + np.array([0.0, -0.15]) * np.linalg.norm(tip - root)
        spike = geom.resample(geom.catmull_rom(np.array([root, mid, tip])), 16)
        polys.append(geom.stroke_polygon(spike, weight * 0.5 * geom.taper(16, 0.0, 0.9)))
    lower_ctrl = [(x, y + 0.02) for x, y in LOWER_LID[:4]]
    lower = geom.resample(geom.catmull_rom(es.screen(lower_ctrl)), 40)
    polys.append(geom.stroke_polygon(lower, weight * 0.28 * geom.taper(40, 0.25, 0.5)))
    return [Drawable(f'lash_{tag}_{i}', 'lash', Z['lash'] + 0.001 * i, fill=[p], color=lash_color,
                     casts=False, receives=False, fill_mode='union')
            for i, p in enumerate(polys)]


def build_brows(frame, eyes_spec, brows, pal, lw):
    out = []
    color = saturate(darken(pal['hair'], 0.95), 0.1)
    for s in (-1, 1):
        cx, cy = s * eyes_spec['spacing'], eyes_spec['height'] + brows['height']
        lift = brows['angle']
        ctrl = [(cx + s * -0.10, cy - 0.118 + lift * 0.02), (cx + s * 0.00, cy - 0.150),
                (cx + s * 0.10, cy - 0.152 - lift * 0.01), (cx + s * 0.175, cy - 0.125)]
        path = geom.resample(geom.catmull_rom(frame.map(ctrl, z='surface')), 50)
        widths = lw * 2.3 * brows['thickness'] * _profile(50, [(0, 0.7), (0.15, 1.0), (0.6, 0.75), (1, 0.05)])
        poly = geom.stroke_polygon(path, widths)
        out.append(Drawable(f'brow_{s}', 'brow', Z['brow'], fill=[poly], color=color, casts=False,
                            receives=False, fill_mode='union'))
        if brows['see_through'] > 0:
            out.append(Drawable(f'brow_over_{s}', 'brow', Z['brow_over'], fill=[poly], color=color,
                                opacity=brows['see_through'], casts=False, receives=False, fill_mode='union'))
    return out


# ---------------------------------------------------------------- nose, mouth, blush

def build_nose(frame, pal, lw, light_x):
    k = 1.0 if light_x < 0 else -1.0  # shadow side faces away from the light
    tip = geom.resample(geom.catmull_rom(frame.map([(k * 0.004, 0.343), (k * 0.024, 0.357), (k * 0.040, 0.349)], z=0.62)), 20)
    shadow = geom.catmull_rom(frame.map([(k * 0.026, 0.27), (k * 0.040, 0.325), (k * 0.036, 0.352),
                                         (k * 0.012, 0.364), (k * 0.016, 0.32)], z=0.60), closed=True)
    return [Drawable('nose_line', 'skin', Z['mouth'], fill=None,
                     strokes=[geom.stroke_polygon(tip, lw * 0.8 * geom.taper(20, 0.3, 0.4))],
                     line_color=line_color(pal['skin'])),
            Drawable('nose_shadow', 'skin', 0, fill=[shadow], kind='shadow', feather=frame.px(0.004),
                     clip_vis=['face'])]


MOUTH_OPEN_DEPTH = 0.075       # head units: a fully open mouth drops this far below the lip line
O_MOUTH_WIDTH = 0.42           # a round 'o' (no smile) is this narrow relative to the closed mouth
OPEN_SMILE_WIDTH = 1.15        # a laughing mouth is a little wider than the closed one
TEETH_DEPTH = 0.30             # the upper teeth fill this fraction of the opening


def open_mouth(frame, mouth, pal, lw):
    """An open mouth: dark inside, a band of teeth under the upper lip in a smile, the tongue below.
    Without a smile it is a small round 'o' (surprise)."""
    smile, w, k = mouth['smile'], mouth['width'], mouth['open']
    depth = MOUTH_OPEN_DEPTH * k
    round_o = smile < 0.3
    half = 0.064 * w * (O_MOUTH_WIDTH if round_o else OPEN_SMILE_WIDTH)
    if round_o:
        shape = frame.map(geom.ellipse(0.0, 0.52 + depth * 0.45, half, depth * 0.55, 40), z='surface')
        top_edge = None
    else:
        lift = min(smile, 1.0) * 0.012
        top = [(-half, 0.514 - lift), (-half * 0.5, 0.516), (0.0, 0.517), (half * 0.5, 0.516), (half, 0.513 - lift)]
        bottom = [(half * 0.70, 0.52 + depth * 0.60), (0.0, 0.52 + depth), (-half * 0.70, 0.52 + depth * 0.60)]
        shape = geom.catmull_rom(frame.map(top + bottom, z='surface'), closed=True)
        top_edge = top
    inside = darken(pal['lips'], 0.32)
    out = [Drawable('mouth_open', 'lips', Z['mouth'] - 0.05, fill=[shape], color=inside, casts=False,
                    strokes=[geom.stroke_polygon(np.vstack([shape, shape[:1]]), lw * 0.8)],
                    line_color=darken(saturate(pal['lips'], 0.2), 0.42))]
    tongue = frame.map(geom.ellipse(0.0, 0.52 + depth * 0.85, half * 0.55, depth * 0.30, 24), z='surface')
    out.append(Drawable('tongue', 'lips', Z['mouth'] - 0.04, fill=[tongue], color=lighten(pal['lips'], 0.15),
                        clip=['mouth_open'], casts=False))
    if top_edge is not None:                          # teeth: a band that follows the upper lip
        band = [(x, y - 0.01) for x, y in top_edge] + [(x, y + depth * TEETH_DEPTH) for x, y in top_edge[::-1]]
        teeth = geom.catmull_rom(frame.map(band, z='surface'), closed=True)
        out.append(Drawable('teeth', 'eye_white', Z['mouth'] - 0.03, fill=[teeth], color=np.array([0.97, 0.96, 0.96]),
                            clip=['mouth_open'], casts=False))
    return out


def build_mouth(frame, mouth, pal, lw):
    if mouth.get('open', 0.0) > 0.05:
        return open_mouth(frame, mouth, pal, lw)
    smile, w = mouth['smile'], mouth['width']
    line_ctrl = [(-0.064 * w, 0.514 - smile * 0.014), (-0.022 * w, 0.522), (0.022 * w, 0.521),
                 (0.066 * w, 0.511 - smile * 0.018)]
    line = geom.resample(geom.catmull_rom(frame.map(line_ctrl, z='surface')), 40)
    widths = lw * 1.0 * _profile(40, [(0, 0.1), (0.25, 0.8), (0.5, 1.0), (0.75, 0.8), (1, 0.1)])
    upper = frame.map([(-0.056 * w, 0.514), (-0.022 * w, 0.501), (0.0, 0.505), (0.022 * w, 0.501), (0.056 * w, 0.512)], z='surface')
    lower = frame.map([(0.050 * w, 0.519), (0.024 * w, 0.548), (0.0, 0.556), (-0.024 * w, 0.548), (-0.050 * w, 0.521)], z='surface')
    lips_poly = geom.catmull_rom(np.vstack([upper, lower]), closed=True)
    lip_color = pal['lips']
    hl = frame.map(geom.ellipse(0.010, 0.541, 0.016, 0.006, 24), z='surface')
    under = frame.map(geom.ellipse(0.0, 0.575, 0.030, 0.0075, 24), z='surface')
    return [Drawable('lips', 'lips', Z['lips'], fill=[lips_poly], color=lip_color,
                     opacity=mouth['lip_strength'], feather=frame.px(0.003), casts=False),
            Drawable('mouth_line', 'skin', Z['mouth'], fill=None, strokes=[geom.stroke_polygon(line, widths)],
                     line_color=darken(saturate(lip_color, 0.2), 0.42)),
            Drawable('lip_gloss', 'lips', 0, fill=[hl], kind='highlight', hl_color=lighten(lip_color, 0.75),
                     opacity=0.8, feather=frame.px(0.003), clip_vis=['lips']),
            Drawable('under_lip', 'skin', 0, fill=[under], kind='shadow', feather=frame.px(0.004),
                     opacity=0.7, clip_vis=['face'])]


def build_blush(frame, amount, pal):
    if amount <= 0:
        return []
    out = []
    for s in (-1, 1):
        shape = frame.map(geom.ellipse(s * 0.25, 0.31, 0.085, 0.040, 40), z='surface')
        out.append(Drawable(f'blush_{s}', 'skin', Z['blush'], fill=[shape], color=pal['blush'],
                            opacity=amount, feather=frame.px(0.03), casts=False, clip=['face']))
    return out


def face_guides(frame, eyes):
    """Construction lines: center line, eye line, nose line, mouth line."""
    center = frame.map([(0, v) for v in np.linspace(-0.5, 0.7, 30)], z=np.linspace(0.30, 0.58, 30))
    lines = [center]
    for v in (eyes['height'], 0.35, 0.52):
        lines.append(frame.map([(u, v) for u in np.linspace(-0.5, 0.5, 30)], z='surface'))
    return lines
