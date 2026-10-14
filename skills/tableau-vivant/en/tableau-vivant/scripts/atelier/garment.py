"""Garments built from the body model's clothing helper shells.

The base mesh ships two skinned helper surfaces: a full bodysuit ("tights") and a long skirt.
Both already follow every pose and body shape, so a garment is a *cut* of a helper
(which region to keep), an *ease* (how far it stands off the skin) and *folds*.
All cuts are expressed in template space (default adult, metres, pelvis origin):

    z: 0.805 chin   0.72 neck base   0.66 shoulder   0.58 armpit   0.52 bust   0.46 underbust
       0.36 waist   0.14 hip   0.06 crotch   -0.28 knee   -0.74 ankle   -0.82 sole
"""
import numpy as np

from scipy.spatial import cKDTree

from .mesh import Mesh, subdivide, cut_by_margin
from .figure import _base_obj_groups, BODY_RANGE
from .noise import rng

SHOULDER = np.array([0.175, -0.023, 0.639])
ARM_AXIS = np.array([0.675, -0.038, -0.737])
ARM_MIN_X, ARM_MIN_Z = 0.19, 0.20
SKIRT_TOP_Z = 0.296
SLEEVES = {"none": None, "cap": 0.07, "short": 0.17, "elbow": 0.29, "three_quarter": 0.40, "long": 0.56}
HEMS = {"micro": -0.02, "mini": -0.10, "above_knee": -0.20, "knee": -0.30, "midi": -0.46, "ankle": -0.68, "floor": -0.80}
def _brief_line(x, y, z):
    """High-cut leg opening: rises from the crotch toward the hip bone."""
    return 0.045 + 0.95 * np.abs(x)


def _low_brief_line(x, y, z):
    """Men's brief: a lower, straighter leg opening."""
    return 0.02 + 0.45 * np.abs(x)


LEG_HEMS = {"brief": _brief_line, "low_brief": _low_brief_line, "short": -0.04, "bermuda": -0.22, "capri": -0.48, "full": -0.76, "footed": -1.0}
NECK_Z = 0.715
OPEN_COLLAR = (0.10, 0.055)      # depth and half width of a shirt's open neck (top button undone)
COLLAR_TOP_Z = 0.755            # a shirt collar stands this high up the neck
HOOD_TOP_Z, HOOD_OPENING, HOOD_FRONT_Z = 0.785, 0.05, 0.665   # a lowered hood: top edge, half width of the face gap
HOOD_BOTTOM_Z, HOOD_PEAK_Z, HOOD_HALF_WIDTH, HOOD_BULK = 0.54, 0.72, 0.15, 0.05
CORD_X, CORD_HALF_WIDTH, CORD_TOP_Z, CORD_LENGTH = 0.038, 0.0045, 0.700, 0.17
POCKET_HALF_WIDTH, POCKET_FRONT_Y = 0.13, 0.03
HANG_START_DEG, HANG_RANGE_DEG = 25.0, 30.0   # thighs raised beyond this start to let a skirt fall from the knee
HAND_MIN_X = 0.44               # template |x| beyond which a body vertex belongs to a hand (wrist included)
PRESS_REACH = 0.06              # cloth farther than this from every hand point is left alone
PRESS_LINE_RADIUS = 0.012       # a hand point this close to the line from the skin through a cloth point lies on it
PRESS_GAP = 0.003               # pressed cloth sits this far under the hand
PRESS_LAYER_STEP = 0.0015       # pressed layers keep this spacing, inner under outer
PRESS_MIN_OFFSET = 0.006        # pressed cloth never comes closer to the skin than this (closer, the skin pokes through)
PRESS_SLOPE = 1.2               # dent around the hand: metres of falloff per metre of depth
PRESS_SPREAD_PASSES = 4         # mesh rings over which a dent spreads past the hand outline
TUCK_STEPS = (0.01, 0.02, 0.03, 0.045, 0.06, 0.08)   # distances out from a hand searched for an arm over it
TUCK_RADIUS = 0.02              # an arm this close to one of those points covers the hand
TUCKED_SHARE = 0.25             # a hand this much covered by the other arm is tucked under it as a whole
KNEE_BLEND = 0.06               # length (m) over which the fall bends round the knee
SIDE_BLEND = 0.04               # width (m) over which the skirt passes from following one leg to the other
FRONT_OPENING_HALF_WIDTH = 0.012   # half the gap (m) down the front of an open skirt, between the two edges
FRONT_OPENING_SEATED = 0.05     # extra half gap (m) when seated: the cloth between the knees falls away
FLOOR_CLEARANCE = 0.004
SHELL_SMOOTHING = 8             # passes that even out the fitted shell's correction
SHELL_GAP = 0.006               # how far the fitted bodysuit shell sits off the skin before any ease
SNUG_EASE = 0.004               # ease a top keeps even where it fits closest
SHOULDER_SEAM_Z, HANG_DROP = 0.68, 0.22   # tops fit at the shoulder seam and reach full looseness this far below
SLEEVE_HANG = 0.22              # distance down the arm over which a sleeve loosens from its cap
HANG_FIT = 0.25                 # share of the extra ease kept at the seam and the sleeve cap
LOOSE_EASE, TOP_DRAPE, TOP_DRAPE_FLOOR = 0.008, 10, 0.5   # tops this loose settle by default (passes, floor share)
SETTLE_FROM_Z, SETTLE_BLEND = 0.50, 0.08   # template height above which a top may settle below its ease
EDGE_KEEP = 0.02                # metres from a cut edge (neckline, armhole) where the full ease is kept
SETTLE_MIN = 0.006              # a settling top stays at least this far off the skin
REST_ON_TOP, REST_POWER = 0.8, 1.5   # share of the ease taken out where the shell faces straight up
DRAPE_STEP = 0.6                # share of the way each relaxing pass moves a vertex toward its neighbours
DRAPE_FLOOR = 1.0               # draped cloth bridges hollows but never sinks below its ease (inner layers stay covered)
TIE_KNOT_Z, TIE_TIP_Z, TIE_FRONT_Y = 0.705, 0.36, -0.05
LAPEL_WIDTH, LAPEL_FRONT_Y, LAPEL_BOTTOM_Z = 0.05, -0.04, 0.40
LAPEL_HALF_SPAN, LAPEL_TOP_Z = 0.11, 0.70
LAPEL_GAP, LAPEL_TAPER = 0.006, 0.09
LAPEL_SUBDIVISIONS = 2
TIE_KNOT_HALF_WIDTH, TIE_BLADE_HALF_WIDTH, TIE_POINT_LENGTH = 0.011, 0.030, 0.035
# gathers at bent joints (template heights and distances, metres)
ELBOW_ALONG = 0.29              # shoulder to elbow along the arm axis
KNEE_Z, ANKLE_BREAK_Z, CROTCH_Z = -0.28, -0.70, 0.06
LEG_CENTRE_X = 0.09
BUNCH_WAVELENGTH = 0.045        # spacing of gathered ridges
BUNCH_SPREAD = 0.07             # how far along the limb the gathers reach
BUNCH_SLANT = 1.2               # ridges spiral a little round the limb instead of forming flat rings
BUNCH_EASE_RANGE = (0.003, 0.02)   # loose cloth gathers more than tight cloth
BUNCH_PER_EASE = 0.8


