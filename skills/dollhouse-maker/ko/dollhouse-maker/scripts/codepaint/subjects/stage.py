"""A one-point perspective stage: a camera, a room or an open ground, and furniture drawn in perspective.

Drafting, not 3D: every form is a box whose front face is parallel to the picture (drawn true to shape) and
whose depth edges run to one vanishing point on the horizon. The camera only answers "where on the screen is
this point (x, y, z)?", so walls, floor boards, furniture and the figures all share one horizon and one scale.

Units are meters. x to the right of the line of sight, y up from the floor, z away from the viewer.
Camera.unit_at(z) gives the head height in px of a figure standing at depth z, Camera.fit() sizes and places
a FigureSpec there, so a person and the table beside them agree.
"""
from dataclasses import dataclass, replace

import numpy as np

from ..color import mix
from ..geometry import catmull_rom, ellipse, Ribbon
from ..scene import Part, Line, Stroke

HEAD_M = 0.215              # head height of an 8-head adult (1.72 m)
FOV_DEG = 58.0              # horizontal field of view of the default lens
NEAR_MARGIN = 24            # px the floor runs past the bottom of the picture
FACE_TONE = dict(front=1.0, top=1.10, side=0.80, under=0.62)   # flat tones of box faces under the room light
INK = "#2a2630"
LINE_PX = 1.5
PLANK_M = 0.20              # floor board width
TILE_M = 0.45               # floor tile size
CONTACT = 0.30              # strength of the soft shadow under furniture


@dataclass
class Camera:
    width: int
    height: int
    horizon: float = None       # image y of eye level; None = 0.42 of the height
    vp_x: float = None          # image x of the vanishing point; None = the middle
    focal: float = None         # px for 1 m at 1 m; None = from FOV_DEG
    eye: float = 1.5            # eye height above the floor, m

    def __post_init__(self):
        self.horizon = self.height * 0.42 if self.horizon is None else self.horizon
        self.vp_x = self.width / 2 if self.vp_x is None else self.vp_x
        if self.focal is None:
            self.focal = self.width / (2 * np.tan(np.radians(FOV_DEG / 2)))

    def P(self, x, y, z):
        """Screen point(s) of room point(s)."""
        x, y, z = np.broadcast_arrays(*(np.asarray(v, float) for v in (x, y, z)))
        z = np.maximum(z, 1e-3)
        return np.stack([self.vp_x + self.focal * x / z, self.horizon - self.focal * (y - self.eye) / z], -1)

    def scale(self, z):
        """px per meter at depth z."""
        return self.focal / z

    def unit_at(self, z):
        """Head height in px of a figure at depth z."""
        return self.focal * HEAD_M / z

    def floor_y(self, z):
        return self.horizon + self.focal * self.eye / z

    def near_z(self):
        """Depth where the floor leaves the bottom of the picture."""
        return self.focal * self.eye / (self.height + NEAR_MARGIN - self.horizon)

    def fit(self, spec, pose, x, z, seat=None, lie=None):
        """A FigureSpec sized for depth z and moved so its feet stand on the floor at (x, z); with seat (m), so it
        sits on a seat of that height; with lie (m), so a lying figure (the reclining pose) rests on a surface
        of that height, 0 for the floor or the sand. Returns the spec; build the Figure with the same pose."""
        from .figure import Figure
        unit = self.unit_at(z)
        probe = Figure(replace(spec, cx=0.0, top=0.0, unit=unit), pose)
        if lie is not None:
            target, y_now = self.P(x, lie, z), probe.rest_y()
        else:
            target = self.P(x, seat if seat is not None else 0.0, z)
            y_now = probe.seat_y() if seat is not None else probe.ground_y()
        return replace(spec, cx=float(target[0]), top=float(target[1] - y_now), unit=unit)


def _ink(width=1.0, color=INK, alpha=0.85):
    return Line(LINE_PX * width, color=color, alpha=alpha)


def _flat(name, color, polys, **kw):
    kw.setdefault("receive", False)
    return Part(name, color, polys=polys, shade=False, material="flat", **kw)


FLOOR = float("inf")         # depth of things flat on the floor (soft shadows, rugs): never in front of anyone
SIT_SHARE = 0.6              # a seat's sorting depth: this share of the way back from its front edge, behind
                             # anyone sitting on it, in front of things standing beside its back


def placed(parts, depth):
    """Mark the parts of one piece of furniture with the depth people are sorted against (Set.arrange): the near
    edge of things people stand behind, a point behind the sitter for things they sit on (SIT_SHARE). Floor
    shadows keep FLOOR."""
    for q in parts:
        if q.depth != FLOOR:
            q.depth = depth
    return parts


