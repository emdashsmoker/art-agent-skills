"""Print and pattern media: woodblock (ukiyo-e), halftone pop, pointillism, faceted cubism."""
import cv2
import numpy as np

from ..core import (reference, lightness, composite_lines, composite_over, luminance, to_rgb,
                    smoothstep, saturate)
from .common import paper_height, blur, streaks


def woodblock(canvas, light, paper="#efe3c8", bands=1, bokashi=0.5, misregister=1.2, mottle=0.25,
              line="#1e1a1c", line_strength=1.0, mute=0.95):
    """Ukiyo-e style: flat colour blocks, graded 'bokashi' at the top of large areas, key-block lines."""
    s = canvas.scale
    paper_rgb = to_rgb(paper)
    tooth = paper_height(canvas, tooth=1.2, fibre=30.0, fibre_mix=0.55)
    base = saturate(canvas.albedo, mute)
    if light.haze_strength:
        fog = (np.clip(canvas.depth, 0, 1) ** 1.5 * light.haze_strength)[..., None]
        base = base * (1 - fog) + light.haze * fog
    if bands > 1:
        lit = blur(lightness(canvas, light), 3 * s)
        tone = smoothstep(0.40, 0.44, lit)[..., None]
        base = base * (0.72 + 0.28 * tone)
    xs, ys = canvas.grid()
    fade = np.clip(1 - ys / (canvas.height * 0.45), 0, 1) ** 1.6 * bokashi
    far = smoothstep(0.7, 0.9, canvas.depth)
    base = base * (1 - (fade * far * 0.3)[..., None] * np.array([1.0, 0.85, 0.6], np.float32))            # darker graded sky toward the top
    shift = np.float32([[1, 0, misregister * s], [0, 1, misregister * 0.6 * s]])
    base = cv2.warpAffine(base, shift, (canvas.W, canvas.H), borderMode=cv2.BORDER_REPLICATE)
    grain = streaks(canvas, 0.0, 120.0, 1.0)
    press = 1 - mottle * (0.25 * (grain - 0.5) + 0.5 * np.clip(tooth - 0.55, 0, 1))
    image = paper_rgb * (1 - (1 - base) * press[..., None])     # ink printed on paper (multiply)
    key = np.clip(blur(canvas.line_a, 0.5 * s) * 1.5, 0, 1) * (0.8 + 0.4 * (1 - tooth)) * line_strength
    key = np.clip(key, 0, 1)[..., None]
    image = image * (1 - key) + to_rgb(line) * key
    return np.clip(composite_over(image, canvas), 0, 1)


def halftone(canvas, light, dot=7.0, paper="#fbf6ea", line="#111111", line_strength=1.0, vivid=1.5, mono=False):
    """Pop-art print: bold flats, Ben-Day dots for shadow, heavy black line. mono=True gives manga screentone."""
    s = canvas.scale
    xs, ys = canvas.grid()
    lit = blur(lightness(canvas, light), 2 * s)
    base = saturate(canvas.albedo, vivid)
    if mono:                                   # screentone: paper white, with tone dots only where the local colour is dark
        tone = luminance(canvas.albedo)
        base = np.ones_like(base)
        lit = lit * smoothstep(0.05, 0.6, tone) * (1 - canvas.unlit) + canvas.unlit * smoothstep(0.2, 0.75, tone)
    a = np.radians(45)
    u = (xs * np.cos(a) + ys * np.sin(a)) / dot
    v = (-xs * np.sin(a) + ys * np.cos(a)) / dot
    cell = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2)
    radius = np.clip(0.75 * (1 - lit), 0, 0.72)
    dots = smoothstep(radius + 0.06, radius - 0.06, cell) * (1 - canvas.unlit)
    if mono:
        dots = smoothstep(radius + 0.06, radius - 0.06, cell)
        shade = np.zeros_like(base) + 0.08
    else:
        shade = saturate(base * 0.55, 1.2)
    image = base * (1 - dots[..., None]) + shade * dots[..., None]
    image = image * to_rgb(paper)
    key = np.clip(cv2.dilate(canvas.line_a, np.ones((3, 3), np.uint8)) * line_strength, 0, 1)[..., None]
    image = image * (1 - key) + to_rgb(line) * key
    return np.clip(composite_over(image, canvas), 0, 1)


