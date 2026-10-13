"""A woman working at a laptop by a café window, as an urban sketch: ink line over loose watercolour.

The café is a room built with Perspective.room; its front is a glass wall cut out of the back wall, so the
street outside (painted first) shows through it. She sits behind a small table; the table, laptop, mug and
plant are drawn after her so they overlap her lap and hands the way they would in life.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, city, geom, light as make_light, objects as ob, props, scenery as sc, studio
from atelier import wardrobe as w

brief = Brief.from_answers(subject="scene", style="urban_sketch", format="landscape", framing="full",
                           composition="thirds_right", view="profile", pose="sit", lighting="soft_front",
                           background="interior", mood="calm", hair_style="bun", fringe="wispy", hair_color="#5a3a2a",
                           eye_color="#5a4030", expression="gentle", message="an afternoon absorbed in work at a window seat", seed=41)
OUTSIDE = ["#d8c4a8", "#b9c4c8", "#e0d2c0", "#c8b0a0", "#aebcb0"]
WINDOW = (0.05, 0.08, 0.95, 0.93)                  # glass front in back-wall (u, v) coordinates
MULLIONS = (0.05, 0.35, 0.65, 0.95)


def street_outside(canvas, camera, light):
    """The street across the glass: pavement, a row of shop houses and two street trees."""
    sc.sky(canvas, "#9fb8d0", "#eef0ea", camera.horizon_y)
    with canvas.layer(depth=0.8):
        canvas.add(camera.ground_quad(-40, 40, 6.0, 30), "#b8b0a4", "street", normal=(0, -1, 0.05))
        canvas.add(camera.ground_quad(-40, 40, 8.0, 12.5), "#8e8c90", "street", normal=(0, -1, 0.05))
    for i, x in enumerate(range(-22, 22, 7)):
        city.building(camera, x, 15.0, 7.0, 6.0, [9.0, 12.0, 8.0, 11.0, 10.0, 13.0][i % 6], OUTSIDE[i % len(OUTSIDE)],
                      kind=["apartment", "old", "house"][i % 3], light=light, sky="#cfdce8",
                      awning=["#4f7a6a", None, "#a8574a"][i % 3], seed=i)
    for x in (-3.0, 4.5):
        city.tree(camera, x, 13.0, height=5.5)
    city.pedestrian(camera, -1.4, 13.6, color="#4a4f5a", seed=3)
    city.pedestrian(camera, 2.2, 13.8, color="#7a5a48", seed=4)


def build(canvas, light, brief):
    light = make_light("soft_front", azimuth=-48, elevation=28, color="#fff3e2", wrap=0.35)
    ob.use_light(light)
    W, H = canvas.width, canvas.height
    camera = sc.Perspective(canvas, H * 0.4, eye=1.15, focal=1.2, centre_x=W * 0.46)
    street_outside(canvas, camera, light)
    faces = camera.room(-3.4, 3.4, 0.3, 5.6, 3.1, wall="#efe4d2", floor="#a8805c", ceiling="#f2ebe0",
                        openings={"back": [WINDOW]}, scene_depth=0.6)
    back = faces["back"]
    u0, v0, u1, v1 = WINDOW

    def panel(a0, b0, a1, b1):
        return geom.polygon([back(a0, b0), back(a1, b0), back(a1, b1), back(a0, b1)])

    canvas.tint(panel(u0, v0, u1, v1), "#d6e6ee", alpha=0.18)          # a faint cool cast on the glass
    with canvas.layer(depth=0.55):
        for u in MULLIONS:                          # window frame: posts and a transom
            canvas.add(panel(u - 0.006, v0, u + 0.006, v1), "#3c3f44", "frame", normal=(0, 0, 1))
        for v in (v0, 0.72, v1):
            canvas.add(panel(u0, v - 0.008, u1, v + 0.008), "#3c3f44", "frame", normal=(0, 0, 1))
    for lamp_x in (-1.6, 1.4):                      # pendant lamps over the tables
        top, bulb = camera.point(lamp_x, 3.1, 3.2), camera.point(lamp_x, 2.35, 3.2)
        size = 0.32 * camera.scale(3.2)
        canvas.stroke([top, bulb], 1.2, "#2a2a2e")
        with canvas.layer(depth=0.5):
            canvas.add(_lamp_shade(bulb, size), "#2f4a44", "lamp", form="round", outline=1.0)
            canvas.add(geom.ellipse(bulb[0], bulb[1] + size * 0.04, size * 0.16, size * 0.1), "#fff1cc", "lamp", unlit=True)

    # ---- a bistro table and what stands on it, then her: her hands rest on the keyboard in front of it ----
    top_y, table_x, table_z, radius = 0.74, -0.1, 3.0, 0.46

    def disc(y, r):
        return camera.quad([(table_x + r * np.cos(a), y, table_z + r * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 40)[:-1]])

    def table(top_only=False, clip=None):
        """The whole table, or with top_only just its top: the one part that passes in front of her lap."""
        with canvas.layer(depth=0.32):
            if not top_only:
                canvas.add(disc(0.01, 0.22), "#3a3430", "table_leg", normal=(0, -1, 0.05), outline=0.8)
                camera.box(table_x - 0.03, table_z - 0.03, 0.06, 0.06, top_y - 0.03, "#3a3430", region="table_leg",
                           outline=0.8)
            canvas.add(disc(top_y - 0.03, radius), "#8a6440", "table", outline=1.0, clip=clip)
            canvas.add(disc(top_y, radius), "#c49a6a", "table", normal=(0, -1, 0.1), outline=1.0, clip=clip)

    table()
    lx, ly = camera.point(0.1, top_y, 2.9)
    props.laptop(canvas, lx, ly, 0.33 * camera.scale(2.9), color="#b8bcc4", screen_kind="code", yaw=-75)
    mx, my = camera.point(-0.17, top_y, 2.7)
    props.mug(canvas, mx, my, 0.085 * camera.scale(2.7), color="#f2ece2", inside="#4a2a1a", handle="left")
    px, py = camera.point(-0.44, top_y, 3.22)
    props.plant(canvas, px, py, 0.1 * camera.scale(3.22), seed=2)
    seat_x, seat_z = 0.62, 3.0
    scale = camera.scale(seat_z)
    camera.chair(seat_x - 0.3, seat_z, back_side="right", color="#5a3e2c", outline=1.0, scene_depth=0.35)
    foot_x, foot_y = camera.point(seat_x - 0.25, 0.0, seat_z)
    figure = Figure(pose="sit", turn=-68, heads=7.6)
    figure.set_pose(head=(12, 6, 0), chest=(8, 0, 0))
    for side in ("r", "l"):                          # both hands rest on the keyboard, just above the table top
        figure.reach(side, (0.26, 5.78, 1.7), anchor="chest")
    character = brief.character(figure, hair=Hair("bun", "wispy", brief.hair_color, seed=brief.seed),
                                outfit=[w.top("#e9eef2", "long", neck=6.62, ease=0.03, detail=w.collar(buttons=4)),
                                        w.pants("#4a5468"), w.shoes("#3a2e28")])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, foot_x, ground_y=foot_y, height=1.66 * scale, light=light)
    table(top_only=True, clip=view.group_mask("pants"))      # her lap and knees are under the table top
    return {"views": [view], "light": light}


def _lamp_shade(centre, size):
    """A cone lamp shade hanging with its mouth down over the bulb at `centre`."""
    x, y = centre
    return geom.polygon([(x - size * 0.18, y - size * 0.55), (x + size * 0.18, y - size * 0.55), (x + size * 0.5, y),
                         (x - size * 0.5, y)])


if __name__ == "__main__":
    studio.run(build, brief, "scene_cafe_window.png")
