"""Procedural hair: locks are grown from the scalp, combed, pulled by gravity and kept off the body.

Each lock is a tapered tube. Growing them in posed space means long hair drapes over
whatever the shoulders and back are doing, with no rigging.
"""
import numpy as np
from scipy.spatial import cKDTree

from .mesh import Mesh, cut_by_margin
from .noise import rng

# Template-space head description (default adult, metres; front is -Y, up is +Z).
HEAD_CENTER = np.array([0.0, -0.055, 0.915])
HEAD_MIN_Z = 0.80
CROWN = (0.0, 0.0, 1.01)
HAIRLINE_SETBACK_DEG = 5.0
# the face stays visible: free-hanging locks may not cross this box in template space (front of the head, chin to brow)
EAR_PAD_X = 0.074                # template |x| of the pad that covers each ear for hair collision
FACE_GUARD_Y, FACE_GUARD_HALF_WIDTH, FACE_GUARD_Z = -0.085, 0.078, (0.775, 0.935)
NECK_GUARD_Y, NECK_GUARD_HALF_WIDTH, NECK_GUARD_Z = -0.02, 0.095, 0.66     # front of the neck down to the collarbones
# Hairline: minimum elevation angle (deg) above the head centre, by azimuth (0 = front, 180 = back).
HAIRLINE_AZIMUTH = np.array([0, 25, 45, 62, 78, 95, 125, 180.0])
HAIRLINE_ELEVATION = np.array([34, 33, 28, 15, 4, -10, -30, -42.0])

LOCK_SIDES = 6
SEGMENTS = 22
COLLISION_MARGIN = 0.004
QUIFF_AZIMUTH = 45.0             # degrees from the front over which a quiff lifts
STYLED_HUG = 0.25                # how firmly styled locks are drawn onto the head
LIFT_SCATTER = 0.12              # randomness of lifted (textured) locks
SHEEN_TINT_GAIN, SHEEN_WHITE = 1.5, 0.35   # sheen colour = hair colour lifted plus a little white
SHEEN_SMOOTH_PX = 4.0            # neighbourhood (output pixels) over which strand directions are averaged for the sheen
FUZZ_CELL = 0.0025               # size of the speckle on a cropped shell (m)
CAP_THICKNESS = 0.0045           # default scalp shell under the locks
THICKNESS_RATIO = 0.42
# width left at the end of a lock: needle tips drew a ragged fringe of ink spikes along the hem in line styles
LOCK_TIP = 0.3
BLUNT_TIP = 0.35                 # styles cut to a hem line (bob, shoulder)
SMOOTHING_PASSES = 3
CLOTH_CLEARANCE = 0.003          # locks lie this far outside clothing
CLOTH_REACH = 0.05               # clothing farther than this from a lock ring does not move it
CLOTH_LIFT_SPREAD = 4            # passes that spread a lift along the lock so it bends instead of kinking
CLOTH_LIFT_PASSES = 6            # repeated moves for rings deep inside loose cloth
CLOTH_SETTLED = 0.0005           # a pass that would move no ring farther than this ends the lifting

# length in metres per zone; wave = lateral amplitude (m); curl = helix radius (m)
STYLES = {
    "long_straight": dict(back=0.52, side=0.46, wave=0.0, curl=0.0, volume=0.8),
    "long_wavy":     dict(back=0.50, side=0.44, wave=0.016, curl=0.0, volume=1.25),
    "very_long":     dict(back=0.85, side=0.75, wave=0.004, curl=0.0, volume=1.0),
    "shoulder":      dict(back=0.36, side=0.34, wave=0.003, curl=0.0, volume=0.9, hem=0.715),
    "bob":           dict(back=0.26, side=0.26, wave=0.0, curl=0.0, volume=1.0, hem=0.800),
    "pixie":         dict(back=0.055, side=0.06, top=0.09, wave=0.004, curl=0.0, volume=1.3),
    "short_crop":    dict(back=0.03, side=0.03, top=0.05, wave=0.0, curl=0.0, volume=0.5, shell=(0.005, 0.010), lock_scale=0.4,
                          density=2.0, styled=0.7),
    # short men's cuts: a shaped shell carries the volume, thin locks on top give the texture
    "buzz":          dict(shell=(0.0025, 0.0035), locks=False),
    "textured_crop": dict(back=0.03, side=0.025, top=0.07, wave=0.004, curl=0.0, volume=0.5, shell=(0.004, 0.013),
                          lock_scale=0.38, density=2.5, lift=0.12, top_only=0.1, styled=0.8, quiff=0.4),
    "side_part":     dict(back=0.035, side=0.03, top=0.11, wave=0.002, curl=0.0, volume=0.6, shell=(0.005, 0.012),
                          lock_scale=0.4, density=2.5, comb="part", top_only=0.0, styled=0.85, quiff=0.3),
    "undercut":      dict(back=0.02, side=0.015, top=0.13, wave=0.003, curl=0.0, volume=0.7, shell=(0.002, 0.011),
                          lock_scale=0.45, density=2.5, comb="back", top_only=0.45, styled=0.9, quiff=0.45),
    "long_male":     dict(back=0.30, side=0.27, wave=0.007, curl=0.0, volume=0.9, hem=0.730),
    "man_bun":       dict(tie=(0.0, 0.050, 0.945), bun=0.036, volume=0.8),
    "curly":         dict(back=0.30, side=0.28, wave=0.006, curl=0.016, volume=1.6),
    "afro":          dict(back=0.10, side=0.10, top=0.10, wave=0.0, curl=0.012, volume=2.4, stiff=True),
    "slick_back":    dict(back=0.16, side=0.14, wave=0.0, curl=0.0, volume=0.8, comb="back", styled=0.8),
    "ponytail":      dict(tie=(0.0, 0.035, 0.955), tail=0.42, wave=0.004, volume=0.85),
    "low_ponytail":  dict(tie=(0.0, 0.050, 0.875), tail=0.45, wave=0.003, volume=0.85),
    "bun":           dict(tie=(0.0, 0.030, 0.975), bun=0.045, volume=0.85),
    "chignon":       dict(tie=(0.0, 0.055, 0.880), bun=0.042, volume=0.9),
}
# bangs: (max length in metres, template z where the fringe is cut)
BANGS = {"none": None, "wispy": (0.10, 0.932), "full": (0.11, 0.927), "side": (0.14, 0.918),
         "curtain": (0.16, 0.885), "long": (0.18, 0.875)}
