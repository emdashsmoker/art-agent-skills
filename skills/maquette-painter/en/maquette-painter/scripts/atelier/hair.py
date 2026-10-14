"""Hair: a scalp cap in the relief plus drawn locks anchored to the head.

The cap follows the skull, so the hair mass is right from every angle. Fringe and side locks
are 2D shapes whose roots sit on the head surface and therefore turn with the head.
Back hair hangs in screen space (gravity) from anchors on the skull.

Draw order matters and is handled by Character: back hair -> body relief -> face -> front hair.
"""
import numpy as np

from . import geom
from .core import to_rgb, trace_color
from .head import Surface

HAIRLINE_V = 0.74          # top of the forehead in head units above the head joint
NAPE_V = 0.05

BACK_STYLES = {
    #  length below crown (HU), flare, tips, tail, bun
    "long": dict(length=2.7, flare=0.10, tips=7, side=1.25, ears=False),
    "medium": dict(length=1.75, flare=0.08, tips=6, side=1.1, ears=False),
    "bob": dict(length=1.08, flare=0.05, tips=5, tuck=0.07, side=0.82, ears=False),
    "short": dict(length=0.86, flare=0.0, tips=5, tuck=0.10, side=0.55, ears=True),
    "ponytail": dict(length=0.0, tail=1.9, side=0.75, ears=True),
    "bun": dict(length=0.0, bun=True, side=0.0, ears=True),
    "updo": dict(length=0.0, bun=True, side=0.6, ears=True),
    "crop": dict(length=0.0, side=0.0, ears=True, volume=0.45, shell=True),   # short men's cut, close at the back and sides
    "beanie": dict(length=0.0, side=0.0, ears=True, volume=1.0, shell=True, knit=True),   # a knitted cap pulled low
}
# Hairline of a short cut: (degrees around the head from the middle of the forehead, height v). It rises a
# little at the temples, drops in front of the ear as a sideburn, clears the ear and runs down to the nape.
CROP_HAIRLINE = [(0, 0.75), (30, 0.756), (52, 0.785), (62, 0.72), (72, 0.60), (80, 0.46), (90, 0.43), (97, 0.53),
                 (122, 0.54), (140, 0.28), (160, 0.10), (180, 0.06)]
# Edge of a knitted cap: low on the forehead, just over the top of the ears, down over the back of the skull.
BEANIE_LINE = [(0, 0.66), (40, 0.65), (70, 0.56), (90, 0.52), (120, 0.4), (150, 0.26), (180, 0.22)]
BEANIE_CUFF = 0.13          # height of the folded-up brim (head units)
FRINGE_STYLES = ("swept", "straight", "parted", "wispy", "curtain", "none", "side_part", "quiff", "textured")
SHORT_FRINGES = ("side_part", "quiff", "textured")          # short top hair; pair with the "crop" back


