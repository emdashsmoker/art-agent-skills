"""Example: bust portrait in any of the three styles, with its process sheet.

Usage: python examples/portrait.py --style anime|illust|painterly --out portrait.png
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, fx
from codepainter.figure import PortraitSpec, draw_portrait
from codepainter.styles import finish, flat_version, get_style

WIDTH, HEIGHT = 1024, 1280
WALL_LIGHT, WALL_DARK = "#6b9a97", "#2c4a52"
SUN = "#ffe9c4"


def paint_backdrop(painting, style):
    """Teal wall lit from the upper left, with a slanted patch of window light."""
    backdrop.gradient(painting, WALL_LIGHT, WALL_DARK, start=(0, 0), end=(WIDTH * 0.7, HEIGHT))
    backdrop.mottle(painting, "#3b6a70", amount=0.30, scale=1.2, seed=3)
    backdrop.glow(painting, (WIDTH * 0.12, HEIGHT * 0.10), HEIGHT * 0.75, SUN, opacity=0.30)
    softness = 0.0 if style.name == "anime" else HEIGHT * 0.006
    backdrop.window_light(painting, (WIDTH * 0.02, HEIGHT * 0.06), (WIDTH * 0.42, HEIGHT * 0.50),
                          slant=0.30, color=SUN, opacity=0.22, softness=softness)


def render(style_name, spec=None, seed=0, with_stages=True):
    style = get_style(style_name)
    spec = spec or PortraitSpec()
    painting = Painting(WIDTH, HEIGHT)
    paint_backdrop(painting, style)
    masks = draw_portrait(painting, spec, style)
    image = finish(painting, style, seed=seed, importance=masks["head"])
    if with_stages:
        # The flat stage is a second render with the light switched off.
        flats = Painting(WIDTH, HEIGHT)
        paint_backdrop(flats, style)
        draw_portrait(flats, spec, flat_version(style))
        if style.line_width > 0:
            painting.stages["1 line"] = painting.line_art()
        painting.stages["2 flat colour"] = flats.color
        painting.stages["3 light and shadow"] = painting.color.copy()
        painting.stages["4 finish"] = image
    return painting, image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="anime", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="portrait.png")
    parser.add_argument("--sheet", default=None, help="optional path for the process sheet")
    args = parser.parse_args()
    painting, image = render(args.style)
    painting.save(args.out, image)
    if args.sheet:
        fx.stage_sheet(painting.stages, args.sheet, columns=len(painting.stages))
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