def _neckline_margin(kind, x, y, z):
    """Signed distance-like margin (m): > 0 where cloth exists for a neckline style."""
    ax = np.abs(x)
    front = y < 0.0
    if kind == "turtle":
        return np.full_like(z, 1.0)
    if kind == "crew":
        return NECK_Z - 0.035 * np.clip(1 - ax / 0.06, 0, 1) * front - z
    if kind == "hood":              # a hood lying down: over the upper back and round the sides of the neck
        return np.minimum(HOOD_TOP_Z - z, np.where(front, np.minimum(ax - HOOD_OPENING, z - HOOD_FRONT_Z), 1.0))
    if kind == "pocket":            # a kangaroo pocket: a panel across the front of the belly
        return np.minimum(POCKET_HALF_WIDTH - ax, -y - POCKET_FRONT_Y)
    if kind == "collar_stand":      # a shirt collar's band: up the sides and back of the neck, open in front
        return np.minimum(COLLAR_TOP_Z - z, np.where(front, ax - OPEN_COLLAR[1], 1.0))
    if kind == "boat":
        return 0.672 - z
    if kind in ("v", "deep_v", "open_collar"):
        depth, half_width = {"v": (0.17, 0.075), "deep_v": (0.27, 0.085), "open_collar": OPEN_COLLAR}[kind]
        return np.where(front, NECK_Z - depth * np.clip(1 - ax / half_width, 0, 1), NECK_Z) - z
    if kind == "scoop":
        depth = 0.13 * np.sqrt(np.clip(1 - (ax / 0.095) ** 2, 0, 1))
        return np.where(front, NECK_Z - depth, NECK_Z - depth * 0.35) - z
    if kind == "square":
        return np.maximum(0.605 - z, ax - 0.085)
    if kind == "straps":            # camisole: straight edge above the bust plus two straps
        return np.maximum(0.585 - z, np.minimum(ax - 0.070, 0.098 - ax))
    if kind == "halter":
        return np.maximum(0.585 - z, np.where(front, 0.03 + (NECK_Z - z) * 0.55 - ax, -1.0))
    if kind == "strapless":
        return 0.575 - z
    if kind == "one_shoulder":
        return 0.60 + np.clip(x + 0.02, 0, 1) * 1.1 - z
    raise KeyError(f"unknown neckline '{kind}'")


def _fold_field(theta, drop, count, seed, sharp=1.0):
    """Vertical folds: 0..1 ridges around the body (theta) that deepen downward (drop 0..1)."""
    generator = rng(seed, 211)
    total = np.zeros_like(theta)
    for k, weight in ((count, 1.0), (count * 2 + 1, 0.35), (max(count // 2, 1), 0.5)):
        total += weight * np.sin(k * theta + generator.uniform(0, 2 * np.pi) + drop * generator.uniform(-1.5, 1.5))
    ridge = 0.5 + 0.5 * total / 1.85
    return np.clip(ridge, 0, 1) ** sharp


def _flex_deg(figure, upper, lower, end):
    """How far a joint is bent (0 = straight), from the posed bone positions."""
    a, b, c = (figure.bone_position(name) for name in (upper, lower, end))
    u, v = b - a, c - b
    return float(np.degrees(np.arccos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9), -1, 1))))


def _bunching(along, around, centre, depth, phase):
    """Ring-shaped ridges where cloth gathers at a bent joint, slanting around the limb and fading away from it."""
    ridge = 0.5 + 0.5 * np.sin(2 * np.pi * (along - centre) / BUNCH_WAVELENGTH + BUNCH_SLANT * np.sin(around) + phase)
    return depth * ridge * np.exp(-((along - centre) / BUNCH_SPREAD) ** 2)


def _joint_folds(figure, x, y, z, along_arm, is_arm, ease, seed):
    """Extra stand-off (m) for gathers at the elbows and knees, deeper the more each joint is bent."""
    generator = rng(seed, 223)
    looseness = np.clip(ease, BUNCH_EASE_RANGE[0], BUNCH_EASE_RANGE[1]) * BUNCH_PER_EASE
    offset = np.zeros_like(z)
    arm_perp = np.cross(ARM_AXIS, [0.0, 1.0, 0.0])
    for side, sign in (("L", 1.0), ("R", -1.0)):
        on_side = np.sign(x) == sign
        bend = 0.3 + _flex_deg(figure, f"upperarm01.{side}", f"lowerarm01.{side}", f"wrist.{side}") / 90.0
        around = np.arctan2(y - SHOULDER[1], (np.stack([np.abs(x), y, z], 1) - SHOULDER) @ arm_perp)
        offset += np.where(is_arm & on_side, _bunching(along_arm, around, ELBOW_ALONG, looseness * bend, generator.uniform(0, 6.3)), 0)
        bend = 0.3 + _flex_deg(figure, f"upperleg01.{side}", f"lowerleg01.{side}", f"foot.{side}") / 90.0
        leg = ~is_arm & on_side & (z < CROTCH_Z)
        around = np.arctan2(x - sign * LEG_CENTRE_X, y)
        offset += np.where(leg, _bunching(z, around, KNEE_Z, looseness * bend, generator.uniform(0, 6.3)), 0)
        offset += np.where(leg, _bunching(z, around, ANKLE_BREAK_Z, looseness * 0.6, generator.uniform(0, 6.3)), 0)
    return offset


def _shell(figure, helper):
    faces = _base_obj_groups()[helper]
    return Mesh(figure.vertices, faces, "cloth", "cloth", None, {"tpl": figure.rest_attr["tpl"]})


def _tights_shell(figure, subdivisions=1):
    """The bodysuit helper, subdivided and brought down onto the skin (cached per figure and level).

    The helper floats 1-2.5 cm off the body, most over the shoulders of a muscular build; left as it is,
    every garment's ease comes on top of that and broad shoulders look padded. Each vertex is moved in
    along the skin normal until it sits SHELL_GAP off the skin, so ease alone sets how loose a garment is."""
    cache = figure.__dict__.setdefault("_tights_cache", {})
    if subdivisions in cache:
        return cache[subdivisions]
    from scipy.spatial import cKDTree
    from .figure import BODY_RANGE
    mesh = subdivide(_shell(figure, "helper-tights"), subdivisions)
    # the skin as rendered (subdivided once): the base mesh is too coarse over the shoulders to measure against
    body_faces = figure.faces[(figure.faces < BODY_RANGE[1]).all(1)]
    skin = subdivide(Mesh(figure.vertices, body_faces), 1)
    used = np.unique(skin.faces)
    body, body_normals = skin.vertices[used], skin.vertex_normals()[used]
    _, nearest = cKDTree(body).query(mesh.vertices)
    gap = np.sum((mesh.vertices - body[nearest]) * body_normals[nearest], 1)
    # the nearest-vertex measure jumps from vertex to vertex: smooth the correction over the shell and move along
    # the shell's own (smooth) normals, or every cut edge on the fitted shell would come out wavy
    correction = _smooth_scalar(np.clip(gap - SHELL_GAP, 0, None), mesh.faces, SHELL_SMOOTHING)
    fitted = mesh.vertices - mesh.vertex_normals() * correction[:, None]
    mesh = Mesh(fitted, mesh.faces, mesh.material, mesh.part, None, dict(mesh.vertex_attr))
    cache[subdivisions] = mesh
    return mesh


