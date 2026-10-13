"""Style registry: a named style = a medium function + its parameters + finishing.

`render_style(frame, name, **overrides)` is the single entry point. Overrides that match
finishing options go to post.finish; the rest go to the medium.
"""
import numpy as np
import cv2

from . import media_cel, media_watercolor, media_oil, media_sketch, post
from . import media_common as mc
from .shade import downsample


def _gouache(F, **params):
    """Opaque matte paint: a flat two-tone plan repainted with visible but calm brushwork."""
    plan = media_cel.render_cel(F, line_width=0, band_softness=0.05, shade_smooth=5.0, saturation=0.92)
    scale = max(F.width, F.height) / 1024.0
    options = dict(brush_radii=(18, 9, 4.5, 2.2), stroke_length=6, color_jitter=0.035, bristle_contrast=0.06,
                   impasto=0.08, weave=0.0, error_threshold=0.04)
    options.update(params)
    radii = tuple(r * scale for r in options.pop("brush_radii"))
    focus = np.clip(cv2.GaussianBlur(F.focus, (0, 0), 4 * scale) + 0.15, 0, 1)
    return media_oil.paint(plan, media_oil.direction_field(F), F.seed, (0.80, 0.76, 0.68), radii, focus=focus, **options)


def _digital(F, smooth=0.55, stroke_opacity=0.5, edge_line=0.35, rim_light=0.25, skin_glow=0.18, **params):
    """Semi-realistic digital painting: smooth blended forms, crisp focal detail, soft rim light."""
    scale = max(F.width, F.height) / 1024.0
    reference = F.reference(0.35, 1.08)
    rim = downsample(mc.fresnel_rim(F) ** 3 * np.clip(F.lit + 0.25, 0, 1), F.g)[..., None] * rim_light
    reference = np.clip(reference + rim * np.asarray(F.light_color, np.float32), 0, 1)
    options = dict(brush_radii=(16, 8, 4, 2), stroke_length=8, color_jitter=0.02, bristle_contrast=0.03,
                   impasto=0.0, weave=0.0, error_threshold=0.03)
    options.update(params)
    radii = tuple(r * scale for r in options.pop("brush_radii"))
    focus = np.clip(cv2.GaussianBlur(F.focus, (0, 0), 4 * scale) + 0.2, 0, 1)
    painted = media_oil.paint(reference, media_oil.direction_field(F, smooth=5.0), F.seed, (0.5, 0.45, 0.42), radii, focus=focus, **options)
    image = mc.mix(reference, painted, stroke_opacity)
    image = mc.mix(image, cv2.GaussianBlur(image, (0, 0), 1.2 * scale), smooth * (1 - F.focus[..., None] * 0.8))
    if skin_glow:       # warm light bleeding through skin at the shadow edge
        warm = cv2.GaussianBlur(image, (0, 0), 6 * scale) * np.array([1.12, 0.96, 0.90], np.float32)
        image = mc.mix(image, np.maximum(image, warm), skin_glow * F.mask[..., None])
    if edge_line:
        ink = mc.outline(F, 1.0, 55.0, thin_in_light=0.7, lit=mc.soft_lit(F, 3.0))[..., None] * edge_line
        image = image * (1 - ink * 0.75)
    return np.clip(image, 0, 1)


def _doomer(F, mono=False, desaturate=0.6, keep_warm=1.0, contrast=1.25, **params):
    """Cold, drained night picture of the panel-block estates. Everything goes grey-blue except what is warm and
    lit: sodium street lamps, a cigarette ember, a lit kitchen. mono=True: grainy black-and-white film instead."""
    options = dict(smooth=0.65, stroke_opacity=0.4, edge_line=0.2, rim_light=0.12, skin_glow=0.05)
    options.update(params)
    image = _digital(F, **options)
    lum = mc.luminance(image)[..., None]
    if mono:
        grey = np.clip((lum - 0.5) * contrast + 0.5, 0, 1)
        return np.repeat(grey, 3, axis=-1)
    # warm and bright pixels keep their colour; the rest is drained toward grey
    warm = np.clip((image[..., 0] - image[..., 2]) * 4.0, 0, 1) * np.clip(lum[..., 0] * 2.2, 0, 1)
    keep = (warm * keep_warm)[..., None]
    drained = lum + (image - lum) * (1 - desaturate)
    return np.clip(drained * (1 - keep) + image * keep, 0, 1)


def _lineart(F, line_width=1.7, paper=(1.0, 1.0, 1.0), ink=(0.08, 0.08, 0.10), taper=0.4, crease_deg=38.0, spot_black=0.0):
    """Ink lines only; spot_black fills the deepest shadows solid (manga inking)."""
    lit = mc.soft_lit(F, 3.0)
    cover = mc.outline(F, line_width, crease_deg, thin_in_light=0.4, lit=lit, taper=taper)
    if spot_black:
        cover = np.maximum(cover, downsample((1 - mc.step(lit, spot_black)) * F.g["mask"], F.g))
    cover = cover[..., None]
    return np.asarray(paper, np.float32) * (1 - cover) + np.asarray(ink, np.float32) * cover


