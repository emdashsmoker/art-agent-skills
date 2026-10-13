"""Color utilities. Every color is an sRGB 0-1 float32 array of length 3."""
import colorsys

import numpy as np

# Lowering value alone makes shadow colors muddy. Pushing hue toward cool and raising saturation keeps them
# clear.
SHADE_HUE_TARGET = 0.66  # blue on the HSV hue wheel
SHADE_HUE_PULL = 0.10
# Raise saturation by this fraction of the remaining headroom. A multiplier would saturate dark colors into
# pure hues.
SHADE_SATURATION_PULL = 0.3
SHADE_VALUE_GAIN = 0.72

# Highlights mix in white with a slight lean toward warm.
TINT_TARGET = (1.0, 0.98, 0.92)


def rgb(value):
    """Convert a '#rrggbb' string or a 0-1 / 0-255 tuple to a 0-1 float32 array."""
    if isinstance(value, str):
        text = value.lstrip("#")
        if len(text) == 3:
            text = "".join(character * 2 for character in text)
        if len(text) != 6:
            raise ValueError(f"color string must be #rgb or #rrggbb: {value!r}")
        return np.array([int(text[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    array = np.asarray(value, np.float32)
    if array.shape != (3,):
        raise ValueError(f"color must have 3 channels: {value!r}")
    return array / 255.0 if array.max() > 1.0 else array


def mix(color_a, color_b, amount):
    """Linear mix of two colors. amount 0 gives a, 1 gives b."""
    return rgb(color_a) * (1.0 - amount) + rgb(color_b) * amount


def shift(color, hue=0.0, saturation=1.0, value=1.0):
    """Apply a hue shift (0-1 rotation), a saturation factor and a value factor in HSV space."""
    h, s, v = colorsys.rgb_to_hsv(*rgb(color))
    h = (h + hue) % 1.0
    s = min(max(s * saturation, 0.0), 1.0)
    v = min(max(v * value, 0.0), 1.0)
    return np.array(colorsys.hsv_to_rgb(h, s, v), np.float32)


def shade(color, depth=1.0):
    """Make a shadow color. depth 1 is the standard first shadow, 2 is a deeper second shadow."""
    h, s, v = colorsys.rgb_to_hsv(*rgb(color))
    # Pull along the shortest direction to blue on the hue wheel.
    delta = ((SHADE_HUE_TARGET - h + 0.5) % 1.0) - 0.5
    h = (h + delta * min(SHADE_HUE_PULL * depth, 1.0)) % 1.0
    s = s + (1.0 - s) * min(SHADE_SATURATION_PULL * depth, 1.0)
    v = v * SHADE_VALUE_GAIN ** depth
    return np.array(colorsys.hsv_to_rgb(h, s, v), np.float32)


def tint(color, amount=0.5):
    """Make a highlight color. A larger amount moves it closer to warm white."""
    return mix(color, TINT_TARGET, amount)


def luminance(image):
    """Rec.709 luminance. Input is an (..., 3) array."""
    return image[..., 0] * 0.2126 + image[..., 1] * 0.7152 + image[..., 2] * 0.0722
