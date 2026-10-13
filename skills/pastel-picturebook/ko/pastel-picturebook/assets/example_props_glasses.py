"""둥근 안경 예제."""
import numpy as np
from raster import ellipse, fill, over, rgb, screen, smooth, stroke

FRAME_COLOR = "#2A2230"

def after_figure(scene):
    fig, unit = scene.fig, scene.px(1.0)
    centers = [fig.points["eye_far_center"], fig.points["eye_near_center"]]
    rings = [ellipse(center + [0, 0.03 * unit], 0.30 * unit, 0.27 * unit, 64) for center in centers]
    for ring in rings:
        screen(scene.image, rgb("#FFFFFF"), fill(scene.size, ring), 0.10)
        over(scene.image, rgb(FRAME_COLOR), stroke(scene.size, np.vstack([ring, ring[:1]]), 0.022 * unit))
    inner_far = rings[0][np.argmin(np.linalg.norm(rings[0] - centers[1], axis=1))]
    inner_near = rings[1][np.argmin(np.linalg.norm(rings[1] - centers[0], axis=1))]
    bridge = smooth([inner_far, 0.5 * (inner_far + inner_near) - [0, 0.04 * unit], inner_near])
    over(scene.image, rgb(FRAME_COLOR), stroke(scene.size, bridge, 0.020 * unit))
