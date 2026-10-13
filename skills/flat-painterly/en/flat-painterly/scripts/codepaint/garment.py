"""Clothing: pieces worn on a figure3d body. Clothing outlines follow the body at any turn angle.

Torso garments use torso sections inflated by ease, and joining the projected left and right end points of each
section gives the outline.
Hems of skirts, coats and robes stack more sections below the pelvis to flare, and sections widen to cover the legs
when walking or dancing.
Sleeves and trouser legs are thick bands around limb bones. Shoes are convex hulls of the inflated foot point cloud.
Each piece has a mass (group) to paint on, and character.paint_figure lays it over that body mass after painting the
mass.
The unit is the head height, and part coordinates (thorax, pelvis) match figure3d.Figure3D.
"""
from dataclasses import dataclass

import numpy as np

from . import color as colors
from . import geometry
from .figure import CAP_SEGMENTS, LIMB_PROFILE
from .figure3d import FRONT_ROUNDNESS, hull_path

RING_SAMPLES = 64
HEM_STEPS = 7
HEM_START = 0.32           # height in pelvis coordinates where the hem leaves the body and starts to flare (below the widest part of the hips)
LINE_VISIBLE = 0.12        # inner lines are drawn only when the garment surface faces the viewer this much
LEG_MARGIN = 0.05          # extra distance from the leg surface when the hem covers a leg
SHOE_GROWTH = 1.12         # shoes inflate the bare foot point cloud by this factor
BUTTON_RADIUS = 0.022
ROOT_EASE = 1.06           # thickness factor of the sleeve root at the shoulder
LEG_ROOT = 1.03            # the trouser leg root is only slightly thicker than the skin, hiding it inside the trouser waist while covering the skin edge
LIMB_ENDS = {"upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"), "thigh": ("hip", "knee"),
             "shin": ("knee", "ankle")}


@dataclass(frozen=True)
class Garment:
    """One clothing piece.

    group: the mass to paint on. body, arm_l, arm_r, leg_l and leg_r go on that limb's mass when the limb is painted
    apart from the body,
        and on the body mass when the limb merges with it. cape hangs behind the back and is painted over the body
        only when it faces the viewer.
    paths: list of screen outlines (painted merged). palette: (base, shadow, light side, line).
    lines: inner lines [(screen point list, width, strength), ...]. dots: points such as buttons [(screen
    coordinates, radius), ...].
    order: paint order within one mass (smaller first). shine: strong metallic glint (0-1).
    facing: how much the back of a cape faces the viewer (above 0 it is painted over the body).
    merge: pieces with the same value that land in the same mass are merged into one shape (trouser waist and legs).
    """
    name: str
    group: str
    paths: tuple
    palette: tuple
    lines: tuple = ()
    dots: tuple = ()
    order: float = 0.0
    shine: float = 0.0
    facing: float = 0.0
    merge: str = ""


@dataclass(frozen=True)
class Hem:
    """A hem that flares below the pelvis. length is the hem height in pelvis coordinates (about 2.0 for the knee,
    3.8 for the ankle).

    flare is the extra half-width at the hem, wave is the ripple amplitude ratio of the hem, waves is the ripple
    count, swirl is the ripple rotation angle.
    drift is how far wind or a stride pushes the hem back (+) (the flutter of a cape).
    """
    length: float
    flare: float = 0.2
    wave: float = 0.0
    waves: int = 7
    swirl: float = 0.0
    drift: float = 0.0


def cloth(base, line=None):
    """Make the four clothing colors (base, shadow, light side, line) from one base color."""
    shade = colors.shade(base)
    return (base, _hex(shade), _hex(colors.tint(base, 0.35)), line or _hex(colors.shade(shade, 1.6) * 0.7))


def _hex(value):
    value = np.clip(np.asarray(value, np.float64), 0.0, 1.0)
    return "#" + "".join(f"{int(round(channel * 255)):02x}" for channel in value)


# ---------- torso garment sections ----------

@dataclass(frozen=True)
class _Section:
    part: str
    y: float
    cx: float
    cz: float
    width: float
    front: float
    back: float
    wave: float = 0.0
    waves: int = 0
    phase: float = 0.0


def _order_key(part, y):
    return (0 if part == "thorax" else 1, y)


