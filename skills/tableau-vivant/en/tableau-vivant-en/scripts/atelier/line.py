"""Outline extraction from geometry buffers (silhouette, part borders, depth steps, creases)."""
import numpy as np
import cv2


def _neighbour_diff(buf):
    """True where a pixel differs from its right or lower neighbour."""
    edge = np.zeros(buf.shape[:2], bool)
    edge[:, :-1] |= buf[:, :-1] != buf[:, 1:]
    edge[:-1, :] |= buf[:-1, :] != buf[1:, :]
    return edge


BUSY_SUFFIXES = (".hair", ".foliage", ".blossom", ".leaf", ".grapes")   # masses drawn as one shape, not strand by strand
BUSY_DEPTH_FACTOR = 5.0
GRAZING_FLOOR = 0.06
QUIET_DEPTH_FACTOR = 3.0         # in quiet areas (a cel face) only depth jumps this many times larger are inked
GROUND_PARTS = ("floor", "terrain", "water", "wall")
MIN_CREASE_LENGTH_PX = 3.0       # a lone cleft fragment shorter than this (output px) is dropped as a speck
CLEFT_DEG = 120.0                # neighbouring normals this far apart belong to two surfaces facing each other
SMALL_EYE_PX = 6.0               # an eye opening lower than this (output px) keeps only its upper lash line
SMALL_EYE_MARGIN_PX = 1.0        # how far around a small eye (output px) its lid outline is looked for


def _thin_small_eyes(edges, g):
    """Keep only the upper lid line around eyes too small to hold a full outline.

    A ring of ink around an eye opening a few pixels high fills it, and the eye reads as a black hollow
    (a figure in a cowboy or knee shot). An inker draws a distant eye as one upper lash stroke over the iris,
    so the lower lid and the inside of the opening lose their lines.
    """
    s = g["supersample"]
    margin = max(int(round(SMALL_EYE_MARGIN_PX * s)), 1)
    h, w = edges.shape
    for index, name in enumerate(g["materials"]):
        if not name.endswith(".eye"):
            continue
        eye = g["material"] == index
        if not eye.any():
            continue
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(eye.astype(np.uint8), connectivity=8)
        for i in range(1, count):
            x0, y0, bw, bh = stats[i, :4]
            if bh >= SMALL_EYE_PX * s:
                continue
            top, left = max(y0 - margin, 0), max(x0 - margin, 0)
            bottom, right = min(y0 + bh + margin, h), min(x0 + bw + margin, w)
            mid = int(round(centroids[i][1]))
            window = edges[top:bottom, left:right]
            inside = labels[top:bottom, left:right] == i
            below = np.arange(top, bottom)[:, None] >= mid
            window[inside | below] = False
    return edges


LONE_CREASE_PX = 5.0             # a lone crease fragment off the skin shorter than this (output px) is a speck
# template-space limbs (arms out to the side, legs below the hips; hands and feet excluded): the body mesh folds
# sharply at elbows and knees when they bend, and a crease line there runs right across the limb like a seam
LIMB_ARM_X, LIMB_HAND_X, LIMB_ARM_Z = 0.19, 0.44, 0.20
LIMB_LEG_Z, LIMB_FOOT_Z = 0.0, -0.74


def _limb_skin(g):
    """Skin of upper arms, forearms and legs, where a crease is a fold of the mesh rather than a feature."""
    skin = np.zeros(g["mask"].shape, bool)
    for index, name in enumerate(g["materials"]):
        if name.endswith(".skin"):
            skin |= g["material"] == index
    if not skin.any() or "tpl" not in g["attrs"]:
        return skin & False
    tpl = g["attrs"]["tpl"]
    x, z = np.abs(tpl[..., 0]), tpl[..., 2]
    arm = (x > LIMB_ARM_X) & (x < LIMB_HAND_X) & (z > LIMB_ARM_Z)
    leg = (z < LIMB_LEG_Z) & (z > LIMB_FOOT_Z) & (x < LIMB_ARM_X)
    return skin & (arm | leg)
KEEPS_DETAIL = (".skin", ".eye", ".lash")    # small creases there are features (nostrils, ear folds, lids)


