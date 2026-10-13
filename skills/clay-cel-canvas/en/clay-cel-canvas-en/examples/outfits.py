"""Worked example: clothed figures, alone or in pairs, from a choice of outfit, pose,
place and shot.

Usage:
  python outfits.py <anime|illust|painterly> <output.png> [width_px] [look]
  python outfits.py <style> <output.png> <width_px> custom <f|m> <outfit> <pose> <place> [shot] [azimuth]

A look is one line of choices (see LOOKS); a duo is two people and a pair pose
(see DUOS). The machinery underneath:
- atelier.staging: the pose (fitted to the body), pair poses, the camera for the shot;
- atelier.wardrobe: clothes that follow the body; atelier.drape: skirts, dresses,
  scarves, which fall free and move in the wind;
- scenes.py: the backdrop and the furniture the pose touches;
- figure study.draw_cast: render everyone together, paint far to near, heads turned to match.
The clothed man is built on the lean physique of figure_male.py.
"""
import sys
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_male  # noqa: E402
import figure_study  # noqa: E402
import figure_study_male  # noqa: E402
from atelier import drape as d  # noqa: E402
from atelier import wardrobe as w  # noqa: E402
from atelier.mannequin import Trunk, build  # noqa: E402
from atelier.sculpt import Scene  # noqa: E402
from atelier.staging import frame, pair_for, pose_for  # noqa: E402
from scenes import PLACES, ground_prop, looking_back  # noqa: E402

WOMAN = figure_study.WOMAN
MAN = replace(figure_study_male.MAN, physique=figure_male.LEAN)
WOMAN_BUST = 0.95
FALLBACK_SUPPORT = ("#8A8290", "#5A5262")     # colour for a support the place has no colour for
BREEZE = (0.35, -0.06, 0.05)                   # wind: metres of hem sway toward the viewer's right
TUCKED_EASE = 0.014                            # skirt waist room over a tee tucked in under it
DARK_HOODIE = ("#2B2C33", "#15161B")           # dark_hoodie outfit: (colour, shadow) of the hoodie
DARK_STRINGS = ("#C9CBD2", "#8A8D99")
DARK_JEANS = ("#2E3442", "#181C26")


@dataclass(frozen=True)
class Look:
    sex: str                 # "f" or "m"
    outfit: str
    pose: str
    place: str
    shot: str = "full"
    azimuth: float = 20.0    # degrees round the figure; positive shows more of the figure's left side
    elevation: float = 5.0
    aspect: float = 1.5      # height / width of the picture
    margin: float = 0.08     # share of the picture left empty round the figure
    wind: tuple = None       # world vector for skirts and scarves, metres of sway
    face: object = None      # head_style.HeadLook: hair, hair colour, eyes, brows, lips; None: the default head


@dataclass(frozen=True)
class Duo:
    first: tuple             # (sex, outfit) of the person on the viewer's left
    second: tuple
    pair: str                # staging.pair_for name
    place: str
    shot: str = "full"
    azimuth: float = 0.0
    elevation: float = 5.0
    aspect: float = 1.0
    margin: float = 0.08
    wind: tuple = None
    faces: tuple = (None, None)   # a HeadLook (or None) for each person, left to right


def _female(sitter):
    return sitter.physique.trunk is Trunk.FEMALE


