# Watercolor Style

A style that glazes clear colors on white paper and adds traces of water, pigment and paper. Examples are `examples/watercolor_robin.py` (bird and blossoms), `watercolor_still_life.py` (still life), `watercolor_old_town.py` (pen-and-wash street), `watercolor_hand_studies.py` (hand studies), `watercolor_street_walk.py` (two people walking hand in hand), `watercolor_doomer_block.py` (a panel apartment block seen from below) and `watercolor_doomer_kitchen.py` (objects in a kitchen at night).

## Visual Traits

- The brightest areas are unpainted, reserved paper
- Paint gathers at the edges of brush marks and forms dark rims
- Density mottles even within one brush mark, and pigment settles into the paper grain
- Where colors overlap, the two mix and darken
- The picture leaves part of the frame open, and the background wash ends irregularly

## Workflow

1. Start on a canvas with a white background
2. Background wash: overlap 2-4 large `g.blob` shapes with `watercolor.wash(..., soft=30-50, rough=20)`
    + A pale wash of the subject's complement behind it makes the subject stand out
    + Dabs of white at low opacity inside the wash make spots where water pooled and dried
    + Scatter paint droplets with `motifs.splatter`
3. Base wash of the subject: paint the whole silhouette in its lightest color
    + White parts stay paper color, and only shade goes in lightly with `form_shadow(soft=0.3)` and `Blend.MULTIPLY`
4. Glazing: stack darker colors with `Blend.MULTIPLY`
    + Give the shapes soft where two colors meet so they seep into each other
    + Add darker blotches of the same color with `canvas.mottle`
5. Dry-brush details: the darkest, crispest things such as eyes, beaks, twigs and stamens come last
6. Apply `watercolor.render(canvas)`

## wash Arguments

| Argument | Default | Adjustment |
|---|---|---|
| `opacity` | 0.85 | 0.45-0.75 for backgrounds, 0.85-0.95 for subjects |
| `soft` | 6 | Bleed width on wet paper. 1.5-2.5 for crisp parts, 30-50 for backgrounds |
| `rough` | 7 | Edge wobble. 2-3 for small parts |
| `cover` | False | True for front objects that must not let the object behind show through |

## Pass Arguments

| Argument | Default | Adjustment |
|---|---|---|
| `wobble` | 2.2 | Contour wobble. Lower it if small details distort |
| `bleed` | 0.55 | Overall bleeding. Higher is softer, lower is crisper |
| `turbulence` | 0.30 | Strength of large blotches |
| `granulation` | 0.22 | Strength of grains settling into the paper grain |
| `edge` | 0.55 | Strength of the edge rims |

## Color

- Keep underpainting colors lighter and clearer than the finished picture
    + The edge pooling of the pass and multiply glazing darken the colors
- Use saturated color on one part of the subject only, and build the rest from pale colors thinned with plenty of water
- Use dark brown or navy for the darkest darks

## Common Defects

| Symptom | Remedy |
|---|---|
| A branch behind shows through the bird in front | `cover=True` on the wash of the front object |
| Overlapping background washes are too dark | Lower the opacity of the background washes or reduce the overlap |
| Stiff like a vector drawing | Raise soft and rough on large areas and add blotches with `mottle` |
| Everything looks blurry | Lower `bleed` and draw the final details without soft |
| A white object loses its form | Lay a background wash behind it and add shade lightly with MULTIPLY |
| Straight lines of buildings and objects go wobbly | Reduce the wash to soft 1.5 and rough 2.5, and lower the pass wobble to 1.4 or less |

## Sources

> Bousseau, Kaplan, Thollot, Sillion (2006), Interactive watercolor rendering with temporal coherence and abstraction (https://dl.acm.org/doi/10.1145/1124728.1124751)

## 3D Figures

- Figures painted with `character.paint_figure` use an Ink with thin, pale lines (`line_opacity` 0.55) and then go through the watercolor pass
    + Keep skin and clothes in clear, light colors and glaze only the background with `wash`
    + Around wobble 1.6 and bleed 0.65 in the pass, figure contours bleed while faces stay readable