BANG_DENSITY = {"wispy": 0.35, "full": 1.0, "side": 0.8, "curtain": 0.8, "long": 0.8}    # share of fringe roots that become bangs


def _unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def _kabsch(source, target):
    """Rotation that best maps centred source points onto centred target points."""
    a, b = source - source.mean(0), target - target.mean(0)
    u, _, vt = np.linalg.svd(a.T @ b)
    d = np.sign(np.linalg.det(u @ vt))
    return (u @ np.diag([1, 1, d]) @ vt).T


def _scalp_weight(tpl):
    """> 0 for template points above the hairline; magnitude = degrees above it."""
    d = tpl - HEAD_CENTER
    azimuth = np.degrees(np.arctan2(np.abs(d[:, 0]), -d[:, 1]))
    elevation = np.degrees(np.arctan2(d[:, 2], np.hypot(d[:, 0], d[:, 1])))
    return elevation - np.interp(azimuth, HAIRLINE_AZIMUTH, HAIRLINE_ELEVATION)


class Body:
    """Posed body surface used for scalp sampling and hair/cloth collision."""

    def __init__(self, figure):
        from .figure import BODY_RANGE
        self.vertices = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]]
        self.tpl = figure.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1]].astype(np.float64)
        faces = figure.faces
        self.faces = faces[(faces < BODY_RANGE[1]).all(1)]
        self.normals = Mesh(figure.vertices, self.faces).vertex_normals()[BODY_RANGE[0]:BODY_RANGE[1]]
        head = self.tpl[:, 2] > HEAD_MIN_Z
        self.head_rotation = _kabsch(self.tpl[head], self.vertices[head])   # template dir -> world dir
        self.head_center = self.vertices[head].mean(0) + self.head_rotation @ (HEAD_CENTER - self.tpl[head].mean(0))
        self.scale = np.linalg.norm(self.vertices[head] - self.vertices[head].mean(0), axis=1).mean() / \
            np.linalg.norm(self.tpl[head] - self.tpl[head].mean(0), axis=1).mean()
        # hair collides with a flat pad over each ear instead of the ear's folds, so locks lie over it without snagging
        ear = head & (np.abs(self.tpl[:, 0]) > EAR_PAD_X) & (self.tpl[:, 2] < 0.905)
        side = np.sign(self.tpl[ear, 0])[:, None] * (self.head_rotation @ np.array([1.0, 0.0, 0.0]))[None]
        self.collide_points = self.vertices.copy()
        self.collide_normals = self.normals.copy()
        self.collide_points[ear] -= side * ((np.abs(self.tpl[ear, 0]) - EAR_PAD_X) * self.scale)[:, None]
        self.collide_normals[ear] = side
        self.tree = cKDTree(self.collide_points)

    def to_world(self, tpl_point):
        return self.head_center + self.scale * (self.head_rotation @ (np.asarray(tpl_point) - HEAD_CENTER))

    def keep_off_face(self, points, guard):
        """Slide points that hang in front of the face out to its sides (guard: per-point bool)."""
        local = HEAD_CENTER + ((points - self.head_center) @ self.head_rotation) / self.scale
        x, y, z = local[:, 0], local[:, 1], local[:, 2]
        on_face = (y < FACE_GUARD_Y) & (np.abs(x) < FACE_GUARD_HALF_WIDTH) & (z > FACE_GUARD_Z[0]) & (z < FACE_GUARD_Z[1])
        # below the chin, locks would gather down the middle of the chest; real hair parts round the neck instead
        on_throat = (y < NECK_GUARD_Y) & (np.abs(x) < NECK_GUARD_HALF_WIDTH) & (z > NECK_GUARD_Z) & (z <= FACE_GUARD_Z[0])
        inside = guard & (on_face | on_throat)
        if not inside.any():
            return points
        side = np.where(x >= 0, 1.0, -1.0)
        width = np.where(on_throat, NECK_GUARD_HALF_WIDTH, FACE_GUARD_HALF_WIDTH)
        local[inside, 0] = (side * width)[inside]
        moved = self.head_center + self.scale * ((local - HEAD_CENTER) @ self.head_rotation.T)
        return np.where(inside[:, None], moved, points)

    def push_out(self, points, margin):
        """Move points that are closer than `margin` to the skin back out along the skin normal."""
        _, nearest = self.tree.query(points)
        normal = self.collide_normals[nearest]
        distance = np.sum((points - self.collide_points[nearest]) * normal, axis=1)
        deficit = np.maximum(np.asarray(margin) - distance, 0.0)
        return points + normal * deficit[:, None], normal


