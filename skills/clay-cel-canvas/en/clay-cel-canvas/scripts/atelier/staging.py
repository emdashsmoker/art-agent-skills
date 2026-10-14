"""Staging a figure: ready-made poses and a camera that frames the shot.

Poses are written for the female mannequin in metres (floor at z = 0, the
figure facing the viewer along -y) and scaled to any other physique by its leg
length, so the same pose fits a man or a woman. A pose may need something to
rest on (a seat, a wall, a bed); it lists those as supports with a role, and
the scene decides what they look like.

frame() places the camera for a shot (full, knee, waist, bust) from a view
direction (azimuth around the figure, elevation above it).
"""
from dataclasses import dataclass, replace

import numpy as np

from .camera import Camera
from .mannequin import FEMALE, Pose, Reach
from .sculpt import RoundBox, facing, rotation

BASE_LEG = FEMALE.thigh + FEMALE.shin       # the poses below are written for this leg length
ANIME_HEAD = 1.1                            # painted heads are drawn this much larger than the skull
HAIR_MARGIN = 0.05                          # metres of hair above the crown
SHOTS = {                                   # lowest landmark each shot keeps in frame
    "full": ("left_ankle", "right_ankle"),
    "knee": ("left_knee", "right_knee"),
    "waist": ("pelvis",),
    "bust": ("chest",),
}
FRAME_MARGIN = 0.08                         # share of the canvas left empty around the subject
FOOT_ROOM = 0.10                            # metres below the ankles kept in a full shot (feet, shoes)
CUT_ROOM = 0.06                             # metres below the lowest landmark of a cropped shot


@dataclass(frozen=True)
class Staging:
    """A pose and what it needs: supports are (role, shape) with role "seat",
    "wall", "bed" or "ground"; hand_at rests hands on landmarks after a first build."""
    pose: Pose
    supports: tuple = ()
    hand_at: tuple = ()
    hand_behind_head: str = ""


def _hang(side, x=0.205, y=0.0, z=0.855, curl=0.3):
    """A relaxed arm hanging at the side, palm toward the thigh."""
    return Reach((side * x, y, z), (0.1, 1, 0), (side * 0.05, -0.1, -1), (side * 1, 0.1, 0), curl)


def _stand_feet(spread=0.0):
    return (Reach((0.12 + spread, -0.07, 0.092), (-0.2, -1, 0.1), (0.3, -1, 0), (0, 0, 1), 0.15),
            Reach((-0.08 - spread, 0.0, 0.081), (0, -1, 0), (-0.3, -1, 0), (0, 0, 1), 0.0))


def standing():
    left_foot, right_foot = _stand_feet()
    return Staging(Pose(
        pelvis=(-0.02, 0.0, 0.872),
        pelvis_frame=rotation(8, 0, 5), chest_frame=rotation(4, 2, -3), head_frame=rotation(0, 3, 3),
        left_hand=_hang(1, 0.215, 0.02, 0.86), right_hand=_hang(-1, 0.225, 0.0, 0.85),
        left_foot=left_foot, right_foot=right_foot))


def hand_on_hip():
    """Weight on the right leg, the left hand on the hip with the elbow out."""
    left_foot, right_foot = _stand_feet(0.02)
    return Staging(Pose(
        pelvis=(-0.03, 0.0, 0.870),
        pelvis_frame=rotation(10, 0, 8), chest_frame=rotation(6, 2, -5), head_frame=rotation(-6, 4, 6),
        left_hand=Reach((0.205, 0.0, 0.985), (1, 0.5, 0.1), (-0.35, -0.5, -0.8), (0.9, 0.1, 0.4), 0.35),
        right_hand=_hang(-1, 0.225, 0.0, 0.85),
        left_foot=left_foot, right_foot=right_foot))


