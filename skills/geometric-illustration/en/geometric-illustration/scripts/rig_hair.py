"""Hair rig: back mass, crown cap, bangs, side locks, tucked locks, highlights.

Why: anime hair reads as overlapping clumps (tapered ribbons) layered back to
front. Each clump is a spine curve plus a width profile; line art traces both
edges through the pointed tip, which is how an illustrator inks a clump.
"""
import numpy as np

import geom
from frames import face_surface_z
from palette import darken, line_color
from scene import Drawable

Z = dict(back=-10.0, tucked=-5.0, cap=9.0, side=9.5, bangs=10.0, wisp=11.5)
HAIR_LIFT = 0.035          # hair floats slightly above the skin surface
CLUMP_SAMPLES = 36
SKULL_RY_EXTRA = 0.02
MIN_BANGS = 3


def _perp_up(d):
    p = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-9)
    return -p if p[1] > 0 else p


def spine_from_ends(root, tip, bend=0.1, curl=-0.03):
    """Cubic spine that arches (bend>0 bulges upward) and curls at the tip."""
    r, t = np.asarray(root, float), np.asarray(tip, float)
    d = t - r
    length = np.linalg.norm(d)
    up = _perp_up(d)
    c1 = r + d / 3 + up * bend * length
    c2 = r + 2 * d / 3 + up * curl * length
    return geom.bezier(r, c1, c2, t, CLUMP_SAMPLES)


def map_spine(frame, spine_uv, depth):
    """depth: 'surface', None (static silhouette) or float lift over the skull."""
    if depth == 'surface':
        z = face_surface_z(spine_uv[:, 0]) + HAIR_LIFT
    elif depth is None:
        return frame.map(spine_uv, z=None)
    else:
        z = np.full(len(spine_uv), float(depth))
    return frame.map(spine_uv, z=z)


def clump_shapes(spine_px, width_px, lw, tip_pinch=0.65, root_cover=0.12):
    """Ribbon polygon plus its inked outline (both edges joined at the tip)."""
    n = len(spine_px)
    s = np.linspace(0, 1, n)
    widths = width_px * (1 - s) ** 0.75 * (0.82 + 0.18 * np.sin(np.pi * s))
    widths = np.maximum(widths, 0.0)
    poly = geom.stroke_polygon(spine_px, widths)
    nrm = geom.normals(spine_px)
    left = spine_px + nrm * widths[:, None] / 2
    right = spine_px - nrm * widths[:, None] / 2
    i0 = int(root_cover * n)
    outline = np.vstack([left[i0:], right[::-1][:n - i0]])
    m = len(outline)
    t = np.linspace(0, 1, m)
    pinch = 1 - tip_pinch * np.exp(-((t - 0.5) / 0.06) ** 2)
    line_w = lw * pinch * geom.taper(m, 0.18, 0.18, 0.0)
    return poly, geom.stroke_polygon(outline, line_w), widths


def make_clump(name, frame, spine_uv, width, depth, color, lw, z, pal, proxy=None, detail=True, rng=None):
    spine_px = geom.resample(map_spine(frame, spine_uv, depth), CLUMP_SAMPLES)
    poly, outline, widths = clump_shapes(spine_px, frame.px(width), lw)
    out = [Drawable(name, 'hair', z, fill=[poly], color=color, strokes=[outline],
                    line_color=line_color(color), form_radius=frame.px(0.35) if proxy is not None else frame.px(width * 0.6),
                    form_poly=proxy, fill_mode='union')]
    if detail:
        offset = (rng.uniform(-0.25, 0.25) if rng is not None else 0.2)
        nrm = geom.normals(spine_px)
        a, b = int(0.30 * CLUMP_SAMPLES), int(0.88 * CLUMP_SAMPLES)
        strand = spine_px[a:b] + nrm[a:b] * (widths[a:b, None] * offset)
        out.append(Drawable(name + '_strand', 'hair', z + 0.0005, fill=None, clip=[name],
                            strokes=[geom.stroke_polygon(strand, lw * 0.45 * geom.taper(len(strand), 0.3, 0.4))],
                            line_color=line_color(color)))
    return out


