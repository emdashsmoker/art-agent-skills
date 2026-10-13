"""Image saving and helper outputs for review."""
from pathlib import Path

import cv2
import numpy as np

SHEET_GAP_PX = 12
SHEET_BACKGROUND = 1.0


def save(image, path):
    """Save a 0-1 float RGB image as PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pixels = (np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    if not cv2.imwrite(str(path), pixels[..., ::-1]):
        raise OSError(f"failed to save image: {path}")
    return path


def crop(image, box, scale, zoom=2.0):
    """Crop and enlarge the logical box=(x0, y0, x1, y1). Used to review focal details."""
    x0, y0, x1, y1 = (int(round(value * scale)) for value in box)
    region = image[max(y0, 0):y1, max(x0, 0):x1]
    return cv2.resize(region, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)


def sheet(images, columns=2):
    """Lay several images side by side in one sheet. Used to compare stages or variants at a glance."""
    height = min(image.shape[0] for image in images)
    resized = [
        cv2.resize(image, (int(image.shape[1] * height / image.shape[0]), height), interpolation=cv2.INTER_AREA)
        for image in images
    ]
    width = max(image.shape[1] for image in resized)
    rows = [resized[i:i + columns] for i in range(0, len(resized), columns)]
    sheet_h = len(rows) * height + (len(rows) + 1) * SHEET_GAP_PX
    sheet_w = columns * width + (columns + 1) * SHEET_GAP_PX
    out = np.full((sheet_h, sheet_w, 3), SHEET_BACKGROUND, np.float32)
    for row_index, row in enumerate(rows):
        for column_index, image in enumerate(row):
            top = SHEET_GAP_PX + row_index * (height + SHEET_GAP_PX)
            left = SHEET_GAP_PX + column_index * (width + SHEET_GAP_PX)
            out[top:top + image.shape[0], left:left + image.shape[1]] = image
    return out
