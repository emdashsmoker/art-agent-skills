"""Cloth that falls away from the body: skirts, dresses, scarves, and wind.

Shell garments (atelier.wardrobe) follow the body. A skirt does not: it sits on
the waist, follows the hips down to their widest line, and from there falls free
in an A-line, wider than the legs under it, in folds, and it moves in the wind.
Flare is that surface: an open shell round a vertical axis whose radius in every
direction is fitted to the posed body (the melted skin, the legs spanned the way
cloth spans them, so a stride widens the skirt), rippled into folds or pleats
from the hips down, pushed and lifted downwind.

Sitting and lying, a skirt lies over the lap and follows the thighs; there a
tube skirt (the hips and thighs grown, the gap between the legs bridged) takes
over, and flared_skirt switches to it by itself.
"""
import cv2
import numpy as np

from .mannequin import dress
from .sculpt import Capsule, Ellipsoid, facing
from .wardrobe import FIT, SMOOTH, Skin, Surface, around, cut_leg, hem, rod, shapes_of, strap

SHELL = 0.0035          # half thickness of a skirt shell, metres
HEM_WAVE = 0.005        # metres the hem rises and falls with the folds
SWAY = 0.30             # share of the wind's length the hem moves downwind
BILLOW = 0.45           # how much the downwind side swells, per metre of wind
DENT_ANGLE = 0.30       # radians round the skirt a resting hand pushes in
DENT_HEIGHT = 0.09      # metres up and down a resting hand pushes in
DENT_MARGIN = 0.002     # a hand pushes the skirt in until it lies this far off the skin
CLEARANCE = 0.014       # below the hips the skirt never comes closer to the body than this
WAIST_EASE = 0.004      # at the waist it sits on the skin: a wider waist shows its rim like a bucket
LIFT_PER_WIND = 0.55    # share of the length the hem rises downwind, per metre of wind
RIPPLE_PER_WIND = 0.05  # extra fold depth from wind, per metre of wind
# Per metre of wind, how much of the flare the wind flattens on the upwind side (1 = all):
# that side lies against the legs instead of bulging.
WIND_PRESS = 2.0
SEATED_THIGH = 50.0     # degrees from vertical past which a skirt lies on the lap
KNEE_RISE = 0.05        # knees this far above the hips count as raised (sitting on the ground)
WEB_THICKNESS = 0.45    # half thickness of cloth stretched between parted legs, share of the thigh radius
PROFILE_STEPS = 13      # heights at which the skirt is fitted round the body
PROFILE_ROWS = 49       # rows of the fitted radius table (finer than the fit, for smooth shading)
ANGLES = 72             # directions round the axis in which the skirt is fitted
WAIST = 0.125           # height of a skirt waist above the hip joints (pelvis frame)
DRESS_WAIST = 0.165     # a dress joins its skirt higher, at the natural waist
HIP_LINE = -0.02        # height of the widest hips relative to the hip joints (measured)
FOLD_START = 0.7        # folds begin this share of the way from the waist to the hip line
FOLD_JITTER = (0.55, 0.30)   # uneven fold spacing: radians of shift at 2 and 3 cycles round
FOLD_SWELL = (0.30, 0.20)    # uneven fold depth: share at 3 and 5 cycles round
SAFETY_SAMPLES = (40, 720)   # heights and angles at which the shell's steepest slope is sampled
BODY_BELOW_WAIST = ("pelvis", "thigh", "shin", "abdomen")
NECK_REST = ("neck", "chest", "shoulder", "breast")   # what a scarf wound round the neck rests on
# Each turn of a scarf round the neck: (height over the neck base, extra room, front-low tilt).
SCARF_TURNS = ((0.022, 0.004, 0.35), (0.042, 0.010, 0.30))
SCARF_SQUASH = 0.5         # share of a turn's thickness it may press into the shoulders
SCARF_KNOT_ANGLE = 30.0     # degrees from the front toward the figure's left where the ends are knotted
# Each end of a scarf: (share of the length, sideways drift hanging, wave phase, droop in wind).
SCARF_ENDS = ((1.0, 0.035, 0.0, 0.0), (0.8, -0.010, 1.7, 0.45))
SCARF_THICKNESS = 0.0022    # half thickness of the cloth, metres
SCARF_STEP = 0.012          # metres between points along a scarf end
SCARF_OFF_BODY = 0.010      # a hanging end keeps this far off the chest
SCARF_PROBE = 0.2           # metres behind a hanging end from which the chest under it is found
SCARF_SAG = 0.12            # how far a streaming end droops at its tip, share of its length
SCARF_FLUTTER = 0.06        # sideways ripple of a streaming end at its tip, share of its length
SCARF_WAVES = 1.6           # ripples along a streaming end
SCARF_TWIST = 0.45          # radians a streaming end turns about its length as it ripples
RIBBON_PIECE = 6            # segments per ribbon piece


