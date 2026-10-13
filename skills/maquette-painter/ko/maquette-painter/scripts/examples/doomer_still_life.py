"""Doomer still life: a kitchen table by the window late at night.

On the table: tea in a faceted glass set in a metal holder with a spoon left in it, a pressed-glass ashtray with a
cigarette burning on its rim, a box of matches and a cassette tape. Through the double window, across the snowy
yard, the next block has a few windows still lit. A warm lamp from the left lights the table; the night outside
stays blue.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Gradient, city, geom, light as make_light, objects as ob, props, scenery as sc, studio

brief = Brief.from_answers(subject="still_life", style="doomer", format="landscape", composition="thirds_left",
                           lighting="night", background="interior", mood="melancholic", palette="doomer",
                           message="늦은 밤 창가 부엌 식탁 위의 차와 담배", seed=149)
SKY = "#1c2234"
FRAME = "#d8d2c4"            # window frames painted over many times
HOLDER = [(0.36, 0.0), (0.38, 0.06), (0.34, 0.12), (0.35, 0.6), (0.38, 1.0)]      # glass holder, base to rim
ASHTRAY = [(0.40, 0.0), (0.48, 0.5), (0.5, 1.0)]


def outside(canvas, window):
    """The view through the glass: the snowy yard from the fifth floor and the next block across it."""
    x0, y0, x1, y1 = window
    camera = sc.Perspective(canvas, y0 + (y1 - y0) * 0.35, eye=14.0, focal=0.6, centre_x=(x0 + x1) / 2)
    sc.sky(canvas, "#070912", SKY, camera.horizon_y)
    with canvas.layer(depth=0.97):
        canvas.add(camera.ground_quad(-300, 300, 5, 600), "#4a5266", "snow", normal=(0, -1, 0.05))
    night = make_light("night", azimuth=-30, elevation=40, color="#8a98c0", shadow_tint="#2c3448")
    city.building(camera, -90, 120, 180, 12, 9 * city.PANEL_STOREY + 0.8, "#6a6864", kind="panel", light=night, night=True,
                  sky=SKY, seed=3)
    city.lamp(camera, 12, 50, height=7, night=True, glow="#ffb468")
    sc.weather(canvas, "snow", near=0.2, amount=0.7, wind=0.1, seed=7)


def window_frame(canvas, window, bar):
    """A Soviet double window: a heavy outer frame, a mullion, a transom and the little vent pane up in one corner."""
    x0, y0, x1, y1 = window
    mid, transom = (x0 + x1) / 2, y0 + (y1 - y0) * 0.3
    outer = geom.subtract(geom.rect(x0 - bar, y0 - bar, x1 + bar, y1 + bar), geom.rect(x0, y0, x1, y1))
    with canvas.layer(depth=0.5):
        canvas.add(outer, FRAME, "frame", normal=(0, 0, 1), outline=1.0)
        canvas.add(geom.rect(mid - bar * 0.6, y0, mid + bar * 0.6, y1), FRAME, "frame", normal=(0, 0, 1), outline=1.0)
        canvas.add(geom.rect(x0, transom - bar * 0.5, x1, transom + bar * 0.5), FRAME, "frame", normal=(0, 0, 1), outline=1.0)
        vent = geom.subtract(geom.rect(x0 + bar * 0.5, y0 + bar * 0.5, mid - bar * 1.2, transom - bar * 0.9),
                             geom.rect(x0 + bar * 1.3, y0 + bar * 1.3, mid - bar * 2.0, transom - bar * 1.7))
        canvas.add(vent, FRAME, "frame", normal=(0, 0, 1), outline=1.0)


def tea_glass(canvas, x, base_y, width, height):
    """Tea in a faceted glass standing in a metal holder with a handle, a spoon leaning in it."""
    ob.revolve(canvas, x, base_y - height * 0.02, width * 0.86, height, "#8a9498", profile="glass", gloss=0.8,
               inside="#2a2e30", outline=(0.8, "#4a5054"))
    ob.revolve(canvas, x, base_y - height * 0.03, width * 0.8, height * 0.86, "#6a300e", profile="glass", gloss=0.5,
               inside="#3a1806", cast=False)
    for k in range(-2, 3):                                   # facets: pale vertical glints between holder and rim
        fx = x + k * width * 0.07
        canvas.stroke([(fx, base_y - height * 0.5), (fx * 1.0 + k * width * 0.012, base_y - height * 0.97)], width * 0.012,
                      "#e8e0d0", start=0.4, end=0.4, alpha=0.35)
    spoon = geom.taper([(x + width * 0.05, base_y - height * 0.8), (x + width * 0.28, base_y - height * 1.28)], width * 0.06,
                       start=0.6, end=1.0)
    canvas.add(spoon, "#d8d4cc", "spoon", form="round", gloss=0.8, outline=0.8)
    canvas.add(geom.ellipse(x + width * 0.3, base_y - height * 1.3, width * 0.06, width * 0.03, -30), "#c8c4bc", "spoon",
               gloss=0.8, outline=0.8)
    ob.revolve(canvas, x, base_y, width, height * 0.5, "#a8a296", profile=HOLDER, gloss=0.85, opening=False, cast=False,
               outline=(1.0, "#4a463e"))
    for level in (0.18, 0.4):                                # engraved bands round the holder
        band = [(x + width * 0.36 * c, base_y - height * level + width * 0.36 * ob.VIEW_TILT * (1 - c * c) ** 0.5)
                for c in (-0.95, -0.5, 0.0, 0.5, 0.95)]
        canvas.stroke(band, width * 0.015, "#4a463e", start=0.3, end=0.3, alpha=0.6)
    handle = geom.subtract(geom.ellipse(x + width * 0.44, base_y - height * 0.28, width * 0.15, height * 0.16),
                           geom.ellipse(x + width * 0.44, base_y - height * 0.28, width * 0.09, height * 0.1))
    canvas.add(handle, "#a8a296", "holder", form="round", gloss=0.85, outline=(1.0, "#4a463e"))


def ashtray(canvas, x, base_y, width, seed):
    """A pressed-glass ashtray with two stubs in it and a cigarette burning on the rim; its smoke climbs to the left."""
    height = width * 0.22
    ob.revolve(canvas, x, base_y, width, height, "#7a8890", profile=ASHTRAY, gloss=0.7, inside="#3a3c40")
    for dx, length in ((-0.12, 0.16), (0.08, 0.12)):
        stub = (x + width * dx, base_y - height * 0.95)
        props.cigarette(canvas, stub, (stub[0] + width * length, stub[1] + width * 0.02), width * 0.05, lit=False)
    rest = (x + width * 0.36, base_y - height * 1.02)
    tip = props.cigarette(canvas, rest, (rest[0] + width * 0.58, rest[1] + width * 0.07), width * 0.06)
    props.smoke(canvas, tip[0], tip[1], width * 3.4, width=width * 1.1, drift=-0.12, alpha=0.4, strands=5, seed=seed)


def build(canvas, light, brief):
    light = make_light("night", azimuth=-58, elevation=36, color="#ffc890", shadow_tint="#2a2c3a", wrap=0.3, haze_strength=0.0)
    ob.use_light(light)
    W, H, seed = canvas.width, canvas.height, brief.seed
    table_y = H * 0.62
    window = (W * 0.22, H * 0.07, W * 0.8, table_y - H * 0.07)
    outside(canvas, window)
    wall = geom.subtract(geom.rect(0, 0, W, table_y), geom.rect(*window))
    with canvas.layer(depth=0.6):
        canvas.add(wall, Gradient.radial((W * 0.08, H * 0.2), W * 0.8, ["#6a5848", "#3a3230", "#26222a"]), "wall", unlit=True)
    window_frame(canvas, window, W * 0.012)
    with canvas.layer(depth=0.55):                          # the sill under the window, just behind the table
        canvas.add(geom.rect(window[0] - W * 0.03, table_y - H * 0.06, window[2] + W * 0.03, table_y), FRAME, "sill",
                   normal=(0, -0.3, 0.95), outline=1.0)
    ob.table(canvas, table_y, "#5a4636", edge=H * 0.04, seed=seed)
    with canvas.layer(depth=0.4, group="objects"):
        tea_glass(canvas, W * 0.3, H * 0.86, W * 0.085, W * 0.12)
        ob.book(canvas, W * 0.42, H * 0.93, W * 0.05, H * 0.014, W * 0.035, cover="#c8a860", pages="#e8dcc0")
        ashtray(canvas, W * 0.55, H * 0.84, W * 0.13, seed)
        props.cassette(canvas, W * 0.66, H * 0.97, W * 0.17, yaw=18)
    return {"light": light}


if __name__ == "__main__":
    studio.run(build, brief, "doomer_still_life.png")
