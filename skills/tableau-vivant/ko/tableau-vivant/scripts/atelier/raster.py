"""Triangle rasterizer producing geometry buffers.

Why a custom rasterizer: every media layer (cel, watercolor, oil) needs exact
per-pixel geometry (face id, barycentrics, depth). A z-buffer over projected
triangles is the smallest thing that yields those without a GPU or a display.
"""
import numpy as np
from numba import njit

BACKGROUND_FACE = -1
FAR_DEPTH = 1e30


@njit(cache=True)
def _rasterize(screen_xy, depth, faces, height, width, perspective):
    face_buf = np.full((height, width), BACKGROUND_FACE, np.int32)
    depth_buf = np.full((height, width), FAR_DEPTH, np.float32)
    bary_buf = np.zeros((height, width, 2), np.float32)
    for f in range(faces.shape[0]):
        i0, i1, i2 = faces[f, 0], faces[f, 1], faces[f, 2]
        z0, z1, z2 = depth[i0], depth[i1], depth[i2]
        if z0 <= 0.0 or z1 <= 0.0 or z2 <= 0.0:
            continue  # behind the camera
        x0, y0 = screen_xy[i0, 0], screen_xy[i0, 1]
        x1, y1 = screen_xy[i1, 0], screen_xy[i1, 1]
        x2, y2 = screen_xy[i2, 0], screen_xy[i2, 1]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if area == 0.0:
            continue
        xmin = max(int(np.floor(min(x0, x1, x2))), 0)
        xmax = min(int(np.ceil(max(x0, x1, x2))), width - 1)
        ymin = max(int(np.floor(min(y0, y1, y2))), 0)
        ymax = min(int(np.ceil(max(y0, y1, y2))), height - 1)
        inv_area = 1.0 / area
        iz0, iz1, iz2 = 1.0 / z0, 1.0 / z1, 1.0 / z2
        for py in range(ymin, ymax + 1):
            cy = py + 0.5
            for px in range(xmin, xmax + 1):
                cx = px + 0.5
                w0 = ((x1 - cx) * (y2 - cy) - (x2 - cx) * (y1 - cy)) * inv_area
                w1 = ((x2 - cx) * (y0 - cy) - (x0 - cx) * (y2 - cy)) * inv_area
                w2 = 1.0 - w0 - w1
                if w0 < 0.0 or w1 < 0.0 or w2 < 0.0:
                    continue
                if perspective:
                    # perspective-correct weights so attributes do not swim
                    p0, p1, p2 = w0 * iz0, w1 * iz1, w2 * iz2
                    z = 1.0 / (p0 + p1 + p2)
                    b0, b1 = p0 * z, p1 * z
                else:
                    # parallel projection (shadow maps): depth is linear across the triangle
                    z = w0 * z0 + w1 * z1 + w2 * z2
                    b0, b1 = w0, w1
                if z < depth_buf[py, px]:
                    depth_buf[py, px] = z
                    face_buf[py, px] = f
                    bary_buf[py, px, 0] = b0
                    bary_buf[py, px, 1] = b1
    return face_buf, depth_buf, bary_buf


def rasterize(screen_xy, depth, faces, height, width, perspective=True):
    """Return (face_buf, depth_buf, bary_buf) for projected triangles.

    perspective=False is for parallel projections, where depth varies linearly on screen."""
    return _rasterize(
        np.ascontiguousarray(screen_xy, np.float64),
        np.ascontiguousarray(depth, np.float64),
        np.ascontiguousarray(faces, np.int64),
        int(height), int(width), bool(perspective),
    )


def interpolate(face_buf, bary_buf, faces, vertex_attr):
    """Interpolate a per-vertex attribute over covered pixels (zeros elsewhere)."""
    vertex_attr = np.asarray(vertex_attr, np.float32)
    if vertex_attr.ndim == 1:
        vertex_attr = vertex_attr[:, None]
    covered = face_buf >= 0
    tri = faces[face_buf[covered]]
    b0 = bary_buf[covered][:, 0:1]
    b1 = bary_buf[covered][:, 1:2]
    b2 = 1.0 - b0 - b1
    values = vertex_attr[tri[:, 0]] * b0 + vertex_attr[tri[:, 1]] * b1 + vertex_attr[tri[:, 2]] * b2
    out = np.zeros(face_buf.shape + (vertex_attr.shape[1],), np.float32)
    out[covered] = values
    return out
