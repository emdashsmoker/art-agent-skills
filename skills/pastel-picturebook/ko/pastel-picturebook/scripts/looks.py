"""A character's look: face shape, eye shape, hair style and colour, skin tone, freckles and moles, identity.

Spec key "look", for example
  {"face_shape": "round", "eye_shape": "big", "hair_style": "ponytail", "hair_color": "brown", "eye_color": "hazel",
   "skin_tone": "tan", "freckles": 0.6, "moles": [[0.35, 0.55]], "identity": 12}
Presets nudge the current settings (assets/looks.json), so a look keeps each style's own proportions.
Settings the user wrote explicitly are left alone. The identity seed then shifts every face
setting a little within fixed limits, so two characters from the same style read as different people.
"""
import json
from pathlib import Path

import numpy as np

from expressions import apply_ops, get_path, set_path

LOOKS_FILE = Path(__file__).resolve().parent.parent / "assets" / "looks.json"
# The skin highlight darkens less than the rest: a fraction of the tone change.
HIGHLIGHT_SHARE = 0.5
# Lips follow the skin's darkening at this share.
LIP_SHARE = 0.6


def channels(hex_color):
    """'#RRGGBB' -> three floats 0..1."""
    return np.array([int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def to_hex(color):
    return "#{:02X}{:02X}{:02X}".format(*(int(round(v * 255)) for v in np.clip(color, 0.0, 1.0)))


def apply_skin_tone(style, target, reference):
    """Recolour skin (and, less, the lips) by the target's ratio to the reference skin, channel by channel.

    Why a ratio: each style keeps its own skin palette (paler anime, warmer oil); the tone only moves it.
    """
    ratio = channels(target) / channels(reference)
    for name, value in style["palette"]["skin"].items():
        factor = ratio ** HIGHLIGHT_SHARE if name == "light" else ratio
        style["palette"]["skin"][name] = to_hex(channels(value) * factor)
    for name, value in style["palette"].get("lip", {}).items():
        if name != "shine":
            style["palette"]["lip"][name] = to_hex(channels(value) * ratio ** LIP_SHARE)


def apply_identity(spec, setup, presets):
    """Shift each face setting by a seeded amount within its limit."""
    if isinstance(setup, (int, float)):
        setup = {"seed": int(setup)}
    rng = np.random.default_rng(setup["seed"])
    amount = setup.get("amount", 1.0)
    for path, reach in presets["identity"].items():
        value = get_path(spec, path, None)
        if value is None:
            continue
        value = value + rng.uniform(-reach, reach) * amount
        low, high = presets["limits"].get(path, (-np.inf, np.inf))
        set_path(spec, path, float(np.clip(value, low, high)))


def apply_look(spec, style, user):
    """Apply spec["look"] in place. `user` is the spec the user wrote; its explicit settings win."""
    look = spec.get("look")
    if not look:
        return
    presets = json.loads(LOOKS_FILE.read_text(encoding="utf-8"))
    for key in ("face_shape", "eye_shape", "hair_style"):
        if key in look:
            if look[key] not in presets[key]:
                raise ValueError(f"unknown {key} {look[key]!r}; known: {sorted(presets[key])}")
            apply_ops(spec, style, presets[key][look[key]], keep=user)
    if "skin_tone" in look:
        tones = presets["skin_tone"]
        apply_skin_tone(style, tones[look["skin_tone"]], tones["reference"])
    if "hair_color" in look:
        style["palette"]["hair"] = dict(presets["hair_color"][look["hair_color"]])
    if "eye_color" in look:
        style["palette"]["eye"].update(presets["eye_color"][look["eye_color"]])
    if "identity" in look:
        apply_identity(spec, look["identity"], presets)
