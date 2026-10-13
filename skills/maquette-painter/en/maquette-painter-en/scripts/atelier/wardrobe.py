"""Wardrobe: garments built as shells around the body masses.

A garment reuses the body's own construction rows with some ease added, so it fits any build
and follows any pose. Loose pieces (skirt, drape) are swept from the pelvis toward the legs.
Each garment becomes its own relief part and canvas region.
"""
import numpy as np

ARM_TOP_Y, ELBOW_Y, WRIST_Y = 6.38, 5.06, 3.98
LAYER_EASE = 0.014
LEG_TOP_Y, KNEE_Y, ANKLE_Y = 4.08, 2.14, 0.40
DRESS_BODICE_LOW = 4.5      # the bodice runs down inside the skirt, so no skin shows where the two meet


class Garment:
    def __init__(self, name, color, builder, gloss=0.0, folds=0.5, detail=None):
        self.name, self.color, self.builder, self.gloss, self.folds = name, color, builder, gloss, folds
        self.detail = detail          # optional f(garment, view, line_width): collars, openings, buttons

    def draw_details(self, view, line_width):
        if self.detail:
            self.detail(self, view, line_width)

    def masses(self, figure, layer=0):
        """layer: position in the outfit; outer layers get a little more ease so they always sit on top."""
        self.layer_ease = LAYER_EASE * layer
        out = self.builder(figure, self.layer_ease)
        for mass in out:
            mass.update(part=self.name, group=self.name, tag="garment")
        return out


def _slice(figure, table_name, side, lo, hi, ease, scale=1.0):
    """Rows of a body table between rest heights lo..hi, grown by `ease` head units."""
    rows = figure.spec["masses"][table_name]
    ys = np.array([r[1][1] for r in rows])
    order = np.argsort(ys)
    rows = [rows[i] for i in order]
    ys = ys[order]
    lo, hi = max(lo, ys[0]), min(hi, ys[-1])
    if hi <= lo:
        return None
    picked = []
    for target in [lo] + [y for y in ys if lo < y < hi] + [hi]:
        i = int(np.clip(np.searchsorted(ys, target) - 1, 0, len(ys) - 2))
        t = (target - ys[i]) / (ys[i + 1] - ys[i])
        a, b = rows[i], rows[i + 1]
        pos = tuple(np.array(a[1]) * (1 - t) + np.array(b[1]) * t)
        vals = [a[k] * (1 - t) + b[k] * t for k in (2, 3, 4)]
        picked.append((a[0] if t < 0.5 else b[0], pos, *[v + ease for v in vals]))
    limb = scale if table_name in ("torso", "neck") else figure.spec["limb"] * scale
    return figure._nodes(picked, side, limb * figure.slim)


def _bumps(figure, lo, hi, ease, parts):
    """Single-ellipsoid body masses (belly, hip bones, bust, buttocks, kneecaps) that lie within lo..hi, grown by ease.

    A garment must wrap these as well as the swept rows, or the body shows through the cloth.
    """
    out = []
    for mass in figure._body_masses():
        if not (mass["part"].startswith(parts) and lo <= mass.get("rest_y", -1) <= hi):
            continue
        grow = ease * (0.5 if mass["rest_y"] > 6.3 else 1.0) * figure.k     # keep the shoulder line from puffing up
        if "centre" in mass:
            out.append(dict(centre=mass["centre"], axes=mass["axes"], radii=mass["radii"] + grow))
        else:           # swept soft tissue (bust, seat): the same sweep, thicker
            back = mass.get("back", mass["front"])
            out.append(dict(points=mass["points"], lateral=mass["lateral"], sagittal=mass["sagittal"],
                            roundness=mass.get("roundness", 0.8), width=mass["width"] + grow,
                            front=mass["front"] + grow, back=back + grow))
    return out


def _torso_shell(figure, lo, hi, ease, bust=True):
    out = [_slice(figure, "torso", "l", lo, hi, ease)]
    out += _bumps(figure, lo, hi, ease, ("torso", "buttock_", "chest_") + (("breast_",) if bust else ()))
    if bust and hi > 5.9 and lo < 6.0 and figure.sex == "female" and figure.bust > 0:
        # Cloth bridges the bust: it spans both sides as one broad form.
        size = 0.75 + 0.25 * figure.bust
        out.append(dict(centre=figure.world("chest", (0, 6.0, figure.surface_z(6.0) - 0.04 + 0.05 * (figure.bust - 1))), axes=figure.R["chest"],
                        radii=(np.array([0.44, 0.22, 0.20]) * size + ease) * figure.k))
    return [m for m in out if m is not None]


def _sleeves(figure, end_y, ease):
    out = []
    for side in ("l", "r"):
        out.append(_slice(figure, "upper_arm", side, max(end_y, ELBOW_Y), ARM_TOP_Y + 0.1, ease))
        if end_y < ELBOW_Y:
            out.append(_slice(figure, "forearm", side, end_y, ELBOW_Y, ease))
    out += _bumps(figure, max(end_y, ELBOW_Y), ARM_TOP_Y + 0.1, ease, ("upper_arm_",))      # deltoid caps of a male build
    return [m for m in out if m is not None]


def _legs(figure, end_y, ease):
    out = []
    for side in ("l", "r"):
        out.append(_slice(figure, "thigh", side, max(end_y, KNEE_Y), LEG_TOP_Y + 0.1, ease))
        if end_y < KNEE_Y:
            out.append(_slice(figure, "shin", side, end_y, KNEE_Y, ease))
    out += _bumps(figure, end_y, LEG_TOP_Y + 0.1, ease, ("thigh_", "buttock_"))
    return [m for m in out if m is not None]


SLEEVE_END = {"none": None, "cap": 6.05, "short": 5.6, "elbow": 5.0, "three_quarter": 4.5, "long": 4.02}


def top(color="#f2efe8", sleeves="short", hem=4.85, neck=6.5, ease=0.03, name="top", **kw):
    """Fitted top. hem / neck are rest heights in head units (waist is about 4.95, hips 4.2)."""
    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, hem, neck, e)
        if SLEEVE_END[sleeves] is not None:
            out += _sleeves(figure, SLEEVE_END[sleeves], e)
        return out
    kw.setdefault("folds", 0.22)
    return Garment(name, color, build, **kw)


def pants(color="#3b4558", length="full", ease=0.03, waist=4.9, name="pants", **kw):
    end = {"full": 0.5, "cropped": 1.2, "knee": 2.1, "shorts": 3.25}[length]

    def build(figure, extra=0.0):
        e = ease + extra
        return _torso_shell(figure, 3.74, waist, e, bust=False) + _legs(figure, end, e)
    kw.setdefault("folds", 0.18)
    return Garment(name, color, build, **kw)


