# Painting Principles

Judgment criteria that apply to every style. Read them when setting composition, values and color during the brief, and when hunting defects during review.

## Composition

- One focal point
    + The place with the strongest value contrast, the crispest contour and the highest saturation reads as the focal point
    + Gather all three at the focal point and hold them back elsewhere
- Place the focal point near a rule-of-thirds intersection and away from the exact center
    + On a 1600x900 frame the intersections are at x 533 or 1067 and y 300 or 600
- 3-5 large masses
    + Give them different sizes so large, medium and small are distinct
- Overlap masses to create depth order
    + Shapes placed side by side without overlap read as flat
- Place at least one line that leads the eye to the focal point
    + Branches, roads, horizons, hair flow, light rays and so on
- Elements that touch the frame edge are either clearly cropped or clearly kept away from it

## Values

- Decide the layout of three value groups (light, middle, dark) before picking colors
    + Give the three groups different areas so one group leads the frame
- Keep values close within one group
    + If a light color inside the shadow gets brighter than a dark color on the lit side, the volume collapses
- Fix one light source and match every shadow and highlight to its direction
- If the subject reads when the render is shrunk, the value structure holds

## Color

- Limit the palette to 5-7 colors and give each a role
    + The dominant color is the hue family that covers most of the frame
    + The supporting color is a hue next to the dominant one
    + The accent is the complement of the dominant color, used in small amounts at the focal point only
- Shadow colors shift the hue of the base as well as its value
    + Under warm light shadows move toward cool, under cool light toward warm
    + `color.shade` performs the cool shift automatically
- Distant things move toward the sky color, with lower contrast and softer contours (aerial perspective)
- Wide areas of saturated colors touching each other tire the eye
    + Keep high saturation to small areas and build wide areas at medium saturation or below
- Pure black and pure white are reserved for the darkest darks and highlight dots

## Form

- Work from large forms to small ones
    + Details laid on large forms with wrong proportions all have to be redrawn
- Design so the subject is recognizable from the silhouette alone
    + Characteristic parts such as arms, tails and branches stick out of the body mass and show in the contour
- Mix straight lines and curves, large and small intervals
    + Repeats of the same size at the same interval look mechanical
    + Jitter the size, spacing and tilt of repeated elements a little with random values
- Give natural contours irregularity with `roughen`, `blob` and `ridge`
- Round solids get their shadows from `form_shadow`. Angular solids and designed shadows are drawn as shapes and limited with `clip`
- Objects on the ground get a dark, narrow contact shadow where they touch, with a wide, pale cast shadow over it
    + Without the contact shadow the object floats above the ground

## Anime Face Proportions

Unit coordinates of a frontal face verified by rendering `examples/anime_sky_pilot.py`. The skull radius is 1 and the origin is the skull center. Body proportions and poses use the rig in `references/figure.md`.

| Part | Coordinates |
|---|---|
| Crown | (0, -1.0) |
| Temples | (±0.98, 0.2) |
| Jawline | (±0.88, 0.64), (±0.6, 1.04), (±0.28, 1.3) |
| Chin tip | (0, 1.4) |
| Eye center | (±0.47, 0.36), eye half-width 0.27 |
| Brows | y -0.02 to -0.12 |
| Nose | (0.03, 0.74) to (0, 0.9) |
| Mouth | y 1.02 to 1.1, half-width 0.2 |
| Outer hair line | 0.1-0.2 outside the skull |

- Eye half-width and jaw length set the age range
    + Eye half-width 0.27 and chin tip 1.4 read as a young adult. Larger eyes and a shorter jaw look younger

## Anime Mature Adult Face

Values verified in `examples/anime_city_window.py`. Pictures that need adult markers, such as nude figures, use this table.

