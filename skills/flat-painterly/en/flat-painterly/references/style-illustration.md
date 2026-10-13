# Illustration Style

A style that stacks flat shapes from a limited palette and shades them with stipple grains. Suits posters, picture books and cover art. Examples are `examples/illustration_moonlit_camp.py` (landscape), `illustration_autumn_walk.py` (full figure), `illustration_fantasy_walk.py` (two travelers walking hand in hand) and `illustration_doomer_rooftop.py` (two people looking down at a night estate from a roof).

## Visual Traits

- Forms separate by value differences between color fields, with no outlines
- Shapes are simple and geometric, and details are left out
- Brightness changes are expressed by stipple with scattered grains
- A rough texture of paper and ink lies over the whole frame

## Workflow

1. Fix the palette first
    + 4-6 value steps of one hue family fill most of the frame
    + 1-2 complementary accents are used only at the focal point
2. Lay the background as flat bands or large shapes
    + The sky stacks bands of different values and loosens the band borders with stipple
3. Stack shapes from back to front
    + Far things are lighter and less saturated, near things darker, which separates the layers
    + `g.polygon` for straight-edged shapes, `g.spline` for curved shapes
4. Add stipple shading
    + `cv.fill(cv.shape(path, soft=20-50), color, clip=parent, grain=1.0)`
    + For round objects, paint the result of `cv.form_shadow(shape, light, amount, soft=0.5)` with grain=1.0
    + Light glows (campfire, window light) are also soft ellipses painted with grain=1.0
    + For backlit objects, paint the contour band from `cv.edge_light(shape, light, width, soft)` with grain=1.0
5. Repeated elements (trees, stars, ripples) get one generator function that places them with random size and position jitter
6. Apply `illustration.render(canvas)`

## Stipple Shading

- A larger soft value spreads the grains wider
    + soft 10-16 for small objects, 30-50 for mountains or sky
- Shading colors are neighboring steps within the palette
    + Making no new colors keeps the unity of the limited palette
- Always set clip so grains stay inside the parent shape

## Pass Arguments

| Argument | Default | Adjustment |
|---|---|---|
| `roughness` | 0.8 | Fine contour jitter. Raise it for a hand-cut paper feel |
| `ink_mottle` | 0.10 | Blotches with less ink. Most visible on dark color fields |
| `paper_tint` | cream | White gives a cold, modern impression |
| `paper_fiber` | 0.05 | Paper fiber texture |
| `misregister` | 0 | 1-2 gives the feel of a misregistered print |

## Common Defects

| Symptom | Remedy |
|---|---|
| Layers stick together | Increase the value difference between neighboring layers |
| Stipple looks like dirty stains | Reduce soft and move the shading color to a step closer to the base |
| The frame looks flat | Stand a large dark shape at the front edge to frame the picture and put the accent at the focal point |
| Repeated shapes look stamped | Jitter height, spacing and tilt with random values |
| White background shows between shapes | Extend the back shape well under the front shape |

## 3D Figures

- Figures painted with `character.paint_figure` keep their bold, dark lines (`line_width` 2.4) and first shadow and go through the print texture pass
    + Keep the background as flat color fields with `fill(grain=1.0)` to match the cel shadows and texture of the figures
