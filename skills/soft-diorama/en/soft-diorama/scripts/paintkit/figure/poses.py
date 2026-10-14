"""Named poses for the full-body figure, built with aim() so they hold from any body turn.

Every function returns a Pose; change anything afterwards with dataclasses.replace. turn is
the body turn (Pose.turn), so the same pose can be drawn from the front, three-quarter,
side or back. Directions inside aim() are in the body's own frame: x across the body toward
the figure's left-hand side of the picture when it faces the viewer, y down, z forward.

Standing:  contrapposto, arms_crossed, hands_on_hips, hands_in_pockets, stretch
Moving:    walk, run (phase 0..1 steps through one stride)
Sitting:   cross_legged_seat (on a chair), squat, sit_floor
Resting:   lean_wall, lie_side
"""
import numpy as np

from .fullbody import Pose, aim
from .hand import HandSpec

_RESTING = HandSpec('relaxed', 'rest')
_BACK = HandSpec('relaxed', 'back')


def _head(turn, follow=0.75):
    """The head turns with the body, a little less near the front so the face stays readable."""
    return turn if abs(turn) >= 90 else turn * follow


def _limbs(turn, left_arm=None, right_arm=None, left_leg=None, right_leg=None):
    """aim() each given limb: ((upper x, y, z), (lower x, y, z)) in the body frame."""
    limbs = dict(left_arm=left_arm, right_arm=right_arm, left_leg=left_leg, right_leg=right_leg)
    return {name: aim(turn, *segments) for name, segments in limbs.items() if segments is not None}


def _hanging_arms(turn):
    return _limbs(turn, left_arm=((-0.12, 1.0, 0.02), (-0.04, 1.0, 0.10)),
                  right_arm=((0.12, 1.0, 0.02), (0.04, 1.0, 0.10)))


def contrapposto(turn=20.0, **changes):
    """Weight on the leg under the raised hip; the other knee bends forward, arms hang loose."""
    pose = dict(turn=turn, head_yaw=_head(turn), lean=-3, hip_tilt=8, shoulder_tilt=-6, head_tilt=5,
                front_leg='right', right_foot=0.35, left_hand=_RESTING, right_hand=_RESTING,
                **_hanging_arms(turn),
                **_limbs(turn, left_leg=((0.04, 1.0, 0.0), (0.0, 1.0, 0.0)),
                         right_leg=((-0.06, 1.0, 0.20), (0.04, 1.0, -0.06))))
    return Pose(**{**pose, **changes})


def arms_crossed(turn=15.0, **changes):
    """Forearms folded across the chest, feet a little apart."""
    pose = dict(turn=turn, head_yaw=_head(turn), hip_tilt=3, shoulder_tilt=-2, left_hand=_BACK, right_hand=_BACK,
                **_limbs(turn, left_arm=((-0.14, 1.0, 0.80), (1.0, -0.20, 0.25)),
                         right_arm=((0.14, 1.0, 0.85), (-1.0, -0.12, 0.35)),
                         left_leg=((-0.05, 1.0, 0.0), (0.0, 1.0, 0.0)),
                         right_leg=((0.05, 1.0, 0.0), (0.0, 1.0, 0.0))))
    return Pose(**{**pose, **changes})


def hands_on_hips(turn=10.0, **changes):
    """Elbows out, hands on the hips."""
    pose = dict(turn=turn, head_yaw=_head(turn), hip_tilt=-5, shoulder_tilt=3, left_hand=_BACK, right_hand=_BACK,
                **_limbs(turn, left_arm=((-0.78, 0.62, -0.10), (0.80, 0.55, 0.20)),
                         right_arm=((0.78, 0.62, -0.10), (-0.80, 0.55, 0.20)),
                         left_leg=((-0.07, 1.0, 0.0), (0.0, 1.0, 0.0)),
                         right_leg=((0.07, 1.0, 0.0), (0.0, 1.0, 0.0))))
    return Pose(**{**pose, **changes})


def hands_in_pockets(turn=15.0, pouch=False, **changes):
    """Hands in the front trouser pockets (the garment covers them; use with bottoms or a suit).
    pouch=True puts them in the kangaroo pocket of a hoodie instead. The arms reach the pocket by
    inverse kinematics; the arm angles below only apply if the hands are changed to something else."""
    pocket = HandSpec('pouch' if pouch else 'pocket')
    pose = dict(turn=turn, head_yaw=_head(turn), hip_tilt=5, shoulder_tilt=-3, lean=-1,
                left_hand=pocket, right_hand=pocket, front_leg='right', right_foot=0.3,
                **_limbs(turn, left_arm=((-0.10, 1.0, 0.05), (0.30, 1.0, 0.35)),
                         right_arm=((0.10, 1.0, 0.05), (-0.30, 1.0, 0.35)),
                         left_leg=((0.03, 1.0, 0.0), (0.0, 1.0, 0.0)),
                         right_leg=((-0.05, 1.0, 0.15), (0.04, 1.0, -0.04))))
    return Pose(**{**pose, **changes})


