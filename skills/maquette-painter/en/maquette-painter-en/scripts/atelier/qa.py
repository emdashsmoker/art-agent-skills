"""Review helpers: contact sheets and buffer views for the look-and-fix loop."""
import cv2
import numpy as np


def sheet(images, labels=None, columns=3, cell_width=480, pad=8, background=1.0):
    """Tile images (float RGB) into one contact sheet with optional labels."""
    cells = []
    for i, image in enumerate(images):
        h, w = image.shape[:2]
        cell = cv2.resize(image.astype(np.float32), (cell_width, int(h * cell_width / w)), interpolation=cv2.INTER_AREA)
        if labels:                                   # text is drawn on 8-bit pixels: OpenCV 5 requires it
            tagged = (np.clip(cell, 0, 1) * 255).astype(np.uint8)
            cv2.rectangle(tagged, (0, 0), (12 + 11 * len(labels[i]), 26), (255, 255, 255), -1)
            cv2.putText(tagged, labels[i], (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (26, 26, 26), 1, cv2.LINE_AA)
            cell = tagged.astype(np.float32) / 255.0
        cells.append(cell)
    cell_h = max(c.shape[0] for c in cells)
    rows = []
    for start in range(0, len(cells), columns):
        row = []
        for cell in cells[start:start + columns]:
            canvas = np.full((cell_h + 2 * pad, cell_width + 2 * pad, 3), background, np.float32)
            canvas[pad:pad + cell.shape[0], pad:pad + cell_width] = cell
            row.append(canvas)
        while len(row) < columns:
            row.append(np.full_like(row[0], background))
        rows.append(np.hstack(row))
    return np.vstack(rows)


def buffers(canvas, light=None):
    """Sheet of the structure buffers: use it to find which stage a defect comes from."""
    from .core import lightness, Light
    lit = lightness(canvas, light or Light())
    region = (canvas.region.astype(np.float32) * 0.6180339) % 1.0
    region_rgb = cv2.cvtColor(np.dstack([region * 360, np.full_like(region, 0.55), np.full_like(region, 0.95)]),
                              cv2.COLOR_HSV2RGB)
    views = [canvas.albedo, canvas.normal * 0.5 + 0.5, np.dstack([lit] * 3), region_rgb,
             np.dstack([1 - canvas.line_a] * 3), np.dstack([canvas.depth] * 3)]
    return sheet(views, ["albedo", "normal", "light", "region", "line", "depth"], columns=3, cell_width=360)


def check_figure(view):
    """Anatomy facts read back from the relief: digits per hand and foot, and what is hidden.

    Each digit is its own construction part, so a count other than 5 means an occlusion or a
    cropped limb, never a drawing error. Returns {name: (visible, total)}.
    """
    relief = view.relief
    report = {}
    for side in ("l", "r"):
        fingers = [f"{n}_{side}" for n in ("thumb", "index", "middle", "ring", "pinky")]
        toes = [f"toe{i}_{side}" for i in range(1, 6)]
        for label, parts in ((f"hand_{side}", fingers), (f"foot_{side}", toes)):
            defined = [p for p in parts if p in relief.parts]
            visible = [p for p in defined if (relief.part == relief.parts[p]).sum() > 4]
            report[label] = (len(visible), len(defined))
    return report


def check_image(image):
    """Quick health numbers for a render: tonal range, contrast and how much is blown out or crushed."""
    grey = image[..., 0] * 0.299 + image[..., 1] * 0.587 + image[..., 2] * 0.114
    low, high = np.percentile(grey, [2, 98])
    return {
        "value_range": (round(float(low), 3), round(float(high), 3)),
        "contrast": round(float(high - low), 3),
        "mean_value": round(float(grey.mean()), 3),
        "clipped_white": round(float((grey > 0.985).mean()), 4),
        "clipped_black": round(float((grey < 0.015).mean()), 4),
        "saturation": round(float((image.max(2) - image.min(2)).mean()), 3),
    }


def zoom(image, x0, y0, x1, y1, width=900):
    """Crop a region (fractions of the image, 0..1) and enlarge it for close inspection."""
    h, w = image.shape[:2]
    crop = image[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    scale = width / crop.shape[1]
    return cv2.resize(crop, (width, int(crop.shape[0] * scale)), interpolation=cv2.INTER_LANCZOS4)
