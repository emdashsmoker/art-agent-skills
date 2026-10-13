"""Doomer series: winter nights among panel blocks, seven pictures in the seven styles.

  man         anime       a man in a hoodie and a beanie under a sodium lamp, snow falling, a cigarette
  woman       illust      a woman in a hoodie in a tiled underpass under fluorescent tubes, wired earphones
  pair        watercolor  two people waiting at a bus stop at night in the snow
  sheet       poster      the man as a character sheet: four views, head-height guides, color chips
  district    painterly   a panel-block district at night: lamps down a snowy road, lit windows
  field       pencil      power pylons across a snowy field at night, far blocks, one walker
  still_life  neon        a kitchen windowsill at night: ashtray and cigarette, pack, mug, cassette player, cup noodle

Everything new here (the hoodie, the beanie, a cigarette, falling snow, panel blocks, sodium lamps, pylons, a bus
stop, an underpass, the windowsill things) is drafted in this file from engine parts; the engine is not changed.
Every builder takes the style as its argument.
Run:  python doomer.py [out_dir]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from codepaint import Scene, Part, Line, Stroke, save, get_style, review, ellipse, catmull_rom, Ribbon, mix  # noqa: E402
from codepaint import vertical_gradient, fbm, offset_polygon  # noqa: E402
from codepaint.subjects import garments, pair, profile  # noqa: E402
from codepaint.subjects import objects as ob  # noqa: E402
from codepaint.subjects import stage as st  # noqa: E402
from codepaint.subjects.figure import Figure, FigureSpec, POSES  # noqa: E402

WIDTH, HEIGHT = 1500, 1000
NIGHT_LIGHT = (-0.35, -0.80, 0.48)             # a street lamp above and to the left
SODIUM = "#ffa64a"                             # the one warm color of the series
SNOW = "#c9d2e4"
SKY = [(0.0, "#070a16"), (0.55, "#1a1d33"), (0.85, "#3a2f40"), (1.0, "#5a4048")]   # orange haze at the horizon
FLOOR_M = 2.8                                  # storey height of a panel block
HAIR_M = dict(hair="#1d1a1c", iris="#4a4038", seed=3)
HAIR_F = dict(hair_style="bob", bangs="full", hair="#141216", iris="#3e3a3a", seed=9, eye_size=0.95, jaw=0.95,
              lip_alpha=0.55, eyeshadow=0.45)
MAN = FigureSpec(cx=0, top=0, unit=100, sex="male", skin="#e8c3a6", legs=1.03, outfit="dressed", upper="hoodie",
                 lower="jeans", cloth="#26272d", cloth2="#343b4a", shoes="sneakers", cloth3="#d9d6cf", head=HAIR_M,
                 ident="man")
WOMAN = FigureSpec(cx=0, top=0, unit=100, skin="#f1d6c6", bust=1.02, waist=0.96, legs=1.04, outfit="dressed",
                   upper="hoodie", lower="long_skirt", cloth="#3a3b44", cloth2="#17171c", shoes="boots",
                   cloth3="#1a1a1e", head=HAIR_F, ident="woman")

# a loose hooded top, registered next to the four tops of garments.py (a cut table entry, no engine change)
garments.TOP_CUT.setdefault("hoodie", dict(neck="crew", hem=0.10, ease=0.075, sleeve=1.95, s_scale=1.24, s_add=0.05,
                                           tucked=False))
if "hoodie" not in garments.TOPS:
    garments.TOPS = garments.TOPS + ("hoodie",)


# ---- the figure: pose, hood, pocket, beanie, scarf, cigarette ----------------------------------------
def pocket_pose(spec, pose):
    """Both hands in the front pocket of a hoodie: each wrist is solved onto the pocket's side opening."""
    pose = replace(pose, left_hand="hidden", right_hand="hidden", left_arm_front=True, right_arm_front=True)
    fig = Figure(spec, pose)
    for _ in range(3):                                   # the shoulders move a little with the arms: settle
        p, u = fig.joint("pelvis"), fig.u
        shift = fig.p.turn * 0.12 * u
        for side, sd in (("left", -1), ("right", 1)):
            upper, fore = pair.reach(fig, side, p + [shift + sd * 0.30 * u, -0.40 * u], elbow="out")
            pose = replace(pose, **{f"{side}_upper_arm": upper, f"{side}_forearm": fore})
        fig = Figure(spec, pose)
    return pose


def _cloth_line(color, width=1.6):
    return Line(width, color=mix(color, "#0a0a10", 0.6))


def hoodie_parts(fig, color, strings="#d9d6cf"):
    """Overlays for Figure.parts(): the hood lying around the neck and the front pocket (front view), the hood on
    the upper back (back view) or behind the neck (profile)."""
    u, c, name = fig.u, fig.joint("neck"), fig.s.ident + "_hood"
    neck = f"{fig.s.ident}/neck" if fig.s.ident else "neck"
    dark = mix(color, "#000000", 0.12)
    px = u / 100.0
    if fig.side:
        f = fig.fc
        mass = catmull_rom(np.array([c + [f * 0.20 * u, 0.10 * u], c + [-f * 0.10 * u, 0.02 * u], c + [-f * 0.38 * u, -0.10 * u],
                                     c + [-f * 0.50 * u, 0.12 * u], c + [-f * 0.42 * u, 0.46 * u], c + [-f * 0.20 * u, 0.40 * u],
                                     c + [f * 0.05 * u, 0.26 * u], c + [f * 0.22 * u, 0.20 * u]]), samples=6, closed=True)
        return [Part(name, dark, polys=[mass], material="cloth", bulge=1.3, under=[neck], line=_cloth_line(color, 1.6 * px))]
    if fig.back:
        top = c + [0, -0.02 * u]
        mass = catmull_rom(np.array([top + [-0.46 * u, 0.04 * u], top + [-0.22 * u, -0.10 * u], top + [0.22 * u, -0.10 * u],
                                     top + [0.46 * u, 0.04 * u], top + [0.30 * u, 0.55 * u], top + [0.0, 0.95 * u],
                                     top + [-0.30 * u, 0.55 * u]]), samples=6, closed=True)
        seam = Stroke(np.array([top + [0, -0.05 * u], top + [0, 0.90 * u]]), width=1.2 * px, color=mix(color, "#000000", 0.5),
                      alpha=0.6, taper=(False, True), clip=True)
        return [Part(name, dark, polys=[mass], material="cloth", bulge=1.1, line=_cloth_line(color, 1.6 * px), strokes=[seam])]
    s = fig.p.turn * 0.10 * u                              # three-quarter: the ring shifts toward the far side
    ring = catmull_rom(np.array([c + [s, 0.40 * u], c + [s - 0.34 * u, 0.20 * u], c + [-0.58 * u, 0.06 * u],
                                 c + [-0.46 * u, -0.30 * u], c + [0, -0.52 * u], c + [0.46 * u, -0.30 * u],
                                 c + [0.58 * u, 0.06 * u], c + [s + 0.34 * u, 0.20 * u]]), samples=8, closed=True)
    hole = catmull_rom(np.array([c + [s, 0.22 * u], c + [s - 0.17 * u, 0.06 * u], c + [-0.20 * u, -0.30 * u],
                                 c + [0, -0.50 * u], c + [0.20 * u, -0.30 * u], c + [s + 0.17 * u, 0.06 * u]]), samples=8,
                       closed=True)
    knots = []
    for sd in (-1, 1):                                     # drawstrings from the opening down the chest
        a = c + [s + sd * 0.09 * u, 0.24 * u]
        b = a + [sd * 0.03 * u, 0.62 * u]
        knots.append(Stroke(catmull_rom(np.array([a, (a + b) / 2 + [sd * 0.02 * u, 0], b]), samples=6), width=2.0 * px,
                            color=strings, taper=(False, False)))
        knots.append(Stroke(np.array([b, b + [0, 0.07 * u]]), width=3.2 * px, color=mix(strings, "#000000", 0.25),
                            taper=(False, False)))
    inside = Part(name + "_inside", mix(color, "#000000", 0.45), polys=[hole], shade=False, material="flat", under=[neck])
    hood = Part(name, dark, polys=[ring], material="cloth", bulge=1.4, erase=[(hole, 0.0)], under=[neck],
                line=_cloth_line(color, 1.7 * px), strokes=knots)
    p = fig.joint("pelvis")
    x = p[0] + fig.p.turn * 0.12 * u
    pocket = np.array([[x - 0.30 * u, p[1] - 0.66 * u], [x + 0.30 * u, p[1] - 0.66 * u], [x + 0.52 * u, p[1] - 0.22 * u],
                       [x + 0.56 * u, p[1] - 0.02 * u], [x - 0.56 * u, p[1] - 0.02 * u], [x - 0.52 * u, p[1] - 0.22 * u]])
    seams = [Stroke(np.array([[x - 0.30 * u, p[1] - 0.66 * u], [x - 0.52 * u, p[1] - 0.22 * u]]), width=2.4 * px,
                    color=mix(color, "#000000", 0.55), alpha=0.8, taper=(False, False)),
             Stroke(np.array([[x + 0.30 * u, p[1] - 0.66 * u], [x + 0.52 * u, p[1] - 0.22 * u]]), width=2.4 * px,
                    color=mix(color, "#000000", 0.55), alpha=0.8, taper=(False, False))]
    pouch = Part(name + "_pocket", color, polys=[pocket], material="cloth", bulge=0.5, line=_cloth_line(color, 1.3 * px),
                 strokes=seams)
    return [inside, hood, pouch]