class Flare:
    """Open cloth shell falling from a waist. profile: (heights t, radii, contact) from
    flare_profile, radii[row, angle] fitted round the body at fractions t of the length
    and ANGLES directions, contact the same lying on the body; folds or pleats from
    `fold_from` metres below the waist down, wind sway and lift."""

    def __init__(self, top, up, front, profile, length, folds=9, fold_depth=0.014, pleats=False,
                 wind=(0.0, 0.0, 0.0), phase=0.0, thickness=SHELL, obstacles=(), fold_from=0.0):
        self.top = np.asarray(top, np.float32)
        self.frame = facing(up, front).astype(np.float32)
        self.length, self.folds, self.pleats, self.phase = float(length), int(folds), pleats, float(phase)
        self.t, self.radii, self.contact = (np.asarray(table, np.float32) for table in profile)
        self.sway, strength, self.wind_angle = _wind(self.frame, wind)
        self.billow = strength * BILLOW                  # the downwind side swells
        self.lift = float(np.clip(strength * LIFT_PER_WIND, 0.0, 0.45))
        self.depth = fold_depth + strength * RIPPLE_PER_WIND
        self.fold_from = float(np.clip(fold_from / self.length, 0.0, 0.9))
        self.thickness = thickness
        # Soft folds hang unevenly: their spacing and depth drift round the skirt.
        rng = np.random.default_rng(int(abs(phase) * 1000) + self.folds)
        self.shifts = rng.uniform(0, 2 * np.pi, 4)
        # Hands and forearms resting against the skirt: (angle, height, how far out the
        # skirt may reach there). The skirt gives way round them instead of swallowing them,
        # but never into the body: a hand resting on the hip lies on the skirt.
        dents = []
        for point, radius in obstacles:
            local = (np.asarray(point, np.float32) - self.top) @ self.frame
            if 0.0 < -local[2] < self.length:
                x, y = local[:2] - self.sway * (-local[2] / self.length) ** 2   # round the swayed axis
                dents.append((np.arctan2(y, x), -local[2], np.hypot(x, y) - radius))
        self.dents = np.array(dents, np.float32).reshape(-1, 3)
        self.safety = self._safety(strength)

    def _safety(self, strength):
        """Folds, flare and dents tilt the surface, so the plain radial gap overstates the
        true distance; scale it down by the steepest slope found, so rays never step through."""
        heights, angles = SAFETY_SAMPLES
        t, theta = np.meshgrid(np.linspace(0, 1, heights, dtype=np.float32),
                               np.linspace(-np.pi, np.pi, angles, dtype=np.float32), indexing="ij")
        radius = self._radius(theta.ravel(), t.ravel()).reshape(t.shape)
        across = np.abs(np.diff(radius, axis=1)) / (2 * np.pi / (angles - 1)) / radius[:, 1:]
        down = np.abs(np.diff(radius, axis=0)) / (self.length / (heights - 1))
        return 1.0 / np.sqrt(1.0 + float(across.max()) ** 2 + float(down.max()) ** 2
                             + (2 * strength / self.length) ** 2)     # the last term: sway bends the axis

    def _fitted(self, theta, t, table=None):
        """Radius from a fitted table (the skirt's by default): bilinear in height and angle."""
        table = self.radii if table is None else table
        rows, count = table.shape
        u = np.mod(theta, 2 * np.pi) / (2 * np.pi) * count
        j0 = np.floor(u).astype(int) % count
        j1, fu = (j0 + 1) % count, u - np.floor(u)
        v = np.clip(t, 0.0, 1.0) * (rows - 1)
        i0 = np.clip(np.floor(v).astype(int), 0, rows - 2)
        fv = v - i0
        upper = table[i0, j0] * (1 - fu) + table[i0, j1] * fu
        lower = table[i0 + 1, j0] * (1 - fu) + table[i0 + 1, j1] * fu
        return upper * (1 - fv) + lower * fv

    def _wave(self, theta):
        """Fold pattern round the skirt, about -1 .. 1."""
        if self.pleats:                                   # sharp knife pleats, sewn evenly
            wave = np.sin(self.folds * theta + self.phase)
            return np.sign(wave) * np.abs(wave) ** 0.35
        a, b, c, d = self.shifts
        drift = FOLD_JITTER[0] * np.sin(2 * theta + a) + FOLD_JITTER[1] * np.sin(3 * theta + b)
        swell = 1.0 + FOLD_SWELL[0] * np.sin(3 * theta + c) + FOLD_SWELL[1] * np.sin(5 * theta + d)
        return np.sin(self.folds * theta + self.phase + drift) * swell

    def _radius(self, theta, t):
        radius = self._fitted(theta, t) * (1.0 + self.billow * t * np.clip(np.cos(theta - self.wind_angle), 0.0, 1.0))
        hanging = np.clip((t - self.fold_from) / (1.0 - self.fold_from), 0.0, 1.0) ** 1.3
        radius = radius + self.depth * hanging * self._wave(theta)
        contact = self._fitted(theta, t, self.contact) if len(self.dents) else None
        for angle, height, room in self.dents:
            near = np.exp(-(_angle_gap(theta, angle) / DENT_ANGLE) ** 2
                          - ((t * self.length - height) / DENT_HEIGHT) ** 2)
            radius = radius - near * np.clip(radius - np.maximum(room, contact), 0.0, None)
        return radius

    def distance(self, points):
        local = (points - self.top) @ self.frame
        h = -local[:, 2]
        t = np.clip(h / self.length, 0.0, 1.0)
        x = local[:, 0] - self.sway[0] * t * t
        y = local[:, 1] - self.sway[1] * t * t
        theta = np.arctan2(y, x)
        shell = (np.abs(np.hypot(x, y) - self._radius(theta, t)) - self.thickness) * self.safety
        downwind = np.clip(np.cos(theta - self.wind_angle), 0.0, 1.0)
        hem_line = self.length * (1.0 - self.lift * downwind) + HEM_WAVE * self._wave(theta)
        return np.maximum.reduce([shell, h - hem_line, -h])

    def bounds(self):
        reach = float(self.radii.max()) * (1.0 + self.billow) + self.depth * 1.5 + float(np.linalg.norm(self.sway))
        centre = self.top - self.frame[:, 2] * self.length / 2
        return centre, float(np.hypot(self.length / 2, reach))


