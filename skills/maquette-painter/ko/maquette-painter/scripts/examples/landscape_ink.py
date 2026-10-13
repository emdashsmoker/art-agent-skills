"""East Asian ink landscape (수묵담채). Empty paper is part of the picture: far ranges dissolve into mist."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, geom, scenery as sc, studio

brief = Brief.from_answers(subject="landscape", style="ink_color", format="tall", lighting="overcast", mood="calm",
                           message="안개 낀 산중의 적막", seed=9)


def build(canvas, light, brief):
    light.haze, light.haze_strength = light.haze * 0 + [0.937, 0.902, 0.824], 0.75       # haze = bare paper colour
    W, H = canvas.width, canvas.height
    with canvas.layer(depth=1.0):
        canvas.add(geom.rect(0, 0, W, H), "#efe7d4", "paper", unlit=True)
    sc.mountains(canvas, H * 0.52, H * 0.34, "#7f8a8a", depth=0.95, seed=1, roughness=0.75, feature=W * 0.7, facets=0.9, shape="rounded")
    sc.mountains(canvas, H * 0.62, H * 0.3, "#5f6a66", depth=0.8, seed=2, roughness=0.8, feature=W * 0.5, facets=1.1, shape="rounded")
    sc.mountains(canvas, H * 0.78, H * 0.26, "#3f4a44", depth=0.55, seed=3, roughness=0.85, feature=W * 0.45, facets=1.2, shape="rounded")
    for i, (x, tall) in enumerate([(0.2, 0.2), (0.3, 0.15), (0.74, 0.24), (0.84, 0.17)]):
        sc.conifer(canvas, W * x, H * (0.86 + 0.02 * (i % 2)), H * tall, color="#2a332c", trunk="#2a2622", seed=20 + i, depth=0.3)
    with canvas.layer(depth=0.2):           # mist band: bare paper drifting across the valley
        xs, ys = canvas.grid()
        band = (canvas.noise(260, 3) - 0.35) * 2.2 * (1 - abs(ys / H - 0.6) / 0.12).clip(0, 1)
        canvas.tint(band.clip(0, 1).astype("float32"), "#efe7d4", alpha=0.9)


if __name__ == "__main__":
    from atelier import finish, save
    import cv2
    path = studio.run(build, brief, "landscape_ink.png")
    if path.name.endswith("landscape_ink.png") or "--out" in sys.argv:      # final render only: add the artist's seal
        image = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB).astype("float32") / 255
        if not any(flag in sys.argv for flag in ("--rough", "--buffers", "--styles")):
            save(finish.seal(image, image.shape[1] * 0.84, image.shape[0] * 0.08, size=int(image.shape[1] * 0.055)), path)
