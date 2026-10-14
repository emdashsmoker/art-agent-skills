"""Example: a modern still life: a desk at night with a monitor, laptop, keyboard, phone, mug, lamp and plant.

Shows how machine-made objects are built: every box is three flat faces placed with an
oblique projection, and screens, keys and icons are laid on a face through a quad mapping.

Usage: python examples/desk.py --style illust|anime|painterly --out desk.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop, fx, geometry as geo, objects, scenery, shading as sh
from codepainter.color import mix, shadow_of
from codepainter.styles import finish, get_style, gloss, paint_part

WIDTH, HEIGHT = 1280, 960
LIGHT = (-0.5, -0.6, 0.6)
WALL_TOP, WALL_LOW = "#26324a", "#141a2a"
WOOD = "#8a6242"
ALUMINIUM, PLASTIC_DARK, SCREEN_OFF = "#b9bfc8", "#2a2e38", "#10141e"
EDITOR_BG = "#18203a"
CODE_COLORS = ["#7fd1ff", "#ffcf7a", "#c79bff", "#8ee6a8", "#f08a9a", "#d8deea"]
LAMP_LIGHT = "#ffd9a0"
SCREEN_LIGHT = "#8fc0ff"
DESK = geo.Oblique(origin=(70, 850), across=(1.0, 0.07), back=(0.50, -0.36))      # desk units are pixels at the front edge


def drop_shadow(painting, mask, desk_top, offset=(22, 9), strength=0.55, softness=5.0):
    """Shadow of an object on the desk, thrown to the right, away from the lamp side of the scene."""
    painting.fill(sh.cast_shadow(mask, desk_top, offset, softness) * (1.0 - mask), "#1a1626", strength, "multiply")


def paint_room(painting, style):
    backdrop.gradient(painting, WALL_TOP, WALL_LOW, start=(0, 0), end=(WIDTH, HEIGHT * 0.7))
    backdrop.mottle(painting, "#32405e", amount=0.25, scale=0.9, seed=2)
    # a window onto the night city: skyline, lit dots, then the frame
    x0, y0, x1, y1 = 60, 50, 420, 370
    pane = painting.mask(np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], dtype=float))
    painting.fill(pane, "#0e1630")
    painting.fill(pane * sh.linear_ramp(painting.shape, (0, y0), (0, y1)), "#3a2f5e", 0.8)
    city = painting.mask(scenery.skyline(painting.shape, y1 - 30, heights=(30, 190), widths=(26, 70), seed=5)) * pane
    painting.fill(city, "#0a0f20")
    rng = np.random.default_rng(6)
    for _ in range(170):
        x, y = rng.uniform(x0, x1), rng.uniform(y0 + 110, y1)
        painting.fill(painting.mask(geo.ellipse((x, y), 2.2, 2.2, count=8)) * city, ["#ffd98a", "#ffb070", "#bfe0ff"][rng.integers(3)], 0.9)
    for bar in ([(x0 - 12, y0 - 12), (x1 + 12, y0 - 12), (x1 + 12, y0), (x0 - 12, y0)], [(x0 - 12, y1), (x1 + 12, y1), (x1 + 12, y1 + 14), (x0 - 12, y1 + 14)],
                [(x0 - 12, y0), (x0, y0), (x0, y1), (x0 - 12, y1)], [(x1, y0), (x1 + 12, y0), (x1 + 12, y1), (x1, y1)],
                [((x0 + x1) / 2 - 5, y0), ((x0 + x1) / 2 + 5, y0), ((x0 + x1) / 2 + 5, y1), ((x0 + x1) / 2 - 5, y1)]):
        paint_part(painting, np.array(bar, dtype=float), "#3a4258", style, LIGHT, line_width=1.5, shade=False)
    desk = objects.paint_box(painting, DESK.box(0, 0, -40, 1120, 600, 40), WOOD, style, line_width=2.5)
    grain = geo.quad_map(DESK.box(0, 0, -40, 1120, 600, 40)["top"])
    for v in np.linspace(0.12, 0.9, 6):                                   # long wood grain lines on the top
        painting.stroke(grain([(0.02, v), (0.5, v + 0.01), (0.98, v)]), 1.6, shadow_of(WOOD), taper=(0.2, 0.2), opacity=0.35,
                        layer="color", clip=desk["top"])
    return desk["top"]


def paint_screen(painting, quad, seed, lines=13, sidebar=True):
    """A code editor on any screen quad: dark page, side bar, title bar, coloured lines of text."""
    mapping = geo.quad_map(quad)
    display = painting.mask(mapping(geo.rounded_rect(0.025, 0.035, 0.975, 0.945, 0.02)))
    painting.fill(display, EDITOR_BG)
    painting.fill(painting.mask(mapping([(0.025, 0.035), (0.975, 0.035), (0.975, 0.10), (0.025, 0.10)])) * display, "#232d4d")
    for k, color in enumerate(("#f0625a", "#f5c04a", "#5ed06a")):          # window buttons
        painting.fill(painting.mask(mapping(geo.ellipse((0.055 + k * 0.03, 0.068), 0.009, 0.014, count=12))), color)
    left = 0.06
    if sidebar:
        painting.fill(painting.mask(mapping([(0.025, 0.10), (0.20, 0.10), (0.20, 0.945), (0.025, 0.945)])) * display, "#1f2844")
        left = 0.24
    rng = np.random.default_rng(seed)
    for row in range(lines):
        v = 0.15 + row * (0.76 / lines)
        indent = rng.integers(0, 4) * 0.035
        cursor = left + indent
        for _ in range(rng.integers(1, 5)):                                # each line is a few coloured words
            length = rng.uniform(0.04, 0.16)
            if cursor + length > 0.94:
                break
            word = mapping([(cursor, v), (cursor + length, v), (cursor + length, v + 0.026), (cursor, v + 0.026)])
            painting.fill(painting.mask(word) * display, CODE_COLORS[rng.integers(len(CODE_COLORS))], 0.9)
            cursor += length + 0.02
        if sidebar and row % 2 == 0:
            width = rng.uniform(0.06, 0.12)
            entry = mapping([(0.05, v), (0.05 + width, v), (0.05 + width, v + 0.022), (0.05, v + 0.022)])
            painting.fill(painting.mask(entry) * display, "#7f8fb8", 0.7)
    shine = painting.mask(mapping([(0.55, 0.035), (0.80, 0.035), (0.55, 0.945), (0.30, 0.945)])) * display
    painting.fill(shine, "#ffffff", 0.05)                                  # a faint diagonal reflection on the glass
    return display


def paint_monitor(painting, style, desk_top):
    base = objects.paint_box(painting, DESK.box(490, 420, 0, 180, 100, 10), ALUMINIUM, style)
    drop_shadow(painting, base["all"], desk_top, offset=(12, 5))
    objects.paint_box(painting, DESK.box(563, 455, 10, 34, 16, 150), ALUMINIUM, style)
    body = objects.paint_box(painting, DESK.box(340, 450, 130, 480, 26, 300), PLASTIC_DARK, style)
    return paint_screen(painting, DESK.box(340, 450, 130, 480, 26, 300)["front"], seed=3), body["all"]


def paint_laptop(painting, style, desk_top):
    faces = DESK.box(30, 150, 0, 290, 200, 12)
    base = objects.paint_box(painting, faces, ALUMINIUM, style)
    drop_shadow(painting, base["all"], desk_top)
    deck = geo.quad_map(faces["top"])
    for cell in geo.grid_cells(12, 4, margin=0.14, inset=(0.06, 0.08, 0.94, 0.58)):          # keys
        painting.fill(painting.mask(deck(cell)), "#3a3f4c")
    painting.fill(painting.mask(deck(geo.rounded_rect(0.36, 0.66, 0.64, 0.94, 0.02))), shadow_of(ALUMINIUM), 0.5)   # trackpad
    lid = DESK.place([(30, 392, 205), (320, 392, 205), (320, 350, 12), (30, 350, 12)])          # the lid leans back from its hinge
    lid_mask = paint_part(painting, lid, PLASTIC_DARK, style, LIGHT, line_width=2.2, shade=False)
    return paint_screen(painting, lid, seed=9, lines=9, sidebar=False), np.maximum(base["all"], lid_mask)


def paint_keyboard_and_mouse(painting, style, desk_top):
    faces = DESK.box(410, 150, 0, 390, 130, 14)
    board = objects.paint_box(painting, faces, "#d8dbe0", style)
    drop_shadow(painting, board["all"], desk_top)
    keys = geo.quad_map(faces["top"])
    for index, cell in enumerate(geo.grid_cells(15, 5, margin=0.13, inset=(0.03, 0.07, 0.97, 0.93))):
        corner = cell[0]
        key = keys(geo.rounded_rect(corner[0], corner[1], cell[2][0], cell[2][1], 0.006))
        accent = index in (0, 14, 60, 74)                                   # a few coloured keys break the grid
        painting.fill(painting.mask(key), "#e8734a" if accent else "#f6f7f9")
    spot = DESK.place([(880, 215, 0)])[0]
    mouse = geo.ellipse(spot - [0, 12], 40, 25, angle=-0.42, count=48)
    drop_shadow(painting, painting.mask(mouse), desk_top, offset=(14, 8))
    mask = paint_part(painting, mouse, "#eceef2", style, LIGHT, line_width=2.2)
    gloss(painting, mask, LIGHT, size=0.14, softness=0.4, opacity=0.6)
    painting.stroke(geo.bent_line(spot + [-22, -30], spot + [4, -14], 0.1), 1.6, "#9aa0ac", taper=(0.1, 0.5), layer="color", clip=mask)


def paint_phone(painting, style, desk_top):
    faces = DESK.box(960, 60, 0, 84, 165, 8)
    phone = objects.paint_box(painting, faces, "#1c1f28", style, line_width=1.8)
    drop_shadow(painting, phone["all"], desk_top, offset=(10, 5))
    glass = geo.quad_map(faces["top"])
    screen = painting.mask(glass(geo.rounded_rect(0.06, 0.04, 0.94, 0.96, 0.07)))
    painting.fill(screen, "#2a3560")
    painting.fill(screen * sh.linear_ramp(painting.shape, *glass([(0.5, 0.0), (0.5, 1.0)])), "#6a4a8a", 0.8)      # wallpaper
    for cell in geo.grid_cells(4, 5, margin=0.2, inset=(0.12, 0.30, 0.88, 0.92)):            # app icons
        corner = cell[0]
        icon = glass(geo.rounded_rect(corner[0], corner[1], cell[2][0], cell[2][1], 0.02))
        painting.fill(painting.mask(icon) * screen, CODE_COLORS[int(corner[0] * 40 + corner[1] * 17) % len(CODE_COLORS)], 0.9)
    painting.fill(painting.mask(glass([(0.30, 0.12), (0.70, 0.12), (0.70, 0.20), (0.30, 0.20)])) * screen, "#ffffff", 0.85)  # clock


def paint_mug(painting, style, desk_top):
    foot = DESK.place([(850, 345, 0)])[0]
    handle = geo.tube(geo.smooth([foot + [34, -64], foot + [70, -58], foot + [68, -24], foot + [34, -18]]), [8, 8, 8], caps=(False, False))
    paint_part(painting, handle, "#e9e3d6", style, LIGHT, line_width=2.0, bevel=6)
    mug = objects.paint_cylinder(painting, foot, 40, 78, "#e9e3d6", style, LIGHT, hollow="#3b2416")
    drop_shadow(painting, mug["body"], desk_top, offset=(16, 6))
    for k, dx in enumerate((-10, 12)):
        steam = geo.smooth([foot + [dx, -92], foot + [dx + 12, -130], foot + [dx - 10, -170], foot + [dx + 6, -215]])
        painting.stroke(steam, 8, "#dfe8ff", taper=(0.3, 0.6), opacity=0.35, layer="color")


def paint_lamp(painting, style, desk_top):
    foot = DESK.place([(1020, 360, 0)])[0]
    base = objects.paint_cylinder(painting, foot, 46, 12, "#30343f", style, LIGHT)
    drop_shadow(painting, base["body"], desk_top, offset=(12, 5))
    elbow, head = foot + [22, -300], foot + [-120, -392]
    for a, b in ((foot + [0, -12], elbow), (elbow, head)):
        arm = geo.tube([a, b], [6, 6], caps=(True, True))
        paint_part(painting, arm, "#3a3f4c", style, LIGHT, line_width=1.8, bevel=4)
    shade = np.array([head + [-26, -22], head + [30, 4], head + [8, 78], head + [-92, 34]])
    paint_part(painting, shade, "#e2a03a", style, LIGHT, line_width=2.2, shade=False)
    painting.fill(painting.mask(geo.ellipse(head + [-42, 58], 46, 16, angle=0.45)), "#fff3c8")           # the lit mouth of the shade
    pool = DESK.place([(700, 300, 0)])[0]
    backdrop.glow(painting, pool, 330, LAMP_LIGHT, opacity=0.42)                                       # light pooling on the desk
    backdrop.glow(painting, head + [-42, 58], 150, LAMP_LIGHT, opacity=0.55)


def paint_plant(painting, style, desk_top):
    foot = DESK.place([(95, 500, 0)])[0]
    pot = objects.paint_cylinder(painting, foot, 50, 74, "#b5633c", style, LIGHT, hollow="#3a2a20")
    drop_shadow(painting, pot["body"], desk_top, offset=(16, 6))
    rng = np.random.default_rng(4)
    leaf = "#3f7a4a"
    for angle in np.linspace(-1.25, 1.25, 9):                               # long leaves fanning up out of the pot
        length = rng.uniform(150, 230)
        tip = foot + [np.sin(angle) * length, -74 - np.cos(angle) * length]
        blade = geo.lock(foot + [-8, -76], foot + [8, -76], tip, bend=0.25 * np.sign(angle) * rng.uniform(0.5, 1.2), belly=1.6)
        mask = paint_part(painting, blade, mix(leaf, "#7fb85a", rng.uniform(0, 0.5)), style, LIGHT, line_width=1.6, bevel=8)
        painting.stroke(geo.bent_line(foot + [0, -76], tip, 0.25 * np.sign(angle)), 1.4, shadow_of(leaf), taper=(0.1, 0.6),
                        opacity=0.6, layer="color", clip=mask)


def paint_notebook(painting, style, desk_top):
    faces = DESK.box(520, 10, 0, 220, 120, 8)
    book = objects.paint_box(painting, faces, "#e9dfc8", style, line_width=1.8)
    drop_shadow(painting, book["all"], desk_top, offset=(10, 5))
    page = geo.quad_map(faces["top"])
    for v in np.linspace(0.18, 0.86, 7):
        painting.stroke(page([(0.08, v), (0.92 - 0.3 * (v > 0.7), v)]), 1.4, "#8a93a8", taper=(0, 0), opacity=0.7, layer="color")
    pen = geo.tube(DESK.place([(560, 100, 10), (700, 40, 10)]), [5, 5, 3], caps=(True, True))
    paint_part(painting, pen, "#c8453a", style, LIGHT, line_width=1.6, bevel=4)


def render(style_name, seed=0):
    style = get_style(style_name)
    painting = Painting(WIDTH, HEIGHT)
    desk_top = paint_room(painting, style)
    painting.snapshot("1 room and desk")
    paint_plant(painting, style, desk_top)                     # back row first
    monitor, _ = paint_monitor(painting, style, desk_top)
    painting.snapshot("2 back row")
    paint_mug(painting, style, desk_top)
    paint_lamp(painting, style, desk_top)
    laptop, _ = paint_laptop(painting, style, desk_top)
    paint_keyboard_and_mouse(painting, style, desk_top)
    paint_phone(painting, style, desk_top)
    paint_notebook(painting, style, desk_top)
    painting.snapshot("3 front row")
    # screens are light sources: a cool glow spills from each onto wall and desk
    for display in (monitor, laptop):
        painting.fill(sh.blur(display, 46) * (1.0 - display), SCREEN_LIGHT, 0.35, "screen")
    image = finish(painting, style, seed=seed, importance=np.clip(monitor + laptop, 0, 1), detail=1.2)
    painting.stages["4 finish"] = image
    return painting, image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="illust", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="desk.png")
    parser.add_argument("--sheet", default=None)
    args = parser.parse_args()
    painting, image = render(args.style)
    painting.save(args.out, image)
    if args.sheet:
        fx.stage_sheet(painting.stages, args.sheet, columns=4)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
