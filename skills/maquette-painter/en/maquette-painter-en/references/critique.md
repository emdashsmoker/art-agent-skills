# Review and defect remedies

> Translated from the Korean original. See the translation notice in `SKILL.md`.

## Contents
- Review order
- Checks by stage
- Defects and remedies
- Reading the buffers
- Numeric checks
- Known limits

## Review order

- Overall impression: does the subject read at once when the picture is viewed small?
- Structure: are shapes, proportions and overlap order right?
- Values: is the light direction consistent, and do the value masses separate?
- Colour: does the scheme match the plan, and is the accent colour at the focal point?
- Details: enlarge faces, hands and edges (`qa.zoom`) and check them
- Medium: does the texture help the picture? (texture that buries the forms is too much)

## Checks by stage

### Rough
- Position and size of the subject match the composition plan
- The figure is not cut at a joint
- Subject and background separate in the three-value study
- No unintended empty band or cut-off shape along the edges

### Figures
- Both eyes sit inside the face and are not overly hidden by the fringe
- The face is not split in half by shadow (unless strong lighting is intended)
- The hand and foot check prints (5, 5), or the reason for hidden digits is explained
- Neck and shoulders join naturally
- No skin pokes through the clothing
- Feet touch the ground and have a contact shadow

### Landscapes
- Contrast and saturation rise from far distance to foreground
- The horizon does not run through the exact middle (except in symmetric compositions)
- Water reflections match the landscape above
- Trees and rocks are sized for their distance

### Still lifes
- Objects look like they rest on the table (shadow directions agree)
- Objects overlap, so depth reads
- The brightest highlights are limited to one or two places

### Final render
- The traits of the style show (bleeding in watercolour, brushwork in oil, crisp edges in cel)
- Detail holds in the focus area (the face)
- Finishing effects are not overdone

## Defects and remedies

| Defect | Cause | Remedy |
|---|---|---|
| Half the face is dark | Side lighting and strong form shading | `--light soft_front`, `draw(face_flatten=0.8)`, or move azimuth toward 0 |
| Eyes hidden by the fringe | The fringe ends below the brows | Change fringe to wispy, parted or none |
| Facial features smeared | Brush larger than the face | Raise `--scale`, shrink oil `focus_radii`, crop closer |
| Figure looks like a mannequin | Upright symmetric pose, even lighting | contrapposto, twist and side on the head, side lighting |
| Limbs pass through the body | Joint angles too large | Reduce the joint values and check with `--rough` |
| Clothes puff up like balloons | Too much ease, layering | Reduce `ease`, fewer outer layers |
| Blotchy clothing shading | Fold shading clashes with cel bands | Garment `folds=0`, raise cel `simplify` |
| Lines too thick or too faint | Line width relative to figure size | Set `draw(line_width=...)` |
| Figure blends into the background | Similar values | Put the background at the opposite value, or place a light or dark shape behind the figure |
| Flat landscape | Too little depth difference and haze | Widen the depth gaps between layers, `haze_strength` 0.4-0.6 |
| Muddy watercolour | Too many shadow glazes | `glazes=1`, `strength` 0.75, raise `vivid` |
| Watercolour bleeding breaks the forms | Too much wetness and wobble | `wetness` 0.2, `wobble_px` 1.5 |
| Blurry oil | Only large brushes, high threshold | Add small values to radii, `threshold` 0.04 |
| Slow oil render | Resolution and fine brushes | Check at `--scale 0.75`, render the final at full scale |
| Ink painting turns into grey masses | Too little value contrast in the source | Make the structure colours clearly light or dark, raise `mist` |
| Colours differ from the plan | Influence of light and shadow colours | Neutralise with `Light(color="#ffffff")`, or `unlit=True` for that area |
| Picture clumps dark or bright | Skewed value range | `finish.grade(exposure=..., contrast=...)` |
| Messy highlights | Gloss clashes with hair-strand shading | `Hair(gloss=0, strand=0)`, garment `gloss=0` |
| Hands look like lumps | Hands drawn small, fingers overlapping | Hand preset open or grace, crop closer |
| Objects look like they float | No contact shadow | For still lifes, redraw after `objects.use_light(light)`; for figures, `scenery.contact_shadow` |
| Shadows look like stickers on the wall | Shadow moved flat across the plane | Objects: `floor_shadow` lays it on the table; buildings: `city.cast_shadows` |
| Bust or buttocks look stuck on | Crease where masses meet | Set a `blend` value in the mass dictionary, bust 1.2 or less |
| Torso as thin as a plank in profile | Too little cross-section depth | Check front and back values in the torso table (about 0.7 HU front to back at the waist) |
| Face outline breaks into dots | In enlarged renders a step spans several pixels | The engine measures steps over 0.004 head units; raise `line_width` to compensate |
| The whole street is in shade | Low sun or sun from the side (that is real) | Light azimuth near -30, elevation near 45 |
| Clouds look like ink blots (watercolour) | Too much cloud relief | `clouds(volume=0.2)` or 0 |
| Snowflakes invisible | White snow has the same value as a bright sky | Compose so snow falls in front of dark woods, buildings or figures; raise near for large flakes |
| Rain streaks lost in the medium | Thin lines absorbed by brushwork or value steps | `weather(..., crisp=True)` (default for rain), raise amount |
| Wet ground too mirror-like | Reflection too strong | `wet_reflection(strength=0.35)`, raise ripple |
| The hand holding the umbrella looks empty | Handle drawn behind the figure | `umbrella(part="back")` before the figure, `part="front"` after it with a clip that cuts out the hand mask |
| Pastel picture speckled with grey dots | Dark tinted paper shows between light strokes (the nature of pastel) | Lighter paper via `style_params`, grain 0.4-0.5 |
| Impressionist strokes bury the forms | Large brushes and strong colour jitter | `style_params` radii (12, 6, 3), hue_jitter 0.02, jitter 0.04 |
| Leaf clumps of a big tree look like huge blots | Clump size scales with the crown | `broadleaf(density=2-3)` |
| Wall in a candle scene is flatly dark | No brightness on the wall around the light | Halo on the wall with `objects.backdrop(glow=(candle x, flame y, radius), glow_color)` |
| A walking leg shows through a skirt or dress | The leg pierces the front corner of the cone cross-section | Shorter stride; kimono and hanbok skirt wrap their corners automatically |
| A face in a night scene floats like a white mask | Light skin and a bright key colour | skin fair or darker, a darker key colour (mercury lamp `#a4b4d4`), cel `key_color` 0.5-0.7 |
| Overhead wires invisible (doomer, watercolour) | The style fades the line layer | `city.wires(..., painted=True, width=1.4-1.6)` |
| A backlit figure from behind is only a black mass | The cel medium draws no rim light | Light `rim` 0.8-0.9 with cel `rim=1.0` (included in the doomer preset) |
| A snowfield at night turns into a black void | Low-angle light barely reaches the ground | Paint the snow as an `unlit=True` gradient and set directly how bright the town glow makes it (`doomer_duo.py`) |
| Smoke twists into figure-eight loops | Strand sway period too long | `smoke(strands=4-5, drift=0.1-0.25)`; for chimneys lay it sideways with drift 3-4 |
| Hanbok skirt covers the arms | With hands in front of the body the arms fall inside the skirt cross-section | Push the hand targets 0.9 HU or more in front of the body, or lower the arms to the sides |
| Thin bands (fundoshi, sarashi) look puffed up | Stamping torso cross-sections overshoots roundly at band ends | Lower the band mass roundness (`BAND_ROUNDNESS`) |

