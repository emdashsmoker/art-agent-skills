"""Two people seen from behind, holding hands at the water's edge at sunset, as an impressionist oil.

The sun sits low ahead of them, so they are backlit: their backs turn to warm shadow edged with light and the
wet sand under their feet mirrors them, the sky and the sun's path. The two figures share one Ensemble so the
joined hands meet between them.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Character, Ensemble, Figure, Hair, Light, geom, scenery as sc, smoothstep, studio
from atelier import wardrobe as w

brief = Brief.from_answers(subject="scene", style="impressionism", format="landscape", framing="full",
                           view="back", outfit="dress", composition="low_horizon", lighting="backlit",
                           background="landscape", mood="romantic", message="해 질 녘 물가에서 손을 잡고 바다를 보는 두 사람",
                           seed=53)
HORIZON, SHORE = 0.5, 0.69                          # fractions of the picture height
BRUSH = dict(radii=(12, 6, 3), length=(2, 6), threshold=0.06, jitter=0.04, hue_jitter=0.02, vivid=1.2)


def shoreline(canvas, y, seed):
    """Spent waves running up the sand: two ragged foam lines over a glassy film of water."""
    rng = np.random.default_rng(seed)
    xs, ys = canvas.grid()
    for k, (offset, thick, alpha) in enumerate(((0.0, 5.0, 0.9), (16.0, 3.0, 0.7))):
        wave = canvas.noise(140.0, 3) - 0.5
        edge = y + offset + wave * 18
        band = smoothstep(thick, 0.0, np.abs(ys - edge)) * smoothstep(0.35, 0.6, canvas.noise(40.0, 2) + 0.15 * k)
        with canvas.layer(depth=0.45):
            canvas.add(np.clip(band * alpha, 0, 1).astype(np.float32), "#f6efe4", "foam", soft=0.6)
    film = smoothstep(y - 2, y + 4, ys) * smoothstep(y + 46 + rng.uniform(-4, 4), y + 20, ys)
    canvas.tint(film.astype(np.float32), "#c9b6b0", alpha=0.5)


def build(canvas, light, brief):
    light = Light(azimuth=170, elevation=10, color="#ffc890", shadow_tint="#4c3c5e", wrap=0.15, rim=0.9,
                  haze="#f0b890", haze_strength=0.45, bounce=0.12, bounce_color="#f0a878")
    W, H, seed = canvas.width, canvas.height, brief.seed
    horizon, shore = H * HORIZON, H * SHORE
    sun = (W * 0.7, horizon - 64)
    sc.sky(canvas, "#3f4a86", "#f8bd7c", horizon, glow=(sun[0], sun[1], W * 0.28), glow_color="#ffd9a0")
    sc.clouds(canvas, 0.38, H * 0.06, H * 0.42, color="#f9cfae", shadow="#9a7aa6", seed=seed, wispy=0.85, volume=0.15)
    sc.sun(canvas, sun[0], sun[1], 30, color="#fff4d8")
    sc.mountains(canvas, horizon, H * 0.06, "#6d5d80", depth=0.92, seed=seed + 1, shape="rounded", roughness=0.4)
    sc.water(canvas, horizon, shore, color="#56659a", seed=seed, light=light, glitter=(sun[0], W * 0.05), ripples=0.7)
    with canvas.layer(depth=0.4):
        canvas.add(geom.rect(0, shore, W, H), "#a07f72", "wet_sand", normal=(0, -0.85, 0.5))
    shoreline(canvas, shore, seed)

    # ---- the two of them, from behind, at the edge of the wet sand ----
    ground_y = H * 0.8
    unit = (ground_y - H * 0.31) / 7.6
    woman = Character(Figure(pose="relaxed", turn=172, heads=7.6), style="classic", jaw=0.8,
                      hair=Hair("long", "parted", "#3a2620", wave=0.5, sway=0.35, seed=seed), skin="light",
                      outfit=[w.dress("#f2e6d4", sleeves="cap", hem=1.6, flare=0.5)])
    man = Character(Figure(sex="male", pose="relaxed", turn=186, heads=7.8), style="classic", jaw=0.6,
                    hair=Hair("crop", "textured", "#241c18", seed=seed), skin="light",
                    outfit=[w.top("#e9eef2", "elbow", ease=0.025), w.pants("#3b4256", length="cropped")])
    woman.figure.set_pose(head=(-4, 18, 4))              # she turns her head a little toward him
    ensemble = Ensemble(canvas, ground_y, unit)
    ensemble.add(woman, W * 0.43, size=0.96)
    ensemble.add(man, W * 0.565)
    ensemble.hold_hands(woman, "r", man, "l")
    for x in (W * 0.43, W * 0.565):
        sc.contact_shadow(canvas, x, ground_y - 2, unit * 1.3, unit * 0.18, strength=0.5)
    with canvas.layer(depth=0.3, group="figure"):
        views = ensemble.draw(light=light)
    wet = canvas.region_mask("wet_sand", "foam").astype(np.float32)
    sc.wet_reflection(canvas, wet, light, strength=0.55, ripple=0.8, streak=0.8, glow=0.6, seed=seed)
    return {"views": views, "light": light, "style_params": {"impressionism": BRUSH}}


if __name__ == "__main__":
    studio.run(build, brief, "scene_beach_sunset.png")
