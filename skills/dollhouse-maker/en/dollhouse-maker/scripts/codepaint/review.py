"""Helpers for checking a render: previews, zoomed crops, side-by-side sheets, basic stats."""
import cv2
import numpy as np

from .color import luminance
from .scene import save


def preview(img, path, max_side=1200):
    """Save a downscaled copy that is quick to open and inspect."""
    h, w = img.shape[:2]
    k = min(1.0, max_side / max(h, w))
    small = cv2.resize(img, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA) if k < 1 else img
    return save(small, path)


def zoom(img, path, box, scale=2.0):
    """Save an enlarged crop. box = (x0, y0, x1, y1) in pixels. Use it on faces, hands, joints."""
    x0, y0, x1, y1 = [int(v) for v in box]
    crop = img[y0:y1, x0:x1]
    size = (int(crop.shape[1] * scale), int(crop.shape[0] * scale))
    return save(cv2.resize(crop, size, interpolation=cv2.INTER_CUBIC), path)


def sheet(images, path, columns=None, height=640):
    """Save several renders side by side (style comparisons, before/after)."""
    columns = columns or len(images)
    cells = [cv2.resize(im, (int(im.shape[1] * height / im.shape[0]), height), interpolation=cv2.INTER_AREA)
             for im in images]
    width = max(c.shape[1] for c in cells)
    cells = [np.pad(c, ((0, 0), (0, width - c.shape[1]), (0, 0)), constant_values=1.0) for c in cells]
    while len(cells) % columns:
        cells.append(np.ones_like(cells[0]))
    rows = [np.hstack(cells[i:i + columns]) for i in range(0, len(cells), columns)]
    return save(np.vstack(rows), path)


def stats(img):
    """Numbers that catch gross failures without looking: blank, blown-out or muddy pictures."""
    lum = luminance(img)
    sat = img.max(2) - img.min(2)
    return dict(mean=float(lum.mean()), contrast=float(np.percentile(lum, 98) - np.percentile(lum, 2)),
                clipped_white=float((lum > 0.985).mean()), clipped_black=float((lum < 0.015).mean()),
                saturation=float(sat.mean()), detail=float(np.abs(cv2.Laplacian(lum, cv2.CV_32F)).mean()))