def walking():
    """Mid-stride: the left foot forward on its heel, the right pushing off its toes;
    arms swing against the legs and the chest turns against the hips."""
    return Staging(Pose(
        pelvis=(0.0, 0.0, 0.855),
        pelvis_frame=rotation(-8, 0, 2), chest_frame=rotation(8, 4, -2), head_frame=rotation(0, 2, 0),
        left_hand=Reach((0.19, 0.17, 0.87), (0.1, 1, -0.3), (0.0, 0.3, -1), (1, -0.1, 0), 0.35),
        right_hand=Reach((-0.17, -0.15, 0.89), (0.0, 1, 0.2), (0.1, -0.4, -1), (-1, 0, 0), 0.4),
        left_foot=Reach((0.09, -0.28, 0.085), (0.0, -1, 0.1), (0.1, -1, 0.25), (0, 0.25, 1), 0.0),
        right_foot=Reach((-0.09, 0.26, 0.135), (0.0, -1, -0.2), (-0.05, -1, -0.5), (0, -0.45, 0.9), 0.55)))


def arms_crossed():
    """Standing, forearms folded across the body below the chest."""
    left_foot, right_foot = _stand_feet()
    return Staging(Pose(
        pelvis=(-0.02, 0.0, 0.872),
        pelvis_frame=rotation(6, 0, 4), chest_frame=rotation(2, 0, -3), head_frame=rotation(4, 5, 4),
        # Each hand tucks behind the opposite upper arm, so no fingers stick out at the sides.
        # Elbows come forward, so the forearms lie across the body instead of pointing at the viewer.
        left_hand=Reach((-0.12, -0.170, 1.10), (0.45, -0.45, -0.75), (-0.4, 0.9, 0.0), (-1, 0, 0.2), 0.45),
        right_hand=Reach((0.13, -0.155, 1.09), (-0.45, -0.45, -0.75), (0.4, 0.9, 0.0), (1, 0, 0.2), 0.45),
        left_foot=left_foot, right_foot=right_foot))


def seated_chair():
    """Upright on a chair, thighs level, feet flat, hands resting on the thighs."""
    return Staging(Pose(
        pelvis=(0.0, 0.06, 0.535),
        pelvis_frame=rotation(0, -6, 0), chest_frame=rotation(0, 2, 0), head_frame=rotation(0, 4, 3),
        left_hand=Reach((0.12, -0.24, 0.585), (0.6, 0.6, -0.2), (-0.1, -1, -0.45), (0.1, -0.2, 1), 0.3),
        right_hand=Reach((-0.12, -0.24, 0.585), (-0.6, 0.6, -0.2), (0.1, -1, -0.45), (-0.1, -0.2, 1), 0.3),
        left_foot=Reach((0.12, -0.40, 0.086), (0.1, -1, 0.2), (0.15, -1, 0), (0, 0, 1), 0.0),
        right_foot=Reach((-0.12, -0.38, 0.086), (-0.1, -1, 0.2), (-0.15, -1, 0), (0, 0, 1), 0.0)),
        supports=(("seat", RoundBox((0.0, 0.08, 0.215), (0.23, 0.22, 0.215), 0.03)),
                  ("seat", RoundBox((0.0, 0.29, 0.72), (0.23, 0.025, 0.28), 0.02))))


def leaning_wall():
    """Back against a wall, one foot set flat on it behind, hands at the sides."""
    return Staging(Pose(
        pelvis=(0.0, 0.095, 0.850),
        pelvis_frame=rotation(4, -5, 3), chest_frame=rotation(0, -6, -2), head_frame=rotation(-8, 6, 5),
        left_hand=Reach((0.215, 0.12, 0.82), (0.1, 1, 0), (0.05, 0.1, -1), (1, 0.2, 0), 0.3),
        right_hand=Reach((-0.215, 0.12, 0.83), (-0.1, 1, 0), (-0.05, 0.1, -1), (-1, 0.2, 0), 0.3),
        left_foot=Reach((0.10, 0.155, 0.40), (0.0, -1, 0.2), (0.05, 0.3, -1), (0, -1, 0.05), 0.2),
        right_foot=Reach((-0.07, -0.12, 0.081), (0, -1, 0), (-0.25, -1, 0), (0, 0, 1), 0.0)),
        # A pier, narrower than the picture, so the place still shows beside it.
        supports=(("wall", RoundBox((0.0, 0.33, 1.25), (0.5, 0.08, 1.25), 0.01)),))