def _contain_legs(w, f, b, legs, radius):
    """Grow an elliptical cross-section (half width w, front f, back b) until it contains both leg sections.

    legs are (sideways, forward) offsets of the leg centres from the cross-section centre, in HU. Checking each
    axis alone lets a striding leg poke out at the front corner of the ellipse; this checks the corners too.
    """
    grow = 1.0
    for x, z in legs:
        for dx, dz in ((radius, 0.0), (0.0, radius), (-radius, 0.0), (0.0, -radius), (0.71 * radius, 0.71 * radius),
                       (0.71 * radius, -0.71 * radius)):
            px, pz = abs(x) + dx, z + dz
            reach = np.hypot(px / w, pz / (f if pz >= 0 else b))
            grow = max(grow, reach)
    return w * grow, f * grow, b * grow


def _cone(figure, top_y, hem_y, flare, ease, corners=False):
    """Loose skirt-like shell: follows the pelvis, then widens toward a hem while clearing both legs.

    corners  also clear the legs at the corners of the cross-section (a narrow wrapped robe over a striding leg)
    """
    rot = figure.R["pelvis"]
    lat_axis, sag_axis = rot @ [1, 0, 0], rot @ [0, 0, 1]
    hip_rows = np.array([(4.95, 0.50, 0.29, 0.27), (4.55, 0.69, 0.35, 0.37), (4.15, 0.78, 0.40, 0.46)])
    if figure.sex == "male":                          # a man's cloth hangs from narrower hips: follow his own table
        table = sorted((r[1][1], r[2], r[3], r[4]) for r in figure._torso_table())
        ys = np.array([t[0] for t in table])
        hip_rows = np.array([(y, *(np.interp(y, ys, [t[k] for t in table]) + 0.02 for k in (1, 2, 3))) for y in hip_rows[:, 0]])
    hip_y = hip_rows[-1, 0]
    levels = [y for y in hip_rows[:, 0] if y <= top_y + 1e-6] or [top_y]
    levels += list(np.linspace(min(levels[-1], hip_y), hem_y, 7)[1:])

    def leg_point(side, y):
        joint = side + "_hip" if y > KNEE_Y else side + "_knee"
        x = (0.34 + figure._dx("hip")) * (1 if side == "l" else -1)
        return figure.world(joint, (x, y, 0.0))
    pts, width, front, back = [], [], [], []
    for y in levels:
        if y >= hip_y:
            w, f, b = (np.interp(-y, -hip_rows[:, 0], hip_rows[:, k]) for k in (1, 2, 3))
            centre = figure.world("pelvis", (0, y, 0))
        else:
            grow = flare * (hip_y - y)
            w, f, b = hip_rows[-1, 1] + grow, hip_rows[-1, 2] + grow * 0.6, hip_rows[-1, 3] + grow * 0.6
            centre = (leg_point("l", y) + leg_point("r", y)) / 2
        if y < 4.5:                                   # the cloth must clear the legs in any pose
            legs = [leg_point("l", y), leg_point("r", y)]
            leg_radius = 0.45 if y > 3.0 else (0.34 if y > KNEE_Y else 0.28)
            w = max(w, max(abs((p - centre) @ lat_axis) for p in legs) / figure.k + leg_radius)
            f = max(f, max((p - centre) @ sag_axis for p in legs) / figure.k + leg_radius)
            b = max(b, max(-((p - centre) @ sag_axis) for p in legs) / figure.k + leg_radius)
            if corners:
                local = [(((p - centre) @ lat_axis) / figure.k, ((p - centre) @ sag_axis) / figure.k) for p in legs]
                w, f, b = _contain_legs(w, f, b, local, leg_radius)
        pts.append(centre)
        width.append(w + ease)
        front.append(f + ease)
        back.append(b + ease)
    scale = figure.k * figure.slim
    return dict(points=np.array(pts), lateral=lat_axis, sagittal=sag_axis, roundness=0.22,
                width=np.array(width) * scale, front=np.array(front) * scale, back=np.array(back) * scale)


def _skirt_shell(figure, top_y, hem_y, flare, ease, corners=False):
    return [_cone(figure, top_y, hem_y, flare, ease, corners)] + _bumps(figure, hem_y, top_y, ease, ("torso", "buttock_", "thigh_"))


def skirt(color="#2f3a4f", hem=2.5, flare=0.12, waist=4.95, ease=0.03, name="skirt", **kw):
    """hem is a rest height: 3.2 mini, 2.5 knee, 1.2 midi, 0.5 maxi. flare widens toward the hem."""
    def build(figure, extra=0.0):
        return _skirt_shell(figure, waist, hem, flare, ease + extra)
    kw.setdefault("folds", 0.45)
    return Garment(name, color, build, **kw)


def dress(color="#7a2e3a", sleeves="none", hem=2.4, flare=0.14, neck=6.3, ease=0.03, name="dress", **kw):
    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, DRESS_BODICE_LOW, neck, e) + _skirt_shell(figure, 4.95, hem, flare, e)
        if SLEEVE_END[sleeves] is not None:
            out += _sleeves(figure, SLEEVE_END[sleeves], e)
        return out
    kw.setdefault("folds", 0.4)
    return Garment(name, color, build, **kw)


def coat(color="#34485c", hem=3.3, sleeves="long", ease=0.09, name="coat", **kw):
    """Outer layer worn over other garments: wider ease, hem below the hips."""
    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, 4.9, 6.52, e) + _skirt_shell(figure, 4.95, hem, 0.05, e)
        out += _sleeves(figure, SLEEVE_END[sleeves], e * 0.5)
        return out
    kw.setdefault("folds", 0.25)
    return Garment(name, color, build, **kw)


def drape(color="#e9e2d0", top_y=4.45, hem=0.3, flare=0.05, ease=0.05, name="drape", **kw):
    """Classical cloth wrapped low on the hips and falling to the feet."""
    def build(figure, extra=0.0):
        return _skirt_shell(figure, top_y, hem, flare, ease + extra)
    kw.setdefault("folds", 0.7)
    return Garment(name, color, build, **kw)


def _thigh_reach(figure, y, facing):
    """How far the thighs reach forward (facing 1) or back (-1) of the pelvis axis at height y, in HU."""
    sag = figure.R["pelvis"] @ [0, 0, 1]
    thigh = figure.spec["masses"]["thigh"]
    ty = np.array([r[1][1] for r in thigh])[::-1]
    column = 3 if facing > 0 else 4
    radius = float(np.interp(y, ty, np.array([r[column] for r in thigh])[::-1]))
    reach = []
    for side in ("l", "r"):
        x = (0.34 + figure._dx("hip")) * (1 if side == "l" else -1)
        leg = figure.world(side + "_hip" if y > KNEE_Y else side + "_knee", (x, y, 0.0))
        reach.append(facing * ((leg - figure.world("pelvis", (0, y, 0))) @ sag) / figure.k + radius)
    return max(reach)


