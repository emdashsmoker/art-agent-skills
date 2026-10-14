"""Doomer cityscape: a wide avenue between panel blocks on a wet winter night. Sodium lamps line both
pavements, their light smeared on the asphalt; the trolleybus wires run off to the vanishing point.
One kiosk is still open.

Run:  python doomer_city.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, doomer, save_image, solids
from paintkit.raster import smoothstep as raster_smooth

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'doomer_city.png'
P = doomer.PALETTE
WIDTH, HEIGHT = 1100, 1400
SEED = 85
VIEW = city.Perspective(vanishing=(560, 800), focal=900, eye=1.7)
ROAD_HALF, PAVEMENT = 7.0, 3.5
FAR = 260.0
BLOCK_DEPTH, BLOCK_LENGTH, GAP = 14.0, 46.0, 16.0        # meters; a block, then a gap to the next one
LAMP_STEP, LAMP_HEIGHT = 18.0, 6.8
WIRE_HEIGHT, WIRE_X = 6.2, (-3.6, -3.0, 3.0, 3.6)        # trolleybus contact wires over the lanes
WIRE_SAG = 0.12                                          # meters: contact wires are pulled nearly straight
ROAD_PX = 6                                              # px per meter of the road texture
NIGHT_WALL = '#5a6069'
KIOSK = (8.2, 15.0, (2.6, 2.7, 2.2))                     # x, z, size (w, h, d) on the right pavement


def road_texture():
    """The avenue seen from above (far end at the top): wet asphalt, faded dashes, puddles holding the sky."""
    width, length = int(2 * ROAD_HALF * ROAD_PX), int((FAR - 1.0) * ROAD_PX)
    tex = Canvas(width, length, P['asphalt'])
    puddles = tex.noise(scale=7.0 * ROAD_PX, octaves=3, seed=SEED, stretch=(1.0, 2.0))
    tex.tint(raster_smooth(puddles, 0.58, 0.66), '#3a4250', 'normal', 0.6)
    dashes = [tex.rect(width / 2 - 0.08 * ROAD_PX, length - (z + 3.0) * ROAD_PX, width / 2 + 0.08 * ROAD_PX,
                       length - z * ROAD_PX) for z in np.arange(3.0, FAR - 1.0, 9.0)]
    tex.tint(np.maximum.reduce(dashes), '#8a8f96', 'normal', 0.45)
    return tex


def paint_ground(cv):
    horizon = VIEW.vanishing[1]
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, horizon)), P['night'], P['sky_top'], '#3a4452'))
    outer = ROAD_HALF + PAVEMENT
    cv.fill(cv.polygon(np.array(VIEW.ground_quad(-outer - 30, outer + 30, 1.0, FAR))), '#7d8692')
    return cv.paste(road_texture(), VIEW.ground_quad(-ROAD_HALF, ROAD_HALF, 1.0, FAR))


def paint_blocks(cv):
    """Blocks down both sides, far to near, so the near ones cover the far ones."""
    outer = ROAD_HALF + PAVEMENT
    plan = []
    for side in (-1, 1):
        z, index = 6.0, 0
        while z < FAR:
            floors = (9, 12, 9, 5)[(index + (side > 0)) % 4]
            plan.append((z, side, floors, index))
            z += BLOCK_LENGTH + GAP
            index += 1
    for z, side, floors, index in sorted(plan, key=lambda item: -item[0]):
        x_near, x_far = side * outer, side * (outer + BLOCK_DEPTH)
        x0, x1 = min(x_near, x_far), max(x_near, x_far)
        distance = min(z / FAR, 1.0) ** 0.6
        doomer.panel_block(cv, VIEW, x0, x1, z, z + BLOCK_LENGTH, floors, wall=NIGHT_WALL, lit_ratio=0.2,
                           haze=P['fog'], haze_amount=0.7 * distance, antennas=2, seed=SEED + index * 2 + (side > 0))


def paint_lamps_and_wires(cv, road):
    outer = ROAD_HALF + PAVEMENT - 0.6
    lamps = [(side * outer, z) for z in np.arange(8.0, FAR * 0.6, LAMP_STEP) for side in (-1, 1)]
    for x, z in sorted(lamps, key=lambda lamp: -lamp[1]):
        city.street_lamp(cv, VIEW, x, z, height=LAMP_HEIGHT, glow=P['sodium'], pole=P['night'])
        pool = VIEW.project(x - np.sign(x) * 1.6, 0.0, z)
        scale = VIEW.scale(z)
        streak = cv.ribbon([pool, (pool[0], pool[1] + 9.0 * scale)], 1.6 * scale, [1.0, 0.5, 0.0])
        cv.tint(blur(streak, 0.5 * scale) * road, P['sodium'], 'screen', 0.35)      # reflection on wet asphalt
    strokes = []
    span_zs = np.arange(8.0, FAR * 0.6, LAMP_STEP)
    for z in span_zs:                                             # span wires from pole to pole
        left, right = VIEW.project(-outer, LAMP_HEIGHT - 0.4, z), VIEW.project(outer, LAMP_HEIGHT - 0.4, z)
        strokes.append(((left, right), z))
    for x in WIRE_X:                                              # contact wires, sagging between spans
        for z0, z1 in zip(span_zs[:-1], span_zs[1:]):
            t = np.linspace(0.0, 1.0, 12)
            points = [VIEW.project(x, WIRE_HEIGHT - WIRE_SAG * 4 * s * (1 - s), z0 + (z1 - z0) * s) for s in t]
            cv.fill(cv.ribbon(np.array(points), max(0.04 * VIEW.scale(z0), 0.8), 'flat'), P['night'], 0.85)
    for (left, right), z in strokes:
        doomer.wires(cv, [(left, right)], sag=0.03, width=max(0.03 * VIEW.scale(z), 0.7), opacity=0.8)


def paint_kiosk(cv):
    x, z, size = KIOSK
    box = solids.box(cv, VIEW, (x - size[0] / 2, 0.0, z), size, '#5a6a6a', light_from='right', edge=0.4)
    window = Canvas(160, 90, P['window_warm'])
    window.fill(window.rect(8, 50, 152, 56), '#b08850')
    for k in range(6):                                            # goods on the shelves
        window.fill(window.rect(14 + k * 24, 26, 30 + k * 24, 48), ('#7a4a3a', '#3a5a6a', '#8a7a4a')[k % 3])
    cv.paste(window, solids.patch(box['left'], 0.08, 0.30, 0.92, 0.66))
    glow_at = VIEW.project(x - size[0] / 2, 1.4, z + size[2] / 2)
    doomer.lamp_glow(cv, glow_at, 3.0 * VIEW.scale(z), P['window_warm'], 0.45)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    road = paint_ground(cv)
    paint_blocks(cv)
    paint_kiosk(cv)
    paint_lamps_and_wires(cv, road)
    image_haze = cv.radial(VIEW.vanishing, 520, 260) ** 1.5
    cv.tint(image_haze, P['fog'], 'screen', 0.35)                # the avenue disappears into the haze
    doomer.snowfall(cv, 260, size=2.0, seed=SEED)
    save_image(OUTPUT, doomer.finish(cv, warmth=0.65, seed=SEED))


if __name__ == '__main__':
    main()
