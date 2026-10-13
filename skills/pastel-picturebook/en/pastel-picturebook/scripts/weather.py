"""Weather over a finished layer: rain, snow or falling blossom petals.

  "weather": {"kind": "rain" | "snow" | "petals", "amount": 1.0, "wind": 12}

rain    the light turns grey and cool, a thin haze, slanted streaks of falling water
snow    a pale haze, flakes of every size: small and sharp far away, large and soft close by
petals  cherry petals drifting down: pink ovals turned every way, small and sharp far, large and soft near

Outdoors the weather covers the whole picture (figures included); an interior shows it only
through its windows (the painter passes the window mask).
"""
import cv2
import numpy as np

from raster import blur, mix, rgb

RAIN = {"tint": "#7D8898", "dim": 0.20, "haze": "#C9D2DC", "haze_amount": 0.08, "streak": "#E6EDF6", "count": 1100,
        "length": (0.018, 0.050), "opacity": (0.18, 0.55)}
SNOW = {"tint": "#D9DFE8", "dim": 0.10, "haze": "#E8EDF3", "haze_amount": 0.12, "flake": "#FFFFFF", "count": 900}
# Flake sizes (share of the picture width) and how many of each, far to near; near flakes are blurred.
FLAKE_LAYERS = ((0.0016, 0.55, 0.0), (0.0030, 0.30, 0.0006), (0.0060, 0.12, 0.0020), (0.0110, 0.03, 0.0045))
REFERENCE_AREA = 1200 * 1600
PETALS = {"tint": "#FFF4F6", "dim": 0.0, "haze": "#FFF0F4", "haze_amount": 0.03, "petal": "#F7B8CC", "petal_light": "#FFE9F0",
          "count": 420}
# Petal sizes (share of the picture width), share of the count and blur (share of the width), far to near.
PETAL_LAYERS = ((0.0030, 0.55, 0.0), (0.0050, 0.30, 0.0), (0.0085, 0.12, 0.0008), (0.0150, 0.03, 0.0030))


def screen_layer(image, color, layer, mask):
    """Screen-blend a coverage layer in `color` onto the image, inside `mask`."""
    amount = (np.clip(layer, 0.0, 1.0) * mask)[..., None]
    return image + (1.0 - image) * rgb(color) * amount


def rain_layer(size, setup, rng):
    """Coverage of slanted rain streaks."""
    height, width = size
    layer = np.zeros(size, np.float32)
    count = int(RAIN["count"] * setup.get("amount", 1.0) * height * width / REFERENCE_AREA)
    turn = np.deg2rad(setup.get("wind", 12.0))
    direction = np.array([np.sin(turn), np.cos(turn)])
    thickness = max(1, int(round(width / 1200)))
    for _ in range(count):
        start = np.array([rng.uniform(-0.1, 1.1) * width, rng.uniform(-0.05, 1.0) * height])
        end = start + direction * rng.uniform(*RAIN["length"]) * height
        shade = float(rng.uniform(*RAIN["opacity"]))
        cv2.line(layer, tuple(int(v) for v in start), tuple(int(v) for v in end), shade, thickness, cv2.LINE_AA)
    return layer


def snow_layer(size, setup, rng):
    """Coverage of snow flakes: four layers from far (small, sharp) to near (large, soft)."""
    height, width = size
    total = np.zeros(size, np.float32)
    count = SNOW["count"] * setup.get("amount", 1.0) * height * width / REFERENCE_AREA
    for radius, share, softness in FLAKE_LAYERS:
        layer = np.zeros(size, np.float32)
        for _ in range(int(count * share)):
            center = (int(rng.uniform(0, width)), int(rng.uniform(0, height)))
            r = max(1, int(round(radius * width * rng.uniform(0.7, 1.3))))
            cv2.circle(layer, center, r, float(rng.uniform(0.6, 1.0)), -1, cv2.LINE_AA)
        if softness > 0:
            layer = blur(layer, softness * width)
            layer = layer / max(float(layer.max()), 1e-6) * 0.9
        total = np.maximum(total, layer)
    return total


def petal_layers(size, setup, rng):
    """Coverage of falling petals and how much of each is its pale side (0..1): ovals at every angle."""
    height, width = size
    cover, pale = np.zeros(size, np.float32), np.zeros(size, np.float32)
    count = PETALS["count"] * setup.get("amount", 1.0) * height * width / REFERENCE_AREA
    for length, share, softness in PETAL_LAYERS:
        layer, light = np.zeros(size, np.float32), np.zeros(size, np.float32)
        for _ in range(int(count * share)):
            center = (int(rng.uniform(0, width)), int(rng.uniform(0, height)))
            long_axis = max(1, int(round(length * width * rng.uniform(0.7, 1.3))))
            # A petal seen edge-on is a sliver; seen flat it is nearly round.
            short_axis = max(1, int(round(long_axis * rng.uniform(0.25, 0.7))))
            angle = float(rng.uniform(0, 180))
            cv2.ellipse(layer, center, (long_axis, short_axis), angle, 0, 360, 1.0, -1, cv2.LINE_AA)
            if rng.random() < 0.5:
                cv2.ellipse(light, center, (long_axis, short_axis), angle, 0, 360, 1.0, -1, cv2.LINE_AA)
        if softness > 0:
            layer, light = blur(layer, softness * width), blur(light, softness * width)
        newer = layer > cover
        pale = np.where(newer, light, pale)
        cover = np.maximum(cover, layer)
    return np.clip(cover, 0.0, 1.0), np.clip(pale, 0.0, 1.0)


def apply_weather(image, setup, seed, mask=None, shelter=None):
    """Return the image with the weather laid over it (inside `mask` when given).

    `shelter` (0..1) keeps the falling rain or snow off a dry area: an umbrella and the column under it.
    The grey light and the haze still cover it.
    """
    if not setup or not setup.get("kind"):
        return image
    kind = setup["kind"]
    if kind not in ("rain", "snow", "petals"):
        raise ValueError(f"unknown weather {kind!r}: use rain, snow or petals")
    size = image.shape[:2]
    mask = np.ones(size, np.float32) if mask is None else mask.astype(np.float32)
    rng = np.random.default_rng(seed + 211)
    look = {"rain": RAIN, "snow": SNOW, "petals": PETALS}[kind]
    amount = setup.get("amount", 1.0)
    # The light goes grey: a cast toward the weather's tint, then a thin haze.
    tinted = image * mix(np.ones(3, np.float32), rgb(look["tint"]), look["dim"] * amount)
    image = image + (tinted - image) * mask[..., None]
    image = image + (rgb(look["haze"]) - image) * (mask * look["haze_amount"] * amount)[..., None]
    falling = mask if shelter is None else mask * (1.0 - np.clip(shelter, 0.0, 1.0))
    if kind == "rain":
        image = screen_layer(image, look["streak"], rain_layer(size, setup, rng), falling)
    elif kind == "petals":
        cover, pale = petal_layers(size, setup, rng)
        color = rgb(look["petal"]) + (rgb(look["petal_light"]) - rgb(look["petal"])) * pale[..., None]
        image = image + (color - image) * (cover * falling)[..., None] * 0.95
    else:
        image = screen_layer(image, look["flake"], snow_layer(size, setup, rng), falling)
    return np.clip(image, 0.0, 1.0).astype(np.float32)
