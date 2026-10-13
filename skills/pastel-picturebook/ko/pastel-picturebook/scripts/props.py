"""Scene props that several figures share: a bench they sit on side by side, a café table between them.

The scene (render.resolve_props) measures the figures that use a prop and passes its geometry,
in pixels of the finished picture, to the figure painted first; that figure paints it right after
its background, so every figure is painted in front of it.

  bench  seat board seen a little from above, front board, legs, an optional backrest of two
         slats on posts; it spans the hips of every figure seated facing us
  table  a round café table seen from the side at eye height above it: the top as a flat
         ellipse with a rim, a pedestal and a round foot; it stands between figures seen in profile
"""
import numpy as np

import kit
from raster import ellipse, fill, mix, over, rgb, screen, stroke

# Bench (head units of the seated figures): seat behind the hips and in front of the knees as in
# subject_figure.paint_seat, overhang past the outer hips, board and leg sizes, backrest.
BENCH = {"back": 0.75, "front": 0.35, "foot": 0.20, "overhang": 2.0, "board": 0.45, "leg": 0.28, "rest_height": 3.4,
         "slat": 0.55, "slat_gap": 0.45, "post": 0.30}
# Table (head units of the figures beside it): top radius, apparent depth of the top (share of the radius),
# rim thickness, pedestal and foot.
TABLE = {"radius": 2.7, "tilt": 0.16, "rim": 0.22, "pole": 0.16, "foot": 1.2, "foot_tilt": 0.18}


def flip_x(points, width, mirror):
    """Picture-space points into the painting figure's own orientation (flipped when it is mirrored)."""
    points = np.array(points, np.float64)
    if mirror:
        points[..., 0] = width - points[..., 0]
    return points


def quad(scene, corners, tone, opacity, group):
    mask = fill(scene.size, np.asarray(corners, np.float64))
    over(scene.image, tone, mask, opacity)
    kit.ink_edges(scene, mask, 1.8, group, "line")
    return mask


def paint_bench(scene, geo, mirror):
    """A long bench under figures seated facing us; geometry from render.bench_geometry."""
    tones = scene.style["palette"].get("seat", scene.style["palette"]["shoe"])
    width = scene.size[1]
    unit = geo["unit"]
    x0, x1 = sorted(flip_x([[geo["x0"], 0], [geo["x1"], 0]], width, mirror)[:, 0])
    back_y, front_y, floor_front = geo["back_y"], geo["front_y"], geo["floor_front"]
    floor_back = floor_front - (front_y - back_y)
    board, leg, narrow = BENCH["board"] * unit, BENCH["leg"] * unit, 0.04 * (x1 - x0)
    if geo.get("backrest", True):
        top = back_y - BENCH["rest_height"] * unit
        for x in (x0 + narrow + 0.3 * unit, x1 - narrow - 0.3 * unit - BENCH["post"] * unit):
            quad(scene, [(x, top), (x + BENCH["post"] * unit, top), (x + BENCH["post"] * unit, back_y), (x, back_y)],
                 rgb(tones["shadow"]), 1.0, "seat")
        for k in range(2):
            y = top + k * (BENCH["slat"] + BENCH["slat_gap"]) * unit
            quad(scene, [(x0 + narrow, y), (x1 - narrow, y), (x1 - narrow, y + BENCH["slat"] * unit), (x0 + narrow, y + BENCH["slat"] * unit)],
                 rgb(tones["base"]), 1.0, "seat")
    for x in (x0 + narrow + 0.25 * unit, x1 - narrow - 0.25 * unit - leg):
        quad(scene, [(x, back_y + board), (x + leg, back_y + board), (x + leg, floor_back), (x, floor_back)], rgb(tones["shadow"]), 0.9, "seat")
    quad(scene, [(x0 + narrow, back_y), (x1 - narrow, back_y), (x1, front_y), (x0, front_y)], rgb(tones["light"]), 1.0, "seat")
    quad(scene, [(x0, front_y), (x1, front_y), (x1, front_y + board), (x0, front_y + board)], rgb(tones["base"]), 1.0, "seat")
    for x in (x0 + 0.15 * unit, x1 - 0.15 * unit - leg):
        quad(scene, [(x, front_y + board), (x + leg, front_y + board), (x + leg, floor_front), (x, floor_front)], rgb(tones["base"]), 1.0, "seat")
    cast = scene.style["palette"].get("floor", {}).get("cast", tones["shadow"])
    kit.ground_shadow(scene, ((x0 + x1) / 2, floor_front - 0.1 * unit), (x1 - x0) * 0.52, 0.30 * unit, cast, 0.45, 0.12)


