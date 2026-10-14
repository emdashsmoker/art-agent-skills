"""Check that the drawing engine can run here. Usage: python check_env.py [--full]

Prints the versions found and renders one tiny picture end to end. Exit code 0 means ready.
--full also renders a small figure-and-landscape scene in every style preset (about a minute).
"""
import importlib
import sys
from pathlib import Path

REQUIRED = {"numpy": "numpy", "cv2": "opencv-python-headless", "scipy": "scipy", "skia": "skia-python"}


def main():
    missing = []
    for module, package in REQUIRED.items():
        try:
            found = importlib.import_module(module)
            print(f"ok       {module:6s} {getattr(found, '__version__', '')}")
        except Exception as error:                      # ImportError, or a missing system library behind the wheel
            print(f"MISSING  {module:6s} ({type(error).__name__}: {error})")
            missing.append(package)
    if missing:
        print("\ninstall with:  pip install " + " ".join(missing))
        print("if skia fails to load on Linux, the system libraries libEGL / libGL / fontconfig are usually what is absent")
        return 1
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from atelier import Canvas, Light, geom, render
    canvas = Canvas(160, 120)
    canvas.add(geom.ellipse(80, 60, 40), "#c8553d", "ball", form="round", outline=2)
    image = render(canvas, "cel", Light())
    assert image.shape == (120, 160, 3) and 0.1 < float(image.mean()) < 1.0, "test render looks wrong"
    print("render   ok", image.shape)
    if "--full" in sys.argv:
        return full_check()
    return 0


def full_check():
    """Every style preset on one small scene: catches a broken medium or finish pass after an install or an edit."""
    from atelier import STYLES, Brief, compose, paint, qa, save, scenery
    failures, images = [], []
    for name in STYLES:
        try:
            brief = Brief.from_answers(style=name, seed=1)
            canvas = type(brief.canvas())(480, 600, scale=0.6, seed=1)
            light = brief.light()
            scenery.sky(canvas, horizon_y=380)
            scenery.hills(canvas, 400, 60, seed=2)
            with canvas.layer(depth=0.3, group="figure"):
                brief.character().draw(canvas, light=light, **compose.framing(canvas, "bust"))
            images.append(paint(canvas, name, light))
            print(f"style    ok {name}")
        except Exception as error:
            failures.append(name)
            print(f"style    FAILED {name}: {type(error).__name__}: {error}")
    if images:
        save(qa.sheet(images, [n for n in STYLES if n not in failures], columns=8, cell_width=220), "check_env_styles.png")
        print("sheet    check_env_styles.png")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