def _body_sections(body, top, bottom, ease, loose=0.0):
    """Torso sections between top and bottom (part, y), inflated by ease, from top to bottom.

    loose (0-1) is the slack. Sections narrower than their neighbors, such as a concave waist, are filled toward the
    neighbors so the fabric stands off the body.
    """
    result = [_Section(top[0], top[1], 0.0, 0.0, *(value + ease for value in body._section_at(*top)))]
    for part, y, width, front, back in body._sections():
        if _order_key(*top) < _order_key(part, y) < _order_key(*bottom):
            result.append(_Section(part, y, 0.0, 0.0, width + ease, front + ease, back + ease))
    result.append(_Section(bottom[0], bottom[1], 0.0, 0.0, *(value + ease for value in body._section_at(*bottom))))
    if loose <= 0.0:
        return result
    filled = [result[0]]
    for before, current, after in zip(result, result[1:], result[2:]):
        bridge = lambda key: max(getattr(current, key), loose * min(getattr(before, key), getattr(after, key))  # noqa: E731
                                 + (1.0 - loose) * getattr(current, key))
        filled.append(_Section(current.part, current.y, 0.0, 0.0, bridge("width"), bridge("front"), bridge("back")))
    return filled + [result[-1]]


def _leg_extent(body, height):
    """x and z range in pelvis coordinates occupied by both legs at pelvis height height. None if no leg passes that
    height."""
    target = body.local_point("pelvis", 0.0, height, 0.0)[1]
    rotation, origin = body.rotations["pelvis"], body.origins["pelvis"]
    xs, zs = [], []
    for side in "lr":
        for bone in ("thigh", "shin"):
            start, end = (body.joints3[f"{joint}_{side}"] for joint in LIMB_ENDS[bone])
            low, high = sorted((start[1], end[1]))
            if not low <= target <= high or abs(end[1] - start[1]) < 1e-6:
                continue
            t = (target - start[1]) / (end[1] - start[1])
            radius = np.interp(t, np.linspace(0.0, 1.0, 4), LIMB_PROFILE[bone]) * body.build.leg / 2.0
            local = rotation.T @ (start + (end - start) * t - origin)
            xs += [local[0] - radius, local[0] + radius]
            zs += [local[2] - radius, local[2] + radius]
    return (min(xs), max(xs), min(zs), max(zs)) if xs else None


def _hem_sections(body, start, ease, hem):
    """Sections that flare from below the hips to the hem. Where a leg leaves a section, the section widens to cover
    it."""
    result = []
    for t in np.linspace(0.0, 1.0, HEM_STEPS)[1:]:
        height = HEM_START + (hem.length - HEM_START) * t
        width, front, back = start.width + hem.flare * t, start.front + hem.flare * t * 0.85, \
            start.back + hem.flare * t * 0.85
        x_lo, x_hi, z_lo, z_hi = -width, width, -front, back
        legs = _leg_extent(body, height)
        if legs is not None:
            x_lo, x_hi = min(x_lo, legs[0] - LEG_MARGIN), max(x_hi, legs[1] + LEG_MARGIN)
            z_lo, z_hi = min(z_lo, legs[2] - LEG_MARGIN), max(z_hi, legs[3] + LEG_MARGIN)
        z_lo, z_hi = z_lo + hem.drift * t * t, z_hi + hem.drift * t * t
        cz = (z_lo + z_hi) / 2.0
        result.append(_Section("pelvis", height, (x_lo + x_hi) / 2.0, cz, (x_hi - x_lo) / 2.0, cz - z_lo, z_hi - cz,
                               hem.wave * t, hem.waves, np.deg2rad(hem.swirl) * t))
    return result


def _ring(section, samples=RING_SAMPLES):
    """(part-coordinate point list, part-coordinate normals, angles) of one section. Angle 0 is front center, 90 is
    screen right (in front view)."""
    angle = np.linspace(-np.pi, np.pi, samples, endpoint=False)
    sin, cos = np.sin(angle), np.cos(angle)
    exponent = 2.0 / FRONT_ROUNDNESS
    x = section.width * np.sign(sin) * np.abs(sin) ** exponent
    depth = np.where(cos > 0.0, section.front * np.abs(cos) ** exponent, -section.back * np.abs(cos))
    scale = 1.0 + section.wave * np.sin(section.waves * angle + section.phase)
    points = np.column_stack([section.cx + x * scale, np.full(samples, section.y), section.cz - depth * scale])
    normals = np.column_stack([sin / max(section.width, 1e-6), np.zeros(samples),
                               -cos / np.where(cos > 0.0, max(section.front, 1e-6), max(section.back, 1e-6))])
    return points, normals / np.linalg.norm(normals, axis=1, keepdims=True), np.rad2deg(angle)


