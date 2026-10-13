"""Surface finish per material: how strongly and how tightly a surface reflects the key light.

Looked up by the last part of a material name ('table.wood' -> 'wood'), so any prop or garment
that reuses a name gets the same finish. (strength 0..1, shininess: higher = smaller, sharper highlight)
"""

MATTE = (0.0, 1.0)

GLOSS = {
    # people
    "skin": (0.16, 12.0), "hair": (0.0, 1.0), "eye": (0.0, 1.0), "teeth": (0.35, 40.0), "tongue": (0.3, 30.0),
    # glass, glaze, metal (shininess kept moderate: a painter states a highlight larger than a camera records it)
    "glass": (1.3, 70.0), "bulb": (0.9, 60.0), "bottle": (1.2, 45.0), "vase": (0.8, 30.0), "teapot": (0.85, 34.0),
    "mug": (0.6, 28.0), "bowl": (0.5, 24.0), "plate": (0.5, 24.0), "wine": (0.9, 50.0),
    "brass": (1.0, 26.0), "steel": (1.1, 40.0), "metal": (0.8, 30.0), "screen": (0.3, 40.0), "laptop": (0.35, 22.0),
    "phone": (0.5, 40.0), "car": (0.9, 36.0), "car_glass": (1.0, 50.0), "lamp_base": (0.4, 24.0),
    # fruit and plants
    "apple": (0.75, 26.0), "peach": (0.12, 8.0), "pear": (0.4, 16.0), "orange": (0.35, 12.0), "lemon": (0.4, 14.0),
    "grapes": (0.8, 30.0), "leaf": (0.3, 16.0), "petal": (0.1, 8.0),
    # stone, wood, clay
    "amphora": (0.14, 7.0), "stone": (0.08, 6.0), "table": (0.28, 18.0), "desk": (0.3, 20.0), "chair": (0.2, 16.0),
    "stool": (0.2, 16.0), "book": (0.18, 12.0), "candle": (0.25, 12.0), "pot": (0.1, 8.0), "ball": (0.6, 28.0),
    "floor": (0.0, 1.0), "frame": (0.3, 18.0), "mattress": (0.25, 12.0), "bolster": (0.3, 14.0),
    # cloth with a sheen
    "gown": (0.35, 18.0), "dress": (0.08, 8.0), "bodysuit": (0.45, 24.0), "swimsuit": (0.35, 22.0), "bikini_top": (0.3, 20.0),
    "bikini_bottom": (0.3, 20.0), "leggings": (0.3, 20.0), "boots": (0.45, 24.0), "shoes": (0.35, 22.0), "belt": (0.4, 24.0),
    "obi": (0.3, 16.0), "kimono_top": (0.15, 10.0), "kimono_skirt": (0.15, 10.0), "vest": (0.15, 10.0),
    "building": (0.0, 1.0),
    # modern objects
    "screen_off": (1.0, 60.0), "monitor": (0.35, 24.0), "stand": (0.8, 30.0), "keyboard": (0.2, 14.0), "keys": (0.15, 12.0),
    "mouse": (0.5, 30.0), "case": (0.4, 24.0), "pad": (0.3, 20.0), "tablet": (0.5, 36.0), "earcup": (0.3, 20.0),
    "cushion": (0.05, 6.0), "band": (0.4, 24.0), "controller": (0.4, 24.0), "stick": (0.2, 12.0), "camera": (0.3, 20.0),
    "lens": (0.5, 30.0), "glass_lens": (1.3, 70.0), "cone": (0.1, 8.0), "cup": (0.2, 10.0), "lid": (0.3, 16.0),
    "sleeve": (0.05, 6.0), "clock_face": (0.2, 14.0), "clock_rim": (0.6, 30.0), "lamp_arm": (0.9, 36.0),
    "lamp_shade": (0.5, 24.0), "chrome": (1.1, 40.0), "trunks": (0.3, 20.0), "sports_tee": (0.04, 6.0), "shorts": (0.04, 6.0), "upholstery": (0.1, 8.0), "sofa": (0.05, 6.0), "shelf": (0.2, 14.0),
}
# materials you can see through: opacity when viewed straight on (edges are always more opaque)
TRANSPARENT = {"glass": 0.16, "bulb": 0.5, "car_glass": 0.55}


def key_of(material):
    return material.rsplit(".", 1)[-1]


def gloss_of(material):
    return GLOSS.get(key_of(material), MATTE)