def beanie(fig, color="#2b2d33", cuff_v=0.205, bottom_v=0.31):
    """A knit watch cap over the skull, its turned-up cuff low on the forehead; bangs show below it."""
    head = fig._head()
    size = head.s.size
    name = (fig.s.ident or "fig") + "_beanie"
    px = size / 100.0
    if fig.side:
        path = profile._skull_path(head, 0.50)
        front = np.array([[0.42, bottom_v + 0.03]])
        local = np.vstack([front, path])
        outline = profile.Q(head, local, lift=np.full(len(local), 0.065))
        outline = np.vstack([outline, profile.Q(head, [[-0.38, 0.54]], lift=0.04)])
        dome = catmull_rom(outline, samples=4)
        band_pts = profile.Q(head, [[0.46, bottom_v - 0.08], [0.46, bottom_v + 0.05], [-0.48, 0.58], [-0.52, 0.45]])
        ribs = [Stroke(profile.Q(head, [[x, bottom_v - 0.09 + 0.25 * (0.4 - x) * 0.0], [x, bottom_v + 0.05]]),
                       width=1.0 * px, color=mix(color, "#000000", 0.45), alpha=0.5, taper=(False, False), clip=True)
                for x in np.linspace(-0.45, 0.42, 11)]
    else:
        right, left = head.skull_contour(v_end=bottom_v)
        dome = offset_polygon(np.vstack([right, left[::-1]]), 0.028 * size)
        band_pts = np.vstack([head.P(np.array([-0.7, 0.7]), np.array([cuff_v, cuff_v])),
                              head.P(np.array([0.7, -0.7]), np.array([bottom_v + 0.08, bottom_v + 0.08]))])
        us = np.linspace(-0.44, 0.44, 15)
        ribs = [Stroke(head.P(np.array([x, x]), np.array([cuff_v + 0.01, bottom_v + 0.02])), width=1.0 * px,
                       color=mix(color, "#000000", 0.45), alpha=0.5, taper=(False, False), clip=True) for x in us]
        ribs += [Stroke(head.P(np.array([x, x * 0.35]), np.array([cuff_v - 0.01, -0.02])), width=0.9 * px,
                        color=mix(color, "#000000", 0.4), alpha=0.25, taper=(False, True), clip=True) for x in us[1:-1:2]]
    cap = Part(name, color, polys=[dome], material="cloth", bulge=1.2, line=_cloth_line(color, 1.8 * px), strokes=ribs[11:])
    cuff = Part(name + "_cuff", mix(color, "#ffffff", 0.06), polys=[band_pts], material="cloth", clip=name, bulge=0.6,
                strokes=ribs[:11] if fig.side else ribs[:15], line=Line(1.4 * px, color=mix(color, "#000000", 0.6),
                                                                        paths=[band_pts[:2]] if not fig.side else None))
    return [cap, cuff]


def scarf(fig, color="#9c2f2f"):
    """A thick scarf wound round the neck with one end hanging down the chest (front view)."""
    u, c = fig.u, fig.joint("neck")
    px = u / 100.0
    neck = f"{fig.s.ident}/neck" if fig.s.ident else "neck"
    wrap = catmull_rom(np.array([c + [-0.40 * u, 0.06 * u], c + [-0.34 * u, -0.22 * u], c + [0, -0.30 * u],
                                 c + [0.34 * u, -0.22 * u], c + [0.40 * u, 0.06 * u], c + [0.10 * u, 0.20 * u],
                                 c + [-0.12 * u, 0.20 * u]]), samples=8, closed=True)
    tail = np.array([c + [-0.06 * u, 0.12 * u], c + [-0.30 * u, 0.12 * u], c + [-0.30 * u, 1.05 * u], c + [-0.08 * u, 1.02 * u]])
    fringe = [Stroke(np.array([c + [-x * u, 1.03 * u], c + [-x * u, 1.13 * u]]), width=1.6 * px, color=color, taper=(False, True))
              for x in np.linspace(0.10, 0.28, 6)]
    lines = [Stroke(np.array([c + [-0.36 * u, y * u], c + [0.36 * u, y * u]]), width=1.0 * px, color=mix(color, "#000000", 0.4),
                    alpha=0.5, taper=(True, True), clip=True) for y in (-0.10, 0.02)]
    return [Part(fig.s.ident + "_scarf_tail", mix(color, "#000000", 0.08), polys=[tail], material="cloth", bulge=0.5,
                 line=_cloth_line(color, 1.4 * px), strokes=fringe),
            Part(fig.s.ident + "_scarf", color, polys=[wrap], material="cloth", bulge=1.3, under=[neck],
                 line=_cloth_line(color, 1.6 * px), strokes=lines)]


def cigarette(start, direction, length, name, glow=0.8):
    """A lit cigarette from start (the lips or the fingers) along direction: filter, paper, ash, an ember with its glow
    and smoke curling up. Returns (parts in front of the face, smoke parts)."""
    d = np.asarray(direction, float) / np.linalg.norm(direction)
    end = start + d * length
    w = length * 0.085
    filt = start + d * length * 0.28
    parts = [Part(name + "_filter", "#c98f4a", ribbon=Ribbon(np.array([start, filt]), [(0, w), (1, w)], step=1.0),
                  material="matte", line=Line(0.8, color="#3a2a20")),
             Part(name + "_paper", "#efe9df", ribbon=Ribbon(np.array([filt, end - d * w * 1.2]), [(0, w), (1, w)], step=1.0),
                  material="matte", line=Line(0.8, color="#4a4440")),
             Part(name + "_ash", "#7a7470", ribbon=Ribbon(np.array([end - d * w * 1.2, end]), [(0, w), (1, w * 0.85)], step=1.0),
                  shade=False, material="flat")]
    glow_parts = [Part(name + "_ember", "#ff5a1e", polys=[ellipse(end[0], end[1], w * 0.9, w * 0.9, n=12)], shade=False,
                       material="flat", alpha=0.9),
                  Part(name + "_glow", "#ff8a3a", polys=[ellipse(end[0], end[1], w * 5, w * 5, n=16)], shade=False,
                       material="flat", blur=w * 2.5, alpha=0.55 * glow, blend="screen")]
    rng = np.random.default_rng(len(name))
    smoke = []
    for k in range(2):                                    # two ribbons of smoke drifting up and sideways
        t = np.linspace(0, 1, 14)
        sway = np.sin(t * (5 + 2 * k) + rng.uniform(0, 3)) * length * (0.15 + 0.35 * t)
        path = np.stack([end[0] + sway + t * length * (0.4 - 0.8 * k), end[1] - t * length * (3.2 + k)], 1)
        smoke.append(Part(f"{name}_smoke{k}", "#d8dce6", ribbon=Ribbon(path, [(0, w * 0.5), (0.5, w * 1.6), (1, w * 3.0)], step=2.0),
                          shade=False, material="flat", alpha=0.20, blur=w * 0.8, blend="screen"))
    return parts + glow_parts, smoke


def mouth_cigarette(fig, side=1.0):
    """A cigarette between the lips, hanging down at the corner of the mouth toward `side`."""
    head = fig._head()
    lips = head.P(0.05 * side, 0.83, lift=0.03)
    return cigarette(lips, (0.80 * side, 0.42), fig.u * 0.34, (fig.s.ident or "fig") + "_cig")


# ---- the night: sky, snow, ground, blocks, lamps, trees ---------------------------------------------
def night_sky(width, height, horizon, seed=1):
    """Dark sky with the orange haze of a lit city along the horizon and a few soft cloud bands."""
    h0 = horizon / height
    stops = [(0.0, SKY[0][1]), (h0 * 0.55, SKY[1][1]), (h0 * 0.88, SKY[2][1]), (h0, SKY[3][1]), (1.0, SKY[3][1])]
    img = vertical_gradient(height, width, stops)
    clouds = fbm(height, width, scale=width * 0.3, octaves=4, seed=seed, stretch=4.0)
    ys = np.arange(height, dtype=np.float32)[:, None] / height
    band = np.clip(1 - ys / max(h0, 1e-3), 0, 1)
    img = img * (1 + 0.18 * (clouds - 0.5)[..., None] * band[..., None])
    return np.clip(img, 0, 1).astype(np.float32)


def snowfall(width, height, count=900, near=120, seed=0, name="snow"):
    """Falling snow in two layers: many small sharp far flakes, fewer big soft near ones (draw last)."""
    rng = np.random.default_rng(seed)
    far = [ellipse(x, y, r, r, n=8) for x, y, r in zip(rng.uniform(0, width, count), rng.uniform(0, height, count),
                                                       rng.uniform(0.8, 2.2, count))]
    big = [ellipse(x, y, r, r, n=10) for x, y, r in zip(rng.uniform(0, width, near), rng.uniform(0, height, near),
                                                        rng.uniform(3.0, 7.5, near))]
    return [Part(name + "_far", "#f2f5fb", polys=far, shade=False, material="flat", alpha=0.85, receive=False),
            Part(name + "_near", "#f2f5fb", polys=big, shade=False, material="flat", alpha=0.55, blur=2.5, receive=False)]


def snow_ground(cam, path_width=0.0, seed=2):
    """Snow from the near edge to the horizon, bluish and darker far off; an optional trodden path to the
    vanishing point."""
    W, H, hz = cam.width, cam.height, cam.horizon
    ground = np.array([(0, hz), (W, hz), (W, H), (0, H)], float)
    parts = [st._flat("snowfield", SNOW, [ground], gradient=((0, hz), "#4a5068", (0, H), "#aeb8cc"))]
    if path_width > 0:
        zn = cam.near_z() * 0.98
        hw = path_width / 2
        path = cam.P([-hw, hw, hw * 0.7, -hw * 0.7], [0, 0, 0, 0], [zn, zn, 300.0, 300.0])
        parts.append(st._flat("slush", "#5d6170", [path], gradient=((0, hz), "#3a3e4c", (0, H), "#7a7f8e"), blur=3.0,
                              alpha=0.55))
    return parts


