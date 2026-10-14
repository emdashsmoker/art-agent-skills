"""Pictures shown on lit screens: invented, generic interfaces drawn from rectangles and circles.

Text is drawn as rounded grey bars, because legible letters at screen scale would read as noise.
Each preset is a function(width, height, rng)
returning a float RGB image; render() draws it at twice the size and shrinks it for clean edges.
"""
import cv2
import numpy as np

from .config import rgb

SUPERSAMPLE = 2


def render(content, width, height, rng):
    """content: a preset name (PRESETS) or a function(width, height, rng) -> float RGB image."""
    painter = PRESETS[content] if isinstance(content, str) else content
    big = painter(width * SUPERSAMPLE, height * SUPERSAMPLE, rng)
    return cv2.resize(big, (width, height), interpolation=cv2.INTER_AREA).astype(np.float32)


# ---- drawing helpers (pixel coordinates of the picture) ------------------------------------------------
def _gradient(width, height, top, bottom):
    t = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    return np.broadcast_to(top * (1 - t) + bottom * t, (height, width, 3)).astype(np.float32).copy()


def _rounded(image, x0, y0, x1, y1, color, radius=0.0):
    """Filled rounded rectangle; coordinates as shares of the picture size."""
    height, width = image.shape[:2]
    left, top, right, bottom = x0 * width, y0 * height, x1 * width, y1 * height
    r = min(radius * min(width, height), (right - left) / 2, (bottom - top) / 2)
    if r < 1:
        cv2.rectangle(image, (int(left), int(top)), (int(right), int(bottom)), tuple(float(c) for c in color), -1)
        return
    arc = np.linspace(0, np.pi / 2, 8)
    corners = [(right - r, bottom - r, 0.0), (left + r, bottom - r, np.pi / 2), (left + r, top + r, np.pi),
               (right - r, top + r, 1.5 * np.pi)]
    points = [(cx + r * np.cos(a0 + a), cy + r * np.sin(a0 + a)) for cx, cy, a0 in corners for a in arc]
    cv2.fillPoly(image, [np.round(np.array(points)).astype(np.int32)], tuple(float(c) for c in color),
                 lineType=cv2.LINE_AA)


def _disc(image, x, y, radius, color):
    height, width = image.shape[:2]
    cv2.circle(image, (int(x * width), int(y * height)), max(1, int(radius * min(width, height))),
               tuple(float(c) for c in color), -1, lineType=cv2.LINE_AA)


def _text_lines(image, x0, y0, x1, count, gap, color, rng, thickness=0.35):
    """Grey bars of uneven length standing in for lines of text."""
    for line in range(count):
        length = rng.uniform(0.45, 1.0) if line % 4 != 3 else rng.uniform(0.2, 0.45)
        y = y0 + line * gap
        _rounded(image, x0, y, x0 + (x1 - x0) * length, y + gap * thickness, color, 0.01)


# ---- presets ------------------------------------------------------------------------------------------
def desktop(width, height, rng):
    image = _gradient(width, height, rgb("#3D5A9E"), rgb("#E89AA8"))
    _disc(image, 0.82, 0.22, 0.20, rgb("#F6C6A0"))
    _rounded(image, 0.07, 0.09, 0.60, 0.74, rgb("#F7F8FB"), 0.02)                 # document window
    _rounded(image, 0.07, 0.09, 0.60, 0.15, rgb("#DDE1EA"), 0.02)
    for k, color in enumerate(("#F06A5E", "#F4BF4F", "#5CC45A")):
        _disc(image, 0.095 + k * 0.025, 0.12, 0.009, rgb(color))
    _rounded(image, 0.11, 0.20, 0.33, 0.40, rgb("#9CC3E6"), 0.01)
    _text_lines(image, 0.36, 0.21, 0.56, 4, 0.045, rgb("#B9BECB"), rng)
    _text_lines(image, 0.11, 0.45, 0.56, 6, 0.045, rgb("#B9BECB"), rng)
    _rounded(image, 0.44, 0.32, 0.93, 0.86, rgb("#FFFFFF"), 0.02)                 # chart window
    _rounded(image, 0.44, 0.32, 0.93, 0.38, rgb("#DDE1EA"), 0.02)
    for k in range(7):
        top = 0.80 - rng.uniform(0.12, 0.36)
        _rounded(image, 0.49 + k * 0.06, top, 0.53 + k * 0.06, 0.80, rgb("#5B8BD6" if k != 4 else "#F2A65A"), 0.005)
    _rounded(image, 0.30, 0.90, 0.70, 0.97, rgb("#FFFFFF") * 0.85 + rgb("#3D5A9E") * 0.15, 0.03)   # dock
    for k, color in enumerate(("#5B8BD6", "#5CC45A", "#F2A65A", "#E8697A", "#9A7BD8", "#4FC3C9")):
        _rounded(image, 0.325 + k * 0.062, 0.913, 0.37 + k * 0.062, 0.957, rgb(color), 0.01)
    return image