def lit(parts):
    """Tag the parts that give light (lamp shades, bulbs, glows): Set.night keeps them bright."""
    for q in parts:
        q.tags = tuple(q.tags) + ("light",)
    return parts


def _tone(color, face, light=1.0):
    k = FACE_TONE[face] * light
    return mix(color, "#ffffff", k - 1.0) if k >= 1.0 else mix(color, "#0c0a14", 1.0 - k)


# ---- room ----------------------------------------------------------------------------------------------
@dataclass
class Room:
    """A box room around the camera: back wall at depth `depth`, side walls at x = +-width/2."""
    cam: Camera
    width: float = 6.0
    depth: float = 7.0
    height: float = 2.8
    wall: str = "#e9e1d4"
    back: str = None             # back wall color; None = the wall color
    floor: str = "#b98b5e"
    ceiling: str = "#f3efe8"
    floor_kind: str = "planks"   # planks / tiles / plain
    light_side: float = -1.0     # the side wall the window light comes from

    def corners(self, z):
        w, h = self.width / 2, self.height
        return self.cam.P([-w, w, w, -w], [0, 0, h, h], [z] * 4)

    def parts(self):
        cam, w, h = self.cam, self.width / 2, self.height
        zn, zb = cam.near_z() * 0.98, self.depth
        back_col = self.back or self.wall
        lit, shade = (-1, 1) if self.light_side < 0 else (1, -1)
        parts = []
        floor = cam.P([-w, w, w, -w], [0, 0, 0, 0], [zn, zn, zb, zb])
        ceil = cam.P([-w, w, w, -w], [h, h, h, h], [zn, zn, zb, zb])
        parts.append(_flat("room_ceiling", self.ceiling, [ceil], gradient=(tuple(ceil[0]), mix(self.ceiling, "#000000", 0.08),
                                                                           tuple(ceil[2]), self.ceiling)))
        for sd in (-1, 1):
            quad = cam.P([sd * w] * 4, [0, 0, h, h], [zn, zb, zb, zn])
            tone = _tone(self.wall, "front", 1.04 if sd == lit else 0.86)
            parts.append(_flat(f"room_wall_{sd}", tone, [quad],
                               gradient=(tuple(quad[0]), mix(tone, "#000000", 0.10), tuple(quad[1]), tone)))
        bw = self.corners(zb)
        parts.append(_flat("room_back", back_col, [bw], gradient=(tuple(bw[3]), mix(back_col, "#ffffff", 0.06),
                                                                   tuple(bw[0]), mix(back_col, "#000000", 0.06))))
        parts.append(_flat("room_floor", self.floor, [floor], gradient=(tuple(floor[2]), mix(self.floor, "#000000", 0.18),
                                                                         tuple(floor[0]), mix(self.floor, "#ffffff", 0.05)),
                           strokes=self._floor_lines(zn, zb)))
        # skirting boards along the walls, the corner lines
        board = 0.09
        for sd in (-1, 1):
            strip = cam.P([sd * w] * 4, [0, 0, board, board], [zn, zb, zb, zn])
            parts.append(_flat(f"room_skirting_{sd}", mix(self.wall, "#ffffff", 0.35), [strip], line=_ink(0.6, alpha=0.5)))
        strip = cam.P([-w, w, w, -w], [0, 0, board, board], [zb] * 4)
        parts.append(_flat("room_skirting_back", mix(back_col, "#ffffff", 0.35), [strip], line=_ink(0.6, alpha=0.5)))
        edges = [cam.P([sd * w] * 2, [y, y], [zn, zb]) for sd in (-1, 1) for y in (0, h)]
        edges += [cam.P([sd * w] * 2, [0, h], [zb, zb]) for sd in (-1, 1)]
        parts.append(_flat("room_edges", back_col, [bw], alpha=0.0,
                           strokes=[Stroke(e, width=LINE_PX * 0.8, color=INK, alpha=0.35, taper=(False, False)) for e in edges]))
        return parts

    def _floor_lines(self, zn, zb):
        cam, w = self.cam, self.width / 2
        dark = mix(self.floor, "#2a1a10", 0.45)
        lines = []
        if self.floor_kind == "plain":
            return lines
        step = PLANK_M if self.floor_kind == "planks" else TILE_M
        for x in np.arange(-w + step, w, step):                    # boards run toward the vanishing point
            lines.append(Stroke(cam.P([x, x], [0, 0], [zn, zb]), width=1.4, color=dark, alpha=0.55, taper=(False, False),
                                feature=False))
        zs = np.arange(zb, zn, -(1.2 if self.floor_kind == "planks" else TILE_M))
        for k, z in enumerate(zs):                                  # joints across the boards / the tile grid
            if self.floor_kind == "tiles":
                lines.append(Stroke(cam.P([-w, w], [0, 0], [z, z]), width=1.0, color=dark, alpha=0.45, taper=(False, False),
                                    feature=False))
                continue
            for x in np.arange(-w + step * (k % 3), w, step * 3):
                lines.append(Stroke(cam.P([x, x + step], [0, 0], [z, z]), width=0.9, color=dark, alpha=0.35,
                                    taper=(False, False), feature=False))
        return lines

    def window(self, x0, x1, y0, y1, wall="back", view="#9cc7e8", view_low="#e9f1f4", frame="#f4f1ea", panes=(2, 2),
               name="window"):
        """A window cut into the back wall (x0..x1) or a side wall (wall="left"/"right", then x0..x1 are depths)."""
        cam = self.cam
        if wall == "back":
            quad = cam.P([x0, x1, x1, x0], [y0, y0, y1, y1], [self.depth] * 4)
            cols = [cam.P([x, x], [y0, y1], [self.depth] * 2) for x in np.linspace(x0, x1, panes[0] + 1)[1:-1]]
            rows = [cam.P([x0, x1], [y, y], [self.depth] * 2) for y in np.linspace(y0, y1, panes[1] + 1)[1:-1]]
        else:
            sx = (-1 if wall == "left" else 1) * self.width / 2
            quad = cam.P([sx] * 4, [y0, y0, y1, y1], [x0, x1, x1, x0])
            cols = [cam.P([sx, sx], [y0, y1], [z, z]) for z in np.linspace(x0, x1, panes[0] + 1)[1:-1]]
            rows = [cam.P([sx, sx], [y, y], [x0, x1]) for y in np.linspace(y0, y1, panes[1] + 1)[1:-1]]
        glass = _flat(f"{name}_view", view, [quad], gradient=(tuple(quad[3]), view, tuple(quad[0]), view_low))
        bars = [Stroke(c, width=5.0, color=frame, taper=(False, False)) for c in cols + rows]
        trim = _flat(f"{name}_frame", frame, [quad], alpha=0.0, line=Line(6.0, color=frame, taper=False),
                     strokes=bars)
        return [glass, trim]

    def picture(self, x0, x1, y0, y1, colors=("#e7c38a", "#6f8fb8", "#c9785c"), name="picture"):
        """A framed picture on the back wall: three soft color fields in a dark frame."""
        cam = self.cam
        quad = cam.P([x0, x1, x1, x0], [y0, y0, y1, y1], [self.depth - 0.02] * 4)
        fields = []
        for k, c in enumerate(colors):
            a, b = y1 - (y1 - y0) * (0.12 + 0.27 * k), y1 - (y1 - y0) * (0.12 + 0.27 * (k + 1)) + 0.02
            fields.append(cam.P([x0 + 0.08 * (x1 - x0), x1 - 0.08 * (x1 - x0)] * 2, [a, a, b, b], [self.depth - 0.03] * 4)[[0, 1, 3, 2]])
        return [_flat(f"{name}_frame", "#3a3030", [quad], line=_ink(0.8)),
                _flat(f"{name}_canvas", "#f3ece0", [quad[[0, 1, 2, 3]] * 0.94 + quad.mean(0) * 0.06])] + \
               [_flat(f"{name}_field{k}", c, [f], blur=1.5) for k, (c, f) in enumerate(zip(colors, fields))]