def panel_block(cam, name, x0, z0, w, floors, d=12.0, color="#59606e", lit=0.25, seed=0, bay=3.0):
    """A prefabricated panel block: the box, panel seams per storey and bay, a window per bay and storey on the
    faces we see (a share of them lit warm), entrance canopies with a lamp, snow along the roof."""
    rng = np.random.default_rng(seed)
    h = floors * FLOOR_M + 0.6
    parts = st.box(cam, name, x0, 0, z0, w, h, d, color)
    dark_win, lit_win, seams = [], [], []
    for f in range(floors):
        y = f * FLOOR_M + 0.95
        for bx in np.arange(x0 + 0.5, x0 + w - 1.4, bay):
            quad = cam.P([bx + 0.3, bx + 1.6, bx + 1.6, bx + 0.3], [y, y, y + 1.3, y + 1.3], [z0 - 0.01] * 4)
            (lit_win if rng.random() < lit else dark_win).append(quad)
    side_x = x0 if x0 > 0 else (x0 + w if x0 + w < 0 else None)
    if side_x is not None:                                           # the end wall we see
        for f in range(floors):
            y = f * FLOOR_M + 0.95
            for zz in np.arange(z0 + 1.5, z0 + d - 1.0, 4.0):
                quad = cam.P([side_x] * 4, [y, y, y + 1.3, y + 1.3], [zz, zz + 1.2, zz + 1.2, zz])
                (lit_win if rng.random() < lit * 0.6 else dark_win).append(quad)
    for f in range(1, floors + 1):                                   # panel joints: storeys and bays
        y = f * FLOOR_M + 0.2
        seams.append(Stroke(cam.P([x0, x0 + w], [y, y], [z0 - 0.01] * 2), width=0.8, color=mix(color, "#000000", 0.35),
                            alpha=0.5, taper=(False, False), feature=False))
    for bx in np.arange(x0 + bay, x0 + w - 0.5, bay):
        seams.append(Stroke(cam.P([bx, bx], [0.2, h - 0.4], [z0 - 0.01] * 2), width=0.7, color=mix(color, "#000000", 0.35),
                            alpha=0.35, taper=(False, False), feature=False))
    face = cam.P([x0, x0 + w, x0 + w, x0], [0, 0, h, h], [z0 - 0.01] * 4)
    parts.append(st._flat(name + "_seams", color, [face], alpha=0.0, strokes=seams))
    if dark_win:
        parts.append(st._flat(name + "_dark", mix(color, "#0c1020", 0.65), dark_win))
    if lit_win:
        warm = ("#ffc46a", "#ffd88f", "#f0a050", "#e8d9b0")
        for k in range(len(warm)):
            group = lit_win[k::len(warm)]
            if group:
                parts.append(st._flat(f"{name}_lit{k}", warm[k], group))
        parts.append(st._flat(name + "_glow", "#ffb860", lit_win, blur=max(1.0, 0.25 * cam.scale(z0)), alpha=0.22,
                              blend="screen"))
    roof = cam.P([x0 - 0.05, x0 + w + 0.05, x0 + w + 0.05, x0 - 0.05], [h - 0.05, h - 0.05, h + 0.25, h + 0.25], [z0 - 0.02] * 4)
    parts.append(st._flat(name + "_roofsnow", "#dfe5f0", [roof], blur=0.5))
    for k, bx in enumerate(np.arange(x0 + 0.5 + bay * 2, x0 + w - 2.0, bay * 4)):   # an entrance every fourth bay
        parts += st.box(cam, f"{name}_canopy{k}", bx - 0.3, 2.3, z0 - 1.0, 2.2, 0.15, 1.0, "#6a6f7a")
        door = cam.P([bx, bx + 1.6, bx + 1.6, bx], [0, 0, 2.2, 2.2], [z0 - 0.01] * 4)
        parts.append(st._flat(f"{name}_door{k}", "#3a3020", [door], line=st._ink(0.4)))
        c = cam.P(bx + 0.8, 2.15, z0 - 0.5)
        r = 0.25 * cam.scale(z0)
        parts.append(st._flat(f"{name}_doorlamp{k}", "#ffd08a", [ellipse(c[0], c[1], r * 4, r * 3)], blur=r * 1.5, alpha=0.5,
                              blend="screen"))
    return parts


def sodium_lamp(cam, name, x, z, height=6.5, arm=1.4, side=1.0, pool=True):
    """A street lamp: a pole, an arm over the road, a head throwing orange light and its pool on the snow."""
    s = cam.scale(z)
    pole = cam.P([x, x], [0, height], [z, z])
    tip = (x + side * arm, height + 0.2, z)
    arm_path = cam.P([x, x + side * arm * 0.5, tip[0]], [height - 0.2, height + 0.25, tip[1]], [z] * 3)
    head = cam.P(*tip)
    parts = []
    if pool:
        c = cam.P(tip[0], 0.0, z)
        parts.append(st._flat(name + "_pool", SODIUM, [ellipse(c[0], c[1], 2.6 * s, 0.6 * s)], blur=0.5 * s, alpha=0.32,
                              blend="screen"))
    parts += [Part(name + "_pole", "#2a2c33", ribbon=Ribbon(pole, [(0, 0.07 * s), (1, 0.05 * s)], step=3.0), material="gloss",
                   line=st._ink(0.6)),
              st._flat(name + "_arm", "#2a2c33", [arm_path[:1]], alpha=0.0,
                       strokes=[Stroke(catmull_rom(arm_path, samples=6), width=max(1.0, 0.06 * s), color="#2a2c33",
                                       taper=(False, True))]),
              st._flat(name + "_head", "#3a3c44", [ellipse(head[0], head[1], 0.30 * s, 0.10 * s)], line=st._ink(0.5)),
              st._flat(name + "_bulb", "#ffe2b0", [ellipse(head[0], head[1] + 0.08 * s, 0.20 * s, 0.05 * s)]),
              st._flat(name + "_halo", SODIUM, [ellipse(head[0], head[1] + 0.15 * s, 0.7 * s, 0.6 * s)], blur=0.3 * s,
                       alpha=0.40, blend="screen")]
    return parts


def bare_tree(cam, name, x, z, height=7.0, color="#2a2a30", seed=0):
    """A leafless tree: a trunk forking into branches, then twigs, all thinning toward the tips."""
    rng = np.random.default_rng(seed)
    s = cam.scale(z)
    parts = []

    def grow(base, angle, length, width, depth):
        pts = [base]
        for k in range(4):
            angle += rng.uniform(-0.18, 0.18)
            pts.append(pts[-1] + np.array([np.sin(angle), np.cos(angle)]) * length / 4)
        pts = np.array(pts)
        axis = catmull_rom(cam.P(pts[:, 0], pts[:, 1], np.full(len(pts), z)), samples=5)
        if depth == 0:
            parts.append(st._flat(f"{name}_twig", color, [axis[:1]], alpha=0.0,
                                  strokes=[Stroke(axis, width=max(0.6, width * s), color=color, alpha=0.8, taper=(False, True))]))
            return
        parts.append(Part(f"{name}_b{depth}", color, ribbon=Ribbon(axis, [(0, width * s), (1, width * 0.55 * s)], step=2.0),
                          material="matte", line=st._ink(0.4)))
        for k in range(2 if depth > 1 else 3):
            t = rng.uniform(0.45, 0.95)
            fork = pts[0] + (pts[-1] - pts[0]) * t
            grow(fork, angle + rng.choice([-1, 1]) * rng.uniform(0.35, 0.8), length * rng.uniform(0.5, 0.7), width * 0.55,
                 depth - 1)
    grow(np.array([x, 0.0]), rng.uniform(-0.08, 0.08), height * 0.55, 0.16, 3)
    return parts


def figure_light(cam, fig, z, color=SODIUM, strength=0.30):
    """Warm lamp light falling on the snow around a figure's feet (under the figure)."""
    feet = (fig.joint("ankle_left") + fig.joint("ankle_right")) / 2
    y = cam.floor_y(z)
    s = cam.scale(z)
    return st._flat("lamp_pool_" + fig.s.ident, color, [ellipse(feet[0], y, 1.6 * s, 0.35 * s)], blur=0.3 * s,
                    alpha=strength, blend="screen")


# ---- 1. the man ---------------------------------------------------------------------------------------
STAND_M = replace(POSES["standing"], turn=-0.18, head_yaw=-14.0, head_tilt=-3.0, pelvis_tilt=-3.0, chest_tilt=2.0,
                  left_foot_turn=14.0, right_foot_turn=10.0)


def _dressed(spec, pose, cam, x, z):
    """A figure in a hoodie with both hands in its pocket, standing at (x, z)."""
    pose = pocket_pose(cam.fit(spec, pose, x, z), pose)
    return Figure(cam.fit(spec, pose, x, z), pose)


