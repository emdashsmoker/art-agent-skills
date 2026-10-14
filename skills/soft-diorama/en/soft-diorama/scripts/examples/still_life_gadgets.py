"""Modern still life up close: a camera, headphones, a game pad and a drink can on a table.

Boxes, cylinders and flat outlines placed with a perspective camera, shaded
with paint_volume(), then repainted as an oil painting.

Run:  python still_life_gadgets.py [output.png] [oil|illustration]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, finish, save_image, shading, solids

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'still_life_gadgets.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'oil'
WIDTH, HEIGHT = 1400, 1000
SEED = 23
VIEW = city.Perspective(vanishing=(700, -60), focal=2600, eye=1.05)
TABLE_Y = 0.74                      # meters
TABLE_FAR = 1.95                    # where the table ends
LIGHT = (-0.75, -0.65)              # window light from the upper left
SHADOW_SHIFT = (0.03, 0.0)          # meters: shadows fall to the right


def paint_room(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (WIDTH, 560)), '#6f7f86', '#4a555e', '#2c3138'))
    cv.tint(cv.radial((150, 120), 800) ** 1.5, '#e9dcc0', 'screen', 0.30)
    # Window light falling on the wall: a skewed, softened pane pattern.
    panes = cv.empty()
    for column in range(2):
        for row in range(2):
            x0, y0 = 170 + column * 210 + row * 40, 40 + row * 170
            panes = np.maximum(panes, cv.polygon([(x0, y0), (x0 + 190, y0 + 20), (x0 + 228, y0 + 175), (x0 + 38, y0 + 155)]))
    cv.tint(blur(panes, 10), '#f6e6c4', 'screen', 0.22)
    table = cv.polygon(np.array(VIEW.quad([(-2, TABLE_Y, TABLE_FAR), (2, TABLE_Y, TABLE_FAR),
                                           (2, TABLE_Y, 0.5), (-2, TABLE_Y, 0.5)])))
    cv.fill(table, cv.ramp(cv.linear((0, 500), (0, HEIGHT)), '#b9a58c', '#e2d3bd'))
    grain = cv.noise(scale=220, octaves=3, seed=SEED, stretch=(14, 1))
    cv.tint(table * np.clip((grain - 0.5) * 5.0, 0.0, 1.0), '#8a7358', 'normal', 0.20)
    cv.tint(table * cv.linear((1400, 0), (300, 0)) ** 1.5, '#3a3038', 'multiply', 0.30)   # light falls off to the right


def paint_headphones(cv):
    """Resting on their ear cups, the headband arching up between them."""
    left, right, z = -0.30, -0.11, 1.44
    middle, reach = 0.5 * (left + right), 0.5 * (right - left)
    arc = np.linspace(np.pi, 0.0, 24)
    band = [VIEW.project(middle + reach * np.cos(a), TABLE_Y + 0.05 + 0.12 * np.sin(a), z + 0.01) for a in arc]
    ground = solids.flat_path(VIEW, [(middle + reach * np.cos(a) + 0.05 * np.sin(a), z + 0.03 + 0.10 * np.sin(a))
                                     for a in arc], TABLE_Y)
    width = 0.022 * VIEW.scale(z)
    cv.tint(blur(cv.ribbon(ground, width * 1.2, 'flat'), 9), '#0a0a12', 'multiply', 0.30)       # band shadow
    for x in (left, right):
        solids.contact_shadow(cv, VIEW, (x, z), TABLE_Y, 0.060, offset=SHADOW_SHIFT, strength=0.6)
    band_mask = cv.ribbon(band, width, 'flat')
    cv.paint_volume(band_mask, '#2c2e36', LIGHT, bulge=width * 0.5, gloss=0.4)
    cv.tint(cv.ribbon(band[8:17], width * 0.75, 'flat') * band_mask, '#7a6450', 'normal', 0.8)  # leather pad
    for x in (left, right):
        solids.cylinder(cv, VIEW, (x, z), TABLE_Y, 0.050, 0.028, '#d9cdb8', light=LIGHT)           # ear cushion
        cup = solids.cylinder(cv, VIEW, (x, z), TABLE_Y + 0.028, 0.047, 0.026, '#2c2e36', light=LIGHT, gloss=0.4,
                              top_color='#3a3d48')
        cx, cy, rx, ry = cup['top']
        ring = cv.ellipse(cx, cy, rx * 0.62, ry * 0.62) * (1.0 - cv.ellipse(cx, cy, rx * 0.52, ry * 0.52))
        cv.tint(ring, '#c9a23a', 'normal', 0.9)                                                     # brass ring
        yoke = [(cx + rx * (0.95 if x > middle else -0.95), cy - ry * 0.2),
                VIEW.project(x + (0.04 if x > middle else -0.04) * 0.0, TABLE_Y + 0.07, z + 0.01)]
        cv.paint_volume(cv.ribbon(yoke, width * 0.6, 'flat', smooth=False), '#4a4d58', LIGHT, bulge=3)


def paint_camera(cv):
    x, z, width, height, depth = -0.02, 1.22, 0.135, 0.078, 0.045
    solids.contact_shadow(cv, VIEW, (x + width / 2, z + 0.02), TABLE_Y, 0.085, 0.045, offset=SHADOW_SHIFT,
                          strength=0.65)
    body = solids.box(cv, VIEW, (x, TABLE_Y, z), (width, height, depth), '#2a2b30', light_from='left',
                      top_color='#c9ccd2', edge=0)
    cv.paint_volume(cv.polygon(np.array(body['front'])), '#2f3036', LIGHT, bulge=10, depth=0.8)
    plate = cv.polygon(np.array(solids.patch(body['front'], 0.0, 0.0, 1.0, 0.20)))
    cv.fill(plate, '#bfc3ca')                                                # silver top plate
    cv.tint(shading.crescent(plate, LIGHT, 5, 2), '#7a7e88', 'normal', 0.7)
    grip = cv.polygon(np.array(solids.patch(body['front'], 0.0, 0.20, 0.20, 1.0)))
    cv.paint_volume(grip, '#1c1d22', LIGHT, bulge=14, depth=1.2)
    # Viewfinder hump and dials on top.
    solids.box(cv, VIEW, (x + 0.050, TABLE_Y + height, z + 0.008), (0.036, 0.016, 0.030), '#b4b8c0',
               light_from='left', edge=0.4)
    solids.cylinder(cv, VIEW, (x + 0.112, z + 0.022), TABLE_Y + height, 0.011, 0.008, '#a8acb4', light=LIGHT)
    solids.cylinder(cv, VIEW, (x + 0.020, z + 0.022), TABLE_Y + height, 0.007, 0.005, '#c0392b', light=LIGHT)
    # Lens: a barrel pointing at the viewer, then rings and glass on its front circle.
    solids.contact_shadow(cv, VIEW, (x + 0.078, z - 0.035), TABLE_Y, 0.032, 0.03, offset=SHADOW_SHIFT, strength=0.45)
    _, (cx, cy, r) = solids.barrel(cv, VIEW, (x + 0.075, TABLE_Y + 0.040), z, z - 0.050, 0.030, '#26272c',
                                   front_radius=0.028, light=LIGHT, gloss=0.5)
    cv.fill(cv.ellipse(cx, cy, r), '#34363e')
    cv.fill(cv.ellipse(cx, cy, r * 0.86), '#15161a')
    glass = cv.ellipse(cx, cy, r * 0.66)
    cv.fill(glass, cv.ramp(cv.radial((cx + r * 0.2, cy + r * 0.25), r * 0.9), '#1a2f5a', '#3a2a5a', '#0c0e18'))
    cv.tint(shading.crescent(glass, (0.7, 0.7), r * 0.28, r * 0.06), '#9fd0ff', 'screen', 0.45)
    cv.tint(blur(cv.ellipse(cx - r * 0.26, cy - r * 0.28, r * 0.16, r * 0.10, -35), 1.5), '#ffffff', 'screen', 0.9)
    cv.tint(cv.ellipse(cx + r * 0.2, cy + r * 0.24, r * 0.06), '#ffe0c0', 'screen', 0.7)
    cv.tint(cv.ellipse(cx, cy, r * 0.97) * (1.0 - cv.ellipse(cx, cy, r * 0.91)), '#8a8e98', 'normal', 0.7)


def paint_can(cv):
    center = (0.27, 1.30)
    solids.contact_shadow(cv, VIEW, center, TABLE_Y, 0.045, offset=SHADOW_SHIFT, strength=0.65)
    can = solids.cylinder(cv, VIEW, center, TABLE_Y, 0.033, 0.122, '#2f8f7a', light=LIGHT, gloss=0.7,
                          top_color='#c9ccd2')
    tx, ty, trx, try_ = can['top']
    _, by, _, _ = can['bottom']
    drop = by - ty
    label = cv.rect(tx - trx * 1.1, ty + drop * 0.30, tx + trx * 1.1, ty + drop * 0.62) * can['mask']
    cv.tint(label, '#f6efe0', 'normal', 0.85)
    turn = shading.band(shading.form_light(can['mask'], LIGHT, trx * 0.95), 0.45, 0.25)
    cv.tint(label * turn, '#8a8478', 'multiply', 0.5)                        # the label turns with the can
    cv.fill(cv.ellipse(tx + trx * 0.1, ty, trx * 0.34, try_ * 0.36), '#5a5e68')   # opening


def paint_game_pad(cv):
    """Lying flat: one outline on the table plane, raised a little, with sticks and buttons on top."""
    cx, cz, top = 0.13, 0.92, TABLE_Y + 0.030
    outline = [(-0.078, 0.030), (-0.040, 0.040), (0.040, 0.040), (0.078, 0.030), (0.086, -0.010), (0.070, -0.052),
               (0.046, -0.050), (0.030, -0.018), (-0.030, -0.018), (-0.046, -0.050), (-0.070, -0.052),
               (-0.086, -0.010)]

    def place(points):
        return [(cx + x, cz + depth) for x, depth in points]

    shadow = solids.flat_shape(cv, VIEW, place([(x + 0.014, depth + 0.004) for x, depth in outline]), TABLE_Y)
    cv.tint(blur(shadow, 9), '#0a0a12', 'multiply', 0.6)
    cable = solids.flat_path(VIEW, [(cx, cz + 0.030), (cx + 0.03, cz + 0.12), (cx + 0.16, cz + 0.16),
                                    (cx + 0.34, cz + 0.10), (cx + 0.60, cz + 0.14)], TABLE_Y + 0.003)
    cv.tint(blur(cv.ribbon([(x + 3, y + 3) for x, y in cable], 5, 'flat'), 2.5), '#0a0a12', 'multiply', 0.4)
    cv.paint_volume(cv.ribbon(cable, 5.5, 'flat'), '#3a3d48', LIGHT, bulge=2.5)
    solids.slab(cv, VIEW, place(outline), TABLE_Y, top - TABLE_Y, '#eceef2', LIGHT, gloss=0.25)
    for x, depth in ((-0.045, 0.012), (0.022, -0.010)):                                            # thumb sticks
        solids.cylinder(cv, VIEW, (cx + x, cz + depth), top - 0.002, 0.0115, 0.010, '#2a2c34', light=LIGHT, gloss=0.3)
    for (x, depth), color in (((0.048, 0.022), '#e0b030'), ((0.060, 0.010), '#d04a3a'), ((0.036, 0.010), '#3f7fd6'),
                              ((0.048, -0.002), '#4aa860')):
        button, (_, _, brx, _) = solids.disc(cv, VIEW, (cx + x, cz + depth), top + 0.002, 0.0055)
        cv.paint_volume(button, color, LIGHT, bulge=brx * 0.8, gloss=0.5)
    arms = [[(-0.031, -0.002), (-0.013, -0.002), (-0.013, -0.010), (-0.031, -0.010)],
            [(-0.026, 0.004), (-0.018, 0.004), (-0.018, -0.016), (-0.026, -0.016)]]
    cross = np.maximum(*[solids.flat_shape(cv, VIEW, place(arm), top + 0.002, smooth=False) for arm in arms])
    cv.fill(cross, '#3a3d48')


def paint_phone(cv):
    """A phone lying face up, turned on the table: a slab, then a glass picture pasted on its top."""
    cx, cz, turn = -0.20, 0.93, np.radians(-20)
    half_w, half_l, corner = 0.037, 0.078, 0.010

    def place(points):
        return [(cx + x * np.cos(turn) - z * np.sin(turn), cz + x * np.sin(turn) + z * np.cos(turn)) for x, z in points]

    outline = [(-half_w + corner, half_l), (half_w - corner, half_l), (half_w, half_l - corner), (half_w, -half_l + corner),
               (half_w - corner, -half_l), (-half_w + corner, -half_l), (-half_w, -half_l + corner),
               (-half_w, half_l - corner)]
    shadow = solids.flat_shape(cv, VIEW, place([(x + 0.010, z) for x, z in outline]), TABLE_Y, smooth=False)
    cv.tint(blur(shadow, 7), '#0a0a12', 'multiply', 0.55)
    solids.slab(cv, VIEW, place(outline), TABLE_Y, 0.009, '#20222a', LIGHT, bulge=3, smooth=False)
    glass = Canvas(150, 310, '#0e1018')
    glass.tint(glass.ribbon([(-20, 250), (170, 40)], 46, 'flat', smooth=False), '#ffffff', 'screen', 0.10)
    glass.tint(glass.ribbon([(-20, 330), (170, 120)], 14, 'flat', smooth=False), '#ffffff', 'screen', 0.08)
    inset = [(-half_w + 0.004, half_l - 0.006), (half_w - 0.004, half_l - 0.006), (half_w - 0.004, -half_l + 0.006),
             (-half_w + 0.004, -half_l + 0.006)]                          # far-left, far-right, near-right, near-left
    cv.paste(glass, solids.flat_path(VIEW, place(inset), TABLE_Y + 0.009))


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_room(cv)
    room = cv.color.copy()
    paint_headphones(cv)
    paint_can(cv)
    paint_camera(cv)
    paint_phone(cv)
    paint_game_pad(cv)
    if STYLE == 'oil':
        # Small brushes wherever an object was painted, so dials, buttons and lens rings stay legible.
        objects = (np.abs(cv.color - room).max(axis=-1) > 0.03).astype(np.float32)
        image = finish.finish_oil(cv, radii=(20, 10, 5, 3), impasto=0.28, ground='#5a5048', seed=SEED, detail=objects)
    else:
        image = finish.finish_illustration(cv, glow=0.14, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