# ---- boxes and furniture --------------------------------------------------------------------------------
def box(cam, name, x0, y0, z0, w, h, d, color, light=1.0, line=True):
    """A box from (x0, y0, z0) with size (w, h, d): the faces the camera sees, back to front."""
    P = cam.P
    x1, y1, z1 = x0 + w, y0 + h, z0 + d
    faces = []
    if x0 > 0:                                                  # right of the line of sight: its left face shows
        faces.append(("side", P([x0] * 4, [y0, y1, y1, y0], [z0, z0, z1, z1])))
    if x1 < 0:
        faces.append(("side", P([x1] * 4, [y0, y1, y1, y0], [z0, z0, z1, z1])))
    if y1 < cam.eye:                                            # below eye level: the top shows
        faces.append(("top", P([x0, x1, x1, x0], [y1] * 4, [z0, z0, z1, z1])))
    if y0 > cam.eye:
        faces.append(("under", P([x0, x1, x1, x0], [y0] * 4, [z0, z0, z1, z1])))
    faces.append(("front", P([x0, x1, x1, x0], [y0, y0, y1, y1], [z0] * 4)))
    ink = _ink(0.7) if line else None
    return placed([_flat(f"{name}_{kind}{k}", _tone(color, kind, light), [quad], line=ink)
                   for k, (kind, quad) in enumerate(faces)], z0)


