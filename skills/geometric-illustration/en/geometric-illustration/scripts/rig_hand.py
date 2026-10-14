"""Hand rig: palm, four three-joint fingers and a thumb as mannequin solids.

Why: hands look wrong when they are drawn as flat outlines, because fingers
overlap, foreshorten and curl. Building them from solids in a local 3D frame
(u toward the fingers, v toward the thumb, n out of the back of the hand)
gives correct overlaps and contours for any orientation, and a gesture is
just a table of joint angles.

Shape decisions (each one fixes a "glove" look of the earlier rig):
- The palm is a flattened slab (elliptical sections), wider at the knuckles
  than at the wrist, with a padded thumb ball on the palm side.
- Each finger is one tapered tube through its joints, ending in a narrow
  tip; knuckles round off instead of showing as beads.
- Knuckles sit on an arc (middle finger furthest out), finger lengths follow
  the human ratios (index 0.89, ring 0.93, pinky 0.73 of the middle finger).
- Nails are returned as indication shapes for the renderers.

Units are head widths; the hand is about 1.0 head width long (ANSUR II hand
length rescaled, see references/anatomy.md).
"""
import numpy as np

from mannequin import Piece, ellipse_cone, sphere, tube

FINGERS = ('index', 'middle', 'ring', 'pinky')
FINGER_V = {'index': 0.135, 'middle': 0.045, 'ring': -0.045, 'pinky': -0.130}     # knuckle offset toward thumb
FINGER_MCP_U = {'index': 0.50, 'middle': 0.52, 'ring': 0.50, 'pinky': 0.46}       # knuckle arc, wrist = 0
FINGER_LEN = {'index': 0.40, 'middle': 0.45, 'ring': 0.42, 'pinky': 0.33}
FINGER_R = {'index': (0.045, 0.039, 0.033, 0.023), 'middle': (0.046, 0.040, 0.034, 0.024),   # knuckle .. tip
            'ring': (0.043, 0.038, 0.032, 0.022), 'pinky': (0.038, 0.033, 0.028, 0.020)}
SEGMENT_SPLIT = (0.45, 0.30, 0.25)          # proximal, middle, distal phalanx share of the finger length
FINGER_ROOT = 0.08                          # the finger tube starts this far inside the palm (blends in)
# palm sections: (u, half-width along v, half-thickness along n, centre v, centre n)
PALM = [(-0.06, 0.085, 0.055, 0.0, 0.0), (0.10, 0.150, 0.058, 0.010, -0.005),
        (0.26, 0.185, 0.060, 0.010, -0.008), (0.40, 0.200, 0.055, 0.005, -0.005),
        (0.50, 0.190, 0.047, 0.005, 0.0)]
THENAR = [((0.16, 0.115, -0.045), 0.060), ((0.25, 0.115, -0.04), 0.050)]  # thumb ball, palm side
THUMB_BASE = (0.08, 0.075, -0.035)
THUMB_LEN = (0.20, 0.15, 0.13)              # metacarpal, proximal, distal
THUMB_R = (0.050, 0.048, 0.042, 0.027)
TUBE_STEPS = 4                              # cones per finger segment
TUBE_SMOOTH = 1.0                           # samples: rounds the knuckles of a curled finger
NAIL_LEN, NAIL_WIDTH = 0.42, 0.72           # nail size: share of the distal segment, of its radius

