"""Anatomical pose language -> bone rotations.

Raw bone Euler angles are error-prone to author, so poses are written as joint angles
with human meaning (raise an arm, bend an elbow, curl fingers). All angles are degrees.

  body  : lean (forward +), tilt (to figure's left +), turn (to figure's left +)   whole-body from the pelvis
  torso : bend, side, twist                                                        spread over the spine
  head  : nod (down +), tilt, turn                                                 spread over neck and head
  arm.L / arm.R : lift (0 hanging, 90 horizontal, 180 up), forward (90 front, 0 side, -90 back),
                  twist, elbow (0 straight), forearm_twist, wrist, wrist_side, shrug
  leg.L / leg.R : forward (hip flexion; 90 = thigh horizontal in front), side (abduction),
                  twist (toes out +), knee (0 straight), ankle (toes down +), foot_turn
  hand.L / hand.R : preset name or {curl: [thumb, index, middle, ring, pinky] 0..1, spread: -1..1}
  reach.L / reach.R : put a palm somewhere without guessing angles. A landmark name ("chin", "hip.R", "heart", ...),
                  a point [x, y, z] in the figure's own space, or {to: ..., elbow: down|out|back|up|forward, offset: metres}.
                  {world: [x, y, z]} aims at a point in the scene; in a scene, "name:landmark" aims at another figure.
                  lay: true lays the palm flat on the landmark's skin (a hand on the chest, a hip, a partner's shoulder).
                  Overrides lift/forward/twist/elbow of that arm; wrist and forearm_twist still apply.
  gaze  : yaw (to figure's left +), pitch (up +)
  airborne : metres the lowest point of the body floats above the ground (a jump); 0 = standing on it
  bones : {bone_name: [rx, ry, rz]} raw overrides in rest-world axes
"""
import functools
import numpy as np

from .mesh import euler_matrix

SIDES = {"L": 1.0, "R": -1.0}
SPINE_BONES = ("spine05", "spine04", "spine03", "spine02", "spine01")
NECK_SHARE = {"neck01": 0.15, "neck02": 0.15, "neck03": 0.15, "head": 0.55}
HEAD_REST_NOD = 7.0          # the rest mesh carries its chin slightly high; this levels the gaze
FINGER_JOINT_MAX = (85.0, 100.0, 70.0)       # knuckle, middle, tip
THUMB_JOINT_MAX = (35.0, 50.0, 70.0)
FINGER_SPREAD_DEG = {2: -9.0, 3: 0.0, 4: 7.0, 5: 15.0}