def _hanging_panel(figure, top_y, drop, width, facing, ease, sign=1):
    """A cloth panel hanging from a hip band in front (facing 1) or behind (-1), clearing the thighs."""
    rot = figure.R["pelvis"]
    lat, sag = rot @ [1, 0, 0], rot @ [0, 0, 1]
    k = figure.k * figure.slim
    pts, widths = [], []
    for i, y in enumerate(np.linspace(top_y - 0.08, top_y - drop, 7)):
        body = figure.surface_z(y, "front" if facing > 0 else "back") if y > 3.8 else 0.0
        depth = max(body, _thigh_reach(figure, y, facing) if y < 4.1 else 0.0) + ease + 0.02
        x = 0.05 * sign * i / 6
        pts.append(figure.world("pelvis", (0, y, 0)) + (lat * x + sag * facing * depth) * figure.k)
        widths.append(width * (0.62 + 0.38 * (i / 6) ** 0.7))          # gathered at the band, fanning out
    return dict(points=np.array(pts), lateral=lat, sagittal=sag, roundness=0.9,
                width=np.array(widths) * k, front=np.full(len(pts), 0.03 * k), back=np.full(len(pts), 0.03 * k))


def loincloth(color="#e6dcc6", top_y=4.3, length=1.0, width=0.34, ease=0.03, knot="l", name="loincloth", **kw):
    """Classical hip cloth: a band low on the hips, a panel hanging in front and behind, a knot at one hip.

    The panels lie over the fronts (and backs) of both thighs, so the hem is a clean edge in any standing
    pose and the legs stay bare. length is the drop of the front panel below top_y (HU).
    """
    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, 3.74, top_y, e, bust=False)
        rot = figure.R["pelvis"]
        lat, sag = rot @ [1, 0, 0], rot @ [0, 0, 1]
        sign = 1 if knot == "l" else -1
        k = figure.k * figure.slim
        for facing, drop in ((1, length), (-1, length * 0.8)):
            out.append(_hanging_panel(figure, top_y, drop, width, facing, e, sign))
        knot_at = figure.world("pelvis", (0.56 * sign, top_y - 0.04, 0.12))
        out.append(dict(centre=knot_at, axes=rot, radii=np.array([0.075, 0.065, 0.07]) * figure.k))
        tail = [figure.world("pelvis", (0.58 * sign, top_y - 0.04 - t, 0.16 - 0.03 * t)) for t in np.linspace(0, 0.45, 5)]
        out.append(dict(points=np.array(tail), lateral=lat, sagittal=sag, roundness=0.9,
                        width=np.linspace(0.05, 0.035, 5) * k, front=np.full(5, 0.02 * k), back=np.full(5, 0.02 * k)))
        return out
    kw.setdefault("folds", 0.8)
    return Garment(name, color, build, **kw)


def shoes(color="#2b2b30", ease=0.02, name="shoes", **kw):
    def build(figure, extra=0.0):
        out = []
        for mass in figure._body_masses():
            if mass["part"].startswith(("foot_", "toe")):
                grow = (ease + extra) * figure.k * (2.2 if mass["part"].startswith("toe") else 1.0)
                out.append(dict(points=mass["points"], lateral=mass["lateral"], sagittal=mass["sagittal"],
                                width=mass["width"] + grow, front=mass["front"] + grow,
                                back=(mass.get("back", mass["front"])) + grow))
        return out
    kw.setdefault("folds", 0.0)
    kw.setdefault("gloss", 0.3)
    return Garment(name, color, build, **kw)


# ---------- details: necklines, lapels, buttons (drawn on the garment after the relief is composited) ----------
def _chest_point(view, x, y, z):
    return tuple(view.to_canvas(view.figure.world("chest", (x, y, z))))


def _front_z(y, ease):
    """Approximate front surface of the clothed torso at rest height y."""
    return float(np.interp(y, [4.9, 5.35, 5.75, 6.0, 6.33, 6.5], [0.29, 0.33, 0.40, 0.50, 0.30, 0.22])) + ease


def neckline(kind="v", depth=0.42, width=0.2):
    """Open the neck of a top: 'v' or 'scoop'. depth and width in head units below / beside the neck base."""
    def detail(garment, view, line_width):
        from . import geom
        canvas, fig = view.canvas, view.figure
        if fig.R["chest"][2, 2] < 0.15:
            return
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        skin = view.skin_color
        from .core import trace_color
        top_y, ease = 6.62, 0.05
        left, right = _chest_point(view, -width, top_y, 0.12), _chest_point(view, width, top_y, 0.12)
        low = _chest_point(view, 0, top_y - depth, _front_z(top_y - depth, ease))
        above = [right, _chest_point(view, width, top_y + 0.3, 0.0), _chest_point(view, -width, top_y + 0.3, 0.0), left]
        if kind == "v":
            edge = [left, low, right]
            shape = geom.runs([[left, low], [low, right], above])
        else:
            mid_l = _chest_point(view, -width * 0.9, top_y - depth * 0.75, _front_z(top_y - depth * 0.75, ease))
            mid_r = _chest_point(view, width * 0.9, top_y - depth * 0.75, _front_z(top_y - depth * 0.75, ease))
            edge = [left, mid_l, low, mid_r, right]
            shape = geom.runs([edge, above])
        canvas.add(shape, skin, "skin", keep_normal=1.0, clip=clip)
        ink = trace_color(view.canvas.albedo[int(low[1] * canvas.scale) + 6, int(low[0] * canvas.scale)]) \
            if 0 <= int(low[1] * canvas.scale) + 6 < canvas.H and 0 <= int(low[0] * canvas.scale) < canvas.W else "#3a3030"
        if kind == "v":
            canvas.stroke([left, low], line_width, ink, start=0.5, end=1.0, clip=clip)
            canvas.stroke([right, low], line_width, ink, start=0.5, end=1.0, clip=clip)
        else:
            canvas.stroke(edge, line_width, ink, start=0.5, end=0.5, clip=clip)
        canvas.shade(geom.offset(shape, line_width * 1.5, line_width * 3), 0.3, clip=canvas.mask(shape) * clip)
    return detail


