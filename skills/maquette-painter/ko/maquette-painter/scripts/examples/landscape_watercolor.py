"""Mountain lake in watercolour. A landscape is laid in back to front; each layer's depth drives haze and softness."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, scenery as sc, studio

brief = Brief.from_answers(subject="landscape", style="watercolor", lighting="golden_hour", composition="low_horizon",
                           mood="calm", message="해 질 무렵 호수의 고요함", seed=5)


def build(canvas, light, brief):
    light.haze_strength = 0.55
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon = H * 0.58
    sc.sky(canvas, "#4a7fc0", "#f3dfc2", horizon, glow=(W * 0.74, horizon - 40, W * 0.22))
    sc.clouds(canvas, 0.4, 0, horizon * 0.72, color="#fff6e8", shadow="#b9a9b8", seed=seed)
    sc.mountains(canvas, horizon, H * 0.36, "#8390b6", depth=0.92, seed=seed + 1, snow=H * 0.34, facets=0.8)
    sc.mountains(canvas, horizon, H * 0.2, "#5d7090", depth=0.8, seed=seed + 2, roughness=0.7)
    sc.hills(canvas, horizon, H * 0.07, "#4d7458", depth=0.68, seed=seed + 3)
    sc.treeline(canvas, horizon, H * 0.055, "#355843", depth=0.62, seed=seed + 4)
    sc.water(canvas, horizon, color="#5e8fb2", seed=seed, light=light, glitter=(W * 0.74, W * 0.05))
    sc.hills(canvas, H * 0.95, H * 0.09, "#6c9a52", depth=0.25, seed=seed + 6, feature=W * 1.2)
    for i, (x, tall) in enumerate([(0.06, 0.52), (0.14, 0.4), (0.9, 0.56), (0.83, 0.36)]):
        sc.conifer(canvas, W * x, H * 0.93 - (i % 2) * 14, H * tall, seed=seed + 10 + i, depth=0.2)
    sc.rock(canvas, W * 0.27, H * 0.93, W * 0.1, H * 0.055, seed=seed + 20, depth=0.18)
    sc.grass(canvas, H * 0.88, H, "#55863f", density=1.2, seed=seed + 30)
    sc.flowers(canvas, H * 0.9, H * 0.99, count=90, seed=seed + 31)


if __name__ == "__main__":
    studio.run(build, brief, "landscape_watercolor.png")