def _tube(paths, widths, normals, material, part, sides=LOCK_SIDES):
    """Sweep a flattened ellipse along each path. paths: (L, S, 3), widths: (L, S), normals: (L, S, 3)."""
    n_locks, n_seg, _ = paths.shape
    tangent = _unit(np.gradient(paths, axis=1))
    normal = _unit(normals - tangent * np.sum(normals * tangent, -1, keepdims=True))
    binormal = np.cross(tangent, normal)
    theta = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = (np.cos(theta)[None, None, :, None] * binormal[:, :, None, :] * widths[:, :, None, None] +
            np.sin(theta)[None, None, :, None] * normal[:, :, None, :] * (widths * THICKNESS_RATIO)[:, :, None, None])
    vertices = (paths[:, :, None, :] + ring).reshape(-1, 3)
    tangents = np.repeat(tangent[:, :, None, :], sides, axis=2).reshape(-1, 3)
    lock, seg, side = np.meshgrid(np.arange(n_locks), np.arange(n_seg - 1), np.arange(sides), indexing="ij")
    nxt = (side + 1) % sides
    index = lambda l, s, k: (l * n_seg + s) * sides + k
    a, b, c, d = index(lock, seg, side), index(lock, seg, nxt), index(lock, seg + 1, nxt), index(lock, seg + 1, side)
    faces = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    lock_id = np.repeat(np.arange(n_locks), n_seg * sides).astype(np.float32)
    return Mesh(vertices, faces, material, part, None,
                {"tangent": tangents.astype(np.float32), "lock": lock_id})


def _grow(body, roots, root_normals, first_dir, lengths, margins, target_fn, stiffness, generator, segments=SEGMENTS,
          face_guard=None):
    """Integrate lock centre lines. Returns paths (L, S, 3) and outward normals (L, S, 3)."""
    count = len(roots)
    paths = np.zeros((count, segments, 3))
    normals = np.zeros((count, segments, 3))
    position, _ = body.push_out(roots, margins)
    direction = _unit(first_dir)
    paths[:, 0], normals[:, 0] = position, root_normals
    step = lengths / (segments - 1)
    for s in range(1, segments):
        progress = s / (segments - 1)
        target = target_fn(position, progress)
        blend = np.clip(stiffness(progress), 0, 1)[..., None] if callable(stiffness) else stiffness
        direction = _unit(direction * (1 - blend) + target * blend)
        moved = position + direction * step[:, None]
        moved, normal = body.push_out(moved, margins)
        if face_guard is not None:
            moved = body.keep_off_face(moved, face_guard)
        direction = _unit(moved - position)
        position = moved
        paths[:, s], normals[:, s] = position, normal
    for _ in range(SMOOTHING_PASSES):       # nearest-vertex collision is noisy; relax the centre line
        paths[:, 1:-1] = 0.5 * paths[:, 1:-1] + 0.25 * (paths[:, :-2] + paths[:, 2:])
        normals[:, 1:-1] = 0.5 * normals[:, 1:-1] + 0.25 * (normals[:, :-2] + normals[:, 2:])
        # relaxing cuts corners (over a raised shoulder, round the neck): collide again so no lock runs under the skin
        flat = paths[:, 1:].reshape(-1, 3)
        pushed, _ = body.push_out(flat, np.repeat(margins, segments - 1) if np.ndim(margins) else margins)
        paths[:, 1:] = pushed.reshape(count, segments - 1, 3)
    return paths, normals


def _trim(paths, body, hem_z, jitter, generator, select=None):
    """Cut locks where they cross a height in the head frame (a scissor line), keeping the segment count."""
    up = body.head_rotation @ np.array([0, 0, 1.0])
    level = (paths - body.head_center) @ up / body.scale + HEAD_CENTER[2]      # template-space height
    limit = np.asarray(hem_z) + generator.uniform(-jitter, jitter, (len(paths), 1))
    below = level < limit
    segments = paths.shape[1]
    first = np.where(below.any(1), below.argmax(1), segments - 1).astype(float)
    if select is not None:
        first = np.where(select, first, segments - 1)
    first = np.maximum(first, 2)
    # resample each lock over [0, first] so the tube keeps its taper
    sample = np.linspace(0, 1, segments)[None, :] * first[:, None]
    lo = np.floor(sample).astype(int); hi = np.minimum(lo + 1, segments - 1); frac = (sample - lo)[..., None]
    rows = np.arange(len(paths))[:, None]
    return paths[rows, lo] * (1 - frac) + paths[rows, hi] * frac


def _profile(segments, root=0.55, tip=0.0, peak_at=0.35):
    """Lock width along its length: narrow root, full body, tapering tip."""
    t = np.linspace(0, 1, segments)
    rise = root + (1 - root) * np.sin(np.clip(t / peak_at, 0, 1) * np.pi / 2)
    fall = tip + (1 - tip) * np.cos(np.clip((t - 0.55) / 0.45, 0, 1) * np.pi / 2) ** 0.8
    return np.minimum(rise, fall)


