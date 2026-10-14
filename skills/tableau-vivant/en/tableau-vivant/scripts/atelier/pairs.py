"""Two-person poses: holding hands, a hand on the shoulder, an arm around, a hug, a dance hold.

A pair is laid out around a centre point (figure a on the left as seen from the default camera, b on the
right), both bodies are posed once without contact, and then each touching hand is solved toward a point
on the other body. Each kind returns the extra pose entries for a and b; anything the user gave for a
figure's pose (a walk, a head turn) is kept unless the contact needs that arm.
"""
import numpy as np

# kind -> layout: (distance between the two pelvises in m, facing of a, facing of b, default body pose)
LAYOUTS = {
    "hold_hands": (0.56, 6.0, -6.0, "stand"),
    "hand_on_shoulder": (0.52, 10.0, -5.0, "stand"),
    "arm_around": (0.44, 0.0, 0.0, "stand"),
    "hug": (0.34, 90.0, -90.0, "stand"),
    "dance": (0.44, 90.0, -90.0, "stand"),
}
HELD_HANDS_DROP = 0.06           # clasped hands hang a little below the hips
HELD_HANDS_FORWARD = 0.07
DANCE_HANDS_OUT, DANCE_HANDS_DROP = 0.30, 0.05   # the joined hands of a dance hold, out to the side of the couple
# in a closed hold each partner looks past the other's right shoulder; smaller turns put the two faces together
DANCE_HEAD_TURN_A, DANCE_HEAD_TURN_B = 40.0, 50.0
CONTACT_OFFSET = 0.03            # a resting palm stops this far off the other body's skin
WRAP_ACROSS = 0.03               # an embracing palm rests this far from the partner's spine, on the holder's side
WRAP_ELBOW_BACK, WRAP_ELBOW_OUT, WRAP_ELBOW_DOWN = 1.0, 0.8, 0.3   # elbow direction of an arm round a partner's back
SHOULDER_INSET = 0.35           # share of the way from the outer shoulder toward the nape
SHOULDER_FRONT = 0.025          # a hand resting on a shoulder lies this far toward its front, where it shows
FINGER_DRAPE = 0.5              # fingers over a shoulder run forward and this much downward
WAIST_FINGER_DROP = 0.3         # fingers round a partner's waist run forward and this much downward


def layout(kind, at=(0.0, 0.0), facing=0.0, distance=None):
    """World positions and facings of a and b for a pair kind, turned by `facing` about the centre `at`."""
    if kind not in LAYOUTS:
        raise KeyError(f"unknown pair '{kind}'. Available: {sorted(LAYOUTS)}")
    d, face_a, face_b, _ = LAYOUTS[kind]
    d = d if distance is None else float(distance)
    angle = np.radians(facing)
    turn = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    centre = np.asarray(at, float)[:2]
    pos_a, pos_b = centre + turn @ [-d / 2, 0.0], centre + turn @ [d / 2, 0.0]
    return (pos_a, facing + face_a), (pos_b, facing + face_b)


def default_pose(kind):
    return LAYOUTS[kind][3]


def _reach(point, elbow="down", offset=0.0, normal=None, fingers=None):
    """Reach entry aiming at a scene point. normal: the partner's skin direction there; the palm is then laid
    flat on it (facing the other way) instead of hanging off the end of the forearm. fingers: the way the
    fingers should run along that skin (otherwise they follow the forearm)."""
    entry = {"world": [float(v) for v in point], "offset": offset}
    if normal is not None:
        entry["palm_world"] = [-float(v) for v in normal]
        if fingers is not None:
            entry["fingers_world"] = [float(v) for v in fingers]
    if isinstance(elbow, str):
        entry["elbow"] = elbow
    else:                                 # a direction in scene axes
        entry["elbow_world"] = [float(v) for v in elbow]
    return entry


def _axes(figure):
    """World directions of a figure: forward (where it faces), left (its own left), up."""
    turn = figure.world[:3, :3]
    return turn @ [0.0, -1.0, 0.0], turn @ [1.0, 0.0, 0.0], np.array([0.0, 0.0, 1.0])


