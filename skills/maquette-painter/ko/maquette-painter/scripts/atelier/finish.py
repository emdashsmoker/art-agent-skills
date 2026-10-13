"""Finishing passes applied to a rendered image (the retouch / compositing stage)."""
import cv2
import numpy as np

from .core import to_rgb, fractal_noise, smoothstep, saturate


def grade(image, contrast=1.0, saturation=1.0, temperature=0.0, exposure=0.0, gamma=1.0):
    """temperature: + warm, - cool (about -0.3..0.3). contrast pivots on mid grey."""
    out = np.clip(image * (2.0 ** exposure), 0, None)
    out = (out - 0.5) * contrast + 0.5
    out = saturate(np.clip(out, 0, 1), saturation)
    out = out * np.array([1 + temperature * 0.5, 1.0, 1 - temperature * 0.5], np.float32)
    return np.clip(out, 0, 1) ** (1.0 / gamma)


def bloom(image, threshold=0.7, radius=18.0, strength=0.25):
    """Soft glow from bright areas (lens diffusion). radius in pixels."""
    bright = np.clip(image - threshold, 0, 1) / max(1 - threshold, 1e-3)
    glow = cv2.GaussianBlur(bright, (0, 0), radius)
    return 1 - (1 - np.clip(image, 0, 1)) * (1 - strength * glow)


def diffusion(image, radius=10.0, strength=0.3):
    """Pro-mist style softening used in anime compositing: blend a blurred copy in 'lighten' mode."""
    soft = cv2.GaussianBlur(image, (0, 0), radius)
    return image * (1 - strength) + np.maximum(image, soft) * strength


def vignette(image, strength=0.25, softness=0.55, color="#000000"):
    h, w = image.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    amount = (smoothstep(softness, 1.0, r) * strength)[..., None]
    return image * (1 - amount) + to_rgb(color) * amount


def light_wash(image, direction=(-1, -1), color="#fff2d8", strength=0.18):
    """Directional light gradient laid over the frame (sun side warm, far side darker)."""
    h, w = image.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.asarray(direction, np.float32)
    d /= np.linalg.norm(d) + 1e-6
    t = ((xs / w - 0.5) * d[0] + (ys / h - 0.5) * d[1]) + 0.5
    t = np.clip(t, 0, 1)[..., None]
    lit = 1 - (1 - image) * (1 - to_rgb(color) * strength * t)
    return lit * (1 - 0.6 * strength * (1 - t))


def glaze(image, color="#c89a4a", strength=0.15):
    """Transparent unifying glaze (old-master warmth, sepia, moonlight blue)."""
    return image * (1 - strength + strength * to_rgb(color))


def grain(image, amount=0.03, size=1.0, seed=0):
    rng = np.random.default_rng(seed)
    h, w = image.shape[:2]
    noise = rng.standard_normal((h, w)).astype(np.float32)
    if size > 1:
        noise = cv2.GaussianBlur(noise, (0, 0), size * 0.5)
        noise /= noise.std() + 1e-6
    return np.clip(image + noise[..., None] * amount, 0, 1)


def craquelure(image, scale=18.0, strength=0.12, seed=0):
    """Fine drying cracks of an aged oil painting. scale = crack cell size for a 1000 px wide picture."""
    rng = np.random.default_rng(seed)
    h, w = image.shape[:2]
    scale = scale * max(w, h) / 1000.0 * 0.6
    count = max(int(h * w / (scale * scale)), 16)
    subdiv = cv2.Subdiv2D((0, 0, w, h))
    for x, y in zip(rng.uniform(1, w - 2, count), rng.uniform(1, h - 2, count)):
        subdiv.insert((float(x), float(y)))
    polys, _ = subdiv.getVoronoiFacetList([])
    cracks = np.zeros((h, w), np.uint8)
    for poly in polys:
        pts = poly.astype(np.int32)
        for i in range(len(pts)):
            if rng.random() < 0.7:
                cv2.line(cracks, tuple(pts[i]), tuple(pts[(i + 1) % len(pts)]), 255, 1, cv2.LINE_AA)
    cracks = cracks.astype(np.float32) / 255.0
    cracks *= fractal_noise(h, w, scale * 9, 2, rng) > 0.5            # cracks gather in patches, not everywhere
    return image * (1 - strength * cracks)[..., None]


def chromatic(image, pixels=1.0):
    """Slight lens colour fringing toward the frame edges."""
    h, w = image.shape[:2]
    out = image.copy()
    for channel, sign in ((0, 1), (2, -1)):
        zoom = 1 + sign * pixels / max(w, h) * 2
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), 0, zoom)
        out[..., channel] = cv2.warpAffine(image[..., channel], matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)
    return out


def seal(image, x, y, size=46, color="#b3261e", seed=0):
    """Red artist seal (낙관) for ink paintings. x, y, size in pixels."""
    rng = np.random.default_rng(seed)
    stamp = np.zeros(image.shape[:2], np.uint8)
    cv2.rectangle(stamp, (int(x), int(y)), (int(x + size), int(y + size)), 255, -1)
    inner = np.zeros_like(stamp)
    pad = size // 6
    for i in range(3):
        yy = int(y + pad + i * (size - 2 * pad) / 3)
        cv2.line(inner, (int(x + pad), yy + pad // 2), (int(x + size - pad), yy + pad // 2), 255, max(size // 14, 1))
    cv2.line(inner, (int(x + size / 2), int(y + pad)), (int(x + size / 2), int(y + size - pad)), 255, max(size // 14, 1))
    stamp = np.clip(stamp.astype(np.float32) - inner.astype(np.float32), 0, 255) / 255.0
    stamp *= rng.uniform(0.75, 1.0, stamp.shape).astype(np.float32)
    stamp = cv2.GaussianBlur(stamp, (0, 0), 0.6)[..., None] * 0.9
    return image * (1 - stamp) + to_rgb(color) * stamp


def mat(image, margin=40, color="#f4f0e6"):
    """Add a plain border around the picture. margin in pixels."""
    return cv2.copyMakeBorder(image, margin, margin, margin, margin, cv2.BORDER_CONSTANT,
                              value=[float(v) for v in to_rgb(color)])
