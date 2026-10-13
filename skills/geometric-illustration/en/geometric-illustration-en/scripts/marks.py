"""Small surface marks shared by the figure builders (rig_nude, rig_figure).

Why a module: a fingernail is drawn the same way on a clothed figure and on a figure study,
and both need the same visibility test (is this point on the front-most visible surface?).
"""
import numpy as np

import geom
from palette import line_color
from scene import Drawable

NAIL_MIN_PX = 6.0          # nails shorter than this on screen are left out (a full figure's hands stay clean)
NAIL_FACING = 0.25         # the back of the fingertip must turn this much toward the viewer
NAIL_SURFACE_TOL = 0.05    # head widths: the nail centre must lie this close to the visible surface
NAIL_SHEEN = (1.0, 0.90, 0.88)
NAIL_OPACITY = 0.30
NAIL_LINE_K = 0.4          # nail outline width as a fraction of the line width
NAIL_INK_MIX = 0.55        # outline color mixed toward the skin (softer than a contour)


def visible(points3, res, bf, tol):
    """True where a view-space point lies on the front-most visible surface of a FormResult."""
    y0, x0 = res.box[0], res.box[1]
    hh, ww = res.height.shape
    out = []
    for p in points3:
        px = bf.map([p[:2]])[0]
        i, j = int(round(px[1])) - y0, int(round(px[0])) - x0
        out.append(bool(0 <= i < hh and 0 <= j < ww and res.sdf_px[i, j] < -2
                        and abs(res.height[i, j] - p[2]) <= tol))
    return np.array(out)


def nails(nail_list, tf, bf, res, layer, z, skin, lw):
    """Fingernails as a soft sheen plus a thin outline on the fingertips that face the viewer.

    nail_list: rig_hand HandSpace.nails, (name, world outline Nx3, world back direction).
    tf: world -> view point map; res: the FormResult whose layer `layer` shows the hand.
    """
    skin = np.asarray(skin, float)
    ink = tuple(np.asarray(line_color(skin)) * (1 - NAIL_INK_MIX) + skin * NAIL_INK_MIX)
    origin = tf(np.zeros(3))
    out = []
    for name, outline, back in nail_list:
        if (tf(back) - origin)[2] < NAIL_FACING:
            continue
        view = np.array([tf(p) for p in outline])
        poly = bf.map(view[:, :2])
        if np.ptp(poly, axis=0).max() < NAIL_MIN_PX:
            continue
        if not visible([view.mean(axis=0)], res, bf, NAIL_SURFACE_TOL)[0]:
            continue
        out.append(Drawable(f'nail_{name}', 'body', 0, kind='highlight', fill=[poly], hl_color=NAIL_SHEEN,
                            opacity=NAIL_OPACITY, clip_vis=[layer], feather=0.6))
        out.append(Drawable(f'nail_{name}_ink', 'body', z + 0.001, fill=None, line_color=ink,
                            strokes=[geom.stroke_polygon(np.vstack([poly, poly[:1]]), lw * NAIL_LINE_K)]))
    return out
