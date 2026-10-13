"""Doomer landscape: a snowfield at the edge of town under a low grey sky, in black and white.

A line of lattice pylons strides from the near left across the field toward the horizon, its wires sagging between
the towers with crows sitting on the nearest span. A rutted track winds off to a strip of bare birches; over the
trees at the left, far away, three panel blocks stand on the skyline. Tufts of dry grass poke through the snow.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from atelier import Brief, city, geom, light as make_light, scenery as sc, studio

brief = Brief.from_answers(subject="landscape", style="doomer_mono", format="landscape", composition="low_horizon",
                           lighting="overcast", background="landscape", mood="melancholic", palette="doomer",
                           message="송전탑이 지나가는 도시 끝자락의 눈 덮인 들판", seed=139)
SKY = "#c4c6c8"
PYLONS = [(-19.0, 46.0), (10.0, 124.0), (39.0, 202.0), (68.0, 280.0), (97.0, 358.0), (126.0, 436.0)]


def track(camera, seed):
    """Two wheel ruts winding away across the field, darker where the wheels pressed the snow down."""
    rng = np.random.default_rng(seed)
    bend = rng.uniform(0, np.pi)
    with camera.canvas.layer(depth=0.7):
        for offset in (-0.8, 0.8):
            pts, widths = [], []
            for z in np.geomspace(5.0, 330.0, 36):
                x = -1.5 - 16.0 * np.sin(z / 90.0 + bend) * (z / 330.0) + offset
                pts.append(camera.point(x, 0.0, z))
                widths.append(0.3 * camera.scale(z, x))
            camera.canvas.add(geom.ribbon(pts, widths), "#9a9ca2", "track", normal=(0, -1, 0.1))


def tufts(camera, count, seed):
    """Dry grass standing out of the snow in tufts of a few blades, larger as they come near."""
    canvas = camera.canvas
    rng = np.random.default_rng(seed)
    for _ in range(count):
        x, z = rng.uniform(-14, 14), rng.uniform(3.5, 16.0)
        px, py = camera.point(x, 0, z)
        s = camera.scale(z, x)
        for _ in range(int(rng.integers(3, 7))):
            lean = rng.uniform(-0.5, 0.5)
            height = rng.uniform(0.12, 0.35) * s
            tip = (px + lean * height, py - height)
            canvas.add(geom.taper([(px, py), ((px + tip[0]) / 2, (py + tip[1]) / 2 - height * 0.05), tip], max(0.01 * s, 0.7),
                                  start=1.0, end=0.1), "#3a3a3c", "grass")


def perched(canvas, points, count, seed):
    """Crows sitting on a wire: small hunched shapes along a line of canvas points."""
    rng = np.random.default_rng(seed)
    for t in rng.uniform(0.15, 0.85, count):
        k = int(t * (len(points) - 1))
        x, y = points[k]
        size = rng.uniform(5.0, 7.0)
        body = geom.ellipse(x, y - size * 0.7, size * 0.55, size * 0.8, rng.uniform(-15, 15))
        canvas.add(body, "#141416", "bird")
        canvas.add(geom.ellipse(x + size * 0.15, y - size * 1.55, size * 0.3), "#141416", "bird")
        canvas.add(geom.taper([(x, y - size * 0.2), (x - size * 0.2, y + size * 0.6)], size * 0.25), "#141416", "bird")


def crows(canvas, area, count, seed):
    """Crows in flight: small dark Ms, wings up or down."""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = area
    for _ in range(count):
        x, y, size = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(7, 14)
        up = rng.uniform(-0.5, 0.6)
        wing = [(x - size, y - size * up), (x - size * 0.4, y - size * 0.15), (x, y + size * 0.1),
                (x + size * 0.4, y - size * 0.15), (x + size, y - size * up)]
        canvas.add(geom.taper(wing, size * 0.28, start=0.1, end=0.1), "#1a1a1c", "bird")


def build(canvas, light, brief):
    light = make_light("overcast", azimuth=-30, elevation=45, haze=SKY, haze_strength=0.7)
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon = H * 0.58
    sc.sky(canvas, "#9a9ca2", SKY, horizon)
    camera = sc.Perspective(canvas, horizon, eye=1.6, focal=1.1)
    with canvas.layer(depth=0.98):
        canvas.add(camera.ground_quad(-3000, 3000, 1, 6000), "#e2e2e4", "snow", normal=(0, -1, 0.05))
    for k, x in enumerate((-190.0, -150.0, -95.0)):         # the town on the skyline
        city.building(camera, x, 680 + k * 40, 60 if k != 1 else 22, 12, (12 if k != 1 else 16) * city.PANEL_STOREY + 0.8,
                      "#8a8a8a", kind="panel", light=light, sky=SKY, seed=k, roof=False, scene_depth=0.95)
    rng = np.random.default_rng(seed)
    for _ in range(90):                                      # the birch strip along the far edge of the field
        x, z = rng.uniform(-260, 160), rng.uniform(330, 380)
        px, py = camera.point(x, 0, z)
        sc.bare_tree(canvas, px, py, rng.uniform(9, 15) * camera.scale(z, x), birch=rng.random() < 0.7,
                     seed=int(rng.integers(1 << 30)), spread=0.4, depth=0.85)
    track(camera, seed)
    towers = [city.pylon(camera, x, z, height=34, yaw=-38) for x, z in reversed(PYLONS)][::-1]
    spans = []
    for k in range(len(towers[0])):
        city.wires(camera, [t[k] for t in towers], sag=3.5, width=1.4, color="#2a2a2e", painted=True)
        a, b = np.array(towers[0][k]), np.array(towers[1][k])
        spans.append([camera.point(*(a + (b - a) * t - np.array([0, 3.5 * 4 * t * (1 - t), 0]))) for t in np.linspace(0, 1, 40)])
    perched(canvas, spans[1], 4, seed)
    perched(canvas, spans[3], 3, seed + 1)
    tufts(camera, 60, seed)
    crows(canvas, (W * 0.45, H * 0.08, W * 0.85, H * 0.3), 5, seed)
    sc.weather(canvas, "snow", near=0.5, amount=0.5, wind=0.2, seed=seed)
    return {"light": light}


if __name__ == "__main__":
    studio.run(build, brief, "doomer_landscape.png")