def _hanging_ease(x, z, along_arm, is_arm, ease):
    """Ease per vertex for a top: a garment hangs from the shoulders, so it fits there and loosens below.

    The body sits close at the shoulder seam and the sleeve cap; the room shows lower down the torso and
    the sleeve. Spreading the same ease everywhere is what makes loose shirts on broad shoulders look padded."""
    loose = np.clip(ease - SNUG_EASE, 0, None)
    torso = np.clip((SHOULDER_SEAM_Z - z) / HANG_DROP, 0, 1)
    sleeve = np.clip(along_arm / SLEEVE_HANG, 0, 1)
    fall = np.where(is_arm, sleeve, torso)
    return np.minimum(ease, SNUG_EASE) + loose * (HANG_FIT + (1 - HANG_FIT) * fall)


def _resting(normals, offset):
    """Cloth lies on surfaces that face up (the tops of the shoulders, a seated lap) instead of standing off them.

    Ease is room around the body, and gravity takes it out of the top: a loose shirt touches the shoulders
    and hangs away below them. Without this the ease rings every bump, so broad shoulders look padded."""
    up = np.clip(normals[:, 2], 0, 1) ** REST_POWER
    return offset * (1 - REST_ON_TOP * up)


def _smooth_scalar(values, faces, passes):
    """Average a per-vertex value with its neighbours `passes` times."""
    from scipy.sparse import coo_matrix, diags
    n = len(values)
    rows = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2], faces[:, 1], faces[:, 2], faces[:, 0]])
    cols = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0], faces[:, 0], faces[:, 1], faces[:, 2]])
    adjacency = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
    adjacency.data[:] = 1.0
    average = diags(1.0 / np.maximum(np.asarray(adjacency.sum(1)).ravel(), 1)) @ adjacency
    out = np.asarray(values, float)
    for _ in range(passes):
        out = 0.5 * out + 0.5 * (average @ out)
    return out


def _cut_draped(vertices, displacement, tpl, faces, margin, material, part=None):
    """Cut on the undraped shell, then apply the drape displacement.

    Relaxing slides vertices sideways; cutting after that turns a clean neckline into a zigzag. Cut first and
    the edge follows the pattern line, carried by the (smooth) displacement onto the draped surface."""
    vertices, attrs, faces = cut_by_margin(vertices, {"tpl": tpl, "drape": displacement}, faces, margin)
    vertices = vertices + attrs.pop("drape")
    return Mesh(vertices, faces, material, part or material, None, attrs)


def _drape(vertices, faces, base, normals, iterations, floor):
    """Relax a garment shell so it bridges hollows and rounds off muscle detail, the way stiff cloth does.

    Each pass moves every vertex toward the average of its neighbours, then keeps it at least `floor`
    metres off the body along the body normal (base = the skin-hugging position)."""
    from scipy.sparse import coo_matrix, diags
    n = len(vertices)
    rows = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2], faces[:, 1], faces[:, 2], faces[:, 0]])
    cols = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0], faces[:, 0], faces[:, 1], faces[:, 2]])
    adjacency = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
    adjacency.data[:] = 1.0
    average = diags(1.0 / np.maximum(np.asarray(adjacency.sum(1)).ravel(), 1)) @ adjacency
    out = vertices.copy()
    for _ in range(iterations):
        out = out * (1 - DRAPE_STEP) + (average @ out) * DRAPE_STEP
        lift = np.sum((out - base) * normals, 1)
        out = out + normals * np.maximum(floor - lift, 0)[:, None]
    # keep only the change in stand-off: relaxing also slides vertices along the surface, unevenly on an
    # irregular mesh, and that sliding shows up as ripples along every cut edge
    return vertices + normals * np.sum((out - vertices) * normals, 1)[:, None]


def tights_part(figure, material, top=0.80, bottom=-1.0, sleeve="none", neckline="turtle", ease=0.004,
                folds=0.0, fold_count=9, seed=7, subdivisions=1, part=None, drape=0, drape_floor=None):
    """A cut of the bodysuit helper. top/bottom are template heights; sleeve is a key of SLEEVES.

    drape: smoothing passes for stiffer cloth (jackets, coats): it stops following every muscle."""
    mesh = _tights_shell(figure, subdivisions)
    tpl = mesh.vertex_attr["tpl"]
    x, y, z = tpl[:, 0], tpl[:, 1], tpl[:, 2]
    is_arm = (np.abs(x) > ARM_MIN_X) & (z > ARM_MIN_Z)
    along_arm = (np.stack([np.abs(x), y, z], 1) - SHOULDER) @ ARM_AXIS
    sleeve_len = SLEEVES[sleeve]
    low = bottom if not callable(bottom) else bottom(x, y, z)
    body_margin = np.minimum(np.minimum(top - z, z - low), _neckline_margin(neckline, x, y, z))
    if sleeve_len is None:
        # sleeveless: one smooth armhole surface for torso and arm vertices alike (tight at the shoulder, wider below the armpit)
        opening = 0.138 + 0.037 * np.clip((0.585 - z) / 0.055, 0, 1)
        armhole = np.where(z > 0.45, opening - np.abs(x), 1.0)
        body_margin = np.minimum(body_margin, armhole)
        arm_margin = opening - np.abs(x)          # always negative on the arm itself: no sleeve at all
    else:
        arm_margin = np.minimum(sleeve_len - along_arm, top - 0.60)   # sleeves need the shoulder to be covered
    margin = np.where(is_arm, arm_margin, body_margin)
    normals = mesh.vertex_normals()
    offset = _hanging_ease(x, z, along_arm, is_arm, ease)
    if folds:
        theta = np.arctan2(x, -y)
        drop = np.clip((0.60 - z) / 0.6, 0, 1)
        offset = offset + folds * _fold_field(theta, drop, fold_count, seed) * np.where(is_arm, 0.6, 1.0)
    offset = offset + _joint_folds(figure, x, y, z, along_arm, is_arm, ease, seed)
    offset = _resting(normals, offset)
    vertices = mesh.vertices + normals * offset[:, None]
    if drape:
        # cloth may settle below its ease only over the shoulders and upper chest (the bumps that make a top look
        # padded); lower down other layers meet it, and next to a cut edge the skin would show through
        settle = 1.0 - (DRAPE_FLOOR if drape_floor is None else drape_floor)
        zone = np.clip((z - SETTLE_FROM_Z) / SETTLE_BLEND, 0, 1) * np.clip(margin / EDGE_KEEP, 0, 1)
        floor = np.maximum(offset * (1 - settle * zone), np.minimum(offset, SETTLE_MIN))
        draped = _drape(vertices, mesh.faces, mesh.vertices, normals, drape, floor)
        # a settling top moves only in its zone, so lower down it keeps its place under other layers
        keep = zone if settle > 0 else np.ones_like(zone)
        return _cut_draped(vertices, (draped - vertices) * keep[:, None], tpl, mesh.faces, margin, material, part)
    vertices, attrs, faces = cut_by_margin(vertices, {"tpl": tpl}, mesh.faces, margin)
    return Mesh(vertices, faces, material, part or material, None, attrs)


def _rotate(vectors, axis, angles):
    """Rotate each row of `vectors` about the unit `axis` by its own angle (radians)."""
    cos, sin = np.cos(angles)[:, None], np.sin(angles)[:, None]
    return vectors * cos + np.cross(axis, vectors) * sin + np.outer(vectors @ axis, axis) * (1 - cos)