def _wind(frame, wind):
    """Hem sway (local x, y), wind strength and the downwind angle, in a skirt frame."""
    local = frame.T @ np.asarray(wind, np.float32)
    return local[:2] * SWAY, float(np.linalg.norm(local[:2])), float(np.arctan2(local[1], local[0]))


def _angle_gap(a, b):
    return np.angle(np.exp(1j * (a - b)))


def _frames(marks):
    return marks["chest"], marks["chest_frame"], marks["pelvis"], marks["pelvis_frame"]


def _level_front(frame):
    """The figure's front, laid level: skirts hang along gravity, not along the spine."""
    front = -frame[:, 1].copy()
    front[2] = 0.0
    return front / max(np.linalg.norm(front), 1e-9)


def _seated(marks):
    """True when the thighs run closer to level than to upright: sitting or lying."""
    up = np.array([0.0, 0.0, 1.0])
    angles = []
    for name in ("left", "right"):
        thigh = marks[f"{name}_knee"] - marks[f"{name}_hip"]
        angles.append(np.degrees(np.arccos(np.clip(-thigh @ up / np.linalg.norm(thigh), -1, 1))))
    return max(angles) > SEATED_THIGH


def _ray_radii(loop, angles):
    """Distance from the origin to the convex hull of a loop of points (x, y), along each
    angle: cloth stretched round two legs spans the gap between them. When the origin
    falls outside the hull, the hull's reach in each direction stands in."""
    hull = cv2.convexHull(loop.astype(np.float32)).reshape(-1, 2).astype(float)
    directions = np.column_stack([np.cos(angles), np.sin(angles)])
    if len(hull) < 3:
        return np.full(len(angles), float(np.linalg.norm(loop, axis=1).max()))
    edges = np.roll(hull, -1, axis=0) - hull
    normals = np.column_stack([edges[:, 1], -edges[:, 0]])
    if np.sum(normals * (hull - hull.mean(axis=0))) < 0:
        normals = -normals                                   # outward, whichever way the hull winds
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    offsets = np.sum(normals * hull, axis=1)                 # edge lines: normal . p = offset
    if offsets.min() <= 1e-4:
        return np.maximum(directions @ hull.T, 0.0).max(axis=1)
    facing_out = directions @ normals.T
    reach = np.where(facing_out > 1e-9, offsets / np.maximum(facing_out, 1e-9), np.inf)
    return reach.min(axis=1)


