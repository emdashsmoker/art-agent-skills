"""Illustration pass: adds print and paper texture to a flat shape picture.

The scene code decides forms and color fields. This pass only finishes the picture by reducing the smoothness of
vector shapes.
Stippled gradients are made directly in the scene code with the grain argument of Canvas.fill.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import noise

# Jitter contours slightly to remove knife-cut vector edges (logical units).
EDGE_ROUGHNESS = 0.8
EDGE_GRAIN = 4.0
# Mottling from ink that does not soak into the paper evenly.
INK_MOTTLE = 0.10
INK_MOTTLE_GRAIN = 3.0
PAPER_TINT = "#f7f1e3"
PAPER_FIBER = 0.05
# Offset of one channel, like a misregistered print plate (logical units). 0 turns it off.
MISREGISTER = 0.0


def render(canvas, roughness=EDGE_ROUGHNESS, ink_mottle=INK_MOTTLE, paper_tint=PAPER_TINT,
           paper_fiber=PAPER_FIBER, misregister=MISREGISTER):
    """Return a 0-1 RGB image of the current canvas with print texture applied."""
    scale = canvas.scale
    image = canvas.image().astype(np.float32)
    height, width = image.shape[:2]

    if roughness > 0.0:
        ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
        grain_px = max(EDGE_GRAIN * scale, 2.0)
        shift_x = (noise.fbm((height, width), grain_px, canvas.next_seed(), octaves=2) - 0.5) * 2.0 * roughness * scale
        shift_y = (noise.fbm((height, width), grain_px, canvas.next_seed(), octaves=2) - 0.5) * 2.0 * roughness * scale
        image = cv2.remap(image, xs + shift_x, ys + shift_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    if misregister > 0.0:
        matrix = np.array([[1.0, 0.0, misregister * scale], [0.0, 1.0, misregister * scale * 0.5]], np.float32)
        image[..., 0] = cv2.warpAffine(image[..., 0], matrix, (width, height), borderMode=cv2.BORDER_REFLECT)

    if ink_mottle > 0.0:
        # Spots with less ink brighten toward the paper. Brighter color fields are affected less.
        mottle = noise.fbm((height, width), max(INK_MOTTLE_GRAIN * scale, 1.5), canvas.next_seed(), octaves=2)
        lift = np.clip((mottle - 0.55) / 0.45, 0.0, 1.0)[..., None] * ink_mottle
        image = 1.0 - (1.0 - image) * (1.0 - lift)

    paper = noise.paper_texture((height, width), canvas.next_seed(), scale)
    image = image * colors.rgb(paper_tint)
    return np.clip(image * (1.0 - paper_fiber * (1.0 - paper))[..., None], 0.0, 1.0)