# ---------------------------------------------------------------- parts

def back_mass(frame, hair, color, lw, z=Z['back'], shift=0.0):
    """z, shift: a turned figure brings the hanging hair over the back (z) and toward it (head units)."""
    vol, length = hair['volume'], hair['length']
    rx, ry = 0.5 + vol * 1.4, 0.52 + vol * 1.4
    top = [(rx * np.cos(a), -0.02 - ry * np.sin(a)) for a in np.linspace(0, np.pi, 9)]
    left_side = [(-rx - 0.04, 0.35), (-rx - 0.08, 0.85), (-rx - 0.10, min(1.35, length - 0.2))]
    right_side = [(rx + 0.10, min(1.35, length - 0.2)), (rx + 0.08, 0.85), (rx + 0.04, 0.35)]
    teeth = []
    xs = np.linspace(-rx - 0.10, rx + 0.10, 11)
    for i, x in enumerate(xs):
        teeth.append((x, length + (0.10 if i % 2 else -0.02)))
    ring = right_side + top[1:-1] + left_side      # bottom-right, over the crown, down to bottom-left
    hang = np.array([max(0.0, min(1.0, (v - 0.2) / 0.8)) for _, v in ring])   # the crown stays, the hanging part shifts
    ring = np.array(ring) + np.stack([shift * hang, 0 * hang], axis=1)
    teeth = np.array(teeth) + np.array([shift, 0.0])
    outline = geom.catmull_rom(frame.map(ring, z=None))
    hem = frame.map(teeth, z=None)                  # left -> right closes the loop
    poly = np.vstack([outline, hem])
    stroke = geom.stroke_polygon(outline, lw * 1.2 * geom.taper(len(outline), 0.05, 0.05, 0.3))
    return [Drawable('hair_back', 'hair', z, fill=[poly], color=color, strokes=[stroke],
                     line_color=line_color(color), form_radius=frame.px(0.25), casts=False)]


def updo_mass(frame, hair, color, lw, z=Z['back']):
    """Hair swept up from the nape: a rounded back-of-head shape ending above the neck."""
    vol = hair['volume']
    rx, ry = 0.5 + vol * 1.2, 0.52 + vol * 1.2
    arc = [(rx * np.cos(a), -0.02 - ry * np.sin(a)) for a in np.linspace(-0.45, np.pi + 0.45, 21)]
    nape = [(-rx * 0.80, 0.30), (-0.22, 0.42), (0.22, 0.42), (rx * 0.80, 0.30)]
    poly = geom.catmull_rom(frame.map(np.array(arc + nape), z=None), closed=True)
    outer = geom.catmull_rom(frame.map(np.array(arc), z=None))
    stroke = geom.stroke_polygon(outer, lw * 1.2 * geom.taper(len(outer), 0.05, 0.05, 0.3))
    return [Drawable('hair_back', 'hair', z, fill=[poly], color=color, strokes=[stroke],
                     line_color=line_color(color), form_radius=frame.px(0.25), casts=False)]


SHORT_NAPE_Y = 0.30           # short hair ends just above the nape
SHORT_SIDEBURN = [(0.43, -0.26), (0.475, -0.02), (0.47, 0.17)]   # temple to the top of the ear (head units)
SHORT_SIDEBURN_W = 0.075


def short_mass(frame, hair, color, lw, z=Z['back']):
    """Short cut seen from the front: the back of the head ending above the nape, ears left free."""
    vol = hair['volume']
    rx, ry = 0.5 + vol * 1.2, 0.52 + vol * 1.2
    arc = [(rx * np.cos(a), -0.02 - ry * np.sin(a)) for a in np.linspace(-0.30, np.pi + 0.30, 21)]
    nape = [(-rx * 0.86, SHORT_NAPE_Y - 0.08), (-0.30, SHORT_NAPE_Y), (0.30, SHORT_NAPE_Y), (rx * 0.86, SHORT_NAPE_Y - 0.08)]
    poly = geom.catmull_rom(frame.map(np.array(arc + nape), z=None), closed=True)
    outer = geom.catmull_rom(frame.map(np.array(arc), z=None))
    stroke = geom.stroke_polygon(outer, lw * 1.2 * geom.taper(len(outer), 0.05, 0.05, 0.3))
    return [Drawable('hair_back', 'hair', z, fill=[poly], color=color, strokes=[stroke],
                     line_color=line_color(color), form_radius=frame.px(0.25), casts=False)]