def man(style="anime"):
    """Night, snow, a sodium lamp: a man in a hoodie and a beanie, hands in the pocket, a cigarette in his mouth;
    panel blocks across the courtyard behind him."""
    cam = st.Camera(WIDTH, HEIGHT, horizon=HEIGHT * 0.50, eye=1.15)
    scene = Scene(WIDTH, HEIGHT, light=NIGHT_LIGHT, seed=11)
    scene.set_background(night_sky(WIDTH, HEIGHT, cam.horizon))
    back = snow_ground(cam, path_width=2.0)
    back += panel_block(cam, "far_block", -70, 150, 64, 12, color="#3a3f4c", lit=0.2, seed=1)
    back += panel_block(cam, "far_block2", 10, 170, 70, 16, color="#363b48", lit=0.18, seed=5)
    back += panel_block(cam, "block_l", -52, 70, 36, 9, color="#424857", lit=0.26, seed=2)
    back += panel_block(cam, "block_r", 9, 62, 40, 9, color="#3f4554", lit=0.3, seed=3)
    for k, (tx, tz) in enumerate(((-9, 24), (-4.5, 17), (5.5, 20), (11, 28), (-14, 34))):
        back += bare_tree(cam, f"tree{k}", tx, tz, height=7.5, seed=k + 3)
    back += sodium_lamp(cam, "lamp_far", 3.2, 16.0, side=-1.0)
    back += sodium_lamp(cam, "lamp", -2.3, 4.6, side=1.0)
    x, z = 0.75, 2.4
    fig = _dressed(MAN, STAND_M, cam, x, z)
    smoke_front, smoke = mouth_cigarette(fig, side=-1.0)
    scene.add(back, figure_light(cam, fig, z, strength=0.4), fig.parts(overlays=hoodie_parts(fig, MAN.cloth)),
              beanie(fig), smoke_front, smoke, snowfall(WIDTH, HEIGHT, seed=4))
    return scene.render(style)


# ---- 2. the woman ---------------------------------------------------------------------------------------
def _wall_strokes(cam, sx, zn, zb, y0, y1, step_y, step_z, color, alpha=0.5, width=1.0):
    """Tile joints on a side wall (x = sx): courses along the tunnel and joints across it, both in perspective."""
    lines = [Stroke(cam.P([sx, sx], [y, y], [zn, zb]), width=width, color=color, alpha=alpha, taper=(False, False),
                    feature=False) for y in np.arange(y0, y1, step_y)]
    lines += [Stroke(cam.P([sx, sx], [y0, y1], [z, z]), width=width, color=color, alpha=alpha * 0.8, taper=(False, False),
                     feature=False) for z in np.arange(zn + step_z, zb, step_z)]
    return lines


def _tag(cam, sx, z, y, size, color, seed):
    """A spray-painted tag on a side wall: a few looping strokes drawn in wall coordinates (z along, y up)."""
    rng = np.random.default_rng(seed)
    strokes = []
    for k in range(3):
        n = 7
        zs = z + np.cumsum(rng.uniform(0.05, 0.25, n)) * size
        ys = y + rng.uniform(-0.3, 0.3, n) * size
        curve = catmull_rom(cam.P(np.full(n, sx), ys, zs), samples=6)
        strokes.append(Stroke(curve, width=max(1.0, 0.035 * size * cam.scale(z)), color=color, alpha=0.85, taper=(True, True),
                              feature=True))
    return strokes


def underpass(cam, length=36.0, width=4.2, height=2.7):
    """A pedestrian underpass: two-tone tiled walls, a wet tiled floor, fluorescent tubes down the ceiling (one
    dead), graffiti, and the far exit glowing with sodium light."""
    room = st.Room(cam, width=width, depth=length, height=height, wall="#a3a296", back="#f2b56a", floor="#35363c",
                   ceiling="#55554f", floor_kind="tiles")
    parts = room.parts()
    zn, zb, w = cam.near_z() * 0.98, length, width / 2
    for sd in (-1, 1):                                              # the dark lower band of tiles, then the joints
        sx = sd * w * 0.999
        band = cam.P([sx] * 4, [0, 0, 1.1, 1.1], [zn, zb, zb, zn])
        parts.append(st._flat(f"wainscot{sd}", "#34504e", [band], gradient=(tuple(band[0]), "#203130", tuple(band[1]), "#34504e")))
        parts.append(st._flat(f"tiles{sd}", "#a3a296", [cam.P([sx] * 4, [0, 0, height, height], [zn, zb, zb, zn])], alpha=0.0,
                              strokes=_wall_strokes(cam, sx, zn, zb, 0.1, height, 0.2, 0.4, "#6d6a60", alpha=0.35, width=0.9)))
        grime = cam.P([sx] * 4, [0, 0, 0.45, 0.45], [zn, zb, zb, zn])
        parts.append(st._flat(f"grime{sd}", "#1a1c1c", [grime], alpha=0.45, blur=4.0))
        stains = []                                                  # damp streaks running down from the ceiling
        rng = np.random.default_rng(20 + sd)
        for z in rng.uniform(2.5, length * 0.6, 9):
            stains.append(cam.P([sx] * 4, [height, height, height - rng.uniform(0.6, 1.6)] * 1 + [height - 0.3],
                                [z, z + 0.25, z + 0.18, z + 0.04]))
        parts.append(st._flat(f"stains{sd}", "#4a4a40", stains, alpha=0.35, blur=3.0))
    tags = [(-1, 5.5, 1.5, 1.4, "#c84a6a", 1), (-1, 9.0, 1.2, 1.0, "#e8e2d2", 2), (1, 7.5, 1.6, 1.6, "#4a8ac8", 3),
            (1, 13.0, 1.3, 1.2, "#202022", 4), (-1, 15.0, 1.6, 1.3, "#7ab85a", 5)]
    for k, (sd, z, y, size, color, seed) in enumerate(tags):
        sx = sd * w * 0.998
        parts.append(st._flat(f"tag{k}", color, [cam.P([sx] * 4, [0, 0, 0.1, 0.1], [z, z + 0.1, z + 0.1, z])], alpha=0.0,
                              strokes=_tag(cam, sx, z, y, size * 0.75, mix(color, "#55554f", 0.25), seed)))
    for k, z in enumerate(np.arange(2.5, length - 1.0, 3.0)):     # tubes along the ceiling, every 3 m
        dead = k == 3
        tube = cam.P([-0.07, 0.07, 0.07, -0.07], [height - 0.02] * 4, [z, z, z + 1.2, z + 1.2])
        parts.append(st._flat(f"tube{k}", "#5a5c60" if dead else "#f4fbff", [tube], line=st._ink(0.4, alpha=0.6)))
        if not dead:
            c = cam.P(0.0, height - 0.05, z + 0.6)
            s = cam.scale(z + 0.6)
            parts.append(st._flat(f"tube_glow{k}", "#dff0ff", [ellipse(c[0], c[1], 0.7 * s, 0.22 * s)], blur=0.18 * s,
                                  alpha=0.40, blend="screen"))
            f = cam.P(0.0, 0.0, z + 0.6)
            parts.append(st._flat(f"floor_light{k}", "#cfe6ff", [ellipse(f[0], f[1], 1.4 * s, 0.25 * s)], blur=0.2 * s,
                                  alpha=0.25, blend="screen"))
    end = room.corners(zb)
    parts.append(st._flat("exit_glow", SODIUM, [np.array([end.mean(0)])], alpha=0.0))
    c = end.mean(0)
    parts.append(st._flat("exit_halo", SODIUM, [ellipse(c[0], c[1], (end[1, 0] - end[0, 0]) * 1.2, (end[0, 1] - end[2, 1]) * 1.0)],
                          blur=(end[1, 0] - end[0, 0]) * 0.5, alpha=0.5, blend="screen"))
    return parts


def earphones(fig, color="#eeeeee"):
    """Wired earbuds: the cords leave the ears below the hair, meet on the chest and run down into the pocket."""
    head = fig._head()
    u = fig.u
    px = u / 100.0
    joint = fig.joint("neck") + [fig.p.turn * 0.1 * u, 0.55 * u]
    pocket = fig.joint("pelvis") + [fig.p.turn * 0.12 * u, -0.62 * u]
    strokes = []
    buds = []
    for sd in (-1, 1):
        ear = head.P(sd * 0.36, 0.60)
        under = head.P(sd * 0.30, 0.95)
        cord = catmull_rom(np.array([ear, under, (under + joint) / 2 + [sd * 0.04 * u, 0], joint]), samples=8)
        strokes.append(Stroke(cord, width=1.3 * px, color=color, alpha=0.9, taper=(False, False)))
        buds.append(ellipse(ear[0], ear[1], 0.05 * u, 0.06 * u, n=10))
    strokes.append(Stroke(catmull_rom(np.array([joint, joint + [0.03 * u, 0.30 * u], pocket]), samples=6), width=1.5 * px,
                          color=color, alpha=0.9, taper=(False, False)))
    return [Part((fig.s.ident or "fig") + "_buds", color, polys=buds, material="gloss", line=Line(0.8 * px, color="#555555"),
                 strokes=strokes)]


STAND_W = replace(POSES["standing"], turn=0.15, head_yaw=10.0, head_tilt=4.0, pelvis_tilt=4.0, chest_tilt=-2.0,
                  left_foot_turn=10.0, right_foot_turn=18.0)


def woman(style="illust"):
    """A woman in a hoodie standing in a tiled underpass at night, earphones in, hands in her pocket; fluorescent
    tubes overhead, tags on the walls, the exit at the far end glowing orange."""
    cam = st.Camera(WIDTH, HEIGHT, horizon=HEIGHT * 0.46, eye=1.45)
    scene = Scene(WIDTH, HEIGHT, light=(0.15, -0.90, 0.40), seed=7)
    x, z = -0.55, 3.9
    fig = _dressed(WOMAN, STAND_W, cam, x, z)
    scene.add(underpass(cam), st.figure_shadow(cam, fig, z, 0.35), fig.parts(overlays=hoodie_parts(fig, WOMAN.cloth)),
              earphones(fig))
    return scene.render(style)