class Loft:
    """A garment body stacked from sections. outline() gives the screen outline, line_at() a vertical line on the
    surface, ring_line() a horizontal line."""

    def __init__(self, body, sections, half=None):
        self.body = body
        self.sections = sections
        self.half = half

    def _body_ring(self, section):
        points, normals, angles = _ring(section)
        if self.half == "back":
            keep = points[:, 2] >= section.cz - 1e-9
            points, normals, angles = points[keep], normals[keep], angles[keep]
        rotation = self.body.rotations[section.part]
        world = np.array([self.body.local_point(section.part, *point) for point in points])
        return world, normals @ rotation.T, angles

    def outline(self):
        """Screen outline. Joins the projected left and right end points of each section, and closes with the upper
        and lower arcs of the top and bottom rings.

        Closing both ends with arcs keeps the curve from bulging at the corners.
        """
        right, left, rings = [], [], []
        for section in self.sections:
            world, _, _ = self._body_ring(section)
            projected = self.body._rig2d(world)
            rings.append(projected)
            right.append(projected[np.argmax(projected[:, 0])])
            left.append(projected[np.argmin(projected[:, 0])])
        top = _arc(rings[0], lower=False)[::-1]          # from the left end, around the top, to the right end
        bottom = _arc(rings[-1], lower=True)              # from the right end, around the bottom, to the left end
        chain = np.array(list(top) + right[1:-1] + list(bottom) + left[-2:0:-1])
        return geometry.spline(self.body.frame(chain), closed=True)

    def line_at(self, angle, start=0, stop=None):
        """Vertical line at angle on the surface. List of screen point lists of the visible spans."""
        points, facings = [], []
        for section in self.sections[start:stop]:
            world, normals, angles = self._body_ring(section)
            index = int(np.argmin(np.abs((angles - angle + 180.0) % 360.0 - 180.0)))
            points.append(self.body.project(world[index]))
            facings.append(self.body.facing(normals[index]))
        return _visible_runs(points, facings)

    def ring_line(self, index):
        """Horizontal line around one section (waistline, hem). The visible spans."""
        world, normals, _ = self._body_ring(self.sections[index])
        return _visible_runs([self.body.project(point) for point in world], [self.body.facing(n) for n in normals])

    def surface_point(self, index, angle):
        """Surface point (screen coordinates) at angle on section index, and how much it faces the viewer."""
        world, normals, angles = self._body_ring(self.sections[index])
        nearest = int(np.argmin(np.abs((angles - angle + 180.0) % 360.0 - 180.0)))
        return self.body.project(world[nearest]), self.body.facing(normals[nearest])


def _arc(projected, lower):
    """Arc of the projected ring from its right end to its left end. With lower it runs along the screen bottom
    (larger y), otherwise along the top."""
    right, left = int(np.argmax(projected[:, 0])), int(np.argmin(projected[:, 0]))
    count = len(projected)
    forward = [projected[(right + step) % count] for step in range((left - right) % count + 1)]
    backward = [projected[(right - step) % count] for step in range((right - left) % count + 1)]
    forward_lower = np.mean([p[1] for p in forward]) > np.mean([p[1] for p in backward])
    return forward if forward_lower == lower else backward


def _visible_runs(points, facings, threshold=LINE_VISIBLE):
    runs, current = [], []
    for point, facing in zip(points, facings):
        if facing > threshold:
            current.append(point)
        elif current:
            runs.append(np.array(current))
            current = []
    if current:
        runs.append(np.array(current))
    return [run for run in runs if len(run) >= 2]


def loft(body, top, bottom, ease, hem=None, half=None, loose=0.0):
    """Torso garment. top and bottom are (part, y). With hem, a hem is stacked below pelvis HEM_START. half='back'
    makes a cape.

    loose is the slack that fills concave places such as the waist (0 hugs the body, 1 joins the upper and lower
    sections straight).
    """
    if hem is None:
        return Loft(body, _body_sections(body, top, bottom, ease, loose), half)
    sections = _body_sections(body, top, ("pelvis", HEM_START), ease, loose)
    return Loft(body, sections + _hem_sections(body, sections[-1], ease, hem), half)


# ---------- limb garments ----------

