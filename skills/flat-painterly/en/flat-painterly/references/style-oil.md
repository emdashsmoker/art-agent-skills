# Oil Style

A style that repaints a smooth underpainting as a set of brushstrokes and then adds the relief of paint thickness. Examples are `examples/oil_harbor_sunset.py` (sea), `oil_summer_fields.py` (fields), `oil_figure_study.py` and `oil_reclining_figure.py` (figure), `oil_evening_dance.py` (two people dancing), `oil_doomer_overpass.py` (a knee-up woman and a chimney) and `oil_doomer_pylons.py` (a snowfield and pylon panorama).

## Visual Traits

- Directional brush marks cover the whole frame
- Each stroke differs a little in color, so mixed color shows up close
- Paint thickness catches the light and raises the brush texture
- Details emerge from clusters of small strokes, and there are no outlines

## Workflow

1. Paint large color fields with gradients: sky, water, ground
2. Lay clouds, terrain and objects over the underpainting
    + The underpainting may be smooth. The pass creates the brush marks
    + Small touches (glitter on water, reflections, leaves) are dozens of ellipses scattered at random
3. Set the stroke direction per area with `canvas.direct`
    + Water horizontal (angle 0), grass and sails near vertical, sky a gentle diagonal
    + Around the sun and moon, a circular direction with `around=center`
    + Where nothing is set, the pass computes a direction that follows color edges
    + Keep broad background directions near horizontal. Steep diagonals catch the eye before the subject
4. Apply `oil.render(canvas, brush_radii, detail)`
5. Match the hues of shade and light with `post.grade` and finish with `post.vignette`

## Pass Arguments

| Argument | Default | Adjustment |
|---|---|---|
| `brush_radii` | (22, 10, 4.5) | Large brush to small brush. If details smear, add a smaller value such as 2.4 at the end |
| `detail` | None | With a shape, the smallest brush is used only inside it. Gives detail to the focal point only |
| `relief` | 0.55 | Paint-thickness relief. 0 gives a flat gouache feel |
| `weave` | 0.05 | Strength of the canvas weave |
| `color_jitter` | 0.05 | Color difference between strokes. Raise it for broken Impressionist color |

- Brush sizes are logical units, so a higher scale paints the same picture with finer strokes
- The pass adds small brushes only where the difference from the underpainting is large
    + Give clear color contrast in the underpainting where detail is needed

## Underpainting Tips

- Keep clear value differences between color fields
    + When similar colors touch, strokes cross the border and blur the form
- Draw focal objects well above the brush radius
    + An object only a few times the smallest brush diameter turns into a few strokes and becomes hard to recognize
- Paint backlit clouds dark on top and light below
- For a path of light on water, scatter long horizontal ellipses under the light source, larger and wider toward the viewer
- For reflections, stack horizontal ellipses of the object color downward and fade them as they go down

## Common Defects

| Symptom | Remedy |
|---|---|
| Rows of same-size dots on flat areas | Set a direction there with `direct` so long strokes come out |
| Pure-hue stains on dark surfaces | Lower `color_jitter` |
| The focal object smears | Add a small value at the end of `brush_radii`, limit its range with `detail` and raise scale |
| Rough relief makes the picture messy | Lower `relief` to about 0.3 |
| Solid shading weakens after the pass | Widen the value gap between the light and shade sides in the underpainting |
| Skin or porcelain loses its smoothness | Lower `relief` to 0.4 and `color_jitter` to 0.035, and gather small brushes there with `detail` |

## Sources

> Hertzmann (1998), Painterly Rendering with Curved Brush Strokes of Multiple Sizes (https://mrl.cs.nyu.edu/publications/painterly98/hertzmann-siggraph98.pdf)

## 3D Figures

- Figures painted with `character.paint_figure` can also go through the oil pass
    + Use an Ink that nearly removes lines (`line_opacity` 0.28) and softens shadow borders (`shadow_soft` 0.45)
    + Set the pass's `detail` around the face and the held hands so small brushes gather at the focal point
