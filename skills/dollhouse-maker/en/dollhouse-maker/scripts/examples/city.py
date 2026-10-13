"""City street in one-point perspective: sunny day, rainy dusk, and an oil version at golden hour.

Run:  python city.py [out_dir]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import save, finish, get_style
from codepaint.subjects.city import build_city, CitySpec


def anime(spec):
    return finish(build_city(spec), "anime")


def oil(spec):
    # architecture needs finer brushwork than open landscape to keep the window grid readable
    return finish(build_city(spec), get_style("painterly", painterly=dict(scale=0.6)), seed=2)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    print("saved", save(anime(CitySpec(seed=2, time="day")), out / "city_day.png"))
    print("saved", save(anime(CitySpec(seed=2, time="dusk", wet_road=0.55)), out / "city_dusk.png"))
    print("saved", save(oil(CitySpec(seed=5, time="golden")), out / "city_painterly.png"))