def seated_ground():
    """Sitting on the ground, knees up, leaning back on straight arms."""
    return Staging(Pose(
        pelvis=(0.0, 0.05, 0.115),
        pelvis_frame=rotation(0, -32, 0), chest_frame=rotation(0, -18, 0), head_frame=rotation(0, 12, 4),
        left_hand=Reach((0.21, 0.34, 0.09), (0.0, -1, 0), (0.2, 0.6, -0.1), (0, 0, 1), 0.1),
        right_hand=Reach((-0.21, 0.34, 0.09), (0.0, -1, 0), (-0.2, 0.6, -0.1), (0, 0, 1), 0.1),
        left_foot=Reach((0.14, -0.46, 0.08), (0.2, -1, 0.9), (0.2, -1, 0), (0, 0, 1), 0.1),
        right_foot=Reach((-0.10, -0.50, 0.08), (-0.2, -1, 0.9), (-0.2, -1, 0), (0, 0, 1), 0.1)),
        supports=(("ground", RoundBox((0, 0.3, -0.05), (2.5, 2.0, 0.05), 0.01)),))


def reclining():
    """Lying on the side across a bed, propped on one arm, the other hand on the hip."""
    return Staging(Pose(
        pelvis=(0.10, 0.18, 0.60),
        pelvis_frame=facing(up=(-1, 0, 0.10), front=(0, -0.9, 0.45)),
        chest_frame=facing(up=(-0.88, 0.04, 0.47), front=(0.05, -0.92, 0.38)),
        head_frame=facing(up=(-0.30, 0.08, 0.95), front=(0.2, -0.97, 0.05)),
        left_hand=Reach((0.08, -0.06, 0.77), (0, 0.5, 1), (1, -0.2, -0.3), (0, -0.5, 0.85), 0.2),
        right_hand=Reach((-0.62, 0.22, 0.95), (-1, 0.2, -0.4), (0.5, 0.4, -0.7), (-0.6, 0.8, 0), 0.4),
        left_foot=Reach((0.82, 0.05, 0.52), (0.2, -1, 0.6), (1, -0.1, -0.2), (0, -0.8, 0.6), 0.6),
        right_foot=Reach((0.91, 0.15, 0.50), (0.0, -1, 0.3), (1, 0, -0.1), (0, -1, 0.3), 0.5)),
        supports=(("bed", RoundBox((0.05, 0.25, 0.22), (1.15, 0.45, 0.22), 0.08)),),
        hand_behind_head="right")


def _chair():
    """Seat and backrest of a chair whose seat top is at 0.43 m: what seated poses rest on."""
    return (("seat", RoundBox((0.0, 0.08, 0.215), (0.23, 0.22, 0.215), 0.03)),
            ("seat", RoundBox((0.0, 0.29, 0.72), (0.23, 0.025, 0.28), 0.02)))


def seated_crossed():
    """On a chair, the right leg crossed over the left knee, the left hand resting on the
    crossed knee, the right hand in the lap; the chest turns a little toward the crossed leg.
    The crossed shin hangs forward of the planted one, so the two calves do not meet, and
    slants out to the side: hanging straight it hides behind the planted shin from the
    front and the two feet stack like one leg."""
    return Staging(Pose(
        pelvis=(0.0, 0.06, 0.535),
        pelvis_frame=rotation(0, -6, 0), chest_frame=rotation(-6, 4, 0), head_frame=rotation(8, 4, 3),
        left_hand=Reach((0.03, -0.26, 0.66), (1, 0.3, -0.3), (0.2, -1, -0.3), (0, 0.2, 1), 0.3),
        right_hand=Reach((-0.04, -0.15, 0.64), (-1, 0.3, -0.4), (0.5, -0.8, -0.2), (0, 0, 1), 0.3),
        left_foot=Reach((0.10, -0.42, 0.086), (0.1, -1, 0.2), (0.15, -1, 0), (0, 0, 1), 0.0),
        right_foot=Reach((0.25, -0.54, 0.29), (0.35, -0.5, 0.8), (0.3, -0.55, -0.75), (0.15, -0.75, 0.6), 0.45)),
        supports=_chair())


