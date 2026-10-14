"""Style presets: a medium, its parameters, the lighting it favours and the finishing passes.

A style never changes the structure of a picture, only how it is painted and finished.
paint(canvas, style) = render with the preset + run the finish chain.
Figures should be drawn inside `canvas.layer(group="figure")` so presets that paint figures
and backgrounds differently (animation) can tell them apart.
"""
from . import finish as fin
from .core import Light
from .media import render

LIGHTS = {
    "studio": dict(azimuth=-40, elevation=40),
    "soft_front": dict(azimuth=-15, elevation=25, wrap=0.4, shadow_tint="#c4a8b4"),
    "rembrandt": dict(azimuth=-55, elevation=45, color="#ffe9c8", shadow_tint="#5a4a52", wrap=0.05),
    "side": dict(azimuth=-80, elevation=20, shadow_tint="#6a6a8e"),
    "top": dict(azimuth=-10, elevation=78, shadow_tint="#7f86a8"),
    "backlit": dict(azimuth=150, elevation=30, color="#fff0d0", shadow_tint="#8088b0", wrap=0.3, rim=0.7),
    "golden_hour": dict(azimuth=62, elevation=16, color="#ffd29a", shadow_tint="#7a78b0", haze="#ffd9b0", haze_strength=0.45),
    "noon": dict(azimuth=-20, elevation=68, color="#fffdf2", shadow_tint="#8090b8", haze="#cfe0f0", haze_strength=0.4),
    "overcast": dict(azimuth=0, elevation=60, color="#eef1f4", shadow_tint="#a9aebb", wrap=0.5, haze="#d5dbe2", haze_strength=0.5),
    "blue_hour": dict(azimuth=-30, elevation=25, color="#b9c8f0", shadow_tint="#4f5a94", haze="#6f7fb8", haze_strength=0.5),
    "night": dict(azimuth=30, elevation=50, color="#8fa0d8", shadow_tint="#3a4070", haze="#2c3360", haze_strength=0.45),
    "candle": dict(azimuth=-60, elevation=8, color="#ffb86a", shadow_tint="#3a2a3a", wrap=0.1),
}


def light(name="studio", **overrides):
    params = dict(LIGHTS[name])
    params.update(overrides)
    return Light(**params)