def open_front(inner="#f1eee6", lapel=True, buttons=0):
    """Wear a coat or jacket open: a strip of the layer underneath shows, with lapels folded back."""
    def detail(garment, view, line_width):
        from . import geom
        from .core import to_rgb, trace_color
        canvas, fig = view.canvas, view.figure
        if fig.R["chest"][2, 2] < 0.15:
            return
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        ease = 0.11
        ys = [6.72, 6.5, 6.2, 5.8, 5.4, 4.95, 4.4, 3.6]
        half = [0.24, 0.19, 0.10, 0.07, 0.08, 0.10, 0.13, 0.17]
        left = [_chest_point(view, -h, y, _front_z(y, ease) if y > 4.9 else 0.42) for y, h in zip(ys, half)]
        right = [_chest_point(view, h, y, _front_z(y, ease) if y > 4.9 else 0.42) for y, h in zip(ys, half)]
        canvas.add(geom.runs([left, [left[-1], right[-1]], right[::-1], [right[0], left[0]]]), inner, garment.name + "_inner",
                   keep_normal=1.0, clip=clip)
        for edge in (left[1:], right[1:]):
            canvas.stroke(edge, line_width, trace_color(to_rgb(garment.color)), start=0.6, end=1.0, clip=clip)
        if lapel:
            dark = np.clip(to_rgb(garment.color) * 0.86, 0, 1)
            for side in (-1, 1):
                notch = _chest_point(view, side * 0.36, 6.12, _front_z(6.12, ease))
                shape = geom.runs([[_chest_point(view, side * 0.17, 6.56, 0.2), _chest_point(view, side * 0.33, 6.42, 0.3), notch],
                                   [notch, _chest_point(view, side * 0.2, 5.9, _front_z(5.9, ease)),
                                    _chest_point(view, side * 0.075, 5.5, _front_z(5.5, ease))],
                                   [_chest_point(view, side * 0.075, 5.5, _front_z(5.5, ease)),
                                    _chest_point(view, side * 0.09, 6.1, _front_z(6.1, ease)), _chest_point(view, side * 0.17, 6.56, 0.2)]])
                canvas.add(shape, dark, garment.name, keep_normal=0.8, clip=clip, outline=line_width,
                           cast=(line_width, line_width * 2.5, 1.0, 0.5))
        for i in range(buttons):
            y = 5.3 - i * 0.42
            px, py = _chest_point(view, 0.16, y, _front_z(y, ease) if y > 4.9 else 0.44)
            canvas.add(geom.ellipse(px, py, view.unit * 0.028), np.clip(to_rgb(garment.color) * 0.6, 0, 1), garment.name,
                       clip=clip, outline=line_width * 0.7)
    return detail


def collar(open_neck=True, buttons=5, color=None, placket=True):
    """Shirt collar on a top: two collar points folded onto the chest, a button placket down the front.

    open_neck  leaves the top button undone, so a small V of skin shows between the collar points
    color      collar colour (default: the shirt colour, a touch lighter)
    """
    def detail(garment, view, line_width):
        from . import geom
        from .core import to_rgb, trace_color
        canvas, fig = view.canvas, view.figure
        if fig.R["chest"][2, 2] < 0.15:
            return
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        cloth = to_rgb(garment.color)
        tone = np.clip(cloth * 1.05 + 0.02, 0, 1) if color is None else to_rgb(color)
        ink = trace_color(cloth)

        def front(x, y, out=0.0):
            z = max(_front_z(y, COLLAR_EASE), fig.surface_z(y) + COLLAR_EASE) + out
            return _chest_point(view, x, y, z)
        if open_neck:
            neckline("v", 0.24, 0.12)(garment, view, line_width)
        meet = 6.42 if open_neck else 6.56
        if placket:
            line = [front(0.0, meet - 0.02), front(0.0, 5.4), front(0.0, 4.9)]
            canvas.stroke(line, line_width * 0.8, ink, start=0.8, end=0.8, alpha=0.8, clip=clip)
            for i in range(buttons):
                y = meet - 0.2 - i * COLLAR_BUTTON_STEP
                if y < 4.85:
                    break
                px, py = front(0.035, y, 0.01)
                canvas.add(geom.ellipse(px, py, view.unit * 0.022), np.clip(cloth * 0.92, 0, 1), garment.name,
                           clip=clip, outline=line_width * 0.6)
        figure_only = (view.coverage() > 0.5).astype(np.float32)        # the collar rises above the shirt onto the neck
        for side in (-1, 1):
            wing = geom.runs([[_chest_point(view, side * 0.21, 6.74, -0.02), _chest_point(view, side * 0.12, 6.68, 0.17),
                               front(side * 0.025, meet)],
                              [front(side * 0.025, meet), front(side * 0.30, 6.30, 0.015)],
                              [front(side * 0.30, 6.30, 0.015), front(side * 0.30, 6.52, 0.02), _chest_point(view, side * 0.21, 6.74, -0.02)]])
            canvas.add(wing, tone, garment.name, keep_normal=0.7, clip=figure_only,
                       outline=line_width * 0.9, cast=(line_width * 0.5, line_width * 2.0, 1.0, 0.45))
    return detail


COLLAR_EASE = 0.06          # head units the collar points stand off the body
COLLAR_BUTTON_STEP = 0.30   # head units between shirt buttons



# ---------- traditional dress: kimono and obi, hanbok, fundoshi and sarashi ----------
UP = np.array([0.0, 1.0, 0.0])
BELL_HIP = 4.6              # rest height where a high-waisted skirt starts to spread
CHIMA_BELL_TOP = 5.75       # the chima's bell hangs from just under the bust, inside the short jeogori
SURFACE_SEEN = 0.08         # a surface point is drawn when its normal turns at least this far toward the viewer
BAND_ROUNDNESS = 0.22       # short stamps: a narrow band over bare skin keeps square edges instead of domed overshoot
KIMONO_SLEEVES = {"short": 0.6, "tomesode": 1.0, "furisode": 2.3}    # drop of the hanging sleeve pocket (HU)


def _ring_point(figure, y, angle, out=0.0):
    """World point and outward normal on the torso at rest height y, `angle` degrees round it
    (0 front, 90 the figure's left, -90 its right), lifted `out` HU off the skin."""
    joint, rest = figure.table_point("torso", y, angle)
    a = np.radians(angle)
    normal = np.array([np.sin(a), 0.0, np.cos(a)])
    return figure.world(joint, np.asarray(rest) + normal * out), figure.R[joint] @ normal


def _surface_path(view, ys, angles, out):
    """Canvas points along the torso surface through (y, angle) pairs, with a facing-the-viewer flag for each."""
    pts, seen = [], []
    for y, a in zip(ys, angles):
        point, normal = _ring_point(view.figure, y, a, out)
        pts.append(tuple(view.to_canvas(point)))
        seen.append(normal[2] > SURFACE_SEEN)
    return pts, np.array(seen)


def _visible_runs(points, seen):
    runs, current = [], []
    for point, ok in zip(points, seen):
        if ok:
            current.append(point)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return [run for run in runs if len(run) > 1]


