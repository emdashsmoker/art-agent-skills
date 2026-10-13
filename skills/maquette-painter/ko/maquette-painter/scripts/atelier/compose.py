"""Composition helpers: canvas formats, figure framing, guides and quick thumbnails."""
import numpy as np

FORMATS = {   # purpose -> (width, height) in design units
    "portrait": (1024, 1280), "tall": (900, 1600), "square": (1100, 1100), "landscape": (1400, 900),
    "wide": (1600, 900), "poster": (1000, 1414), "banner": (1800, 700), "icon": (800, 800),
    "book_cover": (1000, 1500), "phone_wallpaper": (900, 1950), "desktop_wallpaper": (1600, 900),
}
FRAMINGS = {   # figure crop -> (head top as a fraction of canvas height, head size as a fraction of canvas height)
    "face": (0.10, 0.62), "bust": (0.12, 0.37), "half": (0.09, 0.255), "three_quarter": (0.07, 0.172),
    "full": (0.06, None),
}


def framing(canvas, kind="bust", heads=7.5, x=None, margin_bottom=0.05):
    """Keyword arguments for Character.draw that place a figure for a standard crop.

    kind: face | bust | half (waist up) | three_quarter (knees up) | full
    """
    top, head = FRAMINGS[kind]
    x = canvas.width / 2 if x is None else x
    if head is None:
        ground = canvas.height * (1 - margin_bottom)
        return dict(x=x, ground_y=ground, height=ground - canvas.height * top)
    return dict(x=x, head_top_y=canvas.height * top, unit=canvas.height * head)


def thirds(canvas):
    """The four rule-of-thirds power points, in design units."""
    w, h = canvas.width, canvas.height
    return [(w / 3, h / 3), (2 * w / 3, h / 3), (w / 3, 2 * h / 3), (2 * w / 3, 2 * h / 3)]


def golden(canvas):
    """Golden-section lines: (vertical xs, horizontal ys)."""
    phi = 0.618
    w, h = canvas.width, canvas.height
    return [w * (1 - phi), w * phi], [h * (1 - phi), h * phi]


def value_check(image, levels=3):
    """Posterised greyscale of a render: a readable picture works in three values."""
    grey = image[..., 0] * 0.299 + image[..., 1] * 0.587 + image[..., 2] * 0.114
    step = np.floor(np.clip(grey, 0, 0.999) * levels) / (levels - 1)
    return np.dstack([step] * 3).astype(np.float32)


def guides(image, kind="thirds", color=(1.0, 0.2, 0.2)):
    """Overlay composition guides on a render for review (never on the final picture)."""
    import cv2
    out = (np.clip(image, 0, 1) * 255).astype(np.uint8)
    h, w = out.shape[:2]
    stroke = tuple(int(c * 255) for c in color)
    fractions = (1 / 3, 2 / 3) if kind == "thirds" else (0.382, 0.618)
    for f in fractions:
        cv2.line(out, (int(w * f), 0), (int(w * f), h), stroke, 1, cv2.LINE_AA)
        cv2.line(out, (0, int(h * f)), (w, int(h * f)), stroke, 1, cv2.LINE_AA)
    return out.astype(np.float32) / 255.0
