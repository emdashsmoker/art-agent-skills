"""Texture and warp helpers shared by the media renderers."""
import cv2
import numpy as np

from ..core import fractal_noise, luminance, to_rgb


def paper_height(canvas, tooth=1.2, fibre=16.0, fibre_mix=0.3):
    """Paper relief 0..1: fine tooth plus soft fibres. Valleys hold pigment, peaks catch dry media."""
    s = canvas.scale
    fine = fractal_noise(canvas.H, canvas.W, tooth * s + 0.6, 2, canvas.rng)
    soft = fractal_noise(canvas.H, canvas.W, fibre * s, 3, canvas.rng)
    return (1 - fibre_mix) * fine + fibre_mix * soft


def weave(canvas, period=3.2, depth=1.0):
    """Linen canvas weave relief 0..1."""
    xs, ys = canvas.grid()
    wave = np.sin(xs * 2 * np.pi / period) * np.sin(ys * 2 * np.pi / period)
    jitter = fractal_noise(canvas.H, canvas.W, 5 * canvas.scale, 2, canvas.rng) - 0.5
    return np.clip(0.5 + 0.5 * depth * (0.7 * wave + 0.6 * jitter), 0, 1)


def wobble(image, canvas, pixels=4.0, feature=24.0):
    """Displace an image with smooth noise so edges look hand-made rather than ruled."""
    s = canvas.scale
    dx = (fractal_noise(canvas.H, canvas.W, feature * s, 3, canvas.rng) - 0.5) * 2 * pixels * s
    dy = (fractal_noise(canvas.H, canvas.W, feature * s, 3, canvas.rng) - 0.5) * 2 * pixels * s
    gx, gy = np.meshgrid(np.arange(canvas.W, dtype=np.float32), np.arange(canvas.H, dtype=np.float32))
    return cv2.remap(image, gx + dx.astype(np.float32), gy + dy.astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)


def blur(image, sigma):
    return cv2.GaussianBlur(image, (0, 0), sigma) if sigma > 0.05 else image


def streaks(canvas, angle_deg=0.0, length=30.0, fine=1.0):
    """Directional brush-streak texture 0..1 (noise smeared along one direction)."""
    s = canvas.scale
    noise = canvas.rng.standard_normal((canvas.H, canvas.W)).astype(np.float32)
    size = int(length * s) | 1
    kernel = np.zeros((size, size), np.float32)
    kernel[size // 2, :] = 1.0
    rot = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle_deg, 1.0)
    kernel = cv2.warpAffine(kernel, rot, (size, size))
    kernel /= kernel.sum() + 1e-6
    smeared = cv2.filter2D(blur(noise, fine * s * 0.6), -1, kernel)
    smeared /= smeared.std() + 1e-6
    return np.clip(0.5 + 0.25 * smeared, 0, 1)


def pencil_lines(image, canvas, paper, color="#3b3b44", strength=0.8):
    """Graphite line layer: thin, broken by paper tooth."""
    alpha = canvas.line_a * strength * (0.55 + 0.9 * (1 - paper))
    alpha = np.clip(alpha, 0, 1)[..., None]
    return image * (1 - alpha) + to_rgb(color) * alpha


def quantize(value, levels, soft=0.02):
    """Posterise a 0..1 field into `levels` steps with slightly soft transitions."""
    scaled = np.clip(value, 0, 1) * levels
    base = np.floor(scaled)
    frac = scaled - base
    step = np.clip((frac - 0.5) / max(soft * levels, 1e-4) + 0.5, 0, 1)
    return np.clip((base + step) / levels, 0, 1)


def grey(image):
    return luminance(image)
