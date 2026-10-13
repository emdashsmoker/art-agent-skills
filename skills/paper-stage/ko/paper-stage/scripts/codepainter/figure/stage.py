"""Putting figures in a picture: framing, reaching, and several figures together.

- frame(): sets each pose's root and a shared unit so a shot (full, knee, waist, bust) fits the canvas,
  with every figure standing on the same floor.
- reach(): bends one arm so its hand lands on a point of the canvas (two-bone inverse kinematics).
- draw_actors(): draws figures far to near; the nearer one's shadow falls on the farther, and parts
  listed in Actor.over (a hand on a shoulder) are laid back over whoever was drawn after.

Typical two-shot:
    her, him = Actor(spec_a, BodySpec(), pose_a, depth=0.0), Actor(spec_b, MALE_BODY, pose_b, depth=-0.4)
    her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "knee", centers=(0.38, 0.62))
    him.pose = reach(him.pose, him.body, "l", shoulder_pixel, painting.shape, depth=0.3)
    him.over = ("hand_l",)
    draw_actors(painting, [her, him], style)
"""
import warnings
from dataclasses import dataclass, field, replace

import numpy as np

from .. import shading as sh
from ..color import rgb
from . import props as props_rig
from .body import FAR_LIMB_ANGLE, FOREARM, HEAD_PIVOT_Y, UPPER_ARM, Skeleton, _rotate, draw_figure
from .frame import light_on_canvas
from .hand import FIGURE_HAND_LENGTH

# Where each shot cuts the figure: (landmark, head heights below it).
SHOTS = {"full": ("feet", 0.15), "knee": ("knee", 0.30), "waist": ("hip", 0.45), "bust": ("chest", 1.10)}
HEAD_ROOM = 0.18             # hair above the crown, head heights
SIDE_ROOM = 0.55             # room either side of the outermost joint (flesh, hair, hands)
WRIST_CHECK_RADIUS = FOREARM  # head heights round the wrist where a laid-over hand must still show some of its arm
WRIST_SEEN = 0.15            # share of that arm left in view below which the hand counts as floating
SHOULDER_ROOM = 0.45         # room past each shoulder joint for the arm, in closer shots
PALM_REACH = 0.45            # share of the hand length between the wrist and the point a hand rests on
ACTOR_SHADOW = (0.10, 0.06)  # how far a nearer figure's shadow falls on a farther one (along the light, down)


def _extent(pose, body, canvas_shape):
    """(left, top, right, cut points, floor) of a figure in head heights from its pelvis centre, upright on the canvas."""
    probe = replace(pose, root=(0.0, 0.0), unit=1.0 / canvas_shape[0])
    skeleton = Skeleton(probe, body, canvas_shape)
    joints = np.array(list(skeleton.joints.values()))
    head = body.head
    crown = skeleton.joints["head_pivot"] + _rotate([(0.0, -(HEAD_PIVOT_Y + HEAD_ROOM) * head)], pose.lean + pose.head_tilt)[0]
    shoulders = np.array([skeleton.joints["shoulder_l"], skeleton.joints["shoulder_r"]])
    shoulders[:, 0] += np.array([-SHOULDER_ROOM, SHOULDER_ROOM]) * np.sign(shoulders[1, 0] - shoulders[0, 0] + 1e-9)
    # rows 0 and 1 are the shoulders (with room for the deltoids), used to fit closer shots
    points = np.vstack([shoulders, joints, crown[None, :], skeleton.joints["head_pivot"] + [[-0.5 * head, 0.0], [0.5 * head, 0.0]]])
    feet = max(skeleton.joints[f"{part}_{side}"][1] for part in ("ankle", "toe", "heel") for side in ("l", "r"))
    cuts = {"feet": feet, "knee": max(skeleton.joints["knee_l"][1], skeleton.joints["knee_r"][1]),
            "hip": max(skeleton.joints["hip_l"][1], skeleton.joints["hip_r"][1]),
            "chest": skeleton.to_pixels(skeleton.project(skeleton._local["chest"]))[0][1]}
    return points, cuts, feet + 0.10


