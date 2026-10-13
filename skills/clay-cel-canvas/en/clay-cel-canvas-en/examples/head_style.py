"""Choices for a painted head: hair style, hair colour, eyes, brows, lips, eye colour,
and the props it wears or holds (earrings or earphones, a hat, a cigarette).

A HeadLook names the choices; fields left as None take the head's own default
(portrait.DEFAULT_LOOK, portrait_male.DEFAULT_LOOK). A head module applies a look
with `with head.styled(look):` around its drawing calls.

Colours: a hair colour is a palette name below or any "#RRGGBB"; from one hex the
four tones a head needs are worked out (deep for the shade toward the ends, light
for the sheen, shadow for the cel-shadow tint, brow for the eyebrows).
"""
from dataclasses import dataclass, fields, replace

import numpy as np

from atelier.color import adjust, mix

# Hair: (hair, deep, light, shadow, brow). navy and ink are the original heads' colours.
HAIR_COLOURS = {
    "navy": ("#2D315C", "#1B1D3D", "#8E9BE0", "#7668B0", "#2A2748"),
    "ink": ("#262233", "#14111C", "#7E8BC0", "#4A4468", "#231E2A"),
    "black": ("#1E1B22", "#0F0D12", "#6E7690", "#3E3A4E", "#1E1A24"),
    "dark_brown": ("#3B2620", "#22150F", "#A07A62", "#6A4A48", "#3A2620"),
    "chestnut": ("#7A3E26", "#4A2214", "#D99A6A", "#9A5A4E", "#5A2E1E"),
    "honey": ("#D9A957", "#A9783A", "#FFF0BC", "#C9906A", "#9A6E3A"),
    "platinum": ("#E3DCC8", "#B3A992", "#FFFFFF", "#B9AFC4", "#9A8E78"),
    "silver": ("#9BA0AE", "#686C7C", "#E6EAF4", "#7E7A9E", "#6A6E7C"),
    "burgundy": ("#6A1F33", "#3E0F1E", "#D0708A", "#8E4A6E", "#4A1626"),
}
# Eyes: (iris, iris_dark, iris_light). amber and blue are the original heads' colours.
EYE_COLOURS = {
    "amber": ("#C8872F", "#6B3A17", "#FFD98A"),
    "blue": ("#4F7FA0", "#1F3448", "#9FD0EC"),
    "brown": ("#7A4A2A", "#3A2012", "#C99A6A"),
    "green": ("#4E8A5A", "#1F3F28", "#A8E0A0"),
    "grey": ("#7D8794", "#333B47", "#D0D8E2"),
    "violet": ("#8A62B0", "#3E2558", "#D4B8F0"),
}
HAIR_KEYS = ("hair", "hair_deep", "hair_light", "hair_shadow", "brow")
EYE_KEYS = ("iris", "iris_dark", "iris_light")
SHADOW_TINT = "#7668B0"          # cool violet the derived cel-shadow tint leans toward
DEEP_VALUE = 0.58                # derived tones: value scale of the deep shade
LIGHT_MIX = 0.55                 # share of white in the sheen
SHADOW_MIX = 0.35                # share of the violet tint in the shadow tone
BROW_VALUE = 0.72                # brows a little darker than the hair
IRIS_DARK_VALUE = 0.45           # derived iris tones: the dark rim and upper shade
IRIS_LIGHT_MIX = 0.55            # share of white in the iris's lower glow


@dataclass(frozen=True)
class HeadLook:
    hair: str = None             # style name; each head lists its own (HAIR_STYLES)
    hair_colour: str = None      # HAIR_COLOURS name or "#RRGGBB"
    eyes: str = None             # eye shape (female head: sharp, round, soft)
    brows: str = None            # brow shape (female: natural, straight, arched; male: straight, soft)
    lips: str = None             # female head: natural, full, thin
    eye_colour: str = None       # EYE_COLOURS name or "#RRGGBB"
    earrings: str = None         # female head: drop (a gold drop), earphones, none; male head: earphones, none
    hat: str = None              # none, beanie (a dark knit beanie)
    cigarette: str = None        # none, lit (held at the mouth corner, smoke rising)


def merged(look, default):
    """The look with every unset field taken from the head's default."""
    look = look or HeadLook()
    return replace(default, **{f.name: getattr(look, f.name) for f in fields(look)
                               if getattr(look, f.name) is not None})


def _hex(colour):
    return "#" + "".join(f"{int(round(float(c) * 255)):02X}" for c in np.clip(colour, 0.0, 1.0))


def hair_tones(colour):
    """(hair, deep, light, shadow, brow) for a palette name or a hex colour."""
    if colour in HAIR_COLOURS:
        return HAIR_COLOURS[colour]
    if not (isinstance(colour, str) and colour.startswith("#")):
        raise ValueError(f"unknown hair colour {colour!r}; choose from {sorted(HAIR_COLOURS)} or give #RRGGBB")
    return (colour, _hex(adjust(colour, value=DEEP_VALUE)), _hex(mix(colour, "#FFFFFF", LIGHT_MIX)),
            _hex(mix(colour, SHADOW_TINT, SHADOW_MIX)), _hex(adjust(colour, value=BROW_VALUE)))


def eye_tones(colour):
    """(iris, iris_dark, iris_light) for a palette name or a hex colour."""
    if colour in EYE_COLOURS:
        return EYE_COLOURS[colour]
    if not (isinstance(colour, str) and colour.startswith("#")):
        raise ValueError(f"unknown eye colour {colour!r}; choose from {sorted(EYE_COLOURS)} or give #RRGGBB")
    return colour, _hex(adjust(colour, value=IRIS_DARK_VALUE)), _hex(mix(colour, "#FFFFFF", IRIS_LIGHT_MIX))


def palette_for(look):
    """PALETTE entries a look sets: hair tones, brows, iris tones."""
    return {**dict(zip(HAIR_KEYS, hair_tones(look.hair_colour))),
            **dict(zip(EYE_KEYS, eye_tones(look.eye_colour)))}


def check(look, choices):
    """Refuse a name the head does not have. choices: {field: allowed names}."""
    for field, allowed in choices.items():
        value = getattr(look, field)
        if value not in allowed:
            raise ValueError(f"unknown {field} {value!r} for this head; choose from {sorted(allowed)}")