def body_profile(marks, top, front, length, wind=None, steps=PROFILE_STEPS, angles=ANGLES):
    """The posed body below a waist point, round the skirt's own axis: heights t
    (fractions of the length) and radii[row, angle] to the melted skin, the legs spanned.
    Each height is measured round the centre the wind sways it to, so the upwind side
    may come close to the legs and the downwind side gets room."""
    up = np.array([0.0, 0.0, 1.0])
    frame = facing(up, front)
    sway, _, _ = _wind(frame.astype(np.float32), np.zeros(3) if wind is None else wind)
    surface = [Surface(marks, BODY_BELOW_WAIST)]
    theta = np.linspace(0.0, 2 * np.pi, angles, endpoint=False)     # the table's columns (Flare._fitted)
    heights = np.linspace(0.0, 1.0, steps)
    radii = []
    for t in heights:
        centre = np.asarray(top, float) - up * length * t + frame[:, :2] @ (sway * t * t)
        loop = (around(surface, centre, up, front, 0.0, samples=angles) - centre) @ frame
        radii.append(_ray_radii(loop[:, :2], theta))
    return heights, np.array(radii)


def _pressed(front, wind, angles=ANGLES):
    """Per table angle, the share of the flare the wind takes away: most straight
    upwind, none across or downwind."""
    _, strength, wind_angle = _wind(facing((0, 0, 1), front).astype(np.float32), wind)
    theta = np.linspace(0.0, 2 * np.pi, angles, endpoint=False)
    return min(strength * WIND_PRESS, 1.0) * np.clip(-np.cos(theta - wind_angle), 0.0, 1.0)


def _circular_smooth(values, passes=2):
    for _ in range(passes):
        values = (np.roll(values, 1, axis=-1) + 2 * values + np.roll(values, -1, axis=-1)) / 4
    return values


def flare_profile(body, length, flare, hip_drop, clearance=CLEARANCE, ease=WAIST_EASE, press=None,
                  rows=PROFILE_ROWS):
    """Skirt radii from the body's: on the skin at the waist, following the hips down to
    their widest line (hip_drop metres below the waist), then widening by `flare` metres
    per metre of length, never closer to the body than the clearance. The skirt only
    widens going down: it hangs over the hips, it does not tuck in under them.
    ease: room at the waist, more over a top tucked in under the skirt. press: per
    angle, the share of the flare the wind flattens (see _pressed).
    Returns heights t, the skirt's radii and the contact radii (the skirt lying on the
    body, how far a hand may push it in), each radii[row, angle]."""
    heights, radii = body
    t = np.linspace(0.0, 1.0, rows)
    fitted = np.array([np.interp(t, heights, radii[:, j]) for j in range(radii.shape[1])]).T
    ramp = np.clip(t * length / max(hip_drop, 1e-3), 0.0, 1.0)
    ramp = ramp * ramp * (3 - 2 * ramp)                      # eases from the waist to the hip line
    floor = fitted + ease + max(clearance - ease, 0.0) * ramp[:, None]
    out = floor.copy()
    step = length / (rows - 1)
    widening = flare * (1.0 - (0.0 if press is None else press))
    for i in range(1, rows):
        out[i] = np.maximum(floor[i], out[i - 1] + widening * ramp[i] * step)
    contact = fitted + max(ease, SHELL + DENT_MARGIN)
    return t, np.maximum(_circular_smooth(out), floor), contact


def flared_skirt(scene, marks, length=0.48, flare=0.30, folds=9, depth=0.014, pleats=False, wind=None,
                 colour=("#C94F5E", "#8A3550"), group="skirt", waist=WAIST, band=True, ease=WAIST_EASE):
    """A skirt hanging free from the waist. Sitting or lying, it becomes a tube skirt
    over the lap. wind: world vector, metres of hem sway (0.3 is a fresh breeze).
    ease: room at the waist; a top tucked in under the skirt needs its own thickness."""
    if _seated(marks):
        return tube_skirt(scene, marks, at=min(length / 0.42, 1.25), ease=0.016, colour=colour, group=group,
                          waist=waist)
    _, _, pelvis, p = _frames(marks)
    top = pelvis + p @ (0, 0, waist)
    front = _level_front(p)
    wind = np.zeros(3) if wind is None else np.asarray(wind, float)
    hip_drop = waist - HIP_LINE
    profile = flare_profile(body_profile(marks, top, front, length, wind), length, flare, hip_drop, ease=ease,
                            press=_pressed(front, wind))
    scene.add(Flare(top, (0, 0, 1), front, profile, length, folds, depth, pleats, wind,
                    obstacles=_arm_obstacles(marks), fold_from=hip_drop * FOLD_START), group)
    if band:                                                 # a waistband lying on the skirt's top edge
        loop = around([Surface(marks, BODY_BELOW_WAIST)], top - np.array([0, 0, 0.006]), (0, 0, 1), front,
                      ease + SHELL)
        rod(scene, group, loop, 0.006, closed=True, blend=0.004)
    return [(group, *colour)]