def _thigh_raise(figure, side):
    """Hip, knee, unit thigh direction, thigh length, angle from plumb (rad) and how raised it counts (0..1)."""
    hip, knee = figure.bone_head(f"upperleg01.{side}"), figure.bone_head(f"lowerleg01.{side}")
    thigh = knee - hip
    length = np.linalg.norm(thigh)
    u = thigh / length
    theta = np.arccos(np.clip(-u[2], -1, 1))
    return hip, knee, u, length, theta, np.clip((np.degrees(theta) - HANG_START_DEG) / HANG_RANGE_DEG, 0, 1)


def _raised_share(figure, template_x):
    """Per skirt vertex 0..1: how raised the thigh under it is (0 standing, 1 seated), each half following its leg."""
    share = np.zeros(len(template_x))
    for side, sign in (("L", 1.0), ("R", -1.0)):
        share += np.clip(0.5 + sign * template_x / SIDE_BLEND, 0, 1) * _thigh_raise(figure, side)[-1]
    return share


def _hang_from_knees(figure, vertices, template_x):
    """Let a skirt fall from the knees when the thighs are raised (sitting, kneeling on the heels).

    The skirt shell is skinned to the thighs, so on a seated figure it would stick out level past the
    knees. Cloth beyond each knee is swung down about the knee until it hangs plumb, then rests on the floor."""
    from .figure import BODY_RANGE
    down = np.array([0.0, 0.0, -1.0])
    out = vertices.copy()
    for side, sign in (("L", 1.0), ("R", -1.0)):
        hip, knee, u, length, theta, raised = _thigh_raise(figure, side)
        swing = theta * raised
        if swing < 1e-3:
            continue
        axis = np.cross(u, down)
        axis /= np.linalg.norm(axis) + 1e-12
        along = (vertices - hip) @ u
        bend = np.clip((along - (length - KNEE_BLEND)) / (2 * KNEE_BLEND), 0, 1)
        bend = bend * bend * (3 - 2 * bend)
        swung = knee + _rotate(vertices - knee, axis, swing * bend)
        weight = np.clip(0.5 + sign * template_x / SIDE_BLEND, 0, 1)[:, None]      # each half of the skirt follows its leg
        out += weight * (swung - vertices)
    floor = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1], 2].min() + FLOOR_CLEARANCE
    out[:, 2] = np.maximum(out[:, 2], floor)
    return out


def skirt_part(figure, material, hem="knee", flare=0.0, folds=0.012, fold_count=12, ease=0.004, seed=7,
               subdivisions=2, part=None, wind=0.0, hem_slant=0.0, top=None, front_opening=None):
    """A cut of the skirt helper. flare = extra radius at the hem (m); folds = fold depth (m).

    hem_slant: rise of the hem per metre toward the figure's left (a wrapped drape knotted at one hip).
    top: template height of the upper edge when the garment sits lower than the waist.
    front_opening: template height up to which the skirt is open down the centre front (a coat). Seated, the
    two halves part over the thighs instead of closing over the lap like a sack."""
    mesh = subdivide(_shell(figure, "helper-skirt"), subdivisions)
    tpl = mesh.vertex_attr["tpl"]
    x, y, z = tpl[:, 0], tpl[:, 1], tpl[:, 2]
    hem_z = HEMS[hem] if isinstance(hem, str) else float(hem)
    drop = np.clip((SKIRT_TOP_Z - z) / (SKIRT_TOP_Z - hem_z), 0, 1)
    theta = np.arctan2(x, -y)
    ridge = _fold_field(theta, drop, fold_count, seed)
    offset = ease + flare * drop ** 1.3 + folds * drop ** 0.7 * ridge * (1 + 3 * flare)
    normals = mesh.vertex_normals()
    # fullness beyond the ease cannot stand up against gravity: where the shell faces upward (over raised
    # thighs) the extra cloth lies flat instead of billowing. Over a raised thigh it cannot stand out sideways
    # either (that makes a balloon round the lap): there it only hangs down
    raised = _raised_share(figure, x)
    fall = normals.copy()
    fall[:, 2] = np.minimum(fall[:, 2], 0.0)
    fall[:, :2] *= (1 - raised)[:, None]
    vertices = mesh.vertices + normals * ease + fall * (offset - ease)[:, None]
    if wind:
        vertices = vertices + np.array([wind, 0, 0]) * (drop ** 2)[:, None] * 0.25
    vertices = _hang_from_knees(figure, vertices, x)
    margin = z - (hem_z + hem_slant * x)
    if top is not None:
        margin = np.minimum(margin, top - z)
    if front_opening is not None:
        half_width = FRONT_OPENING_HALF_WIDTH + FRONT_OPENING_SEATED * raised    # seated, the halves part over the thighs
        opening = np.maximum(np.abs(x) - half_width, z - front_opening)
        margin = np.where(y < 0, np.minimum(margin, opening), margin)
    vertices, attrs, faces = cut_by_margin(vertices, {"tpl": tpl}, mesh.faces, margin)
    return Mesh(vertices, faces, material, part or material, None, attrs)


# -------------------------------------------------------------------------------------------
# Garment catalogue. Each entry builds one garment; 'layer' orders eases so outer wear clears inner wear.
def _top(figure, material, o):
    ease, sleeve = o.get("ease", 0.005), o.get("sleeve", "short")
    if "drape" in o:
        drape, floor = o["drape"], o.get("drape_floor")
    elif ease >= LOOSE_EASE and sleeve != "none":         # loose sleeved tops settle over the shoulders by default
        drape, floor = TOP_DRAPE, o.get("drape_floor", TOP_DRAPE_FLOOR)
    else:
        drape, floor = 0, None
    return [tights_part(figure, material, top=o.get("top", 0.80), bottom=o.get("bottom", 0.20),
                        sleeve=sleeve, neckline=o.get("neckline", "crew"),
                        ease=ease, folds=o.get("folds", 0.0), seed=o.get("seed", 7), drape=drape, drape_floor=floor)]


def _bottom(figure, material, o):
    return [tights_part(figure, material, top=o.get("top", 0.33), bottom=LEG_HEMS[o.get("length", "full")],
                        ease=o.get("ease", 0.006), folds=o.get("folds", 0.0), seed=o.get("seed", 7))]


def _skirt(figure, material, o):
    waist = o.get("waist", 0.36)
    parts = [skirt_part(figure, material, hem=o.get("length", "knee"), flare=o.get("flare", 0.03),
                        folds=o.get("folds", 0.012), fold_count=o.get("fold_count", 12),
                        seed=o.get("seed", 7), wind=o.get("wind", 0.0), hem_slant=o.get("hem_slant", 0.0),
                        top=waist if waist < SKIRT_TOP_Z else None)]
    if waist > SKIRT_TOP_Z:            # waistband / high waist: borrow a band of the bodysuit
        parts.append(tights_part(figure, material, top=waist, bottom=SKIRT_TOP_Z - 0.03, ease=0.0075))
    return parts


def _dress(figure, material, o):
    bodice = tights_part(figure, material, top=0.80, bottom=SKIRT_TOP_Z - 0.03, sleeve=o.get("sleeve", "none"),
                         neckline=o.get("neckline", "scoop"), ease=o.get("ease", 0.0065),
                         folds=o.get("bodice_folds", 0.0), seed=o.get("seed", 7))
    # skirt_ease: a loose bodice (a coat) needs its skirt as loose, or a step shows at the waist
    skirt_options = {"ease": o["skirt_ease"]} if "skirt_ease" in o else {}
    if "front_opening" in o:
        skirt_options["front_opening"] = o["front_opening"]
    skirt = skirt_part(figure, material, hem=o.get("length", "knee"), flare=o.get("flare", 0.05),
                       folds=o.get("folds", 0.014), fold_count=o.get("fold_count", 12),
                       seed=o.get("seed", 7), wind=o.get("wind", 0.0), **skirt_options)
    return [bodice, skirt]