def _wave(paths, normals, amplitude, curl, generator):
    """Add waves (side to side) and curls (helix) that grow away from the root."""
    count, segments, _ = paths.shape
    tangent = _unit(np.gradient(paths, axis=1))
    side = _unit(np.cross(tangent, normals))
    t = np.linspace(0, 1, segments)[None, :]
    grow = np.clip(t * 2.2, 0, 1)
    phase = generator.random((count, 1)) * 2 * np.pi
    frequency = generator.uniform(2.2, 3.2, (count, 1))
    out = paths + side * (amplitude * grow * np.sin(2 * np.pi * frequency * t + phase))[..., None]
    if curl:
        turns = generator.uniform(3.5, 5.5, (count, 1))
        angle = 2 * np.pi * turns * t + phase
        out = out + (side * np.cos(angle)[..., None] + _unit(normals) * np.sin(angle)[..., None]) * (curl * grow)[..., None]
    return out


def _shell_thickness(tpl, shell):
    """Stand-off of the hair shell: `shell` = (sides and back, crown). Short cuts are fuller on top."""
    sides, crown = shell
    height = np.clip((tpl[:, 2] - HEAD_CENTER[2]) / 0.09, 0, 1)
    return sides + (crown - sides) * height ** 0.7


def make_hair(figure, style="long_straight", bangs="none", part="center", color_material=None,
              density=1.0, seed=7, length_scale=1.0, wind=(0.0, 0.0, 0.0), lock_width=0.021, face_framing=0.2):
    """Return hair meshes for a figure.

    style: key of STYLES.  bangs: key of BANGS.  part: 'center' | 'left' | 'right' | 'none'.
    wind: world-space push on free-hanging hair, e.g. (0.4, 0, 0).
    face_framing: 0 = front hair is swept back behind the ears (face fully open), 1 = it falls forward beside the face.
    """
    if style == "bald":
        return []
    spec = dict(STYLES[style])
    material = color_material or f"{figure.name}.hair"
    generator = rng(seed, 101)
    body = Body(figure)
    weight = _scalp_weight(body.tpl)
    on_head = body.tpl[:, 2] > HEAD_MIN_Z
    scalp = np.flatnonzero((weight > 0) & on_head)
    # denser roots: add midpoints of scalp edges
    keep = np.isin(body.faces, scalp).all(1)
    scalp_faces = body.faces[keep]
    mid = lambda a, b: (body.vertices[a] + body.vertices[b]) / 2
    extra_pos = np.concatenate([mid(scalp_faces[:, i], scalp_faces[:, (i + 1) % 3]) for i in range(3)])
    extra_tpl = np.concatenate([(body.tpl[scalp_faces[:, i]] + body.tpl[scalp_faces[:, (i + 1) % 3]]) / 2 for i in range(3)])
    extra_nrm = _unit(np.concatenate([body.normals[scalp_faces[:, i]] + body.normals[scalp_faces[:, (i + 1) % 3]] for i in range(3)]))
    roots = np.concatenate([body.vertices[scalp], extra_pos])
    tpl = np.concatenate([body.tpl[scalp], extra_tpl])
    nrm = np.concatenate([body.normals[scalp], extra_nrm])
    # locks start a little behind the hairline; the scalp cap draws the hairline itself, as one clean curve
    inside = _scalp_weight(tpl) > HAIRLINE_SETBACK_DEG
    roots, tpl, nrm = roots[inside], tpl[inside], nrm[inside]
    n_target = int(len(scalp) * 1.6 * density * spec.get("density", 1.0))
    pick = generator.choice(len(roots), size=min(n_target, len(roots)), replace=False)
    roots, tpl, nrm = roots[pick], tpl[pick], nrm[pick]

    if "top_only" in spec:          # sides and back are clipped to the shell; locks grow only on top
        keep = (tpl[:, 2] - HEAD_CENTER[2]) / 0.09 > spec["top_only"]
        roots, tpl, nrm = roots[keep], tpl[keep], nrm[keep]
    shell = spec.get("shell", (CAP_THICKNESS, CAP_THICKNESS))

    rot = body.head_rotation
    front, up, left = rot @ np.array([0, -1.0, 0]), rot @ np.array([0, 0, 1.0]), rot @ np.array([1.0, 0, 0])
    d = tpl - HEAD_CENTER
    azimuth = np.degrees(np.arctan2(np.abs(d[:, 0]), -d[:, 1]))          # 0 front .. 180 back
    above = _scalp_weight(tpl)                                             # degrees above hairline
    height = np.clip((d[:, 2]) / 0.09, -1, 1)                              # -1 nape .. 1 crown
    gravity = _unit(np.array([0, 0, -1.0]) + np.asarray(wind, float))
    volume = spec.get("volume", 1.0)
    # higher roots lie on top of lower ones, so they get a larger stand-off from the skin
    layer = np.clip((height + 1) / 2, 0, 1)
    margins = COLLISION_MARGIN + 0.009 * volume * layer + generator.uniform(0, 0.003, len(roots))
    margins = margins + _shell_thickness(tpl, shell) - CAP_THICKNESS      # locks lie on the shell, not under it
    meshes = []
    width = lock_width * spec.get("lock_scale", 1.0) * generator.uniform(0.8, 1.25, len(roots))

    part_x = {"center": 0.0, "left": 0.03, "right": -0.03, "none": 0.0}[part]
    side_sign = np.where(tpl[:, 0] >= part_x, 1.0, -1.0)

    if spec.get("locks", True) is False:
        pass
    elif "tie" in spec:
        tie = body.to_world(spec["tie"])
        tie, _ = body.push_out(tie[None], 0.012)
        tie = tie[0]
        to_tie = np.linalg.norm(roots - tie, axis=1)
        lengths = to_tie * 1.12 + 0.01
        target = lambda pos, progress: _unit(tie - pos)
        first = _unit((tie - roots) - nrm * np.sum((tie - roots) * nrm, 1, keepdims=True))
        paths, normals = _grow(body, roots, nrm, first, lengths, margins * 0.6, target, 0.75, generator)
        widths = width[:, None] * _profile(SEGMENTS, root=0.8, tip=0.5)[None]
        meshes.append(_tube(paths, widths, normals, material, material))
        tie_normal = _unit(tie - body.head_center)
        if "tail" in spec:
            n_tail = int(46 * density)
            spread = _unit(generator.normal(0, 1, (n_tail, 3)))
            start = tie + spread * 0.012
            first = _unit(tie_normal * 1.0 + np.array([0, 0, -0.25]) + spread * 0.25)
            lengths = spec["tail"] * length_scale * generator.uniform(0.85, 1.05, n_tail)
            free = lambda pos, progress: np.broadcast_to(gravity, pos.shape)
            stiff = lambda progress: np.full(n_tail, 0.10 + 0.25 * progress)
            paths, normals = _grow(body, start, np.broadcast_to(tie_normal, start.shape), first, lengths,
                                   np.full(n_tail, 0.012) + generator.uniform(0, 0.025, n_tail), free, stiff, generator)
            paths = _wave(paths, normals, spec.get("wave", 0.0), 0.0, generator)
            widths = (lock_width * 1.1) * _profile(SEGMENTS, root=0.5)[None] * generator.uniform(0.8, 1.2, (n_tail, 1))
            meshes.append(_tube(paths, widths, normals, material, material))
        if "bun" in spec:
            meshes.append(_bun(tie + tie_normal * spec["bun"] * 0.55, tie_normal, spec["bun"], material, generator))
    else:
        zone_len = np.where(azimuth > 100, spec["back"], spec["side"])
        blend = np.clip((azimuth - 70) / 60, 0, 1)
        zone_len = spec["side"] * (1 - blend) + spec["back"] * blend
        if "top" in spec:                                                   # short cuts: longer on top
            zone_len = zone_len + (spec["top"] - zone_len) * np.clip(height, 0, 1)
        lengths = zone_len * length_scale * generator.uniform(0.9, 1.06, len(roots))
        # long hair measured from the crown: lower roots need less length to reach the same hem
        lengths = np.where(zone_len > 0.12, lengths * (0.72 + 0.28 * layer), lengths)
        comb = spec.get("comb", "part" if part != "none" else "crown")
        sideways = left[None] * side_sign[:, None]
        back = -front[None]
        # front roots are combed back as well as sideways so the hair clears the face
        sweep = back * (0.35 + 1.1 * (1 - face_framing) * np.clip(1 - azimuth[:, None] / 75, 0, 1))
        if comb == "part":          # away from the parting line, then down
            flow = sideways * (1.0 - 0.75 * np.clip((azimuth[:, None] - 60) / 80, 0, 1)) + sweep - up[None] * 0.3
        elif comb == "crown":       # no parting: hair radiates from the crown and falls straight
            crown = body.to_world(CROWN)
            outward = _unit(roots - crown)
            radial = outward * 0.8 - up[None] * 0.6
            # roots whose outward direction points forward go to the sides instead,
            # otherwise the whole top of the head would hang over the face
            aside = sideways * 1.0 + sweep - up[None] * 0.3
            forwardness = np.sum(outward * front[None], 1, keepdims=True)
            rear = np.clip((0.2 - forwardness) / 0.4, 0, 1)
            flow = radial * rear + aside * (1 - rear)
        else:                       # swept straight back (no downward pull, or the front would comb onto the forehead)
            flow = back * 1.0 + sideways * 0.15
        tangent_flow = flow - nrm * np.sum(flow * nrm, 1, keepdims=True)
        # where the comb direction points straight out of the scalp, fall back to "down along the head"
        down = -up[None] - nrm * np.sum(-up[None] * nrm, 1, keepdims=True)
        weak = np.linalg.norm(tangent_flow, axis=1, keepdims=True) < 0.35
        first = _unit(np.where(weak, down + tangent_flow, tangent_flow))
        is_bang = np.zeros(len(roots), bool)
        if BANGS[bangs] is not None:
            is_bang = (azimuth < 55) & (above < 24) & (generator.random(len(roots)) < BANG_DENSITY[bangs])
            lengths = np.where(is_bang, BANGS[bangs][0] + above * 0.0022, lengths)
            sweep = {"side": 0.9, "curtain": 0.0}.get(bangs, 0.0)
            bang_flow = front[None] * 0.9 - up[None] * 0.5 + left[None] * sweep
            if bangs == "curtain":       # parted in the middle and swept to both temples
                bang_flow = front[None] * 0.35 - up[None] * 0.6 + sideways * 1.0
            bang_first = _unit(bang_flow - nrm * np.sum(bang_flow * nrm, 1, keepdims=True))
            first = np.where(is_bang[:, None], bang_first, first)
        stiff_value = 0.5 if spec.get("stiff") else None

        def stiffness(progress):
            if stiff_value is not None:
                return np.zeros(len(roots))                                 # stiff hair stands along its normal
            return np.where(is_bang, 0.16 + 0.35 * progress, 0.12 + 0.50 * progress)

        if spec.get("stiff"):
            first = _unit(nrm + first * 0.25)
        quiff = spec.get("quiff", 0.0) * np.clip(1 - azimuth / QUIFF_AZIMUTH, 0, 1) * (~is_bang)
        if quiff.any():                 # the front lifts up and back off the forehead
            first = _unit(first + nrm * quiff[:, None] - front[None] * quiff[:, None] * 0.6)
        if spec.get("lift"):            # product-styled hair rises off the scalp before it turns with the comb
            first = _unit(first + nrm * spec["lift"] + generator.normal(0, LIFT_SCATTER, first.shape))
        curl_in = spec.get("tip_curl_in", 0.0)

        styled = spec.get("styled", 0.0)

        def target(pos, progress):
            pull = np.broadcast_to(gravity, pos.shape).copy()
            if styled:              # held in place by product: the lock keeps its combed direction and hugs the head
                combed = _unit(pull * (1 - styled) + np.where(is_bang[:, None], pull, first) * styled)
                _, nearest = body.tree.query(pos)
                normal = body.collide_normals[nearest]
                hug = STYLED_HUG * (1 - np.clip(quiff * 2, 0, 1))[:, None]     # a quiff stands proud of the head
                along_head = combed - normal * np.sum(combed * normal, 1, keepdims=True) * (1 - quiff[:, None]) - normal * hug
                pull = np.where(is_bang[:, None], pull, _unit(along_head))
            if curl_in and progress > 0.6:                                  # bob: tips turn toward the neck
                pull = _unit(pull + _unit(body.head_center - pos) * curl_in * (progress - 0.6) / 0.4 * 2)
            return pull

        paths, normals = _grow(body, roots, nrm, first, lengths, margins, target, stiffness, generator,
                               face_guard=~is_bang)
        if "hem" in spec:
            paths = _trim(paths, body, spec["hem"], 0.004, generator, ~is_bang)
        if is_bang.any():
            # fringe cut: lower toward the temples so it frames the face
            cut = BANGS[bangs][1] - 0.02 * np.clip(azimuth / 55, 0, 1) ** 2
            paths = np.where(is_bang[:, None, None],
                             _trim(paths, body, cut[:, None], 0.003, generator, is_bang), paths)
        waved = _wave(paths, normals, spec.get("wave", 0.0), spec.get("curl", 0.0), generator)
        paths = np.where(is_bang[:, None, None], paths, waved)       # a fringe stays combed
        blunt = "hem" in spec
        profile = _profile(SEGMENTS, tip=BLUNT_TIP if blunt else LOCK_TIP)[None]
        widths = width[:, None] * np.where(is_bang[:, None], _profile(SEGMENTS, tip=0.3)[None] * 0.75, profile)
        meshes.append(_tube(paths, widths, normals, material, material))

    # scalp cap: a thin shell under the locks so no skin shows through; cut cleanly along the hairline
    head_faces = body.faces[on_head[body.faces].all(1)]
    cap_vertices, _, cap_faces = cut_by_margin(body.vertices + body.normals * _shell_thickness(body.tpl, shell)[:, None], {},
                                               head_faces, np.where(on_head, weight, -1.0))
    meshes.append(Mesh(cap_vertices, cap_faces, material, material, None,
                       {"tangent": np.broadcast_to(-up, cap_vertices.shape).astype(np.float32),
                        "lock": np.zeros(len(cap_vertices), np.float32)}))
    return meshes