def frame(figures, canvas_shape, shot="full", centers=None, margin=0.05, overlap=1.3, floor=None):
    """Poses with root and unit set so all figures fit the shot, standing on one floor.

    figures: [(pose, body), ...]; centers: x of each figure's middle as a share of the width (spread evenly by default).
    shot: "full", "knee", "waist" or "bust". overlap: in closer shots, how far past its share of the width
    each figure's shoulders may reach (figures overlap, as in most two-shots). floor: pixel row the feet stand
    on, to match a background's floor (None: placed by the margins). Returns the new poses in the same order.
    """
    height, width = canvas_shape
    centers = centers or [(index + 0.5) / len(figures) for index in range(len(figures))]
    landmark, below = SHOTS[shot]
    extents = [_extent(pose, body, canvas_shape) for pose, body in figures]
    # vertical: from the highest crown to the lowest cut, with every figure on the same floor
    tops = [points[:, 1].min() - floor for points, _, floor in extents]
    cuts = [cut[landmark] + below - floor for _, cut, floor in extents]
    span = max(cuts) - min(tops)
    slot = width / max(len(figures), 1)
    if shot == "full":                 # the whole figure, hands and feet included, keeps to its share of the width
        sizes = [(points[:, 0].max() - points[:, 0].min()) + 2 * SIDE_ROOM for points, _, _ in extents]
    else:                              # a closer shot may overlap arms and crop the edges; only the shoulders must fit
        sizes = [abs(points[1, 0] - points[0, 0]) / overlap for points, _, _ in extents]
    unit = min((1.0 - 2 * margin) * height / span, min(slot * (1.0 - margin) / size for size in sizes))
    if floor is not None:              # stand on a given floor line, shrinking if the tallest would leave the top
        unit = min(unit, (floor - margin * height) / -min(tops))
        floor_px = floor
    else:
        floor_px = margin * height - min(tops) * unit
        if shot == "full":             # centre the group on the canvas
            floor_px += ((1.0 - 2 * margin) * height - span * unit) / 2
    posed = []
    for (pose, body), (points, _, floor), center in zip(figures, extents, centers):
        middle = (points[:, 0].min() + points[:, 0].max()) / 2
        root = ((center * width - middle * unit) / width, (floor_px - floor * unit) / height)
        posed.append(replace(pose, root=root, unit=unit / height))
    return posed


def _bone_angles(direction):
    """(front-view angle, swing) in degrees for a unit 3D bone direction."""
    x, y, z = direction
    return float(np.degrees(np.arctan2(x, y))), float(np.degrees(np.arcsin(np.clip(z, -1.0, 1.0))))


def to_figure(skeleton, pixel, depth):
    """A canvas point at `depth` (head heights toward the viewer) in the figure's own 3D units."""
    flat = _rotate([(np.asarray(pixel, dtype=np.float64) - skeleton.origin) / skeleton.unit], -skeleton.pose.lean)[0]
    across, down = flat
    if skeleton.pitch != 0.0:
        down = (down - depth * np.sin(skeleton.pitch)) / np.cos(skeleton.pitch)
    return np.array([across * skeleton.cos_yaw - depth * skeleton.sin_yaw, down,
                     across * skeleton.sin_yaw + depth * skeleton.cos_yaw])


