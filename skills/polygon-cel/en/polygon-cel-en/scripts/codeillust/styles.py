"""Style presets and style-specific finishing.

A style is (a) renderer parameters for lines and shading and (b) a
finishing transform. Cel and soft styles composite lines directly; oil
repaints the render with brush strokes; watercolor converts it into
transparent washes with pencil lines.
"""
from enum import Enum

import cv2
import numpy as np

from . import painterly, raster, watercolor
from .scene import Style


class StyleName(Enum):
    ANIME_CEL = "anime_cel"
    SOFT_ILLUST = "soft_illust"
    PAINTERLY = "painterly"
    WATERCOLOR = "watercolor"


PRESETS = {
    StyleName.ANIME_CEL: Style("anime_cel", line_scale=1.0, line_darkness=0.55, line_light_mod=0.9, line_lit_min=0.6,
                               shadow_soft=0.7, shadow_depth=0.20, two_tone=True, rim=0.8, highlight=1.0),
    StyleName.SOFT_ILLUST: Style("soft_illust", line_scale=0.70, line_darkness=0.38, line_light_mod=0.8,
                                 line_lit_min=0.35, line_alpha=0.9, shadow_soft=6.0, shadow_depth=0.17,
                                 shadow_alpha=0.85, two_tone=False, rim=1.3, highlight=1.2),
    StyleName.PAINTERLY: Style("painterly", line_scale=0.60, line_darkness=0.35, line_alpha=1.0, shadow_soft=4.0,
                               shadow_depth=0.22, shadow_alpha=0.9, two_tone=False, rim=1.2, highlight=1.2),
    StyleName.WATERCOLOR: Style("watercolor", line_scale=0.55, line_darkness=0.30, line_light_mod=1.2,
                                line_lit_min=0.3, line_alpha=0.9, shadow_soft=2.5, shadow_depth=0.17,
                                shadow_alpha=0.8, two_tone=False, rim=0.0, highlight=0.6),
}

POST_DEFAULTS = {
    StyleName.ANIME_CEL: {"light_wash": 0.20, "bloom": 0.12, "grade": "neutral", "vignette": 0.0, "grain": 0.0},
    StyleName.SOFT_ILLUST: {"light_wash": 0.40, "bloom": 0.22, "grade": "warm", "grade_amount": 0.25,
                            "vignette": 0.12, "grain": 0.006, "vibrance": 0.12},
    StyleName.PAINTERLY: {"light_wash": 0.35, "bloom": 0.10, "grade": "warm", "grade_amount": 0.25,
                          "vignette": 0.22, "grain": 0.0},
    StyleName.WATERCOLOR: {"light_wash": 0.0, "bloom": 0.0, "grade": "neutral", "vignette": 0.0, "grain": 0.0},
}

# tags dropped per style: hatch marks are a cel convention
DROP_TAGS = {
    StyleName.ANIME_CEL: (),
    StyleName.SOFT_ILLUST: ("blush_hatch",),
    StyleName.PAINTERLY: ("blush_hatch",),
    StyleName.WATERCOLOR: ("blush_hatch",),
}

OIL_LINE_ALPHA = 0.30     # underdrawing kept under the paint
OIL_LINE_OVER = 0.35      # line work restated over the paint
OIL_FACE_BRUSH = 0.012    # finishing brush radius as a fraction of head height
OIL_EYE_RESTORE = 0.65    # eyes keep most of their rendered detail
OIL_MOUTH_RESTORE = 0.55  # the mouth keeps enough line work to read the expression
OIL_SMALL_FACE = 0.06     # tallest face below this share of the canvas height: a distant figure (wide shot)
WATERCOLOR_PROTECT = ("eye", "brows", "mouth", "lip", "nose")   # features kept out of wet blooms


def filter_layers(layers, name):
    drop = DROP_TAGS[name]
    return [L for L in layers if not any(t in L.tags for t in drop)]


def union_mask(masks, names=None, prefixes=()):
    acc = None
    for k, m in masks.items():
        if (names is None and not prefixes) or (names and k in names) or any(k.startswith(p) for p in prefixes):
            acc = m.copy() if acc is None else np.maximum(acc, m)
    return acc


def finish(name, paint, line_rgb, line_a, masks, seed, backdrop=False):
    """backdrop: the picture has a rendered setting (scene, beach, sky) that must not fade away."""
    if name in (StyleName.ANIME_CEL, StyleName.SOFT_ILLUST):
        return raster.over(paint, line_rgb, line_a)
    if name == StyleName.PAINTERLY:
        ref = raster.over(paint, line_rgb, line_a * OIL_LINE_ALPHA)
        face = union_mask(masks, prefixes=("face", "eye", "mouth", "nose", "brows"))
        detail = raster.blur(face, 0.01 * paint.shape[1]) if face is not None else None
        face_r = None
        if "face" in masks:
            # the tallest face sets the brush; two faces side by side must not add up their heights
            n, _, stats, _ = cv2.connectedComponentsWithStats((masks["face"] > 0.5).astype(np.uint8))
            if n > 1:
                face_h = stats[1:, cv2.CC_STAT_HEIGHT].max() - 1
                face_r = OIL_FACE_BRUSH * face_h
                fig = union_mask(masks)
                if face_h < OIL_SMALL_FACE * paint.shape[0] and fig is not None:
                    # a distant figure is only a few brush widths across; the coarse brushes smeared its hands
                    # and face into the street (v13 doomer wide shot), so the finishing pass covers all of it
                    detail = np.maximum(detail, raster.blur(fig, 0.002 * paint.shape[1]))
        out = painterly.paint(ref, seed, detail_mask=detail, face_radius=face_r)
        eyes = union_mask(masks, prefixes=("eyeL", "eyeR", "brows"))
        mouth = union_mask(masks, prefixes=("mouth", "lip"))
        keep = None
        if eyes is not None:
            keep = raster.blur(raster.dilate(eyes, 3), 2.5) * OIL_EYE_RESTORE
        if mouth is not None:
            # the small finishing brush smeared mouths into pink blots, hiding the expression (v10 showcase)
            m = raster.blur(raster.dilate(mouth, 3), 2.5) * OIL_MOUTH_RESTORE
            keep = m if keep is None else np.maximum(keep, m)
        if keep is not None:
            out = raster.over(out, raster.over(paint, line_rgb, line_a), keep)
        out = raster.multiply(out, np.clip(line_rgb * 1.15, 0, 1), line_a * OIL_LINE_OVER)
        return painterly.canvas_texture(out, 0.04, seed)
    if name == StyleName.WATERCOLOR:
        fig = union_mask(masks)
        features = union_mask(masks, prefixes=WATERCOLOR_PROTECT)
        return watercolor.watercolor(paint, line_rgb, line_a, fig if fig is not None else np.zeros(paint.shape[:2]),
                                     seed, fade_background=not backdrop, protect=features)
    raise ValueError(f"unknown style: {name}")


def downsample(img, factor):
    if factor == 1:
        return img
    h, w = img.shape[:2]
    return cv2.resize(img, (w // factor, h // factor), interpolation=cv2.INTER_AREA)