def _drop_lone_creases(edges, crease_only, g):
    """Remove short crease fragments lying alone on clothes and objects.

    A soft fold in cloth turns more than the crease angle over a few pixels only, so a sleeve or a kimono skirt
    picks up stray ticks and dots of ink that belong to no line. On skin the same small fragments are nostrils
    and ear folds, so skin keeps them."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(edges.astype(np.uint8), connectivity=8)
    if count <= 1:
        return edges
    detail = np.zeros(edges.shape, bool)
    for index, name in enumerate(g["materials"]):
        if name.endswith(KEEPS_DETAIL):
            detail |= g["material"] == index
    short = stats[:, cv2.CC_STAT_AREA] < LONE_CREASE_PX * g["supersample"]
    has_other_line = np.bincount(labels[edges & ~crease_only], minlength=count) > 0
    on_detail = np.bincount(labels[edges & detail], minlength=count) > 0
    drop = short & ~has_other_line & ~on_detail
    drop[0] = False
    return edges & ~drop[labels]


def _drop_cleft_specks(edges, crease_only, cleft, supersample):
    """Remove short lone fragments of crease pixels where two surfaces face each other across a cleft.

    Where one surface passes just in front of another that faces it (the inner side of a large breast over the
    sternum), the depth gap is too small for a contour and the crease test fires only at scattered pixels, which
    leaves a dotted trail of ink. Small folds such as nostrils and ear folds bend far less than CLEFT_DEG and stay.
    """
    count, labels, stats, _ = cv2.connectedComponentsWithStats(edges.astype(np.uint8), connectivity=8)
    short = stats[:, cv2.CC_STAT_AREA] < MIN_CREASE_LENGTH_PX * supersample
    has_other_line = np.bincount(labels[edges & ~crease_only], minlength=count) > 0
    has_cleft = np.bincount(labels[edges & cleft], minlength=count) > 0
    drop = short & ~has_other_line & has_cleft
    drop[0] = False                                  # label 0 is the background
    return edges & ~drop[labels]


def edge_map(g, depth_step=0.035, crease_deg=38.0, use_material=True, use_crease=True, busy_detail=0.25, quiet=None):
    """Boolean line map at supersampled resolution.

    depth_step: relative depth jump (fraction of distance) that counts as an occluding contour.
    crease_deg: angle between neighbouring normals that counts as a crease.
    busy_detail: 0..1 how many inner lines hair and foliage keep (0 = silhouette only).
    quiet: optional bool map (supersampled) where only strong contours are inked: no creases, larger depth steps.
    """
    # the far edge of a floor, sea or terrain is a horizon, not an object contour: no ink there
    ground = np.zeros(g["mask"].shape, bool)
    for index, name in enumerate(g["parts"]):
        if name in GROUND_PARTS:
            ground |= g["part"] == index
    open_space = ground | ~g["mask"]
    object_id = np.where(open_space, -1, g["part"])
    edges = _neighbour_diff(object_id)
    if use_material:
        edges |= _neighbour_diff(np.where(open_space, -1, g["material"]))
    busy = np.zeros(g["mask"].shape, bool)
    for index, name in enumerate(g["materials"]):
        if name.endswith(BUSY_SUFFIXES):
            busy |= g["material"] == index
    depth = np.where(g["mask"], g["depth"], 1e6).astype(np.float32)
    gx = np.abs(np.diff(depth, axis=1, append=depth[:, -1:]))
    gy = np.abs(np.diff(depth, axis=0, append=depth[-1:, :]))
    solid = ~open_space
    both_x = solid & np.roll(solid, -1, axis=1)
    both_y = solid & np.roll(solid, -1, axis=0)
    gx, gy = gx * both_x, gy * both_y                 # depth steps count only between two solid objects
    limit = depth_step / g["supersample"] * 0.25
    limit = np.where(busy, limit * (1 + (BUSY_DEPTH_FACTOR - 1) * (1 - busy_detail) / 0.75), limit)
    # a wall seen edge-on changes depth quickly from pixel to pixel without being a contour: allow for the slant
    facing = np.clip(np.abs(np.sum(g["normal"] * g["view"], -1)), GRAZING_FLOOR, 1.0)
    limit = limit / facing
    if quiet is not None:
        limit = np.where(quiet, limit * QUIET_DEPTH_FACTOR, limit)
    edges |= (np.maximum(gx, gy) / np.maximum(depth, 1e-6)) > limit
    if use_crease:
        n = g["normal"]
        cos_x = np.sum(n[:, :-1] * n[:, 1:], axis=-1)
        cos_y = np.sum(n[:-1, :] * n[1:, :], axis=-1)
        limit = np.cos(np.radians(crease_deg))
        crease = np.zeros(edges.shape, bool)
        crease[:, :-1] |= cos_x < limit
        crease[:-1, :] |= cos_y < limit
        crease &= solid & ~busy & ~_limb_skin(g) & (True if quiet is None else ~quiet)
        before = edges.copy()
        cleft = np.zeros(edges.shape, bool)
        cleft[:, :-1] |= cos_x < np.cos(np.radians(CLEFT_DEG))
        cleft[:-1, :] |= cos_y < np.cos(np.radians(CLEFT_DEG))
        edges = _drop_cleft_specks(edges | crease, crease & ~edges, cleft, g["supersample"])
        edges = _drop_lone_creases(edges, crease & ~before, g)
    return _thin_small_eyes(edges, g)


def draw_lines(g, edges, width_px=1.6, weight=None):
    """Line coverage 0..1 at output resolution.

    weight: optional 0..1 map (supersampled) that thins lines where it is low,
    e.g. thinner on the lit side as an inker would.
    """
    s = g["supersample"]
    radius = max(width_px * s / 2.0, 0.5)
    k = int(np.ceil(radius)) * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    thick = cv2.dilate(edges.astype(np.uint8), kernel).astype(np.float32)
    if weight is not None:
        thin = cv2.dilate(edges.astype(np.uint8), np.ones((max(k // 2, 1),) * 2, np.uint8)).astype(np.float32)
        thick = thin + (thick - thin) * np.clip(weight, 0, 1)
    h, w = thick.shape
    return cv2.resize(thick, (w // s, h // s), interpolation=cv2.INTER_AREA)