def reach(pose, body, side, target, canvas_shape, depth=None, pole=None, palm=True):
    """The pose with one arm bent so its hand reaches a canvas point.

    side: "l" or "r". target: pixel (x, y). depth: how far toward the viewer the point is, in head
    heights in the figure's own frame (None: level with the shoulder). pole: 3D direction the elbow
    bends toward (default out to the side, down and back). palm: aim the middle of the hand at the
    point instead of the wrist. An unreachable point is reached for as far as the arm goes.
    """
    skeleton = Skeleton(pose, body, canvas_shape)
    shoulder = skeleton._local[f"shoulder_{side}"]
    depth = skeleton.depth[f"shoulder_{side}"] if depth is None else depth
    goal = to_figure(skeleton, target, depth)
    upper = UPPER_ARM * pose.shorten.get(f"upper_arm_{side}", 1.0)
    lower = FOREARM * pose.shorten.get(f"forearm_{side}", 1.0)
    outward = -1.0 if side == "l" else 1.0
    pole = np.array([0.45 * outward, 0.6, -0.65]) if pole is None else np.asarray(pole, dtype=np.float64)
    wrist = goal
    for _ in range(3 if palm else 1):
        offset = wrist - shoulder
        distance = np.clip(np.linalg.norm(offset), abs(upper - lower) + 1e-3, upper + lower - 1e-3)
        along = offset / max(np.linalg.norm(offset), 1e-9)
        bend = pole - (pole @ along) * along
        bend = bend / max(np.linalg.norm(bend), 1e-9)
        cos_a = (upper ** 2 + distance ** 2 - lower ** 2) / (2 * upper * distance)
        elbow = shoulder + along * upper * cos_a + bend * upper * np.sqrt(max(1.0 - cos_a ** 2, 0.0))
        end = shoulder + along * distance
        fore = (end - elbow) / max(np.linalg.norm(end - elbow), 1e-9)
        if palm:
            wrist = goal - fore * FIGURE_HAND_LENGTH * PALM_REACH
    upper_angle, upper_swing = _bone_angles((elbow - shoulder) / upper)
    fore_angle, fore_swing = _bone_angles(fore)
    swing = {**pose.swing, f"upper_arm_{side}": upper_swing, f"forearm_{side}": fore_swing}
    return replace(pose, **{f"arm_{side}": (upper_angle, fore_angle), f"hand_{side}": None}, swing=swing)


REST_OUTWARD = 0.08         # seen from the front, resting hands sit this far outside each knee (head heights)


def rest_hands(pose, body, canvas_shape, on="knees", sides=("l", "r")):
    """The pose with the hands resting on the knees (on="knees") or on the middle of the thighs (on="thighs").

    Seen from the front the thighs point at the viewer and look short, so two hands on the knees would
    meet over the lap. There each hand moves to the outside of its knee.
    """
    for side in sides:
        skeleton = Skeleton(pose, body, canvas_shape)
        hip, knee = skeleton.joints[f"hip_{side}"], skeleton.joints[f"knee_{side}"]
        spot = knee if on == "knees" else (hip + knee) / 2
        share = 1.0 if on == "knees" else 0.5
        depth = skeleton.depth[f"hip_{side}"] * (1.0 - share) + skeleton.depth[f"knee_{side}"] * share
        outward = (-1.0 if side == "l" else 1.0) * REST_OUTWARD if abs(pose.yaw) <= FAR_LIMB_ANGLE else 0.0
        pose = reach(pose, body, side, spot + [outward * skeleton.unit, -0.12 * skeleton.unit], canvas_shape,
                     depth=depth + 0.12)
    return pose


@dataclass
class Actor:
    spec: object
    body: object
    pose: object
    dress: object = None
    hands: dict = None
    depth: float = 0.0            # head heights toward the viewer: decides who is drawn over whom
    over: tuple = ()              # parts laid back over figures drawn after this one: "hand_l", "hand_r", "arm_l", "arm_r"
    props: list = field(default_factory=list)   # props.Prop drawn with this figure (a chair, a bed)
    masks: dict = None            # filled by draw_actors
    skeleton: object = None
    prop_masks: list = None       # filled by draw_actors: the mask of each prop