def _tube(body, start, end, widths, caps=(True, True)):
    """List of screen outlines of a thick band joining two body-coordinate points. caps picks the round caps at the
    ends."""
    a, b = body._rig2d(start)[0], body._rig2d(end)[0]
    if np.linalg.norm(b - a) < 1e-4:
        b = a + (0.0, 1e-4)
    spine = geometry.densify(np.array([a, b]), 12)
    paths = geometry.ribbon(spine, widths)
    for point, width, cap in ((a, widths[0], caps[0]), (b, widths[-1], caps[1])):
        if cap:
            paths.append(geometry.ellipse(point[0], point[1], width / 2.0, segments=CAP_SEGMENTS))
    return [body.frame(path) for path in paths]


def limb_span(body, bone, side, t0=0.0, t1=1.0, scale=1.25, widths=None, caps=(True, True), root=None):
    """A band wrapped thickly around the t0 to t1 span of a bone. With widths, that width list (head heights) is
    used as is (bell sleeves).

    A band starting at the bone root (t0 0) keeps its root width close to the skin (root factor, default ROOT_EASE)
    so the round cap does not stick up over the shoulder or hip. A sleeve hangs from the shoulder and widens along
    the upper arm.
    """
    start, end = (body.joints3[f"{joint}_{side}"] for joint in LIMB_ENDS[bone])
    limb_scale = body.build.arm if bone in ("upper_arm", "forearm") else body.build.leg
    profile = lambda t: np.interp(t, np.linspace(0.0, 1.0, 4), LIMB_PROFILE[bone]) * limb_scale  # noqa: E731
    if widths is None:
        widths = [profile(t) * scale for t in np.linspace(t0, t1, 4)]
        if t0 == 0.0:
            widths[0] = profile(0.0) * min(scale, ROOT_EASE if root is None else root)
    return _tube(body, start + (end - start) * t0, start + (end - start) * t1, widths, caps)


def limb_surface(body, bone, side, t, angle, out=1.0, scale=1.25):
    """Surface point (screen) of a clothed limb and how much it faces the viewer. angle is 0 front, 90 outside, 180
    back."""
    start, end = (body.joints3[f"{joint}_{side}"] for joint in LIMB_ENDS[bone])
    axis = (end - start) / max(np.linalg.norm(end - start), 1e-9)
    front = np.cross(axis, (1.0, 0.0, 0.0))
    front /= max(np.linalg.norm(front), 1e-9)
    outward = np.cross(front, axis) * (-1.0 if side == "l" else 1.0)
    normal = np.cos(np.deg2rad(angle)) * front + np.sin(np.deg2rad(angle)) * outward
    limb_scale = body.build.arm if bone in ("upper_arm", "forearm") else body.build.leg
    radius = np.interp(t, np.linspace(0.0, 1.0, 4), LIMB_PROFILE[bone]) * limb_scale * scale / 2.0
    return body.project(start + (end - start) * t + normal * radius * out), body.facing(normal)


def limb_marks(body, side, marks, scale=1.25):
    """Clothing fold line through [(bone, t, angle), ...]. The visible spans."""
    samples = [limb_surface(body, bone, side, t, angle, scale=scale) for bone, t, angle in marks]
    return _visible_runs([point for point, _ in samples], [facing for _, facing in samples])


def shoe(body, side, growth=SHOE_GROWTH, lift=0.0):
    """Shoe silhouette. Inflates the bare foot point cloud from the foot center. lift is the heel height, which
    stretches the sole downward."""
    cloud = body._foot_cloud(side)
    center = cloud.mean(axis=0)
    grown = center + (cloud - center) * growth
    grown[:, 1] = np.maximum(grown[:, 1], cloud[:, 1])     # keep it from inflating below the floor
    if lift > 0.0:
        heel = grown[grown[:, 1] > cloud[:, 1].max() - 0.05]
        grown = np.vstack([grown, heel + (0.0, lift, 0.0)])
    return [body.frame(hull_path(body._rig2d(grown)))]


# ---------- small pieces ----------