def sideburns(frame, color, lw, rng):
    out = []
    for s in (-1, 1):
        spine = geom.catmull_rom(np.array([(s * u, v) for u, v in SHORT_SIDEBURN]))
        out += make_clump(f'sideburn_{s}', frame, spine, SHORT_SIDEBURN_W, None, color, lw, Z['side'], None, rng=rng)
    return out


def bun(frame, hair, color, lw, far_side, pal, z=Z['back'] + 0.5, cy=-0.30):
    """Twisted bun on the back of the head, seen past the head on the side opposite the face
    (far_side 0: seen from behind, in the middle of the head)."""
    cx, rx, ry = -far_side * 0.40, 0.27, 0.24
    shape = frame.map(geom.ellipse(cx, cy, rx, ry, 64, rot=-far_side * 0.4), z=None)
    strands = []
    for k in range(4):                                       # spiral strands of the twist
        a0 = k * np.pi / 2
        t = np.linspace(0, 1, 30)
        ang = a0 + t * 2.4
        rad = (0.25 + 0.75 * t)
        pts = np.stack([cx + np.cos(ang) * rx * rad * 0.92, cy + np.sin(ang) * ry * rad * 0.92], axis=1)
        path = geom.resample(frame.map(pts, z=None), 30)
        strands.append(geom.stroke_polygon(path, lw * 0.55 * geom.taper(30, 0.3, 0.3)))
    sheen = frame.map(geom.ellipse(cx + far_side * 0.05, cy - 0.08, rx * 0.55, ry * 0.25, 32), z=None)
    return [Drawable('hair_bun', 'hair', z, fill=[shape], color=color,
                     strokes=[geom.stroke_polygon(np.vstack([shape, shape[:1]]), lw * 1.1)],
                     line_color=line_color(color), form_radius=frame.px(0.18), casts=False),
            Drawable('hair_bun_strands', 'hair', z + 0.01, fill=None, strokes=strands, clip=['hair_bun'],
                     line_color=line_color(color)),
            Drawable('bun_sheen', 'hair', 0, fill=[sheen], kind='highlight', hl_color=pal['hair_highlight'],
                     opacity=0.8, clip_vis=['hair_bun'], feather=frame.px(0.01))]


def face_wisps(frame, color, lw, rng):
    """Two loose strands in front of the ears that soften an updo."""
    out = []
    for s in (-1, 1):
        pts = [(s * 0.44, -0.20), (s * 0.50, 0.05), (s * 0.49, 0.28), (s * 0.45, 0.46)]
        spine = geom.catmull_rom(np.array(pts))
        out += make_clump(f'wisp_{s}', frame, spine, 0.035, None, color, lw * 0.8, Z['wisp'], None, detail=False)
    return out


def skull_proxy(frame, vol):
    return [frame.map(geom.ellipse(0, -0.02, 0.5 + vol, 0.52 + vol + SKULL_RY_EXTRA, 72), z=None)]


def cap(frame, hair, color, lw, proxy):
    vol = hair['volume']
    rx, ry = 0.5 + vol, 0.52 + vol
    arc = frame.map(np.array([(rx * np.cos(a), -0.02 - ry * np.sin(a)) for a in np.linspace(-0.12, np.pi + 0.12, 25)]), z=None)
    hairline = map_spine(frame, HAIRLINE_UV, 'surface')
    poly = np.vstack([geom.catmull_rom(arc), geom.catmull_rom(hairline)])
    outer = geom.catmull_rom(arc)
    stroke = geom.stroke_polygon(outer, lw * 1.2 * geom.taper(len(outer), 0.08, 0.08, 0.3))
    return [Drawable('hair_cap', 'hair', Z['cap'], fill=[poly], color=color, strokes=[stroke],
                     line_color=line_color(color), form_radius=frame.px(0.35), form_poly=proxy)]


