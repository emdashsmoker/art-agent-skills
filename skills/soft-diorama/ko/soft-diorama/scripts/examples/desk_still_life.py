"""Modern still life: a desk at night with a monitor, laptop, keyboard, mouse, phone, mug, lamp, books and a plant.

Every object is a box or a cylinder placed with a perspective camera; screens
and keys are flat pictures pasted onto their faces.

Run:  python desk_still_life.py [output.png] [night|day]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, finish, save_image, scenery, solids

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'desk_still_life.png'
NIGHT = (sys.argv[2] if len(sys.argv) > 2 else 'night') == 'night'
WIDTH, HEIGHT = 1400, 1000
SEED = 19
VIEW = city.Perspective(vanishing=(700, 300), focal=1250, eye=1.45)
DESK_Y = 0.74                       # meters: height of the desk top
DESK_Z, WALL_Z = 1.20, 2.25         # meters from the camera: front edge of the desk, the wall
LIGHT = (0.7, -0.7)                 # the lamp stands on the right
SCREEN_GLOW = '#7fd0ff'
LAMP_GLOW = '#ffc98a'


# --- flat pictures to paste -------------------------------------------------------

def code_screen(width, height, accent):
    """An editor window: title bar, sidebar, colored lines of 'code'."""
    cv = Canvas(width, height, '#141a2a')
    rng = np.random.default_rng(SEED)
    cv.fill(cv.rect(0, 0, width, height * 0.07), '#222a40')
    for index, tone in enumerate(('#ff5f57', '#febc2e', '#28c840')):
        cv.fill(cv.ellipse(height * 0.035 * (1.4 + index * 1.5), height * 0.035, height * 0.016), tone)
    cv.fill(cv.rect(0, height * 0.07, width * 0.18, height), '#1a2136')
    palette = ('#7fd0ff', '#c9a0ff', '#8fe0a0', '#ffd08a', '#8a94b0')
    line_height = height * 0.052
    for row in range(int((height * 0.86) / line_height)):
        y = height * 0.11 + row * line_height
        if row % 7 == 6:
            continue
        indent = width * (0.21 + 0.03 * rng.integers(0, 4))
        x = indent
        for _ in range(rng.integers(1, 5)):
            length = width * rng.uniform(0.04, 0.16)
            if x + length > width * 0.95:
                break
            cv.fill(cv.rect(x, y, x + length, y + line_height * 0.42, radius=line_height * 0.2),
                    palette[rng.integers(len(palette))])
            x += length + width * 0.012
        if row < 16:
            cv.fill(cv.rect(width * 0.03, y, width * (0.08 + 0.06 * rng.random()), y + line_height * 0.38,
                            radius=line_height * 0.18), '#3a4466')
    cv.fill(cv.rect(width * 0.21, height * 0.11 + 9 * line_height - 2, width * 0.94,
                    height * 0.11 + 9.6 * line_height), accent, 0.18)
    return cv


def chart_screen(width, height):
    """A dashboard: a few cards with a line chart and bars."""
    cv = Canvas(width, height, '#e4e9f2')
    cv.fill(cv.rect(0, 0, width, height * 0.10), '#2f4a7a')
    rng = np.random.default_rng(SEED + 1)
    for column in range(2):
        x0 = width * (0.05 + 0.48 * column)
        card = cv.rect(x0, height * 0.17, x0 + width * 0.42, height * 0.92, radius=height * 0.03)
        cv.fill(card, '#ffffff')
        if column == 0:
            xs = np.linspace(x0 + width * 0.04, x0 + width * 0.38, 9)
            ys = height * (0.75 - 0.4 * np.cumsum(rng.uniform(-0.04, 0.12, 9)))
            cv.fill(cv.ribbon(list(zip(xs, ys)), height * 0.02, 'flat', smooth=False), '#3f7fd6')
        else:
            for bar in range(5):
                bx = x0 + width * (0.05 + 0.07 * bar)
                top = height * (0.82 - rng.uniform(0.15, 0.5))
                cv.fill(cv.rect(bx, top, bx + width * 0.045, height * 0.84, radius=3), ('#3f7fd6', '#f2a23a')[bar % 2])
    return cv


def keyboard_top(width, height, body='#23262e', key='#474c5a'):
    cv = Canvas(width, height, body)
    rows, columns = 5, 15
    gap = width * 0.008
    key_w, key_h = (width - gap * (columns + 1)) / columns, (height - gap * (rows + 1)) / rows
    keys = cv.empty()
    for row in range(rows):
        for column in range(columns):
            if row == rows - 1 and 4 <= column <= 9:
                continue
            x0, y0 = gap + column * (key_w + gap), gap + row * (key_h + gap)
            keys = np.maximum(keys, cv.rect(x0, y0, x0 + key_w, y0 + key_h, radius=key_h * 0.18))
    x0 = gap + 4 * (key_w + gap)
    keys = np.maximum(keys, cv.rect(x0, gap + 4 * (key_h + gap), x0 + 6 * key_w + 5 * gap, height - gap,
                                    radius=key_h * 0.18))
    cv.fill(keys, key)
    cv.tint(keys * (1.0 - cv.linear((0, 0), (0, height))), '#ffffff', 'screen', 0.10)
    return cv


def phone_screen(width, height):
    cv = Canvas(width, height, '#101420')
    cv.fill(cv.rect(width * 0.08, height * 0.10, width * 0.92, height * 0.30, radius=width * 0.06), '#2a3a5a')
    cv.fill(cv.rect(width * 0.16, height * 0.15, width * 0.62, height * 0.19, radius=4), '#cfe0ff')
    cv.fill(cv.rect(width * 0.16, height * 0.22, width * 0.80, height * 0.25, radius=4), '#8a9ac0')
    return cv


# --- the scene --------------------------------------------------------------------

def paint_room(cv):
    """Wall, window, poster and the desk top. Returns (desk top mask, window mask)."""
    wall_top, wall_bottom = ('#5a5f8a', '#6a6488') if NIGHT else ('#ece6da', '#ddd5c8')
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, HEIGHT * 0.7)), wall_top, wall_bottom))
    frame_tone = '#8a86a6' if NIGHT else '#f6f2ea'
    frame = VIEW.front_quad(-1.15, -0.40, WALL_Z, 1.95, base=1.05)
    pane = Canvas(450, 540)
    if NIGHT:
        pane.fill(pane.full(), pane.ramp(pane.linear((0, 0), (0, 540)), '#0d1230', '#4a3a6a'))
        city.skyline(pane, 540, height=(90, 360), width=(34, 84), color='#1a1e3c', lit_ratio=0.3, window_px=4, seed=SEED)
        scenery.bokeh(pane, 14, ('#ffd9a0', '#9fd0ff', '#ff9fb0'), (6, 16), opacity=0.45, seed=SEED)
    else:
        scenery.sky(pane, '#4f8fdf', '#d6ecfb')
        scenery.cloud_bank(pane, (140, 460), count=4, size=(140, 320), seed=SEED)
    pane.fill(np.maximum(pane.rect(219, 0, 231, 540), pane.rect(0, 264, 450, 276)), frame_tone)
    window = cv.paste(pane, frame)
    cv.outline(window, 7.0, frame_tone)
    # A framed poster on the right.
    art = Canvas(300, 380, '#f1e6d2')
    art.fill(art.ellipse(170, 150, 70), '#e8804a')
    art.fill(art.blob([(0, 380), (0, 260), (90, 215), (180, 262), (300, 228), (300, 380)]), '#2f5f6a')
    art.fill(art.blob([(0, 380), (0, 318), (130, 288), (300, 330), (300, 380)]), '#1f3f4a')
    poster = cv.paste(art, VIEW.front_quad(0.52, 0.94, WALL_Z, 1.98, base=1.45))
    cv.outline(poster, 5.0, '#2a2c34')
    # Desk top with wood grain.
    desk = solids.box(cv, VIEW, (-1.5, DESK_Y - 0.04, DESK_Z), (3.0, 0.04, WALL_Z - DESK_Z), '#b08660',
                      light_from='right', edge=0)
    top = cv.polygon(np.array(desk['top']))
    cv.tint(top * cv.linear((0, 1000), (0, 690)), '#3a2a20', 'multiply', 0.22)        # the far end falls off
    grain = cv.noise(scale=150, octaves=3, seed=SEED, stretch=(12, 1))
    cv.tint(top * np.clip((grain - 0.5) * 6.0, 0.0, 1.0), '#6a4a34', 'normal', 0.16)
    cv.tint(cv.rect(0, 700, WIDTH, 708) * (1.0 - top), '#1a1420', 'multiply', 0.35)   # where desk meets wall
    return top, window


def paint_monitor(cv):
    z = 1.95
    solids.contact_shadow(cv, VIEW, (0.0, z), DESK_Y, 0.19, 0.10, strength=0.5)
    solids.cylinder(cv, VIEW, (0.0, z), DESK_Y, 0.12, 0.012, '#3a3d46', light=LIGHT)
    solids.box(cv, VIEW, (-0.025, DESK_Y, z), (0.05, 0.16, 0.02), '#30333c', edge=0)
    panel = solids.box(cv, VIEW, (-0.33, DESK_Y + 0.13, z - 0.04), (0.66, 0.40, 0.03), '#1c1e26', edge=0.3)
    screen = solids.patch(panel['front'], 0.018, 0.03, 0.982, 0.93)
    cv.paste(code_screen(960, 560, '#7fd0ff'), screen)
    return screen


def paint_laptop(cv):
    x0, x1, z0, z1, thick = -0.74, -0.40, 1.48, 1.71, 0.016
    solids.contact_shadow(cv, VIEW, (-0.57, 1.61), DESK_Y, 0.20, 0.15, strength=0.5)
    base = solids.box(cv, VIEW, (x0, DESK_Y, z0), (x1 - x0, thick, z1 - z0), '#b9bdc6', light_from='right')
    cv.paste(keyboard_top(600, 240, '#a4a8b2', '#2a2d36'), solids.patch(base['top'], 0.06, 0.08, 0.94, 0.58))
    cv.fill(cv.polygon(np.array(solids.patch(base['top'], 0.36, 0.66, 0.64, 0.95))), '#a8acb6')
    # Lid: tilted back from the hinge, so its top edge is higher and farther away.
    hinge_y, lid_height, lean = DESK_Y + thick, 0.215, 0.075
    lid = VIEW.quad([(x0, hinge_y + lid_height, z1 + lean), (x1, hinge_y + lid_height, z1 + lean),
                     (x1, hinge_y, z1), (x0, hinge_y, z1)])
    cv.fill(cv.polygon(np.array(lid)), '#22252e')
    screen = solids.patch(lid, 0.035, 0.05, 0.965, 0.92)
    cv.paste(chart_screen(640, 400), screen)
    return screen


def paint_keyboard_and_mouse(cv):
    solids.contact_shadow(cv, VIEW, (0.0, 1.57), DESK_Y, 0.25, 0.09, strength=0.45)
    board = solids.box(cv, VIEW, (-0.23, DESK_Y, 1.50), (0.46, 0.018, 0.145), '#23262e', edge=0.4)
    cv.paste(keyboard_top(760, 250), solids.patch(board['top'], 0.012, 0.03, 0.988, 0.97))
    solids.contact_shadow(cv, VIEW, (0.345, 1.57), DESK_Y, 0.045, 0.065, strength=0.5)
    mouse, (mx, my, mrx, mry) = solids.disc(cv, VIEW, (0.34, 1.57), DESK_Y + 0.014, 0.032, 0.056)
    cv.paint_volume(mouse, '#e4e6ec', LIGHT, bulge=mrx * 0.9, gloss=0.4)
    cv.ink([(mx, my - mry * 0.92), (mx, my - mry * 0.15)], 1.4, '#8a8e9a', 'flat')
    cv.fill(cv.ellipse(mx, my - mry * 0.48, mrx * 0.10, mry * 0.15), '#6a6e7a')


def paint_phone(cv):
    solids.contact_shadow(cv, VIEW, (0.50, 1.44), DESK_Y, 0.07, 0.085, strength=0.45)
    phone = solids.box(cv, VIEW, (0.455, DESK_Y, 1.36), (0.075, 0.008, 0.155), '#15171d', edge=0.5, turn=-28)
    screen = solids.patch(phone['top'], 0.07, 0.04, 0.93, 0.96)
    cv.paste(phone_screen(150, 310), screen)
    return screen


def paint_mug(cv):
    center = (0.62, 1.68)
    solids.contact_shadow(cv, VIEW, center, DESK_Y, 0.055, offset=(-0.03, 0.0), strength=0.55)
    mug = solids.cylinder(cv, VIEW, center, DESK_Y, 0.040, 0.095, '#e06a4a', top_radius=0.043, light=LIGHT, gloss=0.5,
                          hollow='#3a2418')
    tx, ty, trx, _ = mug['top']
    bx, by, brx, _ = mug['bottom']
    drop = by - ty
    handle = cv.ribbon([(tx - trx * 0.9, ty + drop * 0.18), (tx - trx * 1.75, ty + drop * 0.42),
                        (bx - brx * 0.9, ty + drop * 0.78)], trx * 0.30, 'flat')
    cv.paint_volume(handle * (1.0 - mug['mask']), '#e06a4a', LIGHT, bulge=trx * 0.14)
    for index in range(3):                                # steam
        sx = tx + trx * (-0.4 + 0.4 * index)
        wisp = cv.ribbon([(sx, ty - 6), (sx + 8, ty - 30), (sx - 7, ty - 58), (sx + 5, ty - 88)], 6, 'taper')
        cv.tint(blur(wisp, 4), '#ffffff', 'screen', 0.20)


def paint_books(cv):
    solids.contact_shadow(cv, VIEW, (0.62, 2.02), DESK_Y, 0.17, 0.12, strength=0.45)
    y = DESK_Y
    for (dx, width, depth, height, color, turn) in ((0.0, 0.26, 0.19, 0.035, '#3f5f8a', 0.0),
                                                    (0.012, 0.24, 0.18, 0.030, '#c9a23a', 7.0),
                                                    (-0.006, 0.25, 0.185, 0.040, '#a8404a', -9.0)):
        book = solids.box(cv, VIEW, (0.49 + dx, y, 1.93), (width, height, depth), color, light_from='right', edge=0.3,
                          turn=turn)
        page_block = solids.patch(book['front'], 0.02, 0.22, 1.0, 0.78)              # pages show on the fore-edge
        cv.fill(cv.polygon(np.array(page_block)), '#f1ead8', 0.92)
        y += height


def paint_lamp(cv):
    foot, z = (0.93, 2.06), 2.06
    solids.contact_shadow(cv, VIEW, foot, DESK_Y, 0.10, strength=0.5)
    solids.cylinder(cv, VIEW, foot, DESK_Y, 0.080, 0.018, '#2a2c34', light=LIGHT)
    elbow = VIEW.project(0.98, DESK_Y + 0.34, z)
    head = VIEW.project(0.74, DESK_Y + 0.50, z)
    arm = cv.ribbon([VIEW.project(0.93, DESK_Y + 0.02, z), elbow, head], 0.011 * VIEW.scale(z), 'flat', smooth=False)
    cv.paint_volume(arm, '#3a3d48', LIGHT, bulge=3)
    cv.fill(cv.ellipse(elbow[0], elbow[1], 0.02 * VIEW.scale(z)), '#4a4d5a')
    unit = 0.01 * VIEW.scale(z)                           # 1 cm on screen at the lamp
    shade = cv.blob([(head[0] - 3 * unit, head[1] - 6 * unit), (head[0] + 7 * unit, head[1] - 2 * unit),
                     (head[0] + 3 * unit, head[1] + 10 * unit), (head[0] - 15 * unit, head[1] + 7 * unit)], smooth=False)
    cv.paint_volume(shade, '#2f3340', LIGHT, bulge=3 * unit)
    mouth_center = (head[0] - 6 * unit, head[1] + 9 * unit)
    mouth = cv.ellipse(mouth_center[0], mouth_center[1], 9.5 * unit, 2.2 * unit, 9)
    cv.fill(mouth, '#fff3d6' if NIGHT else '#e9e2d0')
    return mouth, mouth_center


def paint_plant(cv):
    center = (-0.86, 2.04)
    solids.contact_shadow(cv, VIEW, center, DESK_Y, 0.09, strength=0.5)
    pot = solids.cylinder(cv, VIEW, center, DESK_Y, 0.058, 0.13, '#e2dccf', top_radius=0.080, light=LIGHT, hollow='#3a2a20')
    tx, ty, trx, _ = pot['top']
    scenery.leaves(cv, (tx, ty - trx * 1.3), trx * 2.0, 38, ('#3f7a5a', '#5a9a66', '#2f5f4a'), trx * 1.4,
                   direction_deg=-90, seed=SEED)


def light_the_scene(cv, desk_top, emitters, lamp_mouth):
    """Night: dim everything that does not emit light, then add each source's pool of light."""
    if not NIGHT:
        cv.tint(cv.radial((150, 150), 1300) ** 1.5, '#fff3d6', 'screen', 0.22)
        return
    glowing = cv.empty()
    for mask in emitters.values():
        glowing = np.maximum(glowing, mask)
    mouth, (mx, my) = lamp_mouth
    # The lamp's pool: things inside it keep their own colors, the rest of the room sinks into blue.
    pool = np.maximum(cv.radial((mx - 100, my + 290), 560, 330), cv.radial((mx - 10, my + 40), 190) * 0.8)
    cv.tint((1.0 - glowing) * (1.0 - 0.8 * pool), '#2f3566', 'multiply', 0.72)
    cv.tint(pool * (1.0 - glowing), '#ffd2a0', 'multiply', 0.30)
    for name, strength, reach in (('monitor', 1.0, 560), ('laptop', 0.6, 380), ('phone', 0.35, 150)):
        rows, columns = np.nonzero(emitters[name] > 0.5)
        center = (columns.mean(), rows.max() + reach * 0.12)
        halo = cv.radial(center, reach, reach * 0.62) ** 1.5 * (1.0 - emitters[name])
        cv.tint(halo, SCREEN_GLOW, 'screen', 0.30 * strength)
    cone = cv.polygon(np.array([(mx - 60, my), (mx + 60, my), (mx + 240, HEIGHT + 40), (mx - 560, HEIGHT + 40)]))
    cv.tint(blur(cone, 40) * cv.radial((mx, my), 700) ** 1.3, LAMP_GLOW, 'screen', 0.13)
    cv.tint(cv.radial((mx, my), 90) * (1.0 - mouth), '#ffe6b8', 'screen', 0.45)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    desk_top, window = paint_room(cv)
    paint_plant(cv)
    lamp_mouth = paint_lamp(cv)
    paint_books(cv)
    monitor = paint_monitor(cv)
    laptop = paint_laptop(cv)
    paint_keyboard_and_mouse(cv)
    paint_mug(cv)
    phone = paint_phone(cv)
    emitters = dict(window=window, lamp=lamp_mouth[0],
                    **{name: cv.polygon(np.array(quad)) for name, quad in
                       (('monitor', monitor), ('laptop', laptop), ('phone', phone))})
    light_the_scene(cv, desk_top, emitters, lamp_mouth)
    image = finish.finish_illustration(cv, glow=0.30 if NIGHT else 0.12, texture=0.025, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