def _wrap(holder_side, partner, height_landmark, drop=0.0, across=WRAP_ACROSS):
    """Where a hand rests when an arm goes round a partner's back, and which way the elbow points.

    The palm lies just off the partner's spine on the holder's side, the elbow out at the partner's flank,
    so the forearm runs across the back the way it does in a real embrace."""
    forward_p, _, up = _axes(partner)
    point = partner.landmark(height_landmark, CONTACT_OFFSET) + holder_side * across - up * drop
    elbow = -forward_p * WRAP_ELBOW_BACK + holder_side * WRAP_ELBOW_OUT - up * WRAP_ELBOW_DOWN
    return point, elbow, partner.surface_normal(height_landmark)


def _on_shoulder(partner, landmark, toward):
    """Where a resting hand lies on a partner's shoulder top, the skin direction there and the finger line.

    toward: +1 drapes the fingers over the front of the shoulder (a hand from beside or behind),
    -1 points them back over it (a hand from in front, as in a dance hold: the arm rises to the shoulder, and a
    wrist cannot fold far enough to hang the fingers down the back)."""
    forward_p, _, up = _axes(partner)
    point = partner.landmark(landmark, CONTACT_OFFSET) + forward_p * toward * SHOULDER_FRONT
    return point, partner.surface_normal(landmark), forward_p * toward - up * (FINGER_DRAPE if toward > 0 else 0.0)


def contacts(kind, fa, fb, facing=0.0):
    """Pose entries for a and b, from the provisional (contact-free) bodies fa and fb."""
    angle = np.radians(facing)
    forward = np.array([np.sin(angle), -np.cos(angle), 0.0])        # toward the default camera, turned with the pair
    _, left_a, _ = _axes(fa)
    _, left_b, _ = _axes(fb)
    if kind == "hold_hands":
        meet = (fa.landmark("hip.L") + fb.landmark("hip.R")) / 2 + forward * HELD_HANDS_FORWARD - [0, 0, HELD_HANDS_DROP]
        return ({"reach.L": _reach(meet), "hand.L": "grip"},
                {"reach.R": _reach(meet), "hand.R": "grip"})
    if kind == "hand_on_shoulder":
        point, normal, fingers = _on_shoulder(fb, "shoulder_top.R", 1)
        return ({"reach.L": _reach(point, "back", normal=normal, fingers=fingers), "hand.L": "flat", "head": {"turn": 12}}, {})
    if kind == "arm_around":
        # the hand cups the far shoulder from above, a little in from its outer edge so the fingers stay on it
        far = fb.landmark("shoulder.L", CONTACT_OFFSET + 0.01) * (1 - SHOULDER_INSET) + fb.landmark("nape", CONTACT_OFFSET) * SHOULDER_INSET
        far_normal = fb.surface_normal("shoulder.L") * (1 - SHOULDER_INSET) + fb.surface_normal("nape") * SHOULDER_INSET
        forward_a, _, up = _axes(fa)
        forward_b, _, _ = _axes(fb)
        return ({"reach.L": _reach(far, "back", normal=far_normal, fingers=forward_b - up * FINGER_DRAPE), "hand.L": "relaxed",
                 "head": {"turn": 10}},
                {"reach.R": _reach(fa.landmark("waist.R", CONTACT_OFFSET), "back", normal=fa.surface_normal("waist.R"),
                                   fingers=forward_a - up * WAIST_FINGER_DROP),
                 "hand.R": "flat", "head": {"turn": -10, "tilt": 6}})
    if kind == "hug":
        # a's arms go round b's shoulders, b's round a's waist, so the two pairs of arms do not cross;
        # heads pass on opposite sides (each to its own right), as they do in an embrace
        a_left, a_left_elbow, a_left_n = _wrap(left_a, fb, "spine_upper")
        a_right, a_right_elbow, a_right_n = _wrap(-left_a, fb, "spine_upper", drop=0.06)
        b_left, b_left_elbow, b_left_n = _wrap(left_b, fa, "spine_lower")
        b_right, b_right_elbow, b_right_n = _wrap(-left_b, fa, "spine_lower", drop=0.05)
        return ({"reach.L": _reach(a_left, a_left_elbow, normal=a_left_n), "reach.R": _reach(a_right, a_right_elbow, normal=a_right_n),
                 "hand.L": "flat", "hand.R": "flat", "head": {"turn": -30, "tilt": -8}, "torso": {"bend": 5}},
                {"reach.L": _reach(b_left, b_left_elbow, normal=b_left_n), "reach.R": _reach(b_right, b_right_elbow, normal=b_right_n),
                 "hand.L": "flat", "hand.R": "flat", "head": {"turn": -30, "tilt": -8}, "torso": {"bend": 5}})
    if kind == "dance":
        # closed hold: a's right hand on b's shoulder blade, b's left hand on a's shoulder, the other hands joined out wide
        side = fa.landmark("shoulder.L") - fa.landmark("shoulder.R")
        side /= np.linalg.norm(side) + 1e-12
        joined = (fa.landmark("shoulder.L") + fb.landmark("shoulder.R")) / 2 + side * DANCE_HANDS_OUT - [0, 0, DANCE_HANDS_DROP]
        blade, blade_elbow, blade_normal = _wrap(-left_a, fb, "spine_upper", across=WRAP_ACROSS * 2)
        shoulder, shoulder_normal, drape = _on_shoulder(fa, "shoulder_top.R", -1)
        return ({"reach.R": _reach(blade, blade_elbow, normal=blade_normal), "hand.R": "flat",
                 "reach.L": _reach(joined), "hand.L": "grip", "head": {"turn": DANCE_HEAD_TURN_A, "tilt": -4}},
                {"reach.L": _reach(shoulder, "out", normal=shoulder_normal), "hand.L": "flat",
                 "reach.R": _reach(joined), "hand.R": "grip", "head": {"turn": DANCE_HEAD_TURN_B, "tilt": -12, "nod": -8}})
    raise KeyError(f"unknown pair '{kind}'")