def neck_band(body, height=0.55, ease=0.06):
    """A band around the neck (scarf, high collar). Convex hull of a short cylinder around the lower height span of
    the neck."""
    base, top = body.joints3["shoulder_mid"], body.joints3["neck_top"]
    radius = body.build.neck * 1.12 / 2.0 + ease
    angle = np.linspace(0.0, 2.0 * np.pi, 32, endpoint=False)
    ring = np.column_stack([np.cos(angle) * radius, np.zeros_like(angle), np.sin(angle) * radius * 0.92])
    # Three rings that swell downward and sag at the front. They show the thickness and weight of wrapped
    # cloth.
    levels = ((0.0, 1.35, 0.12), (height * 0.45, 1.2, 0.05), (height, 1.0, 0.0))
    droop = np.column_stack([np.zeros_like(angle), np.maximum(-np.sin(angle), 0.0), np.zeros_like(angle)])
    points = np.vstack([base + (top - base) * t + ring * puff + droop * sag for t, puff, sag in levels])
    return [body.frame(hull_path(body._rig2d(points)))]


def bulge(body, part, center, radii):
    """Ellipsoid in part coordinates (pauldron, lowered hood). List of screen outlines."""
    return [body.bulge(part, *center, radii)]


def surface_curve(body, part, points, side="front", lift=0.02):
    """Curve on the torso surface (collar, front opening, necktie). points are part coordinates (x, y). The visible
    spans."""
    screen, facings = [], []
    for x, y in points:
        point, normal = body.surface(part, x, y, side)
        screen.append(body.project(point + normal * lift))
        facings.append(body.facing(normal))
    return _visible_runs(screen, facings)


def surface_dots(body, part, points, side="front", lift=0.02, radius=BUTTON_RADIUS):
    """Buttons on the torso surface. Only the visible ones [(screen coordinates, radius), ...]."""
    result = []
    for x, y in points:
        point, normal = body.surface(part, x, y, side)
        if body.facing(normal) > LINE_VISIBLE:
            result.append((body.project(point + normal * lift), radius * body.frame.unit))
    return result


def lines(runs, width=1.4, opacity=0.6):
    """Convert a list of line spans to the Garment.lines format."""
    return tuple((run, width, opacity) for run in runs)


# ---------- outfits ----------
# Each function takes colors and returns "a function that takes a body and returns a list of pieces". Pass it
# to character.place(outfit=...).
# order: shoes 1, trouser legs 2, trouser waist 3, top 4, sleeves 4, outerwear 5, belt 6, scarf 7, pauldron 8.

def _pants(body, base, scale=1.22, reach=0.97, waist=-0.85):
    palette = cloth(base)
    hip = loft(body, ("pelvis", waist), ("pelvis", 0.5), 0.07)
    pieces = [Garment("pants", "body", (hip.outline(),), palette, order=2, merge="pants",
                      lines=lines(surface_curve(body, "pelvis", [(0.03, waist + 0.08), (0.05, -0.2)]), 1.2, 0.5))]
    for side in "lr":
        paths = limb_span(body, "thigh", side, 0.0, 1.0, scale, root=LEG_ROOT) + \
            limb_span(body, "shin", side, 0.0, reach, scale * 1.02, caps=(True, False))
        folds = limb_marks(body, side, [("thigh", 0.9, -35), ("thigh", 0.97, 0), ("thigh", 0.9, 35)], scale) + \
            limb_marks(body, side, [("shin", 0.8, -20), ("shin", 0.86, 20)], scale)
        pieces.append(Garment("pant_leg_" + side, "leg_" + side, tuple(paths), palette, lines(folds, 1.2, 0.5), order=2,
                              merge="pants"))
    return pieces


def _shoes(body, base, growth=SHOE_GROWTH, lift=0.0):
    palette = cloth(base)
    return [Garment("shoe_" + side, "leg_" + side, tuple(shoe(body, side, growth, lift)), palette, order=1)
            for side in "lr"]


def _boots(body, base, top=0.55):
    palette = cloth(base)
    pieces = []
    for side in "lr":
        paths = limb_span(body, "shin", side, top, 1.0, 1.22, caps=(False, True)) + shoe(body, side, 1.13)
        pieces.append(Garment("boot_" + side, "leg_" + side, tuple(paths), palette, order=2.5))
    return pieces


