"""Named looks for figures: body types, face shapes, skin tones, hair and eye colours.

These are starting points; any field can be overridden in the figure spec.
Face keys are body-model morphs in -1..1 (see figure.shape_names()['local']).
"""

SKIN_TONES = {
    "porcelain": (0.98, 0.88, 0.82), "fair": (0.97, 0.83, 0.74), "light": (0.94, 0.78, 0.67),
    "medium": (0.86, 0.66, 0.52), "olive": (0.78, 0.62, 0.46), "tan": (0.72, 0.52, 0.38),
    "brown": (0.55, 0.37, 0.26), "dark": (0.36, 0.24, 0.18), "marble": (0.90, 0.89, 0.86),
}
HAIR_COLORS = {
    "black": (0.07, 0.06, 0.07), "dark_brown": (0.20, 0.13, 0.09), "brown": (0.36, 0.23, 0.14),
    "auburn": (0.48, 0.20, 0.12), "red": (0.66, 0.24, 0.12), "blonde": (0.86, 0.70, 0.42),
    "golden": (0.80, 0.58, 0.26), "platinum": (0.92, 0.88, 0.78), "gray": (0.62, 0.62, 0.64), "white": (0.94, 0.94, 0.95),
    "blue": (0.22, 0.36, 0.66), "pink": (0.92, 0.55, 0.68), "purple": (0.46, 0.30, 0.62), "teal": (0.20, 0.58, 0.58),
    "silver": (0.78, 0.80, 0.86),
}
EYE_COLORS = {
    "dark": (0.16, 0.10, 0.07), "brown": (0.36, 0.22, 0.12), "hazel": (0.48, 0.38, 0.18), "amber": (0.70, 0.46, 0.14),
    "green": (0.26, 0.46, 0.30), "blue": (0.26, 0.46, 0.72), "gray": (0.48, 0.54, 0.60), "violet": (0.46, 0.34, 0.70),
    "red": (0.70, 0.14, 0.16),
}

def _both(values):
    """Expand '*-name' keys to the left and right versions of a morph."""
    out = {}
    for key, value in values.items():
        if key.startswith("*"):
            out["l" + key[1:]] = value
            out["r" + key[1:]] = value
        else:
            out[key] = value
    return out


# A lean face with a narrow, defined jaw. Cheeks keep some volume so the face does not turn gaunt.
_SHARP_JAW = _both({
    "chin-width-incr": -0.7, "chin-bones-incr": -0.35, "chin-prominent-incr": 0.2, "chin-height-incr": 0.1,
    "chin-jaw-drop-incr": -0.2, "head-fat-incr": -0.25, "*-cheek-bones-incr": 0.3, "*-cheek-volume-incr": 0.0,
})
# Large open eyes, a small straight nose, full lips, a slim neck.
_FEMININE_FEATURES = _both({
    "*-eye-height1-incr": 0.6, "*-eye-scale-incr": 0.4, "*-eye-corner2-up": 0.3,
    "nose-scale-horiz-incr": -0.7, "nose-width1-incr": -0.4, "nose-width2-incr": -0.4, "nose-width3-incr": -0.5,
    "nose-scale-vert-incr": -0.25, "nose-scale-depth-incr": -0.35, "nose-point-up": 0.35, "nose-hump-incr": -0.3,
    "nose-nostrils-width-incr": -0.4, "nose-flaring-incr": -0.4,
    "mouth-lowerlip-volume-incr": 0.6, "mouth-upperlip-volume-incr": 0.45, "mouth-scale-horiz-incr": -0.2,
    "mouth-cupidsbow-incr": 0.4, "mouth-angles-up": 0.3,
    "neck-scale-horiz-incr": -0.4, "neck-scale-depth-incr": -0.25, "forehead-nubian-incr": -0.2, "eyebrows-trans-up": 0.15,
})

# Body shaping on top of the phenotype axes: a defined waist, fuller hips, longer legs, lifted bust.
_HOURGLASS = {
    "measure-waist-circ-incr": -0.55, "measure-hips-circ-incr": 0.35, "buttocks-volume-incr": 0.4, "hip-waist-up": 0.3,
    "upperlegs-height-incr": 0.35, "lowerlegs-height-incr": 0.35, "measure-shoulder-dist-incr": -0.2,
    "stomach-tone-incr": 0.5, "breast-trans-up": 0.4, "breast-volume-vert-up": 0.4,
}
_FULLER = {**_HOURGLASS, "measure-waist-circ-incr": -0.7, "measure-hips-circ-incr": 0.55, "buttocks-volume-incr": 0.6,
               "breast-trans-up": 0.5, "breast-volume-vert-up": 0.5, "measure-thigh-circ-incr": 0.25,
               "l-upperleg-fat-incr": 0.2, "r-upperleg-fat-incr": 0.2, "measure-shoulder-dist-incr": -0.15}
