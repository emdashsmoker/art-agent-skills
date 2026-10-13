"""Headwear: a knitted beanie pulled over whatever hair the figure has.

The beanie is the head's own surface lifted off the skin, cut along a line that runs from mid-forehead over
the tops of the ears to below the back of the skull. Where there is hair it sits just outside the hair, so
the hair above the line disappears inside and long hair still falls out from under the edge.
"""
import numpy as np
from scipy.spatial import cKDTree

from .mesh import Mesh, cut_by_margin
from .hair import Body, HEAD_CENTER, HEAD_MIN_Z

BEANIE_FRONT = (-0.15, 0.925)    # (template y, z) of the edge on the forehead
BEANIE_SLOPE = 0.30              # the edge drops this much per metre toward the back of the head
BEANIE_KNIT = 0.010              # wool thickness over bare skin or a shaved head
HAIR_CLEARANCE = 0.006           # the wool sits this far outside the outermost hair
HAIR_REACH = 0.06                # hair points this close to a head vertex count when lifting the beanie over them
CUFF = 0.045                     # height of the turned-up band at the edge
CUFF_THICKNESS = 0.005
SMOOTH_PASSES = 6
RIBS = 64                        # knit ribs round the head
STYLES = ("beanie",)


def _edge_margin(tpl):
    """Metres above the beanie's edge line (> 0 is covered)."""
    edge = BEANIE_FRONT[1] - BEANIE_SLOPE * (tpl[:, 1] - BEANIE_FRONT[0])
    return tpl[:, 2] - edge


def make_headwear(figure, style, material, hair_meshes=()):
    """Return the meshes of a hat. style: 'beanie'."""
    if style not in STYLES:
        raise KeyError(f"unknown hat '{style}'. Available: {list(STYLES)}")
    from .garment import _smooth_scalar
    body = Body(figure)
    on_head = body.tpl[:, 2] > HEAD_MIN_Z
    margin = np.where(on_head, _edge_margin(body.tpl), -1.0)
    lift = np.full(len(body.vertices), BEANIE_KNIT)
    hair = [m.vertices for m in hair_meshes if len(m.vertices)]
    if hair:
        points = np.vstack(hair)
        tree = cKDTree(points)
        covered = np.flatnonzero(margin > -CUFF)
        for k, members in zip(covered, tree.query_ball_point(body.vertices[covered], HAIR_REACH)):
            if members:
                reach = (points[members] - body.vertices[k]) @ body.normals[k]
                lift[k] = max(lift[k], reach.max() + HAIR_CLEARANCE)
    head_faces = body.faces[on_head[body.faces].all(1)]
    lift = np.maximum(lift, _smooth_scalar(lift, head_faces, SMOOTH_PASSES))     # smooth, but never down into the hair
    lift += CUFF_THICKNESS * np.clip(1 - margin / CUFF, 0, 1) * (margin > 0)       # the folded band is double
    d = body.tpl - HEAD_CENTER
    azimuth = np.degrees(np.arctan2(d[:, 0], -d[:, 1]))
    attrs = {"knit": np.column_stack([azimuth, margin])}
    vertices, attrs, faces = cut_by_margin(body.vertices + body.normals * lift[:, None], attrs, head_faces, margin)
    mesh = Mesh(vertices, faces, material, material, None, {"knit": np.asarray(attrs["knit"], np.float32)})
    return [mesh]          # no subdivision: the cut head surface has non-manifold edges that it would blow up


def knit_painter(material):
    """Vertical knit ribs, and a fold line where the cuff turns up."""
    from .shade import material_mask

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = material_mask(g, material)
        if not mask.any() or "knit" not in g["attrs"]:
            return
        azimuth, margin = g["attrs"]["knit"][..., 0], g["attrs"]["knit"][..., 1]
        rib = 0.5 + 0.5 * np.cos(np.radians(azimuth) * RIBS)
        shade = 0.84 + 0.16 * rib
        fold = np.abs(margin - CUFF) < 0.004
        shade = np.where(fold, 0.62, shade)
        albedo[mask] = albedo[mask] * shade[mask][:, None]

    return paint