CODE_COLORS = ("#C792EA", "#82AAFF", "#C3E88D", "#F78C6C", "#89DDFF", "#A6ACCD", "#FFCB6B")


def code(width, height, rng):
    image = _gradient(width, height, rgb("#232838"), rgb("#1D2130"))
    _rounded(image, 0.0, 0.0, 1.0, 0.06, rgb("#181C28"))
    _rounded(image, 0.02, 0.012, 0.20, 0.06, rgb("#2C3246"), 0.01)
    _rounded(image, 0.0, 0.06, 0.07, 1.0, rgb("#1A1E2B"))
    lines, indent = 26, 0
    gap = 0.92 / lines
    for line in range(lines):
        y = 0.08 + line * gap
        _rounded(image, 0.02, y + gap * 0.25, 0.045, y + gap * 0.62, rgb("#4A5068"), 0.005)    # line number
        if rng.random() < 0.12:
            continue                                                                         # blank line
        indent = int(np.clip(indent + rng.choice((-1, 0, 0, 1)), 0, 4))
        x = 0.10 + indent * 0.05
        for _ in range(rng.integers(1, 5)):
            length = rng.uniform(0.04, 0.16)
            if x + length > 0.97:
                break
            color = rgb(CODE_COLORS[rng.integers(len(CODE_COLORS))])
            _rounded(image, x, y + gap * 0.25, x + length, y + gap * 0.65, color, 0.005)
            x += length + 0.015
    return image


def video(width, height, rng):
    image = _gradient(width, height, rgb("#3B4F8C"), rgb("#F4A77A"))
    _disc(image, 0.68, 0.48, 0.10, rgb("#FFE6B0"))
    xs = np.arange(width)
    for layer, (color, base, amplitude) in enumerate(((rgb("#6A5C8E"), 0.58, 0.10), (rgb("#4A3F6E"), 0.68, 0.08),
                                                      (rgb("#2C2546"), 0.80, 0.06))):
        phase = rng.uniform(0, 6.28)
        ridge = (base + amplitude * np.sin(xs / width * (5 + 3 * layer) + phase)
                 + amplitude * 0.4 * np.sin(xs / width * 17 + phase * 2)) * height
        mask = np.arange(height)[:, None] > ridge[None, :]
        image[mask] = color
    _rounded(image, 0.04, 0.93, 0.96, 0.945, rgb("#FFFFFF") * 0.5, 0.01)            # progress bar
    _rounded(image, 0.04, 0.93, 0.38, 0.945, rgb("#F05A5A"), 0.01)
    _disc(image, 0.38, 0.9375, 0.018, rgb("#FFFFFF"))
    return image


