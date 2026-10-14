"""Group pictures (two or more figures): placement, draw order and arms that touch the partner.

Each figure keeps its own rig and layer stack, and the pipeline renders them as
separate passes back to front (pipeline.render_figures). This module decides
where each figure stands, which one is in front, and the joints of a contact
arm (hand hold, arm around the shoulders) solved in that figure's body space.

Why separate passes: layer names are global keys of a render pass's mask store,
so two stacks in one pass would collide; separate passes also give the front
figure's coverage for free, which hides the back figure's lines.
"""
from dataclasses import dataclass

import numpy as np

from . import config as cfg
from . import geom
from .body import ARMS, ELBOW_SHIFT, POSES, SHOULDER, WRIST_SHIFT, BodyBuilder
from .character import prepare_character, rig_angles
from .rig import Rig

# arm setups a contact may replace without breaking the other arm's pose
FREE_ARMS = ("hang", "hang_close", "behind", "pocket", "swing_back", "swing_fwd", "support", "hip",
             "behind_head", "rest_knee")
REACH = 0.97            # share of the full arm length a stretched arm uses in a hand hold
HOLD_OFFSET = 0.05      # wrists sit this far (H) to either side of the hold point
# palm toward the partner, fingers down; values describe the image-right hand (the other side mirrors).
# The hand drawn in front closes over the partner's hand; the hand behind reaches across under it.
# (v9 render comparison: a closed front hand over open fingers read as holding; two open hands read as
# hands that only touch)
HOLD_ARM = {"forearm": "front", "hand": "fist", "fingers": (0.10, 1.0, 0.15), "palm": (0.92, 0.0, -0.38),
            "wrist_shift": 0.0}
HOLD_ARM_BEHIND = dict(HOLD_ARM, hand="relaxed", fingers=(-0.35, 0.90, 0.20))
# arm around the shoulders: the upper arm passes behind the partner's head, the forearm comes out on the far
# side of the neck, lies along the shoulder slope, and the hand hangs over the front of the far shoulder
ELBOW_NECK_GAP = 0.04   # partner-local elbow x: just outside the partner's neck base (H)
ELBOW_Y = -0.10         # partner-local elbow height, level with the top of the trapezius
WRIST_OUT = 1.08        # partner-local wrist x as a share of the shoulder joint x: just past the shoulder tip
WRIST_Y = 0.18
AROUND_ARM = {"forearm": "front", "hand": "flat", "fingers": (0.25, 0.95, 0.30), "palm": (0.0, 0.45, -0.89),
              "wrist_shift": 0.0}
REVEAL_START = -0.05  # the reveal band starts behind the elbow; the partner's neck cuts where the arm shows
REVEAL_ARM = 0.18     # half width (H) of the forearm region drawn over the partner
REVEAL_HAND = 0.60    # radius (H) around the wrist that holds the hand
NECK_COLUMN = (-0.40, 0.35)   # body-local y span of the partner's neck column kept in front of the arm


@dataclass
class Figure:
    spec: dict      # the picture spec with this figure as "character"
    rig: Rig
    index: int      # position in spec["characters"]
    reveal: list = None     # canvas polygons of this figure drawn again over its partner (arm around)
    partner: int = None     # draw-order position of the partner the reveal goes over
    reveal_cut: list = None   # canvas polygons of the partner that stay in front (the neck)


def _user_value(entries, i, *path):
    d = entries[i] if i < len(entries) else {}
    for key in path:
        if not isinstance(d, dict) or key not in d:
            return None
        d = d[key]
    return d


def _fill_defaults(chars, entries, toward):
    """Untouched head turns face the group center (the partner in a pair); untouched profiles too."""
    for i, ch in enumerate(chars):
        if _user_value(entries, i, "head", "yaw") is None:
            ch["head"] = dict(ch["head"], yaw=cfg.PAIR_YAW * toward[i])
        if _user_value(entries, i, "facing") is None and toward[i] != 0:
            ch["facing"] = "right" if toward[i] > 0 else "left"


def _figure_height(ch):
    return cfg.SIT_HEIGHT if ch["body"].get("pose") == "sit" else cfg.FIGURE_HEIGHT