def stretch(turn=0.0, **changes):
    """Both arms raised overhead, hands meeting above the head."""
    pose = dict(turn=turn, head_yaw=_head(turn, 0.5), head_tilt=-4,
                left_hand=HandSpec('open', 'palm'), right_hand=HandSpec('open', 'palm'),
                **_limbs(turn, left_arm=((-0.22, -1.0, 0.05), (0.40, -1.0, 0.0)),
                         right_arm=((0.22, -1.0, 0.05), (-0.40, -1.0, 0.0)),
                         left_leg=((-0.04, 1.0, 0.0), (0.0, 1.0, 0.0)),
                         right_leg=((0.04, 1.0, 0.0), (0.0, 1.0, 0.0))))
    return Pose(**{**pose, **changes})


def _stride(phase, forward, back):
    """Blend a limb between its forward and back extremes over one stride (phase 0..1)."""
    amount = 0.5 + 0.5 * np.cos(2.0 * np.pi * phase)          # 1 = fully forward
    return tuple(tuple(b + (f - b) * amount for f, b in zip(fs, bs)) for fs, bs in zip(forward, back))


def walk(turn=90.0, phase=0.0, **changes):
    """One step of a walk: phase 0 = left leg forward, 0.5 = right leg forward. Best read from the side."""
    leg_forward, leg_back = ((0.0, 1.0, 0.42), (0.0, 1.0, 0.12)), ((0.0, 1.0, -0.30), (0.0, 1.0, -0.62))
    arm_forward, arm_back = ((0.0, 1.0, 0.32), (0.0, 1.0, 0.70)), ((0.0, 1.0, -0.34), (0.0, 1.0, -0.22))
    pose = dict(turn=turn, head_yaw=_head(turn), lean=2.0 * np.sign(np.sin(np.radians(turn))),
                left_hand=_RESTING, right_hand=_RESTING,
                front_leg='left' if np.cos(2 * np.pi * phase) >= 0 else 'right',
                **_limbs(turn, left_leg=_stride(phase, leg_forward, leg_back),
                         right_leg=_stride(phase + 0.5, leg_forward, leg_back),
                         left_arm=_offset(_stride(phase + 0.5, arm_forward, arm_back), -0.10),
                         right_arm=_offset(_stride(phase, arm_forward, arm_back), 0.10)))
    return Pose(**{**pose, **changes})


def run(turn=90.0, phase=0.0, **changes):
    """One stride of a run: knee high in front, heel kicked up behind, elbows bent, body leaning in."""
    leg_forward, leg_back = ((0.0, 0.65, 0.90), (0.0, 1.0, -0.20)), ((0.0, 1.0, -0.55), (0.0, -0.20, -1.0))
    arm_forward, arm_back = ((0.0, 1.0, 0.55), (0.0, -0.45, 1.0)), ((0.0, 1.0, -0.65), (0.0, 0.55, 0.45))
    pose = dict(turn=turn, head_yaw=_head(turn), lean=8.0 * np.sign(np.sin(np.radians(turn))),
                left_hand=HandSpec('fist', 'rest'), right_hand=HandSpec('fist', 'rest'),
                front_leg='left' if np.cos(2 * np.pi * phase) >= 0 else 'right',
                **_limbs(turn, left_leg=_stride(phase, leg_forward, leg_back),
                         right_leg=_stride(phase + 0.5, leg_forward, leg_back),
                         left_arm=_offset(_stride(phase + 0.5, arm_forward, arm_back), -0.10),
                         right_arm=_offset(_stride(phase, arm_forward, arm_back), 0.10)))
    return Pose(**{**pose, **changes})


def _offset(limb, x):
    """Move both segments of a limb a little to one side (arms clear the body)."""
    return tuple((sx + x, sy, sz) for sx, sy, sz in limb)