# where the palms hold an open book, in the figure's own space (pelvis origin): wide enough for the spread pages
READ_HOLD_L, READ_HOLD_R = [0.12, -0.34, 0.37], [-0.12, -0.34, 0.37]
READ_SEATED_L, READ_SEATED_R = [0.12, -0.34, 0.30], [-0.12, -0.34, 0.30]
HAND_PRESETS = {
    "relaxed": dict(curl=[0.20, 0.18, 0.26, 0.34, 0.42], spread=0.1),
    "open":    dict(curl=[0.0, 0.0, 0.0, 0.0, 0.0], spread=0.7),
    "flat":    dict(curl=[0.05, 0.0, 0.0, 0.0, 0.0], spread=-0.2),
    "fist":    dict(curl=[0.75, 1.0, 1.0, 1.0, 1.0], spread=-0.2),
    "point":   dict(curl=[0.80, 0.0, 1.0, 1.0, 1.0], spread=0.0),
    "peace":   dict(curl=[0.85, 0.0, 0.0, 1.0, 1.0], spread=0.8),
    "grip":    dict(curl=[0.45, 0.55, 0.58, 0.62, 0.66], spread=0.0),
    "pinch":   dict(curl=[0.55, 0.55, 0.20, 0.25, 0.30], spread=0.2),
    "graceful": dict(curl=[0.12, 0.08, 0.30, 0.38, 0.30], spread=0.25),
    "thumbs_up": dict(curl=[0.0, 1.0, 1.0, 1.0, 1.0], spread=-0.2),
    "cigarette": dict(curl=[0.35, 0.18, 0.22, 0.62, 0.72], spread=-0.15),    # index and middle loose together
    "rest":    dict(curl=[0.10, 0.12, 0.14, 0.16, 0.18], spread=-0.25),     # laid on a body: fingers together, barely bent
}


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def axis_angle(axis, degrees):
    """Rotation matrix about a unit axis (Rodrigues)."""
    x, y, z = _unit(axis)
    a = np.radians(degrees)
    c, s, t = np.cos(a), np.sin(a), 1 - np.cos(a)
    return np.array([[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
                     [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
                     [t * x * z - s * y, t * y * z + s * x, t * z * z + c]])


def swing(source, target):
    """Smallest rotation taking direction `source` to direction `target`."""
    s, t = _unit(source), _unit(target)
    axis = np.cross(s, t)
    norm = np.linalg.norm(axis)
    if norm < 1e-9:
        return np.eye(3) if s @ t > 0 else axis_angle(np.cross(s, [0.3, 0.5, 0.8]), 180.0)
    return axis_angle(axis / norm, np.degrees(np.arctan2(norm, s @ t)))


@functools.lru_cache(maxsize=1)
def _rest():
    """Joint positions of the default adult at rest; pose axes are derived from them."""
    from .figure import Figure, _model
    figure = Figure(name="_rest")
    labels = _model().bone_labels
    return {bone: figure.rest_bone_poses[i][:3, 3] for i, bone in enumerate(labels)}


def _direction(a, b):
    rest = _rest()
    return _unit(rest[b] - rest[a])


def _arm(side, spec, out):
    s = SIDES[side]
    upper = _direction(f"upperarm01.{side}", f"lowerarm01.{side}")
    fore = _direction(f"lowerarm01.{side}", f"wrist.{side}")
    rest_raise = np.degrees(np.arccos(-upper[2]))
    raise_deg = spec.get("lift", rest_raise)
    forward = np.radians(spec.get("forward", 0.0))
    polar = np.radians(raise_deg)
    target = np.array([s * np.sin(polar) * np.cos(forward), -np.sin(polar) * np.sin(forward), -np.cos(polar)])
    rotation = swing(upper, target)
    # inward twist is positive for both arms
    rotation = axis_angle(target, s * spec.get("twist", 0.0)) @ rotation
    out[f"upperarm01.{side}"] = rotation
    # shoulder girdle follows a raised arm (otherwise the shoulder caves in)
    lift = spec.get("shrug", 0.0) + max(raise_deg - 70.0, 0.0) * 0.35
    if lift:
        out[f"clavicle.{side}"] = axis_angle([0, 1, 0], -s * lift)
    hinge = _unit(np.cross(upper, fore))
    rest_flex = np.degrees(np.arccos(np.clip(upper @ fore, -1, 1)))
    if "elbow" in spec:
        out[f"lowerarm01.{side}"] = axis_angle(hinge, spec["elbow"] - rest_flex)
    if spec.get("forearm_twist"):
        out[f"lowerarm02.{side}"] = axis_angle(fore, -s * spec["forearm_twist"])
    hand_dir, width, palm = _hand_axes(side)
    wrist = np.eye(3)
    if spec.get("wrist"):
        wrist = axis_angle(_curl_axis(hand_dir, width, palm), spec["wrist"]) @ wrist
    if spec.get("wrist_side"):
        wrist = axis_angle(palm, spec["wrist_side"]) @ wrist
    if not np.allclose(wrist, np.eye(3)):
        out[f"wrist.{side}"] = wrist


def _hand_axes(side):
    hand_dir = _direction(f"wrist.{side}", f"finger3-1.{side}")
    width = _direction(f"finger2-1.{side}", f"finger5-1.{side}")
    palm = _unit(np.cross(hand_dir, width))
    if palm[2] > 0:               # at rest the palm faces down toward the thigh
        palm = -palm
    return hand_dir, width, palm


def _curl_axis(direction, width, palm):
    """Axis along the hand's width, signed so a positive angle folds `direction` toward the palm."""
    return width if np.cross(width, direction) @ palm > 0 else -width


def _hand(side, spec, out):
    if isinstance(spec, str):
        spec = HAND_PRESETS[spec]
    curl = list(spec.get("curl", [0, 0, 0, 0, 0]))
    spread = spec.get("spread", 0.0)
    hand_dir, width, palm = _hand_axes(side)
    for finger in (2, 3, 4, 5):
        direction = _direction(f"finger{finger}-1.{side}", f"finger{finger}-2.{side}")
        axis = _curl_axis(direction, width, palm)
        for joint, limit in enumerate(FINGER_JOINT_MAX, start=1):
            rotation = axis_angle(axis, curl[finger - 1] * limit)
            if joint == 1 and spread:
                fan = np.sign(np.cross(palm, direction) @ width) * FINGER_SPREAD_DEG[finger] * spread
                rotation = rotation @ axis_angle(palm, fan)
            out[f"finger{finger}-{joint}.{side}"] = rotation
    # the thumb closes by sweeping across the palm, i.e. turning about the hand's long axis
    thumb_axis = hand_dir * SIDES[side]
    for joint, limit in enumerate(THUMB_JOINT_MAX, start=1):
        out[f"finger1-{joint}.{side}"] = axis_angle(thumb_axis, curl[0] * limit)


def _leg(side, spec, out):
    s = SIDES[side]
    thigh = _direction(f"upperleg01.{side}", f"lowerleg01.{side}")
    shin = _direction(f"lowerleg01.{side}", f"foot.{side}")
    rest_side = np.degrees(np.arcsin(s * thigh[0]))
    flex = np.radians(spec.get("forward", 0.0))
    abduct = np.radians(spec.get("side", rest_side))
    target = np.array([s * np.sin(abduct), -np.sin(flex) * np.cos(abduct), -np.cos(flex) * np.cos(abduct)])
    rotation = swing(thigh, target)
    rotation = axis_angle(target, -s * spec.get("twist", 0.0)) @ rotation
    out[f"upperleg01.{side}"] = rotation
    rest_knee = np.degrees(np.arctan2(shin[1], -shin[2]) - np.arctan2(thigh[1], -thigh[2]))
    if "knee" in spec:
        out[f"lowerleg01.{side}"] = axis_angle([1, 0, 0], spec["knee"] - rest_knee)
    foot = np.eye(3)
    if spec.get("ankle"):
        foot = axis_angle([1, 0, 0], spec["ankle"]) @ foot
    if spec.get("foot_turn"):
        foot = axis_angle([0, 0, 1], s * spec["foot_turn"]) @ foot
    if not np.allclose(foot, np.eye(3)):
        out[f"foot.{side}"] = foot


POLES = {"down": (0, 0, -1), "out": (1, 0, -0.2), "back": (0.3, 1, -0.3), "up": (0.4, 0, 1), "forward": (0.2, -1, -0.2)}
REACH_OFFSET = 0.02           # the palm stops this far above the skin
TRUNK_HALF_WIDTH, TRUNK_Z = 0.19, (-0.15, 0.80)     # template box holding the trunk (the rest pose keeps the arms outside it)
ARM_RADIUS = 0.03             # forearm flesh around the bones
ARM_SAMPLES = 8
ARM_SAMPLE_END = 0.7          # the wrist end is meant to touch the target, so it is not tested
ARM_CLEARANCE_TOLERANCE = 0.012   # mean sink (m) accepted before the elbow is turned outward
ELBOW_SWINGS = (15, -15, 30, -30, 45, -45, 60, -60)   # degrees tried when the arm would sink into the trunk
PALM_REACH = 0.085            # wrist to the middle of the palm


class _Torso:
    """The trunk of a posed figure (arms left out), for keeping a reaching arm on its surface instead of inside it."""

    def __init__(self, figure):
        from scipy.spatial import cKDTree
        from .figure import BODY_RANGE
        from .mesh import Mesh
        tpl = figure.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1]]
        trunk = (np.abs(tpl[:, 0]) < TRUNK_HALF_WIDTH) & (tpl[:, 2] > TRUNK_Z[0]) & (tpl[:, 2] < TRUNK_Z[1])
        body_faces = figure.faces[(figure.faces < BODY_RANGE[1]).all(1)]
        normals = Mesh(figure.vertices, body_faces).vertex_normals()[BODY_RANGE[0]:BODY_RANGE[1]]
        local = (figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]] - figure.world[:3, 3]) @ figure.world[:3, :3]
        self.points, self.normals = local[trunk], normals[trunk] @ figure.world[:3, :3]
        self.tree = cKDTree(self.points)

    def penetration(self, elbow, hand):
        """Mean depth (metres) by which the forearm's flesh would sink into the trunk.

        Only the forearm is tested: the upper arm always lies against the trunk near the armpit,
        and the hand end is meant to touch its target."""
        t = np.linspace(0, ARM_SAMPLE_END, ARM_SAMPLES)[:, None]
        samples = elbow + (hand - elbow) * t
        _, nearest = self.tree.query(samples)
        distance = np.sum((samples - self.points[nearest]) * self.normals[nearest], 1)
        return float(np.maximum(ARM_RADIUS - distance, 0).mean())