def contact(cam, name, x, z, w, d, strength=CONTACT):
    """Soft shadow on the floor under a footprint (center x, z; size w, d)."""
    c = cam.P(x, 0.0, z)
    rx, ry = cam.scale(z) * w * 0.55, max(2.0, cam.P(x, 0.0, z - d / 2)[1] - cam.P(x, 0.0, z + d / 2)[1]) * 0.6
    return Part(f"{name}_contact", "#2a2030", polys=[ellipse(c[0], c[1], rx, ry)], shade=False, material="flat",
                blur=ry * 0.6, alpha=strength, blend="multiply", receive=False, depth=FLOOR)


def table(cam, name, x, z, w=1.2, d=0.8, h=0.74, top="#8a5a3a", legs=None, round_top=False):
    """A table centered on x, its front edge at depth z. round_top draws a round cafe table on one stem."""
    legs = legs or mix(top, "#120c0a", 0.35)
    parts = [contact(cam, name, x, z + d / 2, w, d)]
    if round_top:
        c = cam.P(x, h, z + d / 2)
        rx = cam.scale(z + d / 2) * w / 2
        ry = abs(cam.P(x, h, z)[1] - cam.P(x, h, z + d)[1]) / 2
        stem = cam.P([x, x], [0.04, h], [z + d / 2] * 2)
        base = cam.P(x, 0.02, z + d / 2)
        parts += [_flat(f"{name}_base", legs, [ellipse(base[0], base[1], rx * 0.45, max(ry * 0.45, 2.0))], line=_ink(0.6)),
                  Part(f"{name}_stem", legs, ribbon=Ribbon(stem, [(0, 0.03 * cam.scale(z)), (1, 0.03 * cam.scale(z))], step=3.0),
                       material="gloss", line=_ink(0.6)),
                  _flat(f"{name}_edge", _tone(top, "front"), [ellipse(c[0], c[1] + 0.03 * cam.scale(z), rx, max(ry, 2.0))],
                        line=_ink(0.7)),
                  _flat(f"{name}_top", _tone(top, "top"), [ellipse(c[0], c[1], rx, max(ry, 2.0))], line=_ink(0.7))]
        return placed(parts, z)
    t, lw = 0.05, 0.05
    for lx, lz in ((x - w / 2 + 0.04, z + d - 0.1), (x + w / 2 - 0.04 - lw, z + d - 0.1)):
        parts += box(cam, f"{name}_legb", lx, 0, lz, lw, h - t, lw, legs)
    for lx, lz in ((x - w / 2 + 0.04, z + 0.05), (x + w / 2 - 0.04 - lw, z + 0.05)):
        parts += box(cam, f"{name}_legf", lx, 0, lz, lw, h - t, lw, legs)
    parts += box(cam, f"{name}_top", x - w / 2, h - t, z, w, t, d, top)
    return placed(parts, z)


def chair(cam, name, x, z, color="#6b4a32", seat=0.45, facing="away"):
    """A chair seen from the front or the back: seat, four legs and a back rest. facing="away": the back rest
    stands on the far side (a sitter faces the camera); facing="toward": on the near side (we see its back)."""
    w, d, lw = 0.44, 0.42, 0.04
    parts = [contact(cam, name, x, z + d / 2, w, d, 0.22)]
    back_z = z + d - lw if facing == "away" else z
    rest = box(cam, f"{name}_rest", x - w / 2, seat + 0.18, back_z, w, 0.36, lw, mix(color, "#ffffff", 0.1))
    posts = []
    for px_ in (x - w / 2, x + w / 2 - lw):
        posts += box(cam, f"{name}_post", px_, seat, back_z, lw, 0.55, lw, color)
    legs_back, legs_front = [], []
    for px_ in (x - w / 2, x + w / 2 - lw):
        legs_back += box(cam, f"{name}_leg", px_, 0, z + d - lw, lw, seat, lw, color)
        legs_front += box(cam, f"{name}_leg", px_, 0, z, lw, seat, lw, color)
    seat_parts = box(cam, f"{name}_seat", x - w / 2, seat - 0.04, z, w, 0.04, d, color)
    if facing == "away":                                       # sat on from the front: behind its sitter
        return placed(parts + posts + rest + legs_back + legs_front + seat_parts, z + SIT_SHARE * d)
    return placed(parts + legs_back + legs_front + seat_parts + posts + rest, z)