def _ring_line(view, y, out, width, color, clip, alpha=0.8):
    """A line round the clothed torso at rest height y on the side facing the viewer (turns of cloth, cords)."""
    angles = np.linspace(-175, 175, 71)
    pts, seen = _surface_path(view, [y] * len(angles), angles, out)
    for run in _visible_runs(pts, seen):
        view.canvas.stroke(run, width, color, start=0.7, end=0.7, alpha=alpha, clip=clip)


def _band(view, edge, outward, out, color, region, clip, line_width, ink):
    """A strip lying on the torso between a path of (y, angle) points and the same path shifted `outward` degrees."""
    from . import geom
    ys, angles = zip(*edge)
    inner, seen_a = _surface_path(view, ys, angles, out)
    outer, seen_b = _surface_path(view, ys, [a + outward for a in angles], out)
    if not (seen_a.all() and seen_b.all()):
        return None
    shape = geom.polygon(inner + outer[::-1])
    view.canvas.add(shape, color, region, keep_normal=1.0, clip=clip)
    view.canvas.stroke(inner, line_width, ink, start=0.7, end=0.7, clip=clip)
    return shape


def _sleeve_pocket(figure, side, drop, ease, half_width=0.44):
    """The hanging part of a wide sleeve: a flat panel under the forearm that falls with gravity.

    A raised forearm carries the panel along its length; a hanging arm turns it front to back beside the body.
    """
    elbow, wrist = figure.P[side + "_elbow"], figure.P[side + "_wrist"]
    along = wrist - elbow
    flat = along - UP * (along @ UP)
    if np.linalg.norm(flat) > 0.5 * np.linalg.norm(along):
        lat = flat
    else:
        forward = figure.R["chest"] @ [0, 0, 1]
        lat = forward - UP * (forward @ UP)
    lat = lat / (np.linalg.norm(lat) + 1e-9)
    sag = np.cross(lat, UP)
    k = figure.k * figure.slim
    top = elbow + along * 0.55
    pts = np.array([top - UP * drop * figure.k * t for t in np.linspace(0, 1, 6)])
    return dict(points=pts, lateral=lat, sagittal=sag, roundness=0.9, width=np.full(6, half_width * k),
                front=np.full(6, (0.06 + ease) * k), back=np.full(6, (0.06 + ease) * k))


def _crossed_front(view, garment, edges, collar, under, line_width):
    """Left-over-right crossed collar: the V at the throat, an under-collar strip inside it, a collar band along
    each edge. edges = (top panel edge, under panel edge) as lists of (y, angle) from the neck down."""
    from .core import to_rgb, trace_color
    from . import geom
    fig, canvas = view.figure, view.canvas
    if fig.R["chest"][2, 2] < 0.15:
        return
    clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
    cloth = to_rgb(garment.color)
    band = np.clip(cloth * 0.72, 0, 1) if collar is None else to_rgb(collar)
    ink = trace_color(cloth)
    top_edge, under_edge = edges
    out = 0.07
    v_top, _ = _surface_path(view, *zip(*top_edge[:2]), out)
    v_under, _ = _surface_path(view, *zip(*under_edge), out)
    above = [_chest_point(view, 0.32, 6.95, 0.0), _chest_point(view, -0.32, 6.95, 0.0)]
    throat = geom.polygon(v_under + v_top[::-1] + above)
    if under is not None:                                       # the under-collar shows as a strip inside the V
        canvas.add(throat, under, garment.name + "_under", keep_normal=1.0, clip=clip)
        inset = [(y, a + 7) for y, a in under_edge[:-1]] + [under_edge[-1]]
        inset_top = [(y, a - 7) for y, a in top_edge[:2]]
        skin_pts = _surface_path(view, *zip(*inset), out)[0] + _surface_path(view, *zip(*inset_top), out)[0][::-1]
        canvas.add(geom.polygon(skin_pts + above), view.skin_color, "skin", keep_normal=1.0, clip=clip)
    else:
        canvas.add(throat, view.skin_color, "skin", keep_normal=1.0, clip=clip)
    _band(view, under_edge, -10, out, band, garment.name + "_collar", clip, line_width, ink)
    _band(view, top_edge, 10, out, band, garment.name + "_collar", clip, line_width, ink)


def _scatter(view, garment, pattern, colors, seed):
    """Small motifs strewn over a garment: 'blossom' (five petals) or 'dots'."""
    from . import geom
    canvas = view.canvas
    mask = view.part_mask(garment.name) > 0.5
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return
    rng = np.random.default_rng(seed)
    size = view.unit * 0.09
    spacing = size * 4.2 * canvas.scale
    count = int(mask.sum() / spacing ** 2)
    clip = mask.astype(np.float32)
    for _ in range(count):
        i = rng.integers(len(xs))
        x, y = xs[i] / canvas.scale, ys[i] / canvas.scale
        color = colors[rng.integers(len(colors))]
        r = size * rng.uniform(0.7, 1.2)
        if pattern == "blossom":
            turn = rng.uniform(0, 2 * np.pi / 5)
            petals = [geom.ellipse(x + np.cos(turn + j * 2 * np.pi / 5) * r * 0.62, y + np.sin(turn + j * 2 * np.pi / 5) * r * 0.62,
                                   r * 0.42, r * 0.42) for j in range(5)]
            canvas.add(geom.union(*petals), color, garment.name + "_motif", keep_normal=1.0, clip=clip)
            canvas.add(geom.ellipse(x, y, r * 0.2, r * 0.2), "#e8b84a", garment.name + "_motif", keep_normal=1.0, clip=clip)
        else:
            canvas.add(geom.ellipse(x, y, r * 0.35, r * 0.35), color, garment.name + "_motif", keep_normal=1.0, clip=clip)


def _skirt_front_line(view, garment, x, top_y, hem, line_width):
    """The front edge of a wrapped robe below the sash, running down to the hem a little off the centre."""
    from .core import to_rgb, trace_color
    fig = view.figure
    if fig.R["pelvis"][2, 2] < 0.15:
        return
    clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
    pts = []
    for y in np.linspace(top_y, hem + 0.05, 12):
        body = fig.surface_z(y, "front") if y > 3.8 else 0.0
        depth = max(body, _thigh_reach(fig, y, 1) if y < 4.1 else 0.0) + 0.08
        pts.append(tuple(view.to_canvas(fig.world("pelvis", (x, y, depth)))))
    view.canvas.stroke(pts, line_width, trace_color(to_rgb(garment.color)), start=0.8, end=0.8, alpha=0.85, clip=clip)