def _fringe(style, rng, side):
    """Locks of the fringe as (path, half-widths, hanging length).

    A path is [(angle around the head in degrees, height v)]: angle 0 is the middle of the face, +90 the
    figure's left temple. Paths start in the scalp, so every lock follows the skull and turns with the head.
    A hanging length lets the lock fall on past its last point, pulled by gravity.
    A point may carry a third value: how far the lock stands off the scalp there (a lifted quiff).
    """
    locks = []
    fall = max(side - 0.62, 0.0)
    if style in ("parted", "curtain"):          # centre part; the hair sweeps to both temples and falls beside the face
        for s in (-1, 1):
            if style == "curtain":              # long bangs that open over the forehead and close in on the cheeks
                locks.append(([(3 * s, 0.93), (13 * s, 0.80), (32 * s, 0.63), (54 * s, 0.45), (68 * s, 0.27)],
                              [0.035, 0.06, 0.07, 0.055, 0.012], 0.0))
            locks.append(([(5 * s, 0.93), (22 * s, 0.84), (44 * s, 0.70), (64 * s, 0.54), (78 * s, 0.38), (84 * s, 0.22)],
                          [0.04, 0.07, 0.08, 0.075, 0.068, 0.06 if fall else 0.012], fall))
            locks.append(([(14 * s, 0.93), (40 * s, 0.86), (66 * s, 0.72), (86 * s, 0.54), (94 * s, 0.36), (97 * s, 0.22)],
                          [0.04, 0.07, 0.085, 0.085, 0.08, 0.07 if fall else 0.012], fall * 0.92))
    elif style == "swept":                      # side part on the figure's right, bangs sweeping across to the left
        locks += [([(-30, 0.93), (-8, 0.78), (16, 0.64), (40, 0.55), (60, 0.47)], [0.04, 0.07, 0.075, 0.06, 0.01], 0.0),
                  ([(-28, 0.93), (0, 0.84), (30, 0.72), (56, 0.62), (76, 0.50)], [0.04, 0.07, 0.08, 0.07, 0.012], 0.0),
                  ([(-32, 0.93), (-18, 0.74), (-4, 0.60), (8, 0.53)], [0.035, 0.06, 0.05, 0.008], 0.0),
                  ([(-22, 0.93), (14, 0.88), (50, 0.80), (80, 0.66), (94, 0.46)], [0.04, 0.07, 0.085, 0.08, 0.02], 0.0),
                  ([(-38, 0.93), (-58, 0.80), (-76, 0.62), (-86, 0.42)], [0.04, 0.07, 0.08, 0.015], 0.0),
                  ([(-36, 0.93), (-46, 0.74), (-56, 0.58), (-62, 0.48)], [0.035, 0.05, 0.04, 0.008], 0.0)]
    elif style == "straight":                   # blunt bangs cut above the brows
        for angle in np.linspace(-66, 66, 11):
            tip = 0.53 + rng.uniform(-0.012, 0.012) + 0.04 * (abs(angle) / 66) ** 2
            locks.append(([(angle * 0.8, 0.93), (angle * 0.95, 0.74), (angle, tip)], [0.045, 0.062, 0.05], 0.0))
    elif style == "wispy":                      # thin separate strands over the forehead
        for angle in np.linspace(-58, 58, 9):
            tip = 0.52 + rng.uniform(-0.03, 0.04)
            locks.append(([(angle * 0.7, 0.93), (angle * 0.9, 0.74), (angle + rng.uniform(-6, 6), tip)], [0.03, 0.04, 0.007], 0.0))
    elif style == "side_part":                  # part on the figure's right; the top is combed across to the left
        locks.append(([(-36, 0.93), (-20, 0.84, 0.02), (6, 0.795, 0.03), (32, 0.785, 0.025), (56, 0.775, 0.012), (68, 0.75)],
                      [0.03, 0.05, 0.058, 0.055, 0.045, 0.012], 0.0))          # the front edge, lifted a little
        for k in range(5):
            end = 30 + k * 11 + rng.uniform(-4, 4)
            v_end = 0.82 + 0.02 * k
            locks.append(([(-40 + k, 0.93), (-18 + k * 3, 0.92, 0.012), (end * 0.6, v_end + 0.035, 0.012), (end, v_end)],
                          [0.03, 0.055, 0.06, 0.012], 0.0))
        for a in (-54, -66, -78):               # below the part the hair is combed down to the temple
            locks.append(([(-42, 0.93), (a, 0.88, 0.008), (a - 6, 0.78)], [0.03, 0.05, 0.01], 0.0))
    elif style == "quiff":                      # front hair brushed up and back, standing off the forehead
        for a in np.linspace(-48, 48, 7):
            root = 0.75 + 0.02 * (abs(a) / 48) ** 2
            locks.append(([(a, root), (a * 0.94, root + 0.05, 0.055), (a * 0.82, 0.87, 0.07), (a * 0.68, 0.92, 0.03)],
                          [0.05, 0.068, 0.062, 0.02], 0.0))
        for s in (-1, 1):
            locks.append(([(58 * s, 0.77), (54 * s, 0.86, 0.025), (44 * s, 0.92)], [0.04, 0.05, 0.015], 0.0))
    elif style == "textured":                   # short choppy front, a few pieces falling onto the forehead
        for a in np.linspace(-52, 52, 7) + rng.uniform(-5, 5, 7):
            tip = 0.665 + rng.uniform(-0.015, 0.045) + 0.05 * (abs(a) / 52) ** 2
            bend = rng.uniform(-10, 10) + 0.12 * a
            locks.append(([(a * 0.55, 0.93), (a * 0.82, 0.86, 0.025), (a * 0.95 + bend * 0.5, 0.76, 0.012), (a + bend, tip)],
                          [0.035, 0.06, 0.055, 0.008], 0.0))
    if style in SHORT_FRINGES:                  # short sideburns
        for s in (-1, 1):
            locks.append(([(80 * s, 0.80), (86 * s, 0.62), (88 * s, 0.48)], [0.03, 0.035, 0.012], 0.0))
    if style not in ("parted", "curtain") and side > 0:      # locks in front of the ears
        for s in (-1, 1):
            locks.append(([(74 * s, 0.86), (84 * s, 0.60), (88 * s, 0.36), (88 * s, 0.24)], [0.04, 0.065, 0.065, 0.055 if fall else 0.012], fall))
            if fall > 0.3:
                locks.append(([(92 * s, 0.86), (100 * s, 0.58), (102 * s, 0.32), (101 * s, 0.22)], [0.04, 0.07, 0.07, 0.06], fall * 0.9))
    return locks