def paint_table(scene, geo, mirror):
    """A round café table seen from the side, a little from above; geometry from render.table_geometry."""
    tones = scene.style["palette"]["table"]
    width = scene.size[1]
    unit = geo["unit"]
    x = flip_x([[geo["x"], 0]], width, mirror)[0, 0]
    top_y, floor = geo["top_y"], geo["floor"]
    radius = geo.get("radius", TABLE["radius"]) * unit
    depth = radius * TABLE["tilt"]
    foot = TABLE["foot"] * unit
    cast = scene.style["palette"].get("floor", {}).get("cast", tones["shadow"])
    kit.ground_shadow(scene, (x, floor), radius * 0.95, depth * 1.2, cast, 0.40, 0.10)
    foot_mask = fill(scene.size, ellipse((x, floor - foot * TABLE["foot_tilt"] * 0.5), foot, foot * TABLE["foot_tilt"], 40))
    over(scene.image, rgb(tones["metal"]), foot_mask)
    kit.ink_edges(scene, foot_mask, 1.6, "table", "line")
    pole = stroke(scene.size, np.array([[x, top_y + depth], [x, floor - foot * TABLE["foot_tilt"]]]), TABLE["pole"] * unit)
    over(scene.image, rgb(tones["metal"]), pole)
    if scene.shade_on:
        over(scene.image, mix(rgb(tones["metal"]), np.zeros(3, np.float32), 0.35), pole * (np.arange(scene.size[1])[None, :] > x), 0.6)
    kit.ink_edges(scene, pole, 1.4, "table", "line")
    rim_thick = TABLE["rim"] * unit
    side = fill(scene.size, np.vstack([ellipse((x, top_y + rim_thick), radius, depth, 48)[24:], ellipse((x, top_y), radius, depth, 48)[:25][::-1]]))
    edge = np.maximum(side, fill(scene.size, ellipse((x, top_y + rim_thick), radius, depth, 48)))
    over(scene.image, rgb(tones["shadow"]), edge)
    top = fill(scene.size, ellipse((x, top_y), radius, depth, 48))
    over(scene.image, rgb(tones["base"]), top)
    if scene.shade_on:
        shine = fill(scene.size, ellipse((x - radius * 0.3, top_y - depth * 0.2), radius * 0.35, depth * 0.35, 32))
        screen(scene.image, rgb(tones["light"]), scene.soften(shine, 0.3) * top, 0.35)
    kit.ink_edges(scene, np.maximum(top, edge), 1.8, "table", "line")
    for cup in geo.get("cups", []):
        paint_cup_on(scene, flip_x([[cup, 0]], width, mirror)[0, 0], top_y, unit, depth)


def paint_cup_on(scene, x, top_y, unit, depth):
    """A small cup and saucer standing on the table top."""
    tones = scene.style["palette"].get("cup", scene.style["palette"]["table"])
    saucer = fill(scene.size, ellipse((x, top_y), 0.55 * unit, 0.12 * unit, 32))
    over(scene.image, rgb(tones["shadow"]), saucer)
    body = fill(scene.size, np.array([[x - 0.32 * unit, top_y - 0.62 * unit], [x + 0.32 * unit, top_y - 0.62 * unit],
                                      [x + 0.26 * unit, top_y - 0.05 * unit], [x - 0.26 * unit, top_y - 0.05 * unit]]))
    over(scene.image, rgb(tones["base"]), body)
    handle = stroke(scene.size, np.array([[x + 0.30 * unit, top_y - 0.50 * unit], [x + 0.52 * unit, top_y - 0.38 * unit],
                                          [x + 0.29 * unit, top_y - 0.22 * unit]]), 0.07 * unit)
    over(scene.image, rgb(tones["base"]), handle)
    kit.ink_edges(scene, np.maximum.reduce([saucer, body, handle]), 1.3, "table", "line")


PAINTERS = {"bench": paint_bench, "table": paint_table}


def paint_scene_props(scene):
    """Paint the props the scene handed to this figure (it is painted first), in their order."""
    props = scene.fig.spec.get("scene_props") or []
    mirror = scene.fig.spec.get("pose", {}).get("mirror", False)
    for geo in props:
        PAINTERS[geo["kind"]](scene, geo, mirror)
