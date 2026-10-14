#!/usr/bin/env python3
"""Print every option the engine accepts (presets, styles, props, pose joints).

  python catalog.py            all sections
  python catalog.py styles     one section: figures | poses | hair | outfits | props | environments | light | styles | post | shapes
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atelier import beard, estate, face_shape, headwear, pairs, garment, hair, landscape, people, poses, post, props, scene, skin, spec, styles   # noqa: E402


def _line(label, values):
    print(f"  {label}: {', '.join(str(v) for v in values)}")


def figures():
    _line("presets", people.FIGURE_PRESETS)
    _line("skin", people.SKIN_TONES)
    _line("expressions", people.EXPRESSIONS)
    _line("hair colors", people.HAIR_COLORS)
    _line("eye colors (look.iris_color)", people.EYE_COLORS)
    _line("look keys", skin.DEFAULT_LOOK)
    _line("stylize (face proportions)", face_shape.STYLES)
    _line("beard", beard.STYLES)
    _line("hat", headwear.STYLES)


def pose_section():
    _line("body presets", poses.BODY_POSES)
    _line("pair kinds (pairs[].kind)", pairs.LAYOUTS)
    _line("group kinds (groups[].kind, 3+ people in a row)", pairs.CHAIN_KINDS)
    _line("hand presets", poses.HAND_PRESETS)
    print(poses.__doc__)


def hair_section():
    _line("styles", list(hair.STYLES) + ["bald"])
    _line("bangs", hair.BANGS)
    _line("part", ["center", "left", "right", "none"])


def outfits():
    _line("outfit presets", garment.OUTFITS)
    _line("garment types", garment.BUILDERS)
    _line("sleeves", garment.SLEEVES)
    _line("skirt lengths", garment.HEMS)
    _line("leg lengths", garment.LEG_HEMS)
    _line("necklines", ["turtle", "crew", "boat", "v", "deep_v", "open_collar", "collar_stand", "scoop", "square", "straps",
                        "halter", "strapless", "one_shoulder"])
    _line("men's automatic swaps", [f"{k} -> {v}" for k, v in garment.MALE_VARIANTS.items()])
    for name, items in garment.OUTFITS.items():
        print(f"  {name}: garment ids = {[g.get('id', g['type']) for g in items]}")


def prop_section():
    _line("props", props.CATALOGUE)
    _line("held_by", ["<figure>:hand.R", "<figure>:hand.L", "<figure>:hands"])
    _line("lying on the palm when held (others stand upright in the grip)", [k for k, v in props.HOLD_STYLES.items() if v == "rest"])
    _line("held between two fingers", [k for k, v in props.HOLD_STYLES.items() if v == "pinch"])
    _line("trees", ["broadleaf", "pine", "cypress", "birch", "bare", "palm", "sakura"])


def environments():
    _line("types", ["plain_color", "studio", "room", "landscape"])
    _line("landscape presets", spec.LANDSCAPES)
    _line("estate layouts (environment.estate.layout)", estate.LAYOUTS)
    _line("time of day", landscape.SKIES)
    _line("ground", ["grass", "meadow", "sand", "snow", "rock", "dirt"])


def light():
    _line("light presets", scene.LIGHT_PRESETS)
    _line("moods", scene.MOODS)
    _line("camera shots", list(scene.SHOTS) + ["over_shoulder (with over=<figure>, side=right|left)"])


def style_section():
    for name, entry in styles.STYLES.items():
        print(f"  {name}: {entry['about']}")


def post_section():
    _line("post keys", post.DEFAULTS)
    _line("grades (post.grade)", post.GRADES)
    _line("canvas detail", spec.DETAIL)


def shapes():
    from atelier import figure
    names = figure.shape_names()
    _line("phenotype (0..1)", names["phenotype"])
    _line("face / body morphs (-1..1)", names["local"])
    _line("expression units (0..1)", names["expression"])
    _line("bones (raw overrides)", figure.bone_names())


SECTIONS = {"figures": figures, "poses": pose_section, "hair": hair_section, "outfits": outfits, "props": prop_section,
            "environments": environments, "light": light, "styles": style_section, "post": post_section, "shapes": shapes}

if __name__ == "__main__":
    chosen = sys.argv[1:] or [k for k in SECTIONS if k != "shapes"]
    for key in chosen:
        print(f"[{key}]")
        SECTIONS[key]()