def _arm_obstacles(marks):
    """Points along each forearm and hand with their thickness: what a skirt must not
    swallow."""
    obstacles = []
    for name in ("left", "right"):
        elbow, wrist = marks[f"{name}_elbow"], marks[f"{name}_wrist"]
        for t, radius in ((0.5, 0.040), (1.0, 0.032), (1.35, 0.034), (1.7, 0.030)):
            obstacles.append((elbow + (wrist - elbow) * t, radius))
    return obstacles


def pleated_skirt(scene, marks, length=0.40, wind=None, colour=("#2E3550", "#1A1E33"), group="skirt",
                  ease=WAIST_EASE):
    """Knife pleats all round, short and flaring a little."""
    return flared_skirt(scene, marks, length, flare=0.22, folds=22, depth=0.009, pleats=True, wind=wind,
                        colour=colour, group=group, ease=ease)


def mini_skirt(scene, marks, wind=None, colour=("#1F1C24", "#0E0C12"), group="skirt"):
    return flared_skirt(scene, marks, length=0.30, flare=0.20, folds=7, depth=0.008, wind=wind, colour=colour,
                        group=group)


def _between_legs(marks, at):
    """Points on the line midway between the two legs' axes, from the hips to `at`
    (0 hip, 1 knee, 2 ankle), with the half gap between the axes there and the unit
    direction across, from the right leg to the left."""
    points, gaps, across = [], [], []
    for t in np.linspace(0.05, at, 8):
        pair = []
        for name in ("left", "right"):
            hip, knee, ankle = (marks[f"{name}_{j}"] for j in ("hip", "knee", "ankle"))
            pair.append(hip + (knee - hip) * t if t <= 1 else knee + (ankle - knee) * (t - 1))
        points.append((pair[0] + pair[1]) / 2)
        gaps.append(float(np.linalg.norm(pair[0] - pair[1])) / 2)
        across.append((pair[0] - pair[1]) / max(2 * gaps[-1], 1e-9))
    return np.array(points), np.array(gaps), np.array(across)


def _web(scene, group, middle, gaps, across, reach, thickness, blend=0.02):
    """Cloth stretched flat between two legs: flat ellipsoids along the midline, wide
    enough to reach each leg, thin across the plane of the legs. Round rods there
    swell into balls once the legs part (knees up, crossed legs)."""
    for (a, b), (ga, gb), side in zip(zip(middle[:-1], middle[1:]), zip(gaps[:-1], gaps[1:]), across[1:]):
        along = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        side = side - along * (side @ along)
        side /= max(np.linalg.norm(side), 1e-9)
        frame = np.column_stack([side, along, np.cross(side, along)])
        radii = (max(ga, gb) + reach, np.linalg.norm(b - a) / 2 + reach, thickness)
        scene.add(Ellipsoid((a + b) / 2, radii, frame), group, blend)


def _legs_crossed(marks):
    """True when the ankles have swapped sides: one leg crossed over the other."""
    hips = marks["left_hip"] - marks["right_hip"]
    ankles = marks["left_ankle"] - marks["right_ankle"]
    return float(hips @ ankles) < 0.0


def _knees_raised(marks):
    """True when the knees stand higher than the hips: sitting on the ground, knees up."""
    knees = (marks["left_knee"][2] + marks["right_knee"][2]) / 2
    hips = (marks["left_hip"][2] + marks["right_hip"][2]) / 2
    return float(knees - hips) > KNEE_RISE