def bang_layout(hair):
    """Root/tip/bend for each bang clump, generated from the bang style."""
    style, part, n = hair['bangs'], hair['part'], hair['bang_count']
    length = hair['bang_length']
    if n < MIN_BANGS:
        raise ValueError(f"hair.bang_count must be >= {MIN_BANGS} (got {n})")
    layout = []
    sweep = 1.0 if part <= 0 else -1.0          # sweep away from the part
    for i in range(n):
        a = i / (n - 1)
        tip_u = -0.48 + 0.98 * a
        if style == 'swept':
            far = (a if sweep > 0 else 1 - a)
            tip_v = -0.12 + (length + 0.12) * far ** 1.3 + (0.10 if far > 0.92 else 0.0)
            root_u = part + (tip_u - part) * 0.28
            root_v = -0.44 + 0.03 * abs(tip_u - part)
            bend, curl = 0.12, -0.05
        elif style == 'parted':
            off = abs(2 * a - 1)
            # curtain: short at the part, kept above the eyes, only the outermost locks fall to the cheeks
            tip_v = length - 0.14 + 0.06 * off + (0.32 if off > 0.85 else 0.0)
            root_u = part + np.sign(tip_u - part) * 0.02 + (tip_u - part) * 0.2
            root_v = -0.45
            bend, curl = 0.14 * off, -0.02
        elif style == 'blunt':
            tip_v = length
            root_u = tip_u * 0.65
            root_v = -0.42
            bend, curl = 0.03, 0.0
        elif style == 'slicked':                 # combed back: from just inside the hairline up toward the crown
            root_u = -0.42 + 0.84 * a
            root_v = float(np.interp(root_u, HAIRLINE_UV[:, 0], HAIRLINE_UV[:, 1])) - SLICK_INSET
            tip_u, tip_v = root_u * 0.55, SLICK_TIP_V
            bend, curl = 0.04, 0.0
        else:
            raise ValueError(f"unknown bangs style '{style}' (use swept, parted, blunt, slicked)")
        layout.append(dict(root=(root_u, root_v), tip=(tip_u, tip_v), bend=bend, curl=curl))
    return layout


def bangs(frame, hair, color, lw, proxy, rng, pal):
    out = []
    layout = bang_layout(hair)
    width = 0.97 / (hair['bang_count'] - 1) * (SLICK_WIDTH if hair['bangs'] == 'slicked' else 1.55)
    part = hair['part']
    for i, b in enumerate(layout):
        w = width * rng.uniform(0.85, 1.15)
        tip = np.asarray(b['tip']) + [rng.uniform(-0.02, 0.02), rng.uniform(-0.035, 0.035)]
        spine = spine_from_ends(b['root'], tip, b['bend'] * rng.uniform(0.7, 1.3), b['curl'])
        z = Z['bangs'] + 0.5 - abs(b['tip'][0] - part) * 0.4 + rng.uniform(0, 0.02)
        out += make_clump(f'bang_{i}', frame, spine, w, 'surface', color, lw * 0.95, z, None, proxy, rng=rng)
        out += clump_highlight(f'bang_{i}', frame, spine, w, pal)
    return out


def lock_points(fixed, tail):
    """A lock's spine: its fixed shape above the tail, then the tail. A short side length would
    otherwise put the tail above the lower fixed points and the spine would fold back up."""
    top = min(v for _, v in tail)
    return [p for p in fixed if p[1] < top - LOCK_GAP] + tail