def _band(figure, material, o):
    return [tights_part(figure, material, top=o.get("top", 0.40), bottom=o.get("bottom", 0.33), ease=o.get("ease", 0.011),
                        neckline=o.get("neckline", "turtle"))]


def _footwear(figure, material, o):
    top = {"shoes": -0.755, "ankle_boots": -0.66, "boots": -0.36, "socks": -0.62, "stockings": -0.05}[o.get("style", "shoes")]
    return [tights_part(figure, material, top=top, bottom=-1.0, ease=o.get("ease", 0.006))]


def _lapel(figure, material, o):
    """Lapels: the band of a jacket along its V opening, folded back over the jacket's front.

    Built as the jacket's own surface (same ease, same drape) lifted by LAPEL_GAP, so the two never cross."""
    mesh = _tights_shell(figure, LAPEL_SUBDIVISIONS)      # a narrow band: finer mesh for a clean cut
    tpl = mesh.vertex_attr["tpl"]
    x, y, z = tpl[:, 0], tpl[:, 1], tpl[:, 2]
    bottom = o.get("bottom", LAPEL_BOTTOM_Z)
    opening = _neckline_margin(o.get("neckline", "deep_v"), x, y, z)
    width = o.get("width", LAPEL_WIDTH) * np.clip((z - bottom) / LAPEL_TAPER, 0, 1)   # the lapel ends in a point
    band = np.minimum(opening, width - opening)
    # only along the V: the strip beside the neck and over the shoulders stays plain jacket
    beside_v = np.minimum(LAPEL_HALF_SPAN - np.abs(x), LAPEL_TOP_Z - z)
    margin = np.where(y < LAPEL_FRONT_Y, np.minimum(np.minimum(band, z - bottom), beside_v), -1.0)
    normals = mesh.vertex_normals()
    is_arm = (np.abs(x) > ARM_MIN_X) & (z > ARM_MIN_Z)
    along_arm = (np.stack([np.abs(x), y, z], 1) - SHOULDER) @ ARM_AXIS
    jacket = _resting(normals, _hanging_ease(x, z, along_arm, is_arm, o.get("over_ease", 0.022)))   # the jacket's own surface
    vertices = mesh.vertices + normals * jacket[:, None]
    displacement = np.zeros_like(vertices)
    if o.get("drape"):                # relaxed exactly as the jacket is
        displacement = _drape(vertices, mesh.faces, mesh.vertices, normals, o["drape"], jacket * DRAPE_FLOOR) - vertices
    vertices = vertices + normals * o.get("gap", LAPEL_GAP)
    return [_cut_draped(vertices, displacement, tpl, mesh.faces, margin, material)]


def _tie(figure, material, o):
    """A necktie: a strip down the shirt front, narrow at the knot, widening to a pointed tip."""
    mesh = _tights_shell(figure, 1)
    tpl = mesh.vertex_attr["tpl"]
    x, y, z = np.abs(tpl[:, 0]), tpl[:, 1], tpl[:, 2]
    tip = o.get("tip", TIE_TIP_Z)
    width = TIE_KNOT_HALF_WIDTH + (TIE_BLADE_HALF_WIDTH - TIE_KNOT_HALF_WIDTH) * np.clip((TIE_KNOT_Z - z) / (TIE_KNOT_Z - tip), 0, 1)
    width = width * np.clip((z - tip) / TIE_POINT_LENGTH, 0, 1)            # the pointed end
    margin = np.where(y < TIE_FRONT_Y, np.minimum(np.minimum(width - x, TIE_KNOT_Z - z), z - tip + 0.001), -1.0)
    vertices = mesh.vertices + mesh.vertex_normals() * o.get("ease", 0.012)
    vertices, attrs, faces = cut_by_margin(vertices, {"tpl": tpl}, mesh.faces, margin)
    return [Mesh(vertices, faces, material, material, None, attrs)]


def _hood(figure, material, o):
    """A hood lying down: a soft roll behind the neck, thickest at the nape, thinning down the upper back."""
    mesh = _tights_shell(figure, 1)
    tpl = mesh.vertex_attr["tpl"]
    x, y, z = tpl[:, 0], tpl[:, 1], tpl[:, 2]
    bottom = o.get("bottom", HOOD_BOTTOM_Z)
    is_arm = (np.abs(x) > ARM_MIN_X) & (z > ARM_MIN_Z)
    margin = np.minimum(z - bottom, _neckline_margin("hood", x, y, z))
    margin = np.where(is_arm | (np.abs(x) > HOOD_HALF_WIDTH), -1.0, margin)
    rise = np.clip((z - bottom) / (HOOD_PEAK_Z - bottom), 0, 1) ** 0.7
    thickness = o.get("ease", 0.030) + o.get("bulk", HOOD_BULK) * rise * np.clip(1 - np.abs(x) / HOOD_HALF_WIDTH, 0.35, 1)
    vertices = mesh.vertices + mesh.vertex_normals() * thickness[:, None]
    return [_cut_draped(vertices, np.zeros_like(vertices), tpl, mesh.faces, margin, material)]


def _cords(figure, material, o):
    """Hoodie drawstrings: two thin cords hanging down the chest from the neck opening."""
    mesh = _tights_shell(figure, 1)
    tpl = mesh.vertex_attr["tpl"]
    x, y, z = np.abs(tpl[:, 0]), tpl[:, 1], tpl[:, 2]
    top, length = o.get("top", CORD_TOP_Z), o.get("length", CORD_LENGTH)
    margin = np.where(y < 0, np.minimum(np.minimum(CORD_HALF_WIDTH - np.abs(x - CORD_X), top - z), z - (top - length)), -1.0)
    vertices = mesh.vertices + mesh.vertex_normals() * o.get("ease", 0.032)
    vertices, attrs, faces = cut_by_margin(vertices, {"tpl": tpl}, mesh.faces, margin)
    return [Mesh(vertices, faces, material, material, None, attrs)]


BUILDERS = {"top": _top, "bottom": _bottom, "skirt": _skirt, "dress": _dress, "band": _band, "footwear": _footwear, "tie": _tie,
            "hood": _hood, "cords": _cords,
            "lapel": _lapel}

