"""Doomer cityscape: a wide suburban avenue at night in wet snow, sodium lamps running off to the vanishing point.

Long prefabricated blocks line both sides behind strips of birches; trolleybus wires hang over each carriageway from
the lamp posts; a lit kiosk and a bus shelter stand on the right pavement, where one late walker heads home. A car
comes toward us with its lights on. Grey slush lies between dark wet wheel tracks and mirrors the lights, and a
chimney's red warning lights blink far down the avenue.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from atelier import Brief, city, geom, light as make_light, scenery as sc, studio

brief = Brief.from_answers(subject="landscape", style="doomer", format="landscape", composition="center",
                           lighting="night", background="city", mood="melancholic", palette="doomer",
                           message="a suburban avenue lined with sodium lamps on a night of wet snow", seed=137)
SODIUM = "#ffb468"
SKY = "#2a2a3a"
WALLS = ["#6e6c68", "#76726a", "#686a6c"]
WIRE_Y = 6.2                 # height of the trolleybus contact wires
AXIS = -10.0                 # the avenue's centre line; the camera stands at x = 0 by the right-hand kerb


def kiosk(camera, x, z):
    """A small street kiosk: a box with a lit shop window and a flat roof that overhangs."""
    faces = camera.box(x, z, 2.6, 2.0, 2.5, "#4a5a5e", region="kiosk", outline=0.8)
    camera.box(x - 0.15, z - 0.15, 2.9, 2.3, 0.18, "#3a3e42", y=2.5, region="kiosk", outline=0.8)
    side = faces["side"] if faces["side"].visible else faces["front"]
    window = geom.polygon([side(0.12, 0.35), side(0.88, 0.35), side(0.88, 0.85), side(0.12, 0.85)])
    camera.canvas.add(window, "#ffd890", "kiosk_window", unlit=True)


def shelter(camera, x, z, length=5.0):
    """A bus shelter: a back wall of glass between steel posts under a thin roof."""
    posts = [((x, 0, z + d), (x, 2.4, z + d)) for d in np.linspace(0, length, 4)]
    city.struts(camera, posts, "#2a2c30", width=0.08, region="shelter", depth=float(np.clip(0.2 + camera.depth(x, z) / 200, 0.15, 0.8)))
    glass = camera.quad([(x, 0.3, z), (x, 2.3, z), (x, 2.3, z + length), (x, 0.3, z + length)])
    camera.canvas.add(glass, "#5a6a7a", "shelter", alpha=0.45, normal=(-1, 0, 0.3))
    camera.box(x - 1.4, z, 1.6, length, 0.12, "#3a3e42", y=2.4, region="shelter", outline=0.8)


def slush(camera):
    """Wet snow churned on the carriageway: grey slush between the lanes, dark wet wheel tracks, banks at the kerbs."""
    canvas = camera.canvas
    with canvas.layer(depth=0.62):
        for lane in (-10.25, -6.75, -3.25, 3.25, 6.75, 10.25):
            canvas.add(camera.ground_quad(AXIS + lane - 1.6, AXIS + lane + 1.6, 0.5, 900, y=0.004), "#464a56", "road",
                       normal=(0, -1, 0.05))
            for track in (-0.8, 0.8):
                canvas.add(camera.ground_quad(AXIS + lane + track - 0.24, AXIS + lane + track + 0.24, 0.5, 900, y=0.008),
                           "#2c2e36", "road", normal=(0, -1, 0.05), gloss=0.5)
        for edge in (-12.0, 11.2):
            canvas.add(camera.ground_quad(AXIS + edge, AXIS + edge + 0.8, 0.5, 900, y=0.01), "#7a808e", "road",
                       normal=(0, -1, 0.2))


def build(canvas, light, brief):
    light = make_light("night", azimuth=-25, elevation=40, color="#9aa4c4", shadow_tint="#2c3448", haze="#2a2630",
                       haze_strength=0.45)
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon = H * 0.56
    sc.sky(canvas, "#05060c", "#2e2832", horizon, glow=(W * 0.4, horizon, W * 0.3), glow_color="#5a3c2c")
    # We stand at the right-hand kerb: the avenue's axis lies to our left, so the camera turns a little toward it.
    camera = sc.Perspective(canvas, horizon, eye=1.7, focal=0.95, yaw=-7)
    with canvas.layer(depth=0.97):
        canvas.add(camera.ground_quad(-300, 300, 0.5, 900), "#4a4e5a", "snow", normal=(0, -1, 0.05))
    city.chimney(camera, AXIS + 30, 820, 110, 4.5)
    for side in (-1, 1):                                    # blocks on both sides, far to near
        for k, z in enumerate(np.arange(520, 30, -70)):
            x = AXIS + (26 if side > 0 else -26 - 13)
            storeys = (9, 12, 9, 5, 9, 16, 9)[(k + (side > 0)) % 7]
            city.building(camera, x, z, 13, 58, storeys * city.PANEL_STOREY + 0.8, WALLS[(k + side) % 3], kind="panel",
                          light=light, night=True, sky=SKY, seed=seed + k * 2 + (side > 0))
    for side in (-1, 1):                                    # birches between the pavement and the blocks
        for k, z in enumerate(np.arange(300, 5, -9)):
            x = AXIS + side * (17.5 + (k % 3) * 1.2)
            px, py = camera.point(x, 0, z)
            sc.bare_tree(canvas, px, py, 8.5 * camera.scale(z, x), birch=True, seed=seed + k * 3 + (side > 0), spread=0.4,
                         depth=float(np.clip(0.2 + camera.depth(x, z) / 200, 0.15, 0.8)))
    city.road(camera, AXIS - 12, AXIS + 12, 0.5, 900, color="#33353e", line="#6a6a70")
    slush(camera)
    city.sidewalk(camera, AXIS - 16, AXIS - 12, 0.5, 900, color="#5a5e6a")
    city.sidewalk(camera, AXIS + 12, AXIS + 16, 0.5, 900, color="#5a5e6a")
    wires = {AXIS + x: [] for x in (-7.5, -4.5, 4.5, 7.5)}
    for z in np.arange(600, 6, -32):                       # lamp posts carry the span wires for the trolleybus lines
        for side in (-1, 1):
            city.lamp(camera, AXIS + side * 12.6, z, height=8.5, reach=1.8, night=True, glow=SODIUM)
        for x in wires:
            wires[x].append((x, WIRE_Y, z))
        city.wires(camera, [(AXIS - 12.6, WIRE_Y + 0.4, z), (AXIS + 12.6, WIRE_Y + 0.4, z)], sag=0.25, width=0.8,
                   color="#16181e", painted=True)
    for x, anchors in wires.items():
        city.wires(camera, anchors, sag=0.15, width=0.9, color="#16181e", painted=True)
    kiosk(camera, AXIS + 13.0, 34)
    shelter(camera, AXIS + 15.4, 17, length=5.5)
    city.car(camera, AXIS - 7.0, 30, "#5a5e66", kind="hatch", facing=-1, night=True, sky=SKY, light=light)
    city.pedestrian(camera, AXIS + 13.6, 46, color="#1c1e24", seed=4)
    road = canvas.region_mask("road", "sidewalk", "kerb")
    sc.wet_reflection(canvas, road.astype("float32"), light, strength=0.5, streak=1.6, glow=1.4, threshold=0.5, seed=seed)
    sc.weather(canvas, "snow", near=0.3, amount=1.0, wind=0.25, seed=seed)
    return {"light": light}


if __name__ == "__main__":
    studio.run(build, brief, "doomer_city.png")