def _tube_shape(mesh):
    """(locks, segments) of a mesh built by `_tube`, or None for any other hair mesh (the scalp cap)."""
    if "lock" not in mesh.vertex_attr:
        return None
    locks = int(mesh.vertex_attr["lock"].max()) + 1
    segments, rest = divmod(len(mesh.vertices), locks * LOCK_SIDES)
    if rest or segments < 2 or len(mesh.faces) != 2 * locks * (segments - 1) * LOCK_SIDES:
        return None
    return locks, segments


def _open_edge_vertices(faces, count):
    """True for vertices on an open edge (a neckline, cuff or hem)."""
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique, uses = np.unique(edges, axis=0, return_counts=True)
    open_vertex = np.zeros(count, bool)
    open_vertex[unique[uses == 1].ravel()] = True
    return open_vertex


def _cloth_lift(rings, tree, points, normals, on_edge):
    """Per ring: how far (m) and along which cloth normal it must move to sit CLOTH_CLEARANCE outside the cloth."""
    distance, nearest = tree.query(rings.mean(1), distance_upper_bound=CLOTH_REACH)
    found = np.isfinite(distance)
    nearest = np.minimum(nearest, len(points) - 1)
    normal = normals[nearest]
    depth = np.einsum("rkj,rj->rk", rings - points[nearest][:, None], normal).min(1)
    return np.where(found & ~on_edge[nearest], np.maximum(CLOTH_CLEARANCE - depth, 0.0), 0.0), normal