def _sleeves(body, base, reach=0.92, scale=1.3, short=None, bell=None, order=4):
    """Long sleeves (reach is where they end on the forearm). With short, short sleeves ending at that point on the
    upper arm. bell is the cuff width factor."""
    palette = cloth(base)
    pieces = []
    for side in "lr":
        if short is not None:
            paths = limb_span(body, "upper_arm", side, 0.0, short, scale, caps=(True, False))
            folds = []
        else:
            paths = limb_span(body, "upper_arm", side, 0.0, 1.0, scale)
            widths = None
            if bell is not None:
                base_width = LIMB_PROFILE["forearm"][0] * body.build.arm * scale
                widths = [base_width * factor for factor in np.linspace(1.0, bell, 4)]
            paths += limb_span(body, "forearm", side, 0.0, reach, scale, widths=widths, caps=(True, False))
            folds = limb_marks(body, side, [("upper_arm", 0.86, -70), ("forearm", 0.1, -50), ("forearm", 0.2, -20)],
                               scale)
        pieces.append(Garment("sleeve_" + side, "arm_" + side, tuple(paths), palette, lines(folds, 1.2, 0.5),
                              order=order))
    return pieces


def _cape(body, base, length, ease=0.16, flare=0.6, drift=0.0):
    shape = loft(body, ("thorax", -0.22), None, ease, hem=Hem(length, flare, wave=0.05, waves=5, drift=drift),
                 half="back")
    facing = body.facing(body.rotations["thorax"] @ np.array([0.0, 0.0, 1.0]))
    folds = [run for angle in (130, 160, -160, -130) for run in shape.line_at(angle, start=4)]
    return Garment("cape", "cape", (shape.outline(),), cloth(base), lines(folds, 1.3, 0.55), facing=facing)


def _scarf(body, base, tail=True):
    palette = cloth(base)
    paths = neck_band(body, 0.55, 0.07)
    if tail:
        runs = surface_curve(body, "thorax", [(0.16, -0.06), (0.24, 0.3), (0.26, 0.82)], lift=0.15)
        for run in runs:
            unit = body.frame.unit
            paths += geometry.ribbon(geometry.densify(run, 12), (0.17 * unit, 0.15 * unit, 0.16 * unit))
    return Garment("scarf", "body", tuple(paths), palette, order=7)


def casual_knit(knit="#c8b49c", pants="#3e4a62", shoes="#5c4033"):
    """Casual wear (women's): crew-neck knit, long trousers, flats."""
    def build(body):
        top = loft(body, ("thorax", -0.17), ("pelvis", -0.42), 0.06, loose=0.5)
        neck = surface_curve(body, "thorax", [(-0.26, -0.13), (-0.13, -0.01), (0.0, 0.03), (0.13, -0.01), (0.26, -0.13)])
        details = lines(neck, 1.5, 0.8) + lines(top.ring_line(len(top.sections) - 1), 1.2, 0.5)
        return (_shoes(body, shoes, 1.08) + _pants(body, pants, 1.16)
                + [Garment("knit", "body", (top.outline(),), cloth(knit), details, order=4)]
                + _sleeves(body, knit, 0.94, 1.32))
    return build


def casual_shirt(shirt="#7e9cb8", pants="#454545", shoes="#e8e4dc"):
    """Casual wear (men's): collared short-sleeve shirt, trousers, sneakers."""
    def build(body):
        top = loft(body, ("thorax", -0.18), ("pelvis", -0.3), 0.08, loose=0.7)
        collar = surface_curve(body, "thorax", [(-0.3, -0.16), (-0.1, 0.04), (0.0, 0.16)]) + \
            surface_curve(body, "thorax", [(0.3, -0.16), (0.1, 0.04), (0.0, 0.16)])
        placket = surface_curve(body, "thorax", [(0.0, 0.16), (0.0, 0.98)]) + \
            surface_curve(body, "pelvis", [(0.0, -0.98), (0.0, -0.36)])
        buttons = surface_dots(body, "thorax", [(0.0, 0.32), (0.0, 0.62), (0.0, 0.92)])
        return (_shoes(body, shoes, 1.16, 0.03) + _pants(body, pants, 1.22)
                + [Garment("shirt", "body", (top.outline(),), cloth(shirt), lines(collar, 1.6, 0.85)
                           + lines(placket, 1.2, 0.6), buttons, order=4)]
                + _sleeves(body, shirt, short=0.62, scale=1.38))
    return build