def sofa(cam, name, x, z, w=2.0, d=0.9, color="#5b6f8f", seat=0.44):
    """A sofa against the back: a back rest, two arms and a seat with two cushions."""
    dark = mix(color, "#0c0a14", 0.2)
    parts = [contact(cam, name, x, z + d / 2, w, d, 0.35)]
    parts += box(cam, f"{name}_back", x - w / 2, 0.10, z + d - 0.22, w, 0.80, 0.22, dark)
    parts += box(cam, f"{name}_base", x - w / 2 + 0.16, 0.10, z, w - 0.32, seat - 0.24, d - 0.2, dark)
    for k in range(2):
        cw = (w - 0.32) / 2
        parts += box(cam, f"{name}_cushion{k}", x - w / 2 + 0.16 + k * cw, seat - 0.14, z + 0.02, cw, 0.14, d - 0.24, color)
    for sd in (-1, 1):
        ax = x - w / 2 if sd < 0 else x + w / 2 - 0.16
        parts += box(cam, f"{name}_arm{sd}", ax, 0.10, z, 0.16, seat + 0.18, d, dark)
    for k, lx in enumerate((x - w / 2 + 0.05, x + w / 2 - 0.10)):
        parts += box(cam, f"{name}_foot{k}", lx, 0.0, z + 0.04, 0.05, 0.10, 0.05, "#3a2a20")
    return placed(parts, z + SIT_SHARE * d)


def shelf(cam, name, x, z, w=1.0, h=1.8, d=0.32, color="#7b5636", rows=4, seed=0):
    """A bookcase against the back: a carcass, shelves and rows of book spines."""
    rng = np.random.default_rng(seed)
    parts = box(cam, f"{name}_case", x - w / 2, 0, z, w, h, d, color)
    spines = ("#8c3b3b", "#3b5b8c", "#c9a24a", "#4a7a5a", "#e8dccb", "#5a4a6a")
    inner = _tone(color, "front", 0.55)
    for r in range(rows):
        y0 = 0.08 + r * (h - 0.12) / rows
        y1 = y0 + (h - 0.12) / rows - 0.04
        cavity = cam.P([x - w / 2 + 0.04, x + w / 2 - 0.04, x + w / 2 - 0.04, x - w / 2 + 0.04], [y0, y0, y1, y1], [z] * 4)
        parts.append(_flat(f"{name}_cavity{r}", inner, [cavity]))
        bx = x - w / 2 + 0.06
        while bx < x + w / 2 - 0.10:
            bw, bh = rng.uniform(0.03, 0.06), (y1 - y0) * rng.uniform(0.62, 0.92)
            spine = cam.P([bx, bx + bw, bx + bw, bx], [y0, y0, y0 + bh, y0 + bh], [z] * 4)
            parts.append(_flat(f"{name}_book", spines[rng.integers(len(spines))], [spine], line=_ink(0.4, alpha=0.5)))
            bx += bw + rng.uniform(0.0, 0.012)
    return placed(parts, z)


def rug(cam, name, x, z, w, d, color="#c9a27e", border="#8a5a46"):
    """A rug flat on the floor: drawn under every standing thing (FLOOR)."""
    quad = cam.P([x - w / 2, x + w / 2, x + w / 2, x - w / 2], [0.005] * 4, [z, z, z + d, z + d])
    inner = cam.P([x - w / 2 + 0.12, x + w / 2 - 0.12, x + w / 2 - 0.12, x - w / 2 + 0.12], [0.006] * 4,
                  [z + 0.12, z + 0.12, z + d - 0.12, z + d - 0.12])
    return [_flat(f"{name}_rug", border, [quad], depth=FLOOR), _flat(f"{name}_field", color, [inner], depth=FLOOR)]


def plant(cam, name, x, z, h=1.1, pot="#c46a4a", leaf="#4f7f4a", seed=0):
    """A potted plant: a pot box and a cluster of leaves fanned out from its top."""
    rng = np.random.default_rng(seed)
    parts = [contact(cam, name, x, z + 0.15, 0.4, 0.3)] + box(cam, f"{name}_pot", x - 0.16, 0, z, 0.32, 0.34, 0.30, pot)
    root = cam.P(x, 0.32, z + 0.15)
    s = cam.scale(z)
    for k in range(9):
        a = np.radians(-70 + 140 * k / 8 + rng.uniform(-8, 8))
        length = h * rng.uniform(0.55, 0.95) * s
        tip = root + [np.sin(a) * length * 0.55, -np.cos(a) * length]
        mid = (root + tip) / 2 + [np.sin(a) * length * 0.12, 0]
        axis = catmull_rom(np.array([root, mid, tip]), samples=8)
        parts.append(Part(f"{name}_leaf", mix(leaf, "#ffffff", rng.uniform(0, 0.15)),
                          ribbon=Ribbon(axis, [(0, 0.012 * s), (0.5, 0.07 * s), (1, 0.0)], step=3.0),
                          material="matte", line=_ink(0.6, mix(leaf, "#0a140a", 0.6))))
    return placed(parts, z)