_WILLOWY = {"measure-waist-circ-incr": -0.4, "measure-hips-circ-incr": 0.15, "buttocks-volume-incr": 0.3,
            "upperlegs-height-incr": 0.6, "lowerlegs-height-incr": 0.6, "stomach-tone-incr": 0.7,
            "breast-trans-up": 0.4, "breast-volume-vert-up": 0.3}

# A masculine face: heavier brow ridge, wider square jaw, firmer chin, narrower eyes, a larger nose, thinner lips, a thick neck.
_MASCULINE_FEATURES = _both({
    "eyebrows-trans-forward": 0.5, "forehead-trans-forward": 0.15, "chin-width-incr": 0.35, "chin-prominent-incr": 0.35,
    "chin-bones-incr": 0.45, "chin-height-incr": 0.15, "*-cheek-bones-incr": 0.25, "head-fat-incr": -0.25,
    "*-eye-scale-incr": -0.15, "*-eye-height1-incr": -0.25, "nose-scale-vert-incr": 0.15, "nose-width1-incr": 0.1,
    "mouth-upperlip-volume-incr": -0.35, "mouth-lowerlip-volume-incr": -0.1, "mouth-scale-horiz-incr": 0.1,
    "neck-scale-horiz-incr": 0.4, "measure-neck-circ-incr": 0.35,
})
# Broad shoulders over a narrow waist, the outline that reads as a fit man.
_V_TAPER = _both({
    "torso-vshape-incr": 0.6, "measure-shoulder-dist-incr": 0.3, "torso-muscle-pectoral-incr": 0.35, "torso-muscle-dorsi-incr": 0.35,
    "measure-waist-circ-incr": -0.25, "stomach-tone-incr": 0.6, "hip-scale-horiz-incr": -0.15,
    "*-upperarm-muscle-incr": 0.3, "*-upperarm-shoulder-muscle-incr": 0.1,
})
_ATHLETE = _both({
    "torso-muscle-pectoral-incr": 0.7, "torso-muscle-dorsi-incr": 0.6, "stomach-tone-incr": 0.9, "*-upperarm-muscle-incr": 0.6,
    "*-upperarm-shoulder-muscle-incr": 0.2, "*-lowerarm-muscle-incr": 0.5, "*-upperleg-muscle-incr": 0.5, "*-lowerleg-muscle-incr": 0.5,
})
# Men's skin paint: natural lips, no eye make-up, fuller brows, a matte finish.
_MALE_LOOK = dict(lip_strength=0.32, lip_gloss=0.04, lip_color=(0.70, 0.43, 0.40), eyeshadow_strength=0.0, blush_strength=0.04,
                  brow_thickness=1.6, brow_strength=0.95, brow_arch=0.6, lash_strength=0.40, lash_width=0.8, crease=0.35,
                  contour=0.6, skin_gloss=0.07, chest_tone_strength=0.22, flesh_variation=0.40, nail_strength=0.15,
                  muscle_definition=0.5)

