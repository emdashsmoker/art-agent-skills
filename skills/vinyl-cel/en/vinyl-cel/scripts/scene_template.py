#!/usr/bin/env python3
"""Scene template: a young woman in a summer breeze.

Copy this file, edit the SCENE section, then run for example:

    export CODEILLUST_HOME=<skill folder>/scripts             # needed once the file is copied
    python my_scene.py --style all --preview --out out/
    python my_scene.py --style anime --out out/               # delivery size

A scene is data (the character) plus one compose() function that draws
back to front: background, character, then any extra props.
"""
import os
import sys
from pathlib import Path

# A copied scene script finds the toolkit through CODEILLUST_HOME (the skill's scripts folder).
TOOLKIT_DIR = Path(os.environ.get("CODEILLUST_HOME", Path(__file__).resolve().parent))
if not (TOOLKIT_DIR / "codeillust").is_dir():
    sys.exit("codeillust package not found. Set CODEILLUST_HOME to the skill's scripts folder.")
sys.path.insert(0, str(TOOLKIT_DIR))

from codeillust import background, studio  # noqa: E402
from codeillust.character import default_character  # noqa: E402
from codeillust.config import StyleName  # noqa: E402
from codeillust.figure import draw_character  # noqa: E402

# ---- SCENE ------------------------------------------------------------------
SCENE_NAME = "summer_portrait"
CHARACTER = default_character()
# Cumulus placement: (base centre, width, height, puff count) in canvas units (1000 x 1333).
CLOUDS = [((800.0, 1230.0), 760.0, 760.0, 80), ((110.0, 1260.0), 420.0, 260.0, 30),
          ((900.0, 300.0), 260.0, 70.0, 14)]
SUN_CENTER = (60.0, 40.0)
SUN_RADIUS = 520.0


def compose(painter):
    """Each style gets the backdrop that suits its surface."""
    canvas = painter.canvas
    style_name = painter.style.name
    if style_name is StyleName.ANIME:
        background.summer_sky(canvas, CLOUDS, painter.light)
        background.sun_glow(canvas, SUN_CENTER, SUN_RADIUS)
    elif style_name is StyleName.ILLUST:
        background.flat_graphic(canvas)
    elif style_name is StyleName.PAINTERLY:
        background.studio_backdrop(canvas)
    else:
        raise ValueError(f"no backdrop chosen for style: {style_name}")
    draw_character(painter, CHARACTER)
# ---- END SCENE ----------------------------------------------------------------


if __name__ == "__main__":
    studio.run_cli(SCENE_NAME, compose, description=__doc__)