def floor_lamp(cam, name, x, z, h=1.6, shade="#f1e2c0", glow=0.5):
    s = cam.scale(z)
    pole = cam.P([x, x], [0.02, h - 0.15], [z, z])
    top = cam.P(x, h, z)
    cone = np.array([top + [-0.17 * s, 0.22 * s], top + [0.17 * s, 0.22 * s], top + [0.10 * s, -0.04 * s],
                     top + [-0.10 * s, -0.04 * s]])
    base = cam.P(x, 0.01, z)
    parts = [contact(cam, name, x, z, 0.3, 0.3),
             _flat(f"{name}_base", "#2f2a28", [ellipse(base[0], base[1], 0.14 * s, 0.035 * s)], line=_ink(0.5)),
             Part(f"{name}_pole", "#2f2a28", ribbon=Ribbon(pole, [(0, 0.012 * s), (1, 0.012 * s)], step=3.0), material="gloss")]
    if glow > 0:
        c = top + [0, 0.3 * s]
        parts += lit([_flat(f"{name}_glow", "#ffe2a8", [ellipse(c[0], c[1], 0.9 * s, 0.7 * s)], blur=0.35 * s,
                            alpha=glow * 0.35, blend="screen")])
    parts += lit([_flat(f"{name}_shade", shade, [cone], line=_ink(0.6), gradient=(tuple(cone[3]), mix(shade, "#000000", 0.08),
                                                                                  tuple(cone[0]), mix(shade, "#ffffff", 0.4)))])
    return placed(parts, z)


def pendant(cam, name, x, z, drop=0.9, ceiling=2.8, color="#2f3a3a", glow=0.6):
    """A pendant light hanging from the ceiling on a cord."""
    s = cam.scale(z)
    y = ceiling - drop
    cord = cam.P([x, x], [ceiling, y + 0.12], [z, z])
    c = cam.P(x, y, z)
    dome = np.array([c + [-0.16 * s, 0.0], c + [0.16 * s, 0.0], c + [0.08 * s, -0.13 * s], c + [-0.08 * s, -0.13 * s]])
    parts = [_flat(f"{name}_cord", "#222222", [dome], alpha=0.0, strokes=[Stroke(cord, width=max(1.0, 0.01 * s), color="#222222",
                                                                                   taper=(False, False))])]
    if glow > 0:
        bulb = c + [0, 0.02 * s]
        parts += lit([_flat(f"{name}_glow", "#ffdca0", [ellipse(c[0], c[1] + 0.25 * s, 0.7 * s, 0.6 * s)], blur=0.3 * s,
                            alpha=glow * 0.35, blend="screen"),
                      _flat(f"{name}_bulb", "#fff3d6", [ellipse(bulb[0], bulb[1], 0.06 * s, 0.03 * s)])])
    parts.append(_flat(f"{name}_dome", color, [dome], line=_ink(0.6)))
    return placed(parts, z)


def blackboard(cam, room, x0, x1, y0, y1, name="board", seed=0):
    """A green board on the back wall with a wooden frame, a chalk tray and a few chalk lines."""
    rng = np.random.default_rng(seed)
    z = room.depth - 0.02
    quad = cam.P([x0, x1, x1, x0], [y0, y0, y1, y1], [z] * 4)
    lines = []
    for k in range(4):                                          # chalk: a heading and three lines of writing
        yy = y1 - 0.18 - 0.22 * k
        xs = np.linspace(x0 + 0.25, x0 + 0.25 + (x1 - x0) * (0.55 if k else 0.35), 14)
        pts = cam.P(xs, yy + 0.02 * np.sin(np.arange(14) * 2.3 + rng.uniform(0, 3)), [z] * 14)
        lines.append(Stroke(pts, width=2.2 if k == 0 else 1.6, color="#eef2ea", alpha=0.75, taper=(True, True)))
    tray = cam.P([x0, x1, x1, x0], [y0 - 0.05, y0 - 0.05, y0, y0], [z - 0.06] * 4)
    return [_flat(f"{name}_frame", "#8a6a48", [quad], line=Line(7.0, color="#8a6a48", taper=False)),
            _flat(f"{name}_slate", "#2f4a3c", [quad], strokes=lines,
                  gradient=(tuple(quad[3]), "#355544", tuple(quad[1]), "#263d31")),
            _flat(f"{name}_tray", "#7a5a3a", [tray], line=_ink(0.6))]