def side_locks(frame, hair, color, lw, side, rng, prefix='side'):
    """Locks on an untucked side fall in front of the shoulder."""
    out = []
    s = side
    end = hair['side_length']
    locks = [
        (lock_points([(0.42, -0.30), (0.535, 0.08), (0.56, 0.50), (0.60, 0.95)], [(0.585, end - 0.20), (0.55, end)]),
         0.17, Z['side']),
        (lock_points([(0.36, -0.28), (0.47, 0.08), (0.475, 0.42), (0.50, 0.80)], [(0.48, end - 0.45)]),
         0.11, Z['side'] + 0.1),
        ([(0.30, -0.24), (0.41, 0.10), (0.425, 0.40), (0.45, 0.66)], 0.04, Z['wisp']),
    ]
    for i, (pts, w, z) in enumerate(locks):
        spine = geom.catmull_rom(np.array([(s * u, v) for u, v in pts]))
        out += make_clump(f'{prefix}_{i}', frame, spine, w, None, color, lw, z, None, proxy=None, rng=rng)
    return out


def tucked_locks(frame, hair, color, lw, near_side, rng):
    out = []
    s = near_side
    end = hair['side_length'] - 0.25
    pts_list = [
        (lock_points([(-0.36, -0.32), (-0.50, -0.12), (-0.585, 0.05), (-0.62, 0.32), (-0.645, 0.75)], [(-0.66, end)]), 0.15),
        ([(-0.30, -0.36), (-0.47, -0.17), (-0.57, 0.0), (-0.60, 0.30), (-0.61, 0.60)], 0.10),
    ]
    for i, (pts, w) in enumerate(pts_list):
        spine = geom.catmull_rom(np.array([(-s * u, v) for u, v in pts]))
        out += make_clump(f'tucked_{i}', frame, spine, w, None, color, lw, Z['tucked'] + 0.01 * i, None, rng=rng)
    wisp = geom.catmull_rom(np.array([(-s * u, v) for u, v in [(-0.40, -0.26), (-0.465, -0.02), (-0.475, 0.20), (-0.455, 0.36)]]))
    out += make_clump('wisp_front', frame, wisp, 0.03, None, color, lw * 0.8, Z['wisp'], None, detail=False)
    return out


def ring_v(u):
    """Height of the angel ring: a band around the skull that droops toward the sides."""
    return -0.24 + 0.16 * (np.asarray(u) / 0.58) ** 2


def clump_highlight(name, frame, spine_uv, width, pal, depth='surface', band=(-0.035, 0.045)):
    """Short tapered sheen on one clump where it crosses the ring band (broken anime ring)."""
    dv = spine_uv[:, 1] - ring_v(spine_uv[:, 0])
    idx = np.nonzero((dv > band[0]) & (dv < band[1]))[0]
    if len(idx) < 3:
        return []
    seg = map_spine(frame, spine_uv[idx[0]:idx[-1] + 1], depth)
    seg = geom.resample(seg, 16)
    poly = geom.stroke_polygon(seg, frame.px(width) * 0.42 * geom.taper(16, 0.45, 0.45))
    return [Drawable(name + '_sheen', 'hair', 0, fill=[poly], kind='highlight', hl_color=pal['hair_highlight'],
                     opacity=0.9, clip_vis=[name], fill_mode='union')]


def cap_ring(frame, pal):
    """Thin arc of the ring on the visible crown, clipped to the cap."""
    us = np.linspace(-0.55, 0.55, 30)
    top = np.stack([us, ring_v(us) - 0.020], axis=1)
    bottom = np.stack([us, ring_v(us) + 0.010 + 0.03 * (np.arange(30) % 2)], axis=1)
    poly = map_spine(frame, np.vstack([top, bottom[::-1]]), 'surface')
    return [Drawable('cap_ring', 'hair', 0, fill=[poly], kind='highlight', hl_color=pal['hair_highlight'],
                     opacity=0.8, clip_vis=['hair_cap'], feather=frame.px(0.002))]


def side_highlights(frame, far_side, pal):
    s = far_side
    pts = [(0.53, 0.18), (0.55, 0.30), (0.57, 0.44)]
    spine = map_spine(frame, np.array([(s * u, v) for u, v in pts]), None)
    poly = geom.stroke_polygon(geom.resample(geom.catmull_rom(spine), 20), frame.px(0.05) * geom.taper(20, 0.4, 0.4))
    return [Drawable('side_ring', 'hair', 0, fill=[poly], kind='highlight', hl_color=pal['hair_highlight'],
                     opacity=0.8, clip_vis=['side_0', 'side_1'], feather=frame.px(0.002), fill_mode='union')]