# ---- 3. the pair ----------------------------------------------------------------------------------------
def bus_stop(cam, x0=-2.6, x1=2.0, z0=5.6, z1=7.2, h=2.45):
    """A bus shelter: four posts, a roof with snow on it and a light strip under it, glass at the back and the
    ends, a bench, a lit advert panel and the stop sign on its pole."""
    parts = []
    glass = "#9fb4c8"
    back = cam.P([x0, x1, x1, x0], [0.15, 0.15, h, h], [z1] * 4)
    parts.append(st._flat("shelter_back", glass, [back], alpha=0.30, line=st._ink(0.6, alpha=0.6)))
    for sd, x in ((-1, x0), (1, x1)):
        end = cam.P([x] * 4, [0.15, 0.15, h, h], [z0 + 0.2, z1, z1, z0 + 0.2])
        parts.append(st._flat(f"shelter_end{sd}", glass, [end], alpha=0.25, line=st._ink(0.6, alpha=0.6)))
    ad = cam.P([x1 - 1.3, x1 - 0.1, x1 - 0.1, x1 - 1.3], [0.4, 0.4, 2.1, 2.1], [z1 - 0.03] * 4)
    parts.append(st._flat("advert", "#e9eef2", [ad], line=st._ink(0.6),
                          gradient=(tuple(ad[3]), "#f4f7fa", tuple(ad[0]), "#b8c8d8")))
    inner = ad * 0.72 + ad.mean(0) * 0.28                           # the printed picture on the lit panel
    parts.append(st._flat("advert_print", "#c86a4a", [inner], alpha=0.45))
    parts += st.box(cam, "bench", x0 + 0.5, 0.42, z1 - 0.45, 2.4, 0.06, 0.38, "#6b5a48")
    for k, x in enumerate((x0 + 0.65, x0 + 2.65)):
        parts += st.box(cam, f"bench_leg{k}", x, 0, z1 - 0.40, 0.06, 0.42, 0.06, "#2e3038")
    for k, (x, z) in enumerate(((x0, z1), (x1 - 0.08, z1), (x0, z0), (x1 - 0.08, z0))):
        parts += st.box(cam, f"post{k}", x, 0, z, 0.08, h, 0.08, "#2e3038")
    parts += st.box(cam, "roof", x0 - 0.15, h, z0 - 0.1, x1 - x0 + 0.3, 0.14, z1 - z0 + 0.3, "#3a3d46")
    snow = cam.P([x0 - 0.2, x1 + 0.2, x1 + 0.2, x0 - 0.2], [h + 0.14, h + 0.14, h + 0.24, h + 0.24], [z0 - 0.12] * 4)
    parts.append(st._flat("roof_snow", "#e6ebf3", [snow], blur=0.8))
    strip = cam.P([x0 + 0.2, x1 - 0.2, x1 - 0.2, x0 + 0.2], [h - 0.01] * 4, [z0 + 0.5, z0 + 0.5, z0 + 0.6, z0 + 0.6])
    parts.append(st._flat("roof_light", "#f2f8ff", [strip]))
    c = cam.P(0.0, h - 0.2, z0 + 0.6)
    s = cam.scale(z0)
    parts.append(st._flat("shelter_glow", "#dbe8ff", [ellipse(c[0], c[1], 2.4 * s, 1.3 * s)], blur=0.6 * s, alpha=0.30,
                          blend="screen"))
    sx = x1 + 0.45
    pole = cam.P([sx, sx], [0, 2.9], [z0 - 0.2] * 2)
    sign = cam.P(sx, 2.75, z0 - 0.2)
    parts += [Part("sign_pole", "#2e3038", ribbon=Ribbon(pole, [(0, 0.04 * s), (1, 0.035 * s)], step=3.0), material="gloss",
                   line=st._ink(0.5)),
              st._flat("sign", "#f2f0ea", [ellipse(sign[0], sign[1], 0.28 * s, 0.28 * s)], line=st._ink(0.8)),
              st._flat("sign_bus", "#2f6a3a", [np.array([sign + [-0.15 * s, -0.10 * s], sign + [0.15 * s, -0.10 * s],
                                                         sign + [0.15 * s, 0.08 * s], sign + [-0.15 * s, 0.08 * s]])],
                       strokes=[Stroke(np.array([sign + [-0.11 * s, -0.03 * s], sign + [0.11 * s, -0.03 * s]]),
                                       width=0.05 * s, color="#f2f0ea", taper=(False, False))]),
              st._flat("sign_wheels", "#2f6a3a", [ellipse(sign[0] - 0.09 * s, sign[1] + 0.10 * s, 0.035 * s, 0.035 * s),
                                                  ellipse(sign[0] + 0.09 * s, sign[1] + 0.10 * s, 0.035 * s, 0.035 * s)]),
              st._flat("sign_ring", "#2f6a3a", [ellipse(sign[0], sign[1], 0.28 * s, 0.28 * s)], alpha=0.0,
                       line=Line(0.05 * s, color="#2f6a3a"))]
    return parts


def road_strip(cam, z0, z1, color="#2e313a"):
    """A road crossing the picture between depths z0 and z1 (z1 farther), slush along its edges and tyre tracks."""
    W = cam.width
    near_y, far_y = min(cam.floor_y(z0), cam.height + 10), cam.floor_y(z1)
    road = np.array([(0, far_y), (W, far_y), (W, near_y), (0, near_y)], float)
    tracks = [Stroke(np.array([(0, y), (W, y)]), width=1.5, color="#545866", alpha=0.6, taper=(False, False), feature=False)
              for y in np.linspace(far_y + (near_y - far_y) * 0.2, near_y - 4, 4)]
    curb = np.array([(0, far_y - 3), (W, far_y - 3), (W, far_y + 4), (0, far_y + 4)], float)
    return [st._flat("road", color, [road], gradient=((0, far_y), "#262931", (0, near_y), "#3a3e48"), strokes=tracks),
            st._flat("curb_snow", "#cfd7e6", [curb], blur=1.5)]


PHONE_W = replace(POSES["phone"], turn=0.10, head_yaw=-4.0, head_tilt=-6.0)


def pair_stop(style="watercolor"):
    """Two people waiting at a bus stop at night in the snow: he smokes with his hands in his pocket, she looks
    at her phone; the shelter light and a lamp, panel blocks behind."""
    cam = st.Camera(WIDTH, HEIGHT, horizon=HEIGHT * 0.48, eye=1.5)
    scene = Scene(WIDTH, HEIGHT, light=(-0.2, -0.85, 0.48), seed=9)
    scene.set_background(night_sky(WIDTH, HEIGHT, cam.horizon, seed=3))
    back = snow_ground(cam)
    back += panel_block(cam, "block_a", -70, 110, 60, 12, color="#3c4150", lit=0.24, seed=11)
    back += panel_block(cam, "block_b", 0, 130, 80, 9, color="#383d4b", lit=0.2, seed=12)
    back += bare_tree(cam, "tree_a", -5.0, 14.0, height=8.0, seed=21)
    back += bare_tree(cam, "tree_b", 6.5, 18.0, height=7.0, seed=22)
    back += sodium_lamp(cam, "stop_lamp", -4.2, 8.5, side=1.0)
    back += bus_stop(cam)
    back += road_strip(cam, 2.0, 5.0)
    z = 6.55
    him = _dressed(MAN, STAND_M, cam, -0.85, z)
    her_spec = replace(WOMAN, upper="longsleeve", lower="long_skirt", cloth="#5a5f6e", cloth2="#202027", right_item="phone",
                       head=dict(HAIR_F, hair_style="long", bangs="full"))
    her = Figure(cam.fit(her_spec, PHONE_W, 0.25, z), PHONE_W)
    smoke_front, smoke = mouth_cigarette(him, side=-1.0)
    scene.add(back, figure_light(cam, him, z, "#dbe8ff", 0.25), figure_light(cam, her, z, "#dbe8ff", 0.25),
              him.parts(overlays=hoodie_parts(him, MAN.cloth)), beanie(him), smoke_front, smoke,
              her.parts(), scarf(her), snowfall(WIDTH, HEIGHT, count=700, near=90, seed=8))
    return scene.render(style)


# ---- 4. the character sheet --------------------------------------------------------------------------
SHEET_W, SHEET_H, SHEET_UNIT, SHEET_TOP = 2000, 1300, 120, 110
CHIPS = ["#2b2d33", "#26272d", "#343b4a", "#e8c3a6", "#1d1a1c", "#d9d6cf", "#c98f4a", "#ff5a1e"]   # cap, hoodie, jeans,
#                                                         skin, hair, shoes and strings, filter, ember


