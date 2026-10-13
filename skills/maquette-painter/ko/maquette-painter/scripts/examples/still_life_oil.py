"""Classical still life in oil. Objects stand on a table plane and cast shadows onto it and onto each other."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, objects as ob, studio

brief = Brief.from_answers(subject="still_life", style="baroque", lighting="rembrandt", palette="earth", key="low",
                           message="어둠 속에서 떠오르는 과일과 도자기", seed=4)


def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    table_y = H * 0.62
    ob.use_light(light)                      # shadows lie on the table along the scene light
    ob.backdrop(canvas, "#2a2622", "#4a4238", table_y, glow=(W * 0.3, H * 0.35, W * 0.4))
    ob.table(canvas, table_y, "#6a4a30", edge=H * 0.05)
    ob.cloth(canvas, [(W * 0.03, table_y + 30), (W * 0.42, table_y), (W * 0.56, table_y + 50), (W * 0.52, H * 0.94),
                      (W * 0.18, H * 0.97), (W * 0.02, H * 0.84)], "#8f2f2a", seed=2, depth=0.48, folds=0.6)
    with canvas.layer(depth=0.4, group="objects"):
        ob.revolve(canvas, W * 0.33, H * 0.79, W * 0.19, H * 0.44, "#2f6f8f", "vase", gloss=0.6)
        for i, (fx, fy) in enumerate([(0.30, 0.25), (0.37, 0.2), (0.42, 0.3), (0.25, 0.33)]):
            ob.stem(canvas, (W * 0.33 + (i - 1.5) * 8, H * 0.36), (W * fx, H * fy))
            ob.flower(canvas, W * fx, H * fy, W * 0.07, ["#f0c9d6", "#f4e3a0", "#e8a0a8", "#ffffff"][i], seed=i)
        ob.plate(canvas, W * 0.68, H * 0.86, W * 0.33)
        ob.grapes(canvas, W * 0.61, H * 0.83, W * 0.15, seed=3)
        ob.apple(canvas, W * 0.73, H * 0.845, W * 0.11)
        ob.pear(canvas, W * 0.83, H * 0.855, W * 0.15)
        ob.citrus(canvas, W * 0.52, H * 0.91, W * 0.09, lemon=True, color="#e6c435")
        ob.revolve(canvas, W * 0.88, H * 0.74, W * 0.09, H * 0.28, "#3a5a40", "bottle", gloss=0.7)


if __name__ == "__main__":
    studio.run(build, brief, "still_life_oil.png")