def formal_dress(dress="#9e2a2b", shoes="#2a1a1a", length=3.6, flare=0.55, wave=0.06, swirl=0.0, sash=None):
    """Formal wear (women's): a long fitted-waist dress with short sleeves, heeled shoes. swirl rotates the hem
    ripples to express a spin."""
    def build(body):
        gown = loft(body, ("thorax", -0.12), None, 0.04, hem=Hem(length, flare, wave, 7, swirl))
        start = len(_body_sections(body, ("thorax", -0.12), ("pelvis", HEM_START), 0.04)) - 1
        folds = [run for angle in (-70, -40, -12, 15, 45, 75) for run in gown.line_at(angle, start=start)]
        neck = surface_curve(body, "thorax", [(-0.3, -0.1), (-0.15, 0.12), (0.0, 0.2), (0.15, 0.12), (0.3, -0.1)])
        waist = surface_curve(body, "pelvis", [(x, -0.66) for x in np.linspace(-0.5, 0.5, 9)], lift=0.05)
        pieces = _shoes(body, shoes, 1.06, 0.06) + [
            Garment("dress", "body", (gown.outline(),), cloth(dress), lines(neck, 1.5, 0.8) + lines(waist, 1.6, 0.8)
                    + lines(folds, 1.3, 0.5), order=4)] + _sleeves(body, dress, short=0.3, scale=1.3)
        if sash is not None:
            band = loft(body, ("pelvis", -0.72), ("pelvis", -0.64), 0.05)
            pieces.append(Garment("sash", "body", (band.outline(),), cloth(sash), order=6))
        return pieces
    return build


def formal_suit(jacket="#2d3340", shirt="#eeeae2", tie="#7a2830", pants=None, shoes="#1c1714"):
    """Formal wear (men's): a jacket that covers the hips, shirt front and necktie, slacks, dress shoes."""
    def build(body):
        coat = loft(body, ("thorax", -0.16), ("pelvis", 0.36), 0.1, loose=0.6)
        lapels = surface_curve(body, "thorax", [(-0.3, -0.12), (-0.24, 0.3), (0.0, 0.8)], lift=0.1) + \
            surface_curve(body, "thorax", [(0.3, -0.12), (0.24, 0.3), (0.0, 0.8)], lift=0.1)
        hem_front = surface_curve(body, "thorax", [(0.0, 0.8), (0.02, 0.98)], lift=0.1) + \
            surface_curve(body, "pelvis", [(0.02, -0.98), (0.08, 0.3)], lift=0.1)
        buttons = surface_dots(body, "pelvis", [(0.06, -0.9), (0.06, -0.62)], lift=0.1)
        front = _shirt_front(body, shirt, tie)
        return (_shoes(body, shoes, 1.08, 0.02) + _pants(body, pants or jacket, 1.2)
                + [Garment("jacket", "body", (coat.outline(),), cloth(jacket),
                           lines(lapels, 1.6, 0.85) + lines(hem_front, 1.3, 0.7), buttons, order=5)]
                + front + _sleeves(body, jacket, 0.93, 1.34, order=5))
    return build


def _shirt_front(body, shirt, tie):
    """Shirt front and necktie seen between the jacket lapels. Only when the front is visible."""
    pieces = []
    for name, base, outline, order in (("shirt_front", shirt, [(-0.22, -0.16), (0.0, -0.2), (0.22, -0.16), (0.0, 0.8)], 6),
                                       ("tie", tie, [(-0.05, -0.12), (0.05, -0.12), (0.07, 0.62), (0.0, 0.74),
                                                     (-0.07, 0.62)], 7)):
        surface = [body.surface("thorax", x, y) for x, y in outline]
        if min(body.facing(normal) for _, normal in surface) > LINE_VISIBLE:
            points = np.array([body.project(point + normal * 0.11) for point, normal in surface])
            pieces.append(Garment(name, "body", (points,), cloth(base), order=order))
    return pieces


def long_coat(coat="#8a6f55", scarf="#c44536", legs="#2b2b33", boots="#3b2a20", length=2.0, belt=True,
              scarf_tail=True):
    """Outerwear: knee-length coat, belt, scarf, fitted trousers, boots. Reduce length to 1.4 for thigh length."""
    def build(body):
        shape = loft(body, ("thorax", -0.16), None, 0.12, hem=Hem(length, 0.18), loose=0.5)
        start = len(_body_sections(body, ("thorax", -0.16), ("pelvis", HEM_START), 0.12)) - 1
        folds = [run for angle in (-50, 20, 60) for run in shape.line_at(angle, start=start + 1)]
        closing = surface_curve(body, "thorax", [(0.1, 0.1), (0.12, 0.98)], lift=0.13) + \
            surface_curve(body, "pelvis", [(0.12, -0.98), (0.14, 0.3)], lift=0.13)
        buttons = surface_dots(body, "thorax", [(0.2, 0.4), (0.2, 0.75)], lift=0.13) + \
            surface_dots(body, "thorax", [(-0.04, 0.4), (-0.04, 0.75)], lift=0.13)
        pieces = (_pants(body, legs, 1.08) + _boots(body, boots)
                  + [Garment("coat", "body", (shape.outline(),), cloth(coat), lines(closing, 1.4, 0.75)
                             + lines(folds, 1.3, 0.5), buttons, order=5)]
                  + _sleeves(body, coat, 0.94, 1.46, order=5) + [_scarf(body, scarf, scarf_tail)])
        if belt:
            band = loft(body, ("pelvis", -0.8), ("pelvis", -0.64), 0.15)
            pieces.append(Garment("belt", "body", (band.outline(),), cloth(_hex(colors.shade(coat, 0.8))), order=6))
        return pieces
    return build