# Outfit presets: lists of garments. 'color' is the default flat colour (overridable).
OUTFITS = {
    "figure_study": [],
    "underwear": [dict(type="top", id="bra", top=0.585, bottom=0.455, sleeve="none", neckline="straps", color=(0.93, 0.92, 0.90)),
                  dict(type="bottom", id="briefs", top=0.19, length="brief", color=(0.93, 0.92, 0.90))],
    "briefs": [dict(type="bottom", id="briefs", top=0.19, length="brief", color=(0.93, 0.92, 0.90))],
    "trunks": [dict(type="bottom", id="trunks", top=0.24, length="short", ease=0.008, color=(0.18, 0.28, 0.46))],
    "swimsuit": [dict(type="top", id="swimsuit", top=0.80, bottom=_brief_line, sleeve="none", neckline="scoop", color=(0.12, 0.22, 0.42))],
    "bikini": [dict(type="top", id="bikini_top", top=0.585, bottom=0.46, sleeve="none", neckline="halter", color=(0.85, 0.25, 0.22)),
               dict(type="bottom", id="bikini_bottom", top=0.17, length="brief", color=(0.85, 0.25, 0.22))],
    "tshirt_jeans": [dict(type="bottom", id="jeans", length="full", ease=0.007, color=(0.25, 0.34, 0.52)),
                     dict(type="top", id="tshirt", sleeve="short", neckline="crew", bottom=0.22, ease=0.009, folds=0.004, color=(0.95, 0.95, 0.93)),
                     dict(type="footwear", id="shoes", style="shoes", color=(0.92, 0.92, 0.92))],
    "tank_shorts": [dict(type="bottom", id="shorts", length="short", color=(0.30, 0.33, 0.38)),
                    dict(type="top", id="tank", sleeve="none", neckline="scoop", bottom=0.24, ease=0.007, color=(0.92, 0.90, 0.86))],
    "sportswear": [dict(type="top", id="sports_top", top=0.80, bottom=0.44, sleeve="none", neckline="scoop", color=(0.15, 0.15, 0.18)),
                   dict(type="bottom", id="leggings", length="capri", ease=0.004, color=(0.15, 0.15, 0.18)),
                   dict(type="footwear", id="shoes", style="shoes", color=(0.95, 0.95, 0.95))],
    # men's versions of the presets above that are cut for a woman's body (chosen automatically for male figures)
    "underwear_male": [dict(type="bottom", id="briefs", top=0.21, length="low_brief", ease=0.005, color=(0.93, 0.92, 0.90))],
    "swim_trunks": [dict(type="bottom", id="trunks", top=0.22, length="short", ease=0.008, alias="swimsuit", color=(0.12, 0.22, 0.42))],
    "board_shorts": [dict(type="bottom", id="board_shorts", top=0.24, length="bermuda", ease=0.014, folds=0.004, alias="bikini_bottom",
                          color=(0.85, 0.25, 0.22))],
    "sportswear_male": [dict(type="top", id="sports_tee", sleeve="short", neckline="crew", bottom=0.20, ease=0.006, alias="sports_top",
                             color=(0.15, 0.15, 0.18)),
                        dict(type="bottom", id="shorts", length="short", ease=0.010, alias="leggings", color=(0.24, 0.27, 0.34)),
                        dict(type="footwear", id="shoes", style="shoes", color=(0.95, 0.95, 0.95))],
    "sweater_skirt": [dict(type="top", id="sweater", sleeve="long", neckline="turtle", bottom=0.26, ease=0.012, folds=0.005, color=(0.86, 0.80, 0.70)),
                      dict(type="skirt", id="skirt", length="midi", flare=0.05, folds=0.014, color=(0.36, 0.25, 0.22)),
                      dict(type="footwear", id="boots", style="ankle_boots", color=(0.18, 0.13, 0.11))],
    "blouse_trousers": [dict(type="bottom", id="trousers", length="full", ease=0.016, folds=0.004, top=0.38, color=(0.20, 0.21, 0.25)),
                        dict(type="top", id="blouse", sleeve="long", neckline="v", bottom=0.30, ease=0.013, folds=0.006, color=(0.96, 0.95, 0.92)),
                        dict(type="footwear", id="shoes", style="shoes", color=(0.12, 0.10, 0.10))],
    "suit": [dict(type="bottom", id="trousers", length="full", ease=0.016, folds=0.003, top=0.38, color=(0.15, 0.17, 0.22)),
             dict(type="top", id="shirt", sleeve="long", neckline="crew", bottom=0.30, ease=0.008, drape=0, color=(0.96, 0.96, 0.96)),
             dict(type="tie", id="tie", ease=0.0115, color=(0.45, 0.10, 0.14)),
             dict(type="top", id="jacket", sleeve="long", neckline="deep_v", bottom=0.10, ease=0.022, folds=0.004, drape=40, color=(0.18, 0.20, 0.27),
                  closure=dict(top=NECK_Z - 0.27, bottom=0.10, buttons=(0.36, 0.27))),
             dict(type="lapel", id="lapels", neckline="deep_v", over_ease=0.022, drape=40, color=(0.12, 0.135, 0.185)),
             dict(type="footwear", id="shoes", style="shoes", color=(0.10, 0.08, 0.08))],
    # a men's casual-office look: open-collar shirt tucked into belted trousers (the trousers' larger ease keeps
    # them over the shirt tail); the collar points are a narrow lapel along the open neck
    "shirt_trousers": [dict(type="top", id="shirt", sleeve="long", neckline="open_collar", bottom=0.24, ease=0.010,
                            folds=0.005, alias="blouse", color=(0.82, 0.87, 0.94)),
                       dict(type="band", id="collar_stand", top=0.80, bottom=0.685, ease=0.013, neckline="collar_stand",
                            alias="collar", color=(0.84, 0.89, 0.95)),
                       dict(type="lapel", id="collar", neckline="open_collar", width=0.042, bottom=0.62,
                            over_ease=0.017, gap=0.008, color=(0.84, 0.89, 0.95)),
                       dict(type="bottom", id="trousers", length="full", ease=0.016, folds=0.004, top=0.31,
                            color=(0.30, 0.29, 0.27)),
                       dict(type="band", id="belt", top=0.32, bottom=0.29, ease=0.020, color=(0.20, 0.13, 0.09)),
                       dict(type="footwear", id="shoes", style="shoes", color=(0.16, 0.11, 0.08))],
    # street wear of the panel-block estates: a loose hoodie with its hood down and a kangaroo pocket, dark jeans
    "hoodie_jeans": [dict(type="bottom", id="jeans", length="full", ease=0.008, folds=0.004, color=(0.16, 0.18, 0.24)),
                     dict(type="top", id="hoodie", sleeve="long", neckline="crew", bottom=0.10, ease=0.022, folds=0.008,
                          color=(0.10, 0.10, 0.11)),
                     dict(type="hood", id="hood", alias="hoodie", color=(0.09, 0.09, 0.10)),
                     dict(type="band", id="pocket", top=0.27, bottom=0.14, ease=0.030, neckline="pocket", alias="hoodie",
                          color=(0.075, 0.075, 0.085)),
                     dict(type="cords", id="cords", color=(0.72, 0.72, 0.70)),
                     dict(type="footwear", id="shoes", style="shoes", color=(0.13, 0.13, 0.14))],
    # a knee-length wool coat over a turtleneck and trousers
    "long_coat": [dict(type="bottom", id="trousers", length="full", ease=0.012, folds=0.003, top=0.36, color=(0.10, 0.10, 0.11)),
                  dict(type="top", id="sweater", sleeve="long", neckline="turtle", bottom=0.24, ease=0.010, color=(0.14, 0.14, 0.15)),
                  dict(type="dress", id="coat", neckline="deep_v", sleeve="long", length="knee", flare=0.05, ease=0.024, front_opening=0.20,
                       skirt_ease=0.024, bodice_folds=0.004, folds=0.012, color=(0.24, 0.25, 0.23)),
                  dict(type="lapel", id="lapels", neckline="deep_v", over_ease=0.024, color=(0.20, 0.21, 0.19)),
                  dict(type="footwear", id="boots", style="ankle_boots", color=(0.08, 0.07, 0.07))],
    "sundress": [dict(type="dress", id="dress", neckline="straps", length="above_knee", flare=0.07, folds=0.016, color=(0.95, 0.86, 0.55))],
    "little_black_dress": [dict(type="dress", id="dress", neckline="scoop", length="above_knee", flare=0.0, folds=0.004, color=(0.09, 0.09, 0.11))],
    "evening_gown": [dict(type="dress", id="gown", neckline="strapless", length="floor", flare=0.10, folds=0.022, fold_count=14, color=(0.50, 0.08, 0.14))],
    "summer_dress": [dict(type="dress", id="dress", neckline="v", sleeve="cap", length="midi", flare=0.09, folds=0.02, color=(0.80, 0.88, 0.93))],
    # a classical loincloth: a short wrapped drape low on the hips, the covering of Renaissance male figure studies
    "perizoma": [dict(type="skirt", id="perizoma", length="micro", flare=0.02, folds=0.02, fold_count=7, waist=0.17, hem_slant=0.3,
                      color=(0.93, 0.91, 0.86))],
    "chiton": [dict(type="dress", id="chiton", neckline="v", length="ankle", flare=0.05, folds=0.026, fold_count=18,
                    ease=0.012, bodice_folds=0.013, color=(0.95, 0.93, 0.86)),
               dict(type="band", id="belt", top=0.385, bottom=0.350, ease=0.030, color=(0.72, 0.58, 0.30))],
    "hanbok": [dict(type="skirt", id="chima", length="floor", flare=0.16, folds=0.03, fold_count=16, waist=0.50, color=(0.78, 0.20, 0.30)),
               dict(type="top", id="jeogori", sleeve="long", neckline="v", bottom=0.455, ease=0.014, folds=0.004, color=(0.97, 0.95, 0.90))],
    "kimono": [dict(type="skirt", id="kimono_skirt", length="ankle", flare=0.0, folds=0.006, waist=0.40, color=(0.20, 0.28, 0.48)),
               dict(type="top", id="kimono_top", sleeve="long", neckline="v", bottom=0.30, ease=0.016, folds=0.006, color=(0.20, 0.28, 0.48)),
               dict(type="band", id="obi", top=0.47, bottom=0.335, ease=0.024, color=(0.80, 0.68, 0.36))],
    "robe": [dict(type="skirt", id="robe_skirt", length="floor", flare=0.06, folds=0.02, waist=0.40, color=(0.35, 0.30, 0.42)),
             dict(type="top", id="robe_top", sleeve="long", neckline="v", bottom=0.30, ease=0.02, folds=0.010, color=(0.35, 0.30, 0.42))],
    "bodysuit": [dict(type="top", id="bodysuit", top=0.80, bottom=-1.0, sleeve="long", neckline="turtle", ease=0.004, color=(0.20, 0.21, 0.26))],
    "tactical": [dict(type="top", id="bodysuit", top=0.80, bottom=-1.0, sleeve="none", neckline="crew", ease=0.004, color=(0.30, 0.31, 0.36)),
                 dict(type="top", id="vest", top=0.80, bottom=0.30, sleeve="none", neckline="scoop", ease=0.014, color=(0.22, 0.25, 0.24)),
                 dict(type="band", id="belt", top=0.34, bottom=0.29, ease=0.018, color=(0.14, 0.13, 0.12)),
                 dict(type="footwear", id="boots", style="boots", ease=0.010, color=(0.12, 0.12, 0.13))],
    "office": [dict(type="skirt", id="pencil_skirt", length="knee", flare=0.0, folds=0.002, waist=0.38, color=(0.17, 0.18, 0.22)),
               dict(type="top", id="blouse", sleeve="three_quarter", neckline="v", bottom=0.33, ease=0.010, folds=0.004, color=(0.95, 0.94, 0.92)),
               dict(type="footwear", id="shoes", style="shoes", color=(0.10, 0.09, 0.09))],
}