# gesture: per-finger (spread, mcp, pip, dip) radians; thumb = target tip position (u, v, n).
# Curl grows from index to pinky, as in a resting hand.
GESTURES = {
    'relaxed': dict(fingers={'index': (0.05, 0.25, 0.35, 0.18), 'middle': (0.0, 0.32, 0.45, 0.22),
                             'ring': (-0.04, 0.38, 0.52, 0.26), 'pinky': (-0.09, 0.45, 0.58, 0.30)},
                    thumb=(0.50, 0.30, -0.08)),
    'hip': dict(fingers={'index': (0.04, 0.12, 0.16, 0.08), 'middle': (0.0, 0.15, 0.18, 0.09),
                         'ring': (-0.03, 0.18, 0.21, 0.10), 'pinky': (-0.07, 0.22, 0.25, 0.12)},
                thumb=(0.42, 0.20, -0.10)),
    'hair': dict(fingers={'index': (0.09, 0.30, 0.30, 0.15), 'middle': (0.01, 0.35, 0.35, 0.18),
                          'ring': (-0.06, 0.38, 0.40, 0.20), 'pinky': (-0.13, 0.42, 0.45, 0.22)},
                 thumb=(0.48, 0.32, -0.12)),
    'chin': dict(fingers={'index': (0.04, 0.55, 1.45, 0.60), 'middle': (0.0, 0.65, 1.50, 0.60),
                          'ring': (-0.03, 0.72, 1.50, 0.60), 'pinky': (-0.06, 0.80, 1.50, 0.60)},
                 thumb=(0.42, 0.10, -0.24)),
    'cover': dict(fingers={'index': (0.04, 0.10, 0.12, 0.06), 'middle': (0.0, 0.12, 0.14, 0.07),
                           'ring': (-0.03, 0.14, 0.16, 0.07), 'pinky': (-0.07, 0.17, 0.18, 0.09)},
                  thumb=(0.52, 0.27, -0.04)),
    'clasp': dict(fingers={'index': (0.02, 0.80, 1.05, 0.50), 'middle': (0.0, 0.88, 1.10, 0.52),
                           'ring': (-0.02, 0.92, 1.12, 0.52), 'pinky': (-0.04, 0.98, 1.15, 0.55)},
                  thumb=(0.42, 0.04, -0.28)),
    'pocket': dict(fingers={'index': (0.02, 0.80, 1.05, 0.50), 'middle': (0.0, 0.88, 1.10, 0.52),    # a loose fist
                            'ring': (-0.02, 0.92, 1.12, 0.52), 'pinky': (-0.04, 0.98, 1.15, 0.55)},     # hidden in cloth
                   thumb=(0.42, 0.04, -0.28)),
    'prop': dict(fingers={'index': (0.06, 0.15, 0.20, 0.10), 'middle': (0.0, 0.18, 0.22, 0.10),
                          'ring': (-0.05, 0.22, 0.26, 0.12), 'pinky': (-0.10, 0.28, 0.30, 0.14)},
                 thumb=(0.55, 0.25, -0.08)),
}


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-9)


def hand_basis(u_dir, n_dir, side):
    """World axes of the hand. side = +1 right hand, -1 left hand (anatomical)."""
    u = unit(u_dir)
    n = unit(np.asarray(n_dir, float) - np.dot(n_dir, u) * u)
    v = np.cross(u, n) if side > 0 else np.cross(n, u)
    return u, v, n


class HandSpace:
    def __init__(self, wrist, u_dir, n_dir, side, scale=1.0):
        self.o = np.asarray(wrist, float)
        self.u, self.v, self.n = hand_basis(u_dir, n_dir, side)
        self.s = scale
        self.nails = []

    def p(self, local):
        a, b, c = local
        return self.o + (self.u * a + self.v * b + self.n * c) * self.s

    def d(self, local):
        a, b, c = local
        return unit(self.u * a + self.v * b + self.n * c)


