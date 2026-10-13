# Painting process

A document mapping a human artist's process onto code work. It defines the output and the judgment criteria of each stage.

## Contents

- Stage 1 Plan
- Stage 2 Design
- Stage 3 Form
- Stage 4 Color
- Stage 5 Shading
- Stage 6 Lines
- Stage 7 Finishing
- Stage 8 Review
- Tips for revision loops

## Stage 1 Plan

- The output is a 3-line brief
    + Who is drawn (age range, impression, hair, clothing)
    + What mood (time of day, emotion, temperature feel)
    + What style (anime, illust, painterly)
- Decide items the user left open yourself, to fit the mood
- Translate the impression into face parameters
    + Cool and sharp impression : `jaw_sharpness` 0.85 or more, `eye_tilt` 0.016, `smile` 0.1-0.3
    + Soft and gentle impression : `jaw_sharpness` 0.3-0.5, `eye_tilt` 0.004, `smile` 0.6 or more
    + Mature impression : `eye_height` 0.080-0.090, `eyelid_open` 0.88, `chin_length` 1.05
    + Younger-looking impression : `eye_height` 0.10 or more, `iris_scale` 1.1, `chin_length` 0.95
- Firm up the impression once more with eye and brow presets
    + Cool and sharp impression : `eye_shape` `upturned`, `brow_shape` `straight`
    + Soft and gentle impression : `eye_shape` `droopy`, `brow_shape` `arched`
    + Plain, understated impression : `eye_shape` `monolid`, `nose_shape` `dot`
- Decide the view in the planning stage too
    + Front : a picture where the face and expression are the subject
    + Three-quarter (`head_turn` 1.5-2.5) : a picture where the face's volume and jawline are the subject
    + Profile (`side_*`) : a picture where motion and silhouette are the subject, like walking or sitting
    + Back view (`back_*`) : a scene looking at a landscape, a scene looking back over the shoulder
- Decide the number of characters in the planning stage too
    + 1 person : `figure`
    + 2 people in a relationship (couple, friends) : set the relationship with `duo` `pose` (side by side, holding hands, arm in arm, arm around shoulders, face to face)
    + Unrelated people around : `extras`

## Stage 2 Design

- The output is a palette and composition note
- Decide the palette's 13 colors at once
    + 1 main color (hair or outfit), 1 supporting color (background), 1 accent color (iris or prop)
    + Place the accent color in the smallest area of the picture with the highest saturation
- Composition is decided by `placement` and 3 pose keys
    + For the full body rig, first pick where to crop with `shot` : whole body `full`, figure and outfit `thigh`, standard close-up `knee`, conversation and expression `waist`
    + With `shot`, put the character to one side with `x` to leave room for the background (window, bed, vanishing point)
    + For tension or dynamism, `finish.tilt` 3-8 degrees
    + `head_height` 0.38-0.45 : bust standard
    + `eye_center` x 0.45-0.55 : more room on the side the head turns toward is stable
    + Design the flow of the gaze with the combination of `head_turn`, `head_tilt`, `gaze`
- Use only 1 light, top left (135 degrees) by default

## Stage 3 Form

- Areas the rig handles : face contour, eyes, nose, mouth, hair, neck, shoulders, outfit
- Verify form with panel 1 of the `--stages` output
    + Check the 6 proportion guide lines (crown, brows, eyes, nose, mouth, chin)
    + Check that the silhouette alone reads as a person
- In a free scene, write from large masses to small ones
    + Create layers in order of far view, middle view, near view
    + Start each element as a spline of 4-8 control points

## Stage 4 Color

- One base color per part; panel 2 of the process sheet is this stage
- First check that the base colors alone hold together as a harmony
    + Awkward base colors are not saved by shading and finishing
- Add a partial reddish tint to the skin for life
    + At the cheeks, around the eyes, the nose tip and under the lips (handled by the rig, strength via `airbrush`)

## Stage 5 Shading

- There are 4 kinds of shading, all derived from one light vector
    + (Form shadow) faces of a mass turned away from the light
    + (Cast shadow) shadows the fringe throws on the forehead, the chin on the neck, side hair on the shoulders
    + (Contact shadow) deep dark where things meet, like under the chin and the hair behind the neck
    + (Rim light) a bright band on the edge toward the light
- The difference between styles comes from how hard the shadow edges are
    + anime : `shadow_softness` 0.02, edges knife sharp
    + illust : 0.16, edges blur softly
    + painterly : 0.30, spread wide, with brush strokes carrying the texture
- Move the shadow color's hue along with its value
    + Skin shadows move toward red, shadows on white clothes toward blue-violet

## Stage 6 Lines

- Lines are generated automatically from the edges of filled areas
    + The line color is a darker, deeper version of the adjacent area's color (colored lines)
    + Line width is thin on the light side and thick on the shadow side (`line_variation`)
- Draw inner lines only as tapered strokes with thinning ends
    + Lines of even width look like technical drawings
- The painterly style shows form through the edges of color areas (`line_width` 0)

## Stage 7 Finishing

- A default chain per style is applied automatically
    + anime : diffusion glow, bloom, color grading, grain
    + illust : glow, bloom, color grading, vignette, grain
    + painterly : brush stroke reconstruction, color grading, canvas texture
- Adjust the strength of each item with the `finish` key
    + Taking `shadow_tint` and `highlight_tint` from the background's dark and light colors places character and background under one light
- `ambient` lays the background color over the lower part of the character to settle the character into the scene

## Stage 8 Review

- Open the final PNG to check it, then zoom in on the face to check again
- Check from large to small
    + Silhouette and composition
    + Color harmony and shading direction
    + Face (eyes, jawline, mouth)
    + Hair edges and gaps
    + Edge defects
- When you find a defect, go back to the stage that caused it and fix it there
    + Do not cover form problems with finishing

## Tips for revision loops

- Change only 1-3 keys per revision
    + Changing many keys at once hides which one had the effect
- Move values by 10-20% within the allowed range
- For a quick check, shrink `canvas` to [800, 1000] and render (about 3 seconds)
- To change only the hair shape, change `hair_seed`
- A defect not solved after 3 revisions is likely a limit of the rig, so tell the user and offer alternatives