def tube_skirt(scene, marks, at=0.95, ease=0.008, colour=("#2B2E3A", "#16181F"), group="skirt", waist=WAIST,
               band=True):
    """A skirt that follows the hips and thighs, the gap between the legs bridged:
    a pencil skirt standing, a skirt over the lap sitting. at: hem position along the
    legs, 0 hips, 1 knees, 2 ankles. Over crossed legs or raised knees the skirt rides
    up to the knees and each leg is cut on its own: the shins part widely there, and
    cloth bridged between them, or one cut across both, balloons round the knees."""
    _, _, pelvis, p = _frames(marks)
    rides_up = _legs_crossed(marks) or _knees_raised(marks)
    at = min(at, 1.0) if rides_up else at
    regions = ("pelvis", "thigh") + (("shin",) if at > 1 else ())
    dress(scene, marks, group, regions, ease, SMOOTH)
    middle, gaps, across = _between_legs(marks, at if rides_up else at + 0.05)
    thigh_radius = marks["leg_radii"][0][0]
    if rides_up:
        _web(scene, group, middle, gaps, across, thigh_radius * 0.3 + ease, thigh_radius * WEB_THICKNESS)
    else:
        for (a, b), (ga, gb) in zip(zip(middle[:-1], middle[1:]), zip(gaps[:-1], gaps[1:])):
            scene.add(Capsule(a, ga + thigh_radius * 0.3 + ease, b, gb + thigh_radius * 0.25 + ease), group, 0.02)
    hem(scene, group, pelvis + p @ (0, 0, waist), -p[:, 2])
    if rides_up:
        for name in ("left", "right"):
            cut_leg(scene, group, marks, name, at, keep_upper=True)
    else:
        ends, along = [], []
        for name in ("left", "right"):
            hip, knee, ankle = (marks[f"{name}_{j}"] for j in ("hip", "knee", "ankle"))
            start, end, t = (hip, knee, at) if at <= 1 else (knee, ankle, at - 1)
            ends.append(start + (end - start) * t)
            along.append((end - start) / np.linalg.norm(end - start))
        hem(scene, group, np.mean(ends, axis=0), -np.mean(along, axis=0))
    if band:
        loop = around(shapes_of(marks, ("pelvis", "abdomen")), pelvis + p @ (0, 0, waist - 0.006), p[:, 2],
                      -p[:, 1], ease)
        rod(scene, group, loop, 0.007, closed=True, blend=0.004)
    return [(group, *colour)]


def pencil_skirt(scene, marks, colour=("#2B2E3A", "#16181F"), group="skirt"):
    return tube_skirt(scene, marks, at=0.95, ease=0.008, colour=colour, group=group)


def _bodice(scene, marks, group, thickness, neckline, straps, waist):
    """Dress top: chest, bust and waist grown, cut straight across above the bust and
    at the waist; straps: spaghetti straps over the shoulders, else none. The hips are
    grown too and cut away: the skin's waist is the belly melted into the hips, and a
    top grown without them sinks under the skin there."""
    origin, c, pelvis, p = _frames(marks)
    dress(scene, marks, group, ("chest", "breast", "abdomen", "pelvis"), thickness, SMOOTH)
    hem(scene, group, pelvis + p @ (0, 0, waist - 0.01), p[:, 2])
    chest_marks = [c.T @ (point - origin) for point, _ in marks["chest_marks"]]
    top_z = float(np.mean([n[2] for n in chest_marks])) + neckline
    hem(scene, group, origin + c @ (0, 0, top_z), -c[:, 2])
    for name, n in zip(("right", "left"), chest_marks):
        side = 1 if name == "left" else -1
        scene.carve(Ellipsoid(marks[f"{name}_shoulder"] + c @ (side * 0.012, 0.0, -0.035), (0.058, 0.09, 0.088), c),
                    group, 0.006)
        if straps:
            path = [origin + c @ (n[0], -0.20, top_z - 0.004), origin + c @ (side * 0.090, -0.030, 0.255),
                    origin + c @ (side * 0.100, 0.020, 0.300), origin + c @ (side * 0.085, 0.080, 0.230)]
            rod(scene, group, strap([Skin(scene)], path), 0.0030, blend=0.002)
    return top_z


def sundress(scene, marks, length=0.62, wind=None, colour=("#F3D36B", "#C28F5E"), group="dress"):
    """Strappy summer dress: a fitted bodice cut straight above the bust on spaghetti
    straps, a full skirt from the waist that swings in the wind."""
    _bodice(scene, marks, group, FIT + 0.002, 0.050, straps=True, waist=DRESS_WAIST)
    items = [(group, *colour)]
    items += flared_skirt(scene, marks, length, flare=0.30, folds=8, depth=0.018, wind=wind, colour=colour,
                          group=f"{group}_skirt", waist=DRESS_WAIST)
    return items


def sheath_dress(scene, marks, colour=("#2F2A44", "#18152A"), group="dress"):
    """Fitted knee-length dress with a straight neckline above the bust, sleeveless."""
    _bodice(scene, marks, group, 0.005, 0.075, straps=False, waist=DRESS_WAIST)
    return [(group, *colour)] + tube_skirt(scene, marks, at=1.0, ease=0.006, colour=colour, group=f"{group}_skirt",
                                           waist=DRESS_WAIST, band=False)