def dress_outfit(name, scene, marks, sitter, pose, wind=None):
    """Build an outfit on the posed body; returns what to paint."""
    body = sitter.physique
    female = _female(sitter)
    if name in ("innerwear", "sundress", "sheath_dress", "sundress_scarf") and not female:
        raise ValueError(f"{name} is built on the female mannequin; choose another outfit")
    if name == "bikini":
        return w.bikini(scene, marks) if female else w.swim_trunks(scene, marks)
    if name == "swim_trunks":
        return w.swim_trunks(scene, marks)
    if name == "innerwear":
        return w.innerwear(scene, marks, sitter.skin)
    if name == "crop_top":
        return w.crop_top(scene, marks) + w.hot_pants(scene, marks) + w.shoes(scene, marks, pose, body, "sneaker")
    if name == "tee_jeans":
        return w.tee(scene, marks, body) + w.jeans(scene, marks) + w.shoes(scene, marks, pose, body, "sneaker")
    if name == "suit":
        if female:
            return (w.suit(scene, marks, body, colour=("#D8C6B0", "#9C8A86"), tie=None, lapel="#E4D5C2")
                    + w.shoes(scene, marks, pose, body, "flat"))
        return w.suit(scene, marks, body) + w.shoes(scene, marks, pose, body, "oxford")
    if name == "hoodie":
        if female:                                 # oversized, worn as a dress, bare legs
            return w.hoodie(scene, marks, body, colour=("#C8B8E6", "#8E7FB2"), long=True)
        return w.hoodie(scene, marks, body) + w.jeans(scene, marks) + w.shoes(scene, marks, pose, body, "sneaker")
    if name == "flared_skirt":
        return (w.crop_top(scene, marks) + d.flared_skirt(scene, marks, wind=wind)
                + w.shoes(scene, marks, pose, body, "sneaker"))
    if name == "pleated_skirt":
        return (w.tee(scene, marks, body, colour=("#F4F1EC", "#B9B6C8"))
                + d.pleated_skirt(scene, marks, wind=wind, ease=TUCKED_EASE)
                + w.shoes(scene, marks, pose, body, "flat"))
    if name == "pencil_skirt":
        return (w.shirt(scene, marks, colour=("#F6F1EA", "#C2B8C8"), sleeves=1.9, physique=body)
                + d.pencil_skirt(scene, marks)
                + w.shoes(scene, marks, pose, body, "flat"))
    if name == "sundress":
        return d.sundress(scene, marks, wind=wind)
    if name == "sundress_scarf":
        return d.sundress(scene, marks, wind=wind) + d.scarf(scene, marks, wind=wind)
    if name == "sheath_dress":
        return d.sheath_dress(scene, marks) + w.shoes(scene, marks, pose, body, "flat")
    if name == "dark_hoodie":                      # black hoodie, dark jeans, dark sneakers
        return (w.hoodie(scene, marks, body, colour=DARK_HOODIE, strings=DARK_STRINGS)
                + w.jeans(scene, marks, colour=DARK_JEANS) + w.shoes(scene, marks, pose, body, "dark_sneaker"))
    raise ValueError(f"unknown outfit {name!r}; choose from {OUTFITS}")


OUTFITS = ("bikini", "swim_trunks", "innerwear", "crop_top", "tee_jeans", "suit", "hoodie", "flared_skirt",
           "pleated_skirt", "pencil_skirt", "sundress", "sundress_scarf", "sheath_dress", "dark_hoodie")

LOOKS = {
    "beach_bikini": Look("f", "bikini", "hand_on_hip", "beach", azimuth=25),
    "beach_trunks": Look("m", "swim_trunks", "standing", "beach", azimuth=-20),
    "bedroom_innerwear": Look("f", "innerwear", "reclining", "bedroom", azimuth=8, elevation=12, aspect=0.72,
                             margin=0.12),
    "bedroom_hoodie": Look("f", "hoodie", "standing", "bedroom", shot="knee", azimuth=-25),
    "office_suit_f": Look("f", "suit", "seated_chair", "office", azimuth=30),
    "office_suit_m": Look("m", "suit", "arms_crossed", "office", shot="knee", azimuth=-25),
    "night_crop_top": Look("f", "crop_top", "leaning_wall", "night_street", azimuth=25),
    "night_hoodie": Look("m", "hoodie", "walking", "night_street", azimuth=35),
    "dusk_jeans": Look("f", "tee_jeans", "walking", "dusk", azimuth=30),
    "beach_sundress": Look("f", "sundress", "standing", "beach", azimuth=20, wind=BREEZE),
    "night_pleated": Look("f", "pleated_skirt", "walking", "night_street", azimuth=30),
    "office_sheath": Look("f", "sheath_dress", "seated_chair", "office", azimuth=25),
    "dusk_scarf": Look("f", "sundress_scarf", "hand_on_hip", "dusk", shot="knee", azimuth=15,
                       wind=(0.55, -0.10, 0.10)),
    "cafe_crossed": Look("f", "sundress", "seated_crossed", "cafe", azimuth=25),
    "park_wave": Look("f", "crop_top", "waving", "park", azimuth=10, elevation=-4),
}