TONE_EDGE = 0.1                  # manga screentone fades in over this much shadow coverage


def _manga(F, line_width=1.5, paper=(1.0, 1.0, 1.0), ink=(0.08, 0.08, 0.10), taper=0.4, crease_deg=38.0, spot_black=0.12,
           dark_value=0.16, tone_below=0.42, tone_darkness=0.35, tone_pitch=5.0):
    """Manga inking: lines; solid black where the local colour is dark (black hair, dark clothes, eyes, brows)
    and in the deepest shadow; screentone dots over the rest of the shadow side.

    Shadow alone is not enough: a black-haired head lit from the front would stay white paper."""
    lit = mc.soft_lit(F, 3.0)
    cover = mc.outline(F, line_width, crease_deg, thin_in_light=0.4, lit=lit, taper=taper)
    mask = F.g["mask"]
    solid = np.maximum(1 - mc.step(lit, spot_black), 1 - mc.step(mc.luminance(F.albedo), dark_value)) * mask
    shade = downsample((1 - mc.step(lit, tone_below)) * mask, F.g)
    tone = mc.halftone(shade.shape, shade * tone_darkness, pitch=tone_pitch) * np.clip(shade / TONE_EDGE, 0, 1)  # no dots on lit paper
    cover = np.maximum.reduce([cover, downsample(solid, F.g), tone])
    cover = cover[..., None]
    return np.asarray(paper, np.float32) * (1 - cover) + np.asarray(ink, np.float32) * cover


def _clay(F):
    """Neutral lit preview for checking pose, framing and light before committing to a medium."""
    return F.reference(0.0)


