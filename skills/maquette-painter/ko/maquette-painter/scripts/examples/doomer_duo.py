"""Doomer two-shot: two friends seen from behind on a bench at the top of a hill, looking down on the suburb at night.

The camera stands behind the bench, so the pair are dark backs against the town: rows of prefabricated blocks with
their windows lit, sodium lamps along the streets, a striped boiler-house chimney with red warning lights and
power lines sweeping across the sky from one tower. The town's glow lights them from in front and rims their
outlines; his cigarette smoke climbs past his cap.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from atelier import Brief, Figure, Gradient, Hair, city, geom, light as make_light, props, scenery as sc, studio, wardrobe as w

brief = Brief.from_answers(subject="scene", style="doomer", format="landscape", framing="half", composition="thirds_left",
                           view="back", pose="sit", lighting="backlit", background="city", mood="melancholic",
                           palette="doomer", message="언덕 위 벤치에서 밤의 변두리를 내려다보는 두 사람", seed=127)
HILL = 23.0                  # the hill top stands this many metres above the town
SODIUM = "#ffb468"
SKY = "#1e2638"
WALLS = ["#6e6c68", "#76726a", "#686a6c", "#7a766e"]


def town(camera, light, seed):
    """Blocks on a loose grid below the hill, far to near so nearer ones overlap; sodium lamps along two roads."""
    rng = np.random.default_rng(seed)
    for z in np.arange(640, 180, -46):
        for x in np.arange(-0.6 * z, 0.6 * z, 52):
            if rng.random() < 0.35:
                continue
            long_block = rng.random() < 0.6
            width = rng.uniform(50, 90) if long_block else rng.uniform(16, 22)
            storeys = int(rng.choice([5, 9, 9, 12])) if long_block else int(rng.choice([12, 16, 16]))
            city.building(camera, x + rng.uniform(-8, 8), z + rng.uniform(-6, 6), width, 12, storeys * city.PANEL_STOREY + 0.8,
                          WALLS[int(rng.integers(len(WALLS)))], kind="panel", light=light, night=True, sky=SKY,
                          seed=int(rng.integers(1 << 30)), roof=False)
    for z in (230.0, 330.0, 470.0, 640.0):            # streets crossing the view, a lamp every 30 m along each
        for x in np.arange(-0.7 * z, 0.7 * z, 30):
            px, py = camera.point(x, 8.0, z)
            s = camera.scale(z, x)
            camera.canvas.accent(geom.ellipse(px, py, 0.6 * s, 0.6 * s), "#ffe0b0", alpha=0.9)
            camera.canvas.accent(geom.ellipse(px, py, 4.0 * s, 3.0 * s), SODIUM, alpha=0.3, blur=2.5 * s)


def bench(camera, x0, x1, z, seat=0.45, color="#5a4a40", part="seat"):
    """A park bench seen from behind: 'seat' draws the legs and seat, 'back' the slatted back rest nearest the camera."""
    y = HILL
    if part == "seat":
        for x in (x0 + 0.15, x1 - 0.25):
            camera.box(x, z, 0.1, 0.4, seat, "#3a3634", y=y, region="bench")
        camera.box(x0, z, x1 - x0, 0.42, 0.05, color, y=y + seat - 0.05, region="bench", outline=1.0)
        return
    for x in (x0 + 0.15, x1 - 0.25):                    # the iron frame behind the slats
        camera.box(x, z - 0.07, 0.07, 0.05, 0.82, "#3a3634", y=y, region="bench")
    for low in (0.5, 0.62, 0.74):                       # three slats with gaps the coats show through
        camera.box(x0, z - 0.06, x1 - x0, 0.05, 0.1, color, y=y + low, region="bench", outline=1.0)


def trodden(camera, seed):
    """Footprints trodden through the snow up to the bench, and dry stalks along the brow."""
    canvas = camera.canvas
    rng = np.random.default_rng(seed)
    with canvas.layer(depth=0.55):
        for k in range(14):
            z = 1.2 + k * 0.18
            px, py = camera.point(-0.4 + (0.12 if k % 2 else -0.12) - 0.25 * np.sin(z), HILL, z)
            s = camera.scale(z)
            canvas.add(geom.ellipse(px, py, 0.06 * s, 0.03 * s), "#1c2029", "path", unlit=True, alpha=0.7)
        for _ in range(60):                         # dry grass standing out of the snow on the brow
            x, z = rng.uniform(-14, 14), rng.uniform(11.5, 13)
            px, py = camera.point(x, HILL, z)
            s = camera.scale(z, x)
            tip = (px + rng.uniform(-0.2, 0.2) * s, py - rng.uniform(0.3, 0.8) * s)
            canvas.add(geom.taper([(px, py), tip], max(0.02 * s, 0.8), start=1.0, end=0.2), "#1a1c22", "grass")


def build(canvas, light, brief):
    light = make_light("backlit", azimuth=172, elevation=12, color="#e0a070", shadow_tint="#2a3044", haze=SKY,
                       haze_strength=0.55, rim=0.9)
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon = H * 0.34
    sc.sky(canvas, "#070a14", "#5a4a50", horizon, glow=(W * 0.62, horizon, W * 0.7), glow_color="#8a6048")
    camera = sc.Perspective(canvas, horizon, eye=HILL + 1.15, focal=1.0)
    with canvas.layer(depth=0.98):
        canvas.add(camera.ground_quad(-1200, 1200, 150, 2000), "#262a36", "ground", normal=(0, -1, 0.05))
    top, s = city.chimney(camera, -190, 620, 120, 4.5)
    props.smoke(canvas, top[0], top[1], 70 * s, width=40 * s, drift=0.9, color="#8a8a96", alpha=0.3, strands=7, seed=seed)
    town(camera, light, seed)
    towers = [city.pylon(camera, x, z, height=46, yaw=-8) for x, z in ((-150, 170), (40, 150), (230, 130))]
    for k in range(len(towers[0])):                  # one tower stands in view; its lines sweep across the town
        city.wires(camera, [t[k] for t in towers], sag=7, width=1.6, color="#16181e", painted=True)
    with canvas.layer(depth=0.6):                    # the snowy hill top, its far edge cutting off the foot of the town
        # Snow at night takes its light from the glow over the town: brightest at the brow, dim at our feet.
        brow, feet = camera.point(0, HILL, 13), (0, H)
        canvas.add(camera.ground_quad(-40, 40, 1, 13, y=HILL), Gradient.linear(brow, feet, ["#6c6c7a", "#3a4050", "#2a2f3c"]),
                   "snow", unlit=True)
    for k, (x, z, height) in enumerate(((-7.5, 11.5, 7.0), (-5.6, 12.4, 5.0), (6.2, 12.0, 6.5))):
        px, py = camera.point(x, HILL, z)              # birches on the brow of the hill frame the view
        sc.bare_tree(canvas, px, py, height * camera.scale(z, x), birch=True, seed=seed + k, spread=0.4, depth=0.5)
    trodden(camera, seed)
    sc.weather(canvas, "snow", near=0.25, amount=0.6, wind=0.2, seed=seed)

    seat_z, x0, x1 = 3.7, -1.35, 0.3
    bench(camera, x0, x1, seat_z)
    views = []
    people = [   # (x on the bench, sex, hair, outfit, head pose)
        (-1.05, "female", Hair("bob", "straight", "#141216", seed=seed, gloss=0.2),
         [w.turtleneck("#18181c"), w.pants("#202024"), w.coat("#34322f", hem=2.4), w.shoes("#141416")], (2, -6, -9)),
        (-0.3, "male", Hair("beanie", "none", "#2a2a30", seed=seed),
         [w.hoodie("#1d1e23"), w.pants("#26272c"), w.shoes("#1c1c20")], (6, 4, 0)),
    ]
    for x, sex, hair, outfit, head in people:
        foot_x, foot_y = camera.point(x, HILL, seat_z + 0.45)
        figure = Figure(sex=sex, pose="sit", turn=180, heads=7.6 if sex == "female" else 7.8)
        figure.set_pose(head=head)
        character = brief.character(figure, hair=hair, outfit=outfit, expression="tired")
        with canvas.layer(depth=0.3, group="figure"):
            views.append(character.draw(canvas, foot_x, ground_y=foot_y, height=1.66 * camera.scale(seat_z), light=light))
    head, unit = views[1].joint("head"), views[1].unit
    props.smoke(canvas, head[0] + unit * 0.55, head[1] + unit * 0.2, unit * 2.2, drift=0.25, alpha=0.35, seed=seed + 2)
    with canvas.layer(depth=0.2):
        bench(camera, x0, x1, seat_z, part="back")
    sc.weather(canvas, "snow", near=0.8, amount=0.3, wind=0.2, seed=seed + 1)
    return {"views": views, "light": light}


if __name__ == "__main__":
    studio.run(build, brief, "doomer_duo.png")
