"""3D hand: palm block + five jointed fingers, posed by gesture presets.

Why 3D: a hand turns and curls in depth, and its 2D silhouette changes
completely with orientation. Building it as a skeleton (palm, metacarpal
knuckles, three phalanges per finger) and projecting keeps every view
consistent. Fingers are capsules, which project to capsules of the same
radius, so foreshortening comes for free.

Canonical frame (image-right hand): wrist at the origin, fingers point to -y,
palm faces +z, thumb on the -x side. Units are head heights (H). Anime hands
are drawn a little smaller than life; total length here is about 0.62 H.
"""
import cv2
import numpy as np

from . import geom

WRIST_HALF = 0.092
PALM_THICK = 0.055
# metacarpal knuckles (MCP) and phalanx lengths, index -> pinky
MCP = np.array([(-0.092, -0.330, 0.0), (-0.030, -0.345, 0.0), (0.030, -0.335, 0.0), (0.088, -0.305, 0.0)])
PHALANX = np.array([(0.110, 0.070, 0.060), (0.122, 0.080, 0.066), (0.115, 0.075, 0.062), (0.090, 0.056, 0.052)])
FINGER_W = np.array([(0.060, 0.054, 0.046), (0.062, 0.056, 0.048), (0.058, 0.052, 0.045), (0.050, 0.045, 0.040)])
PALM = [(-0.060, 0.0), (-0.108, -0.090), (-0.116, -0.250), (-0.100, -0.338), (-0.032, -0.358), (0.032, -0.348),
        (0.098, -0.315), (0.115, -0.190), (0.066, 0.0)]
THUMB_BASE = np.array([-0.080, -0.065, 0.020])
THUMB_LEN = (0.135, 0.100, 0.085)
THUMB_W = (0.085, 0.070, 0.060)

# curl: flexion (rad) of the three joints per finger; spread: abduction (rad, + toward pinky)
GESTURES = {
    "open":    {"curl": [(0.08, 0.06, 0.04)] * 4, "spread": [-0.13, -0.04, 0.05, 0.15],
                "thumb": {"abd": 0.75, "opp": 0.15, "curl": (0.05, 0.10)}},
    "relaxed": {"curl": [(0.30, 0.45, 0.28), (0.38, 0.50, 0.30), (0.46, 0.55, 0.32), (0.55, 0.60, 0.35)],
                "spread": [-0.05, -0.01, 0.03, 0.08], "thumb": {"abd": 0.18, "opp": 0.30, "curl": (0.25, 0.30)}},
    "flat":    {"curl": [(0.15, 0.22, 0.12), (0.18, 0.24, 0.12), (0.22, 0.26, 0.14), (0.26, 0.30, 0.16)],
                "spread": [-0.03, 0.0, 0.03, 0.06], "thumb": {"abd": 0.35, "opp": 0.30, "curl": (0.15, 0.15)}},
    # wraps a can: knuckles barely bent so the first phalanges lie across its front, then the middle and last
    # phalanges turn away from the viewer around its far edge (their projection ends as rounded knuckles)
    "grip":    {"curl": [(0.30, 1.30, 0.80)] * 4, "spread": [-0.03, 0.0, 0.02, 0.05],
                "thumb": {"abd": 0.30, "opp": 0.60, "curl": (0.30, 0.40)}},
    "fist":    {"curl": [(1.45, 1.55, 0.95)] * 4, "spread": [-0.03, 0.0, 0.02, 0.05],
                "thumb": {"abd": 0.20, "opp": 1.05, "curl": (0.45, 0.55)}},
    "point":   {"curl": [(0.05, 0.05, 0.03), (1.45, 1.55, 0.95), (1.45, 1.55, 0.95), (1.45, 1.55, 0.95)],
                "spread": [-0.04, 0.0, 0.02, 0.05], "thumb": {"abd": 0.30, "opp": 0.95, "curl": (0.45, 0.50)}},
    "peace":   {"curl": [(0.05, 0.05, 0.03), (0.05, 0.05, 0.03), (1.45, 1.55, 0.95), (1.45, 1.55, 0.95)],
                "spread": [-0.20, 0.10, 0.04, 0.07], "thumb": {"abd": 0.30, "opp": 1.00, "curl": (0.45, 0.55)}},
}


def _unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / (np.linalg.norm(v) + 1e-9)


def _chain(base, d0, bend_dir, lengths, angles):
    """Joint positions of a finger bending in the plane of d0 and bend_dir."""
    pts, theta = [np.asarray(base, dtype=np.float64)], 0.0
    for L, a in zip(lengths, angles):
        theta += a
        d = d0 * np.cos(theta) + bend_dir * np.sin(theta)
        pts.append(pts[-1] + d * L)
    return np.array(pts)