def _spread_along_locks(lift):
    """Spread each ring's lift to its neighbours along the lock (lift: locks x segments), never lowering it."""
    for _ in range(CLOTH_LIFT_SPREAD):
        padded = np.pad(lift, ((0, 0), (1, 1)), mode="edge")
        lift = np.maximum(lift, 0.25 * padded[:, :-2] + 0.5 * padded[:, 1:-1] + 0.25 * padded[:, 2:])
    return lift


def lift_over_cloth(hair_meshes, cloth_meshes):
    """Return the hair meshes with locks that sank into the clothes laid back over them.

    Hair is grown against the skin before the clothes exist, so long hair falling over the chest ends up inside a
    shirt: it looks cut off where it enters, and a tip that pokes back out shows as a stray dot. Each lock ring is
    moved out along the nearest cloth normal; the lift spreads along the lock so the lock bends smoothly. Rings
    whose nearest cloth point is on an open edge (a neckline) are left alone: they are past the cloth, not in it.
    A ring deep inside loose cloth may first meet a fold of it at a slant, so the move repeats a few times.
    """
    if not cloth_meshes:
        return list(hair_meshes)
    used = [np.unique(m.faces) for m in cloth_meshes]        # garments share one vertex array; keep their own part
    points = np.vstack([m.vertices[u] for m, u in zip(cloth_meshes, used)])
    normals = np.vstack([m.vertex_normals()[u] for m, u in zip(cloth_meshes, used)])
    on_edge = np.concatenate([_open_edge_vertices(m.faces, len(m.vertices))[u] for m, u in zip(cloth_meshes, used)])
    tree = cKDTree(points)
    lifted = []
    for mesh in hair_meshes:
        shape = _tube_shape(mesh)
        if shape is None:
            lifted.append(mesh)
            continue
        rings = mesh.vertices.reshape(-1, LOCK_SIDES, 3)
        passes = 0
        for passes in range(CLOTH_LIFT_PASSES):
            lift, normal = _cloth_lift(rings, tree, points, normals, on_edge)
            if lift.max() < CLOTH_SETTLED:
                break
            rings = rings + (normal * _spread_along_locks(lift.reshape(shape)).reshape(-1)[:, None])[:, None, :]
        if passes == 0:
            lifted.append(mesh)
            continue
        lifted.append(Mesh(rings.reshape(-1, 3), mesh.faces, mesh.material, mesh.part, mesh.face_uv,
                           dict(mesh.vertex_attr), mesh.smooth))
    return lifted


