"""Two figures in one picture: standing together, holding hands, an arm over the shoulders, talking.

Each composition places two FigureSpecs side by side (a on the left, b on the right), gives each its own
ident so their parts never mix, solves the touching arms so the hands land where they should, and returns
the parts back to front. Arms are solved with two-bone reach in the picture plane (reach()).
"""
from dataclasses import dataclass, replace

import numpy as np

from .figure import Figure, POSES

HAND_PALM = 0.30          # palm center of a hanging hand, hand lengths from the wrist
HAND_GRIP = 0.56          # where a closed hand holds something (Figure GRIP_POINT)
HOLD_DROP = 0.55          # hu; joined hands hang this far below the hips
REACH_ITER = 4            # passes to settle a wrist that depends on its own forearm direction
MIN_BEND = 1.0            # px kept off a fully straight or fully folded arm
OVER_SHOULDER_REST = (0.56, -0.14)   # wrist over the far shoulder of the other figure (its chest frame)
OVER_SHOULDER_FORE = 0.95           # the forearm along the shoulders, nearly in the picture plane


@dataclass
class Pair:
    parts: list           # back to front, ready for Scene.add
    a: Figure
    b: Figure


def _deg(v):
    """Pose angle of a screen vector: degrees from straight down, + toward the screen-right."""
    return float(np.degrees(np.arctan2(v[0], v[1])))