CHAIN_KINDS = ("hold_hands", "arm_around", "hand_on_shoulder")   # contacts that link a row of people one to the next


def row(count, kind, at=(0.0, 0.0), facing=0.0, spacing=None):
    """Ground positions of `count` people in a row, left to right as seen from the default camera."""
    if kind not in CHAIN_KINDS:
        raise KeyError(f"unknown group '{kind}'. Available: {list(CHAIN_KINDS)}")
    d = LAYOUTS[kind][0] if spacing is None else float(spacing)
    angle = np.radians(facing)
    across = np.array([np.cos(angle), np.sin(angle)])
    centre = np.asarray(at, float)[:2]
    return [centre + across * d * (i - (count - 1) / 2) for i in range(count)]


def chain_contacts(kind, bodies, facing=0.0):
    """Pose entries per person of a row linked neighbour to neighbour, each pair touching as a and b of `kind`.

    A person's left arm reaches the neighbour on the right and the right arm the neighbour on the left, so the
    two contacts of a person in the middle never need the same arm. That person looks ahead: the two contacts
    would turn the head opposite ways."""
    entries = [dict() for _ in bodies]
    for i in range(len(bodies) - 1):
        left, right = contacts(kind, bodies[i], bodies[i + 1], facing)
        entries[i].update(left)
        entries[i + 1].update(right)
    for middle in entries[1:-1]:
        middle.pop("head", None)
    return entries


def merge_pose(user_pose, kind, contact):
    """User pose (name or dict) + contact entries. Contact wins for the arms it uses; user head/torso settings win."""
    spec = {"preset": user_pose} if isinstance(user_pose, str) else dict(user_pose or {"preset": default_pose(kind)})
    spec.setdefault("preset", default_pose(kind))
    for key, value in contact.items():
        if key in ("head", "torso") and key in spec:
            continue
        spec[key] = value
        if key.startswith("reach."):
            spec.pop("arm." + key.split(".")[1], None)
    return spec