def kimono(color="#2f4a7a", sleeves="tomesode", hem=0.3, collar=None, under="#f4efe4", pattern=None,
           pattern_colors=("#f3c4cf", "#fbf3f0"), ease=0.05, seed=0, name="kimono", **kw):
    """Japanese robe worn left panel over right, ankle length, with wide sleeves whose pockets hang below the arm.

    sleeves  short | tomesode (pockets about 1 HU deep) | furisode (long pockets falling toward the knees)
    collar   colour of the collar band along the crossed edges (default: the robe colour, darker)
    under    colour of the under-collar strip showing inside the V at the throat (None: bare skin only)
    pattern  None | 'blossom' | 'dots', strewn over the robe in pattern_colors
    Wear obi() over it.
    """
    drop = KIMONO_SLEEVES[sleeves]

    def build(figure, extra=0.0):
        e = ease + extra
        # The body shell reaches down over the hips: seen from behind, the wrapped robe hides the small of the back.
        out = _torso_shell(figure, 3.9, 6.55, e) + _skirt_shell(figure, 4.95, hem, -0.01, e, corners=True)
        out += _sleeves(figure, SLEEVE_END["long"], e + 0.02)
        out += [_sleeve_pocket(figure, side, drop, e) for side in ("l", "r")]
        return out

    def detail(garment, view, line_width):
        if pattern:
            _scatter(view, garment, pattern, pattern_colors, seed)
        top_edge = [(6.64, 26), (6.2, 8), (5.95, -10), (5.7, -30), (5.45, -45)]
        under_edge = [(6.64, -26), (6.32, -12), (6.12, 0)]
        _crossed_front(view, garment, (top_edge, under_edge), collar, under, line_width)
        _skirt_front_line(view, garment, -0.24, 4.75, hem, line_width)
    kw.setdefault("folds", 0.35)
    return Garment(name, color, build, detail=detail, **kw)


def obi(color="#c8a040", width="wide", cord="#b8433a", bow=True, ease=0.1, name="obi", **kw):
    """Sash over a kimono.

    width  wide: a stiff band from the waist to under the bust with a drum knot (otaiko) at the back and a cord
           (obijime) round its middle; narrow: a man's band low on the hips with a small knot behind
    """
    lo, hi = (4.85, 5.78) if width == "wide" else (4.3, 4.62)

    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, lo, hi, e, bust=False)
        if bow and width == "wide":                    # the drum knot: a stiff box of folded sash hanging at the back
            k = figure.k * figure.slim
            behind = min(figure.surface_z(y, "back") for y in np.linspace(lo - 0.6, hi, 8)) - e - 0.2
            pts = [figure.world("waist", np.array([0.0, y, behind])) for y in np.linspace(hi + 0.04, lo - 0.32, 6)]
            lat = figure.R["waist"] @ [1, 0, 0]
            out.append(dict(points=np.array(pts), lateral=lat, sagittal=figure.R["waist"] @ [0, 0, 1], roundness=0.9,
                            width=np.full(6, 0.46 * k), front=np.full(6, 0.12 * k), back=np.full(6, 0.12 * k)))
        elif bow:                                       # a man's small knot behind
            joint, rest = figure.table_point("torso", (lo + hi) / 2, 180)
            centre = figure.world(joint, np.asarray(rest) + np.array([0.0, 0.0, -(e + 0.1)]))
            out.append(dict(centre=centre, axes=figure.R[joint], radii=np.array([0.22, 0.11, 0.08]) * figure.k))
        return out

    def detail(garment, view, line_width):
        if cord and width == "wide":
            clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
            _ring_line(view, (lo + hi) / 2, ease + 0.04, line_width * 2.4, cord, clip, alpha=1.0)
    kw.setdefault("folds", 0.15)
    kw.setdefault("gloss", 0.2)
    return Garment(name, color, build, detail=detail, **kw)


def jeogori(color="#f2d16b", length="short", git="#6a3a7a", dongjeong="#fbfaf4", goreum="#b8334a", ease=0.05,
            name="jeogori", **kw):
    """Korean jacket closing to the wearer's right (left panel over right): a band collar (git) edged at the
    neck with a white strip (dongjeong), long sleeves with a softly rounded underside, and two long ribbons
    (goreum) tied at the wearer's right breast.

    length  short: a woman's jacket ending just over the bust, worn over a chima; long: a man's, to the hips
    """
    hem = 5.72 if length == "short" else 4.35

    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, hem, 6.55, e)
        out += _sleeves(figure, SLEEVE_END["long"], e + 0.02)
        out += [_sleeve_pocket(figure, side, 0.26, e, half_width=0.3) for side in ("l", "r")]      # baerae curve
        return out

    def detail(garment, view, line_width):
        from . import geom
        from .core import to_rgb, trace_color
        fig, canvas = view.figure, view.canvas
        if fig.R["chest"][2, 2] < 0.15:
            return
        low = hem + 0.06 if length == "short" else 5.6
        top_edge = [(6.64, 24), (6.3, 8), (6.05, -10), (low + 0.05, -26), (low, -34)]
        under_edge = [(6.64, -24), (6.36, -10), (6.2, 0)]
        _crossed_front(view, garment, (top_edge, under_edge), git, None, line_width)
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        if dongjeong:                                     # the white strip runs along the collar near the neck
            _band(view, top_edge[:2], 4, 0.075, dongjeong, garment.name + "_dongjeong", clip, line_width * 0.6,
                  trace_color(to_rgb(dongjeong)))
            _band(view, under_edge[:2], -4, 0.075, dongjeong, garment.name + "_dongjeong", clip, line_width * 0.6,
                  trace_color(to_rgb(dongjeong)))
        if length == "long":
            _skirt_front_line(view, garment, -0.3, 5.5, hem, line_width)
        knot_point, normal = _ring_point(fig, (low + 0.12) if length == "short" else 5.75, -30, 0.1)
        if not goreum or normal[2] < SURFACE_SEEN:
            return
        kx, ky = view.to_canvas(knot_point)
        unit = view.unit
        tone, ink = to_rgb(goreum), trace_color(to_rgb(goreum))
        long_drop = 1.45 if length == "short" else 0.9
        for drop, lean, width in ((long_drop, -0.06, 0.11), (long_drop * 0.65, 0.1, 0.1)):
            end = (kx + lean * unit, ky + drop * unit)
            ribbon = geom.taper([(kx, ky), (kx + lean * unit * 0.4, ky + drop * unit * 0.5), end], width * unit,
                                start=0.7, end=1.0, peak=0.9)
            canvas.add(ribbon, tone, garment.name + "_goreum", form="round", bulge=width * unit * 0.4, relief=0.4,
                       outline=(line_width * 0.8, ink), cast=(line_width, line_width * 2, 1.0, 0.35))
        canvas.add(geom.ellipse(kx, ky, unit * 0.09, unit * 0.07), tone, garment.name + "_goreum", form="round",
                   outline=(line_width * 0.8, ink))
    kw.setdefault("folds", 0.3)
    return Garment(name, color, build, detail=detail, **kw)