def _paste(painting, source, mask):
    """Copy colour and lines of `source` (a saved state) back into the painting inside `mask`."""
    color, line_rgb, line_alpha = source
    m = np.clip(mask, 0.0, 1.0).astype(np.float32)
    painting.color += (color - painting.color) * m[..., None]
    lines = np.clip(sh.blur(m, 1.5) * 1.5, 0.0, 1.0)
    painting.line_rgb += (line_rgb - painting.line_rgb) * lines[..., None]
    painting.line_alpha += (line_alpha - painting.line_alpha) * lines


def _part(masks, name):
    side = name[-1]
    return masks["hands"][side] if name.startswith("hand") else masks["limbs"][f"arm_{side}"]


def draw_actors(painting, actors, style, light=sh.DEFAULT_LIGHT, shadows=True):
    """Draw figures far to near (by Actor.depth). Fills each actor's masks and skeleton; returns the union of the figures."""
    drawn = np.zeros(painting.shape, dtype=np.float32)
    saved = {}
    offset = -light_on_canvas(light)
    for actor in sorted(actors, key=lambda a: a.depth):
        actor.skeleton = Skeleton(actor.pose, actor.body, painting.shape)
        backs = [props_rig.draw(painting, actor.skeleton, prop, style, light) for prop in actor.props]
        masks = draw_figure(painting, actor.spec, actor.body, actor.pose, style, light, dress=actor.dress, hands=actor.hands)
        figure = masks["figure"]
        for back in backs:
            props_rig.contact_shadows(painting, actor.skeleton, figure, back, style, light)
        if shadows and drawn.any():          # the nearer figure darkens the one behind it
            shift = (offset * ACTOR_SHADOW[0] + [0.0, ACTOR_SHADOW[1]]) * actor.skeleton.unit
            cast = sh.cast_shadow(figure, drawn, shift, actor.skeleton.px(0.04)) * (1.0 - figure)
            painting.fill(cast, rgb(style.shadow_tint), 0.6 * style.shadow_depth, "multiply")
        fronts = [props_rig.draw(painting, actor.skeleton, prop, style, light, layer="front") for prop in actor.props]
        actor.prop_masks = [np.maximum(back, front) for back, front in zip(backs, fronts)]
        if actor.over:
            saved[id(actor)] = (painting.color.copy(), painting.line_rgb.copy(), painting.line_alpha.copy())
        actor.masks = masks
        drawn = np.maximum(drawn, figure)
    for actor in actors:
        nearer = [other.masks["figure"] for other in actors if other.depth > actor.depth]
        for name in actor.over:
            if name.startswith("hand") and nearer:
                _warn_floating_hand(painting, actor, name[-1], np.maximum.reduce(nearer))
            _paste(painting, saved[id(actor)], _part(actor.masks, name))
    return drawn


def _warn_floating_hand(painting, actor, side, nearer):
    """Warn when a hand laid over a nearer figure has its own forearm hidden behind that figure: it would float."""
    wrist = actor.skeleton.joints[f"wrist_{side}"]
    radius = actor.skeleton.px(WRIST_CHECK_RADIUS)
    disc = painting.mask(np.array([wrist + radius * np.array([np.cos(a), np.sin(a)]) for a in np.linspace(0, 2 * np.pi, 24)]))
    arm = actor.masks["limbs"][f"arm_{side}"] * disc
    if arm.sum() > 0 and (arm * (1.0 - nearer)).sum() / arm.sum() < WRIST_SEEN:
        warnings.warn(f"hand_{side} is laid over a nearer figure but its forearm is hidden behind it, so the hand floats; "
                      f"hold with the hand whose arm stays in view, or bend the elbow forward with reach(..., pole=...)")


def floor_shadows(painting, actors, style, color=None, strength=0.55):
    """Shadows on the floor under each actor's feet and props (after draw_actors)."""
    for actor in actors:
        legs = [actor.masks["limbs"]["leg_l"], actor.masks["limbs"]["leg_r"]] + list(actor.prop_masks or [])
        props_rig.floor_shadow(painting, actor.skeleton, legs, style, strength, color)