def character_sheet(style="poster"):
    """The man as a character sheet: front, three-quarter, profile and back on one ground line, faint guide
    lines at every head height, and chips of his colors along the bottom."""
    scene = Scene(SHEET_W, SHEET_H, light=(-0.6, -0.5, 0.62), seed=4)
    scene.set_background("#ebe9e2")
    guides = [Stroke(np.array([(60, SHEET_TOP + k * SHEET_UNIT), (SHEET_W - 60, SHEET_TOP + k * SHEET_UNIT)]), width=1.2,
                     color="#8f8c84", alpha=0.45, taper=(False, False)) for k in range(9)]
    scene.add(Part("guides", "#efeee9", polys=[np.array([(0, 0), (1, 0), (1, 1)])], alpha=0.0, shade=False, material="flat",
                   strokes=guides))
    base = replace(MAN, top=SHEET_TOP, unit=SHEET_UNIT, ident="")
    views = [replace(STAND_M, turn=0.0, head_yaw=0.0, head_tilt=0.0, pelvis_tilt=0.0, chest_tilt=0.0),
             replace(STAND_M, turn=0.45, head_yaw=6.0),
             replace(POSES["side_stand"], left_hand="relaxed", right_hand="relaxed"),
             replace(POSES["standing"], view="back", left_upper_arm=-10.0, right_upper_arm=10.0)]
    for k, pose in enumerate(views):
        spec = replace(base, cx=SHEET_W * (0.13 + 0.235 * k), ident=f"v{k}")
        if pose.view == "front":
            pose = pocket_pose(spec, pose)
        fig = Figure(spec, pose)
        y = fig.ground_y()
        x = (fig.joint("ankle_left")[0] + fig.joint("ankle_right")[0]) / 2
        scene.add(Part(f"floor{k}", "#3a3040", polys=[ellipse(x, y, 0.9 * SHEET_UNIT, 0.10 * SHEET_UNIT)], shade=False,
                       material="flat", blur=0.08 * SHEET_UNIT, alpha=0.22, blend="multiply", receive=False))
        scene.add(fig.parts(overlays=hoodie_parts(fig, MAN.cloth)), beanie(fig))
        if pose.view == "front" and k == 0:
            front, smoke = mouth_cigarette(fig, side=-1.0)
            scene.add(front, smoke)
    size, gap = 70, 22
    x0 = SHEET_W - 60 - len(CHIPS) * (size + gap) + gap
    for k, color in enumerate(CHIPS):
        x = x0 + k * (size + gap)
        scene.add(Part(f"chip{k}", color, polys=[np.array([(x, 1170), (x + size, 1170), (x + size, 1170 + size),
                                                          (x, 1170 + size)])], shade=False, material="flat",
                       line=Line(2.0, color="#2a2630")))
    return scene.render(style)


# ---- 5. the district -----------------------------------------------------------------------------------
OIL = get_style("painterly", painterly=dict(scale=0.6, jitter=3.0, relief=0.08))


def district(style=OIL):
    """A panel-block district at night seen down its main road: long blocks on both sides, sodium lamps every
    22 m with their pools of light, tram wires overhead, snow, and one person walking away."""
    cam = st.Camera(WIDTH, HEIGHT, horizon=HEIGHT * 0.46, eye=1.7, vp_x=WIDTH * 0.48)
    scene = Scene(WIDTH, HEIGHT, light=NIGHT_LIGHT, seed=13)
    scene.set_background(night_sky(WIDTH, HEIGHT, cam.horizon, seed=5))
    back = snow_ground(cam)
    zn = cam.near_z() * 0.98
    road = cam.P([-4, 4, 4, -4], [0.002] * 4, [zn, zn, 600, 600])
    tracks = [Stroke(cam.P([x, x], [0.003, 0.003], [zn, 600]), width=2.0, color="#23252d", alpha=0.6, taper=(False, False),
                     feature=False) for x in (-2.6, -1.4, 1.4, 2.6)]
    back.append(st._flat("road", "#3a3d48", [road], gradient=((0, cam.horizon), "#2a2c35", (0, HEIGHT), "#4a4e5a"),
                         strokes=tracks))
    for sd in (-1, 1):                                                # ploughed snow banked along both kerbs
        bank = cam.P([sd * 4.0, sd * 4.0, sd * 4.6, sd * 4.6], [0.0, 0.0, 0.35, 0.35], [zn, 600, 600, zn])
        back.append(st._flat(f"bank{sd}", "#b9c2d4", [bank], gradient=((0, cam.horizon), "#5a6078", (0, HEIGHT), "#c9d1e0"),
                             line=st._ink(0.4, alpha=0.4)))
    back += panel_block(cam, "end_block", -40, 420, 80, 12, d=14, color="#3a3f4c", lit=0.25, seed=30)
    blocks = [(-27, 170, 9), (15, 160, 12), (-27, 95, 9), (15, 88, 9), (-27, 22, 9), (15, 18, 12)]
    for k, (x0, z0, floors) in enumerate(blocks):                     # far to near, so nearer blocks cover farther
        back += panel_block(cam, f"blk{k}", x0, z0, 12, floors, d=58, color=("#3e4351", "#434856")[k % 2], lit=0.28,
                            seed=40 + k)
    for k, z in enumerate(np.arange(207.0, 5.0, -22.0)):              # lamps both sides, far to near
        back += sodium_lamp(cam, f"lamp_l{k}", -5.2, z, side=1.0)
        back += sodium_lamp(cam, f"lamp_r{k}", 5.2, z + 11.0, side=-1.0)
        back += bare_tree(cam, f"tree_l{k}", -7.5, z + 6.0, height=6.5, seed=60 + k)
        back += bare_tree(cam, f"tree_r{k}", 7.6, z + 15.0, height=6.0, seed=80 + k)
    wires = [Stroke(cam.P([x, x], [6.2, 6.2], [zn, 600]), width=1.2, color="#15161c", alpha=0.8, taper=(False, False))
             for x in (-0.8, 0.8)]
    back.append(st._flat("tram_wires", "#15161c", [road[:1]], alpha=0.0, strokes=wires))
    walker_pose = replace(POSES["standing"], view="back", left_upper_arm=-6.0, right_upper_arm=6.0)
    walker = Figure(cam.fit(replace(MAN, ident="walker"), walker_pose, 5.4, 24.0), walker_pose)
    scene.add(back, figure_light(cam, walker, 24.0, strength=0.3), walker.parts(overlays=hoodie_parts(walker, MAN.cloth)),
              beanie(walker), snowfall(WIDTH, HEIGHT, count=600, near=60, seed=14))
    return scene.render(style)


# ---- 6. the field --------------------------------------------------------------------------------------
PYLON = dict(height=32.0, base=3.2, waist=0.9, arms=((24.0, 7.0), (29.0, 5.4)), drop=1.6)   # meters


def _pylon_points(x, arm, side):
    """Where a wire hangs: the end of an insulator string under one cross arm."""
    y, span = PYLON["arms"][arm]
    return x + side * span, y - PYLON["drop"]


def pylon(cam, name, x, z, color="#1d1e24"):
    """A lattice power pylon seen face on: two tapering legs, X bracing between them, two cross arms with
    insulator strings and a peak. Drawn as lines whose width follows the distance."""
    s = cam.scale(z)
    H, b, w = PYLON["height"], PYLON["base"], PYLON["waist"]
    width = max(0.7, 0.10 * s)
    lines = []
    leg = lambda sd, t: (x + sd * (b + (w - b) * t), H * t)
    for sd in (-1, 1):
        lines.append(np.array([leg(sd, 0.0), leg(sd, 1.0)]))
    ts = np.linspace(0.0, 1.0, 9)
    for t0, t1 in zip(ts[:-1], ts[1:]):                              # X bracing panel by panel
        lines.append(np.array([leg(-1, t0), leg(1, t1)]))
        lines.append(np.array([leg(1, t0), leg(-1, t1)]))
        lines.append(np.array([leg(-1, t1), leg(1, t1)]))
    for y, span in PYLON["arms"]:
        lines.append(np.array([(x - span, y), (x + span, y)]))
        lines.append(np.array([(x - span, y), (x - w, y + 1.6)]))
        lines.append(np.array([(x + span, y), (x + w, y + 1.6)]))
        for sd in (-1, 1):
            lines.append(np.array([(x + sd * span, y), (x + sd * span, y - PYLON["drop"])]))
    lines.append(np.array([(x - w, H), (x, H + 3.0), (x + w, H)]))
    strokes = [Stroke(cam.P(l[:, 0], l[:, 1], np.full(len(l), z)), width=width, color=color, alpha=0.9, taper=(False, False))
               for l in lines]
    base = cam.P(x, 0, z)
    return [st._flat(name, color, [np.array([base])], alpha=0.0, strokes=strokes)]


def power_line(cam, name, x, zs, color="#1d1e24", sag=3.0):
    """The wires between consecutive pylons at depths zs: four hanging curves per span."""
    strokes = []
    t = np.linspace(0, 1, 24)
    for z0, z1 in zip(zs[:-1], zs[1:]):
        for arm in range(2):
            for sd in (-1, 1):
                wx, wy = _pylon_points(x, arm, sd)
                ys = wy - sag * 4 * t * (1 - t)
                strokes.append(Stroke(cam.P(np.full(24, wx), ys, z0 + (z1 - z0) * t), width=max(0.6, 0.03 * cam.scale(z0)),
                                      color=color, alpha=0.8, taper=(False, False)))
    return [st._flat(name, color, [np.array([cam.P(x, 0, zs[0])])], alpha=0.0, strokes=strokes)]


def moon_sky(width, height, horizon, moon=(0.74, 0.16), seed=6):
    """The night sky with a moon behind thin cloud: a pale disc and a wide soft halo."""
    img = night_sky(width, height, horizon, seed=seed)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    d = np.hypot(xx - moon[0] * width, yy - moon[1] * height) / width
    halo = np.exp(-(d / 0.09) ** 2) * 0.35 + np.exp(-(d / 0.25) ** 2) * 0.12
    img = 1 - (1 - img) * (1 - halo[..., None] * np.array([0.85, 0.88, 1.0], np.float32))
    disc = np.clip((0.024 - d) / 0.003, 0, 1)[..., None]
    return np.clip(img * (1 - disc) + np.array([0.93, 0.93, 0.88], np.float32) * disc, 0, 1).astype(np.float32)