MALE_VARIANTS = {"underwear": "underwear_male", "swimsuit": "swim_trunks", "bikini": "board_shorts", "sportswear": "sportswear_male",
                 "blouse_trousers": "shirt_trousers", "office": "shirt_trousers"}


UNDERWEAR_IDS = ("bra", "briefs")             # worn under clothes: they do not count as clothing a minor is shown in
ONE_PIECE_IDS = ("swimsuit", "bodysuit")      # tops that also cover the pelvis
BARE_BOTTOM_LENGTHS = ("brief", "low_brief")  # bottoms this short (a bikini, briefs) leave the pelvis bare
BARE_SKIRT_LENGTHS = ("micro",)               # a loincloth


def resolve_outfit(outfit, masculine=False):
    """Garment dicts of an outfit preset name or list, after the men's swaps."""
    if isinstance(outfit, str) and masculine:
        outfit = MALE_VARIANTS.get(outfit, outfit)
    return OUTFITS[outfit] if isinstance(outfit, str) else list(outfit)


def covers(garments):
    """(chest covered, pelvis covered) by the garments, not counting underwear."""
    worn = [g for g in garments if g.get("id", g["type"]) not in UNDERWEAR_IDS]
    chest = any(g["type"] in ("top", "dress") for g in worn)
    pelvis = any(g["type"] == "dress" or g.get("id") in ONE_PIECE_IDS
                 or (g["type"] == "skirt" and g.get("length", "knee") not in BARE_SKIRT_LENGTHS)
                 or (g["type"] == "bottom" and g.get("length", "full") not in BARE_BOTTOM_LENGTHS) for g in worn)
    return chest, pelvis


CLOSURE_EDGE_X = -0.012         # a jacket's overlapping front edge runs just to the wearer's right of centre
CLOSURE_HALF_WIDTH = 0.0022      # half width of the shadow line along that edge (m)
CLOSURE_SHADE = 0.55             # the edge line is the jacket colour darkened this much
CLOSURE_SOFT = 0.0008
CLOSURE_FRONT_Y = -0.03          # template y in front of which the closure shows
BUTTON_RADIUS = 0.0085
BUTTON_SHADE = 0.6


def closure_painters(figure_name, outfit, masculine=False):
    """Painters for garments that close down the front (a suit jacket): the overlapping edge and its buttons.

    Without them a jacket over a shirt reads as a V-neck sweater."""
    return [_closure_painter(f"{figure_name}.{piece.get('id', piece['type'])}", **piece["closure"])
            for piece in resolve_outfit(outfit, masculine) if piece.get("closure")]


def _closure_painter(material, top, bottom, buttons):
    from .shade import material_mask

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = material_mask(g, material)
        if not mask.any():
            return
        tpl = g["attrs"]["tpl"]
        x, y, z = tpl[..., 0], tpl[..., 1], tpl[..., 2]
        front = mask & (y < CLOSURE_FRONT_Y)
        edge = np.clip((CLOSURE_HALF_WIDTH - np.abs(x - CLOSURE_EDGE_X)) / CLOSURE_SOFT + 0.5, 0, 1) * front * (z < top) * (z > bottom)
        dark = albedo * CLOSURE_SHADE
        albedo[:] = albedo + (dark - albedo) * edge[..., None]
        for height in buttons:
            dot = np.clip((BUTTON_RADIUS - np.hypot(x, z - height)) / CLOSURE_SOFT + 0.5, 0, 1) * front
            albedo[:] = albedo + (albedo * BUTTON_SHADE - albedo) * dot[..., None]

    return paint


