"""회화풍(수채화) 예제: 손 습작 여섯 가지.

공정: 손 좌표계 배치 → 부위별 살색 번짐 → 그늘 겹칠 → 윤곽 펜 선 → 마디 주름과 손톱 → 수채화 패스.
손은 figure.hand_open(손등, 손바닥)과 figure.hand_side(옆모습)가 마디 길이와 굽힘을 계산한다.
장면 코드는 손목 위치, 방향, 벌림, 굽힘만 정한다.
실행: python watercolor_hand_studies.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, figure, io  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402

WIDTH, HEIGHT = 1500, 1000
LIGHT = (-0.7, -0.7)
SKIN, SKIN_DEEP, NAIL = "#f2c4a2", "#c9785e", "#f7ddd0"
INK = "#6a3a2e"
WASHES = ["#d9e6ea", "#efe0d0", "#e6dcec"]
BACK_ORDER = ("palm", "pinky", "ring", "middle", "index", "thumb")
PALM_ORDER = ("palm", "thumb", "pinky", "ring", "middle", "index")


def creases(cv, hand, unit, nails):
    """마디 주름과 손톱. 마디 위치는 hand.joints가 알려 준다."""
    for name, points in hand.joints.items():
        points = np.asarray(points)
        for index in range(1, len(points) - 1):
            along = points[index + 1] - points[index - 1]
            length = np.linalg.norm(along)
            if length < unit * 0.04:
                continue   # 접혀서 보이지 않는 마디
            across = np.array([-along[1], along[0]]) / length * unit * 0.04
            cv.stroke([points[index] - across, points[index] + across], INK, width=1.4, opacity=0.55)
        tip_length = np.linalg.norm(points[-1] - points[-2])
        if nails and tip_length > unit * 0.05:
            heading = np.rad2deg(np.arctan2(*(points[-1] - points[-2])[::-1])) + 90.0
            center = points[-2] + (points[-1] - points[-2]) * 0.72
            nail = g.ellipse(center[0], center[1], unit * 0.034, unit * 0.045, heading)
            cv.fill(cv.shape(nail), NAIL, opacity=0.9)
            cv.stroke(nail, INK, width=1.0, closed=True, opacity=0.5)


def study(cv, hand, order, unit, nails=True):
    for name in order:
        part = figure.shape_of(cv, hand.parts[name])
        cv.fill(part, "#ffffff")
        cv.fill(part, SKIN, opacity=0.9, blend=Blend.MULTIPLY)
        cv.fill(cv.form_shadow(part, LIGHT, 0.4, soft=0.35), SKIN_DEEP, opacity=0.6, blend=Blend.MULTIPLY)
        cv.fill(cv.edge_light(part, (-LIGHT[0], -LIGHT[1]), width=2.2), INK, opacity=0.8)
        cv.fill(cv.edge_light(part, LIGHT, width=1.3), INK, opacity=0.6)
    creases(cv, hand, unit, nails)


def main(out_dir="out", scale=1.0, seed=37):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    unit = 300
    # 각 습작 뒤에 옅은 번짐을 깔아 종이 위에서 손이 떠 보이게 한다.
    spots = [(260, 300), (750, 290), (1240, 300), (260, 760), (750, 770), (1240, 760)]
    for index, (x, y) in enumerate(spots):
        watercolor.wash(cv, g.blob(x, y, 190, 0.25, 9, rng), WASHES[index % 3], 0.8, soft=30, rough=18)

    study(cv, figure.hand_open(g.Frame((250, 470), unit, rotate=-6)), BACK_ORDER, unit)
    study(cv, figure.hand_open(g.Frame((740, 470), unit, rotate=4), spread=2.3, thumb=1.5), BACK_ORDER, unit)
    study(cv, figure.hand_open(g.Frame((1230, 480), unit, rotate=10), curl=(0.0, 0.85, 0.9, 0.92), thumb=0.5),
          BACK_ORDER, unit)
    study(cv, figure.hand_open(g.Frame((250, 930), unit, rotate=-8).mirrored(), curl=0.4, view="palm"),
          PALM_ORDER, unit, nails=False)
    study(cv, figure.hand_side(g.Frame((740, 950), unit, rotate=-4), curl=0.3), BACK_ORDER, unit, nails=False)
    study(cv, figure.hand_side(g.Frame((1250, 950), unit, rotate=8).mirrored(), curl=0.8), BACK_ORDER, unit,
          nails=False)
    io.save(cv.guide_image(), out_dir / "hands_1_underpainting_guide.png")
    return io.save(watercolor.render(cv, wobble=1.0, bleed=0.4), out_dir / "watercolor_hand_studies.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