class Hair:
    """style: key of BACK_STYLES. fringe: key of FRINGE_STYLES. side: side-lock length in HU (0 = none).
    Short men's hair: style "crop" with fringe "side_part", "quiff" or "textured".

    volume lifts the cap off the skull; wave (0..1) adds curl to hanging hair; sway shifts the hang.
    """

    def __init__(self, style="long", fringe="swept", color="#3e2f45", side=None, volume=None, wave=0.0,
                 sway=0.0, length=None, seed=1, gloss=0.55, strand=0.3, ring=0.0):
        self.spec = dict(BACK_STYLES[style])
        volume = self.spec.get("volume", 1.0) if volume is None else volume
        if self.spec.get("knit"):                   # wool is matte and has no strands
            gloss, strand, ring = 0.0, 0.0, 0.0
        if length is not None:
            self.spec["length"] = length
        self.style, self.fringe = style, fringe
        self.color = to_rgb(color)
        self.side = self.spec["side"] if side is None else side
        self.volume, self.wave, self.sway = volume, wave, sway
        self.rng = np.random.default_rng(seed)
        self.gloss, self.strand, self.ring = gloss, strand, ring
        self.outline = True          # ink lines between overlapping locks (graphic styles); painted hair reads as one mass
        self.limit = None            # optional canvas mask: hanging hair is only painted inside it (another figure in front)

    # ----- relief part -----
    def prepare(self, figure):
        """Add the scalp cap (and bun) to the figure's masses. Call before the relief is built."""
        surface = Surface(figure)
        rot, hs = figure.R["head"], figure.head_scale
        figure.ears = self.spec["ears"]
        figure.extra_masses = [m for m in figure.extra_masses if m.get("tag") != "hair"]
        figure.late["hair"] = self.locks
        if self.spec.get("shell"):
            figure.extra_masses.append(dict(part="hair", group="hair", tag="hair", surface=self._shell(figure)))
            return self
        rows = []
        for y in np.linspace(NAPE_V, surface.y_max, 16):
            w, zf, zb = float(surface.w(y)), float(surface.zf(y)), float(surface.zb(y))
            if y >= HAIRLINE_V:
                front = zf + 0.03
            elif y >= 0.30:
                t = (y - 0.30) / (HAIRLINE_V - 0.30)
                front = -0.02 + (zf + 0.03 + 0.02) * t ** 1.6
            else:
                front = -0.14 + 0.12 * (y - NAPE_V) / (0.30 - NAPE_V)
            back = zb - (0.03 + 0.05 * self.volume)
            lift = 0.035 * self.volume * np.clip((y - 0.6) / 0.3, 0, 1)
            rows.append((y + lift, w * (1 + 0.07 * self.volume) + 0.012, front, back))
        rows = np.array(rows)
        points = np.array([figure.head_point((0, y, (zf + zb) / 2)) for y, _, zf, zb in rows])
        figure.extra_masses.append(dict(part="hair", group="hair", tag="hair", points=points,
                                        lateral=rot @ [1, 0, 0], sagittal=rot @ [0, 0, 1],
                                        width=rows[:, 1] * hs, front=np.maximum((rows[:, 2] - rows[:, 3]) / 2, 0.02) * hs))
        if self.spec.get("bun"):
            centre = (0, 0.80, -0.44) if self.style == "bun" else (0, 0.62, -0.50)
            figure.extra_masses.append(dict(part="hair", group="hair", tag="hair", centre=figure.head_point(centre),
                                            axes=rot, radii=np.array([0.19, 0.17, 0.17]) * hs * (0.9 + 0.2 * self.volume)))
        return self

    def _shell(self, figure):
        """Close-cut hair as a skin of even thickness over the skull, bounded by a drawn hairline.

        The skull grid is pushed out along its normals inside the hairline and sunk under the skin
        outside it, so the hairline is a clean edge that curves over the temples and around the ears.
        """
        from .head import head_grid
        local = head_grid(figure.head_profile, None, columns=360)
        n, m = local.shape[:2]
        theta = np.degrees(np.abs(np.linspace(-np.pi, np.pi, m + 0)))[None, :]
        v = local[..., 1]
        knots = np.array(BEANIE_LINE if self.spec.get("knit") else CROP_HAIRLINE)
        line = np.interp(theta, knots[:, 0], knots[:, 1])
        normal = np.cross(np.gradient(local, axis=1), np.gradient(local, axis=0))
        length = np.linalg.norm(normal, axis=2, keepdims=True)
        radial = local - np.array([0.0, 0.42, 0.0])
        radial /= np.linalg.norm(radial, axis=2, keepdims=True) + 1e-9
        normal = np.where(length > 1e-9, normal / np.maximum(length, 1e-12), radial)
        width = np.abs(local[..., 0]).max(axis=1, keepdims=True)
        top = np.clip((v - 0.55) / 0.25, 0, 1)
        thick = (0.012 + 0.07 * width * self.volume) * top + (0.010 + 0.02 * self.volume) * (1 - top)
        thick *= 0.6 + 0.4 * np.clip((v - 0.06) / 0.2, 0, 1)                  # thinner at the nape
        if self.spec.get("knit"):                   # wool stands off the head, rises to a soft crown, rolls at the cuff
            cuff = np.clip(1 - (v - line) / BEANIE_CUFF, 0, 1) * (v > line)
            thick = 0.026 + 0.035 * top ** 2 * self.volume + 0.016 * cuff
        ramp = np.clip((v - line) / 0.03, 0, 1)
        ramp = ramp * ramp * (3 - 2 * ramp)
        offset = thick * ramp - 0.04 * (1 - ramp)
        shell = local + normal * offset[..., None]
        return figure.P["head"] + (shell * figure.head_scale) @ figure.R["head"].T

    # ----- helpers -----
    def _bind(self, view):
        self.view, self.figure, self.canvas = view, view.figure, view.canvas
        self.surface = Surface(self.figure)
        self.unit = view.unit * self.figure.head_scale
        self.lw = self.unit * 0.011

    def _local(self, x, y, z):
        return tuple(self.view.to_canvas(self.figure.head_point((x, y, z))))

    def _on_face(self, u, v, lift=0.05):
        return self._local(u, v, self.surface.z(u, v) + lift)

    def _add(self, shape, shade=1.0, bulge=None, outline=True, clip=None, cast=None, relief=0.9, keep=0.0):
        color = np.clip(self.color * shade, 0, 1)
        self.canvas.add(shape, color, "hair", form="round", bulge=bulge or self.unit * 0.06, relief=relief, keep_normal=keep,
                        gloss=self.gloss, outline=(self.lw, trace_color(self.color)) if outline else None,
                        clip=clip, cast=cast)

    def _limited(self, shape):
        mask = self.canvas.mask(shape)
        return mask if self.limit is None else mask * self.limit

    def _edge_lines(self, shape, skip_above):
        """Ink a shape's outline only below a screen height (keeps roots seamless)."""
        mask = np.zeros((self.canvas.H, self.canvas.W), np.float32)
        mask[int(skip_above * self.canvas.scale):] = 1.0
        self.canvas.ink(shape, trace_color(self.color), stroke=self.lw, clip=mask)

    # ----- behind the body -----
    def draw_back(self, view):
        self._bind(view)
        spec, unit = self.spec, self.unit
        if spec.get("tail"):
            self._tail(spec["tail"])
        length = spec.get("length", 0.0)
        if length <= 0:
            return self
        crown = np.array(self._local(0, 0.93, -0.05))

        def rim(v, reach):
            """Outermost points (left, right on screen) of the back half of the skull at height v."""
            ring = [self._local(reach * np.sin(a), v, -0.04 + (reach + 0.08) * np.cos(a)) for a in np.radians(np.linspace(84, 276, 33))]
            ring = np.array(ring)
            return ring[ring[:, 0].argmin()], ring[ring[:, 0].argmax()]
        left, right = rim(0.50, 0.40)
        top_left, top_right = rim(0.86, 0.30)
        bottom = crown[1] + length * unit
        sway = self.sway * unit
        flare, tuck = spec.get("flare", 0.0) * unit, spec.get("tuck", 0.0) * unit
        steps = 7

        def side_run(anchor, sign):
            run = [tuple(anchor)]
            for i in range(1, steps + 1):
                t = i / steps
                y = anchor[1] + (bottom - anchor[1]) * t
                x = anchor[0] + sign * (flare * np.sin(t * np.pi * 0.9) + unit * 0.03) - sign * tuck * t ** 3 + sway * t ** 1.5
                x += self.wave * unit * 0.07 * np.sin(t * np.pi * 3.2 + (0 if sign < 0 else 1.3))
                run.append((x, y))
            return run
        left_run, right_run = side_run(left, -1), side_run(right, 1)
        tips = spec.get("tips", 6)
        x0, x1 = left_run[-1][0], right_run[-1][0]
        hem = [left_run[-1]]
        for i in range(tips):
            xa = x0 + (x1 - x0) * (i + 0.5) / tips
            xb = x0 + (x1 - x0) * (i + 1) / tips
            drop = unit * (0.10 + 0.07 * self.rng.random())
            hem.append((xa + sway * 0.2, bottom + drop))
            hem.append((xb, bottom - unit * 0.04 * (i < tips - 1)))
        top = [tuple(right), tuple(top_right), tuple(crown), tuple(top_left), tuple(left)]
        hem_runs = [[hem[i], hem[i + 1]] for i in range(len(hem) - 1)]
        shape = geom.runs([left_run] + hem_runs + [right_run[::-1], top])
        self._add(shape, shade=0.82, bulge=unit * 0.16, clip=self.limit)
        for i in range(tips + 3):                                   # strand lines follow the fall
            t = (i + 0.5) / (tips + 3)
            xa = left[0] + (right[0] - left[0]) * t
            xb = x0 + (x1 - x0) * t
            mid_y = (left[1] + bottom) / 2
            strand = [(xa, left[1] + unit * 0.1), ((xa + xb) / 2 + self.wave * unit * 0.05 * np.sin(i), mid_y), (xb, bottom)]
            self.canvas.stroke(strand, self.lw * 0.8, trace_color(self.color), alpha=0.5, clip=self._limited(shape))
        return self

    def _tail(self, length):
        unit = self.unit
        root = np.array(self._local(0, 0.66, -0.50))
        sway = (self.sway + 0.25 * np.sign(self.figure.R["head"][0, 2] + 1e-6)) * unit
        pts = [tuple(root)]
        for i in range(1, 6):
            t = i / 5
            pts.append((root[0] + sway * t ** 1.4 + self.wave * unit * 0.06 * np.sin(t * 7), root[1] + length * unit * t))
        shape = geom.ribbon(pts, np.array([0.16, 0.24, 0.26, 0.22, 0.14, 0.0]) * unit)
        self._add(shape, shade=0.85, bulge=unit * 0.1, clip=self.limit)
        self.canvas.stroke(pts, self.lw * 0.8, trace_color(self.color), alpha=0.5, clip=self._limited(shape))

    # ----- locks on the head (relief) -----
    def locks(self, view):
        """Fringe and side locks as flat swept forms lying on the skull; hanging ends fall with gravity.

        They are part of the relief, so they overlap the face correctly from any angle, cast their own
        shadow on the forehead and never show the face through them. Each wide lock is laid as a few
        narrower strands side by side, which gives the mass its ridges.
        """
        figure = view.figure
        surface = Surface(figure)
        rot, hs = figure.R["head"], figure.head_scale
        specs = []
        for pts, widths, hang in _fringe(self.fringe, self.rng, self.side):
            phase = self.rng.uniform(0, 6.28)            # strands of one lock wave together
            count = 3 if max(widths) > 0.055 else 1
            for j in range(count):
                offset = (j - (count - 1) / 2) / count                    # position across the lock, -0.33 .. 0.33
                reach = hang * (1.0 if j == count // 2 else self.rng.uniform(0.84, 0.97))
                squeeze = self.rng.uniform(0.85, 1.0) if j != count // 2 else 1.0
                strand = []
                for i, (angle, v, *rise) in enumerate(pts):
                    w = max(float(surface.w(np.clip(v, surface.y_min, surface.y_max))), 0.08)
                    spread = np.degrees(widths[i] * 1.5 * offset / w)       # sideways shift expressed as an angle
                    strand.append((angle + spread, v + (1 - squeeze) * 0.3 * (i == len(pts) - 1), rise[0] if rise else 0.0))
                specs.append((strand, [wd * (0.62 if count > 1 else 1.0) for wd in widths], reach, phase + 0.3 * j))
        out, self.paths = [], []
        for index, (pts, widths, hang, phase) in enumerate(specs):
            lift = 0.004 + 0.004 * (index % 3)                       # neighbouring strands lie at different heights
            world, sag = [], []
            for theta, v, rise in pts:
                t = np.radians(theta + self.rng.normal(0, 0.8))
                vc = np.clip(v, surface.y_min, surface.y_max)
                w, zf, zb = float(surface.w(vc)), float(surface.zf(vc)), float(surface.zb(vc))
                centre, depth = (zf + zb) / 2, (zf - zb) / 2
                on_scalp = np.clip((v - (HAIRLINE_V - 0.14)) / 0.14, 0, 1)
                emerge = np.clip((0.88 - v) / 0.2, 0, 1)                  # the root grows out from under the scalp hair
                off = (0.012 + 0.07 * w * self.volume) * on_scalp + lift * emerge - 0.03 * (1 - emerge) + rise
                world.append(figure.head_point(((w + off) * np.sin(t), v, centre + (depth + off) * np.cos(t))))
                normal = np.array([np.sin(t) / w, 0.0, np.cos(t) / depth])
                sag.append(rot @ (normal / np.linalg.norm(normal)))
            widths = list(widths)
            if hang > 0:
                steps = max(int(hang / 0.1), 3)
                out_dir = sag[-1] * [1, 0, 1]
                out_dir /= np.linalg.norm(out_dir) + 1e-9
                point = world[-1]
                for i in range(1, steps + 1):
                    t = i / steps
                    point = point + np.array([self.sway * 0.5 * t, -1.0, 0.0]) * hang * hs / steps
                    world.append(point + out_dir * self.wave * 0.03 * hs * np.sin(t * 6 + phase)
                                 + np.cross(out_dir, [0, 1, 0]) * self.wave * 0.05 * hs * np.sin(t * 5 + phase))
                    sag.append(out_dir)
                    widths.append(widths[len(pts) - 1] * (1 - t ** 1.5) + 0.004)
            world, sag = np.array(world), np.array(sag)
            tangent = np.gradient(world, axis=0)
            lateral = np.cross(tangent, sag)
            lateral /= np.linalg.norm(lateral, axis=1, keepdims=True) + 1e-9
            widths = np.array(widths) * hs * (0.9 + 0.2 * self.volume)
            thick = np.minimum(0.015 * hs, widths * 0.6)
            name = f"hair_lock{index}"
            self.paths.append((name, world))
            out.append(dict(part=name, group="hair", tag="hair", points=world, lateral=lateral, sagittal=sag,
                            width=widths, front=thick, back=thick * 0.5, roundness=1.0))
        return out

    # ----- finish on top of the relief -----
    def draw_front(self, view, eye_top=None, own=None):
        """Strand streaks, the parting line and the graphic highlight band.

        own: optional canvas mask of this figure's hair, so a second figure's hair is left alone.
        """
        self._bind(view)
        if self.spec.get("knit"):
            self._ribs(own)
            return self
        self.strands(self.strand, own)
        if self.outline:                                # graphic styles: one drawn line down each visible lock
            line = trace_color(self.color)
            for name, world in getattr(self, "paths", []):
                mask = view.part_mask(name)
                if mask.max() > 0.5:
                    pts = [tuple(p) for p in view.to_canvas(world)]
                    self.canvas.stroke(pts, self.lw * 0.8, line, start=0.9, end=0.6, alpha=0.5, clip=(mask > 0.5).astype(np.float32))
        if self.ring and self.unit > 140:              # a small head reads better without the highlight band
            self._ring()
        return self

    def _ribs(self, own=None):
        """Knitted ribs running up the cap and the fold line of the cuff, on the side facing the viewer."""
        canvas, figure = self.canvas, self.figure
        mask = (canvas.region == canvas.region_id("hair")).astype(np.float32)
        if own is not None:
            mask *= own
        knots = np.array(BEANIE_LINE)
        rot = figure.R["head"]
        ink = trace_color(self.color)

        def point(theta, v, lift):
            vc = np.clip(v, self.surface.y_min, self.surface.y_max)
            w, zf, zb = float(self.surface.w(vc)), float(self.surface.zf(vc)), float(self.surface.zb(vc))
            t = np.radians(theta)
            normal = rot @ np.array([np.sin(t) / max(w, 1e-3), 0.0, np.cos(t) / max((zf - zb) / 2, 1e-3)])
            world = figure.head_point(((w + lift) * np.sin(t), v, (zf + zb) / 2 + ((zf - zb) / 2 + lift) * np.cos(t)))
            return tuple(self.view.to_canvas(world)), normal[2] > 0.05
        for theta in np.arange(-170, 180, 7):
            edge = float(np.interp(abs(theta), knots[:, 0], knots[:, 1]))
            pts = [point(theta, edge + d, 0.06) for d in np.linspace(0.01, BEANIE_CUFF - 0.01, 4)]
            if all(seen for _, seen in pts):
                canvas.stroke([p for p, _ in pts], self.lw * 0.7, ink, start=0.5, end=0.5, alpha=0.55, clip=mask)
        fold = [point(theta, float(np.interp(abs(theta), knots[:, 0], knots[:, 1])) + BEANIE_CUFF, 0.075)
                for theta in np.arange(-176, 180, 4)]
        run = []
        for p, seen in fold + [((0, 0), False)]:
            if seen:
                run.append(p)
            elif len(run) > 1:
                canvas.stroke(run, self.lw, ink, start=0.8, end=0.8, alpha=0.8, clip=mask)
                run = []
            else:
                run = []

    def _ring(self):
        """Graphic highlight band across the crown (the anime 'angel ring'), broken into uneven teeth."""
        canvas = self.canvas
        hair_mask = (canvas.region == canvas.region_id("hair")).astype(np.float32)
        top, bottom = [], []
        us = np.linspace(-0.30, 0.22, 15)
        for i, u in enumerate(us):
            arc = 0.80 + 0.05 * (1 - (u / 0.34) ** 2)
            top.append(self._on_face(u, arc + (0.012 if i % 2 else 0.03), 0.07))
            bottom.append(self._on_face(u + 0.012, arc - self.rng.uniform(0.03, 0.075) * (1.0 if i % 2 else 0.45), 0.07))
        band = geom.polygon(top + bottom[::-1])
        light = np.clip(self.color * 1.9 + 0.22, 0, 1)
        canvas.tint(band, light, alpha=0.55 * self.ring, clip=hair_mask)

    def strands(self, strength=0.3, own=None):
        """Strand texture: streaks that run along each lock, so light breaks up the way it does on real hair.

        Noise is smeared along the hair's flow (line integral convolution); the streaks then tilt the
        surface sideways and vary the colour a little.
        """
        import cv2
        canvas = self.canvas
        mask = canvas.region == canvas.region_id("hair")
        if own is not None:
            mask &= own > 0.5
        if not mask.any() or strength <= 0:
            return
        ys, xs = np.nonzero(mask)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        h, w = y1 - y0, x1 - x0
        scale = self.unit * canvas.scale
        flow = getattr(self.view, "flow", None)
        flow = np.zeros((h, w, 2), np.float32) if flow is None else flow[y0:y1, x0:x1].copy()
        still = np.linalg.norm(flow, axis=2) < 0.3
        flow[still] = (0.0, 1.0)                                   # hair drawn as flat shapes hangs straight down
        flow /= np.linalg.norm(flow, axis=2, keepdims=True)
        flow = cv2.GaussianBlur(flow, (0, 0), max(scale * 0.01, 1.0))
        cell = max(scale * 0.012, 1.0)
        noise = cv2.resize(self.rng.standard_normal((max(int(h / cell), 2), max(int(w / cell), 2))).astype(np.float32),
                           (w, h), interpolation=cv2.INTER_CUBIC)
        gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        steps = int(np.clip(scale * 0.22 / (cell * 0.6), 6, 48))
        total = noise.copy()
        reach = scale * 0.22 / steps
        for k in range(1, steps + 1):
            for sign in (-1, 1):
                step = float(sign * k * reach)
                total += cv2.remap(noise, (gx + flow[..., 0] * step).astype(np.float32), (gy + flow[..., 1] * step).astype(np.float32),
                                   cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        local = mask[y0:y1, x0:x1]
        total = (total - total[local].mean()) / (total[local].std() + 1e-6)
        tilt = np.clip(total * 0.22 * strength, -0.6, 0.6)
        canvas.normal[y0:y1, x0:x1, 0][local] += (-flow[..., 1] * tilt)[local]
        canvas.normal[y0:y1, x0:x1, 1][local] += (flow[..., 0] * tilt)[local]
        tone = np.clip(1 + total * 0.16 * strength, 0.6, 1.4)[..., None]
        canvas.albedo[y0:y1, x0:x1][local] = np.clip(canvas.albedo[y0:y1, x0:x1] * tone, 0, 1)[local]
