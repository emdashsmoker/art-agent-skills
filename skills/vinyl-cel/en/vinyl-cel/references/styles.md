# Style recipes

## Contents

- Shared structure
- Anime
- Illust
- Painterly
- Colour grades
- Adding a style

## Shared structure

- A style is one `config.Style` and one finishing function in `finish.py`
    + `Style` decides the shading mode and the lines while drawing
    + The finishing function decides the surface of the whole picture (light, grain, brushwork)
- Scene scripts pass only the style name
    + The same layout branches into 3 styles, so figure data is not rebuilt per style

| `Style` field | Meaning |
|---|---|
| `shade_mode` | `CEL` (two tones) or `SOFT` (continuous) |
| `line_width` | Outline width (canvas units), 0 for no lines |
| `line_opacity` | Outline opacity |
| `shadow_edge` | Blur of cast shadow edges (canvas units) |
| `shadow_opacity` | Shadow strength |
| `cel_threshold` | Share of light at which the cel shadow starts |
| `detail_line_opacity` | Strength of hair strands and cloth folds |

## Anime

- (Drawing) Two-tone cel shading, coloured line art, a jagged hair highlight
- (Finish) `finish._finish_anime`
    + A soft cool-coloured gradient over the whole figure (`AIRBRUSH_SHADE`, `AIRBRUSH_STRENGTH`)
    + Rim light on the silhouette facing the light (`RIM_SHIFT_UNITS`, `RIM_STRENGTH`)
    + Bloom in bright areas (`BLOOM_THRESHOLD`, `BLOOM_RADIUS_UNITS`, `BLOOM_STRENGTH`)
    + Saturation tuning and fine grain
- (Tuning) If lines are thin, raise `line_width` from 2.3 to 3.0; if shadows are too wide, lower `cel_threshold` from 0.80 to 0.72

## Illust

- (Drawing) Soft shading, no lines, a smooth hair highlight, lips drawn as shapes
- (Finish) `finish._finish_illust`
    + Low-frequency noise wobbles edges by 1-2 units for a hand-cut feel (`EDGE_WOBBLE_UNITS`)
    + Paper fibres and grain are multiplied in (`PAPER_GRAIN`)
    + Saturation is lowered slightly
- (Tuning) For a flatter look, lower `shadow_opacity` from 0.72 to 0.5

## Painterly

- (Drawing) The same soft-shaded underpainting as illust
- (Finish) `finish._finish_painterly`
    + Chiaroscuro that sinks the side away from the light (`CHIAROSCURO_SHADE`, `CHIAROSCURO_STRENGTH`)
    + Gamma and a warm tint give oil-paint mid tones (`PAINT_GAMMA`, `PAINT_WARMTH`)
    + `brushwork.paint()` rebuilds the underpainting with brush strokes
- (Brush algorithm) 6 layers are stacked from large brushes to small (radii 30, 15, 7.5, 3.6, 1.8, 0.9 units)
    + Each layer blurs the underpainting to the brush size and places strokes only where the current picture differs strongly in colour
    + Strokes run perpendicular to the brightness gradient, that is along the contours
    + The 3 finest layers apply only where the importance map is at least 0.25, 0.80 and 0.95 (`DETAIL_FLOOR`)
    + Eyes and mouth get importance 1.0, faces 0.5 to 1.0 by size (`finish.SMALL_FACE_UNITS`): 1.0 when the visible face is 100 units wide or less, 0.5 at 160 units or more
    + So even small figures in a scene get their eyes, brows and mouth painted with the finest brush, while large portraits keep the v5 brushwork
    + Hand-sized objects in 3D scenes have `Prop3D.detail` 0.85 and get down to the finest brush, so keyboards and screens do not smear
    + The paint thickness of each stroke is recorded and lit to show relief
- (Tuning) The constants are at the top of `brushwork.py`
    + For a rougher picture, drop the last value of `BRUSH_RADII_UNITS` and raise `STROKE_STEPS`
    + Relief is `IMPASTO_STRENGTH`, canvas weave is `CANVAS_WEAVE_STRENGTH`
- (Source) The layered brushwork follows the method of the paper below

> Hertzmann(1998), Painterly Rendering with Curved Brush Strokes of Multiple Sizes, SIGGRAPH 98(https://dl.acm.org/doi/10.1145/280814.280951)

## Colour grades

- A separate step laid over the style's finish (`grade.apply`), combined with all 3 styles
    + The order is halation (an orange bloom round bright lights), saturation, split toning (colour leaning of shadows and highlights), fade and contrast, vignette, film grain
- The doomer presets are `doomer` (night) and `doomer_day` (overcast day)
    + `doomer`: saturation x0.55, teal shadows `#1E4650`, orange highlights `#F2A866`, black lifted by 0.07, contrast 0.88, grain 0.034
    + `doomer_day`: saturation x0.45, shadows `#2E4A50`, highlights `#DCD8C8`, black lifted by 0.10, weak halation
- The warm presets are `cozy_night` (a room at night), `late_sun` (a window in the late afternoon) and `golden_hour` (outdoors at sunset)
    + Shared values are saturation x0.92-0.95, black lifted by 0.03, contrast 0.96-0.97 and grain 0.014-0.016, leaving only a hint of film
    + `cozy_night`: indigo shadows `#24305C`, highlights `#FFD6A0`, halation threshold 0.78
    + `late_sun`: shadows `#3A4E70`, highlights `#FFDDA8`, vignette 0.22
    + `golden_hour`: violet shadows `#3A3466`, highlights `#FFC88C`, halation threshold 0.88 (a bright face does not bloom)
- A scene's default is `run_cli(..., grade="doomer")`, switched on the command line with `--grade none|doomer|doomer_day|cozy_night|late_sun|golden_hour`
- A new grade is a `grade.Grade(...)` value registered in `grade.GRADES`
- Effects that brushwork and lines must not touch, such as falling snow, go in `canvas.overlays` and are drawn between the finish and the grade

## Adding a style

1. Add the name to `config.StyleName`
2. Add a `Style` value to `config.STYLES`
3. Write a finishing function in `finish.py` and connect it in the branches of `apply()`
    + A style missing from the branches raises an error, so the omission shows
4. Add a background branch to `compose()` in `scene_template.py`
5. Run `selftest.py` and check a preview