## Reading the buffers

The six images of `python scene.py --buffers`.

| Buffer | Healthy | Warning sign |
|---|---|---|
| albedo | Clean unlit local colour in each region | Colour leaks or holes (drawing order, clip problems) |
| normal | Rainbow-like gradients on round forms, uniform on planes | Sudden stripes inside a form (masses colliding) |
| light | Bright toward the light, dark on the far side | All dark or blotchy (light direction, too much shadow) |
| region | A different colour for each region | Regions mixed (duplicate names, order problems) |
| line | Lines only on outlines and overlaps | Unwanted lines inside forms (lower crease) |
| depth | Darker when nearer | Background and figure share a value (missing layer depth) |

- A defect that shows in albedo comes from the structure code; one that first shows in light comes from lighting or form; one that shows only in the final render comes from the medium parameters

## Numeric checks

The `image check` items printed by the final render of `studio.run`.

| Item | Meaning | Watch range |
|---|---|---|
| value_range | 2nd and 98th percentile values | A range under 0.35 looks flat |
| contrast | Width of that range | 0.4-0.85 depending on style |
| mean_value | Mean value | Below 0.25 or above 0.8, confirm it is intended |
| clipped_white, clipped_black | Share of blown whites and crushed blacks | Above 0.05 |
| saturation | Mean saturation | Below 0.03 is close to grey |

- The numbers support the review; they never replace looking at the image

## Known limits

- Bodies are smooth masses with added muscle tone (sternocleidomastoid, shoulder blades, dimples of Venus, male abdominals and so on); fine relief such as tendons and veins is not shown
- Faces are stylised constructions per style; likenesses of specific people are not supported
- An arm reaching toward the camera is drawn in parallel projection, so the hand does not grow and the arm reads as a short mass
- Keep whole-body tilt at 60 or less (beyond that the figure leaves the frame)
- A full-length crop of a seated figure is placed by standing height, so the figure comes out small (raise `height` directly to compensate)
- Clothing is made of shells around the body and cone skirts, so complex tailoring and large folds are not shown
- Hair is made of masses and strand ribbons, so curly and braided hair are approximations
- All short male haircuts (crop) share one hairline curve; receding hairlines and beards go no further than stubble (beard)
- Avoid combining an open coat with arms crossing the body, such as folded arms: the pattern of the inner garment is drawn over the arms
- In a two-shot, a hanging hand in front of the other person's pelvis reads as unintended contact
    + Watch for the `tangent check` warning in the render output
    + Fix it by placing that hand on the other person's waist or upper arm with `touch`, or by widening the gap between the figures
- Two-shot contact covers placing one hand on a set spot of the other body (shoulder, upper arm, waist, hand)
    + Poses where two people's arms wrap round each other, such as a hug, need hand positions given as coordinates and are unstable
    + Long hanging hair is drawn flat, so its depth is approximated at back height
- Lying poses are not supported because placement on the canvas assumes an upright figure
- Poses resting the chin on a hand or cupping a cheek are unstable because the hand-target IK picks a solution that sends the elbow up (use folded arms or arms on a table instead)
- Weather goes as far as layers of falling particles; splashing raindrops, the depth of fallen snow and trees bending in the wind are not shown
- Wet-ground reflections are exact for objects standing upright on the ground and approximate for tilted objects or objects off the ground
- Umbrellas and parasols are canopies assembled in the picture plane, so they flatten when the shaft tilts strongly toward the viewer
- Perspective supports one-, two- and three-point views (`Perspective` yaw and pitch)
- Distant pedestrians are simple silhouettes; draw near figures with `Character`
- Cars are bodies joined from flat pieces, so curved reflections and small parts (wipers, aerials) are left out
- Modern objects are assembled from plates, so small parts such as cables, ports and logos must be added by hand
- For requests at a limit, offer what is possible instead (another crop, a simpler pose, a stylised style)