# name -> dict(phenotype=..., face=..., look=..., stylize=...)
FIGURE_PRESETS = {
    "woman": dict(phenotype=dict(gender=1.0, age=0.776, muscle=0.5, weight=0.44, height=0.55, proportions=0.1, cupsize=0.68, firmness=0.85),
                  face={**_SHARP_JAW, **_FEMININE_FEATURES, **_HOURGLASS}),
    "woman_fuller": dict(phenotype=dict(gender=1.0, age=0.776, muscle=0.5, weight=0.47, height=0.55, proportions=0.1, cupsize=0.82, firmness=0.9),
                        face={**_SHARP_JAW, **_FEMININE_FEATURES, **_FULLER}),
    "woman_slender": dict(phenotype=dict(gender=1.0, age=0.776, muscle=0.62, weight=0.36, height=0.7, proportions=0.05, cupsize=0.6, firmness=0.9),
                          face={**_SHARP_JAW, **_FEMININE_FEATURES, **_WILLOWY}),
    "woman_soft": dict(phenotype=dict(gender=1.0, age=0.776, muscle=0.35, weight=0.52, height=0.5, proportions=0.2, cupsize=0.66, firmness=0.7),
                       face={**_FEMININE_FEATURES, **_HOURGLASS, "head-fat-incr": 0.1, "chin-width-incr": -0.2, "measure-waist-circ-incr": -0.3}),
    "woman_athletic": dict(phenotype=dict(gender=1.0, age=0.776, muscle=0.82, weight=0.42, height=0.62, proportions=0.05, cupsize=0.55, firmness=0.9),
                           face={**_SHARP_JAW, **_FEMININE_FEATURES, **_HOURGLASS, "stomach-tone-incr": 0.9},
                           look=dict(muscle_definition=0.35)),
    "woman_classical": dict(phenotype=dict(gender=1.0, age=0.778, muscle=0.4, weight=0.56, height=0.55, proportions=0.2, cupsize=0.6, firmness=0.8),
                            face={**_FEMININE_FEATURES, **_HOURGLASS, "nose-greek-incr": 0.7, "chin-width-incr": -0.3, "head-fat-incr": -0.1,
                                  "measure-waist-circ-incr": -0.3, "measure-hips-circ-incr": 0.45, "stomach-tone-incr": 0.0,
                                  "upperlegs-height-incr": 0.15, "lowerlegs-height-incr": 0.15}),
    "woman_mature": dict(phenotype=dict(gender=1.0, age=0.80, muscle=0.40, weight=0.50, height=0.55, proportions=0.3, cupsize=0.5, firmness=0.5),
                         face={**_FEMININE_FEATURES, "chin-width-incr": -0.3}),
    "woman_elder": dict(phenotype=dict(gender=1.0, age=0.97, muscle=0.30, weight=0.50, height=0.45, proportions=0.4, cupsize=0.5, firmness=0.3), face={}),
    "woman_anime": dict(phenotype=dict(gender=1.0, age=0.775, muscle=0.45, weight=0.38, height=0.55, proportions=0.0, cupsize=0.68, firmness=0.9),
                        face={**_SHARP_JAW, **_FEMININE_FEATURES, **_HOURGLASS, "upperlegs-height-incr": 0.6, "lowerlegs-height-incr": 0.6, "l-eye-scale-incr": 1.0, "r-eye-scale-incr": 1.0,
                              "l-eye-height1-incr": 0.9, "r-eye-height1-incr": 0.9,
                              "l-eye-height2-incr": 0.6, "r-eye-height2-incr": 0.6, "nose-scale-horiz-incr": -0.9,
                              "nose-scale-depth-incr": -0.6, "nose-scale-vert-incr": -0.4, "mouth-scale-horiz-incr": -0.5,
                              "chin-height-incr": -0.2, "head-scale-vert-incr": -0.15, "forehead-scale-vert-incr": 0.2,
                              "mouth-lowerlip-volume-incr": -0.2, "mouth-upperlip-volume-incr": -0.3, "nose-point-up": 0.5,
                              "nose-nostrils-width-incr": -0.6, "nose-flaring-incr": -0.6},
                        look=dict(iris_size=1.30, pupil_size=1.1, catchlight_size=1.7, lip_strength=0.28, lash_width=1.5, blush_strength=0.3),
                        stylize="anime"),
    "man": dict(phenotype=dict(gender=0.0, age=0.778, muscle=0.62, weight=0.46, height=0.62, proportions=0.12, cupsize=0.5, firmness=0.5),
                face={**_MASCULINE_FEATURES, **_V_TAPER}, look=_MALE_LOOK),
    "man_athletic": dict(phenotype=dict(gender=0.0, age=0.778, muscle=0.92, weight=0.46, height=0.66, proportions=0.05, cupsize=0.5, firmness=0.5),
                         face={**_MASCULINE_FEATURES, **_V_TAPER, **_ATHLETE}, look={**_MALE_LOOK, "muscle_definition": 1.0}),
    "man_slim": dict(phenotype=dict(gender=0.0, age=0.775, muscle=0.55, weight=0.36, height=0.62, proportions=0.08, cupsize=0.5, firmness=0.5),
                     face={**_MASCULINE_FEATURES, **_SHARP_JAW, "chin-width-incr": -0.2, "torso-vshape-incr": 0.3, "stomach-tone-incr": 0.6},
                     look={**_MALE_LOOK, "muscle_definition": 0.5}),
    "man_classical": dict(phenotype=dict(gender=0.0, age=0.776, muscle=0.80, weight=0.48, height=0.62, proportions=0.10, cupsize=0.5, firmness=0.5),
                          face={**_MASCULINE_FEATURES, **_V_TAPER, **_ATHLETE, "nose-greek-incr": 0.7, "nose-hump-incr": -0.3,
                                "mouth-upperlip-volume-incr": 0.1, "mouth-cupidsbow-incr": 0.4},
                          look={**_MALE_LOOK, "muscle_definition": 0.85}),
    "man_mature": dict(phenotype=dict(gender=0.0, age=0.82, muscle=0.60, weight=0.52, height=0.6, proportions=0.25, cupsize=0.5, firmness=0.5),
                       face={**_MASCULINE_FEATURES, **_V_TAPER, "torso-vshape-incr": 0.2, "stomach-tone-incr": 0.0},
                       look={**_MALE_LOOK, "flesh_variation": 0.5}),
    "man_elder": dict(phenotype=dict(gender=0.0, age=0.98, muscle=0.40, weight=0.52, height=0.5, proportions=0.4, cupsize=0.5, firmness=0.5),
                      face={**_MASCULINE_FEATURES}, look={**_MALE_LOOK, "brow_color": (0.6, 0.6, 0.6), "flesh_variation": 0.5}),
    "man_anime": dict(phenotype=dict(gender=0.0, age=0.775, muscle=0.62, weight=0.40, height=0.66, proportions=0.0, cupsize=0.5, firmness=0.5),
                      face={**_MASCULINE_FEATURES, **_SHARP_JAW, **_V_TAPER, "upperlegs-height-incr": 0.5, "lowerlegs-height-incr": 0.5,
                            "chin-width-incr": -0.3, "nose-scale-horiz-incr": -0.4, "mouth-scale-horiz-incr": -0.3},
                      look={**_MALE_LOOK, "iris_size": 1.2, "catchlight_size": 1.4, "lash_strength": 0.55, "muscle_definition": 0.6},
                      stylize="semi"),
    "androgynous": dict(phenotype=dict(gender=0.55, age=0.775, muscle=0.45, weight=0.38, height=0.58, proportions=0.1, cupsize=0.2, firmness=0.7),
                        face={**_SHARP_JAW, "l-eye-scale-incr": 0.2, "r-eye-scale-incr": 0.2}, look=dict(lip_strength=0.4)),
}

