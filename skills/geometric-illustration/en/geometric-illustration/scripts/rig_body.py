"""Bust body rig: neck, shoulders, arms (to frame edge), sleeveless turtleneck.

Why: the bust shot needs a believable neck-to-shoulder transition and an
outfit silhouette. Body coordinates use head units with the head center as
origin, so the head and body stay proportional at any canvas size.
"""
import numpy as np

import geom
from palette import darken, lighten, line_color
from rig_face import face_contour, map_points
from scene import Drawable

Z = dict(collar_back=0.8, torso=0.0, neck=1.0, cloth=2.0, arm=2.5, collar=3.0)
BOTTOM = 3.2
NECK_HALF = 0.15
COLLAR_TOP, COLLAR_FOLD, COLLAR_BASE, COLLAR_RX = 0.86, 0.975, 1.07, 0.20


def _mirror(half):
    """Right-side outline (top -> bottom) mirrored to the left side (bottom -> top)."""
    return [(-u, v) for u, v in half[::-1]]


def edge_stroke(path, lw, k=1.0, start=0.15, end=0.02):
    return geom.stroke_polygon(path, lw * k * geom.taper(len(path), start, end))


def build_neck(head, body, face_spec, pal, lw, light_x):
    skin = pal['skin']
    w = NECK_HALF
    top_l = head.map([(-w - 0.01, 0.36), (-w, 0.58)], z=0.0)
    top_r = head.map([(w, 0.58), (w + 0.01, 0.36)], z=0.0)
    base_l = body.map([(-w - 0.005, 0.86), (-w - 0.05, 1.00)])
    base_r = body.map([(w + 0.05, 1.00), (w + 0.005, 0.86)])
    poly = np.vstack([top_l, base_l, base_r, top_r])
    left = geom.resample(geom.catmull_rom(np.vstack([top_l[1:], base_l])), 30)
    right = geom.resample(geom.catmull_rom(np.vstack([base_r, top_r[:1]])), 30)
    strokes = [geom.stroke_polygon(p, lw * 0.9 * geom.taper(30, 0.3, 0.3)) for p in (left, right)]
    neck = Drawable('neck', 'skin', Z['neck'], fill=[poly], color=skin, strokes=strokes,
                    line_color=line_color(skin), form_radius=body.px(0.10), casts=False)

    # shadow cast by the jaw: the jaw line pushed down and away from the light
    jaw = geom.catmull_rom(map_points(head, face_contour(face_spec)[3:10]))
    k = 1.0 if light_x < 0 else -1.0
    drop = jaw + np.array([k * 0.05, 0.19]) * head.unit
    neck_shadow = Drawable('neck_shadow', 'skin', 0, fill=[np.vstack([jaw, drop[::-1]])], kind='shadow',
                           clip_vis=['neck'], feather=head.px(0.005))
    return [neck, neck_shadow]


def build_torso_skin(body, outfit, pal, lw):
    sw = outfit['shoulder_width']
    half = [(0.16, 0.90), (0.35, 1.045), (0.62, 1.12), (0.90 * sw, 1.21), (sw, 1.36),
            (0.82, 1.70), (0.72, 2.4), (0.72, BOTTOM)]
    right = geom.catmull_rom(body.map(half))
    left = geom.catmull_rom(body.map(_mirror(half)))
    trap_r = geom.catmull_rom(body.map(half[:5]))
    trap_l = geom.catmull_rom(body.map(_mirror(half[:5])))
    return [Drawable('torso', 'skin', Z['torso'], fill=[np.vstack([left, right])], color=pal['skin'],
                     strokes=[edge_stroke(trap_r, lw, 1.1, 0.3, 0.05), edge_stroke(trap_l[::-1], lw, 1.1, 0.3, 0.05)],
                     line_color=line_color(pal['skin']), form_radius=body.px(0.25), casts=False)]


def build_arms(body, outfit, pal, lw):
    """Upper arms hang beside the torso and overlap the outfit's side seams."""
    sw = outfit['shoulder_width']
    out = []
    for s in (-1, 1):
        # outer contour bulges at the deltoid then tapers toward the elbow, angled slightly inward
        outer = [(0.86 * sw, 1.20), (sw, 1.27), (sw + 0.06, 1.45), (sw + 0.05, 1.85), (sw - 0.01, 2.45), (sw - 0.06, BOTTOM)]
        inner = [(sw - 0.31, BOTTOM), (sw - 0.27, 2.45), (sw - 0.25, 1.92), (sw - 0.235, 1.66), (0.68, 1.42), (0.72, 1.24)]
        o = geom.catmull_rom(body.map([(s * u, v) for u, v in outer]))
        i = geom.catmull_rom(body.map([(s * u, v) for u, v in inner]))
        poly = np.vstack([o, i])
        armpit = geom.catmull_rom(body.map([(s * u, v) for u, v in inner[:4]]))
        strokes = [edge_stroke(o, lw, 1.2, 0.12, 0.0), edge_stroke(armpit[::-1], lw, 0.9, 0.35, 0.0)]
        out.append(Drawable(f'arm_{s}', 'skin', Z['arm'], fill=[poly], color=pal['skin'], strokes=strokes,
                            line_color=line_color(pal['skin']), form_radius=body.px(0.13)))
    return out