def solve_reach(figure, side, target, elbow="down", palm_reach=PALM_REACH, info=None):
    """Two-bone inverse kinematics: bone rotations that put the palm of one hand on `target`.

    figure: a Figure already posed without this reach (gives where the shoulder ended up).
    target: point in the figure's own space.  elbow: where the elbow points (key of POLES or a vector).
    palm_reach: wrist to the target along the forearm (0 puts the wrist itself on the target).
    info: optional dict that receives the solved forearm direction and the body scale.
    """
    s = SIDES[side]
    rest = _rest()
    upper_rest = _direction(f"upperarm01.{side}", f"lowerarm01.{side}")
    fore_rest = _direction(f"lowerarm01.{side}", f"wrist.{side}")
    hinge_rest = _unit(np.cross(upper_rest, fore_rest))
    rest_flex = np.degrees(np.arccos(np.clip(upper_rest @ fore_rest, -1, 1)))
    shoulder = figure.bone_position(f"upperarm01.{side}")
    scale = np.linalg.norm(figure.bone_position(f"lowerarm01.{side}") - shoulder) / \
        np.linalg.norm(rest[f"lowerarm01.{side}"] - rest[f"upperarm01.{side}"])
    len_upper = np.linalg.norm(rest[f"lowerarm01.{side}"] - rest[f"upperarm01.{side}"]) * scale
    len_fore = (np.linalg.norm(rest[f"wrist.{side}"] - rest[f"lowerarm01.{side}"]) + palm_reach) * scale
    to_target = np.asarray(target, float) - shoulder
    distance = np.clip(np.linalg.norm(to_target), abs(len_upper - len_fore) + 1e-3, len_upper + len_fore - 1e-3)
    aim = _unit(to_target)
    # law of cosines: elbow opening and the angle between the upper arm and the shoulder-target line
    elbow_inner = np.arccos(np.clip((len_upper ** 2 + len_fore ** 2 - distance ** 2) / (2 * len_upper * len_fore), -1, 1))
    lead = np.arccos(np.clip((len_upper ** 2 + distance ** 2 - len_fore ** 2) / (2 * len_upper * distance), -1, 1))
    pole = np.asarray(POLES[elbow] if isinstance(elbow, str) else elbow, float) * [s, 1, 1]
    sideways = pole - aim * (pole @ aim)
    sideways = _unit(sideways if np.linalg.norm(sideways) > 1e-6 else np.cross(aim, [0, 1, 0]))
    hand = shoulder + aim * distance
    torso = _Torso(figure)

    def arm_for(swing_deg):
        """Elbow placement for the pole turned `swing_deg` about the shoulder-hand line."""
        turned = axis_angle(aim, swing_deg) @ sideways
        upper = np.cos(lead) * aim + np.sin(lead) * turned
        return upper, shoulder + upper * len_upper

    # keep the requested elbow direction unless the arm would sink into the torso; then turn it outward just enough
    requested = torso.penetration(arm_for(0.0)[1], hand)
    chosen = 0.0
    if requested > ARM_CLEARANCE_TOLERANCE:
        # the smallest turn that clears the trunk; failing that, the clearest turn tried
        depths = {swing_deg: torso.penetration(arm_for(swing_deg)[1], hand) for swing_deg in ELBOW_SWINGS}
        clear = [swing_deg for swing_deg in ELBOW_SWINGS if depths[swing_deg] <= ARM_CLEARANCE_TOLERANCE]
        chosen = clear[0] if clear else min(depths, key=depths.get)
    upper_dir, elbow_pos = arm_for(chosen)
    fore_dir = _unit(hand - elbow_pos)
    if info is not None:
        info.update(forearm=fore_dir, scale=scale)
    # express the wanted directions in the parent's frame, where the bone's own rotation is defined
    parent = figure.bone_rotation(f"shoulder01.{side}")
    upper_local, fore_local = parent.T @ upper_dir, parent.T @ fore_dir
    rotation = swing(upper_rest, upper_local)
    hinge_now = rotation @ hinge_rest
    hinge_wanted = _unit(np.cross(upper_local, fore_local))
    twist = np.degrees(np.arctan2(np.cross(hinge_now, hinge_wanted) @ upper_local, hinge_now @ hinge_wanted))
    return {f"upperarm01.{side}": axis_angle(upper_local, twist) @ rotation,
            f"lowerarm01.{side}": axis_angle(hinge_rest, 180.0 - np.degrees(elbow_inner) - rest_flex)}


