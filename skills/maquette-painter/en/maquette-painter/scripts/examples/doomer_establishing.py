"""Doomer establishing shot: a winter courtyard of a panel-block microdistrict seen from an upper floor, in black
and white like a photocopied record sleeve.

A long nine-storey slab closes the yard, a sixteen-storey tower stands at the left and another slab runs down the
right. In the snow between them: a playground with a swing frame, a slide and a climbing globe, footpaths trodden
across the yard, rubbish containers and a lamp post, cars parked along the access road, birches, two people walking. Beyond the roofs more blocks
fade into the haze, a line of pylons crosses the horizon and a boiler-house chimney sends its smoke sideways.
Crows cross the white sky.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from atelier import Brief, city, geom, light as make_light, props, scenery as sc, studio

brief = Brief.from_answers(subject="landscape", style="doomer_mono", format="landscape", composition="high_horizon",
                           lighting="overcast", background="city", mood="melancholic", palette="doomer",
                           message="a winter courtyard of the blocks seen from an upper-floor window", seed=131)
WALL = "#9a968e"
SKY = "#c8cacc"
EYE = 36.0                   # an upper floor of a tower across the yard


def playground(camera, x, z):
    """Swing frame, slide and climbing globe in welded steel tube."""
    bars = []
    for sx in (0.0, 3.2):                                    # swing: two A-frames and a top bar
        bars += [((x + sx, 0, z - 0.9), (x + sx, 2.4, z)), ((x + sx, 0, z + 0.9), (x + sx, 2.4, z))]
    bars.append(((x, 2.4, z), (x + 3.2, 2.4, z)))
    for sx in (0.8, 2.2):                                    # two seats on chains
        bars += [((x + sx - 0.2, 2.4, z), (x + sx - 0.2, 0.5, z)), ((x + sx + 0.2, 2.4, z), (x + sx + 0.2, 0.5, z)),
                 ((x + sx - 0.25, 0.5, z), (x + sx + 0.25, 0.5, z))]
    gx, gz, r = x + 7.5, z + 2.0, 1.4                       # climbing globe: meridians and parallels
    for a in np.linspace(0, np.pi, 6, endpoint=False):
        ring = [(gx + r * np.cos(t) * np.cos(a), r + r * np.sin(t), gz + r * np.cos(t) * np.sin(a))
                for t in np.linspace(-np.pi / 2, np.pi * 1.5, 17)]
        bars += list(zip(ring[:-1], ring[1:]))
    for h in (0.5, 1.0, 1.5, 2.1):
        rr = np.sqrt(max(r * r - (h - r) ** 2, 0.0))
        ring = [(gx + rr * np.cos(t), h, gz + rr * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 17)]
        bars += list(zip(ring[:-1], ring[1:]))
    sx, sz = x - 4.5, z + 3.0                                # slide: ladder up to a platform, chute down
    bars += [((sx, 0, sz), (sx, 2.0, sz)), ((sx + 0.6, 0, sz), (sx + 0.6, 2.0, sz))]
    bars += [((sx, h, sz), (sx + 0.6, h, sz)) for h in (0.4, 0.8, 1.2, 1.6, 2.0)]
    city.struts(camera, bars, "#2a2a2e", width=0.06, region="playground", depth=0.45)
    with camera.canvas.layer(depth=0.45):
        camera.canvas.add(camera.quad([(sx, 2.0, sz + 0.1), (sx + 0.6, 2.0, sz + 0.1), (sx + 0.6, 0.2, sz + 3.2),
                                       (sx, 0.2, sz + 3.2)]), "#5a5a5e", "playground", normal=(0, -0.5, 0.86))


def footpaths(camera, seed):
    """Paths trodden across the yard: dark wandering bands in the snow, the shortest way between doors."""
    rng = np.random.default_rng(seed)
    for (x0, z0), (x1, z1) in (((-40, 166), (34, 84)), ((-62, 112), (46, 150)), ((-14, 166), (-34, 70))):
        pts = []
        for t in np.linspace(0, 1, 14):
            x = x0 + (x1 - x0) * t + np.sin(t * 6 + rng.uniform(0, 3)) * 1.5
            z = z0 + (z1 - z0) * t
            pts.append(camera.point(x, 0.0, z))
        width = 0.9 * camera.scale((z0 + z1) / 2)
        with camera.canvas.layer(depth=0.6):
            camera.canvas.add(geom.taper(pts, width, start=1.0, end=1.0), "#a4a4aa", "path", normal=(0, -1, 0.05))


def crows(canvas, area, count, seed):
    """Crows in flight: small dark Ms, wings up or down."""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = area
    for _ in range(count):
        x, y, size = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(6, 13)
        up = rng.uniform(-0.5, 0.6)
        wing = [(x - size, y - size * up), (x - size * 0.4, y - size * 0.15), (x, y + size * 0.1),
                (x + size * 0.4, y - size * 0.15), (x + size, y - size * up)]
        canvas.add(geom.taper(wing, size * 0.28, start=0.1, end=0.1), "#1a1a1c", "bird")


def build(canvas, light, brief):
    light = make_light("overcast", azimuth=-35, elevation=50, haze=SKY, haze_strength=0.55)
    W, H, seed = canvas.width, canvas.height, brief.seed
    camera = sc.Perspective(canvas, H * 0.5, eye=EYE, focal=1.15, yaw=12, pitch=-8)
    horizon = camera.point(0, EYE, 4000)[1]
    sc.sky(canvas, "#b4b6ba", SKY, horizon + 2)
    with canvas.layer(depth=0.98):
        canvas.add(camera.ground_quad(-2000, 2000, 1, 4000), "#e4e4e6", "snow", normal=(0, -1, 0.05))
    towers = [city.pylon(camera, -300 + k * 120, 480, height=44) for k in range(7)]
    for k in range(len(towers[0])):
        city.wires(camera, [t[k] for t in towers], sag=5, width=0.9, color="#3a3a3e", painted=True)
    top, s = city.chimney(camera, 230, 540, 80, 4.0, lights=False)
    props.smoke(canvas, top[0], top[1], 22 * s, width=24 * s, drift=4.0, color="#8a8a90", alpha=0.5, strands=9, seed=seed)
    rng = np.random.default_rng(seed)
    for z in (440, 380, 320, 260):                           # the rest of the district behind the yard, far to near
        for x in np.arange(-300, 340, 75):
            if rng.random() < 0.3:
                continue
            tall = rng.random() < 0.3
            city.building(camera, x + rng.uniform(-10, 10), z, 20 if tall else rng.uniform(50, 70), 14 if tall else 12,
                          (16 if tall else 9) * city.PANEL_STOREY + 0.8, WALL, kind="panel", light=light, sky=SKY,
                          seed=int(rng.integers(1 << 30)), roof=False)
    city.building(camera, -80, 172, 150, 12, 9 * city.PANEL_STOREY + 0.8, WALL, kind="panel", light=light, sky=SKY, seed=1)
    for k, x in enumerate((2, 9, 16, 31)):             # cars along the access road in front of the slab
        city.car(camera, x, 166, ["#4a4a4e", "#8a8a8e", "#2e2e32", "#6a6a6e"][k], kind=["hatch", "sedan"][k % 2],
                 facing=1 if k % 2 else -1, sky=SKY, light=light)
    city.building(camera, 48, 70, 13, 92, 9 * city.PANEL_STOREY + 0.8, WALL, kind="panel", light=light, sky=SKY, seed=2)
    footpaths(camera, seed)
    for k, (x, z, height) in enumerate(((-24, 128, 13), (-40, 146, 15), (20, 140, 12), (30, 104, 14), (-14, 92, 11),
                                         (36, 150, 10))):
        px, py = camera.point(x, 0, z)
        sc.bare_tree(canvas, px, py, height * camera.scale(z, x), birch=k % 3 != 2, seed=seed + k, spread=0.45, depth=0.4)
    playground(camera, -2.0, 100.0)
    for k in range(3):                                       # rubbish containers by the path
        camera.box(-16 + k * 1.6, 90, 1.4, 1.0, 1.2, "#4a4a4e", region="bin", outline=0.8)
    city.lamp(camera, 9, 92, height=6.5)
    city.pedestrian(camera, -16, 126, color="#2a2a2e", seed=3)
    city.pedestrian(camera, 14, 104, color="#3a3a3e", seed=7)
    city.building(camera, -34, 138, 22, 22, 16 * city.PANEL_STOREY + 0.8, WALL, kind="panel", light=light, sky=SKY, seed=3)
    crows(canvas, (W * 0.25, H * 0.03, W * 0.7, H * 0.16), 6, seed)
    sc.weather(canvas, "snow", near=0.4, amount=0.4, wind=0.3, seed=seed)
    return {"light": light}


if __name__ == "__main__":
    studio.run(build, brief, "doomer_establishing.png")