HAND_PRESS_REACH = 0.08          # lock rings whose centre is farther than this from every resting hand point stay
HAND_PRESS_REST = 0.06           # a hand point this close to the hair owner's skin rests on that person
HAND_PRESS_ABOVE = 0.06          # hair farther out than this past the back of the hand is not caught by it
HAND_PRESS_GAP = 0.003           # a pressed lock passes this far under the hand
HAND_PRESS_FLOOR = 0.002         # a pressed lock keeps this much room between its underside and the skin
HAND_PRESS_MIN_HALF = 0.0015     # a lock flattened under a hand keeps at least this half thickness
HAND_PRESS_FOOTPRINT = 0.012     # a lock passing this close beside a hand point lies on it
HAND_PRESS_SLOPE = 1.2           # dent around the hand: metres of falloff per metre of depth


def _resting_hand(skin_tree, hand_points):
    """Hand points resting on a body: per point the skin under it, the outward skin direction there and the
    height of the hand's underside above that skin (lowest hand point nearby along that direction)."""
    distance, nearest = skin_tree.query(hand_points)
    keep = distance < HAND_PRESS_REST
    points, base = hand_points[keep], skin_tree.data[nearest[keep]]
    out = (points - base) / np.maximum(distance[keep], 1e-9)[:, None]
    underside = np.empty(len(points))
    tree = cKDTree(points)
    for j, members in enumerate(tree.query_ball_point(points, 2 * HAND_PRESS_FOOTPRINT)):
        rel = points[members] - base[j]
        rise = rel @ out[j]
        beside = np.linalg.norm(rel - rise[:, None] * out[j], axis=1)          # off the line from the skin through point j
        underside[j] = rise[beside < HAND_PRESS_FOOTPRINT].min()
    return points, base, out, underside


def press_under_hands(hair_meshes, skin_points, hand_points):
    """Flatten the locks lying under another person's resting hand, in place, so the hand sits on the hair.

    Hair is grown on its owner's body before anyone touches it, so a partner's hand laid on a shoulder ends up
    buried in the locks there and only its fingertips poke out. A real hand traps the hair under it against the
    body: every lock ring lying over the hand (outward from the skin under the hand) sinks toward that skin
    until it passes under the hand, and where the hand lies too close to the skin for the whole lock, the lock
    is squashed thinner as well. The sink spreads along the lock so it bends into the dent instead of kinking."""
    hand_points = np.asarray(hand_points, float).reshape(-1, 3)
    if len(hand_points) == 0 or not hair_meshes:
        return
    skin_tree = cKDTree(skin_points)
    points, base, out, underside = _resting_hand(skin_tree, hand_points)
    if len(points) == 0:
        return
    hand_tree = cKDTree(points)
    for mesh in hair_meshes:
        shape = _tube_shape(mesh)
        if shape is None:
            continue
        rings = mesh.vertices.reshape(-1, LOCK_SIDES, 3)
        centres = rings.mean(1)
        offsets = rings - centres[:, None]
        near = np.flatnonzero(np.isfinite(hand_tree.query(centres, distance_upper_bound=HAND_PRESS_REACH)[0]))
        sink = np.zeros(len(centres))
        squash = np.ones(len(centres))
        direction = np.zeros((len(centres), 3))
        for k, members in zip(near, hand_tree.query_ball_point(centres[near], HAND_PRESS_REACH)):
            members = np.asarray(members)
            up = out[members]
            rel = centres[k] - base[members]
            height = np.einsum("mj,mj->m", rel, up)                    # ring centre over the skin under each hand point
            half = np.abs(np.einsum("sj,mj->ms", offsets[k], up)).max(1)
            lateral = np.linalg.norm(rel - height[:, None] * up, axis=1)  # off the line from the skin through each hand point
            limit = underside[members] - HAND_PRESS_GAP                 # where the ring's top must get to
            drop = height + half - limit
            caught = (drop > 0) & (height - half < underside[members] + HAND_PRESS_ABOVE) & (height > 0)
            if not caught.any():
                continue
            weight = np.clip(1 - (lateral - HAND_PRESS_FOOTPRINT) / (HAND_PRESS_SLOPE * np.maximum(drop, 1e-9)), 0, 1) * caught
            j = int(np.argmax(weight * drop))
            if weight[j] * drop[j] <= 0:
                continue
            allowed = height[j] + half[j] - weight[j] * drop[j]
            thin = float(np.clip((allowed - HAND_PRESS_FLOOR) / 2, HAND_PRESS_MIN_HALF, half[j]))
            centre = max(allowed - half[j], HAND_PRESS_FLOOR + thin)
            sink[k] = max(height[j] - centre, 0.0)
            squash[k] = thin / half[j] if centre + half[j] > allowed else 1.0
            direction[k] = up[j]
        if not sink.any():
            continue
        # one push direction per lock (the skin normals under a hand differ little), spread along it
        locks = direction.reshape(shape + (3,)).sum(1)
        locks /= np.maximum(np.linalg.norm(locks, axis=1, keepdims=True), 1e-9)
        lock_dir = np.repeat(locks, shape[1], axis=0)
        sink = _spread_along_locks(sink.reshape(shape)).reshape(-1)
        squash = 1.0 - _spread_along_locks((1.0 - squash).reshape(shape)).reshape(-1)
        along = np.einsum("rkj,rj->rk", offsets, lock_dir)
        flat = offsets - along[..., None] * lock_dir[:, None, :] * (1.0 - squash)[:, None, None]
        mesh.vertices = (centres[:, None] - (lock_dir * sink[:, None])[:, None, :] + flat).reshape(-1, 3)


