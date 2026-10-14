"""figure: parametric people built on the codepainter engine (bust portrait, full body, hands)."""
from . import anatomy, body, face, hair, hand, outfit, wardrobe   # wardrobe before clothing: it registers clothing's outfits
from . import accessories, clothing, palette, props, stage
from .body import BodySpec, Pose, draw_figure
from .frame import HeadFrame, PortraitSpec
from .portrait import draw_portrait

__all__ = ["BodySpec", "HeadFrame", "PortraitSpec", "Pose", "draw_figure", "draw_portrait",
           "accessories", "anatomy", "body", "clothing", "face", "hair", "hand", "outfit", "palette", "props", "stage",
           "wardrobe"]