# ---- outdoors ------------------------------------------------------------------------------------------
@dataclass
class Ground:
    """An open ground under the sky: grass to the horizon, a path toward the vanishing point."""
    cam: Camera
    sky_top: str = "#7fb3e6"
    sky_low: str = "#e7f0f2"
    grass: str = "#7fae5a"
    far_grass: str = "#a9c77f"
    path: str = "#d8c6a2"
    path_width: float = 2.2

    def parts(self):
        cam, W, H = self.cam, self.cam.width, self.cam.height
        hz = cam.horizon
        sky = np.array([(0, 0), (W, 0), (W, hz + 2), (0, hz + 2)], float)
        ground = np.array([(0, hz), (W, hz), (W, H), (0, H)], float)
        zn = cam.near_z() * 0.98
        hw = self.path_width / 2
        path = cam.P([-hw, hw, hw * 0.6, -hw * 0.6], [0, 0, 0, 0], [zn, zn, 400.0, 400.0])
        return [_flat("sky", self.sky_top, [sky], gradient=((0, 0), self.sky_top, (0, hz), self.sky_low)),
                _flat("ground", self.grass, [ground], gradient=((0, hz), self.far_grass, (0, H), self.grass)),
                _flat("path", self.path, [path], gradient=((0, hz), mix(self.path, "#ffffff", 0.2), (0, H), self.path),
                      line=_ink(0.6, alpha=0.4))]

    def treeline(self, z=60.0, height=7.0, color="#6f9a62", seed=0):
        """A band of distant trees along the horizon: overlapping round crowns, lighter with distance."""
        rng = np.random.default_rng(seed)
        cam = self.cam
        s = cam.scale(z)
        base = cam.P(0, 0, z)[1]
        crowns = []
        x = -cam.vp_x / s - 4
        while x < (cam.width - cam.vp_x) / s + 4:
            r = rng.uniform(0.35, 0.6) * height
            c = cam.P(x, height * rng.uniform(0.55, 0.85), z)
            crowns.append(ellipse(c[0], c[1], r * s, r * s * 0.9))
            x += r * rng.uniform(0.9, 1.3)
        fill = np.array([(0, base), (cam.width, base), (cam.width, base - height * 0.5 * s), (0, base - height * 0.5 * s)])
        return [_flat("treeline", color, crowns + [fill], blur=1.0)]


def tree(cam, name, x, z, height=5.0, crown="#5f8f4e", trunk="#6a4a34", seed=0):
    """A tree: a tapering trunk and a crown of clustered round leaf masses, lit from the upper left."""
    rng = np.random.default_rng(seed)
    s = cam.scale(z)
    stem = cam.P([x, x + 0.1, x], [0, height * 0.45, height * 0.62], [z] * 3)
    parts = [contact(cam, name, x, z, height * 0.5, height * 0.3, 0.30),
             Part(f"{name}_trunk", trunk, ribbon=Ribbon(catmull_rom(stem, samples=6), [(0, 0.16 * s), (1, 0.08 * s)], step=3.0),
                  material="matte", line=_ink(0.7))]
    center = cam.P(x, height * 0.72, z)
    r = height * 0.32 * s
    blobs = []
    for k in range(9):
        a = rng.uniform(0, 2 * np.pi)
        d = rng.uniform(0.2, 0.65) * r
        c = center + [np.cos(a) * d * 1.2, np.sin(a) * d * 0.8]
        blobs.append(ellipse(c[0], c[1], r * rng.uniform(0.45, 0.65), r * rng.uniform(0.40, 0.55)))
    # merged ink: only the outer edge of the clustered leaf masses is drawn, not each mass
    parts.append(Part(f"{name}_crown", crown, polys=blobs, material="matte", bulge=0.8, merge=f"{name}_crown",
                      line=_ink(0.8, mix(crown, "#0a140a", 0.6))))
    for k in range(5):                                          # lit leaf clumps on the upper left of the crown
        c = center + [-r * rng.uniform(0.1, 0.5), -r * rng.uniform(0.2, 0.6)]
        parts.append(_flat(f"{name}_lit", mix(crown, "#e8f0a0", 0.35), [ellipse(c[0], c[1], r * 0.22, r * 0.16)], blur=r * 0.05,
                           alpha=0.6, clip=f"{name}_crown"))
    return placed(parts, z)


BENCH_DEPTH = 0.51          # m from a bench's front edge to the back of its back rest


def bench(cam, name, x, z, w=1.6, color="#8a5a3a", frame="#2f3333"):
    """A park bench seen from the front: slats for the seat and the back, iron legs."""
    parts = [contact(cam, name, x, z + 0.25, w, 0.5, 0.3)]
    for k, lx in enumerate((x - w / 2 + 0.1, x + w / 2 - 0.16)):
        parts += box(cam, f"{name}_leg{k}", lx, 0, z + 0.05, 0.06, 0.45, 0.45, frame)
    for k in range(3):
        parts += box(cam, f"{name}_back{k}", x - w / 2, 0.55 + k * 0.13, z + 0.48, w, 0.09, 0.03, color)
    for k in range(3):
        parts += box(cam, f"{name}_slat{k}", x - w / 2, 0.42, z + 0.03 + k * 0.15, w, 0.04, 0.12, color)
    return placed(parts, z + SIT_SHARE * BENCH_DEPTH)          # sat on: behind its sitters