def _bell(figure, top_y, hem_y, flare, ease):
    """A full skirt from high on the chest: the torso's own section at the top, widening steadily to the hem,
    always clearing both legs."""
    rows = sorted(figure._torso_table(), key=lambda r: r[1][1])
    ys = np.array([r[1][1] for r in rows])

    def section(y):
        return [float(np.interp(y, ys, [r[c] for r in rows])) for c in (2, 3, 4)]
    w0, f0, b0 = section(top_y)
    rot = figure.R["pelvis"]
    lat, sag = rot @ [1, 0, 0], rot @ [0, 0, 1]

    def leg_point(side, y):
        joint = side + "_hip" if y > KNEE_Y else side + "_knee"
        x = (0.34 + figure._dx("hip")) * (1 if side == "l" else -1)
        return figure.world(joint, (x, y, 0.0))
    pts, width, front, back = [], [], [], []
    for y in np.linspace(top_y, hem_y, 14):
        drop, below_hip = top_y - y, max(BELL_HIP - y, 0.0)
        body_w, body_f, body_b = section(y)
        # Above the hips the cloth falls nearly straight, so arms resting in front stay outside it; below, it spreads.
        w = max(w0 + flare * (0.25 * drop + below_hip), body_w + 0.04)
        f = max(f0 + flare * 0.6 * below_hip, body_f + 0.04)
        b = max(b0 + flare * (0.15 * drop + 0.6 * below_hip), body_b + 0.04)
        if y > 4.3:
            joint = rows[int(np.argmin(np.abs(ys - y)))][0]
            centre = figure.world(joint, (0, y, float(np.interp(y, ys, [r[1][2] for r in rows]))))
        else:
            centre = (leg_point("l", y) + leg_point("r", y)) / 2
        if y < 4.5:                                     # the cloth must clear the legs in any pose
            legs = [leg_point("l", y), leg_point("r", y)]
            leg_radius = 0.45 if y > 3.0 else (0.34 if y > KNEE_Y else 0.28)
            local = [(((p - centre) @ lat) / figure.k, ((p - centre) @ sag) / figure.k) for p in legs]
            w, f, b = _contain_legs(w, f, b, local, leg_radius)
        pts.append(centre)
        width.append(w + ease)
        front.append(f + ease)
        back.append(b + ease)
    scale = figure.k * figure.slim
    return dict(points=np.array(pts), lateral=lat, sagittal=sag, roundness=0.22,
                width=np.array(width) * scale, front=np.array(front) * scale, back=np.array(back) * scale)


def chima(color="#b8334a", top=6.05, hem=0.2, flare=0.16, ease=0.04, name="chima", **kw):
    """Korean wrap skirt tied high under the arms: it covers the bust and falls in a full bell to the floor.

    The bell starts just under the bust, where a short jeogori ends, so the jacket always lies over the skirt top.
    """
    def build(figure, extra=0.0):
        e = ease + extra
        return _torso_shell(figure, 4.9, top, e) + [_bell(figure, min(top, CHIMA_BELL_TOP), hem, flare, e)]
    kw.setdefault("folds", 0.55)
    return Garment(name, color, build, **kw)


def baji(color="#ece6d6", ease=0.16, name="baji", **kw):
    """Korean trousers: very full legs gathered close at the ankles where the ties (daenim) bind them."""
    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, 3.74, 4.95, e * 0.5, bust=False)
        for side in ("l", "r"):
            out.append(_slice(figure, "thigh", side, KNEE_Y, LEG_TOP_Y + 0.1, e))
            out.append(_slice(figure, "shin", side, 0.9, KNEE_Y, e))
            out.append(_slice(figure, "shin", side, 0.42, 0.9, e * 0.25))          # gathered at the ankle tie
        out += _bumps(figure, 0.42, LEG_TOP_Y + 0.1, e, ("thigh_", "buttock_"))
        return [m for m in out if m is not None]
    kw.setdefault("folds", 0.5)
    return Garment(name, color, build, **kw)


def fundoshi(color="#f4f1ea", apron=0.0, twist=True, ease=0.02, name="fundoshi", **kw):
    """Japanese loincloth: a twisted band round the hips, a pouch over the groin, a strand between the buttocks.

    apron  > 0 lets a front cloth hang that many HU below the band (etchu style); 0 is the plain rokushaku
    twist  draws the rolled twist of the band
    """
    band_lo, band_hi = 4.04, 4.3

    def build(figure, extra=0.0):
        e = ease + extra
        k = figure.k * figure.slim
        rot = figure.R["pelvis"]
        lat, sag = rot @ [1, 0, 0], rot @ [0, 0, 1]
        out = [dict(_slice(figure, "torso", "l", band_lo, band_hi, e + 0.04), roundness=BAND_ROUNDNESS)]   # buttocks bare
        # (facing, half widths, thickness, lift off the skin, tuck): a flat pouch in front, a strand down the cleft behind
        for facing, half_widths, thick, lift, tuck_by in ((1, np.linspace(0.2, 0.07, 7), 0.03, 0.015, 0.06),
                                                         (-1, np.linspace(0.05, 0.035, 7), 0.03, 0.05, 0.03)):
            pts = []
            for i, y in enumerate(np.linspace(4.18, 3.75, 7)):
                surface = figure.surface_z(y, "front" if facing > 0 else "back")
                tuck = tuck_by * (i / 6) ** 2                 # the cloth turns under between the legs
                pts.append(figure.world("pelvis", (0, y, 0)) + sag * (surface + facing * (e + lift - tuck)) * figure.k)
            out.append(dict(points=np.array(pts), lateral=lat, sagittal=sag, roundness=0.9, width=half_widths * k,
                            front=np.full(7, thick * k), back=np.full(7, thick * k)))
        if apron > 0:
            out.append(_hanging_panel(figure, band_lo + 0.1, apron, 0.32, 1, e + 0.03))
        return out

    def detail(garment, view, line_width):
        from .core import to_rgb, trace_color
        if not twist:
            return
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        ink = trace_color(to_rgb(garment.color))
        mid = (band_lo + band_hi) / 2
        for angle in np.arange(-170, 180, 16):           # the rolled band: short slanted creases all round
            pts, seen = _surface_path(view, (mid + 0.09, mid - 0.09), (angle - 5, angle + 5), ease + 0.06)
            if seen.all():
                view.canvas.stroke(pts, line_width * 0.8, ink, start=0.3, end=0.3, alpha=0.6, clip=clip)
    kw.setdefault("folds", 0.3)
    return Garment(name, color, build, detail=detail, **kw)


