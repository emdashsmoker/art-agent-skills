"""Stylised face proportions beyond what the body model's morphs reach.

Why: the body model's morphs stop at realistic proportions. Anime and webtoon faces need
larger eyes, a smaller nose and mouth and a shorter, narrower lower face. These are applied
as smooth offset fields on the rest mesh, so lids, brows and eyeballs move together and the
mesh stays watertight.

Regions are located in template space (the default adult) so they fit every body shape;
the offsets are measured on the figure's own rest mesh, so they scale with its face.
"""
import numpy as np

# Template-space anchors (metres, pelvis origin) found once from the default adult.
NOSE_SEARCH = dict(x=0.012, z=(0.83, 0.88))             # where the nose tip is looked for
MOUTH_CENTRE = np.array([0.0, -0.163, 0.823])           # template position of the lip line centre
NOSE_ROOT_RISE = 0.012                                   # the nose shrinks toward a point this far above its tip's height
NOSE_BASE_DEPTH = 0.024                                  # nose tip to where the nose meets the face
EYE_REGION = np.array([0.026, 0.032, 0.020])             # half-axes (x, y, z) of the zone that scales with each eye
NOSE_REGION = np.array([0.020, 0.035, 0.034])
NOSE_PROUD_FADE = 0.010                                  # depth over which the nose's pull fades into the cheek
MOUTH_REGION = np.array([0.032, 0.025, 0.016])
LOWER_FACE_TOP_OFFSET = 0.012                            # lower face starts this far below the nose tip
NECK_FADE = (0.785, 0.745)                               # template z where lower-face changes fade out into the neck
FACE_FRONT_FADE = (0.0, 0.05)                            # template y where changes fade toward the back of the head
JAW_TAPER_HEIGHT = 0.05                                  # height over which the jaw narrows toward the chin

STYLES = {
    # eyes: (width, depth, height) scale of each eye and its lids. nose: size. mouth: width.
    # lower_face: height below the nose. jaw: width toward the chin
    "none": None,
    "semi": dict(eyes=(1.10, 1.0, 1.12), nose=0.85, mouth=0.92, lower_face=0.94, jaw=0.94),
    "anime": dict(eyes=(1.24, 1.0, 1.30), nose=0.62, mouth=0.82, lower_face=0.86, jaw=0.88),
    "chibi": dict(eyes=(1.38, 1.0, 1.48), nose=0.45, mouth=0.72, lower_face=0.78, jaw=0.82),
}


def _falloff(local, half_axes):
    """1 near the centre, 0 at the ellipsoid surface, smooth in between."""
    r = np.linalg.norm(local / half_axes, axis=1)
    t = np.clip((1.0 - r) / 0.55, 0, 1)
    return t * t * (3 - 2 * t)


def _ramp(value, start, end):
    """0 at `start`, 1 at `end` (either order), smooth."""
    t = np.clip((value - start) / (end - start), 0, 1)
    return t * t * (3 - 2 * t)


def _anchor_indices(tpl):
    """Vertex indices of the nose tip and mouth centre in the template mesh."""
    near_nose = (np.abs(tpl[:, 0]) < NOSE_SEARCH["x"]) & (tpl[:, 2] > NOSE_SEARCH["z"][0]) & (tpl[:, 2] < NOSE_SEARCH["z"][1])
    nose = int(np.flatnonzero(near_nose)[np.argmin(tpl[near_nose, 1])])
    mouth = int(np.argmin(np.linalg.norm(tpl - MOUTH_CENTRE, axis=1)))
    return nose, mouth


def offsets(rest, tpl, eye_groups, style):
    """Per-vertex offsets (rest space) that restyle the face. eye_groups: [(lo, hi), ...] eyeball vertex ranges."""
    params = STYLES[style] if isinstance(style, str) else style
    delta = np.zeros_like(rest)
    if not params:
        return delta
    tpl = tpl.astype(np.float64)
    nose_i, mouth_i = _anchor_indices(tpl)
    front = 1 - _ramp(tpl[:, 1], *FACE_FRONT_FADE)
    neck = _ramp(tpl[:, 2], NECK_FADE[1], NECK_FADE[0])
    # eyes: scale each eye with its lids and brow about the eyeball centre
    eye_scale = np.asarray(params["eyes"]) - 1
    for lo, hi in eye_groups:
        centre_t, centre_r = tpl[lo:hi].mean(0), rest[lo:hi].mean(0)
        w = _falloff(tpl - centre_t, EYE_REGION)
        w[lo:hi] = 1.0
        delta += (rest - centre_r) * eye_scale * w[:, None]
    # nose: shrinks toward the point where it meets the face, keeping its shape
    tip_t, tip_r = tpl[nose_i], rest[nose_i]
    root_offset = np.array([0.0, NOSE_BASE_DEPTH, NOSE_ROOT_RISE])
    # only what stands in front of the cheeks moves, so the cheeks beside the nose keep their shape
    proud = _ramp(tpl[:, 1], tip_t[1] + NOSE_BASE_DEPTH, tip_t[1] + NOSE_BASE_DEPTH - NOSE_PROUD_FADE)
    w = _falloff(tpl - (tip_t + root_offset * 0.5), NOSE_REGION) * front * proud
    delta += (rest - (tip_r + root_offset)) * (params["nose"] - 1) * w[:, None]
    # mouth: narrower
    mouth_t, mouth_r = tpl[mouth_i], rest[mouth_i]
    w = _falloff(tpl - mouth_t, MOUTH_REGION) * front
    delta[:, 0] += (rest[:, 0] - mouth_r[0]) * (params["mouth"] - 1) * w
    # lower face: shorter (everything below the nose rises) and the jaw tapers toward the chin
    top_t, top_r = tip_t[2] - LOWER_FACE_TOP_OFFSET, tip_r[2] - LOWER_FACE_TOP_OFFSET
    below = (tpl[:, 2] < top_t) * front * neck
    delta[:, 2] += np.minimum(rest[:, 2] - top_r, 0) * (params["lower_face"] - 1) * below
    taper = _ramp(tpl[:, 2], top_t, top_t - JAW_TAPER_HEIGHT) * front * neck
    delta[:, 0] += (rest[:, 0] - tip_r[0]) * (params["jaw"] - 1) * taper
    return delta