STYLES = {
    "clay": dict(fn=_clay, params=dict(), post=dict(), about="plain lit preview for checking pose and composition"),
    # --- cel family
    "anime": dict(fn=media_cel.render_cel, params=dict(shadow_threshold=0.38, colored_lines=0.7, saturation=1.08, rim_light=0.15, face_smooth=4.5, face_lift=0.45, quiet_face=True, relief_lines=0.45),
                  post=dict(bloom=0.12), about="TV anime cel: two tones, colour-traced lines"),
    "anime_film": dict(fn=media_cel.render_cel,
                       params=dict(shadow_threshold=0.44, deep_threshold=0.16, line_width=1.25, colored_lines=0.25, saturation=0.82,
                                   thin_in_light=0.25, crease_deg=30.0, shade_smooth=2.2, rim_light=0.10, background_blur=1.5),
                       post=dict(contrast=1.06, shadows_tint=(0.52, 0.62, 0.66), highlights_tint=(0.90, 0.86, 0.78), bloom=0.18, grain=0.035, vignette=0.18),
                       about="feature-film cel with realistic proportions: three tones, thin dark lines, muted grade"),
    "comic": dict(fn=media_cel.render_cel, params=dict(line_width=2.4, colored_lines=0.0, line_color=(0.03, 0.03, 0.04), halftone_shadows=True, saturation=1.15, line_taper=0.5, thin_in_light=0.3),
                  post=dict(contrast=1.08), about="western comic: heavy black ink, halftone shadows"),
    "webtoon": dict(fn=media_cel.render_cel, params=dict(shadow_threshold=0.42, band_softness=0.10, gradient=0.6, line_width=1.15, colored_lines=0.85, shade_smooth=4.0, rim_light=0.30, saturation=1.0, background_blur=2.5),
                    post=dict(bloom=0.22, saturation=1.04), about="semi-realistic webtoon: soft cel bands over gradients, thin tinted lines, glow"),
    "flat": dict(fn=media_cel.render_flat, params=dict(), post=dict(), about="flat vector / stock illustration: clean shapes, grainy gradient"),
    "woodblock": dict(fn=media_cel.render_woodblock, params=dict(), post=dict(), about="ukiyo-e woodblock print: limited inks, key lines, bokashi"),
    "lineart": dict(fn=_lineart, params=dict(), post=dict(), about="ink line drawing"),
    "manga": dict(fn=_manga, params=dict(), post=dict(), about="manga inking: black on dark hair and clothes, screentone shadows"),
    # --- water media
    "watercolor": dict(fn=media_watercolor.render_watercolor, params=dict(), post=dict(), about="transparent watercolor with pencil underdrawing"),
    "watercolor_loose": dict(fn=media_watercolor.render_watercolor, params=dict(bleed=3.2, wobble=3.5, simplify=6.0, pencil=0.0, turbulence=0.4, edge_darkening=0.55, wash_levels=(0.5,)),
                             post=dict(), about="wet-in-wet watercolor: big soft washes, no drawing"),
    "ink_wash": dict(fn=media_watercolor.render_ink_wash, params=dict(), post=dict(), about="East Asian ink wash (sumi-e / sumukhwa)"),
    "gouache": dict(fn=_gouache, params=dict(), post=dict(), about="opaque matte gouache, as in animation background art"),
    # --- oil family
    "oil": dict(fn=media_oil.render_oil, params=dict(), post=dict(), about="alla prima oil: visible brushwork, warm ground"),
    "impasto": dict(fn=media_oil.render_oil, params=dict(brush_radii=(30, 15, 8, 4.5), impasto=1.6, bristle_contrast=0.18, color_jitter=0.07, saturation=1.15, stroke_length=6),
                    post=dict(), about="thick palette-knife oil"),
    "classical": dict(fn=media_oil.render_classical, params=dict(), post=dict(), about="Renaissance / academic oil: sfumato, glazes, aged varnish"),
    "baroque": dict(fn=media_oil.render_classical, params=dict(chiaroscuro=1.7, umber=(0.10, 0.07, 0.05), vignette=0.5, sfumato=1.6),
                    post=dict(contrast=1.08), about="tenebrism: figures emerging from darkness"),
    "impressionist": dict(fn=media_oil.render_oil,
                          params=dict(brush_radii=(10, 6, 4, 2.6), stroke_length=4, hue_jitter=0.04, color_jitter=0.06, saturation=1.25, contrast=0.85,
                                      ground=(0.80, 0.76, 0.66), impasto=0.9, curvature=0.3, density=1.3, error_threshold=0.03, terminator_saturation=0.5),
                          post=dict(brightness=0.03), about="broken colour, short strokes, light-filled palette"),
    "pointillist": dict(fn=media_oil.render_oil,
                        params=dict(brush_radii=(7, 4.6, 3.2), dabs=True, hue_jitter=0.12, color_jitter=0.08, saturation=1.3, ground=(0.90, 0.88, 0.80),
                                    impasto=0.3, density=0.85, error_threshold=0.0, focus_bias=1.0, contrast=0.9),
                        post=dict(), about="dots of pure colour"),
    "expressionist": dict(fn=media_oil.render_oil,
                          params=dict(brush_radii=(24, 12, 6), stroke_length=14, hue_jitter=0.05, color_jitter=0.09, saturation=1.6, contrast=1.25,
                                      along_form=True, impasto=1.1, bristle_contrast=0.2, ground=(0.15, 0.12, 0.20), swirl=1.0),
                          post=dict(contrast=1.05), about="bold long strokes, heightened colour"),
    "pastel": dict(fn=media_oil.render_pastel, params=dict(), post=dict(), about="soft pastel on toned paper"),
    "digital": dict(fn=_digital, params=dict(), post=dict(bloom=0.15, sharpen=0.25), about="semi-realistic digital painting"),
    # --- signature: the panel-block estate at night
    "doomer": dict(fn=_doomer, params=dict(),
                   post=dict(contrast=1.14, shadows_tint=(0.34, 0.44, 0.60), highlights_tint=(1.0, 0.84, 0.62), fade=0.04,
                             bloom=0.5, bloom_threshold=0.55, grain=0.06, grain_size=0.9, vignette=0.40),
                   about="doomer: drained grey-blue night, only sodium lamps and embers stay warm, film grain"),
    "doomer_mono": dict(fn=_doomer, params=dict(mono=True),
                        post=dict(fade=0.03, bloom=0.25, bloom_threshold=0.7, grain=0.085, grain_size=1.1, vignette=0.45),
                        about="doomer in grainy black-and-white film, like a post-punk record sleeve photograph"),
    # --- drawing
    "pencil": dict(fn=media_sketch.render_pencil, params=dict(), post=dict(), about="graphite hatching"),
    "charcoal": dict(fn=media_sketch.render_pencil, params=dict(charcoal=True, graphite=(0.10, 0.10, 0.11), line_width=2.0, darkness=1.0, paper_color=(0.90, 0.88, 0.83)),
                     post=dict(), about="charcoal on rough paper"),
    "pen": dict(fn=media_sketch.render_pen, params=dict(), post=dict(), about="pen and ink cross-hatching"),
    "pen_wash": dict(fn=media_sketch.render_pen, params=dict(wash=0.6), post=dict(), about="pen with sepia wash"),
}


def render_style(frame, name, post_options=None, **overrides):
    """Paint a Frame in a named style. Returns float RGB (H, W, 3) in 0..1."""
    if name not in STYLES:
        raise KeyError(f"unknown style '{name}'. Available: {sorted(STYLES)}")
    style = STYLES[name]
    params = {**style["params"], **overrides}
    image = style["fn"](frame, **params)
    extra = dict(post_options or {})
    grade = extra.pop("grade", None)
    if grade:                       # a named grade sits between the style's own finish and explicit options
        extra = {**post.GRADES[grade], **extra}
    return post.finish(image, frame.seed, **{**style["post"], **extra})