def sarashi(color="#f6f3ec", lo=4.62, hi=5.6, ease=0.03, name="sarashi", **kw):
    """Bleached cotton wound flat round the body in many turns, with fine lines at the turns.

    Round the belly: lo 4.62, hi 5.6 (the default). Round the chest: lo 5.5, hi 6.35.
    """
    def build(figure, extra=0.0):
        shell = _torso_shell(figure, lo, hi, ease + extra, bust=hi > 5.9)
        shell[0] = dict(shell[0], roundness=BAND_ROUNDNESS)
        return shell

    def detail(garment, view, line_width):
        from .core import to_rgb, trace_color
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        ink = trace_color(to_rgb(garment.color))
        for y in np.arange(lo + 0.14, hi - 0.06, 0.17):
            _ring_line(view, y, ease + 0.04, line_width * 0.7, ink, clip, alpha=0.45)
    kw.setdefault("folds", 0.1)
    return Garment(name, color, build, detail=detail, **kw)


# ---------------------------------------------------------------- everyday dark layers: hoodie and turtleneck
def turtleneck(color="#1e1e22", sleeves="long", hem=4.35, ease=0.03, name="turtleneck", **kw):
    """Fitted knit top whose collar rolls up the neck: the torso shell and a tube over the lower neck."""
    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, hem, 6.6, e) + _sleeves(figure, SLEEVE_END[sleeves], e)
        neck = _slice(figure, "neck", "l", 6.45, 6.95, e + 0.05, scale=figure.spec["neck"] * figure.neck_scale)
        return [m for m in out + [neck] if m is not None]

    def detail(garment, view, line_width):
        from .core import to_rgb, trace_color
        if view.figure.R["chest"][2, 2] < 0.15:
            return
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        fold = [tuple(view.to_canvas(view.figure.world("neck", (x, 6.82, 0.24 - 0.9 * x * x)))) for x in np.linspace(-0.3, 0.3, 9)]
        view.canvas.stroke(fold, line_width * 0.9, trace_color(to_rgb(garment.color)), start=0.6, end=0.6, alpha=0.7, clip=clip)
    kw.setdefault("folds", 0.2)
    return Garment(name, color, build, detail=detail, **kw)


HOOD_ANGLES = np.linspace(18, 342, 19)       # the roll runs from the throat round the back of the neck and back again
HOOD_SACK = (6.6, 5.85)                      # the emptied hood lies on the upper back between these rest heights


def _hood_ring(figure, ease):
    """Centre line of the lowered hood's roll: points, outward normals, height and thickness at each angle."""
    pts, normals, width, thick = [], [], [], []
    for angle in HOOD_ANGLES:
        a = np.radians(angle)
        back = (1 - np.cos(a)) / 2                  # 0 at the front of the neck, 1 at the back
        y = 6.64 - 0.2 * max(np.cos(a), 0.0) ** 2
        joint, rest = figure.table_point("neck", y, angle)
        normal = np.array([np.sin(a), 0.0, np.cos(a)])
        point = figure.world(joint, np.asarray(rest) + normal * (ease + 0.05 + 0.1 * back))
        pts.append(point + UP * figure.k * (0.02 + 0.06 * back))
        normals.append(figure.R[joint] @ normal)
        width.append((0.09 + 0.07 * back) * figure.k)
        thick.append((0.07 + 0.06 * back) * figure.k)
    return np.array(pts), np.array(normals), np.array(width), np.array(thick)


def _hood_roll(figure, ease):
    """A lowered hood seen as a thick collar: a roll hugging the base of the neck, fuller and higher at the back
    where the hood folds over itself, dipping at the front where its two edges meet over the throat."""
    pts, normals, width, thick = _hood_ring(figure, ease)
    return dict(points=pts, lateral=UP, sagittal=normals, roundness=0.9, width=width, front=thick, back=thick)


def _hood_sack(figure, ease):
    """The empty hood hanging on the back: a flattened U from the back of the neck to the shoulder blades."""
    top, bottom = HOOD_SACK
    pts, normals, width = [], [], []
    for t in np.linspace(0, 1, 9):
        point, normal = _ring_point(figure, top + (bottom - top) * t, 180, ease + 0.05)
        pts.append(point)
        normals.append(normal)
        width.append(0.3 * figure.k * np.sqrt(np.clip(1 - t ** 3, 0.04, 1)))
    lateral = figure.R["chest"] @ np.array([1.0, 0.0, 0.0])
    return dict(points=np.array(pts), lateral=lateral, sagittal=np.array(normals), roundness=0.5,
                width=np.array(width), front=np.full(9, 0.05 * figure.k), back=np.full(9, 0.05 * figure.k))


def hoodie(color="#232428", sleeves="long", hem=4.3, ease=0.07, strings="#d8d4cc", pocket=True, name="hoodie", **kw):
    """Loose hooded sweatshirt worn with the hood down: the hood lies in a soft roll round the back of the neck,
    two drawstrings hang at the throat and a pouch pocket crosses the belly."""
    def build(figure, extra=0.0):
        e = ease + extra
        out = _torso_shell(figure, hem, 6.55, e) + _sleeves(figure, SLEEVE_END[sleeves], e * 0.8)
        return out + [_hood_roll(figure, e), _hood_sack(figure, e)]

    def detail(garment, view, line_width):
        from . import geom
        from .core import to_rgb, trace_color
        fig, canvas = view.figure, view.canvas
        if fig.R["chest"][2, 2] < 0.15:
            return
        clip = (view.part_mask(garment.name) > 0.5).astype(np.float32)
        ink = trace_color(to_rgb(garment.color))
        pts, normals, width, thick = _hood_ring(fig, ease)          # crease where the roll lies on the shoulders
        edge = [tuple(view.to_canvas(p - UP * w * 0.75 + n * t * 0.4)) for p, n, w, t in zip(pts, normals, width, thick)]
        for run in _visible_runs(edge, normals[:, 2] > SURFACE_SEEN):
            canvas.stroke(run, line_width * 0.9, ink, start=0.5, end=0.5, alpha=0.75, clip=clip)
        if strings:
            for x in (-0.11, 0.11):
                top = _chest_point(view, x, 6.5, _front_z(6.5, ease + 0.04))
                low = _chest_point(view, x * 1.15, 5.95, _front_z(5.95, ease + 0.04))
                canvas.add(geom.taper([top, low], view.unit * 0.018, start=1.0, end=1.0), strings, garment.name + "_string",
                           outline=(line_width * 0.6, trace_color(to_rgb(strings))))
        if pocket:
            edge = [_chest_point(view, x, y, _front_z(y, ease + 0.04) if y > 4.9 else 0.44 + ease)
                    for x, y in ((-0.42, 4.45), (-0.3, 5.1), (0.3, 5.1), (0.42, 4.45))]
            canvas.stroke(edge, line_width * 0.8, ink, start=0.8, end=0.8, alpha=0.7, clip=clip)
    kw.setdefault("folds", 0.35)
    return Garment(name, color, build, detail=detail, **kw)