def mage_robe(robe="#3c4f7a", cape="#6e2c3a", sash="#d8b45a", boots="#4a3426", length=3.75, cape_drift=0.0):
    """Fantasy (women's): an ankle-length robe, bell sleeves, belt, cape, boots."""
    def build(body):
        shape = loft(body, ("thorax", -0.15), None, 0.08, hem=Hem(length, 0.35, 0.03, 6), loose=0.6)
        start = len(_body_sections(body, ("thorax", -0.15), ("pelvis", HEM_START), 0.08)) - 1
        folds = [run for angle in (-55, -20, 20, 55) for run in shape.line_at(angle, start=start)]
        neck = surface_curve(body, "thorax", [(-0.24, -0.14), (0.0, 0.3), (0.24, -0.14)])
        band = loft(body, ("pelvis", -0.76), ("pelvis", -0.6), 0.1)
        trim = surface_curve(body, "thorax", [(0.0, 0.3), (0.0, 0.98)]) + \
            surface_curve(body, "pelvis", [(0.0, -0.98), (0.0, 0.32)])
        return (_boots(body, boots, 0.7)
                + [Garment("robe", "body", (shape.outline(),), cloth(robe), lines(neck, 1.6, 0.85)
                           + lines(trim, 1.4, 0.6) + lines(folds, 1.3, 0.5), order=4),
                   Garment("sash", "body", (band.outline(),), cloth(sash), order=6)]
                + _sleeves(body, robe, 0.9, 1.34, bell=2.3) + [_cape(body, cape, length - 0.4, drift=cape_drift)])
    return build


def light_armor(tunic="#5a6b4a", metal="#9aa3ad", leather="#6b4a2f", cape="#2f4a6b", legs="#3a3530",
                boots="#4a3426", cape_drift=0.0):
    """Fantasy (men's): a thigh-length tunic, breastplate, pauldrons, bracers, leather belt, cape, boots."""
    def build(body):
        tunic_shape = loft(body, ("thorax", -0.16), None, 0.08, hem=Hem(1.45, 0.12), loose=0.6)
        plate = loft(body, ("thorax", -0.06), ("pelvis", -0.6), 0.15)
        ridge = plate.line_at(0.0)
        band = loft(body, ("pelvis", -0.72), ("pelvis", -0.5), 0.19)
        metal_palette = cloth(metal)
        pieces = (_pants(body, legs, 1.12) + _boots(body, boots, 0.45)
                  + [Garment("tunic", "body", (tunic_shape.outline(),), cloth(tunic), order=4),
                     Garment("breastplate", "body", (plate.outline(),), metal_palette, lines(ridge, 1.4, 0.6),
                             order=5, shine=0.55),
                     Garment("belt", "body", (band.outline(),), cloth(leather), order=6)]
                  + _sleeves(body, tunic, 0.9, 1.3) + [_cape(body, cape, 3.0, drift=cape_drift)])
        for side, sign in (("l", -1.0), ("r", 1.0)):
            pauldron = bulge(body, "thorax", (sign * (body.build.shoulder + 0.02), body.shoulder_drop - 0.04, 0.0),
                             (0.3, 0.22, 0.32))
            pieces.append(Garment("pauldron_" + side, "arm_" + side, tuple(pauldron), metal_palette, order=8,
                                  shine=0.55))
            bracer = limb_span(body, "forearm", side, 0.35, 0.95, 1.5, caps=(True, True))
            pieces.append(Garment("bracer_" + side, "arm_" + side, tuple(bracer), cloth(leather), order=6))
        return pieces
    return build