def reach_requests(spec):
    """Extract {side: (target, elbow, offset, palm)} from a pose spec ('reach.L' / 'reach.R' entries).

    palm: None, or ("world" | "local", direction) the palm should face when it rests flat on a surface."""
    out = {}
    for side in SIDES:
        entry = (spec or {}).get(f"reach.{side}")
        if entry is not None:
            entry = {"to": entry} if isinstance(entry, (str, list, tuple)) else entry
            target = ("world", np.asarray(entry["world"], float)) if "world" in entry else entry["to"]
            elbow = ("world", np.asarray(entry["elbow_world"], float)) if "elbow_world" in entry else entry.get("elbow", "down")
            palm = ("world", np.asarray(entry["palm_world"], float)) if "palm_world" in entry else \
                ("local", np.asarray(entry["palm"], float)) if "palm" in entry else \
                ("landmark", None) if entry.get("lay") and isinstance(target, str) else None
            if palm is not None and ("fingers_world" in entry or "fingers" in entry):
                key = "fingers_world" if "fingers_world" in entry else "fingers"
                palm = palm + (np.asarray(entry[key], float),)
            out[side] = (target, elbow, entry.get("offset", REACH_OFFSET), palm)
    return out


WRIST_SWING_LIMIT = 80.0       # wrist flexion or extension a hand laid on a surface may use (degrees)
FOREARM_TWIST_LIMIT = 100.0    # pronation or supination from the hanging rest (degrees)
SLIDE_MIN = 0.25               # below this the forearm meets the surface head-on and the fingers keep its line


def _quat(m):
    """Unit quaternion (w, x, y, z) of a rotation matrix."""
    w = np.sqrt(max(1.0 + np.trace(m), 1e-12)) / 2
    return np.array([w, (m[2, 1] - m[1, 2]) / (4 * w), (m[0, 2] - m[2, 0]) / (4 * w), (m[1, 0] - m[0, 1]) / (4 * w)])


def _quat_angle_axis(q):
    q = q if q[0] >= 0 else -q
    vector = np.linalg.norm(q[1:])
    if vector < 1e-9:
        return 0.0, np.array([1.0, 0.0, 0.0])
    return np.degrees(2 * np.arctan2(vector, q[0])), q[1:] / vector


def _swing_twist(rotation, axis):
    """Split `rotation` into swing @ twist, the twist turning about `axis`. Returns (swing, twist_deg)."""
    q = _quat(rotation)
    along = q[1:] @ axis
    twist_q = np.array([q[0], *(along * axis)])
    twist_q /= max(np.linalg.norm(twist_q), 1e-12)
    angle, twist_axis = _quat_angle_axis(twist_q)
    twist_deg = angle if twist_axis @ axis > 0 else -angle
    swing_rot = rotation @ axis_angle(axis, -twist_deg)
    return swing_rot, twist_deg


def _limited(rotation, limit_deg):
    """The same rotation, its angle cut to `limit_deg`."""
    angle, axis = _quat_angle_axis(_quat(rotation))
    return rotation if angle <= limit_deg else axis_angle(axis, limit_deg)


def _laid_palm(figure_options, bones, figure, side, point, elbow, facing, fingers=None):
    """Arm and hand rotations that lay a palm flat on a surface at `point` (figure space).

    facing: direction the palm faces (into the surface). fingers: optional direction the fingers should run
    (a hand on a shoulder drapes them over its front); without it the fingers carry on the forearm's line where
    it crosses the surface, so the wrist bends no more than the surface asks. The wrist goes where the palm
    centre lands on `point`. The hand's turn is shared out the way a real arm does it: the turn about the
    forearm goes to the forearm bone, only the bend toward the palm or the back of the hand to the wrist."""
    from .figure import Figure
    info = {}
    solve_reach(figure, side, point, elbow, info=info)
    facing = _unit(facing)
    lead = info["forearm"] if fingers is None else _unit(fingers)
    slide = lead - facing * (lead @ facing)
    fingers = _unit(slide) if np.linalg.norm(slide) > SLIDE_MIN else info["forearm"]
    facing = _unit(facing - fingers * (facing @ fingers))
    wrist_point = np.asarray(point, float) - fingers * PALM_REACH * info["scale"]
    arm = solve_reach(figure, side, wrist_point, elbow, palm_reach=0.0)
    posed = {**bones, **arm}
    posed.pop(f"lowerarm02.{side}", None)
    posed.pop(f"wrist.{side}", None)
    forearm = Figure(pose=posed, **figure_options).bone_rotation(f"lowerarm02.{side}")
    hand_dir, _, palm = _hand_axes(side)
    rest_frame = np.column_stack([hand_dir, palm, np.cross(hand_dir, palm)])
    wanted = np.column_stack([fingers, facing, np.cross(fingers, facing)])
    local = forearm.T @ wanted @ rest_frame.T
    axis = _direction(f"lowerarm01.{side}", f"wrist.{side}")
    swing_rot, twist_deg = _swing_twist(local, axis)
    twist = axis_angle(axis, float(np.clip(twist_deg, -FOREARM_TWIST_LIMIT, FOREARM_TWIST_LIMIT)))
    wrist = _limited(twist.T @ swing_rot @ twist, WRIST_SWING_LIMIT)
    return {**arm, f"lowerarm02.{side}": twist, f"wrist.{side}": wrist}