def chat(width, height, rng):
    image = _gradient(width, height, rgb("#EEF1F6"), rgb("#E4E8F0"))
    _rounded(image, 0.0, 0.0, 1.0, 0.10, rgb("#5B8BD6"))
    _disc(image, 0.12, 0.065, 0.045, rgb("#F6C6A0"))
    _rounded(image, 0.22, 0.05, 0.55, 0.08, rgb("#FFFFFF") * 0.9 + rgb("#5B8BD6") * 0.1, 0.01)
    y = 0.14
    mine = False
    while y < 0.82:
        lines = int(rng.integers(1, 3))
        tall = 0.035 + lines * 0.03
        wide = rng.uniform(0.35, 0.68)
        if mine:
            _rounded(image, 0.94 - wide, y, 0.94, y + tall, rgb("#9EE09A"), 0.04)
        else:
            _rounded(image, 0.06, y, 0.06 + wide, y + tall, rgb("#FFFFFF"), 0.04)
        y += tall + 0.03
        mine = not mine if rng.random() < 0.75 else mine
    _rounded(image, 0.0, 0.88, 1.0, 1.0, rgb("#FFFFFF"))
    _rounded(image, 0.05, 0.905, 0.80, 0.955, rgb("#E9ECF2"), 0.04)
    _disc(image, 0.89, 0.93, 0.04, rgb("#5B8BD6"))
    return image


def home(width, height, rng):
    image = _gradient(width, height, rgb("#F4B48A"), rgb("#7A6BC8"))
    _rounded(image, 0.08, 0.07, 0.92, 0.24, rgb("#FFFFFF") * 0.35 + rgb("#F4B48A") * 0.65, 0.05)   # clock widget
    _rounded(image, 0.14, 0.10, 0.55, 0.17, rgb("#FFFFFF"), 0.02)
    _rounded(image, 0.14, 0.185, 0.40, 0.205, rgb("#FFFFFF") * 0.8, 0.01)
    colors = ("#5B8BD6", "#5CC45A", "#F2A65A", "#E8697A", "#9A7BD8", "#4FC3C9", "#F4D35E", "#7FB069")
    for row in range(4):
        for col in range(4):
            x, y = 0.08 + col * 0.225, 0.30 + row * 0.13
            color = rgb(colors[int(rng.integers(len(colors)))])
            _rounded(image, x, y, x + 0.16, y + 0.085, color, 0.04)
    _rounded(image, 0.05, 0.86, 0.95, 0.97, rgb("#FFFFFF") * 0.35 + rgb("#7A6BC8") * 0.65, 0.06)
    for col in range(4):
        _rounded(image, 0.10 + col * 0.215, 0.875, 0.26 + col * 0.215, 0.955, rgb(colors[col]), 0.04)
    return image


def game(width, height, rng):
    image = _gradient(width, height, rgb("#5EC4F2"), rgb("#BFEAFA"))
    for _ in range(4):
        x, y = rng.uniform(0.1, 0.9), rng.uniform(0.08, 0.35)
        for dx, size in ((-0.05, 0.05), (0.0, 0.07), (0.05, 0.05)):
            _disc(image, x + dx, y, size, rgb("#FFFFFF"))
    xs = np.arange(width)
    hill = (0.62 + 0.06 * np.sin(xs / width * 7 + rng.uniform(0, 6))) * height
    image[np.arange(height)[:, None] > hill[None, :]] = rgb("#7CC85A")
    _rounded(image, 0.0, 0.82, 1.0, 1.0, rgb("#B07A48"))
    _rounded(image, 0.0, 0.80, 1.0, 0.84, rgb("#5CA840"))
    for x, y in ((0.18, 0.55), (0.55, 0.45), (0.78, 0.60)):
        _rounded(image, x, y, x + 0.16, y + 0.05, rgb("#C8884A"), 0.01)
        for k in range(3):
            _disc(image, x + 0.03 + k * 0.05, y - 0.05, 0.018, rgb("#FFD23A"))
    _disc(image, 0.30, 0.755, 0.05, rgb("#F05A5A"))                                    # the player
    _disc(image, 0.315, 0.74, 0.012, rgb("#FFFFFF"))
    for k in range(3):
        _disc(image, 0.05 + k * 0.05, 0.06, 0.018, rgb("#F05A5A"))                     # lives
    _rounded(image, 0.70, 0.04, 0.95, 0.08, rgb("#FFFFFF") * 0.8, 0.02)
    return image


PRESETS = {"desktop": desktop, "code": code, "video": video, "chat": chat, "home": home, "game": game}