def field(style="pencil"):
    """A snowy field at night: a line of pylons striding to the horizon, a rutted road, a few bare trees, panel
    blocks far off with a handful of lit windows, the moon in thin cloud and one person walking away."""
    cam = st.Camera(WIDTH, HEIGHT, horizon=HEIGHT * 0.52, eye=1.6, vp_x=WIDTH * 0.44)
    scene = Scene(WIDTH, HEIGHT, light=(0.4, -0.6, -0.3), seed=17)
    scene.set_background(moon_sky(WIDTH, HEIGHT, cam.horizon))
    back = snow_ground(cam)
    for k, (x0, w, floors) in enumerate(((-260, 90, 16), (-120, 70, 12), (40, 110, 16), (210, 80, 9))):
        back += panel_block(cam, f"far{k}", x0, 900, w, floors, d=14, color="#2c303c", lit=0.12, seed=70 + k)
    zn = cam.near_z() * 0.98
    road = cam.P([-1.5, 1.5, 1.0, -1.0], [0.002] * 4, [zn, zn, 900, 900])
    ruts = [Stroke(cam.P([x, x * 0.7], [0.003, 0.003], [zn, 900]), width=3.0, color="#3a3c46", alpha=0.75,
                   taper=(False, True), feature=False) for x in (-0.95, -0.55, 0.55, 0.95)]
    back.append(st._flat("road", "#8a8e9c", [road], gradient=((0, cam.horizon), "#4a4e5c", (0, HEIGHT), "#9a9eac"),
                         strokes=ruts, blur=1.5))
    zs = [40.0, 100.0, 160.0, 220.0, 280.0, 340.0, 400.0]
    for k, z in enumerate(zs[::-1]):
        back += pylon(cam, f"pylon{k}", 22.0, z)
    back += power_line(cam, "wires", 22.0, zs)
    zs_far = [120.0, 220.0, 320.0, 420.0]
    for k, z in enumerate(zs_far[::-1]):
        back += pylon(cam, f"pylon_far{k}", -70.0, z)
    back += power_line(cam, "wires_far", -70.0, zs_far)
    for k, (tx, tz, th) in enumerate(((-6.0, 11.0, 7.5), (-9.5, 15.0, 8.0), (-4.2, 20.0, 6.5), (5.5, 32.0, 6.0))):
        back += bare_tree(cam, f"birch{k}", tx, tz, height=th, color="#2c2c32", seed=90 + k)
    walk = replace(POSES["standing"], view="back", left_upper_arm=-6.0, right_upper_arm=6.0)
    walker = Figure(cam.fit(replace(MAN, ident="walker"), walk, 0.4, 16.0), walk)
    birds = []
    rng = np.random.default_rng(3)
    for bx, by in zip(rng.uniform(0.15, 0.55, 4) * WIDTH, rng.uniform(0.12, 0.30, 4) * HEIGHT):
        r = rng.uniform(5, 9)
        birds.append(Stroke(np.array([(bx - r, by - r * 0.4), (bx - r * 0.4, by - r * 0.6), (bx, by), (bx + r * 0.4, by - r * 0.6),
                                      (bx + r, by - r * 0.4)]), width=1.6, color="#141418", taper=(True, True)))
    scene.add(back, st.figure_shadow(cam, walker, 16.0, 0.25), walker.parts(overlays=hoodie_parts(walker, MAN.cloth)),
              beanie(walker), st._flat("crows", "#141418", [np.array([(0, 0)])], alpha=0.0, strokes=birds),
              snowfall(WIDTH, HEIGHT, count=350, near=30, seed=18))
    return scene.render(style)


# ---- 7. the still life ---------------------------------------------------------------------------------
SILL_Y = 0.70                                   # image height of the sill top's front edge, fraction of the height
SILL_UNIT = 118                                 # px per 10 cm on the sill


def _rect(x0, y0, x1, y1):
    return np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], float)


def night_window(x0, y0, x1, y1, seed=5):
    """An old double window at night: a painted frame with a small vent pane in the upper corner, and behind the
    glass a dark sky, panel blocks with a few lit windows, lamp glows, falling snow and frost in the corners."""
    rng = np.random.default_rng(seed)
    w, h = x1 - x0, y1 - y0
    frame_col = "#c9c5bb"
    glass = Part("glass", "#141a30", polys=[_rect(x0, y0, x1, y1)], shade=False, material="flat", receive=False,
                 gradient=((x0, y0), "#0a0e1e", (x0, y1), "#4a3a44"))
    towers, lights, glows = [], [], []
    x = x0 - 20
    while x < x1:
        tw, th = rng.uniform(0.10, 0.22) * w, rng.uniform(0.18, 0.45) * h
        top = y1 - th
        towers.append(_rect(x, top, x + tw, y1 + 5))
        for wy in np.arange(top + 10, y1 - 6, 15):
            for wx in np.arange(x + 6, x + tw - 8, 13):
                if rng.random() < 0.18:
                    lights.append(_rect(wx, wy, wx + 7, wy + 8))
        x += tw + rng.uniform(4, 30)
    for gx in rng.uniform(x0, x1, 5):
        gy = y1 - rng.uniform(0.02, 0.10) * h
        glows.append(ellipse(gx, gy, 0.05 * w, 0.03 * w))
    flakes = [ellipse(fx, fy, r, r, n=6) for fx, fy, r in zip(rng.uniform(x0, x1, 220), rng.uniform(y0, y1, 220),
                                                              rng.uniform(1.0, 2.6, 220))]
    parts = [glass,
             Part("towers", "#20253a", polys=towers, shade=False, material="flat", clip="glass", receive=False),
             Part("tower_lights", "#ffcf80", polys=lights, shade=False, material="flat", clip="towers", receive=False),
             Part("lamp_glow", SODIUM, polys=glows, shade=False, material="flat", blur=0.02 * w, alpha=0.55, blend="screen",
                  clip="glass", receive=False),
             Part("outside_snow", "#e8eef8", polys=flakes, shade=False, material="flat", alpha=0.8, clip="glass", receive=False)]
    frost = [ellipse(cx, cy, 0.16 * w, 0.20 * h) for cx in (x0, x0 + w / 2, x1) for cy in (y1,)]
    parts.append(Part("frost", "#dfe8f5", polys=frost, shade=False, material="flat", blur=0.05 * w, alpha=0.45, clip="glass",
                      receive=False))
    bar = 0.022 * w
    mid = x0 + w / 2
    vent_y = y0 + 0.36 * h
    bars = [_rect(x0 - bar, y0 - bar, x1 + bar, y0 + bar * 0.4), _rect(x0 - bar, y1 - bar * 0.4, x1 + bar, y1 + bar),
            _rect(x0 - bar, y0, x0 + bar * 0.4, y1), _rect(x1 - bar * 0.4, y0, x1 + bar, y1),
            _rect(mid - bar * 0.6, y0, mid + bar * 0.6, y1), _rect(x0, vent_y - bar * 0.4, mid, vent_y + bar * 0.4),
            _rect(x0 + w * 0.25 - bar * 0.4, y0, x0 + w * 0.25 + bar * 0.4, vent_y)]
    chips = [ellipse(px_, py_, rng.uniform(2, 5), rng.uniform(1.5, 3), n=6)
             for px_, py_ in zip(rng.uniform(x0, x1, 18), np.full(18, y1 + bar * 0.3))]
    parts.append(Part("window_frame", frame_col, polys=bars, shade=False, material="flat", receive=False,
                      line=Line(2.2, color="#3a3640"), merge="window_frame"))      # one outline round the joined bars
    parts.append(Part("paint_chips", "#8a8478", polys=chips, shade=False, material="flat", alpha=0.7, receive=False))
    return parts


def cassette_player(desk, x, z, color="#3a3d44"):
    """A pocket cassette player lying on its back: the lid window shows the tape and its two reels."""
    w, h, d = 1.15, 0.32, 0.80
    parts = [ob.contact_shadow(desk, x - w / 2, z, w, d, h)]
    body, planes = ob.box(desk, desk.name("player"), x - w / 2, 0, z, w, h, d, color, r=0.06)
    parts += body
    lid = desk.rect(planes["top"], 0.10, 0.12, w - 0.20, d - 0.24, 0.04)
    parts.append(ob._flat(desk.name("lid"), "#1a1c22", [lid], line=desk.ink(0.6)))
    for s_ in (0.36, w - 0.36):
        parts.append(ob._flat(desk.name("reel"), "#d9d4c8", [desk.disc(planes["top"], s_, d / 2, 0.12)], line=desk.ink(0.5)))
        parts.append(ob._flat(desk.name("hub"), "#2a2a30", [desk.disc(planes["top"], s_, d / 2, 0.04)]))
    keys = [desk.rect(planes["front"], 0.12 + k * 0.2, 0.08, 0.14, 0.14, 0.02) for k in range(4)]
    parts.append(ob._flat(desk.name("keys"), "#8a8e98", keys, line=desk.ink(0.4)))
    led = desk.P(x + w / 2 - 0.12, h * 0.6, z)
    parts.append(ob._flat(desk.name("led"), "#ff4a3a", [ellipse(led[0], led[1], 3.0, 3.0)]))
    parts.append(ob._flat(desk.name("led_glow"), "#ff4a3a", [ellipse(led[0], led[1], 12.0, 12.0)], blur=5.0, alpha=0.6,
                          blend="screen"))
    jack = desk.P(x - w / 2, h * 0.5, z + 0.2)
    return parts, jack