def waving():
    """Standing, the right hand raised beside the head and waving, palm to the viewer,
    elbow out to the side; the head tips toward it."""
    left_foot, right_foot = _stand_feet()
    return Staging(Pose(
        pelvis=(-0.02, 0.0, 0.872),
        pelvis_frame=rotation(8, 0, 5), chest_frame=rotation(4, 2, -3), head_frame=rotation(-4, 3, 5),
        left_hand=_hang(1, 0.215, 0.02, 0.86),
        right_hand=Reach((-0.36, -0.05, 1.56), (-1, 0.3, -0.5), (0.1, 0, 1), (0.05, 1, 0), 0.1),
        left_foot=left_foot, right_foot=right_foot))


POSES = {"standing": standing, "hand_on_hip": hand_on_hip, "walking": walking, "arms_crossed": arms_crossed,
         "seated_chair": seated_chair, "leaning_wall": leaning_wall, "seated_ground": seated_ground,
         "reclining": reclining, "seated_crossed": seated_crossed, "waving": waving}


def _scaled_box(box, k):
    return RoundBox(box.center * k, box.half * k, box.rounding * k, box.rotation)


def _scaled_reach(reach, k):
    return replace(reach, target=tuple(np.asarray(reach.target, float) * k))


def pose_for(name, physique, bust=1.0):
    """A named pose fitted to a physique: positions scale with the leg length."""
    staging = POSES[name]()
    k = (physique.thigh + physique.shin) / BASE_LEG
    pose = staging.pose
    pose = replace(pose, pelvis=tuple(np.asarray(pose.pelvis, float) * k), bust=bust,
                   **{limb: _scaled_reach(getattr(pose, limb), k)
                      for limb in ("left_hand", "right_hand", "left_foot", "right_foot")})
    supports = tuple((role, _scaled_box(shape, k)) for role, shape in staging.supports)
    return replace(staging, pose=pose, supports=supports)


def placed(staging, offset=(0.0, 0.0, 0.0), turn=0.0):
    """A staging turned about the vertical by `turn` degrees (positive turns the front
    toward the viewer's right), then moved by `offset`: where one of two people stands."""
    spin = rotation(turn)
    offset = np.asarray(offset, float)

    def point(value):
        return tuple(spin @ np.asarray(value, float) + offset)

    def reach(value):
        return replace(value, target=point(value.target), bend=tuple(spin @ np.asarray(value.bend, float)),
                       forward=tuple(spin @ np.asarray(value.forward, float)),
                       back=tuple(spin @ np.asarray(value.back, float)))

    pose = staging.pose
    limbs = {limb: reach(getattr(pose, limb)) for limb in ("left_hand", "right_hand", "left_foot", "right_foot")}
    pose = replace(pose, pelvis=point(pose.pelvis), pelvis_frame=spin @ pose.pelvis_frame,
                   chest_frame=spin @ pose.chest_frame, head_frame=spin @ pose.head_frame, **limbs)
    supports = tuple((role, RoundBox(spin @ box.center + offset, box.half, box.rounding, spin @ box.rotation))
                     for role, box in staging.supports)
    hand_at = tuple((hand, landmark, tuple(spin @ np.asarray(shift, float)))
                    for hand, landmark, shift in staging.hand_at)
    return replace(staging, pose=pose, supports=supports, hand_at=hand_at)


def _joined_hands(first, second, meeting):
    """The first person's left hand and the second's right hand meet at one point, palms together."""
    left = Reach(meeting + np.array([-0.012, 0, 0]), (0.2, 1, 0), (0.1, -0.2, -1), (-1, 0.1, 0), 0.55)
    right = Reach(meeting + np.array([0.012, 0, 0]), (-0.2, 1, 0), (-0.1, -0.2, -1), (1, 0.1, 0), 0.55)
    return (replace(first, pose=replace(first.pose, left_hand=left)),
            replace(second, pose=replace(second.pose, right_hand=right)))


