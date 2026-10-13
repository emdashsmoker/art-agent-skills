"""Mountain lake in two finishes: an oil painting and a crisp anime background.

Run:  python landscape.py [out_dir]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import save, finish
from codepaint.subjects.landscape import build_landscape, LandscapeSpec

SPEC = LandscapeSpec(width=1280, height=896, seed=3)
SUNSET = LandscapeSpec(width=1280, height=896, seed=8, horizon=0.60, sun=(0.30, 0.50), sun_color="#ffd9a0",
                       sky=[(0.0, "#2b3a78"), (0.45, "#a0629a"), (0.85, "#f59a5a"), (1.0, "#ffd48a")],
                       haze="#f2b48c", far="#7a6a9c", near="#2a2440", grass_color="#4a5a3a", cloud_cover=0.5)


def oil(spec):
    """Reference picture -> brush strokes -> varnish, weave, vignette."""
    return finish(build_landscape(spec), "painterly", seed=1)


def anime(spec):
    """Reference picture kept crisp, finished with glow and grading only."""
    return finish(build_landscape(spec), "anime")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    print("saved", save(oil(SPEC), out / "landscape_painterly.png"))
    print("saved", save(anime(SUNSET), out / "landscape_anime.png"))
