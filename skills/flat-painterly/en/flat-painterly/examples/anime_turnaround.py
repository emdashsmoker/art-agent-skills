"""Anime style example: turnaround sheet and pose sheet of adult female and male full-body bases (3D rig).

The turnaround rotates one pose through five angles on one sheet: front, 3/4 front, profile, 3/4 back, back.
The pose sheet holds poses where body and head turn separately, such as sitting, walking seen from the side and
looking back over the shoulder.
Process: head-unit guides → 3D rig (figure3d) → masses in the order far limbs, body, near limbs → surface markers →
hands and feet → head (head3d): back hair locks, face, ears, hair cap, front locks.
Adult markers and the groin treatment match anime_figure_base.py and anime_figure_base_male.py.
Torso markers are drawn only where the surface normal faces the viewer and fade toward the edges.
Run: python anime_turnaround.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, io, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.character import FEMALE, MALE, paint_figure  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 2300, 1460
POSE_WIDTH = 2500                # the pose sheet uses a wider frame for the knees of seated poses and the walking stride
UNIT = 148.0                     # head height (logical units)
FLOOR_Y = 1330.0
ELEVATION = 5.0                  # a slightly downward view. The insteps and shoulder tops show
TURNS = (0.0, 45.0, 90.0, 135.0, 180.0)
COLUMN_X = (250.0, 700.0, 1150.0, 1600.0, 2050.0)
STANDING = dict(hip_tilt=0.0, chest_tilt=0.0, spine=0.0, head=0.0, arm_l=(12.0, 6.0), arm_r=(12.0, 6.0),
                leg_l=(4.0, 0.0), leg_r=(4.0, 0.0))


def make_model(look, x, floor_y, turn, head_pitch=0.0, **pose):
    """A figure whose pelvis height puts the lowest foot on floor_y."""
    pose = {**STANDING, **pose}
    lowest = ch.lowest_foot(look, UNIT, turn, ELEVATION, **pose)
    return ch.place(look, (x, floor_y - lowest), UNIT, turn, ELEVATION, head_pitch, **pose)


def paint_paper(cv, pal, guide_model=None, width=WIDTH):
    cv.fill(cv.full(), Linear([pal.paper_top, pal.paper_low], (0, 0), (0, HEIGHT)))
    if guide_model is None:
        return
    # Head-unit guides: 8 units from crown to sole.
    head = guide_model.head
    top = head.frame.point(0.0, -1.0)[1]
    step = (FLOOR_Y - top) / 8.0
    for index in range(9):
        y = top + index * step
        cv.stroke([(60, y), (width - 60, y)], pal.guide, width=1.4, opacity=0.8)


def floor_shadow(cv, model, pal, width=170.0):
    x = model.body.joint("pelvis")[0]
    cv.fill(cv.shape(g.ellipse(x + 18, FLOOR_Y + 4, width, 22), soft=10), "#9aa4c0", opacity=0.45)


def render_turnaround(look, out_dir, scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    models = [make_model(look, x, FLOOR_Y, turn) for x, turn in zip(COLUMN_X, TURNS)]
    paint_paper(cv, look.palette, models[0])
    for model in models:
        floor_shadow(cv, model, look.palette)
        paint_figure(cv, model)
    image = anime.finish(cv, diffusion=0.08, bloom=0.0, grade_amount=0.04, aberration=0.0, grain=0.01)
    return io.save(post.vignette(image, strength=0.05), out_dir / f"anime_turnaround_{look.sex.value}.png")


# Pose sheet: (look, screen x, body turn, chair, head bow, pose). The chair is a box in pelvis coordinates (x,
# y, z ranges), or None.
SEAT = ((-0.95, 0.95), (0.44, None), (-1.25, 0.55))
POSES = (
    # Seated woman seen 3/4 front: both hands on the thighs, face turned a little more toward the viewer.
    (FEMALE, 360.0, 35.0, SEAT, 4.0, dict(lean=6.0, head=3.0, head_turn=-18.0, arm_l=(10.0, -14.0),
                                          arm_r=(8.0, -16.0), leg_l=(2.0, 0.0), leg_r=(2.0, 2.0),
                                          swing={"leg_l": (86.0, 2.0), "leg_r": (90.0, 12.0), "arm_l": (14.0, 62.0),
                                                 "arm_r": (18.0, 66.0)})),
    # Walking man seen from the side: the near leg forward, the far leg with a bent knee and raised heel. The
    # arms swing opposite to the legs.
    (MALE, 1010.0, -90.0, None, 0.0, dict(lean=4.0, arm_l=(6.0, 2.0), arm_r=(6.0, 2.0), leg_l=(2.0, 0.0),
                                        leg_r=(2.0, 0.0), foot_pitch={"l": 24.0},
                                        swing={"leg_r": (24.0, 4.0), "leg_l": (-14.0, -38.0),
                                               "arm_r": (-20.0, -6.0), "arm_l": (22.0, 44.0)})),
    # Woman looking back over her shoulder: body at 3/4 back, head turned to profile. The weight rests on one
    # leg.
    (FEMALE, 1560.0, 155.0, None, -4.0, dict(head_turn=-72.0, hip_tilt=5.0, chest_tilt=-3.0, spine=1.0, head=2.0,
                                             arm_l=(9.0, 4.0), arm_r=(14.0, 8.0), leg_l=(3.0, -1.0),
                                             leg_r=(7.0, 1.0))),
    # Seated man seen from the side: upper body leaning slightly forward, both hands on the knees.
    (MALE, 1990.0, 75.0, SEAT, 8.0, dict(lean=12.0, head=0.0, arm_l=(6.0, -6.0), arm_r=(8.0, -8.0),
                                        leg_l=(4.0, 0.0), leg_r=(6.0, 2.0),
                                        swing={"leg_l": (84.0, 4.0), "leg_r": (80.0, 10.0), "arm_l": (25.0, 60.0),
                                               "arm_r": (22.0, 62.0)})),
)
BLOCK_COLORS = {"top": "#c9d0e2", "side": "#a7b1cb", "front": "#b6bfd6", "line": "#6d7896"}


def paint_seat(cv, model, seat):
    """Box chair. Projected with the same view as the body, painting only the faces toward the viewer."""
    b = model.body
    floor = max(b.joints3["ankle_" + side][1] + 0.46 for side in "lr")
    (x0, x1), (y0, _), (z0, z1) = seat
    corners = {(i, j, k): np.array([(x0, x1)[i], (y0, floor)[j], (z0, z1)[k]]) for i in (0, 1) for j in (0, 1)
               for k in (0, 1)}
    faces = [((0, 0, 1), "top", [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
             ((0, 0, -1), "front", [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]),
             ((0, 0, 1), "front", [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
             ((-1, 0, 0), "side", [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
             ((1, 0, 0), "side", [(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)])]
    normals = {"top": (0.0, -1.0, 0.0)}
    for direction, kind, keys in faces:
        normal = normals.get(kind) if kind == "top" else np.array(direction, np.float64)
        if b.facing(normal) <= 0.0:
            continue
        face = cv.shape(b.project_path(np.array([corners[key] for key in keys])))
        cv.fill(face, BLOCK_COLORS[kind])
        cv.fill(cv.contour(face, 1.6), BLOCK_COLORS["line"])


def render_pose_sheet(out_dir, scale, seed):
    cv = Canvas(POSE_WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_paper(cv, FEMALE.palette, width=POSE_WIDTH)
    cv.stroke([(60, FLOOR_Y + 2), (POSE_WIDTH - 60, FLOOR_Y + 2)], FEMALE.palette.guide, width=1.4, opacity=0.8)
    for look, x, turn, seat, head_pitch, pose in POSES:
        model = make_model(look, x, FLOOR_Y, turn, head_pitch=head_pitch, **pose)
        floor_shadow(cv, model, look.palette, width=230.0 if seat else 170.0)
        if seat:
            paint_seat(cv, model, seat)
        paint_figure(cv, model)
    image = anime.finish(cv, diffusion=0.08, bloom=0.0, grade_amount=0.04, aberration=0.0, grain=0.01)
    return io.save(post.vignette(image, strength=0.05), out_dir / "anime_pose_sheet.png")


def main(out_dir="out", scale=1.0, seed=73):
    out_dir = Path(out_dir)
    return [render_turnaround(look, out_dir, scale, seed) for look in (FEMALE, MALE)] \
        + [render_pose_sheet(out_dir, scale, seed)]


if __name__ == "__main__":
    arguments = sys.argv[1:]
    for path in main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0):
        print(path)