def build_turtleneck(body, outfit, pal, lw):
    cloth = pal['cloth']
    cl = line_color(cloth)
    half = [(0.38, 1.04), (0.47, 1.22), (0.60, 1.48), (0.70, 1.70), (0.70, 2.0), (0.66, 2.5), (0.70, BOTTOM)]
    right = geom.catmull_rom(body.map(half))
    left = geom.catmull_rom(body.map(_mirror(half)))
    top = body.map([(-0.30, 1.02), (0.0, 1.00), (0.30, 1.02)])
    poly = np.vstack([left, top, right])       # left armhole up, across the yoke, right armhole down
    armholes = [edge_stroke(geom.catmull_rom(body.map(half[:5])), lw, 1.1, 0.05, 0.0),
                edge_stroke(geom.catmull_rom(body.map([(-u, v) for u, v in half[:5]])), lw, 1.1, 0.05, 0.0)]
    out = [Drawable('cloth', 'cloth', Z['cloth'], fill=[poly], color=cloth, strokes=armholes, line_color=cl,
                    form_radius=body.px(0.30))]

    # knit ribs follow the torso curvature: dense near the sides, wide at the center
    ribs = []
    for a in np.linspace(-0.92, 0.92, 15):
        u = 0.66 * np.sin(a * np.pi / 2)
        path = geom.resample(geom.catmull_rom(body.map([(u * 0.75, 1.05), (u, 1.6), (u * 1.02, 2.2), (u, BOTTOM)])), 40)
        ribs.append(geom.stroke_polygon(path, lw * 0.35 * geom.taper(40, 0.2, 0.0)))
    out.append(Drawable('cloth_ribs', 'cloth', Z['cloth'] + 0.01, fill=None, strokes=ribs, clip=['cloth'],
                        line_color=lighten(cl, 0.2)))

    # bust volume: normal-map bumps let the style's own lighting shade them, plus short contour hints
    for s in (-1, 1):
        cx, cy, r = s * 0.33, 1.80, 0.24
        bump = body.map(geom.ellipse(cx, cy, r, r * 0.92, 48))
        out.append(Drawable(f'bust_form_{s}', 'cloth', 0, fill=[bump], kind='form', form_radius=body.px(0.20),
                            clip_vis=['cloth'], feather=body.px(0.015), opacity=0.9))
        a0, a1 = (0.35, 1.25) if s > 0 else (np.pi - 1.25, np.pi - 0.35)
        arc = body.map(geom.ellipse(cx, cy, r, r * 0.9, 30, start=a0, end=a1))
        out.append(Drawable(f'bust_line_{s}', 'cloth', Z['cloth'] + 0.02, fill=None, clip=['cloth'],
                            strokes=[geom.stroke_polygon(arc, lw * 0.7 * geom.taper(len(arc), 0.45, 0.45))],
                            line_color=cl))
    out += build_collar(body, pal, lw)
    return out


def build_collar(body, pal, lw, z_back=Z['collar_back']):
    """Turtleneck collar. z_back: depth of the inner face; it must sit behind the neck so the neck
    enters the collar (the figure rig passes a value behind its mannequin body)."""
    cloth = pal['cloth']
    cl = line_color(cloth)
    rx, top_v = COLLAR_RX, COLLAR_TOP
    a = np.linspace(np.pi, 0, 40)
    front = body.map(np.stack([rx * np.cos(a), top_v + 0.045 * np.sin(a)], axis=1))   # left -> right, dips down
    back = body.map(np.stack([rx * np.cos(a), top_v - 0.035 * np.sin(a)], axis=1))
    sides_r = body.map([(rx + 0.01, COLLAR_FOLD - 0.02), (0.25, COLLAR_BASE - 0.03), (0.31, COLLAR_BASE)])
    sides_l = body.map([(-0.31, COLLAR_BASE), (-0.25, COLLAR_BASE - 0.03), (-rx - 0.01, COLLAR_FOLD - 0.02)])
    poly = np.vstack([front, sides_r, sides_l])
    xs = np.linspace(-rx - 0.01, rx + 0.01, 30)
    fold = body.map(np.stack([xs, COLLAR_FOLD + 0.03 * (1 - (xs / rx) ** 2)], axis=1))
    rim = np.vstack([back, front[::-1]])
    ribs = []
    for t in np.linspace(-0.85, 0.85, 11):
        x = rx * np.sin(t * np.pi / 2)
        path = body.map([(x, top_v + 0.045 * np.cos(t * np.pi / 2)), (x * 1.05, COLLAR_FOLD + 0.03)])
        ribs.append(geom.stroke_polygon(geom.resample(path, 12), lw * 0.4))
    # the back rim is inked on the inner layer so the neck hides it; the front rim belongs to the collar
    strokes = [geom.stroke_polygon(front, lw * 1.0), geom.stroke_polygon(fold, lw * 0.9 * geom.taper(30, 0.15, 0.15))]
    return [Drawable('collar_inner', 'cloth', z_back, fill=[rim], color=darken(cloth, 0.55), casts=False,
                     strokes=[geom.stroke_polygon(back, lw * 0.9)], line_color=cl),
            Drawable('collar', 'cloth', Z['collar'], fill=[poly], color=cloth, strokes=strokes, line_color=cl,
                     form_radius=body.px(0.10)),
            Drawable('collar_ribs', 'cloth', Z['collar'] + 0.01, fill=None, strokes=ribs, clip=['collar'],
                     line_color=lighten(cl, 0.15))]


def build_bust_outfit(body, outfit, pal, lw):
    out = build_torso_skin(body, outfit, pal, lw) + build_arms(body, outfit, pal, lw)
    if outfit['type'] == 'turtleneck_sleeveless':
        out += build_turtleneck(body, outfit, pal, lw)
    else:
        raise ValueError(f"unknown outfit type '{outfit['type']}' (use turtleneck_sleeveless)")
    return out


def body_guides(body):
    return [body.map([(-1.0, 1.27), (1.0, 1.27)]), body.map([(0, 0.6), (0, BOTTOM)])]