STYLES = {
    # ---------- animation and comics ----------
    "anime_cel": dict(family="animation", face="anime", light="studio", medium="cel",
                      params=dict(bands=2, soft=0.015),
                      finish=[("diffusion", dict(radius=9, strength=0.16)), ("grade", dict(saturation=1.06))]),
    "anime_film": dict(family="animation", face="semi", light="studio", medium="gouache",
                       params=dict(steps=5, soft=0.2, brush=0.2, wobble_px=0.5),
                       groups={"figure": ("cel", dict(bands=3, soft=0.02, shadow_saturation=1.0, line_strength=0.85))},
                       finish=[("light_wash", dict(strength=0.12)), ("diffusion", dict(radius=10, strength=0.2)),
                               ("grade", dict(saturation=0.94, contrast=1.06)), ("chromatic", dict(pixels=0.6)),
                               ("grain", dict(amount=0.012)), ("vignette", dict(strength=0.14))]),
    "retro_anime": dict(family="animation", face="anime", light="studio", medium="gouache",
                        params=dict(steps=4, soft=0.1),
                        groups={"figure": ("cel", dict(bands=2, soft=0.0, lines="black", shadow_saturation=1.25))},
                        finish=[("grade", dict(saturation=1.12, contrast=1.08, temperature=0.04)), ("grain", dict(amount=0.03, size=1.6))]),
    "webtoon": dict(family="animation", face="semi", light="soft_front", medium="cel",
                    params=dict(bands=2, soft=0.13, shadow_saturation=1.2, line_strength=0.9),
                    finish=[("bloom", dict(threshold=0.72, radius=16, strength=0.2)), ("light_wash", dict(strength=0.1)),
                            ("grade", dict(saturation=1.08))]),
    "manga": dict(family="animation", face="anime", light="studio", medium="halftone",
                  params=dict(mono=True, dot=5.0), finish=[]),
    # ---------- illustration and design ----------
    "flat_vector": dict(family="illustration", face="anime", light="studio", medium="flat", params={}, finish=[]),
    "flat_shadow": dict(family="illustration", face="anime", light="studio", medium="cel",
                        params=dict(bands=2, soft=0.0, lines="none", highlight=0.0), finish=[]),
    "poster": dict(family="illustration", face="semi", light="studio", medium="gouache",
                   params=dict(steps=3, soft=0.04, brush=0.2), finish=[("grain", dict(amount=0.02))]),
    "storybook": dict(family="illustration", face="anime", light="soft_front", medium="watercolor",
                      params=dict(wetness=0.4, border=26, line_strength=0.8), finish=[]),
    "pop_art": dict(family="illustration", face="semi", light="studio", medium="halftone", params=dict(dot=8.0), finish=[]),
    "art_nouveau": dict(family="illustration", face="semi", light="soft_front", medium="woodblock",
                        params=dict(bokashi=0.0, mute=0.82, misregister=0.0, paper="#f0e4c8", line_strength=1.0),
                        finish=[("glaze", dict(color="#e8d2a0", strength=0.12))]),
    # ---------- western painting ----------
    "renaissance": dict(family="painting", face="classic", light="rembrandt", medium="oil",
                        params=dict(radii=(18, 9, 4.5, 2.2, 1.1), threshold=0.035, jitter=0.012, impasto=0.12,
                                    ground="#5a4632", vivid=0.92, canvas_texture=0.25, length=(3, 10)),
                        finish=[("glaze", dict(color="#c89a4a", strength=0.16)), ("vignette", dict(strength=0.32)),
                                ("craquelure", dict(strength=0.045)), ("grade", dict(contrast=1.04))]),
    "baroque": dict(family="painting", face="classic", light="rembrandt", medium="oil",
                    params=dict(radii=(20, 10, 5, 2.4, 1.2), threshold=0.04, jitter=0.02, impasto=0.2, ground="#2a1f18",
                                vivid=1.0, length=(3, 10)),
                    finish=[("grade", dict(contrast=1.12)), ("glaze", dict(color="#b8823a", strength=0.12)),
                            ("vignette", dict(strength=0.4)), ("craquelure", dict(strength=0.04))]),
    "academic": dict(family="painting", face="classic", light="soft_front", medium="oil",
                     params=dict(radii=(18, 9, 4.5, 2.2, 1.1), threshold=0.035, jitter=0.012, impasto=0.1, ground="#b8aa94",
                                 vivid=1.0, length=(3, 10)),
                     finish=[("glaze", dict(color="#e8d8b8", strength=0.08))]),
    "oil": dict(family="painting", face="classic", light="studio", medium="oil", params={}, finish=[]),
    "impressionism": dict(family="painting", face="classic", light="noon", medium="oil",
                          params=dict(radii=(16, 9, 5), length=(2, 5), jitter=0.06, hue_jitter=0.035, impasto=1.0,
                                      threshold=0.09, vivid=1.3, ground="#d8cdb8"),
                          finish=[("grade", dict(saturation=1.08))]),
    "post_impressionism": dict(family="painting", face="classic", light="noon", medium="oil",
                               params=dict(radii=(14, 8, 5), length=(6, 16), curvature=0.3, swirl=0.35, impasto=1.2,
                                           vivid=1.45, hue_jitter=0.03, jitter=0.05, threshold=0.08),
                               finish=[]),
    "expressionism": dict(family="painting", face="classic", light="side", medium="oil",
                          params=dict(radii=(26, 13, 7), length=(4, 12), jitter=0.08, hue_jitter=0.05, vivid=1.7,
                                      impasto=1.1, swirl=0.2, threshold=0.1, line_strength=0.9),
                          finish=[("grade", dict(contrast=1.12))]),
    "fauvism": dict(family="painting", face="classic", light="studio", medium="oil",
                    params=dict(radii=(22, 11, 6), length=(3, 9), vivid=2.0, jitter=0.05, hue_jitter=0.06, impasto=0.8,
                                threshold=0.1, ground="#e8d8a0"),
                    finish=[]),
    "pointillism": dict(family="painting", face="classic", light="noon", medium="pointillism", params={}, finish=[]),
    "cubism": dict(family="painting", face="classic", light="side", medium="facets", params={}, finish=[]),
    # ---------- east asian traditions ----------
    "sumi_e": dict(family="east_asian", face="semi", light="studio", medium="ink", params=dict(color=0.0), finish=[]),
    "ink_color": dict(family="east_asian", face="semi", light="studio", medium="ink", params=dict(color=0.55), finish=[]),
    "ukiyo_e": dict(family="east_asian", face="semi", light="studio", medium="woodblock", params={}, finish=[]),
    "minhwa": dict(family="east_asian", face="semi", light="studio", medium="woodblock",
                   params=dict(bokashi=0.0, mute=1.05, paper="#e9dcc0", misregister=0.0, mottle=0.35), finish=[]),
    # ---------- drawing ----------
    "pencil": dict(family="drawing", face="classic", light="studio", medium="pencil", params={}, finish=[]),
    "colored_pencil": dict(family="drawing", face="semi", light="studio", medium="pencil", params=dict(color=1.0), finish=[]),
    "charcoal": dict(family="drawing", face="classic", light="rembrandt", medium="charcoal", params={}, finish=[]),
    "pastel": dict(family="drawing", face="classic", light="soft_front", medium="pastel", params={}, finish=[]),
    # ---------- watercolour ----------
    "watercolor": dict(family="watercolor", face="semi", light="studio", medium="watercolor", params={}, finish=[]),
    "watercolor_loose": dict(family="watercolor", face="semi", light="soft_front", medium="watercolor",
                             params=dict(wetness=0.75, wobble_px=5.0, lines="none", bloom=0.22, border=30), finish=[]),
    "urban_sketch": dict(family="watercolor", face="semi", light="studio", medium="watercolor",
                         params=dict(lines="ink", line_strength=0.9, wetness=0.3, border=24), finish=[]),
    # ---------- doomer: this skill's own look ----------
    # Late-night post-Soviet suburb as a worn photograph: drained colour, teal-black shadows, sodium and window light
    # that blooms into the haze, heavy film grain. The figure keeps soft cel shapes so faces stay readable.
    "doomer": dict(family="doomer", face="semi", light="night", medium="gouache",
                   params=dict(steps=6, soft=0.35, brush=0.1, wobble_px=0.3, vivid=0.9, lines="trace", line_strength=0.35),
                   groups={"figure": ("cel", dict(bands=2, soft=0.08, shadow_saturation=0.7, line_strength=0.55, key_color=0.6,
                                                  highlight=0.2, rim=1.0))},
                   finish=[("bloom", dict(threshold=0.5, radius=18, strength=0.7)), ("grade", dict(saturation=0.72, contrast=1.12,
                                                                                                     temperature=-0.04)),
                           ("chromatic", dict(pixels=0.8)), ("grain", dict(amount=0.03, size=1.6)),
                           ("vignette", dict(strength=0.4))]),
    # The same world on a photocopied record sleeve: black and white, crushed blacks, coarse toner grain.
    "doomer_mono": dict(family="doomer", face="semi", light="overcast", medium="gouache",
                        params=dict(steps=5, soft=0.25, brush=0.15, wobble_px=0.3, lines="black", line_strength=0.3),
                        groups={"figure": ("cel", dict(bands=2, soft=0.05, line_strength=0.6))},
                        finish=[("bloom", dict(threshold=0.7, radius=14, strength=0.3)),
                                ("grade", dict(saturation=0.0, contrast=1.4, gamma=0.9)), ("grain", dict(amount=0.035, size=1.8)),
                                ("vignette", dict(strength=0.5))]),
}


def default_light(style):
    return light(STYLES[style]["light"])


def paint(canvas, style="anime_cel", light=None, finish=True, params=None, extra_finish=()):
    """Render a canvas in a named style and run its finishing chain.

    params overrides the preset's medium parameters; extra_finish appends (name, kwargs) passes.
    """
    preset = STYLES[style]
    scene_light = light if light is not None else default_light(style)
    medium_params = dict(preset["params"])
    medium_params.update(params or {})
    image = render(canvas, preset["medium"], scene_light, groups=preset.get("groups"), **medium_params)
    if finish:
        for name, kwargs in list(preset["finish"]) + list(extra_finish):
            kwargs = dict(kwargs)
            if name in ("diffusion", "bloom") and "radius" in kwargs:
                kwargs["radius"] *= canvas.scale
            if name in ("grain", "craquelure"):
                kwargs.setdefault("seed", canvas.seed)
            image = getattr(fin, name)(image, **kwargs)
    return image
