"""Facial hair: a shadow of stubble painted on the skin, or a beard shell standing off the jaw.

Regions are defined in template space (default adult, metres, pelvis origin; front is -Y, up is +Z)
so every style fits every face, expression and pose. A beard is a thin shell offset from the skin
and cut along the region's edge; it is painted like hair.
"""
import numpy as np

from .mesh import Mesh, cut_by_margin
from .noise import rng

# cheek line: from the sideburn in front of the ear down to beside the mouth corner
SIDEBURN = (0.072, 0.885)            # (|x|, z)
CHEEK_LOW = (0.030, 0.836)
MUSTACHE_TOP_Z = 0.8395              # just under the nose
SIDEBURN_BACK_Y = -0.050             # the beard stops in front of the ear
JAW_UNDER_Z = (0.772, 0.800)         # lower edge under the chin (front, toward the ear)
LIP_CENTRE_Z, LIP_HALF_HEIGHT, LIP_HALF_WIDTH = 0.8245, 0.0085, 0.028
GOATEE_HALF_WIDTH = 0.033
GOATEE_FRONT_Y, MUSTACHE_FRONT_Y = -0.118, -0.12     # these styles sit on the front of the face only
MUSTACHE_LOW_Z = 0.8300
EDGE_TAPER = 0.008                   # margin over which the shell thins to nothing (m)
EDGE_JITTER = 0.0015                 # ragged edge of a grown beard (m of margin)
HEAD_ZONE_Z = 0.70                   # only skin above this is considered

STYLES = {
    # paint: stubble darkness on the skin. shell: (thickness at the cheek line, thickness at the chin) or None.
    # region: which outline. low: how far the lower edge drops below the jaw line (m)
    "none": None,
    "stubble": dict(paint=0.45, shell=None, region="full", low=0.0),
    "short_beard": dict(paint=0.35, shell=(0.0025, 0.006), region="full", low=0.0),
    "full_beard": dict(paint=0.35, shell=(0.004, 0.024), region="full", low=0.03),
    "goatee": dict(paint=0.30, shell=(0.002, 0.008), region="goatee", low=0.0),
    "mustache": dict(paint=0.25, shell=(0.0035, 0.0035), region="mustache", low=0.0),
}


def margin(x, y, z, region="full", low=0.0):
    """Signed distance-like margin (m): > 0 inside the beard. x is |x| in template space."""
    t = np.clip((x - CHEEK_LOW[0]) / (SIDEBURN[0] - CHEEK_LOW[0]), 0, 1)
    cheek_top = np.where(x < CHEEK_LOW[0], MUSTACHE_TOP_Z, CHEEK_LOW[1] + t * (SIDEBURN[1] - CHEEK_LOW[1]))
    under = JAW_UNDER_Z[0] + (JAW_UNDER_Z[1] - JAW_UNDER_Z[0]) * np.clip(x / SIDEBURN[0], 0, 1) - low
    outside_lips = np.maximum(x - LIP_HALF_WIDTH, np.abs(z - LIP_CENTRE_Z) - LIP_HALF_HEIGHT)
    if region == "full":
        return np.minimum(np.minimum(np.minimum(cheek_top - z, z - under), SIDEBURN_BACK_Y - y), outside_lips)
    if region == "goatee":
        inside = np.minimum(np.minimum(MUSTACHE_TOP_Z - z, z - under), GOATEE_HALF_WIDTH - x)
        return np.where(y < GOATEE_FRONT_Y, np.minimum(inside, outside_lips), -1.0)
    if region == "mustache":
        inside = np.minimum(np.minimum(MUSTACHE_TOP_Z - z, z - MUSTACHE_LOW_Z), LIP_HALF_WIDTH + 0.004 - x)
        return np.where(y < MUSTACHE_FRONT_Y, inside, -1.0)
    raise KeyError(f"unknown beard region '{region}'")


def make_beard(figure, style, material, seed=7):
    """Beard shell meshes for a figure (empty for paint-only styles)."""
    spec = STYLES[style]
    if not spec or not spec["shell"]:
        return []
    from .figure import BODY_RANGE
    tpl = figure.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1]].astype(np.float64)
    faces = figure.faces[(figure.faces < BODY_RANGE[1]).all(1)]
    faces = faces[(tpl[faces][..., 2] > HEAD_ZONE_Z).all(1)]
    vertices = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]]
    normals = Mesh(figure.vertices, faces).vertex_normals()[BODY_RANGE[0]:BODY_RANGE[1]]
    x, y, z = np.abs(tpl[:, 0]), tpl[:, 1], tpl[:, 2]
    jitter = (rng(seed, 307).random(len(tpl)) - 0.5) * 2 * EDGE_JITTER
    inside = margin(x, y, z, spec["region"], spec["low"]) + jitter
    top, bottom = spec["shell"]
    # fuller toward the chin, thin at the cheek line
    thickness = top + (bottom - top) * np.clip((CHEEK_LOW[1] - z) / (CHEEK_LOW[1] - JAW_UNDER_Z[0] + spec["low"]), 0, 1)
    # the beard thins out toward its edge and blends into the stubble under it instead of ending in a step
    thickness = thickness * np.clip(inside / EDGE_TAPER, 0, 1) ** 0.6
    shell, _, shell_faces = cut_by_margin(vertices + normals * thickness[:, None], {}, faces, inside)
    head_down = figure.world[:3, :3] @ (figure.bone_rotation("head") @ np.array([0.0, 0.0, -1.0]))
    return [Mesh(shell, shell_faces, material, material, None,
                 {"tangent": np.broadcast_to(head_down, shell.shape).astype(np.float32),
                  "lock": np.zeros(len(shell), np.float32)})]