EXPRESSIONS = {
    "neutral": {},
    "soft_smile": {"mouthSmileLeft": 0.45, "mouthSmileRight": 0.45, "cheekSquintLeft": 0.2, "cheekSquintRight": 0.2},
    "smile": {"mouthSmileLeft": 0.8, "mouthSmileRight": 0.8, "cheekSquintLeft": 0.5, "cheekSquintRight": 0.5, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3},
    "serene": {"mouthSmileLeft": 0.2, "mouthSmileRight": 0.2, "eyeBlinkLeft": 0.25, "eyeBlinkRight": 0.25},
    "eyes_closed": {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0, "mouthSmileLeft": 0.15, "mouthSmileRight": 0.15},
    "serious": {"browDownLeft": 0.5, "browDownRight": 0.5, "mouthPressLeft": 0.3, "mouthPressRight": 0.3},
    "determined": {"browDownLeft": 0.75, "browDownRight": 0.75, "eyeSquintLeft": 0.35, "eyeSquintRight": 0.35, "mouthPressLeft": 0.4, "mouthPressRight": 0.4, "jawForward": 0.2},
    "sad": {"browInnerUp": 0.8, "mouthFrownLeft": 0.6, "mouthFrownRight": 0.6, "eyeBlinkLeft": 0.2, "eyeBlinkRight": 0.2},
    "surprised": {"browInnerUp": 0.7, "browOuterUpLeft": 0.7, "browOuterUpRight": 0.7, "eyeWideLeft": 0.8, "eyeWideRight": 0.8, "jawOpen": 0.3},
    "angry": {"browDownLeft": 1.0, "browDownRight": 1.0, "noseSneerLeft": 0.5, "noseSneerRight": 0.5, "mouthFrownLeft": 0.4, "mouthFrownRight": 0.4, "eyeSquintLeft": 0.4, "eyeSquintRight": 0.4},
    "melancholy": {"browInnerUp": 0.45, "eyeLookDownLeft": 0.4, "eyeLookDownRight": 0.4, "eyeBlinkLeft": 0.3, "eyeBlinkRight": 0.3, "mouthFrownLeft": 0.2, "mouthFrownRight": 0.2},
    "smirk": {"mouthSmileLeft": 0.6, "mouthDimpleLeft": 0.3, "browOuterUpRight": 0.3, "eyeSquintLeft": 0.2},
}