SLICK_INSET, SLICK_TIP_V = 0.09, -0.50     # slicked-back clumps: from inside the hairline up to the crown
SLICK_WIDTH = 0.85            # (of the bang spacing) combed-back clumps are narrow: their roots stay in the cap
HAIRLINE_UV = np.array([(-0.47, 0.0), (-0.43, -0.20), (-0.25, -0.34), (0.0, -0.38), (0.25, -0.34), (0.43, -0.20),
                        (0.47, 0.0)])     # where the cap meets the forehead (head units)
# Named looks over the three hair builders: (builder, field overrides). They keep the spec's color and seed.
HAIR_PRESETS = {
    'side_part': ('short', dict(bangs='swept', part=-0.32, bang_length=0.0, bang_count=6, volume=0.07)),
    'slicked': ('short', dict(bangs='slicked', part=0.0, bang_count=7, volume=0.06, bang_length=0.0)),
    'two_block': ('short', dict(bangs='parted', part=0.02, bang_length=0.13, bang_count=8, volume=0.10,
                                undercut=True)),
    'medium': ('long', dict(length=1.05, side_length=0.78, volume=0.07, tuck='none', bangs='swept', bang_length=0.06)),
    'bob': ('long', dict(length=0.95, side_length=0.62, volume=0.09, tuck='none', bangs='blunt', bang_length=0.04)),
    'ponytail': ('updo', dict(tail=True, volume=0.05)),
    'hime': ('long', dict(length=2.6, side_length=0.62, volume=0.06, tuck='none', bangs='blunt', bang_length=0.08)),
    'center_part': ('long', dict(bangs='parted', part=0.0, bang_length=0.14, tuck='none')),
    'shoulder': ('long', dict(length=1.35, side_length=1.15, volume=0.07, tuck='far', bangs='parted', part=0.04,
                              bang_length=0.12)),
    'crop': ('short', dict(bangs='blunt', part=0.0, bang_length=0.0, bang_count=9, volume=0.05)),
}
TAIL_LENGTH = 1.55            # head widths a ponytail hangs below its tie
LOCK_GAP = 0.12               # head widths: a lock's fixed points stop this far above its tail
AWAY_Z = 6.0                  # back of the head: the hair is the front-most part of the head
BACK_OVER_Z = 3.0             # a figure turned away: hanging hair lies over the back, behind the face
HAIR_BACK_SHIFT = 0.22        # head widths the hanging hair moves toward the back of a turned body
AWAY_STRANDS = 7


def away_long_mass(frame, hair, color, lw, z=AWAY_Z, shift=0.0):
    """Long hair from behind: the crown and the fall, its lower edge hidden under the clump tips."""
    vol, length = hair['volume'], hair['length']
    rx, ry = 0.5 + vol * 1.4, 0.52 + vol * 1.4
    top = [(rx * np.cos(a), -0.02 - ry * np.sin(a)) for a in np.linspace(0, np.pi, 13)]
    low = min(1.35, length - 0.2)
    right = [(rx + 0.10, low), (rx + 0.08, 0.85), (rx + 0.04, 0.35)]
    left = [(-rx - 0.04, 0.35), (-rx - 0.08, 0.85), (-rx - 0.10, low)]
    hem = [(-rx - 0.06, length - 0.30), (-0.25, length - 0.20), (0.25, length - 0.20), (rx + 0.06, length - 0.30)]
    ring = np.array(right + top[1:-1] + left + hem)
    ring[:, 0] += shift * np.clip((ring[:, 1] - 0.2) / 0.8, 0, 1)   # the crown stays, the fall moves with the back
    poly = geom.catmull_rom(frame.map(ring, z=None), closed=True)
    outer = geom.catmull_rom(frame.map(ring[:len(right) + len(top) - 2 + len(left)], z=None))
    stroke = geom.stroke_polygon(outer, lw * 1.2 * geom.taper(len(outer), 0.05, 0.05, 0.3))
    return [Drawable('hair_back', 'hair', z, fill=[poly], color=color, strokes=[stroke],
                     line_color=line_color(color), form_radius=frame.px(0.25), casts=False)]