def cross_legged_seat(turn=30.0, **changes):
    """On a chair, right knee over the left, hands resting on the top knee."""
    pose = dict(turn=turn, head_yaw=_head(turn), front_leg='right', left_hand=_BACK, right_hand=_BACK,
                **_limbs(turn, left_leg=((-0.06, 0.14, 1.0), (0.0, 1.0, 0.08)),
                         right_leg=((-0.30, -0.12, 1.0), (-0.30, 1.0, 0.45)),
                         left_arm=((0.05, 1.0, 0.35), (0.05, 0.55, 1.0)),
                         right_arm=((-0.10, 1.0, 0.35), (-0.15, 0.55, 1.0))))
    return Pose(**{**pose, **changes})


def squat(turn=40.0, **changes):
    """Crouched on the heels, knees up and apart, forearms on the knees. Place the pelvis low."""
    pose = dict(turn=turn, head_yaw=_head(turn), lean=10.0 * np.sign(np.sin(np.radians(turn))),
                left_hand=_BACK, right_hand=_BACK,
                **_limbs(turn, left_leg=((-0.18, -0.45, 0.88), (0.0, 1.0, -0.50)),
                         right_leg=((0.18, -0.45, 0.88), (0.0, 1.0, -0.50)),
                         left_arm=((-0.05, 1.0, 0.75), (0.10, 0.55, 1.0)),
                         right_arm=((0.05, 1.0, 0.75), (-0.10, 0.55, 1.0))))
    return Pose(**{**pose, **changes})


def sit_floor(turn=50.0, knees_up=False, **changes):
    """On the floor: legs stretched out with hands propped behind, or knees drawn up and hugged."""
    if knees_up:
        # Knees high and shins slanted back so the feet rest on the floor level with the seat.
        limbs = _limbs(turn, left_leg=((-0.14, -0.90, 0.60), (0.0, 1.0, 0.35)),
                       right_leg=((0.02, -0.90, 0.60), (0.04, 1.0, 0.35)),
                       left_arm=((-0.10, 1.0, 0.55), (0.45, -0.15, 0.90)),
                       right_arm=((0.10, 1.0, 0.55), (-0.45, -0.15, 0.90)))
    else:
        limbs = _limbs(turn, left_leg=((-0.10, 0.04, 1.0), (-0.06, 0.08, 1.0)),
                       right_leg=((0.08, 0.04, 1.0), (0.12, 0.08, 1.0)),
                       left_arm=((-0.25, 1.0, -0.45), (-0.05, 1.0, -0.25)),
                       right_arm=((0.25, 1.0, -0.45), (0.05, 1.0, -0.25)))
    pose = dict(turn=turn, head_yaw=_head(turn), left_hand=HandSpec('open', 'back'),
                right_hand=HandSpec('open', 'back'), **limbs)
    if knees_up:
        pose.update(left_hand=_BACK, right_hand=_BACK)
    return Pose(**{**pose, **changes})


def lean_wall(turn=-25.0, **changes):
    """Leaning a shoulder on a wall: ankles crossed, arms folded. The wall is on the side the body leans to."""
    pose = arms_crossed(turn)
    side = 1.0 if turn < 0 else -1.0                          # lean away from the way the body faces
    pose_changes = dict(lean=7.0 * side, hip_tilt=-4.0 * side, shoulder_tilt=-2.0 * side, front_leg='left',
                        **_limbs(turn, left_leg=((0.08, 1.0, 0.04), (0.10, 1.0, 0.0)),
                                 right_leg=((-0.02, 1.0, 0.0), (-0.06, 1.0, 0.0))))
    return Pose(**{**pose.__dict__, **pose_changes, **changes})


def lie_side(**changes):
    """Lying on one side facing the viewer, head to screen right resting on the lower arm, knees bent,
    the upper hand on the hip. Limb angles are on screen (aim() does not follow roll)."""
    # Rolled to put the head on screen right, the body's right side is underneath; that arm reaches
    # along the bed past the head as a pillow.
    pose = dict(roll=88.0, head_tilt=-4, left_leg=(-62, -108), right_leg=(-82, -98), front_leg='left',
                left_arm=(-92, -70), right_arm=(98, 62), left_hand=_RESTING, right_hand=_BACK,
                left_foot=0.0, right_foot=0.0)
    return Pose(**{**pose, **changes})


POSES = dict(contrapposto=contrapposto, arms_crossed=arms_crossed, hands_on_hips=hands_on_hips,
             hands_in_pockets=hands_in_pockets, stretch=stretch, walk=walk, run=run,
             cross_legged_seat=cross_legged_seat, squat=squat, sit_floor=sit_floor, lean_wall=lean_wall,
             lie_side=lie_side)
