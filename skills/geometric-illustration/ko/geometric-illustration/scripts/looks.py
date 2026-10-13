"""Color grades applied after the style renderer (spec look).

Why: a mood such as the cold post-Soviet night ('doomer') is a property of the whole
picture, so it is graded once over the finished image: the colors drain toward grey and
the shadows toward blue, only the warm lights (sodium lamps, lit windows, a bulb) keep
their orange, the blacks lift like old film, and grain plus a vignette close the frame.
"""
import cv2
import numpy as np

LOOKS = ('none', 'doomer')

DOOMER = dict(
    saturation=0.46,              # color left in ordinary surfaces (skin stays faintly warm)
    warm_saturation=0.95,         # color left in warm, bright lights
    warm_hue=(0.20, 0.30),        # red minus blue that starts / completes a 'warm light'
    warm_value=(0.40, 0.65),      # brightness that starts / completes a 'warm light'
    shadow_tint=(0.86, 0.92, 1.06),   # multiplier that cools the dark half of the tones
    lift=(0.055, 0.062, 0.080),   # faded film: black lifts to a cold grey
    contrast=0.92,
    vignette=0.32,                # darkening at the corners
    grain=0.026,                  # film grain strength (luminance noise)
    grain_blur=0.7,               # px: grain clumps a little, like film
)
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def apply_look(img, spec):
    look = spec.get('look', 'none')
    if look not in LOOKS:
        raise ValueError(f"unknown look '{look}' (use {', '.join(LOOKS)})")
    if look == 'none':
        return img
    return doomer(img, np.random.default_rng(spec['canvas']['seed'] + 101))


def _ramp(x, lo_hi):
    lo, hi = lo_hi
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def doomer(img, rng, k=DOOMER):
    img = np.clip(img.astype(np.float32), 0.0, 1.0)
    y = img @ LUMA
    warm = _ramp(img[..., 0] - img[..., 2], k['warm_hue']) * _ramp(y, k['warm_value'])
    sat = k['saturation'] + (k['warm_saturation'] - k['saturation']) * warm
    out = y[..., None] + (img - y[..., None]) * sat[..., None]
    dark = (1.0 - y)[..., None] ** 2 * (1.0 - warm[..., None])
    out = out * (1.0 + (np.asarray(k['shadow_tint'], np.float32) - 1.0) * dark)
    out = 0.5 + (out - 0.5) * k['contrast']
    lift = np.asarray(k['lift'], np.float32)
    out = lift + out * (1.0 - lift)
    h, w = y.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / np.sqrt(2)
    out = out * (1.0 - k['vignette'] * r[..., None] ** 2)
    noise = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), k['grain_blur'])
    noise /= max(float(noise.std()), 1e-6)
    out = out + (k['grain'] * noise)[..., None]
    return np.clip(out, 0.0, 1.0)