def long_fall(frame, hair, color, lw, rng, z, shift=0.0):
    """Long hair falling down a back that faces the viewer: a mass plus clumps (smooth, pointed ends)."""
    rx = 0.5 + hair['volume']
    out = away_long_mass(frame, hair, color, lw, z, shift)
    n = AWAY_STRANDS
    for i in range(n):
        a = i / (n - 1) * 2 - 1
        root = (a * rx * 0.55, -0.38 + 0.12 * a * a)
        tip = (a * rx * (1.10 + hair['volume']) + rng.uniform(-0.03, 0.03) + shift,
               hair['length'] - rng.uniform(0.0, 0.14) - 0.06 * abs(a))
        spine = spine_from_ends(root, tip, 0.03 * np.sign(a), -0.02)
        out += make_clump(f'away_{i}', frame, spine, 0.26 * rng.uniform(0.85, 1.15), None, color, lw * 0.9,
                          z + 0.1 + 0.01 * (n - abs(i - n // 2)), None, rng=rng)
    return out, ['hair_back'] + [f'away_{i}' for i in range(n)]


def back_view_hair(frame, hair, pal, lw, rng):
    """The head seen from behind: the hair mass in front, clumps for its fall, the crown sheen."""
    hair = resolve_style(hair)
    base = pal['hair']
    style = hair.get('style', 'long')
    rx = 0.5 + hair['volume']
    if style == 'long':
        out, names = long_fall(frame, hair, base, lw, rng, AWAY_Z)
    else:                                                 # short or swept up: strand lines show the lay of the hair
        if style == 'short':
            out = short_mass(frame, hair, base, lw, AWAY_Z)
            whorl, ends = (0.06, -0.30), [(a * rx * 0.85, SHORT_NAPE_Y - 0.02 - 0.10 * a * a) for a in np.linspace(-1, 1, 7)]
        else:
            out = updo_mass(frame, hair, base, lw, AWAY_Z)
            if hair.get('tail'):                                   # the tail hangs down the middle of the back
                spine = geom.catmull_rom(np.array([(0.0, -0.20), (0.04, 0.30), (0.02, 0.9), (0.0, TAIL_LENGTH)]))
                out += make_clump('tail', frame, spine, 0.30, None, darken(base, 0.9), lw, AWAY_Z + 0.5, None, rng=rng)
            else:
                out += bun(frame, hair, darken(base, 0.9), lw, 0, pal, z=AWAY_Z + 0.5, cy=-0.12)
            whorl, ends = (0.0, -0.12), [(a * rx * 0.80, 0.36 - 0.10 * a * a) for a in np.linspace(-1, 1, 7)]
        lines = []
        for k, e in enumerate(ends):
            mid = ((whorl[0] + e[0]) / 2 * 1.15, (whorl[1] + e[1]) / 2)
            path = geom.resample(geom.catmull_rom(frame.map(np.array([whorl, mid, e]), z=None)), 24)
            lines.append(geom.stroke_polygon(path, lw * 0.5 * geom.taper(24, 0.6, 0.3)))
        out.append(Drawable('away_strands', 'hair', AWAY_Z + 0.05, fill=None, strokes=lines, clip=['hair_back'],
                            line_color=line_color(base)))
        names = ['hair_back']
    us = np.linspace(-0.5, 0.5, 30)                        # crown sheen: the broken anime ring
    top = np.stack([us, ring_v(us) - 0.025], axis=1)
    bottom = np.stack([us, ring_v(us) + 0.005 + 0.025 * (np.arange(30) % 2)], axis=1)
    poly = frame.map(np.vstack([top, bottom[::-1]]), z=None)
    out.append(Drawable('away_ring', 'hair', 0, fill=[poly], kind='highlight', hl_color=pal['hair_highlight'],
                        opacity=0.6, clip_vis=names, feather=frame.px(0.004)))
    return out


def resolve_style(hair):
    """Hair fields with a named look (HAIR_PRESETS) expanded onto its builder."""
    style = hair.get('style', 'long')
    if style in HAIR_PRESETS:
        base, fields = HAIR_PRESETS[style]
        return dict(hair, **fields, style=base, look=style)
    return hair


def ponytail(frame, hair, color, lw, far_side, rng, z):
    """A tail tied at the back of the head, hanging past the head on the side opposite the face."""
    s = far_side if far_side else 1
    root = (s * 0.30, -0.28)
    pts = [root, (s * 0.52, 0.10), (s * 0.60, 0.60), (s * 0.56, 0.60 + TAIL_LENGTH * 0.6), (s * 0.48, -0.28 + TAIL_LENGTH + 0.3)]
    spine = geom.catmull_rom(np.array(pts))
    out = make_clump('tail', frame, spine, 0.30, None, color, lw, z, None, rng=rng)
    tie = frame.map(geom.ellipse(root[0], root[1] + 0.02, 0.07, 0.05, 24), z=None)
    out.append(Drawable('tail_tie', 'hair', z + 0.01, fill=[tie], color=darken(color, 0.6), casts=False))
    return out


def build_hair(frame, hair, pal, lw, rng, view=None):
    """view: (look, turn) of a turned clothed figure; look 'away' draws the back of the head."""
    hair = resolve_style(hair)
    look, turn = view or ('face', 0.0)
    if look == 'away':
        return back_view_hair(frame, hair, pal, lw, rng)
    back_z = BACK_OVER_Z if abs(turn) > np.pi / 2 else Z['back']
    shift = -np.sin(turn) * HAIR_BACK_SHIFT
    base = pal['hair']
    proxy = skull_proxy(frame, hair['volume'])
    far_side = 1 if frame.yaw >= 0 else -1
    tuck = hair['tuck']
    tuck_side = {'near': -far_side, 'far': far_side, 'none': 0}[tuck]
    style = hair.get('style', 'long')
    if style not in ('long', 'updo', 'short'):
        raise ValueError(f"unknown hair style '{style}' (use long, updo, short)")
    if style == 'short':
        out = short_mass(frame, hair, darken(base, 0.72), lw)
        out += cap(frame, hair, base, lw, proxy)
        if not hair.get('undercut'):                      # a two-block cut leaves the sides close-cropped
            out += sideburns(frame, base, lw, rng)
        out += bangs(frame, hair, base, lw, proxy, rng, pal)
        return out + cap_ring(frame, pal)
    if style == 'updo':
        out = updo_mass(frame, hair, darken(base, 0.72), lw)
        if hair.get('tail'):
            out += ponytail(frame, hair, darken(base, 0.9), lw, far_side, rng, Z['back'] + 0.5)
        else:
            out += bun(frame, hair, darken(base, 0.9), lw, far_side, pal)
        out += cap(frame, hair, base, lw, proxy)
        out += bangs(frame, hair, base, lw, proxy, rng, pal)
        out += face_wisps(frame, base, lw, rng)
        return out + cap_ring(frame, pal)
    if abs(turn) > np.pi / 2:                 # the back faces the viewer: the fall of the hair lies over it
        out = long_fall(frame, hair, darken(base, 0.85), lw, rng, back_z, shift)[0]
    else:
        out = back_mass(frame, hair, darken(base, 0.72), lw, back_z, shift)
    out += cap(frame, hair, base, lw, proxy)
    out += bangs(frame, hair, base, lw, proxy, rng, pal)
    open_side = -tuck_side if tuck_side else far_side
    out += side_locks(frame, hair, base, lw, open_side, rng)
    if tuck_side:
        out += tucked_locks(frame, hair, darken(base, 0.85), lw, tuck_side, rng)
    else:
        out += side_locks(frame, hair, base, lw, -open_side, rng, prefix='side_m')
    out += cap_ring(frame, pal)
    out += side_highlights(frame, open_side, pal)
    return out
