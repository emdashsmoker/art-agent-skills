"""Assembly of a bust portrait, back to front, like stacking sheets of cut paper.

The head is split into a back pass (hair behind everything) and a front pass (ears,
face, features, front hair) so that other rigs can slide a body in between.
"""
from dataclasses import dataclass

import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..styles import ANIME, line_color
from . import accessories, face, hair, outfit
from .frame import NAPE_IDS, HeadFrame, PortraitSpec, expressed, head_contour, light_on_canvas, midline_shape

RIM_COLOR = "#d6e8ff"        # cool secondary light from behind, opposite the warm key light


@dataclass
class HeadParts:
    frame: HeadFrame
    plan: hair.HairPlan
    contour: np.ndarray          # head outline (pixels)
    head: np.ndarray             # head mask
    front_hair: np.ndarray       # mask of cap and front locks, known before drawing for cast shadows
    locks: np.ndarray = None     # front locks alone: they stand off the skin, so their shadows reach further
    caster: np.ndarray = None    # the part of the head that throws a shadow down onto the neck and clothes


def prepare_head(painting, spec, hair_plan=None):
    """Work out the head geometry before anything is drawn."""
    frame = HeadFrame(spec, painting.shape)
    plan = hair_plan or hair.plan_hair(frame, spec)
    contour = geo.smooth(frame.place(head_contour(frame, spec.jaw)), closed=True)
    locks = np.maximum.reduce([painting.mask(curve) for curve in plan.locks]) if plan.locks else np.zeros(painting.shape, np.float32)
    front_hair = np.maximum(painting.mask(plan.cap), locks)
    head = painting.mask(contour)
    caster = head
    if frame.profile > 0:            # brow, nose, lips and chin stand out of the outline
        head = np.maximum.reduce([head, painting.mask(midline_shape(frame)), painting.mask(midline_shape(frame, smooth=False))])
        # Behind the jaw angle the head runs on into the neck: only the jaw overhangs it and shades it.
        caster = head * (1.0 - nape_region(painting, frame, spec.jaw, reach=JAW_SHADOW_CUT) * nape_join(frame))
    return HeadParts(frame, plan, contour, head, front_hair, locks, caster)


NAPE_LINE_REACH = 0.03       # head units above the jaw-to-nape edge that the dropped line may occupy
NAPE_NECK_DROP = 0.30        # head units below that edge where the neck carries on
JAW_SHADOW_CUT = 0.15        # head units above that edge that throw no shadow on the neck
NAPE_JOIN_PROFILE = (0.10, 0.45)   # profile range over which that edge turns from cheek outline into neck join


def nape_join(frame):
    """0..1: how far the jaw-to-nape edge has turned from an outline into the place where the neck carries on."""
    return float(sh.smoothstep(*NAPE_JOIN_PROFILE, frame.profile))


def nape_region(painting, frame, jaw=1.0, reach=NAPE_LINE_REACH):
    """Mask round the jaw-to-nape edge of a turned head (reach above it, down into the neck); None for a front view."""
    if frame.profile <= 0:
        return None
    edge = head_contour(frame, jaw)[NAPE_IDS[0]:NAPE_IDS[1] + 1]
    region = np.vstack([edge - [0.0, reach], (edge + [0.0, NAPE_NECK_DROP])[::-1]])
    return painting.mask(frame.place(region))


def nape_keep(painting, frame, jaw=1.0, region=None):
    """Outline weight mask that drops the line from the jaw angle to the nape, where a turned head runs into the neck.

    region: the nape_region mask when the caller already has it.
    """
    region = nape_region(painting, frame, jaw) if region is None else region
    if region is None:
        return None
    return 1.0 - sh.blur(region, frame.px(0.008)) * nape_join(frame)


def draw_head_back(painting, parts, spec, style, light):
    """Hair behind the head and body. Returns its mask."""
    return hair.draw_back_hair(painting, parts.frame, spec, style, light, parts.plan)


def draw_head_front(painting, parts, spec, style, light):
    """Ears, face, features and the hair in front. Returns (eyes mask, front hair mask)."""
    spec = expressed(spec)
    frame, light2d = parts.frame, light_on_canvas(light)
    ears_in_front = frame.profile >= face.EAR_FRONT_PROFILE      # turned far, the ear sits on the side of the head
    if not ears_in_front:
        face.draw_ears(painting, frame, spec, style)
    neck_join = nape_region(painting, frame, spec.jaw)
    keep = nape_keep(painting, frame, spec.jaw, neck_join)
    face.draw_head_skin(painting, frame, spec, style, light, parts.head, parts.contour, parts.front_hair,
                        keep=keep, locks=parts.locks,
                        joined=None if neck_join is None else neck_join * nape_join(frame))
    if ears_in_front:
        face.draw_ears(painting, frame, spec, style)
    accessories.draw_stubble(painting, frame, spec, style, parts.head)
    eyes = face.draw_features(painting, frame, spec, style, light2d, clip=parts.head)
    accessories.draw_earrings(painting, frame, spec, style)
    front = hair.draw_front_hair(painting, frame, spec, style, light, parts.plan, light2d, parts.head, spec.skin)
    if style.strands > 0:
        hair.draw_flyaways(painting, frame, spec, style, parts.plan)
    hat = accessories.draw_hat(painting, frame, spec, style, light, parts.head, front)
    accessories.draw_glasses(painting, frame, spec, style, parts.head, front)
    return eyes, np.maximum(front, hat)         # headwear belongs to the silhouette of the hair


def draw_rim_light(painting, figure, style, light, width):
    """Cool light along the figure's edge on the side away from the key light."""
    if style.rim <= 0:
        return
    light2d = light_on_canvas(light)
    rim = sh.rim(figure, (-light2d[0], -0.15), width, width * (0.14 + 0.36 * style.gradient))
    painting.fill(rim, RIM_COLOR, 0.6 * style.rim)


def draw_portrait(painting, spec=None, style=ANIME, light=sh.DEFAULT_LIGHT, hair_plan=None):
    """Draw the bust onto `painting`, over whatever background it already holds.

    hair_plan: optional HairPlan (from hair.plan_hair, then edited) for a custom hairstyle.
    Returns a dict of masks (head, hair, body, eyes, figure) and the HeadFrame,
    for extra effects, importance maps, or props added by the caller.
    """
    spec = spec or PortraitSpec()
    parts = prepare_head(painting, spec, hair_plan)
    frame = parts.frame
    skin_shadow = face.skin_shadow_color(spec, style)
    skin_ink = line_color(style, spec.skin, face.SKIN_INK)

    back_hair = draw_head_back(painting, parts, spec, style, light)
    body = outfit.draw_body_skin(painting, frame, spec, style, light, parts.caster, skin_shadow, skin_ink)
    clothes = outfit.OUTFITS[spec.outfit](painting, frame, spec, style, light, parts.caster)
    eyes, front = draw_head_front(painting, parts, spec, style, light)

    figure = np.clip(back_hair + body + clothes + parts.head + front, 0.0, 1.0)
    draw_rim_light(painting, figure, style, light, frame.px(0.011))
    return {"head": parts.head, "hair": np.maximum(front, back_hair), "body": np.maximum(body, clothes),
            "eyes": eyes, "figure": figure, "frame": frame}
