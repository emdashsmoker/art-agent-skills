"""Named colours for people: skin, hair, eyes, lips and outfit schemes, checked together.

look() turns names into PortraitSpec colour fields, picking a lip colour that suits the skin:
    PortraitSpec(**FACES["cool"], **look("tan", "auburn", "green", "sea"))
"""
from ..color import mix, rgb

# From the fairest to the deepest; the face and body rigs move blush and shadow-edge colours with skin depth.
SKIN = {
    "porcelain": "#fbe9de",
    "fair": "#f6d9c4",
    "light": "#efc6a4",
    "olive": "#d8aa82",
    "tan": "#c08a60",
    "brown": "#946043",
    "deep": "#66412e",
}
# Lip colour that reads as natural on each skin, with no lipstick.
LIP = {
    "porcelain": "#d06e76", "fair": "#c96a70", "light": "#c0625f", "olive": "#b25d5a",
    "tan": "#a4544e", "brown": "#8a4943", "deep": "#6c3a35",
}
HAIR = {
    # natural
    "black": "#1f1a20", "dark_brown": "#3a2a26", "brown": "#6a4632", "chestnut": "#8a4b2c",
    "auburn": "#9c3f24", "blonde": "#d9b46a", "platinum": "#ebe0c6", "gray": "#9a9aa0",
    # anime
    "pink": "#f2a0b8", "sky": "#7fb8e8", "silver": "#c9ccd8", "lavender": "#b39ad8", "mint": "#86d1b4", "crimson": "#b8283c",
}
EYE = {
    # natural
    "brown": "#6e4a2c", "amber": "#b07a2a", "hazel": "#8a7a3c", "green": "#4f8a52", "blue": "#4a7ab8", "gray": "#7a8590",
    # anime
    "red": "#c0303a", "violet": "#8a52c8", "gold": "#d8a830", "teal": "#2aa3a0",
}
# Outfit schemes: (cloth, cloth_second). Which part each colour goes to depends on the outfit (see the wardrobe docs).
OUTFIT = {
    "classic": ("#2b3140", "#e9e4da"),
    "warm": ("#c7445a", "#3a3a40"),
    "earth": ("#8a6a4a", "#e8dcc8"),
    "pastel": ("#b8a0c8", "#f1ede4"),
    "sea": ("#2a8a86", "#f4f0e6"),
    "mono": ("#1c1a22", "#d8d8dc"),
    "denim": ("#e8e0d0", "#3a5a8a"),
    "doomer": ("#1c1c22", "#2e3440"),      # black hoodie or coat over dark slate trousers
}
NATURAL_HAIR = ("black", "dark_brown", "brown", "chestnut", "auburn", "blonde", "platinum", "gray")
ANIME_HAIR = ("pink", "sky", "silver", "lavender", "mint", "crimson")


def look(skin="fair", hair="dark_brown", eye="brown", outfit=None, lipstick=None, lipstick_amount=0.6):
    """PortraitSpec colour fields from palette names. Hex colours are accepted in place of any name.

    outfit: an OUTFIT name (fills cloth and cloth_second) or None to leave the clothes alone.
    lipstick: optional colour mixed into the natural lip by lipstick_amount.
    """
    fields = {"skin": _pick(SKIN, skin), "hair": _pick(HAIR, hair), "eye": _pick(EYE, eye)}
    lip = LIP.get(skin, _lip_for(fields["skin"]))
    fields["lip"] = mix(lip, rgb(lipstick), lipstick_amount) if lipstick else lip
    if outfit is not None:
        fields["cloth"], fields["cloth_second"] = OUTFIT[outfit] if outfit in OUTFIT else outfit
    return fields


def _pick(table, name):
    if name in table:
        return table[name]
    if isinstance(name, str) and name.startswith("#"):
        return name
    raise ValueError(f"unknown colour name: {name} (choose from {', '.join(table)})")


def _lip_for(skin):
    """Lip colour for a skin given as a hex colour: the palette lip of the nearest skin."""
    target = rgb(skin)
    nearest = min(SKIN, key=lambda name: float(((rgb(SKIN[name]) - target) ** 2).sum()))
    return LIP[nearest]