def cassette_case(desk, x, z, y0=0.0, color="#d8d2c4", label="#c84a3a"):
    """A tape in its clear case lying flat: the case, the tape inside and its label."""
    w, h, d = 1.08, 0.16, 0.70
    parts = [ob.contact_shadow(desk, x - w / 2, z, w, d, h + y0)] if y0 == 0 else []
    body, planes = ob.box(desk, desk.name("case"), x - w / 2, y0, z, w, h, d, color, r=0.02)
    parts += body
    parts.append(ob._flat(desk.name("label"), label, [desk.rect(planes["top"], 0.12, 0.12, w - 0.24, d - 0.30, 0.02)],
                          line=desk.ink(0.4)))
    for s_ in (0.38, w - 0.38):
        parts.append(ob._flat(desk.name("spool"), "#2a2a30", [desk.disc(planes["top"], s_, d - 0.26, 0.07)]))
    return parts


def cup_noodle(desk, x, z, color="#f2eee4", band="#c8483a"):
    """A cup of instant noodles: a tapered paper cup, a printed band, the lid peeled back and a fork on top."""
    r, h = 0.50, 1.05
    parts = [ob.contact_shadow(desk, x - r, z, 2 * r, 2 * r, h)]
    body, top_c, (rx, ry) = ob.cylinder(desk, desk.name("cup"), x, 0, z + r, r, h, color, taper=0.78, top_color="#c89a62")
    parts += body
    noodles = [Stroke(np.stack([top_c[0] + np.linspace(-0.7, 0.7, 12) * rx,
                                top_c[1] + (k - 1) * 0.3 * ry + 0.12 * ry * np.sin(np.linspace(0, 9, 12) + k)], 1),
                      width=0.03 * desk.unit, color="#f0d8a0", alpha=0.9, taper=(True, True), clip=True) for k in range(3)]
    parts.append(ob._flat(desk.name("noodles"), "#c89a62", [ellipse(top_c[0], top_c[1], rx * 0.9, ry * 0.9)], strokes=noodles))
    mid = desk.P(x, h * 0.55, z + r)
    stripe = np.array([mid + [-rx * 0.92, -0.10 * desk.unit], mid + [rx * 0.92, -0.10 * desk.unit],
                       mid + [rx * 0.88, 0.12 * desk.unit], mid + [-rx * 0.88, 0.12 * desk.unit]])
    parts.append(ob._flat(desk.name("band"), band, [stripe], clip=body[0].name))
    flap = np.array([top_c + [-rx * 0.2, -ry * 0.6], top_c + [rx * 0.9, -ry * 1.4], top_c + [rx * 1.0, -ry * 3.4],
                     top_c + [-rx * 0.1, -ry * 2.2]])
    parts.append(ob._flat(desk.name("lid"), "#d9d4c4", [flap], line=desk.ink(0.5)))
    fork = np.array([top_c + [-rx * 0.8, ry * 0.2], top_c + [rx * 0.6, -ry * 0.9]])
    parts.append(ob._flat(desk.name("fork"), "#f4f2ea", [fork[:1]], alpha=0.0,
                          strokes=[Stroke(fork, width=0.05 * desk.unit, color="#efe9da", taper=(False, False))]))
    return parts


def cigarette_pack(desk, x, z, color="#e9e6de", band="#2f5a4a"):
    """A soft pack standing on the sill, its top torn open and two filters showing."""
    w, h, d = 0.56, 0.86, 0.24
    parts = [ob.contact_shadow(desk, x - w / 2, z, w, d, h)]
    body, planes = ob.box(desk, desk.name("pack"), x - w / 2, 0, z, w, h, d, color, r=0.02)
    parts += body
    parts.append(ob._flat(desk.name("pack_band"), band, [desk.rect(planes["front"], 0.0, 0.42, w, 0.22)]))
    for k, s_ in enumerate((0.16, 0.34)):
        tip = desk.P(x - w / 2 + s_, h + 0.10, z + 0.12)
        parts.append(ob._flat(desk.name("filter"), "#c98f4a", [ellipse(tip[0], tip[1], 0.06 * desk.unit, 0.10 * desk.unit)],
                              line=desk.ink(0.4)))
    return parts


def ashtray(desk, x, z, color="#8a96a4"):
    """A heavy glass ashtray with two stubbed-out butts; returns the parts and the rim point a burning
    cigarette rests on."""
    r, h = 0.78, 0.26
    parts = [ob.contact_shadow(desk, x - r, z, 2 * r, 2 * r, h)]
    body, top_c, (rx, ry) = ob.cylinder(desk, desk.name("ashtray"), x, 0, z + r, r, h, color)
    parts += body
    parts.append(ob._flat(desk.name("bowl"), "#4a4e58", [ellipse(top_c[0], top_c[1], rx * 0.78, ry * 0.78)]))
    parts.append(ob._flat(desk.name("ash"), "#9a9690", [ellipse(top_c[0] + rx * 0.1, top_c[1] + ry * 0.1, rx * 0.4, ry * 0.35)],
                          blur=3.0, alpha=0.8))
    for k, (dx, ang) in enumerate(((-0.3, 0.4), (0.2, -0.3))):
        a = top_c + [dx * rx, 0.1 * ry]
        b = a + np.array([np.cos(ang), np.sin(ang) * 0.4]) * 0.32 * desk.unit
        parts.append(Part(desk.name("butt"), "#c98f4a", ribbon=Ribbon(np.array([a, b]), [(0, 0.035 * desk.unit),
                                                                                         (1, 0.035 * desk.unit)], step=1.0),
                          material="matte", line=Line(0.8, color="#3a2a20")))
    return parts, top_c + [rx * 0.92, 0.0]


def still_life(style="neon"):
    """A kitchen windowsill at night: an old double window onto the blocks, snow outside; on the sill a cigarette
    burning in a glass ashtray, a soft pack, a mug of tea, a cup of noodles, a cassette player with its earphones
    and two tapes; a radiator under the sill."""
    scene = Scene(WIDTH, HEIGHT, light=(-0.4, -0.6, 0.6), seed=19)
    sill_y = HEIGHT * SILL_Y
    scene.set_background(vertical_gradient(HEIGHT, WIDTH, [(0.0, "#2a2a34"), (1.0, "#1c1c24")]))
    desk = ob.Desk(WIDTH * 0.5, sill_y, SILL_UNIT)
    parts = night_window(WIDTH * 0.05, HEIGHT * 0.03, WIDTH * 0.95, sill_y - 0.30 * SILL_UNIT * 3.0)
    sill, _ = ob.box(desk, "sill", -8, -0.45, -0.9, 16, 0.45, 3.6, "#d6d2c8")
    edge = desk.P(0, -0.45, -0.9)[1]
    wall = Part("under_sill", "#26262e", polys=[_rect(0, edge, WIDTH, HEIGHT)], shade=False, material="flat", receive=False,
                gradient=((0, edge), "#30303a", (0, HEIGHT), "#16161c"))
    fins = [_rect(x, edge + 40, x + 30, HEIGHT - 20) for x in np.arange(WIDTH * 0.18, WIDTH * 0.82, 44)]
    radiator = Part("radiator", "#3c3e46", polys=fins, material="gloss", bulge=0.6, line=Line(1.6, color="#121216"))
    parts += [wall, radiator] + sill
    player, jack = cassette_player(desk, 2.9, 0.1)
    rest = None
    items = [(1.4, cigarette_pack(desk, -5.4, 1.4)), (1.4, ob.mug(desk, -1.2, 1.3, color="#e8e4da", drink="#8a4a1a")),
             (1.2, cassette_case(desk, 4.5, 1.2) + cassette_case(desk, 4.6, 1.25, y0=0.16, label="#3a6aa8")),
             (0.7, cup_noodle(desk, 1.0, 0.7)), (0.1, player)]
    tray, rest = ashtray(desk, -3.4, 0.1)
    items.append((0.1, tray))
    for _, p in sorted(items, key=lambda q: -q[0]):
        parts += p
    buds = [desk.P(1.3, 0.05, -0.4), desk.P(1.8, 0.05, -0.55)]
    cord = catmull_rom(np.array([jack, jack + [-0.5 * SILL_UNIT, 0.25 * SILL_UNIT], buds[0] + [0.2 * SILL_UNIT, 0.1 * SILL_UNIT],
                                 buds[0]]), samples=8)
    cord2 = catmull_rom(np.array([buds[0] + [0.2 * SILL_UNIT, 0.1 * SILL_UNIT], buds[1] + [-0.2 * SILL_UNIT, 0.05 * SILL_UNIT],
                                  buds[1]]), samples=6)
    parts.append(Part("earbuds", "#f0f0ee", polys=[ellipse(b[0], b[1], 0.08 * SILL_UNIT, 0.06 * SILL_UNIT) for b in buds],
                      material="gloss", line=Line(1.0, color="#555555"),
                      strokes=[Stroke(cord, width=2.0, color="#e8e8e6", taper=(False, False)),
                               Stroke(cord2, width=2.0, color="#e8e8e6", taper=(False, False))]))
    burning, smoke = cigarette(rest + [-0.45 * SILL_UNIT, -0.05 * SILL_UNIT], (1.0, 0.18), 0.85 * SILL_UNIT, "sill_cig")
    scene.add(parts, burning, smoke)
    return scene.render(style)


BUILDERS = {"man": man, "woman": woman, "pair": pair_stop, "sheet": character_sheet, "district": district,
            "field": field, "still_life": still_life}


def sheet(images, path):
    return review.sheet(images, path, columns=3, height=420)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for name, build in BUILDERS.items():
        img = build()
        done.append(img)
        print("saved", save(img, out / f"doomer_{name}.png"))
    print("saved", sheet(done, out / "doomer_sheet.jpg"))
