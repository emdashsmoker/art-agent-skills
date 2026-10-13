# Anime Style

A style that composites cel-painted figures over painted backgrounds and finishes with compositing effects. Examples are `examples/anime_sky_pilot.py` (figure and sky), `anime_night_desk.py` (objects and interior), `anime_city_window.py` (adult figure study), `anime_figure_base.py` (female full-body base), `anime_figure_base_male.py` (male full-body base), `anime_morning_light.py` (frontal half-figure study male scene), `anime_turnaround.py` (male and female turnaround and pose sheet), `anime_outfit_sheet.py` (outfit sheet), `anime_cafe_talk.py` (two people seated face to face in a cafe), `anime_doomer_bus_stop.py` (a man at a bus stop on a snowy night), `anime_doomer_courtyard.py` (establishing shot of an estate courtyard without people), `anime_face_templates.py` (face template sheet), `anime_hair_templates.py` (hair template sheet), `anime_hair_colors.py` (hair color sheet), `anime_long_hair_platform.py` (long straight hair on a platform at dusk), `anime_long_hair_window.py` (backlit back view at a window) and `anime_long_hair_walk.py` (two-shot on a park path).

## Visual Traits

- Surfaces split into two steps, base and shadow color, with crisp borders
- Outlines use a darkened surface color and vary in weight
- The eyes are the most detailed part of the frame, with a vertical gradient and highlights in the iris
- Backgrounds are softer than the figures
- Bloom and atmosphere go over the whole frame at the end

## Workflow

1. Paint sky, clouds and distance on the background canvas
    + The sky is a `Linear` gradient, dark on top and lighter toward the horizon
    + Clouds come from `motifs.cumulus`
2. Draw figures separately on a transparent `Canvas(..., background=None)`
3. Set the pose with `figure.Figure` and fit the face frame to the rig's head
    + Pose values and how to make clothes are in `references/figure.md`
    + The face uses the skull radius as unit 1 and starts from the proportion table in `references/craft.md`
4. Stack parts from back to front: back hair, neck and torso, face, eyes and brows, bangs
5. Call `anime.cel(canvas, outline, base, shade, amount, line)` for each part
    + Round parts (arms, ribbons, collars) are fine with an automatic shadow of amount 0.3-0.4
    + Parts with several overlapping outlines, such as arms, are merged with `figure.shape_of` and painted, with only the outer outline drawn through `edge_light`
    + Face and hair turn off automatic shadows and take designed shadow shapes through `clip`
6. Add three kinds of designed shadows
    + Shadow of the bangs on the forehead: the bangs tip line moved down a little
    + Shadow of the jaw on the neck: a shape that covers the top of the neck
    + Shadow of collars and ornaments on clothing: that part shifted away from the light
7. Add strand lines and a banded highlight to the hair
    + Strand lines are `stroke(..., taper=(0.2, 1, 0.2), clip=hair)`
    + The highlight is a zigzag band that follows the round surface of the head. Build it with `g.polygon`, then apply clip
8. Composite with `anime.rim_light(character, light)` and then `background.paste(character)`
9. Apply compositing effects with `anime.finish(background)` and add light from the source side with `post.light_gradient` if needed

## Objects and Interiors

- Objects are 3D solids from `solids` and `props`, and `s3.draw(..., line=ink_color)` paints them and draws their outlines in one go
    + Face shading follows the light direction, so the two-step cel shading falls into place automatically
- Night scenes split the light into two sources
    + Warm light (lamp) goes into the light direction of face shading, cold light (screen, window) into soft ellipses with SCREEN blending
    + The bloom of `anime.finish` makes screens and bulbs glow
- Detailed methods are in the modern objects section of `references/subjects.md`

## Hair

- Draw the bangs as one closed spline
    + The top is a smooth arc running a little outside the skull
    + The bottom is a sawtooth of alternating tips (sharp) and notches (sharp), with one midpoint between each tip and notch so the strands curve
    + Put every tip and notch index in corners
- Draw long hair blowing in the wind strand by strand with `g.ribbon(center line, width list)`
    + Wide roots that overlap make the strands flow as one mass and split only at the tips
    + Draw lower strands first so upper strands cover them
    + Vary strand length, width and tip direction
- Paint the torso part of the back hair in the shade color so it recedes behind the face

## Eyes

The example's `draw_eye` is the reference implementation. It stacks the layers below in a Frame with the eye center as origin and the eye half-width as 1.

1. White: a closed curve with sharp inner and outer corners. Intersected with the face shape
2. Upper shade on the white: a pale blue-gray ellipse over the top third
3. Iris: a tall ellipse with a `Linear` that is dark on top and light below
4. Upper iris shade, pupil and lower reflected light
5. Two highlights: a large one up on the light side and a small one down on the opposite side
    + Both eyes place them in the same screen direction (correct the sign with `eye.flip`)
6. Upper lashes: a closed shape thicker toward the outer corner. The darkest color
7. Lower line and double-eyelid crease: thin tapered lines

## Color

- Skin shadows are redder and darker than the skin color
- Hair uses three colors: base, shade, highlight
- Shadows on white clothing are in the sky-blue range
- Outline colors differ per part: red-brown for skin, a dark base for hair, blue-gray for clothing

## Compositing Arguments

| Argument | Default | Adjustment |
|---|---|---|
| `diffusion` | 0.16 | Higher is dreamier, lower is crisper |
| `bloom` | 0.25 | Lower it if white clouds and skin blow out |
| `shadows`, `highlights` | navy, cream | Match the time of day. Sunset uses purple and orange |
| `aberration` | 0.6 | 0 means no chromatic aberration |
| `grain` | 0.018 | Reduces the artificial look of smooth surfaces |

## Common Defects

| Symptom | Remedy |
|---|---|
| Blowing hair looks like webbing or tentacles | Split it into one ribbon per strand and widen the roots so they overlap |
| The face blows out to white | Lower the value of the skin base and lower bloom |
| Clouds lose their volume | Darken the shade color of the cloud palette and lower diffusion |
| Eyes look small or close-set | Adjust unit and x of the eye Frame. The example uses center x ±0.47 and half-width 0.27 |
| Thin lines look flat | Raise the width of `anime.cel` and render the final at scale 1.25 or above |
