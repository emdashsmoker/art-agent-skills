"""Small props built from the same part recipe. Use these as templates for new props."""
import numpy as np

from .geometry import catmull_rom, ellipse, lock

BOW_LOOP = ((0.10, 0.00), (0.55, -0.42), (1.00, -0.30), (1.05, 0.12), (0.62, 0.34))
BOW_TAILS = (((-0.08, 0.10), (-0.50, 1.30), 0.34, 0.08), ((0.08, 0.10), (0.42, 1.42), 0.34, -0.08))
BOW_KNOT_RADIUS = (0.20, 0.24)


def bow(painter, frame, material, name="bow"):
    """Ribbon bow. frame places a unit bow: loops reach x = +-1, tails hang to y = 1.4."""
    canvas = painter.canvas
    for root, tip, width, bend in BOW_TAILS:
        polygon, _ = lock(frame.apply([root])[0], frame.apply([tip])[0], width * frame.scale, bend)
        painter.part(name, canvas.mask(polygon), material, roundness=0.6)
    for mirror in (1.0, -1.0):
        loop = np.asarray(BOW_LOOP) * np.array([mirror, 1.0])
        painter.part(name, canvas.mask(catmull_rom(frame.apply(loop), closed=True)), material, roundness=0.6)
    knot = frame.apply(ellipse((0.0, 0.0), BOW_KNOT_RADIUS[0], BOW_KNOT_RADIUS[1], samples=32))
    painter.part(name, canvas.mask(knot), material, roundness=0.7)