def canonical(gesture):
    """Palm box corners and five finger joint chains in the canonical frame."""
    g = GESTURES.get(gesture, GESTURES["relaxed"])
    palm_n = np.array([0.0, 0.0, 1.0])
    fingers = []
    for i in range(4):
        s = g["spread"][i]
        d0 = _unit([np.sin(s), -np.cos(s), 0.0])
        fingers.append((_chain(MCP[i], d0, palm_n, PHALANX[i], g["curl"][i]), FINGER_W[i]))
    t = g["thumb"]
    d0 = _unit([-np.sin(t["abd"]), -np.cos(t["abd"]), t["opp"]])
    bend = _unit(np.array([1.0, 0.0, 0.6]) - d0 * np.dot([1.0, 0.0, 0.6], d0))
    thumb = (_chain(THUMB_BASE, d0, bend, THUMB_LEN, (0.0,) + tuple(t["curl"])), np.array(THUMB_W))
    palm2 = np.array(PALM)
    palm = np.vstack([np.column_stack([palm2, np.full(len(palm2), z)]) for z in (-PALM_THICK / 2, PALM_THICK / 2)])
    return palm, fingers, thumb


def frame(finger_dir, palm_normal):
    """Rotation whose columns are the world images of canonical x, y, z."""
    F = _unit(finger_dir)
    N = np.asarray(palm_normal, dtype=np.float64)
    N = _unit(N - F * np.dot(N, F))
    Y = -F
    X = np.cross(Y, N)
    return np.column_stack([X, Y, N])


def capsule_outline(a, b, wa, wb, n=10):
    """2D outline of a tapered capsule between projected points a and b."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    spine = np.array([a + (b - a) * t for t in np.linspace(0, 1, n)])
    if np.linalg.norm(b - a) < 1e-6:
        return geom.ellipse(*a, wa / 2, wa / 2, 24)
    w = np.linspace(wa, wb, n)
    ang = np.linspace(-np.pi / 2, np.pi / 2, 9)
    d = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([-d[1], d[0]])
    cap_b = [b + (d * np.cos(t) + nrm * np.sin(t)) * wb / 2 for t in ang]
    cap_a = [a + (-d * np.cos(t) - nrm * np.sin(t)) * wa / 2 for t in ang]
    left = spine + nrm * (w[:, None] / 2)
    right = spine - nrm * (w[:, None] / 2)
    return np.vstack([left, cap_b[::-1], right[::-1], cap_a[::-1]])


def posed_parts(gesture, wrist, finger_dir, palm_normal, side, to_canvas, H, scale=1.0):
    """Return parts [(name, polys, depth)] sorted back to front.

    finger_dir and palm_normal describe the image-right hand; side=-1 mirrors
    them for the image-left hand. wrist is the real (already mirrored) position.
    to_canvas maps body-local 3D (N, 3) to canvas px.
    """
    mir = np.array([side, 1.0, 1.0])
    # the image-left hand is the mirror image of the posed image-right hand
    R = frame(finger_dir, palm_normal)
    wrist = np.asarray(wrist, dtype=np.float64)

    def world(P):
        return (np.asarray(P) * scale @ R.T) * mir + wrist

    H = H * scale   # finger widths scale with the hand

    palm, fingers, thumb = canonical(gesture)
    pw = world(palm)
    pc = to_canvas(pw)
    tb = world(thumb[0][:2])
    tc = to_canvas(tb)
    # the thumb metacarpal (thenar mass) merges with the palm silhouette
    palm_polys = [pc[_hull(pc)], capsule_outline(tc[0], tc[1], THUMB_W[0] * H * 1.05, THUMB_W[0] * H)]
    parts = [("palm", palm_polys, pw[:, 2].mean())]
    for k, (chain, widths) in enumerate(fingers + [thumb]):
        cw = world(chain)
        cc = to_canvas(cw)
        first = 1 if k == 4 else 0
        polys = [capsule_outline(cc[j], cc[j + 1], widths[j] * H, widths[j] * H * 0.92)
                 for j in range(first, len(cc) - 1)]
        # fingers sort by the depth of their outer joints
        parts.append(("thumb" if k == 4 else f"finger{k}", polys, cw[1:, 2].mean()))
    parts.sort(key=lambda p: p[2])
    return parts


def _hull(P):
    return cv2.convexHull(P.astype(np.float32), returnPoints=False)[:, 0]
