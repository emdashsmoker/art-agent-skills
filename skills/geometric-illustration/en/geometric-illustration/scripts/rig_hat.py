"""Hats drawn over the hair (outfit.hat): a cuffed knit beanie.

Why: a hat sits on the skull and presses the hair flat, so it is drawn as its own
dome over the head after the hair: the hair above the cuff is hidden, the bangs and
side locks show only below it. Like the hair cap, the dome outline is a fixed
silhouette while the cuff follows the face surface, so it wraps the forehead when
the head turns.
"""
import numpy as np

import geom
from frames import face_surface_z
from palette import darken, line_color
from scene import Drawable

HATS = ('none', 'beanie')
HAT_Z = 12.0                   # above every hair layer (bangs 10, wisps 11.5)
HAT_THICK = 0.05               # head units the knit stands off the pressed hair
HAT_CROWN = 0.07               # extra height of the dome (a beanie is a little taller than the skull)
HAIR_PRESS = 0.5               # share of the hair volume left under the hat
CUFF_FRONT_V = -0.21           # cuff bottom over the forehead (brows sit near -0.02)
CUFF_BACK_V = 0.06             # seen from behind the cuff runs lower, over the nape hair
CUFF_SIDE_V = 0.02             # cuff bottom at the sides, over the tops of the ears
CUFF_HEIGHT = 0.14             # folded band
CUFF_CURVE = 2.2               # how fast the cuff drops from the forehead to the sides
CUFF_RIBS = 22
DOME_RIBS = 9
SAMPLES = 25


def build_hat(frame, kind, pal, lw, hair_volume, away=False):
    if kind not in HATS:
        raise ValueError(f"unknown outfit.hat '{kind}' (use {', '.join(HATS)})")
    if kind == 'none':
        return []
    return beanie(frame, pal['hat'], lw, hair_volume, away)


def _dome(hair_volume):
    rx = 0.5 + hair_volume * HAIR_PRESS + HAT_THICK
    return rx, rx + 0.02 + HAT_CROWN


def _edge_point(rx, ry, v):
    """Half-width of the dome silhouette (center v = -0.02) at height v."""
    s = np.clip((-0.02 - v) / ry, -1, 1)
    return rx * np.sqrt(1 - s * s)


def _cuff_line(frame, rx, ry, v_mid, v_side, lift_v, away):
    """Cuff edge from the left silhouette to the right one at the given heights."""
    half = _edge_point(rx, ry, v_side + lift_v)
    u = np.linspace(-half, half, SAMPLES)
    v = v_mid + (v_side - v_mid) * np.abs(u / half) ** CUFF_CURVE + lift_v
    uv = np.stack([u, v], axis=1)
    if away:
        return frame.map(uv, z=None)
    k = np.clip(1 - (u / half) ** 2, 0, 1)
    return frame.map(uv, z=face_surface_z(u) + HAT_THICK * np.sqrt(k))     # meets the silhouette at the sides


def beanie(frame, color, lw, hair_volume, away):
    rx, ry = _dome(hair_volume)
    v_mid = CUFF_BACK_V if away else CUFF_FRONT_V
    a0 = np.arcsin(np.clip((CUFF_SIDE_V + 0.02) / ry, -1, 1))
    arc_uv = np.array([(rx * np.cos(a), -0.02 - ry * np.sin(a)) for a in np.linspace(-a0, np.pi + a0, SAMPLES)])
    arc = frame.map(arc_uv, z=None)
    bottom = _cuff_line(frame, rx, ry, v_mid, CUFF_SIDE_V, 0.0, away)
    top = _cuff_line(frame, rx, ry, v_mid, CUFF_SIDE_V, -CUFF_HEIGHT, away)
    body = np.vstack([arc, bottom])                 # arc runs right to left over the top, the cuff back left to right
    proxy = [frame.map(geom.ellipse(0, -0.02, rx, ry, 72), z=None)]
    lc = line_color(color)
    outline = geom.stroke_polygon(np.vstack([arc, bottom]), lw * 1.2)
    out = [Drawable('hat', 'cloth', HAT_Z, fill=[body], color=color, strokes=[outline], line_color=lc,
                    form_radius=frame.px(0.35), form_poly=proxy)]
    band = np.vstack([top, bottom[::-1]])
    out.append(Drawable('hat_cuff', 'cloth', HAT_Z + 0.01, fill=[band], color=darken(color, 0.92), clip=['hat'],
                        strokes=[geom.stroke_polygon(top, lw * 0.9)], line_color=lc, form_radius=frame.px(0.06)))
    ribs = [geom.stroke_polygon(np.array([bottom[i], top[i]]), lw * 0.5) for i in
            np.linspace(1, SAMPLES - 2, CUFF_RIBS).round().astype(int)]
    out.append(Drawable('hat_cuff_ribs', 'cloth', HAT_Z + 0.02, fill=ribs, fill_mode='union', color=darken(color, 0.7),
                        opacity=0.7, clip=['hat_cuff'], casts=False, receives=False))
    apex = frame.map([(0.0, -0.02 - ry * 0.98)], z=None)[0]
    seams = []
    for i in np.linspace(2, SAMPLES - 3, DOME_RIBS).round().astype(int):
        start = top[i]
        mid = (start + apex) / 2 + np.array([(start[0] - apex[0]) * 0.15, 0.0])   # meridians bow out like a dome
        path = geom.resample(geom.catmull_rom(np.array([start, mid, apex])), 16)
        seams.append(geom.stroke_polygon(path, lw * 0.4 * geom.taper(16, 0.0, 0.6)))
    out.append(Drawable('hat_knit', 'cloth', HAT_Z + 0.005, fill=seams, fill_mode='union', color=darken(color, 0.75),
                        opacity=0.45, clip=['hat'], casts=False, receives=False))
    return out