class Ribbon:
    """A flat strip of cloth along a path: the scarf's ends. points (n, 3) along the
    middle, across (n, 3) unit vectors along the width, half width and half thickness.
    Each segment is a thin box swept along it; segments run a little past their ends
    (`overlap`) so the outer edge of a bend has no notch. Built in short pieces
    (ribbon()), each with tight bounds."""

    def __init__(self, points, across, half_width, thickness, rounding=0.0015):
        points, across = np.asarray(points, np.float32), np.asarray(across, np.float32)
        self.a, self.b = points[:-1], points[1:]
        self.wa, self.wb = across[:-1], across[1:]
        self.half_width, self.thickness, self.rounding = float(half_width), float(thickness), float(rounding)
        self.overlap = float(np.linalg.norm(self.b - self.a, axis=1).max()) / 2

    def distance(self, points):
        best = np.full(len(points), np.inf, np.float32)
        for a, b, wa, wb in zip(self.a, self.b, self.wa, self.wb):
            span = b - a
            length = float(np.linalg.norm(span))
            tangent = span / max(length, 1e-9)
            offset = points - a
            along = offset @ tangent
            u = np.clip(along / max(length, 1e-9), 0.0, 1.0)
            width = wa[None, :] * (1 - u)[:, None] + wb[None, :] * u[:, None]
            width -= (width @ tangent)[:, None] * tangent
            width /= np.maximum(np.linalg.norm(width, axis=1, keepdims=True), 1e-9)
            normal = np.cross(tangent, width)
            rel = offset - (u * length)[:, None] * tangent
            x = np.abs(np.sum(rel * width, axis=1)) - (self.half_width - self.rounding)
            y = np.abs(np.sum(rel * normal, axis=1)) - (self.thickness - self.rounding)
            z = np.maximum(np.abs(along - u * length) - self.overlap, 0.0)
            outside = np.sqrt(np.maximum(x, 0) ** 2 + np.maximum(y, 0) ** 2 + z ** 2)
            best = np.minimum(best, outside + np.minimum(np.maximum(x, y), 0.0) - self.rounding)
        return best

    def bounds(self):
        ends = np.concatenate([self.a, self.b[-1:]])
        centre = ends.mean(axis=0)
        reach = float(np.linalg.norm(ends - centre, axis=1).max())
        return centre, reach + self.half_width + self.thickness + self.overlap


def ribbon(scene, group, points, across, half_width, thickness, blend=0.0, piece=RIBBON_PIECE):
    """Add a ribbon in pieces of a few segments sharing their end points; only the first
    piece melts into what the group already holds (a knot), the rest join exactly."""
    for start in range(0, len(points) - 1, piece):
        stop = min(start + piece, len(points) - 1) + 1
        scene.add(Ribbon(points[start:stop], across[start:stop], half_width, thickness), group,
                  blend if start == 0 else 0.0)


def _neck_loop(marks, height, offset, tilt, give=0.0, samples=36):
    """Loop round the neck column `offset` out from it, lower at the front by `tilt`
    (rise over run), lifted wherever the slope of the shoulders would cut into it by
    more than `give`: a scarf wound round the neck rests on the shoulders at the sides,
    pressed into them a little, since it is soft."""
    _, c, _, _ = _frames(marks)
    front = -c[:, 1]
    axis = c[:, 2] + front * tilt
    loop = around([Surface(marks, ("neck",))], marks["neck"] + c[:, 2] * height, axis, front, offset,
                  samples=samples)
    body = Surface(marks, NECK_REST)
    for _ in range(40):
        gap = body.distance(loop) - offset + give
        if gap.min() > -1e-4:
            break
        loop = loop + c[:, 2] * np.clip(-gap, 0.0, None)[:, None]
    rise = (loop - marks["neck"]) @ c[:, 2]
    for _ in range(3):                                       # even out the lifted heights round the loop
        rise = np.maximum(rise, (np.roll(rise, 1) + 2 * rise + np.roll(rise, -1)) / 4)
    return loop + c[:, 2] * (rise - (loop - marks["neck"]) @ c[:, 2])[:, None]