def make_figure(pose_spec, **figure_options):
    """Build a posed Figure from a pose spec, including hands that must reach a target.

    Reaches need two passes: pose the body first to learn where the shoulders are, then solve the arms."""
    from .figure import Figure
    pose_spec = {"preset": pose_spec} if isinstance(pose_spec, str) else dict(pose_spec or {})
    bones = resolve(pose_spec)
    figure = Figure(pose=bones, **figure_options)
    reaches = reach_requests(_merge(BODY_POSES.get(pose_spec.get("preset"), {}), pose_spec))
    if not reaches:
        return figure
    for side, (target, elbow, offset, palm) in reaches.items():
        if isinstance(target, tuple) and target[0] == "world":         # a point in the scene, e.g. on another figure
            point = figure.world[:3, :3].T @ (target[1] - figure.world[:3, 3])
        elif isinstance(target, str):
            point = figure.landmark(target, offset, local=True)
        else:
            point = np.asarray(target, float)
        if isinstance(elbow, tuple) and elbow[0] == "world":           # elbow direction given in scene axes
            elbow = (figure.world[:3, :3].T @ elbow[1]) * [SIDES[side], 1, 1]   # solve_reach mirrors x for the side
        if palm is None:
            bones.update(solve_reach(figure, side, point, elbow))
        else:
            to_local = figure.world[:3, :3].T if palm[0] in ("world", "landmark") else np.eye(3)
            facing = -figure.surface_normal(target) if palm[0] == "landmark" else palm[1]
            fingers = to_local @ palm[2] if len(palm) > 2 else None
            bones.update(_laid_palm(figure_options, bones, figure, side, point, elbow, to_local @ facing, fingers))
    return Figure(pose=bones, **figure_options)


def airborne(pose_spec):
    """Height (metres) the pose leaves the ground by: the 'airborne' entry of the spec or of its preset."""
    spec = {"preset": pose_spec} if isinstance(pose_spec, str) else dict(pose_spec or {})
    return float(_merge(BODY_POSES.get(spec.get("preset"), {}), spec).get("airborne", 0.0))


def _merge(base, override):
    merged = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def resolve(spec):
    """Pose spec (see module docstring) -> {bone: 3x3 rotation in rest-world axes}."""
    spec = dict(spec or {})
    preset = spec.pop("preset", None)
    if preset:
        if preset not in BODY_POSES:
            raise KeyError(f"unknown pose preset '{preset}'. Available: {sorted(BODY_POSES)}")
        spec = _merge(BODY_POSES[preset], spec)
    out = {}
    body = spec.get("body", {})
    if body:
        out["root"] = euler_matrix(body.get("lean", 0), body.get("tilt", 0), body.get("turn", 0))
    torso = spec.get("torso", {})
    if torso:
        share = 1.0 / len(SPINE_BONES)
        step = euler_matrix(torso.get("bend", 0) * share, torso.get("side", 0) * share, torso.get("twist", 0) * share)
        for bone in SPINE_BONES:
            out[bone] = step
    head = spec.get("head", {})
    nod = head.get("nod", 0) + HEAD_REST_NOD
    for bone, share in NECK_SHARE.items():
        out[bone] = euler_matrix(nod * share, head.get("tilt", 0) * share, head.get("turn", 0) * share)
    for side in SIDES:
        if f"arm.{side}" in spec:
            _arm(side, spec[f"arm.{side}"], out)
        if f"leg.{side}" in spec:
            _leg(side, spec[f"leg.{side}"], out)
        _hand(side, spec.get(f"hand.{side}", "relaxed"), out)
    gaze = spec.get("gaze", {})
    if gaze:
        look = euler_matrix(-gaze.get("pitch", 0), 0, gaze.get("yaw", 0))
        out["eye.L"] = out["eye.R"] = look
    for bone, angles in spec.get("bones", {}).items():
        out[bone] = euler_matrix(*angles)
    return out