| Part | Coordinates and treatment |
|---|---|
| Jawline | (±0.86, 0.6), (±0.6, 1.0), (±0.26, 1.34) |
| Chin tip | (0, 1.45) |
| Eyes | center (±0.45, 0.4), half-width 0.24. An almond shape 0.4 times as tall as it is wide |
| Lids | Half-lowered eyes with the upper lid covering the top of the iris. Outer lashes sweep out like a wing |
| Brows | A thin arc that tapers quickly at the end. y -0.02 to -0.12 |
| Nose | Bridge line on the shaded side from (0.1, 0.42) to (0.06, 0.86) and a shadow under the nose tip |
| Mouth | Upper lip line, colored lower lip, a small light on the lower lip, shadow under the lip |
| Cheeks | A shadow band from below the cheekbone to the jaw on the shaded side |
| Head size | Head height 2.3 times the skull radius, slightly larger than the rig's head |

- Tilting the head while keeping the torso upright adds movement even to a frontal composition
- Draw hair in the order back hair, face, bangs so the face sits between the layers of hair
- Stack eyes in the order white, iris gradient, upper shade, pupil, reflected light, highlights, lashes

## Anime Adult Male Face

Values verified in `examples/anime_figure_base_male.py`. The skull radius is 1 and the origin is the skull center.

| Part | Coordinates and treatment |
|---|---|
| Jawline | Jaw corner breaking at (±0.92, 0.68), (±0.66, 1.1), (±0.3, 1.4) |
| Chin tip | A flat chin tip breaking at (±0.13, 1.47) with shade below |
| Eyes | center (±0.44, 0.38), half-width 0.235. A narrow shape one third as tall as it is wide, no wing at the outer corner |
| Brows | Thick shapes close to the eyes. (0.1, -0.02) to (0.88, -0.06), about 0.08 thick |
| Nose | Bridge line from (0.12, 0.34) to (0.08, 0.9), a shadow under the nose tip, philtrum line |
| Mouth | Thin upper lip line at y 1.12-1.14, half-width 0.22. A short shade under the lower lip |
| Cheeks | A shade band from below the cheekbone to the jaw on the side away from the light, weak shade on the lit side |
| Ears | (±0.98, 0.42), radius 0.15×0.27. Visible from the front because the hair is short |
| Neck | Two sternocleidomastoid lines and the Adam's apple |

- For faces at an angle, pass the coordinates of the tables above unchanged to `head3d.Head3D.face()`
    + The coordinates attach to the face surface and distort with the angle, and hidden parts are filtered with `face.facing`. Usage is in the head and hair by angle section of `references/figure.md`

## Review Checklist

Check from top to bottom while looking at the whole image and a close-up of the focal area.

| Area | What to check |
|---|---|
| Composition | Does the focal point read as one place? Does the subject show when shrunk? |
| Proportion | Are part sizes and positions natural? Are places that need symmetry aligned? |
| Joins | Are there no gaps between parts or holes showing the background? Do things that should touch actually touch? |
| Values | Does the light direction agree on every part? Is the focal contrast the strongest? |
| Color | Has no color from outside the palette crept in? Is the accent kept off areas outside the focal point? |
| Edges | Do shapes avoid awkward cuts at the frame edge? |
| Material | Did the focal forms survive the style pass? Are the light areas free of blowouts? |
| Mechanical traces | Are there no same shapes repeating at the same interval? Are perfect circles and straight lines absent from natural forms? |

## Common Defects and Remedies

| Symptom | Cause | Remedy |
|---|---|---|
| A shape sits somewhere unexpected | Coordinates guessed without looking | Read coordinates on the grid of `guide_image` and fix them |
| A curve bulges or twists between control points | Uneven control point spacing | Add intermediate control points or list the break points in corners |
| Background shows between parts | Neighboring parts only touch | Push the back part well under the front part so they overlap |
| Shadows are a muddy gray | Black mixed into the base | Use `color.shade` or a hue-shifted shadow color |
| The frame looks hazy and light areas blow out | Too much bloom | Lower bloom and diffusion and lower the value of the base colors |
| Repeated elements look stamped | Constant size and spacing | Jitter size, position, tilt and opacity with random values |
| An object floats above the ground | No contact shadow | Add a dark, narrow shadow with MULTIPLY where it touches |
| Small details vanish after the pass | Details smaller than the brush or bleed | Enlarge the details, raise scale or reduce the pass arguments |
| Thin lines look broken | Line width under 1px for the scale | Raise the line width or the final scale |