def _hanging_path(marks, start, length, drift, step=SCARF_STEP, lift=SCARF_OFF_BODY):
    """A scarf end hanging from `start`: straight down along gravity, held off the body
    where the chest stands out; past the bust it keeps that distance and falls straight
    instead of tucking in under it. drift: metres it moves sideways over its length."""
    origin, c, _, _ = _frames(marks)
    up = np.array([0.0, 0.0, 1.0])
    front = _level_front(c)
    side = np.cross(up, front)
    trunk = [Surface(marks, ("chest", "breast", "abdomen", "neck"))]

    def ahead(point):                                        # how far in front of the chest centre
        return float((point - origin) @ front)

    count = max(int(length / step), 2)
    path, forward = [], ahead(start)
    for s in np.linspace(0.0, 1.0, count + 1):
        point = start - up * length * s + side * drift * s
        # Walk in from the front toward a point behind the trunk's front: the first
        # surface met is the chest (or the belly) at this height.
        surface = around(trunk, point - front * SCARF_PROBE, side, front, lift, arc=(0.0, 0.0), samples=1)[0]
        forward = max(forward, ahead(surface))
        path.append(point + front * (forward - ahead(point)))
    path = np.array(path)
    return path, np.repeat(side[None, :], len(path), axis=0)


def _streaming_path(start, wind, length, phase, droop=0.0, step=SCARF_STEP):
    """A scarf end streaming downwind from `start`, falling where the wind is light, and
    waving like a flag: its width stands upright and it ripples sideways, more toward
    the free end. droop: extra fall (rise over run), so two ends do not lie as one."""
    strength = float(np.linalg.norm(wind))
    towards = np.asarray(wind, float) / strength
    up = np.array([0.0, 0.0, 1.0])
    flat = towards - up * (towards @ up)
    flat /= max(np.linalg.norm(flat), 1e-9)
    lateral = np.cross(up, flat)
    heading = flat * min(1.0, strength * 2) - up * (max(0.25, 1.0 - strength * 2) + droop)
    heading /= np.linalg.norm(heading)
    count = max(int(length / step), 2)
    s = np.linspace(0.0, 1.0, count + 1)[:, None]
    sag = -up * SCARF_SAG * length * s ** 2                   # the free end droops a little
    wave = lateral * SCARF_FLUTTER * length * s * np.sin(2 * np.pi * SCARF_WAVES * s - phase)
    path = start + heading * length * s + sag + wave
    tangent = np.gradient(path, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    across = up - tangent * (tangent @ up)[:, None]
    across /= np.linalg.norm(across, axis=1, keepdims=True)
    twist = SCARF_TWIST * s[:, 0] * np.sin(2 * np.pi * SCARF_WAVES * s[:, 0] - phase + 1.0)
    across = across * np.cos(twist)[:, None] + np.cross(tangent, across) * np.sin(twist)[:, None]
    return path, across


def scarf(scene, marks, wind=None, length=0.65, width=0.065, colour=("#E85A71", "#A33A5A"), group="scarf"):
    """A long scarf wound twice round the neck, knotted at the front, both ends hanging
    from the knot. Without wind they fall down the chest; in wind they stream downwind
    and wave. width: of the cloth, metres."""
    _, c, _, _ = _frames(marks)
    front = -c[:, 1]
    roll = width * 0.28                                        # a wound turn is a soft roll this thick
    turns = [_neck_loop(marks, height, offset + roll, tilt, give=roll * SCARF_SQUASH)
             for height, offset, tilt in SCARF_TURNS]
    for loop in turns:
        rod(scene, group, loop, roll, closed=True, blend=0.004)
    first = turns[0]
    toward_knot = front * np.cos(np.radians(SCARF_KNOT_ANGLE)) + c[:, 0] * np.sin(np.radians(SCARF_KNOT_ANGLE))
    knot = first[np.argmax(first @ toward_knot)] + front * roll * 0.6 - c[:, 2] * roll * 0.5
    scene.add(Ellipsoid(knot, (roll * 1.5, roll * 1.1, roll * 1.3), c), group, 0.008)
    wind = np.zeros(3) if wind is None else np.asarray(wind, float)
    calm = float(np.linalg.norm(wind)) < 0.05
    for share, drift, phase, droop in SCARF_ENDS:
        if calm:
            path, across = _hanging_path(marks, knot - c[:, 2] * roll, length * share, drift)
        else:
            path, across = _streaming_path(knot, wind, length * share, phase, droop)
        ribbon(scene, group, path, across, width / 2, SCARF_THICKNESS, blend=0.008)
    return [(group, *colour)]


__all__ = ["CLEARANCE", "Flare", "Ribbon", "body_profile", "flare_profile", "flared_skirt", "mini_skirt", "pencil_skirt",
           "pleated_skirt", "scarf", "sheath_dress", "sundress", "tube_skirt"]