def finger_joints(name, spread, flex):
    """Hand-local knuckle, two inner joints, tip, and the back-of-finger direction of each segment."""
    base_dir = np.array([np.cos(spread), np.sin(spread), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    pos = np.array([FINGER_MCP_U[name], FINGER_V[name], 0.0])
    pts, backs, total = [pos], [], 0.0
    for seg, angle in zip(SEGMENT_SPLIT, flex):
        total += angle
        pos = pos + (base_dir * np.cos(total) - up * np.sin(total)) * FINGER_LEN[name] * seg
        pts.append(pos)
        backs.append(base_dir * np.sin(total) + up * np.cos(total))
    return np.array(pts), backs


def thumb_joints(tip):
    """Hand-local thumb joints bent along an arc so the tip lands on `tip`, and the nail direction.

    Why an arc: the thumb's joints flex together, so a constant-curvature curve between
    the base and the target looks natural for every gesture.
    """
    base = np.asarray(THUMB_BASE, float)
    chord = np.asarray(tip, float) - base
    c = np.linalg.norm(chord)
    lengths = np.asarray(THUMB_LEN)
    total = lengths.sum()
    d = chord / max(c, 1e-9)
    bend = np.array([0.0, 0.0, -1.0]) - d * (-d[2])          # curl toward the palm side
    bend = unit(bend if np.linalg.norm(bend) > 1e-6 else np.array([0.0, -1.0, 0.0]))
    lo, hi = 0.0, np.pi * 0.9                                 # total turning angle of the arc
    for _ in range(40):
        mid = (lo + hi) / 2
        if np.linalg.norm(_arc_points(lengths, mid)[-1]) > min(c, total * 0.999):
            lo = mid
        else:
            hi = mid
    pts = _arc_points(lengths, (lo + hi) / 2)
    end = pts[-1]
    ang = np.arctan2(end[1], end[0])
    rot = np.array([[np.cos(-ang), -np.sin(-ang)], [np.sin(-ang), np.cos(-ang)]])
    pts = pts @ rot.T
    scale = c / max(np.linalg.norm(pts[-1]), 1e-9) if c > total else 1.0
    local = np.array([base + (d * x + bend * y) * scale for x, y in pts])
    seg = unit(local[-1] - local[-2])
    nail_dir = unit(-(bend - np.dot(bend, seg) * seg))          # the nail faces away from the curl
    return local, nail_dir


def _arc_points(lengths, turn):
    """Polyline with equal turning at each joint, starting at the origin heading along +x."""
    pts, pos, heading = [np.zeros(2)], np.zeros(2), -turn / 2
    step = turn / max(len(lengths) - 1, 1)
    for length in lengths:
        pos = pos + length * np.array([np.cos(heading), np.sin(heading)])
        pts.append(pos)
        heading += step
    return np.array(pts)


def nail_outline(dip, tip, back, radius, n=12):
    """Hand-local rounded nail on the back of the distal segment (dip -> tip)."""
    along = unit(tip - dip)
    across = unit(np.cross(along, back))
    length = np.linalg.norm(tip - dip)
    centre = dip + (tip - dip) * 0.60 + back * radius * 0.92
    half_l, half_w = length * NAIL_LEN / 2, radius * NAIL_WIDTH
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    sq = np.sign(np.cos(a)) * np.abs(np.cos(a)) ** 0.8, np.sign(np.sin(a)) * np.abs(np.sin(a)) ** 0.8
    return np.array([centre + along * half_l * x + across * half_w * y - back * radius * 0.25 * y * y
                     for x, y in zip(*sq)])


def hand_pieces(prefix, wrist, u_dir, n_dir, side, gesture, parent, forearm_r=None, scale=1.0):
    """Palm piece (attached to `parent`, normally the forearm piece) plus finger and thumb pieces.

    Returns (pieces, hand space); hand_space.nails lists (name, world outline, world back direction).
    """
    g = GESTURES.get(gesture)
    if g is None:
        raise ValueError(f"unknown hand gesture '{gesture}' (use {', '.join(GESTURES)})")
    hs = HandSpace(wrist, u_dir, n_dir, side, scale)
    sc = scale

    def lift(local_pts):
        return [hs.p(p) for p in local_pts]
    wrist_w = (forearm_r if forearm_r is not None else PALM[0][1]) * 0.9
    sections = [(u, (wrist_w if i == 0 else w) * sc, t * sc, hs.p((u, cv, cn))) for i, (u, w, t, cv, cn) in enumerate(PALM)]
    axes = [sections[i + 1][3] - sections[i][3] for i in range(len(sections) - 1)]
    palm = [ellipse_cone(sections[i][3], sections[i + 1][3], sections[i][1], sections[i][2],
                         sections[i + 1][1], sections[i + 1][2], hs.v, hs.v,
                         axes[i - 1] if i > 0 else None, axes[i + 1] if i < len(axes) - 1 else None)
            for i in range(len(axes))]
    palm += [sphere(hs.p(c), r * sc) for c, r in THENAR]
    pieces = [Piece(f'{prefix}_palm', palm, k=0.04, parent=parent, attach_k=0.05, attach_n=1,
                    skip_contour_with=[parent])]
    for f in FINGERS:
        spread, *flex = g['fingers'][f]
        joints, backs = finger_joints(f, spread, flex)
        root = joints[0] - np.array([FINGER_ROOT, FINGER_V[f] * 0.1, 0.01])
        radii = [FINGER_R[f][0] * 0.95] + list(FINGER_R[f])
        solids = tube(lift(np.vstack([root, joints])), [r * sc for r in radii], TUBE_STEPS, TUBE_SMOOTH)
        pieces.append(Piece(f'{prefix}_{f}', solids, k=0.004, parent=f'{prefix}_palm', attach_k=0.035,
                            attach_n=TUBE_STEPS))
        nail = nail_outline(joints[2], joints[3], backs[2], FINGER_R[f][3] * 1.25)
        hs.nails.append((f'{prefix}_{f}', np.array(lift(nail)), hs.d(backs[2])))
    joints, nail_dir = thumb_joints(g['thumb'])
    solids = tube(lift(joints), [r * sc for r in THUMB_R], TUBE_STEPS, TUBE_SMOOTH)
    pieces.append(Piece(f'{prefix}_thumb', solids, k=0.004, parent=f'{prefix}_palm', attach_k=0.05,
                        attach_n=TUBE_STEPS))
    nail = nail_outline(joints[2], joints[3], nail_dir, THUMB_R[3] * 1.3)
    hs.nails.append((f'{prefix}_thumb', np.array(lift(nail)), hs.d(nail_dir)))
    return pieces, hs
