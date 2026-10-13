"""Finishing passes (stage 5): what turns a clean render into a style.

  anime   diffusion glow + warm/cool light wash
  illust  paper grain + print-like tone texture
  paint   the whole image re-built from brush strokes on canvas
  watercolor, pencil, manga, pixel   see media.py
"""
import numpy as np

import brushwork
import media
from raster import blur, fill_many, noise, rgb, smoothstep, stroke

# Focus levels: how much fine brushwork each region of the portrait deserves.
# Glaze starts on regions of this focus and is full from the second value up.
GLAZE_FROM, GLAZE_FULL = 0.30, 0.60
FOCUS = {"background": 0.0, "cloth": 0.3, "hair": 0.4, "body": 0.5, "face": 0.75, "features": 1.0}


def light_wash(image, light, warm_hex, cool_hex, strength):
    """Warm tint where the lamp comes from, cool tint on the far side."""
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    along = (xs / width - 0.5) * light[0] + (ys / height - 0.5) * light[1]
    toward = smoothstep(along, -0.05, 0.45)[..., None]
    away = smoothstep(-along, -0.05, 0.45)[..., None]
    image = image + (1.0 - image) * rgb(warm_hex) * toward * strength
    return image * (1.0 - away * strength * (1.0 - rgb(cool_hex)))


def diffusion_glow(image, radius, strength):
    """Bright areas bleed softly into their surroundings (the 'anime glow')."""
    bright = blur(np.clip(image - 0.55, 0.0, 1.0) / 0.45, radius)
    return image + (1.0 - image) * bright * strength


def vignette(image, strength):
    """Darken the corners to hold the eye on the face."""
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    distance = np.hypot((xs / width - 0.5) * 1.1, (ys / height - 0.45))
    return image * (1.0 - strength * smoothstep(distance, 0.35, 0.85))[..., None]


def finish_anime(image, fig, options):
    image = light_wash(image, fig.light, options["warm"], options["cool"], options["wash"])
    image = diffusion_glow(image, fig.unit * options["glow_radius"], options["glow"])
    return vignette(image, options["vignette"])


def finish_illust(image, fig, options, seed):
    """Printed-illustration feel: paper tooth plus a fine ink grain."""
    height, width = image.shape[:2]
    paper = noise((height, width), options["paper_cell"], seed + 3, 3)
    rng = np.random.default_rng(seed + 4)
    grain = blur(rng.random((height, width), dtype=np.float32), 0.6)
    grain = (grain - grain.mean()) / grain.std()
    image = image * (1.0 + options["paper"] * (paper - 0.5))[..., None]
    image = image + (options["grain"] * grain)[..., None]
    return vignette(image, options["vignette"])


def focus_map(fig):
    """Per-pixel detail budget: the subject's own map if it made one, else built from portrait shapes."""
    if fig.focus is not None:
        return fig.focus
    size = fig.size
    focus = np.full(size, FOCUS["background"], np.float32)
    regions = [("cloth", ["cloth"]), ("hair", ["hair_back", "hair_near", "hair_far"]),
               ("body", ["skin_body"]), ("face", ["face"])]
    for level, names in regions:
        mask = fill_many(size, [fig.shapes[name] for name in names])
        focus = np.where(mask > 0.5, FOCUS[level], focus)
    features = [fig.shapes[name] for name in ("eye_far_opening", "eye_near_opening", "eye_far_lash",
                                              "eye_near_lash", "upper_lip", "lower_lip", "nose_under")]
    detail = fill_many(size, features)
    for name in ("eye_far_brow", "eye_near_brow"):
        detail = np.maximum(detail, stroke(size, fig.paths[name], fig.unit * 0.06))
    detail = blur(detail, fig.unit * 0.05) > 0.05
    return np.where(detail, FOCUS["features"], focus).astype(np.float32)


def finish_paint(image, fig, options, seed):
    focus = focus_map(fig)
    painted = brushwork.paint(image, focus, fig.light, options, seed)
    glaze = options.get("glaze", 0.0)
    if glaze > 0:
        # Why: painters finish skin with thin glazes that melt the brushwork; here the smooth
        # underpainting is laid back over the strokes, most where detail matters.
        weight = glaze * smoothstep(focus, GLAZE_FROM, GLAZE_FULL)
        painted = painted + (image - painted) * weight[..., None]
    return vignette(painted, options["vignette"])


FINISHERS = {"anime": lambda image, fig, options, seed: finish_anime(image, fig, options),
             "illust": finish_illust,
             "paint": finish_paint,
             "none": lambda image, fig, options, seed: image,
             **media.FINISHERS}


def finish(image, fig, style, seed):
    """Apply the finishing pass named by the style."""
    return np.clip(FINISHERS[style["finish"]["kind"]](image, fig, style["finish"], seed), 0.0, 1.0)