def _rows(spec, chars):
    """Row of each figure (0 = front): place.row, else the list filled front row first."""
    rows = int(spec["pair"].get("rows", 1))
    per_row = int(np.ceil(len(chars) / rows))
    return [int(ch.get("place", {}).get("row", i // per_row)) for i, ch in enumerate(chars)]


def _ranks(chars, members):
    """Left-to-right position within a row: by place.x when every member has one, else list order."""
    xs = {i: chars[i].get("place", {}).get("x") for i in members}
    order = sorted(members, key=lambda i: xs[i]) if all(x is not None for x in xs.values()) else list(members)
    return {i: r for r, i in enumerate(order)}


def _offsets(spec, chars, rows):
    """Body-center offsets (head heights) from the group center, one gap per pair of neighbours in a row."""
    offsets, ranks = [0.0] * len(chars), [0] * len(chars)
    side_view = all(ch.get("view") == "side" for ch in chars)
    for row in sorted(set(rows)):
        members = [i for i in range(len(chars)) if rows[i] == row]
        rank = _ranks(chars, members)
        by_rank = sorted(members, key=lambda i: rank[i])
        if side_view:
            gaps = [cfg.PAIR_SIDE_SPACING] * (len(members) - 1)
        else:
            base = cfg.PAIR_SPACING[spec["pair"]["contact"]]
            male = [chars[i]["gender"] == "male" for i in by_rank]
            gaps = [base + cfg.PAIR_MALE_EXTRA * (male[k] + male[k + 1]) for k in range(len(members) - 1)]
        pos = np.concatenate([[0.0], np.cumsum(gaps)])
        pos -= pos[-1] / 2
        if row > 0 and len(members) == rows.count(0) and gaps:
            # a back row as long as the front row would hide behind it: shift it half a gap
            pos += np.mean(gaps) / 2 * (1 if row % 2 else -1)
        for i in members:
            offsets[i], ranks[i] = pos[rank[i]], rank[i]
    mid = (max(offsets) + min(offsets)) / 2      # a shifted back row must not push the group off center
    return [o - mid for o in offsets], ranks


def _place(spec, chars, offsets, rows, width, height):
    """Head height, head top and center x per figure; each row shares one ground line.

    A group wider than the canvas is scaled down to fit; full and wide framings keep the front ground line,
    waist framing keeps the highest head top. Rows further back stand higher and smaller.
    """
    fr = cfg.FRAMING[spec["framing"]]
    scales = [float(ch.get("place", {}).get("scale", 1.0)) * float(ch.get("head_scale", 1.0))
              * cfg.ROW_SCALE ** row for ch, row in zip(chars, rows)]
    unit = fr["head_frac"] * height
    if spec["framing"] in cfg.WHOLE_FIGURE and all(ch["body"].get("pose") == "sit" for ch in chars):
        unit *= cfg.FIGURE_HEIGHT / cfg.SIT_HEIGHT     # a seated group fills the frame like a seated single
    Hs0 = [unit * s / max(scales) for s in scales]
    ground0 = fr["top"] * height + max(_figure_height(ch) * h for ch, h in zip(chars, Hs0))
    span = max(offsets) - min(offsets) + 2 * cfg.GROUP_MARGIN
    fit = min(1.0, width / (span * max(Hs0)))
    Hs = [h * fit for h in Hs0]
    rise = [cfg.ROW_RISE * row * max(Hs) for row in rows]
    highest = max(_figure_height(ch) * h + r for ch, h, r in zip(chars, Hs, rise))
    ground = ground0 if spec["framing"] in cfg.WHOLE_FIGURE else fr["top"] * height + highest
    tops = [ground - r - _figure_height(ch) * h for ch, h, r in zip(chars, Hs, rise)]
    yaw = np.mean([ch["head"]["yaw"] for ch in chars if ch.get("view", "front") != "side"] or [0.0])
    center = width * (0.5 - np.sign(yaw) * cfg.LEAD_ROOM * min(abs(yaw) / 20.0, 1.0))
    xs = []
    for ch, off in zip(chars, offsets):
        x = ch.get("place", {}).get("x")
        xs.append(width * float(x) if x is not None else center + off * max(Hs))
    return Hs, tops, xs


def _body(ch, rig):
    return BodyBuilder(rig, prepare_character(ch))


def _keep_posed_arm_outside(ch, inner):
    """Mirror the pose when the contact would take the arm that carries the pose."""
    right, left = POSES.get(ch["body"].get("pose", "relaxed"), POSES["relaxed"])
    inner_arm, outer_arm = (right, left) if inner > 0 else (left, right)
    if inner_arm not in FREE_ARMS and outer_arm in FREE_ARMS:
        ch["_mirror_pose"] = True


def _arm_lengths(bb):
    """Upper arm and forearm length (H) of the hanging arm of this body."""
    dx = bb.shoulder[0] - SHOULDER[0]
    elbow = np.array([ARMS["hang"]["elbow"][0] + dx * ELBOW_SHIFT, ARMS["hang"]["elbow"][1]])
    wrist = np.array([ARMS["hang"]["wrist"][0] + dx * WRIST_SHIFT, ARMS["hang"]["wrist"][1]])
    return np.linalg.norm(elbow - bb.shoulder), np.linalg.norm(wrist - elbow)


def _elbow(S, W, L1, L2, outward):
    """Two-bone solve in canvas px; the elbow bends toward x * outward > 0."""
    v = W - S
    d = float(np.linalg.norm(v))
    if d >= L1 + L2 - 1e-6:
        return S + v * L1 / (L1 + L2)
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    h = np.sqrt(max(L1 * L1 - a * a, 0.0))
    u = v / d
    n = np.array([-u[1], u[0]])
    P = S + a * u
    return P + h * n if n[0] * outward >= 0 else P - h * n


def _local_arm(rig, side, elbow, wrist, template):
    """Canvas joints -> arm entry in image-right body-local units (joints() mirrors by side)."""
    E, W = rig.body_local(np.array([elbow, wrist]))
    return dict(template, elbow=(E[0] * side, E[1]), wrist=(W[0] * side, W[1]))


def _hand_hold(chars, rigs, sides, front):
    order = np.argsort(sides)                     # left figure first
    inner = {i: -sides[i] for i in range(2)}      # the left figure reaches with its image-right arm
    for i in range(2):
        _keep_posed_arm_outside(chars[i], inner[i])
    bodies = [_body(chars[i], rigs[i]) for i in range(2)]
    S = {i: rigs[i].body2([bodies[i].joints(inner[i])[0]])[0] for i in range(2)}
    mx = (S[order[0]][0] + S[order[1]][0]) / 2
    lengths = {i: np.array(_arm_lengths(bodies[i])) * rigs[i].H for i in range(2)}
    lows = []
    for i in range(2):
        reach = REACH * lengths[i].sum()
        dx = abs(mx - S[i][0])
        lows.append(S[i][1] + np.sqrt(max(reach * reach - dx * dx, (0.5 * reach) ** 2)))
    y = min(lows)
    for i in range(2):
        W = np.array([mx - inner[i] * HOLD_OFFSET * rigs[i].H, y])
        E = _elbow(S[i], W, *lengths[i], outward=inner[i])
        template = HOLD_ARM if i == front else HOLD_ARM_BEHIND
        chars[i]["_arms"] = {inner[i]: _local_arm(rigs[i], inner[i], E, W, template)}


def _shoulder_arm(chars, rigs, sides, lead):
    """Solve the lead's inner arm; return the canvas region where it shows over the partner and the
    partner's neck, which stays in front of it."""
    partner = 1 - lead
    inner = -sides[lead]
    _keep_posed_arm_outside(chars[lead], inner)
    pb = _body(chars[partner], rigs[partner])
    # partner-local, measured from the partner's own neck and shoulder so a male frame widens it
    rest = np.array([[(pb.neck_w[1] + ELBOW_NECK_GAP) * inner, ELBOW_Y],
                     [pb.shoulder[0] * WRIST_OUT * inner, WRIST_Y]])
    E, W = rigs[partner].body2(rest)
    chars[lead]["_arms"] = {inner: _local_arm(rigs[lead], inner, E, W, AROUND_ARM)}
    H = rigs[lead].H
    u = (W - E) / np.linalg.norm(W - E)
    start = E + u * REVEAL_START * H
    n = np.array([-u[1], u[0]]) * REVEAL_ARM * H
    band = np.array([start + n, W + n, W - n, start - n])
    # the arm passes behind the partner's neck and the top of the back: that column stays in front
    nb = pb.neck_w[1]
    column = rigs[partner].body2([(-nb, NECK_COLUMN[0]), (nb, NECK_COLUMN[0]), (nb, NECK_COLUMN[1]),
                                  (-nb, NECK_COLUMN[1])])
    return [band, geom.ellipse(W[0], W[1], REVEAL_HAND * H, REVEAL_HAND * H, 48)], [pb.neck_canvas(), column]


def plan(spec, width, height):
    """Figures of a group spec (two or more characters) in draw order (back to front)."""
    chars = [dict(ch) for ch in spec["characters"]]
    n = len(chars)
    rows = _rows(spec, chars)
    offsets, ranks = _offsets(spec, chars, rows)
    toward = [-int(np.sign(off)) for off in offsets]      # toward the group center; the middle figure looks out
    _fill_defaults(chars, spec.get("_user_characters", []), toward)
    Hs, tops, xs = _place(spec, chars, offsets, rows, width, height)
    rigs = [Rig(Hs[i], (xs[i], tops[i]), **rig_angles(chars[i])) for i in range(n)]
    contact = spec["pair"]["contact"]
    lead = int(spec["pair"].get("lead", 0))
    # rows further back are drawn first; place.depth overrides
    depth = [float(ch.get("place", {}).get("depth", row)) for ch, row in zip(chars, rows)]
    order = sorted(range(n), key=lambda i: (-depth[i], i))
    if contact == "shoulder_arm":
        order = [lead, 1 - lead]     # the arm passes behind the partner's head, so the lead stands behind
    sides = [-1 if r == 0 else 1 for r in ranks]          # contacts are two-figure only
    reveal, cut = {}, {}
    if contact == "hand_hold":
        _hand_hold(chars, rigs, sides, front=order[1])
    elif contact == "shoulder_arm":
        reveal[lead], cut[lead] = _shoulder_arm(chars, rigs, sides, lead)
    return [Figure(dict(spec, character=chars[i]), rigs[i], i, reveal.get(i),
                   order.index(1 - i) if i in reveal else None, cut.get(i)) for i in order]