def _bun(center, axis, radius, material, generator):
    """A coiled bun: a few tube turns wrapped on a flattened sphere."""
    axis = _unit(axis)
    helper = np.array([0, 0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0, 0])
    u = _unit(np.cross(helper, axis)); v = np.cross(axis, u)
    n_coils, segments = 7, 40
    paths = np.zeros((n_coils, segments, 3)); normals = np.zeros_like(paths)
    t = np.linspace(0, 1, segments)
    for i in range(n_coils):
        lat = (i + 0.5) / n_coils * np.pi * 0.9 - np.pi * 0.42
        angle = 2 * np.pi * (t * 1.15 + generator.random())
        ring = np.cos(lat) * (np.cos(angle)[:, None] * u + np.sin(angle)[:, None] * v)
        lift = (np.sin(lat) + 0.25 * np.sin(angle * 1.0 + i)[:, None] * 0.3) * axis * 0.75
        shell = ring + lift
        paths[i] = center + radius * shell
        normals[i] = _unit(shell)
    widths = np.full((n_coils, segments), radius * 0.42)
    return _tube(paths, widths, normals, material, material)


def hair_painter(material, sheen=0.55, sheen_color=(1.0, 0.95, 0.85), sharpness=26.0, strand_contrast=0.06, fuzz=0.35):
    """Anisotropic highlight across the strands (the bright band on combed hair) + lock-to-lock variation.

    fuzz: speckle on the bare shell (buzz cuts, shaved sides) so it reads as cropped hair, not a cap."""
    from .shade import material_mask

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = material_mask(g, material)
        if not mask.any() or "tangent" not in g["attrs"]:
            return
        # comb direction averaged over neighbouring locks: the highlight then runs as one band across the hair
        # instead of breaking into a spot on every lock
        import cv2
        sigma = SHEEN_SMOOTH_PX * g["supersample"]
        weight = mask.astype(np.float32)
        raw = g["attrs"]["tangent"] * weight[..., None]
        tangent = _unit(cv2.GaussianBlur(raw, (0, 0), sigma) / np.maximum(cv2.GaussianBlur(weight, (0, 0), sigma), 1e-6)[..., None])
        to_light = -g["light_dir"] / np.linalg.norm(g["light_dir"])
        half = _unit(to_light[None, None] - g["view"])
        t_dot_h = np.sum(tangent * half, -1)
        band = np.sqrt(np.clip(1 - t_dot_h ** 2, 0, 1)) ** sharpness
        facing = np.clip(np.sum(g["normal"] * to_light, -1) + 0.2, 0, 1)
        lock = g["attrs"]["lock"][..., 0]
        variation = (np.sin(lock * 12.9898) * 43758.5453) % 1.0
        albedo[mask] *= (1 + strand_contrast * (variation[mask] - 0.5) * 2)[:, None]
        if fuzz:
            cell = np.floor(g["position"] / FUZZ_CELL)
            speck = (np.sin(cell[..., 0] * 12.9898 + cell[..., 1] * 78.233 + cell[..., 2] * 37.719) * 43758.5453) % 1.0
            bare = mask & (lock < 0.5)                                       # the shell carries lock id 0
            albedo[bare] *= (1 + fuzz * (speck[bare] - 0.3))[:, None]
        alpha = band * facing * sheen * mask * (0.8 + 0.2 * variation)
        stronger = alpha > glow_alpha
        # the sheen takes the hair's own colour: dark hair shines in a lighter brown, not in white
        tinted = np.clip(albedo * SHEEN_TINT_GAIN + np.asarray(sheen_color, np.float32) * SHEEN_WHITE, 0, 1)
        glow_rgb[stronger] = tinted[stronger]
        glow_alpha[:] = np.maximum(glow_alpha, alpha)

    return paint
