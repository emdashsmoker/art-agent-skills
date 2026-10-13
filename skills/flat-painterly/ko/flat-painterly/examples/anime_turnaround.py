"""애니메풍 예제: 성인 남녀 전신 베이스의 턴어라운드 시트와 포즈 시트(3차원 리그).

턴어라운드는 같은 자세를 정면, 3/4 앞, 옆, 3/4 뒤, 뒷면 다섯 각도로 돌려 한 장에 놓는다.
포즈 시트는 앉기, 옆에서 본 걷기, 어깨 너머로 돌아보기처럼 몸과 머리가 따로 도는 자세를 담는다.
공정: 머리 단위 안내선 → 3차원 리그(figure3d) → 먼 팔다리, 몸, 가까운 팔다리 순서의 덩어리 → 겉면 표지
→ 손과 발 → 머리(head3d): 뒷머리 다발, 얼굴, 귀, 머리 덮개, 앞머리 다발.
성인 표지와 사타구니 처리는 anime_figure_base.py, anime_figure_base_male.py와 같다.
몸통 표지는 겉면 점의 법선이 관찰자를 향할 때만 그리고 가장자리로 갈수록 흐리게 한다.
실행: python anime_turnaround.py [출력폴더] [scale]
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
POSE_WIDTH = 2500                # 포즈 시트는 앉은 자세의 무릎과 걷는 보폭이 넓어 화면을 더 넓게 쓴다
UNIT = 148.0                     # 머리 높이(논리 단위)
FLOOR_Y = 1330.0
ELEVATION = 5.0                  # 살짝 내려다보는 시선. 발등과 어깨 윗면이 보인다
TURNS = (0.0, 45.0, 90.0, 135.0, 180.0)
COLUMN_X = (250.0, 700.0, 1150.0, 1600.0, 2050.0)
STANDING = dict(hip_tilt=0.0, chest_tilt=0.0, spine=0.0, head=0.0, arm_l=(12.0, 6.0), arm_r=(12.0, 6.0),
                leg_l=(4.0, 0.0), leg_r=(4.0, 0.0))


def make_model(look, x, floor_y, turn, head_pitch=0.0, **pose):
    """가장 낮은 발이 floor_y에 닿도록 골반 높이를 정한 인물."""
    pose = {**STANDING, **pose}
    lowest = ch.lowest_foot(look, UNIT, turn, ELEVATION, **pose)
    return ch.place(look, (x, floor_y - lowest), UNIT, turn, ELEVATION, head_pitch, **pose)


def paint_paper(cv, pal, guide_model=None, width=WIDTH):
    cv.fill(cv.full(), Linear([pal.paper_top, pal.paper_low], (0, 0), (0, HEIGHT)))
    if guide_model is None:
        return
    # 머리 단위 안내선: 정수리에서 발바닥까지 8칸.
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


# 포즈 시트: (모습, 화면 x, 몸 회전, 의자, 머리 숙임, 자세). 의자는 골반 좌표의 상자 (x, y, z 범위)이며 없으면 None.
SEAT = ((-0.95, 0.95), (0.44, None), (-1.25, 0.55))
POSES = (
    # 3/4 앞에서 본 앉은 여성: 두 손을 허벅지에 얹고 얼굴은 관찰자 쪽으로 조금 더 돌린다.
    (FEMALE, 360.0, 35.0, SEAT, 4.0, dict(lean=6.0, head=3.0, head_turn=-18.0, arm_l=(10.0, -14.0),
                                          arm_r=(8.0, -16.0), leg_l=(2.0, 0.0), leg_r=(2.0, 2.0),
                                          swing={"leg_l": (86.0, 2.0), "leg_r": (90.0, 12.0), "arm_l": (14.0, 62.0),
                                                 "arm_r": (18.0, 66.0)})),
    # 옆에서 본 걷는 남성: 가까운 다리가 앞, 먼 다리는 무릎을 굽히고 뒤꿈치를 든다. 팔은 다리와 엇갈린다.
    (MALE, 1010.0, -90.0, None, 0.0, dict(lean=4.0, arm_l=(6.0, 2.0), arm_r=(6.0, 2.0), leg_l=(2.0, 0.0),
                                        leg_r=(2.0, 0.0), foot_pitch={"l": 24.0},
                                        swing={"leg_r": (24.0, 4.0), "leg_l": (-14.0, -38.0),
                                               "arm_r": (-20.0, -6.0), "arm_l": (22.0, 44.0)})),
    # 어깨 너머로 돌아보는 여성: 몸은 3/4 뒷면, 머리는 옆모습까지 돌린다. 한쪽 다리에 체중을 싣는다.
    (FEMALE, 1560.0, 155.0, None, -4.0, dict(head_turn=-72.0, hip_tilt=5.0, chest_tilt=-3.0, spine=1.0, head=2.0,
                                             arm_l=(9.0, 4.0), arm_r=(14.0, 8.0), leg_l=(3.0, -1.0),
                                             leg_r=(7.0, 1.0))),
    # 옆에서 본 앉은 남성: 상체를 조금 숙이고 두 손을 무릎에 얹는다.
    (MALE, 1990.0, 75.0, SEAT, 8.0, dict(lean=12.0, head=0.0, arm_l=(6.0, -6.0), arm_r=(8.0, -8.0),
                                        leg_l=(4.0, 0.0), leg_r=(6.0, 2.0),
                                        swing={"leg_l": (84.0, 4.0), "leg_r": (80.0, 10.0), "arm_l": (25.0, 60.0),
                                               "arm_r": (22.0, 62.0)})),
)
BLOCK_COLORS = {"top": "#c9d0e2", "side": "#a7b1cb", "front": "#b6bfd6", "line": "#6d7896"}


def paint_seat(cv, model, seat):
    """상자 의자. 몸과 같은 시선으로 투영하고 관찰자를 향한 면만 칠한다."""
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