def pointillism(canvas, light, dot=5.0, ground="#e8dcc0", divide=0.5, passes=3, vivid=1.25):
    """Divisionist dots: each area is built from separate touches of its component hues."""
    s = canvas.scale
    rng = canvas.rng
    target = composite_lines(reference(canvas, light), canvas, "trace", 0.5 * canvas.focus)
    target = saturate(composite_over(target, canvas), vivid)
    image = np.empty((canvas.H, canvas.W, 3), np.uint8)
    image[:] = (to_rgb(ground) * 255).astype(np.uint8)
    for p in range(passes):
        radius = max(dot * s * (1.25 - 0.25 * p) * 0.5, 1.0)
        step = radius * 1.7
        gy, gx = np.mgrid[0:canvas.H:step, 0:canvas.W:step]
        px = (gx + rng.uniform(-step, step, gx.shape) * 0.55).ravel()
        py = (gy + rng.uniform(-step, step, gy.shape) * 0.55).ravel()
        ix = np.clip(px, 0, canvas.W - 1).astype(int)
        iy = np.clip(py, 0, canvas.H - 1).astype(int)
        colors = target[iy, ix]
        hue = rng.choice([-1, 0, 0, 1], len(colors)) * 38.0 * divide          # split into neighbour hues
        colors = _shift_each(colors, hue)
        colors = np.clip(colors * (1 + rng.normal(0, 0.06, (len(colors), 1))), 0, 1)
        order = rng.permutation(len(px))
        r = int(round(radius))
        for i in order:
            cv2.circle(image, (int(px[i]), int(py[i])), r, tuple(float(c) * 255 for c in colors[i]), -1, cv2.LINE_AA)
    return image.astype(np.float32) / 255.0


def _shift_each(colors, degrees):
    hsv = cv2.cvtColor(colors.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_RGB2HSV)
    hsv[:, 0, 0] = (hsv[:, 0, 0] + degrees) % 360
    hsv[:, 0, 1] = np.clip(hsv[:, 0, 1] * 1.1, 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).reshape(-1, 3)


def facets(canvas, light, cell=70.0, mute=0.75, tilt=0.35, line="#2a241e", line_strength=0.8,
           palette_shift="#b89b6a"):
    """Analytic-cubism feel: the picture broken into shifting planes with a muted palette."""
    s = canvas.scale
    rng = canvas.rng
    target = composite_over(reference(canvas, light), canvas)
    count = max(int(canvas.width * canvas.height / (cell * cell)), 8)
    sites = np.stack([rng.uniform(0, canvas.W, count), rng.uniform(0, canvas.H, count)], axis=1).astype(np.float32)
    subdiv = cv2.Subdiv2D((0, 0, canvas.W, canvas.H))
    for x, y in sites:
        subdiv.insert((float(np.clip(x, 1, canvas.W - 2)), float(np.clip(y, 1, canvas.H - 2))))
    polys, centres = subdiv.getVoronoiFacetList([])
    label = np.zeros((canvas.H, canvas.W), np.int32)
    for i, poly in enumerate(polys):
        cv2.fillConvexPoly(label, poly.astype(np.int32), i + 1)
    xs, ys = np.meshgrid(np.arange(canvas.W, dtype=np.float32), np.arange(canvas.H, dtype=np.float32))
    earth = to_rgb(palette_shift)
    region_count = int(canvas.region.max()) + 1
    label = label * region_count + canvas.region          # a plane never crosses a subject boundary
    flat = label.ravel()
    ids, inverse = np.unique(flat, return_inverse=True)
    counts = np.bincount(inverse).astype(np.float32)
    means = np.stack([np.bincount(inverse, target[..., ch].ravel()) / counts for ch in range(3)], axis=1)
    means = saturate(means, mute) * 0.8 + earth * luminance(means)[:, None] * 0.2
    cx = np.bincount(inverse, xs.ravel()) / counts
    cy = np.bincount(inverse, ys.ravel()) / counts
    angle = rng.uniform(0, 2 * np.pi, len(ids))
    ramp = ((xs.ravel() - cx[inverse]) * np.cos(angle[inverse]) + (ys.ravel() - cy[inverse]) * np.sin(angle[inverse])) / (cell * s)
    image = np.clip(means[inverse] * (1 + tilt * ramp[:, None]), 0, 1).reshape(canvas.H, canvas.W, 3).astype(np.float32)
    edge = (cv2.Laplacian(label.astype(np.float32), cv2.CV_32F) != 0).astype(np.float32)
    edge = np.clip(blur(edge, 0.8 * s) * 1.4, 0, 1) * line_strength * 0.6
    key = np.clip(edge + canvas.line_a * line_strength, 0, 1)[..., None]
    image = image * (1 - key) + to_rgb(line) * key
    tooth = paper_height(canvas)
    return np.clip(image * (1 - 0.06 * (0.5 - tooth) * 2)[..., None], 0, 1)
