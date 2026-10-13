"""Doomer still life: a kitchen windowsill late at night. A glass ashtray with a cigarette left burning,
tea in a glass with a metal holder, an old cassette radio; through the double window the lit blocks
across the yard and the falling snow.

Run:  python doomer_still_life.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, doomer, save_image, solids

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'doomer_still_life.png'
P = doomer.PALETTE
WIDTH, HEIGHT = 1400, 1000
SEED = 87
VIEW = city.Perspective(vanishing=(700, 430), focal=1500, eye=1.18)
WALL_Z, SILL = 1.55, (-1.2, 1.2, 1.12, 0.95, 0.04)      # wall plane; sill x0, x1, front z, top y, thickness
WINDOW = (-0.55, 0.55, 0.99, 2.6)                       # opening x0, x1, bottom y, top y (on the wall plane)
FRAME = 0.045                                           # meters; window frame bars
LIGHT = 'left'                                          # a dim lamp somewhere on the left of the kitchen
LAMP_LIGHT = (-0.7, -0.6)
ASHTRAY = (-0.34, 1.33)
TEA = (0.02, 1.30)
RADIO = (0.12, 0.955, 1.25, (0.32, 0.13, 0.09))         # x, y, z of its near-left corner, size (w, h, d)
RADIATOR = (-0.65, 0.65, 0.18, 0.80, 14)                # x0, x1, bottom y, top y, sections (under the sill)


def paint_outside(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, VIEW.vanishing[1])), P['night'], P['sky_top'], '#3d4855'))
    for x0, x1, z0, floors, seed in ((-40, 2, 38, 9, 1), (8, 60, 52, 12, 2)):
        doomer.panel_block(cv, VIEW, x0, x1, z0, z0 + 12, floors, wall='#4e545c', lit_ratio=0.24, haze=P['fog'],
                           haze_amount=0.2, antennas=0, seed=SEED + seed)
    ground = city.project_polygon(VIEW, [(-80, 0, 20), (80, 0, 20), (80, 0, 200), (-80, 0, 200)])
    cv.fill(cv.polygon(ground), '#6f7884')
    city.street_lamp(cv, VIEW, 4.0, 28.0, height=6.0, glow=P['sodium'], pole=P['night'])
    doomer.snowfall(cv, 240, size=1.6, seed=SEED)


def paint_window_and_wall(cv):
    x0, x1, bottom, top = WINDOW
    opening = cv.polygon(np.array(VIEW.front_quad(x0, x1, WALL_Z, top, base=bottom)))
    wall = 1.0 - opening
    cv.fill(wall, cv.ramp(cv.linear((0, 0), (WIDTH, 0)), '#4d5560', '#39404a'))
    cv.tint(cv.radial((0, 300), 1100) ** 2 * wall, '#e8b07a', 'soft_light', 0.35)        # the lamp on the left
    cv.tint(cv.radial((0, 300), 1100) ** 2 * opening, '#e8b07a', 'screen', 0.06)          # its reflection in the glass
    frame = '#b9b6ae'
    bars = [(x0, x0 + FRAME, bottom, top), (x1 - FRAME, x1, bottom, top), (x0, x1, bottom, bottom + FRAME),
            (-FRAME / 2, FRAME / 2, bottom, top), (x0, x1, 1.95, 1.95 + FRAME)]           # sash, mullion, transom
    for bx0, bx1, by0, by1 in bars:
        cv.fill(cv.polygon(np.array(VIEW.front_quad(bx0, bx1, WALL_Z - 0.02, by1, base=by0))), frame)
    reveal = cv.polygon(np.array(VIEW.front_quad(x0 - 0.06, x1 + 0.06, WALL_Z, top, base=bottom - 0.01))) * wall
    cv.tint(reveal, '#2a2f36', 'multiply', 0.4)


def paint_sill(cv):
    sx0, sx1, front, top, thick = SILL
    sill = solids.box(cv, VIEW, (sx0, top - thick, front), (sx1 - sx0, thick, WALL_Z - front), '#9d9a92',
                      light_from=LIGHT, edge=0.3)
    below = cv.polygon(np.array(VIEW.front_quad(-3.0, 3.0, front, top - thick, base=-1.0)))
    cv.fill(below, '#2c3139')                                                            # the dark under the sill
    rx0, rx1, bottom, rtop, sections = RADIATOR
    step = (rx1 - rx0) / sections
    for k in range(sections):                                                            # cast-iron radiator ribs
        x = rx0 + k * step
        rib = cv.polygon(np.array(VIEW.front_quad(x + step * 0.12, x + step * 0.88, WALL_Z - 0.08, rtop, base=bottom)))
        cv.paint_volume(rib * below, '#4a4f56', LAMP_LIGHT, bulge=step * 0.3 * VIEW.scale(WALL_Z))
    return sill


def paint_ashtray(cv):
    _, _, _, top, _ = SILL
    solids.contact_shadow(cv, VIEW, ASHTRAY, top, 0.08, offset=(0.03, 0.0), strength=0.5)
    tray = solids.cylinder(cv, VIEW, ASHTRAY, top, 0.075, 0.028, '#8d9eac', top_radius=0.08, light=LAMP_LIGHT,
                           gloss=0.6, hollow='#5c6976')
    cv.tint(tray['mask'], '#cfe0ef', 'screen', 0.15)                                    # glass catches the window
    ashes = cv.ellipse(*VIEW.project(ASHTRAY[0] + 0.01, top + 0.02, ASHTRAY[1]), 0.03 * VIEW.scale(ASHTRAY[1]),
                       0.008 * VIEW.scale(ASHTRAY[1]))
    cv.fill(blur(ashes, 1.5), '#9a9a96', 0.8)
    base = VIEW.project(ASHTRAY[0] - 0.02, top + 0.024, ASHTRAY[1] + 0.01)
    tip = VIEW.project(ASHTRAY[0] + 0.12, top + 0.031, ASHTRAY[1] - 0.05)
    ember = doomer.cigarette(cv, base, tip, 0.0085 * VIEW.scale(ASHTRAY[1]))
    doomer.smoke(cv, ember, 520, drift=90, width=3.0, color='#c9cfd5', opacity=0.6, strands=4, seed=SEED)


def paint_tea(cv):
    _, _, _, top, _ = SILL
    solids.contact_shadow(cv, VIEW, TEA, top, 0.045, offset=(0.02, 0.0), strength=0.5)
    glass = solids.cylinder(cv, VIEW, TEA, top, 0.031, 0.115, '#9aa8b3', top_radius=0.034, light=LAMP_LIGHT,
                            gloss=0.7, hollow='#6a3418')
    tea = solids.cylinder(cv, VIEW, TEA, top + 0.005, 0.029, 0.09, '#7a3a18', light=LAMP_LIGHT, gloss=0.3)
    cv.tint(tea['mask'], '#e09a50', 'screen', 0.2)
    holder = solids.cylinder(cv, VIEW, TEA, top, 0.035, 0.07, '#8c8a84', top_radius=0.037, light=LAMP_LIGHT,
                             gloss=0.8)
    tx, ty, trx, _ = holder['top']
    bx, by, brx, _ = holder['bottom']
    handle = cv.ribbon([(tx + trx * 0.9, ty + 2), (tx + trx * 1.8, (ty + by) / 2), (bx + brx * 0.9, by - 6)],
                       trx * 0.22, 'flat')
    cv.paint_volume(handle * (1.0 - holder['mask']), '#8c8a84', LAMP_LIGHT, bulge=trx * 0.1, gloss=0.6)
    gx, gy, grx, _ = glass['top']
    spoon = cv.ribbon([(gx + grx * 0.2, gy + 6), (gx - grx * 0.9, gy - 0.07 * VIEW.scale(TEA[1]))], grx * 0.12, 'flat')
    cv.fill(spoon, '#b7b5ae')


def paint_radio(cv):
    x, y, z, size = RADIO
    _, _, _, top, _ = SILL
    solids.contact_shadow(cv, VIEW, (x + size[0] / 2, z + size[2] / 2), top, 0.2, 0.06, strength=0.5)
    radio = solids.box(cv, VIEW, (x, y, z), size, '#3d3a36', light_from=LIGHT, edge=0.4, turn=-12)
    face = Canvas(360, 150, '#45413c')
    for cx in (62, 298):                                                              # speaker grilles
        face.fill(face.ellipse(cx, 75, 50), '#2b2926')
        holes = [face.ellipse(cx + dx, 75 + dy, 3) for dx in range(-40, 41, 10) for dy in range(-40, 41, 10)
                 if dx * dx + dy * dy < 1500]
        face.fill(np.maximum.reduce(holes), '#1a1917')
    face.fill(face.rect(122, 52, 238, 112, radius=4), '#1d1c1a')                       # cassette window
    for cx in (155, 205):
        face.fill(face.ellipse(cx, 82, 12), '#5a554e')
    face.fill(face.rect(122, 20, 238, 38, radius=3), '#d9a35e')                         # the lit tuning dial
    face.fill(face.rect(178, 20, 181, 38), '#4a2a1a')
    cv.paste(face, solids.patch(radio['front'], 0.0, 0.0, 1.0, 1.0))
    dial = solids.patch(radio['front'], 0.34, 0.13, 0.66, 0.25)
    doomer.lamp_glow(cv, tuple(np.mean(np.array(dial), axis=0)), 0.06 * VIEW.scale(z), '#ffb867', 0.5)
    corner = VIEW.project(x + size[0] - 0.03, y + size[1], z + size[2] - 0.02)
    cv.fill(cv.ribbon([corner, VIEW.project(x + size[0] - 0.25, y + size[1] + 0.42, z + 0.05)],
                      0.004 * VIEW.scale(z), 'flat'), '#a9aaa8')                          # telescopic antenna


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_outside(cv)
    paint_window_and_wall(cv)
    paint_sill(cv)
    paint_radio(cv)
    paint_tea(cv)
    paint_ashtray(cv)
    save_image(OUTPUT, doomer.finish(cv, warmth=0.7, seed=SEED))


if __name__ == '__main__':
    main()