# Body presets. Each is a partial pose spec; user specs are merged over them.
BODY_POSES = {
    "a_pose": {},
    "stand": {
        "arm.L": dict(lift=9, forward=10, elbow=14), "arm.R": dict(lift=9, forward=10, elbow=14),
        "leg.L": dict(side=3), "leg.R": dict(side=3),
    },
    "contrapposto": {
        "body": dict(tilt=6), "torso": dict(side=-13, twist=-6, bend=0), "head": dict(tilt=6, turn=12, nod=2),
        "leg.L": dict(forward=-1, side=-2), "leg.R": dict(forward=16, side=8, knee=30, ankle=16, twist=12),
        "arm.L": dict(lift=9, forward=14, elbow=22, twist=10), "arm.R": dict(lift=10, forward=-8, elbow=28, twist=10),
        "hand.L": "graceful", "hand.R": "graceful",
    },
    "hand_on_hip": {
        "body": dict(tilt=-4), "torso": dict(side=8, twist=6), "head": dict(turn=-14, tilt=-3),
        "leg.L": dict(forward=10, side=9, knee=18, ankle=8, twist=14), "leg.R": dict(side=-1),
        "reach.L": dict(to="hip.L", elbow="back", lay=True), "hand.L": "relaxed",
        "arm.R": dict(lift=10, forward=8, elbow=12),
    },
    # men's standing poses
    "david": {     # Michelangelo's David: weight on the right leg, the left hand at the shoulder, gaze to the side
        "body": dict(tilt=-3), "torso": dict(side=-6, twist=-8), "head": dict(turn=35, tilt=3),
        "leg.L": dict(forward=8, side=12, knee=16, ankle=6, twist=14), "leg.R": dict(side=-2),
        "reach.L": dict(to="shoulder.L", elbow="down", offset=0.05), "hand.L": "grip",
        "arm.R": dict(lift=6, forward=4, elbow=16), "hand.R": "relaxed",
    },
    "heroic": {
        "torso": dict(bend=-5), "head": dict(nod=-5, turn=6), "reach.L": dict(to="hip.L", elbow="out"),
        "reach.R": dict(to="hip.R", elbow="out"), "hand.L": "fist", "hand.R": "fist",
        "leg.L": dict(side=11), "leg.R": dict(side=11),
    },
    "hands_in_pockets": {     # the palms sink below the skin so trousers hide the hands (meant for clothed figures)
        "torso": dict(side=3), "head": dict(turn=-10, tilt=2), "reach.L": dict(to="pocket.L", elbow="back", offset=-0.035),
        "reach.R": dict(to="pocket.R", elbow="back", offset=-0.035), "hand.L": "relaxed", "hand.R": "relaxed",
        "arm.L": dict(wrist_side=-50), "arm.R": dict(wrist_side=50),          # fingers point down into the pockets
        "leg.L": dict(forward=6, side=6, knee=10, twist=10), "leg.R": dict(side=3),
    },
    "arms_crossed": {
        "torso": dict(bend=-2), "head": dict(turn=8),
        "reach.L": dict(to="ribs.R", elbow="down", offset=0.10), "reach.R": dict(to="ribs.L", elbow="down", offset=0.05),
        "hand.L": "flat", "hand.R": "flat", "leg.L": dict(side=5), "leg.R": dict(side=5),
    },
    "hands_on_hips": {
        "torso": dict(bend=-3), "reach.L": dict(to="hip.L", elbow="back"), "reach.R": dict(to="hip.R", elbow="back"),
        "hand.L": "grip", "hand.R": "grip", "leg.L": dict(side=8), "leg.R": dict(side=8),
    },
    "hand_on_chest": {
        "head": dict(tilt=4), "reach.R": dict(to="heart", elbow="down", offset=0.03, lay=True), "hand.R": "flat",
        "arm.L": dict(lift=10, forward=8, elbow=14), "leg.L": dict(side=4), "leg.R": dict(side=4),
    },
    "hair_touch": {
        "head": dict(tilt=-8, turn=-10), "reach.R": dict(to="temple.R", elbow="out", offset=0.04), "hand.R": "graceful",
        "arm.L": dict(lift=10, forward=8, elbow=14), "leg.L": dict(side=3), "leg.R": dict(side=6, forward=8, knee=14, ankle=8),
    },
    "walk": {
        "torso": dict(twist=7, bend=3), "head": dict(turn=-3),
        "leg.L": dict(forward=24, side=2, knee=10, ankle=-6), "leg.R": dict(forward=-17, side=2, knee=24, ankle=24),
        "arm.L": dict(lift=18, forward=-70, elbow=22), "arm.R": dict(lift=20, forward=80, elbow=34),
    },
    "run": {
        "body": dict(lean=11), "torso": dict(twist=13, bend=4), "head": dict(nod=-8),
        "leg.L": dict(forward=58, knee=78, ankle=8), "leg.R": dict(forward=-24, knee=44, ankle=34),
        "arm.L": dict(lift=36, forward=-78, elbow=88), "arm.R": dict(lift=40, forward=84, elbow=96),
        "hand.L": "fist", "hand.R": "fist",
    },
    "arms_up": {
        "torso": dict(bend=-7), "head": dict(nod=-12),
        "arm.L": dict(lift=158, forward=30, elbow=22), "arm.R": dict(lift=150, forward=30, elbow=34),
        "hand.L": "open", "hand.R": "open", "leg.L": dict(side=4), "leg.R": dict(side=6, forward=6, knee=10),
    },
    "wave": {
        "body": dict(tilt=2), "head": dict(tilt=-5, turn=-6),
        "arm.R": dict(lift=118, forward=38, twist=-30, elbow=64), "hand.R": "open",
        "arm.L": dict(lift=10, forward=6, elbow=14), "leg.L": dict(side=4), "leg.R": dict(side=4),
    },
    "venus": {
        "body": dict(tilt=5), "torso": dict(side=-10, twist=-5, bend=4), "head": dict(tilt=8, turn=18, nod=6),
        "leg.L": dict(side=-2), "leg.R": dict(forward=14, side=4, knee=28, ankle=16, twist=6),
        "reach.R": dict(to="breast.L", elbow="down", offset=0.03), "hand.R": "graceful",
        "reach.L": dict(to="pelvis", elbow="out", offset=0.03), "hand.L": "graceful",
    },
    "thinking": {
        "torso": dict(bend=4, side=3), "head": dict(nod=8, tilt=-4, turn=-10),
        "reach.R": dict(to="chin", elbow="down", offset=0.03), "hand.R": "point",
        "reach.L": dict(to="ribs.R", elbow="down", offset=0.07), "hand.L": "flat",
        "leg.L": dict(side=4), "leg.R": dict(side=5, forward=6, knee=10),
    },
    "arms_behind_head": {
        "body": dict(tilt=6), "torso": dict(side=-13, bend=-8, twist=-5), "head": dict(tilt=6, turn=10, nod=-2),
        "leg.L": dict(forward=-1, side=-2), "leg.R": dict(forward=18, side=8, knee=34, ankle=18, twist=10),
        "reach.L": dict(to="nape", elbow="up", offset=0.05), "reach.R": dict(to="nape", elbow="up", offset=0.07),
        "hand.L": "relaxed", "hand.R": "relaxed",
    },
    "s_curve": {
        "body": dict(tilt=8), "torso": dict(side=-17, twist=-8, bend=-4), "head": dict(tilt=9, turn=16, nod=2),
        "leg.L": dict(forward=-2, side=-3), "leg.R": dict(forward=20, side=6, knee=38, ankle=22, twist=14),
        "reach.R": dict(to="nape", elbow="up", offset=0.06), "hand.R": "relaxed",
        "reach.L": dict(to="hip.L", elbow="back", offset=0.02), "hand.L": "graceful",
    },
    "look_over_shoulder": {      # meant to be seen from behind: use camera yaw 150..180
        "body": dict(tilt=6), "torso": dict(side=-12, twist=28), "head": dict(turn=62, tilt=-6, nod=4),
        "leg.L": dict(forward=-1, side=-2), "leg.R": dict(forward=14, side=8, knee=26, ankle=14, twist=10),
        "arm.L": dict(lift=12, forward=20, elbow=24), "reach.R": dict(to="hip.R", elbow="back"), "hand.R": "graceful",
    },
    "kneel_sit": {               # sitting back on the heels
        "torso": dict(bend=-2), "head": dict(tilt=5, turn=10),
        "leg.L": dict(forward=72, side=10, knee=152, ankle=62), "leg.R": dict(forward=72, side=10, knee=152, ankle=62),
        "reach.L": dict(to="thigh.L", elbow="out", offset=0.03), "reach.R": dict(to="thigh.R", elbow="out", offset=0.03),
        "hand.L": "flat", "hand.R": "flat",
    },
    "seated_side": {             # on the floor, leaning on the left hand, legs folded to the right
        "body": dict(tilt=44), "torso": dict(side=-38, twist=-8), "head": dict(tilt=-14, turn=-8, nod=2),
        "leg.L": dict(forward=62, side=0, knee=112, ankle=36), "leg.R": dict(forward=84, side=-8, knee=104, ankle=36),
        "arm.L": dict(lift=42, forward=0, twist=0, elbow=6, wrist=-60), "hand.L": "flat",
        "reach.R": dict(to="thigh.R", elbow="up", offset=0.03), "hand.R": "graceful",
    },
    "sit_chair": {
        "torso": dict(bend=4), "head": dict(nod=2),
        "leg.L": dict(forward=86, side=5, knee=88), "leg.R": dict(forward=86, side=5, knee=88),
        "arm.L": dict(lift=22, forward=52, elbow=58, twist=20), "arm.R": dict(lift=22, forward=52, elbow=58, twist=20),
    },
    "sit_crossed_legs": {
        "torso": dict(bend=6, twist=8), "head": dict(turn=-10),
        "leg.L": dict(forward=84, side=4, knee=86), "leg.R": dict(forward=98, side=-9, knee=74, ankle=18),
        "arm.L": dict(lift=20, forward=60, elbow=62, twist=30), "arm.R": dict(lift=24, forward=64, elbow=50, twist=34),
    },
    "sit_floor": {
        "body": dict(lean=-14), "torso": dict(bend=20), "head": dict(nod=-4),
        "leg.L": dict(forward=112, side=10, knee=118, ankle=4), "leg.R": dict(forward=106, side=12, knee=110, ankle=4),
        "arm.L": dict(lift=34, forward=78, elbow=44, twist=30), "arm.R": dict(lift=34, forward=78, elbow=44, twist=30),
        "hand.L": "grip", "hand.R": "grip",
    },
    "kneel": {
        "torso": dict(bend=2), "leg.L": dict(forward=2, side=6, knee=92, ankle=62), "leg.R": dict(forward=2, side=6, knee=92, ankle=62),
        "arm.L": dict(lift=14, forward=40, elbow=48, twist=28), "arm.R": dict(lift=14, forward=40, elbow=48, twist=28),
    },
    "recline": {      # lying on the figure's left side, hips and legs flat, upper body propped on the left forearm (odalisque)
        "body": dict(tilt=88), "torso": dict(side=-44, twist=-8), "head": dict(tilt=-28, turn=-6, nod=4),
        "leg.L": dict(forward=18, side=2, knee=30, ankle=30), "leg.R": dict(forward=40, side=-4, knee=60, ankle=30),
        "arm.L": dict(lift=64, forward=6, twist=10, elbow=96), "hand.L": "flat",
        "reach.R": dict(to="thigh.R", elbow="up", offset=0.03), "hand.R": "graceful",
    },
    "lie_back": {
        "body": dict(lean=-90), "head": dict(turn=20),
        "leg.L": dict(forward=4, side=5, ankle=30), "leg.R": dict(forward=24, side=6, knee=44, ankle=30),
        "arm.L": dict(lift=140, forward=-10, elbow=70), "arm.R": dict(lift=30, forward=0, elbow=20),
    },
    "jump": {                    # in mid-air: the lowest point floats this far above the ground
        "airborne": 0.30,
        "body": dict(lean=-4), "torso": dict(bend=-12), "head": dict(nod=-14),
        "leg.L": dict(forward=34, side=8, knee=96, ankle=34), "leg.R": dict(forward=-22, side=6, knee=70, ankle=38),
        "arm.L": dict(lift=150, forward=10, elbow=20), "arm.R": dict(lift=140, forward=20, elbow=30),
        "hand.L": "open", "hand.R": "open",
    },
    "fight_stance": {
        "body": dict(turn=-28, lean=6), "torso": dict(twist=18, bend=6), "head": dict(turn=20, nod=6),
        "leg.L": dict(forward=28, side=10, knee=36, ankle=-4), "leg.R": dict(forward=-16, side=14, knee=30, ankle=16, twist=30),
        "arm.L": dict(lift=62, forward=74, elbow=92, twist=-20), "arm.R": dict(lift=34, forward=44, elbow=128, twist=-12),
        "hand.L": "fist", "hand.R": "fist",
    },
    "point_forward": {
        "torso": dict(twist=-10), "head": dict(turn=4),
        "arm.R": dict(lift=88, forward=84, elbow=6), "hand.R": "point",
        "arm.L": dict(lift=12, forward=-6, elbow=18), "leg.L": dict(side=6), "leg.R": dict(side=6, forward=8, knee=8),
    },
    "reach_up": {
        "torso": dict(side=7, bend=-5), "head": dict(nod=-22, turn=-10),
        "arm.R": dict(lift=172, forward=40, elbow=6), "hand.R": "open",
        "arm.L": dict(lift=20, forward=-14, elbow=12), "leg.L": dict(side=4, ankle=24), "leg.R": dict(side=4, ankle=24),
    },
    "pray": {                    # palms pressed together before the breastbone, fingers up, elbows out
        "head": dict(nod=14), "hand.L": "flat", "hand.R": "flat",
        # the targets cross the midline: with the wrists bent back the palms then meet in the middle
        "reach.L": dict(to=[-0.05, -0.26, 0.43], elbow="out"), "reach.R": dict(to=[0.05, -0.26, 0.43], elbow="out"),
        "arm.L": dict(wrist=-85), "arm.R": dict(wrist=-85),
    },
    "read_book": {               # standing, an open book held in both hands: add_prop("book", held_by="<name>:hands", open=True)
        "torso": dict(bend=6), "head": dict(nod=26), "hand.L": "relaxed", "hand.R": "relaxed",
        "reach.L": dict(to=READ_HOLD_L, elbow="down"), "reach.R": dict(to=READ_HOLD_R, elbow="down"),
        "arm.L": dict(forearm_twist=60), "arm.R": dict(forearm_twist=60), "leg.L": dict(side=4), "leg.R": dict(side=4),
    },
    "hold_cup": {                # a cup raised in the right hand: add_prop("mug", held_by="<name>:hand.R")
        "head": dict(nod=6), "arm.L": dict(lift=9, forward=10, elbow=14), "leg.L": dict(side=3), "leg.R": dict(side=3),
        "reach.R": dict(to=[-0.06, -0.30, 0.50], elbow="down"), "hand.R": "grip",
    },
    "look_at_phone": {           # a phone on the upturned right palm: add_prop("phone", held_by="<name>:hand.R")
        "head": dict(nod=24), "arm.L": dict(lift=9, forward=10, elbow=14), "leg.L": dict(side=3), "leg.R": dict(side=3),
        "reach.R": dict(to=[-0.04, -0.33, 0.40], elbow="down"), "arm.R": dict(forearm_twist=110, wrist=-10),
        "hand.R": "flat",           # open fingers: a curled hand hides the phone
    },
    "smoke": {                   # a cigarette held low in the right hand, head down: add_prop("cigarette", held_by="<name>:hand.R")
        "head": dict(nod=16, turn=-8), "torso": dict(bend=4), "leg.L": dict(side=4), "leg.R": dict(side=6, forward=6, knee=6),
        "arm.L": dict(lift=8, forward=6, elbow=10), "arm.R": dict(lift=12, forward=24, elbow=58, forearm_twist=40),
        "hand.R": "cigarette", "hand.L": "relaxed",
    },
    "smoke_inhale": {            # between drags: the right hand up beside the jaw, the face left clear
        "head": dict(nod=-2, turn=10), "leg.L": dict(side=4), "leg.R": dict(side=6, forward=6, knee=6),
        "arm.L": dict(lift=8, forward=6, elbow=10),
        "reach.R": dict(to=[-0.13, -0.20, 0.70], elbow="down"), "arm.R": dict(forearm_twist=-30),
        "hand.R": "cigarette", "hand.L": "relaxed",
    },
    "sit_smoke": {               # seated, elbows on the knees, a cigarette in the right hand hanging between them
        "torso": dict(bend=22), "head": dict(nod=6, turn=-6),
        "leg.L": dict(forward=86, side=8, knee=92), "leg.R": dict(forward=86, side=10, knee=90),
        "reach.R": dict(to="knee.L", elbow="out", offset=0.10), "arm.R": dict(forearm_twist=30), "hand.R": "cigarette",
        "reach.L": dict(to="knee.L", elbow="out", offset=0.02), "hand.L": "relaxed",
    },
    "read_seated": {             # the same on a chair (sit_chair legs)
        "torso": dict(bend=8), "head": dict(nod=28), "hand.L": "relaxed", "hand.R": "relaxed",
        "leg.L": dict(forward=86, side=5, knee=88), "leg.R": dict(forward=86, side=5, knee=88),
        "reach.L": dict(to=READ_SEATED_L, elbow="down"), "reach.R": dict(to=READ_SEATED_R, elbow="down"),
        "arm.L": dict(forearm_twist=60), "arm.R": dict(forearm_twist=60),
    },
}
