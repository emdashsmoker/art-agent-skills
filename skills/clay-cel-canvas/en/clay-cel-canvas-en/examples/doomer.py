"""Worked example: seven pictures in one doomer mood: cold, faded, late at night.

Usage: python doomer.py <anime|illust|painterly> <output.png> [width_px] [picture]
  picture: man, woman, pair, establishing, city, landscape, still_life (default man)

The mood is a grade laid over the finished picture (atelier.mood.doomer): colour
drained, darks leaning cold, blacks faded, corners sunk, film grain. Any picture
takes it with `art.grade = doomer`.
- man, woman, pair, establishing: outfits.py figures in the dark_hoodie outfit, in the
  panel_yard and rooftop places, wearing head props (beanie, cigarette, earphones);
  establishing is the world seen wide, a small figure from behind on a roof.
- city, landscape, still_life: painted in 2-D with the prefab blocks of scenes.py.
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import nude  # noqa: E402
import doomer_city  # noqa: E402
import doomer_landscape  # noqa: E402
import doomer_still_life  # noqa: E402
import outfits  # noqa: E402
from atelier import Camera  # noqa: E402
from atelier.mood import doomer  # noqa: E402
from head_style import HeadLook  # noqa: E402
from outfits import Duo, Look  # noqa: E402

# ---- figures ------------------------------------------------------------------------
SMOKER = HeadLook(hat="beanie", cigarette="lit", earrings="earphones")
FIGURES = {
    "man": Look("m", "dark_hoodie", "walking", "panel_yard", azimuth=25, face=SMOKER),
    "woman": Look("f", "dark_hoodie", "seated_crossed", "panel_yard", azimuth=25,
                  face=HeadLook(hair_colour="black", eyes="soft", hat="beanie", cigarette="lit",
                                earrings="earphones")),
    "pair": Duo(("f", "dark_hoodie"), ("m", "dark_hoodie"), "side_by_side", "rooftop", shot="knee", azimuth=8,
                faces=(HeadLook(hair="bob", hair_colour="dark_brown", cigarette="lit", earrings="none"),
                       HeadLook(hat="beanie", cigarette="lit"))),
    "establishing": Look("m", "dark_hoodie", "standing", "rooftop", azimuth=180, elevation=20, aspect=0.66,
                         margin=0.36, face=HeadLook(hat="beanie", cigarette="lit")),
}


# Canvas units to slide a picture's content: the establishing shot puts its small figure
# on the right third and drops the empty roof below the frame.
FRAME_SHIFT = {"establishing": (170.0, 150.0)}


def shifted(camera, dx, dy):
    """The same camera with its picture slid by (dx, dy): a crop of a wider view."""
    return Camera(camera.eye, camera.eye + camera.forward, camera.focal, camera.center + (dx, dy))


def draw_figure(style_name, width_px, name):
    setting, cast = outfits.cast_for(FIGURES[name])
    if name in FRAME_SHIFT:
        setting = replace(setting, camera=shifted(setting.camera, *FRAME_SHIFT[name]))
    return nude.draw_cast(style_name, width_px, setting, cast)


PICTURES = {**{name: (lambda style, width, name=name: draw_figure(style, width, name)) for name in FIGURES},
            "city": doomer_city.draw, "landscape": doomer_landscape.draw, "still_life": doomer_still_life.draw}


def draw(style_name, width_px, picture="man"):
    if picture not in PICTURES:
        raise ValueError(f"unknown picture {picture!r}; choose from {sorted(PICTURES)}")
    art = PICTURES[picture](style_name, width_px)
    art.grade = doomer
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    choice = sys.argv[4] if len(sys.argv) > 4 else "man"
    draw(style_name, width, choice).save(output)
    print(f"saved {output}")
