# Style Renderers

> Translated from the Korean original. Where the two editions disagree, follow the Korean edition.

All 4 styles take the same layers as input. They differ only in how they composite them.

Common rules:
- Groups `bg`, `lash`, `brow`, `sky`, `emissive`, `scenery`, `screen` receive no shading (designed colors or self-lit).
- Shadows of group `body` (the mannequin body) are cleaned up before style compositing (`styles.simplify_shadow`).
    + Narrow light gaps between shadows are filled with a grayscale closing (`SHADOW_SIMPLIFY`)
    + Small light islands enclosed by shadow are found by their bright core (`LIT_CORE`) and merged into the shadow out to a surrounding ring (`ISLAND_HALO`) (`SHADOW_HOLE_AREA`)
    + Thin terminator bands that follow the silhouette are real form, so no opening removes them
    + In anime cel, the edge of the body's self shadow is cut with a narrower width than designed shadows (`BODY_SHAPE_EDGE`)
- Groups `bg`, `sky` are treated as the backdrop. Oil paints the backdrop separately with large brushes; watercolor leaves a paper margin at the backdrop edges.
- Mannequin forms (body, hands, still life) pass depth-based normals, self shadow and Blinn gloss as layers. The styles use them as they are.

## Contents
- Anime cel
- Soft illustration
- Oil
- Watercolor
- Color grade looks
- Common tuning order

## Anime Cel (`styles.render_anime`)

Reproduces the layer stack of digital cel painting (flat color, multiply shadow, screen highlight, line art).

- Shadow = the maximum of 3 sources: form shading, cast shadow, designed shadow shapes
    + Form shading applies where the normal dot product is below `cel_threshold`, with a 1-2 px antialiased edge
    + Only the hair gets a second cel level (a deeper shadow) to show its layers
- Highlights show only on lit faces, with hard edges
- Line art goes on last

Tuning points:
- Shadow area: spec `cel_threshold.<group>`
- Shadow color: spec `shadow_tint.<group>`
- Edge softness: `styles.CEL_EDGE`

## Soft Illustration (`styles.render_illustration`)

Soft coloring in the manner of light novel covers.

- Form shading turns into a gradient 0.4 wide
- A wide, weak blur around cast shadows adds contact shadows
- Rim light on the silhouette opposite the light (spec `light.rim_color`, `light.rim_strength`)
- Line art opacity 0.85, bloom on bright areas, color grading with blue-violet shadows and cream highlights, fine grain

The shared function `styles.soft_shaded` covers everything up to the line art stage, and oil reuses it.

## Oil (`painterly.render_oil`)

Based on the multi-size curved brush stroke algorithm of Hertzmann (1998), with 4 added stages.

1. Ground: a single color, the darkened mean color of the picture
2. Background blocking: paints only the backdrop with 3 levels of large brushes sized by canvas width (`OIL_BG_BRUSHES`, smaller `OIL_SCENE_BG_BRUSHES` for scenes)
3. Figure underpainting and strokes: lays a blurred base color inside material boundaries only, then covers it with 4 brush levels sized by head width (`OIL_FIG_BRUSHES`)
    + Strokes bend along a structure tensor direction field and stop at material boundaries (cut-out edges)
    + The finest brush is used only on skin and facial features
4. Finish: eyes and lips keep 65% of the precise render (`OIL_DETAIL_KEEP`), dense edge areas (window grids, fingers, fruit rims) keep 40% (`OIL_BUSY_KEEP`). Then line integral convolution (LIC) for bristle marks, value-based impasto relief and canvas weave lighting

Tuning points:
- If the strokes are rough, reduce `OIL_FIG_BRUSHES`; if too smooth, enlarge them
- If there are too many strokes, raise `OIL_ERROR_T` (it must exceed the color jitter to stop endless repainting)
- If the face is too painterly, raise `OIL_SKIN_KEEP`, `OIL_DETAIL_KEEP`
- If small details smear, raise `OIL_BUSY_KEEP`
- Time is proportional to the stroke count. A 1024 x 1280 bust takes about 12 s, a 1400 x 900 scene about 8-12 s

## Watercolor (`painterly.render_watercolor`)

Based on the pigment density model of Bousseau et al. (2006), it imitates 5 physical effects of watercolor.

| Effect | Implementation | Constant |
|---|---|---|
| Transparent layers | Lighten the flat colors by 10%, then multiply shadows as a glaze | 0.10, 0.85 in code |
| Edge darkening | Higher pigment density just inside each material region's edge | `WC_EDGE_DARKEN` |
| Turbulent blotches | Density modulated by low-frequency noise | `WC_TURBULENCE` |
| Granulation | Density modulated by high-frequency noise | `WC_GRANULATION` |
| Edge wobble | Region edges displaced by noise | `WC_WOBBLE_PX` |

Additional stages:
- Highlights are the paper color where paint has been lifted
- The background wash stops short with an irregular margin
- Paper fiber texture, pencil under-drawing (`WC_PENCIL`), stronger lines on facial features only

## Color Grade Looks (`looks.apply_look`)

The spec `look` is applied once to the whole image after the style renderer finishes. It reads no layers, so it works the same way on all 4 styles.

`doomer` (`looks.DOOMER`) processing order:
1. Lower saturation to `saturation` (0.46). Pixels that are strongly reddish (`warm_hue`) and bright (`warm_value`) keep saturation up to `warm_saturation` (0.95), so only street lamps, lit windows and light bulbs stay orange
2. Multiply darker tones by `shadow_tint` to turn shadows blue. Warm light pixels are excluded
3. Reduce contrast by `contrast` and lift black to `lift` (blue-gray) like faded film
4. Darken the corners by `vignette` and add luminance noise of strength `grain`, slightly clumped by `grain_blur`. The noise seed comes from `canvas.seed`

Tuning: if skin looks ashen, raise `saturation`; if the lights look dull, lower the lower bound of `warm_value`; if the grain is coarse, lower `grain`.

## Common Tuning Order

1. If the form is wrong, fix the rig (spec `character.*`) first. A style cannot hide form defects.
2. If the values are wrong, fix the light (`light.direction`) and `cel_threshold`.
3. If the colors are wrong, fix `palette` and `shadow_tint`.
4. If the texture is wrong, fix the style constants.

Style constants are defined in proportion to the image size. Oil figure brushes scale with head width, background brushes with canvas width.

## References

- Hertzmann, A. (1998). Painterly Rendering with Curved Brush Strokes of Multiple Sizes. SIGGRAPH.
- Bousseau, A., Kaplan, M., Thollot, J., Sillion, F. (2006). Interactive Watercolor Rendering with Temporal Coherence and Abstraction. NPAR.
- Cabral, B., Leedom, L. (1993). Imaging Vector Fields Using Line Integral Convolution. SIGGRAPH.