def reach(figure, side, target, elbow="out"):
    """(upper arm, forearm) pose angles that put the wrist of one arm on target (image px).
    elbow: "out" bends away from the body's center line, "up" or "down" picks the higher or lower elbow."""
    shoulder = figure.joint(f"shoulder_{side}")
    scale = getattr(figure.p, f"{side}_arm_scale")
    l1, l2 = (figure.b["arm"][k] * scale[k] * figure.u for k in (0, 1))
    v = np.asarray(target, float) - shoulder
    d = float(np.clip(np.linalg.norm(v), abs(l1 - l2) + MIN_BEND, l1 + l2 - MIN_BEND))
    base = np.arctan2(v[1], v[0])
    bend = np.arccos(np.clip((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1.0, 1.0))
    elbows = [shoulder + l1 * np.array([np.cos(base + k * bend), np.sin(base + k * bend)]) for k in (1, -1)]
    center_x = figure.joint("pelvis")[0]
    if elbow == "up":
        e = min(elbows, key=lambda p: p[1])
    elif elbow == "down":
        e = max(elbows, key=lambda p: p[1])
    else:
        e = max(elbows, key=lambda p: abs(p[0] - center_x))
    wrist = shoulder + v / max(np.linalg.norm(v), 1e-6) * d
    return _deg(e - shoulder), _deg(wrist - e)


def _posed(spec, pose, **changes):
    return Figure(spec, replace(pose, **changes))


def _arm_to(spec, pose, side, target_fn, elbow="out", **extra):
    """Pose one arm so its wrist meets target_fn(figure) (which may depend on the forearm direction);
    a raised arm moves its shoulder, so the solve repeats until the wrist settles."""
    fig = _posed(spec, pose, **extra)
    for _ in range(REACH_ITER):
        upper, fore = reach(fig, side, target_fn(fig), elbow)
        fig = _posed(spec, pose, **{f"{side}_upper_arm": upper, f"{side}_forearm": fore, **extra})
    return fig


def _forearm_dir(fig, side):
    d = fig.joint(f"wrist_{side}") - fig.joint(f"elbow_{side}")
    return d / max(np.linalg.norm(d), 1e-6)


def _hand_len(fig):
    return fig.b["arm"][2] * fig.u


def _place(a, b, cx, gap):
    """Both specs on one ground line: a on the left, b on the right, gap hu between their pelvis centers."""
    u = a.unit
    return (replace(a, cx=cx - gap * u / 2, ident=a.ident or "a"),
            replace(b, cx=cx + gap * u / 2, ident=b.ident or "b"))


def mirrored(pose):
    """The same pose seen in a mirror: left and right swap, every angle and turn changes sign."""
    swap = {}
    for f in pose.__dataclass_fields__:
        if f.startswith("left_") or f.startswith("right_"):
            side, rest = f.split("_", 1)
            swap[("right_" if side == "left" else "left_") + rest] = getattr(pose, f)
    signed = ("turn", "lean", "pelvis_tilt", "chest_tilt", "spine_shift", "head_tilt", "head_yaw")
    out = {k: -getattr(pose, k) for k in signed}
    for k, v in swap.items():
        if k.endswith(("_thigh", "_shin", "_upper_arm", "_forearm", "_wrist")):
            v = -v
        out[k] = v
    out["facing"] = -pose.facing
    return replace(pose, **out)


# ---- compositions ---------------------------------------------------------------------------------
STAND_A = replace(POSES["standing"], turn=0.22, head_yaw=10.0, head_tilt=3.0, pelvis_tilt=3.0, chest_tilt=-2.0,
                  left_upper_arm=-10.0, right_upper_arm=8.0, left_foot_turn=14.0, right_foot_turn=10.0)
STAND_B = mirrored(STAND_A)


def side_by_side(a, b, cx, gap=1.6, front="b"):
    """Two people standing shoulder to shoulder, bodies and heads turned a little toward each other.
    front: the one nearer the viewer ("a" or "b"); that figure is drawn last."""
    a, b = _place(a, b, cx, gap)
    fa, fb = Figure(a, STAND_A), Figure(b, STAND_B)
    first, last = (fb, fa) if front == "a" else (fa, fb)
    return Pair(first.parts() + last.parts(), fa, fb)


def holding_hands(a, b, cx, gap=2.1, front="b"):
    """Hand in hand: a's right hand hangs relaxed, b's left hand closes around it (or the other way round
    with front="a"). The two hands meet halfway between the figures, a little below the hips."""
    a, b = _place(a, b, cx, gap)
    probe_a, probe_b = Figure(a, STAND_A), Figure(b, STAND_B)
    meet = (probe_a.joint("hip_right") + probe_b.joint("hip_left")) / 2 + [0.0, HOLD_DROP * a.unit]
    back_side, front_side = ("right", "left") if front == "b" else ("left", "right")
    back_spec, front_spec = (a, b) if front == "b" else (b, a)
    back_pose, front_pose = (STAND_A, STAND_B) if front == "b" else (STAND_B, STAND_A)
    fig_back = _arm_to(back_spec, back_pose, back_side,
                       lambda f: meet - _forearm_dir(f, back_side) * HAND_PALM * _hand_len(f),
                       **{f"{back_side}_hand": "relaxed", f"{back_side}_arm_front": True})
    fig_front = _arm_to(front_spec, front_pose, front_side,
                        lambda f: meet - _forearm_dir(f, front_side) * HAND_GRIP * _hand_len(f),
                        **{f"{front_side}_hand": "grip", f"{front_side}_arm_front": True})
    fa, fb = (fig_back, fig_front) if front == "b" else (fig_front, fig_back)
    return Pair(fig_back.parts() + fig_front.parts(), fa, fb)


def arm_over_shoulder(a, b, cx, gap=1.35):
    """a stands half behind b and lays the right arm across b's shoulders. The forearm runs along the top of
    b's shoulders behind the neck (it shows above b's shoulder line), the upper arm goes back from a's
    shoulder (foreshortened) and the hand drapes over b's far shoulder, in front of it."""
    a, b = _place(a, b, cx, gap)
    fb = Figure(b, STAND_B)
    rest = fb.I(fb.F("chest", OVER_SHOULDER_REST, b.shoulder))[0]
    pose = replace(STAND_A, right_hand="relaxed", right_arm_front=True)
    fa = Figure(a, pose)
    for _ in range(2):                                   # a raised arm moves its shoulder: settle it
        upper_len, fore_len = (fa.b["arm"][k] * fa.u for k in (0, 1))
        elbow = rest - [fore_len * OVER_SHOULDER_FORE, 0.0]
        span = elbow - fa.joint("shoulder_right")
        scale = (float(np.clip(np.linalg.norm(span) / upper_len, 0.25, 1.0)), OVER_SHOULDER_FORE)
        # the hand drapes down over the shoulder: bend it from the forearm line to point down the screen
        pose = replace(pose, right_upper_arm=_deg(span), right_forearm=90.0, right_arm_scale=scale, right_wrist=-80.0)
        fa = Figure(a, pose)
    parts_a = fa.parts()
    is_hand = [f"{a.ident}/hand_right" in q.tags for q in parts_a]       # parts compare by identity here
    hand = [q for q, h in zip(parts_a, is_hand) if h]
    body_a = [q for q, h in zip(parts_a, is_hand) if not h]
    return Pair(body_a + fb.parts(overlays=hand), fa, fb)


TALK_LISTEN = replace(POSES["coffee"], turn=0.50, head_yaw=12.0, head_tilt=2.0)
TALK_GESTURE = mirrored(replace(POSES["standing"], turn=0.45, head_yaw=10.0, head_tilt=-3.0, pelvis_tilt=4.0,
                                chest_tilt=-3.0, right_upper_arm=22.0, right_forearm=104.0,
                                right_arm_scale=(0.95, 0.72), right_hand="open", right_wrist=20.0,
                                right_arm_front=True, left_upper_arm=-8.0))


def conversation(a, b, cx, gap=3.6):
    """Two people facing each other in three-quarter view: a listens with a mug, b talks with an open hand."""
    a, b = _place(a, b, cx, gap)
    a = replace(a, left_item=a.left_item or "mug")
    fa, fb = Figure(a, TALK_LISTEN), Figure(b, TALK_GESTURE)
    return Pair(fa.parts() + fb.parts(), fa, fb)


COMPOSITIONS = {"side_by_side": side_by_side, "holding_hands": holding_hands, "arm_over_shoulder": arm_over_shoulder,
                "conversation": conversation}