DUOS = {
    "beach_couple": Duo(("f", "bikini"), ("m", "swim_trunks"), "side_by_side", "beach", azimuth=10),
    "night_date": Duo(("f", "flared_skirt"), ("m", "hoodie"), "holding_hands", "night_street", azimuth=8),
    "office_talk": Duo(("f", "pencil_skirt"), ("m", "suit"), "facing", "office", shot="knee"),
}


def _props(place, supports, toward=1.0):
    supports = tuple((role, shape) for role, shape in supports if role != "ground")   # the place has one
    props = (ground_prop(place, toward),) + tuple(
        (role, shape, *place.roles.get(role, FALLBACK_SUPPORT)) for role, shape in supports)
    return props + (place.furnish(supports) if place.furnish else ())


def _sitter(sex):
    return WOMAN if sex == "f" else MAN


def _actor(sex, outfit, staging, wind, face=None):
    """A posed, dressed person: the pose resolved (hands on landmarks) for the body,
    the painted head in its look."""
    sitter = replace(_sitter(sex), look=face)
    pose = figure_study.resolve(figure_study.Setting(1.0, None, staging.pose, hand_at=staging.hand_at,
                                     hand_behind_head=staging.hand_behind_head), sitter.physique)
    extras = lambda scene, marks: dress_outfit(outfit, scene, marks, sitter, pose, wind)   # noqa: E731
    return figure_study.Actor(sitter, pose, extras)


def cast_for(look):
    """Setting and cast for a look or a duo."""
    place = PLACES[look.place]
    if isinstance(look, Duo):
        stagings = pair_for(look.pair, _sitter(look.first[0]).physique, _sitter(look.second[0]).physique,
                            WOMAN_BUST if look.first[0] == "f" else 1.0, WOMAN_BUST if look.second[0] == "f" else 1.0)
        people = [look.first, look.second]
        faces = list(look.faces)
    else:
        stagings = [pose_for(look.pose, _sitter(look.sex).physique, WOMAN_BUST if look.sex == "f" else 1.0)]
        people = [(look.sex, look.outfit)]
        faces = [look.face]
    cast = [_actor(sex, outfit, staging, look.wind, face)
            for (sex, outfit), staging, face in zip(people, stagings, faces)]
    supports = tuple(support for staging in stagings for support in staging.supports)
    marks = [build(Scene(), actor.pose, physique=actor.sitter.physique) for actor in cast]
    camera = frame(marks, [actor.sitter.physique for actor in cast], look.shot, look.azimuth, look.elevation,
                   aspect=look.aspect, margin=look.margin)
    setting = figure_study.Setting(aspect=look.aspect, camera=camera, pose=cast[0].pose, props=_props(place, supports, looking_back(camera)),
                           room=place.backdrop, painters=place.painters)
    return setting, cast


def draw(style_name, width_px, look="beach_bikini"):
    if isinstance(look, str):
        look = LOOKS[look] if look in LOOKS else DUOS[look]
    setting, cast = cast_for(look)
    return figure_study.draw_cast(style_name, width_px, setting, cast)


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    choice = sys.argv[4] if len(sys.argv) > 4 else "beach_bikini"
    if choice == "custom":
        sex, outfit, pose_name, place_name = sys.argv[5:9]
        shot = sys.argv[9] if len(sys.argv) > 9 else "full"
        azimuth = float(sys.argv[10]) if len(sys.argv) > 10 else 20.0
        choice = Look(sex, outfit, pose_name, place_name, shot, azimuth)
    draw(style_name, width, choice).save(output)
    print(f"saved {output}")