def make_outfit(figure, outfit="figure_study", colors=None, masculine=False):
    """Build an outfit. outfit: preset name or a list of garment dicts.

    colors: {garment_id: rgb} overrides. Returns (meshes, palette).
    masculine: presets cut for a woman's body (bra tops, bikinis) are swapped for their men's version.
    """
    garments = resolve_outfit(outfit, masculine)
    meshes, palette = [], {}
    for garment in garments:
        options = dict(garment)
        kind = options.pop("type")
        gid = options.pop("id", kind)
        alias = options.pop("alias", None)            # men's variants answer to the colour keys of the original
        default = options.pop("color", (0.6, 0.6, 0.6))
        color = (colors or {}).get(gid, (colors or {}).get(alias, default))
        material = f"{figure.name}.{gid}"
        meshes.extend(BUILDERS[kind](figure, material, options))
        palette[material] = tuple(color)
    return meshes, palette


def hand_points(figure):
    """Posed hand vertices (wrists included) of a figure."""
    body = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]]
    tpl = figure.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1]]
    return body[np.abs(tpl[:, 0]) > HAND_MIN_X]


def _arm_side(tpl):
    """Per template point: +1 left arm, -1 right arm, 0 trunk and legs (hands count as arm)."""
    is_arm = (np.abs(tpl[:, 0]) > ARM_MIN_X) & (tpl[:, 2] > ARM_MIN_Z)
    return np.where(is_arm, np.sign(tpl[:, 0]), 0).astype(int)


def press_under_hands(figure, cloth_meshes, other_hands):
    """Push a figure's clothes behind any hand resting on them (its own or another person's).

    The garments stand off the skin by their ease, so a hand laid on a thigh or a hip ends up inside a loose
    skirt or trouser leg. A real hand presses the cloth down under the palm: here every cloth point with a hand
    between itself and the skin sinks below that hand, and the dent spreads and softens over its neighbours
    the way fabric bridges the gaps between fingers.
    """
    body = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]]
    tpl = figure.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1]]
    side = _arm_side(tpl)
    hand = np.abs(tpl[:, 0]) > HAND_MIN_X
    own = {k: body[hand & (side == k)] for k in (1, -1)}
    trunk = body[side == 0]
    # a hand tucked under the other arm (arms crossed) is hidden there: it should not dent the shirt behind it
    own = {k: points if _tucked(points, trunk, body[(side == -k) & ~hand]).mean() < TUCKED_SHARE else points[:0]
           for k, points in own.items()}
    other = np.asarray(other_hands, float).reshape(-1, 3)
    # a sleeve is measured from its whole arm, wrist and hand included (its cuff hangs over the wrist), and only a
    # partner's hand presses it: the wearer's own hands on their arms (arms crossed) tuck under, they do not rest on top
    regions = {0: (trunk, np.vstack([own[1], own[-1], other])),
               1: (body[side == 1], other),
               -1: (body[side == -1], other)}
    push = [np.zeros(len(m.vertices)) for m in cloth_meshes]
    normals = [m.vertex_normals() for m in cloth_meshes]
    for region, (skin, hands) in regions.items():
        if len(hands) == 0 or len(skin) == 0:
            continue
        hand_tree, skin_tree = cKDTree(hands), cKDTree(skin)
        layers = []
        for index, mesh in enumerate(cloth_meshes):
            mine = _arm_side(mesh.vertex_attr["tpl"]) == region
            dist, _ = hand_tree.query(mesh.vertices, distance_upper_bound=PRESS_REACH)
            near = np.flatnonzero(np.isfinite(dist) & mine)
            if len(near):
                gap = skin_tree.query(mesh.vertices[near])[0]
                layers.append((index, mine, near, np.median(gap)))
        # inner layers are pressed a little deeper than outer ones so they never cross
        layers.sort(key=lambda layer: layer[3])
        for rank, (index, mine, near, _) in enumerate(layers):
            under = (len(layers) - 1 - rank) * PRESS_LAYER_STEP
            floor = PRESS_MIN_OFFSET + rank * PRESS_LAYER_STEP
            mesh, normal = cloth_meshes[index], normals[index]
            depth = np.zeros(len(mesh.vertices))
            depth[near] = _hand_depth(mesh.vertices[near], normal[near], skin_tree, hands, hand_tree, under)
            # fabric bridges the fingers and slopes into the dent instead of following every knuckle
            depth = _spread(depth, mesh.faces, PRESS_SPREAD_PASSES) * mine
            moved = np.flatnonzero(depth > 0)
            if len(moved):
                room = skin_tree.query(mesh.vertices[moved])[0] - floor
                push[index][moved] = np.maximum(push[index][moved], np.clip(depth[moved], 0, np.maximum(room, 0)))
    body_tree = cKDTree(body[~hand])
    for mesh, normal, amount in zip(cloth_meshes, normals, push):
        moved = np.flatnonzero(amount > 0)
        if len(moved):
            points = mesh.vertices[moved]
            away = points - body_tree.data[body_tree.query(points)[1]]
            inward = np.where(np.sum(normal[moved] * away, axis=1, keepdims=True) < 0, normal[moved], -normal[moved])
            vertices = mesh.vertices.copy()
            vertices[moved] = points + inward * amount[moved, None]
            mesh.vertices = vertices


def _tucked(hand, trunk, arm):
    """True for hand points with the given arm lying over them, seen from the trunk outward."""
    if len(hand) == 0 or len(arm) == 0:
        return np.zeros(len(hand), bool)
    base = trunk[cKDTree(trunk).query(hand)[1]]
    outward = hand - base
    outward /= np.maximum(np.linalg.norm(outward, axis=1, keepdims=True), 1e-9)
    arm_tree = cKDTree(arm)
    covered = np.zeros(len(hand), bool)
    for step in TUCK_STEPS:
        covered |= np.isfinite(arm_tree.query(hand + outward * step, distance_upper_bound=TUCK_RADIUS)[0])
    return covered


def _hand_depth(points, normal, skin_tree, hands, hand_tree, under):
    """How far each cloth point must sink along its inward normal to pass under the hand points beneath it."""
    base = skin_tree.data[skin_tree.query(points)[1]]
    outward = np.where(np.sum(normal * (points - base), axis=1, keepdims=True) < 0, -normal, normal)
    height = np.linalg.norm(points - base, axis=1)
    depth = np.zeros(len(points))
    for k, members in enumerate(hand_tree.query_ball_point(points, PRESS_REACH)):
        if not members:
            continue
        rel = hands[members] - points[k]
        inside = -(rel @ outward[k])                                    # how far each hand point lies under the cloth
        lateral = np.linalg.norm(rel + inside[:, None] * outward[k], axis=1)
        caught = (inside > 0) & (inside < height[k])                    # under the cloth, above the skin
        if caught.any():
            need = inside[caught] + PRESS_GAP + under
            weight = np.clip(1 - (lateral[caught] - PRESS_LINE_RADIUS) / (PRESS_SLOPE * need), 0, 1)
            depth[k] = (weight * need).max()
    return depth


def _spread(values, faces, passes):
    """Grow a per-vertex value into its neighbourhood (never lowering it), then soften the result."""
    from scipy.sparse import coo_matrix, diags
    n = len(values)
    rows = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2], faces[:, 1], faces[:, 2], faces[:, 0]])
    cols = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0], faces[:, 0], faces[:, 1], faces[:, 2]])
    adjacency = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
    adjacency.data[:] = 1.0
    average = diags(1.0 / np.maximum(np.asarray(adjacency.sum(1)).ravel(), 1)) @ adjacency
    out = np.asarray(values, float)
    for _ in range(passes):
        out = np.maximum(out, average @ out)
    return np.maximum(values, 0.5 * out + 0.5 * (average @ out))