def lamp_post(cam, name, x, z, height=3.6, color="#2f3333"):
    s = cam.scale(z)
    pole = cam.P([x, x], [0, height], [z, z])
    head = cam.P(x, height + 0.15, z)
    return placed([contact(cam, name, x, z, 0.4, 0.4, 0.25),
                   Part(f"{name}_pole", color, ribbon=Ribbon(pole, [(0, 0.06 * s), (1, 0.035 * s)], step=3.0),
                        material="gloss", line=_ink(0.6)),
                   *lit([_flat(f"{name}_head", "#f6ecd2", [ellipse(head[0], head[1], 0.16 * s, 0.22 * s)], line=_ink(0.7))])],
                  z)


def rain(width, height, count=900, length=(16.0, 44.0), angle=8.0, color="#d6e4ff", alpha=(0.15, 0.45), seed=0,
         name="rain"):
    """Falling rain over the whole picture: thin streaks slanted by `angle` degrees. A streak's length,
    width and opacity grow together, so long bright streaks read as drops near the viewer."""
    rng = np.random.default_rng(seed)
    near = rng.uniform(0, 1, count) ** 2                          # most drops are far and faint
    lengths = length[0] + (length[1] - length[0]) * near
    a = np.radians(angle)
    d = np.array([np.sin(a), np.cos(a)])
    tops = np.stack([rng.uniform(-0.05, 1.05, count) * width, rng.uniform(-0.05, 1.0, count) * height], 1)
    strokes = [Stroke(np.array([p, p + d * n]), width=0.8 + 1.0 * k, color=color, alpha=alpha[0] + (alpha[1] - alpha[0]) * k,
                      taper=(True, False)) for p, n, k in zip(tops, lengths, near)]
    frame = np.array([(0, 0), (width, 0), (width, height), (0, height)], float)
    return _flat(name, color, [frame], alpha=0.0, strokes=strokes)


def splashes(cam, x_range, z_range, count=120, color="#d6e4ff", alpha=0.35, seed=0, name="splash"):
    """Rings where drops hit a wet floor: flat ellipses on the ground plane, smaller with distance."""
    rng = np.random.default_rng(seed)
    strokes = []
    for _ in range(count):
        z = cam.near_z() + (z_range[1] - cam.near_z()) * rng.uniform(0, 1) ** 2 if z_range[0] is None else \
            rng.uniform(*z_range)
        x = rng.uniform(*x_range)
        c = cam.P(x, 0.0, z)
        r = cam.scale(z) * rng.uniform(0.02, 0.045)
        ring = ellipse(c[0], c[1], r, r * 0.28)
        strokes.append(Stroke(np.vstack([ring, ring[:1]]), width=max(0.6, r * 0.12), color=color, alpha=alpha,
                              taper=(False, False)))
    frame = np.array([(0, 0), (cam.width, 0), (cam.width, cam.height), (0, cam.height)], float)
    return _flat(name, color, [frame], alpha=0.0, strokes=strokes)


def reflection(parts, ground_y, color="#b8a8d8", alpha=0.30, blur=3.0, squash=0.85, name="reflection"):
    """The mirror image of some parts in a wet floor: their shapes flipped about the ground line (a little
    shortened, as a reflection seen from above eye level of the floor) as one soft glowing silhouette.
    Add it before the parts it mirrors."""
    polys = []
    for q in parts:
        if q.alpha < 0.05 or q.blend != "normal":
            continue
        shapes = q.ribbon.polys() if q.ribbon is not None else (q.polys or [])
        for poly in shapes:
            poly = np.asarray(poly, float)
            polys.append(np.stack([poly[:, 0], ground_y + (ground_y - poly[:, 1]) * squash], 1))
    return _flat(name, color, polys, blur=blur, alpha=alpha, blend="screen")


def figure_shadow(cam, figure, z, strength=0.32):
    """Soft shadow on the floor under a standing or seated figure at depth z."""
    feet = [figure.joint(f"ankle_{side}") for side in ("left", "right")]
    x = (feet[0][0] + feet[1][0]) / 2
    y = cam.floor_y(z)
    span = abs(feet[0][0] - feet[1][0]) + 0.5 * figure.u
    return Part("figure_shadow", "#2a2030", polys=[ellipse(x + 0.1 * figure.u, y, span * 0.75, 0.12 * figure.u)], shade=False,
                material="flat", blur=0.08 * figure.u, alpha=strength, blend="multiply", receive=False)