PAIR_GAP = 0.62          # metres between two people standing side by side, pelvis to pelvis


def pair_for(name, physique_a, physique_b, bust_a=1.0, bust_b=1.0):
    """Two people posed together; the first stands on the viewer's left.

    side_by_side: both stand, turned a little toward each other.
    holding_hands: side by side, the inner hands joined between them, heads turned in.
    facing: turned toward each other in conversation.
    """
    if name == "side_by_side":
        a, b = pose_for("standing", physique_a, bust_a), pose_for("hand_on_hip", physique_b, bust_b)
        return placed(a, (-PAIR_GAP / 2, 0, 0), 12.0), placed(b, (PAIR_GAP / 2, 0, 0), -12.0)
    if name == "holding_hands":
        a, b = pose_for("standing", physique_a, bust_a), pose_for("standing", physique_b, bust_b)
        a = replace(a, pose=replace(a.pose, head_frame=rotation(22, 4, 3)))
        b = replace(b, pose=replace(b.pose, head_frame=rotation(-22, 2, -2)))
        a, b = placed(a, (-PAIR_GAP / 2, 0, 0), 6.0), placed(b, (PAIR_GAP / 2, 0, 0), -6.0)
        height = min(physique_a.thigh + physique_a.shin, physique_b.thigh + physique_b.shin) / BASE_LEG * 0.86
        return _joined_hands(a, b, np.array([0.0, -0.06, height]))
    if name == "facing":
        a, b = pose_for("standing", physique_a, bust_a), pose_for("arms_crossed", physique_b, bust_b)
        return placed(a, (-0.30, 0.0, 0), 32.0), placed(b, (0.30, 0.05, 0), -32.0)
    raise ValueError(f"unknown pair pose {name!r}; choose from {PAIRS}")


PAIRS = ("side_by_side", "holding_hands", "facing")


def _view(azimuth, elevation):
    """Unit direction from the subject toward the camera: azimuth 0 is straight in
    front, positive moves the camera to the figure's left (the viewer's right)."""
    a, e = np.radians(azimuth), np.radians(elevation)
    return np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])


def frame(marks, physique, shot="full", azimuth=0.0, elevation=5.0, distance=4.5, aspect=1.6,
          margin=FRAME_MARGIN):
    """Camera that fits the shot on a 1000-unit-wide canvas of the given aspect.

    The crown of the painted head is the top; the shot's lowest landmark (plus
    room for feet or a clean cut) is the bottom; hands, elbows and knees keep
    the sides in frame. marks and physique may be lists: everyone in a group shot.
    """
    group = list(zip(marks, physique)) if isinstance(marks, (list, tuple)) else [(marks, physique)]
    names = ("skull", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist",
             "right_wrist", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")
    floor_room = FOOT_ROOM if shot == "full" else CUT_ROOM
    lowest = min(person[name][2] for person, _ in group for name in SHOTS[shot])
    points = []
    for person, body in group:
        crown = person["chin"] + person["head_up"] * (body.head_length * ANIME_HEAD + HAIR_MARGIN)
        points += [p for p in [crown] + [person[name] for name in names] if p[2] >= lowest - 1e-6]
        points += [np.array(person[name]) - (0, 0, floor_room) for name in SHOTS[shot]]
    points = np.array(points)
    centre = (points.min(axis=0) + points.max(axis=0)) / 2
    eye = centre + _view(azimuth, elevation) * distance
    width, height = 1000.0, 1000.0 * aspect
    probe = Camera(eye, centre, 1.0, (0.0, 0.0))
    spread = probe.project(points)
    low, high = spread.min(axis=0), spread.max(axis=0)
    focal = min(width * (1 - 2 * margin) / (high[0] - low[0]),
                height * (1 - 2 * margin) / (high[1] - low[1]))
    middle = (low + high) / 2 * focal
    return Camera(eye, centre, focal, (width / 2 - middle[0], height / 2 - middle[1]))


__all__ = ["PAIRS", "POSES", "SHOTS", "Staging", "frame", "pair_for", "placed", "pose_for"]
