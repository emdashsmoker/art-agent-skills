# Methods by Subject

Read this document when painting landscapes, cities, still lifes and modern objects. Figures are in `references/figure.md`.

## Landscape

Examples are `examples/oil_summer_fields.py`, `examples/oil_harbor_sunset.py`, `examples/illustration_moonlit_camp.py` and `examples/oil_doomer_pylons.py` (a line of pylons).

- Use three depth cues together
    + Aerial perspective: mix in more sky color and lower contrast with distance. `color.mix(color, sky_light, 0.3 * distance)`
    + Size change: field bands, trees, ripples and grass get smaller and denser with distance
    + Overlap: a large tree or hill at the front edge hides part of the landscape behind
- Split the frame into four layers (sky, distance, middle ground, foreground) and paint back to front
- Keep the horizon away from the center, near the upper or lower third
- Bend a leading road or river into an S that links the foreground to the focal point in the distance
    + Its width must shrink fast with distance to read as a plane lying down

| Subject | Tool |
|---|---|
| Cumulus | `motifs.cumulus(canvas, center_x, base_y, width, height, light, palette, puffs)` |
| Mountain ridge | Close the result of `motifs.ridge(x_start, x_end, base_y, peak_height, roughness)` with two points below |
| Tree foliage | `motifs.canopy(canvas, cx, cy, width, height, light, palette, puffs, puff_size)` |
| Grass | `motifs.grass(canvas, x_range, y_range, count, palette, blade)` |
| Glitter on water, flowers, fallen leaves | Scatter small ellipses or `g.blob` at random. Larger up close |

- Draw the trunk first with `g.ribbon` and put `canopy` on top
    + Narrow, tall trees need larger puffs such as `puff_size=(0.32, 0.5)` to fill gaps
    + A MULTIPLY shadow on the grass under the tree stands it on the ground
- In oil style, set the brush direction per layer with `canvas.direct`
    + Sky a gentle diagonal, fields and water horizontal, trunks and grass vertical, foliage `around=center`

## City

Examples are `examples/watercolor_old_town.py`, `examples/anime_doomer_courtyard.py` (two-point estate), `examples/watercolor_doomer_block.py` (three-point view from below) and `examples/illustration_doomer_rooftop.py` (estate seen from above).

- Scenes that recede in depth read as space only when parallel lines converge at a vanishing point
- `Perspective` projects scene coordinates (meters) onto the screen

```python
from codepaint import Perspective
VIEW = Perspective(vanish=(690, 640), eye_height=1.6, focal=880)
wall = VIEW.side_wall(x=-3.6, z_near=5.0, z_far=10.5, y_bottom=0.0, y_top=12.5)   # side face of a building left of the street
windows = VIEW.side_wall_grid(-3.6, 5.0, 10.5, 3.4, 12.0, columns=2, rows=3, margin=0.27)
road = VIEW.ground(-3.6, 4.2, 1.2, 90)
foot = VIEW.project(1.3, 0.0, 14.0)                                              # a point on the street
```

| Argument | Meaning |
|---|---|
| `vanish` | Screen coordinates of the vanishing point. The horizon passes at this height |
| `eye_height` | Eye level. 1.6 is the eye line of a standing person, higher values look down |
| `focal` | Screen length of a scene length of 1 at depth 1. Higher values give a telephoto look |

- Scene coordinates: x left-right, y height, z depth
    + Define one building as (wall x, near z, far z, height) and vary height and color per building
    + The nearest building starts at z 5 or more. Closer, windows and doors stretch badly
    + Attach a camera-facing front wall to the nearest building with `front_wall` to fill the edge of the frame
- Draw far buildings first so near ones cover them
- One row along the street is lit and the other in shade, and the shadow the shaded row casts across the street goes on in one glaze
- People, streetlights and cars take their foot position from `VIEW.project(x, 0, z)` and their size from `VIEW.scale_at(z)`
    + Passersby are `figure.Figure(g.Frame(VIEW.project(x, 0.93, z), 0.225 * VIEW.scale_at(z)), ...)`
- For pen and wash, draw outlines with `cv.stroke(path, ink_color, width=1.5, closed=True, jitter=0.5)` after the painting is done
- A tower or tall building at the end of the street makes the vanishing point the focal point
- Blocks standing at an angle, estates seen from above and blocks seen from below are boxes from `solids` projected with one camera
    + Windows and balconies attach to faces with `camera.region(face, u0, v0, u1, v1)`. On side faces v runs top to bottom
    + Tilting the camera up gives three-point perspective with verticals converging upward
    + An estate seen from above needs blocks within the view width on every depth row, or the bottom of the frame goes empty

## Still Life

The example is `examples/watercolor_still_life.py`.

- Group 3 or 5 objects and vary their sizes as large, medium and small
- Overlap objects partly to create depth order, and use objects of different heights to form a triangular composition
- Place the table line near the lower third of the frame and let it break behind the objects
- Order for round objects: base color, `form_shadow(soft=0.3-0.4)` shade, `form_light` highlight, reflected light from the ground color
    + Reflected light puts the color of a neighboring object or the table at low opacity low on the shaded side
- In watercolor style, highlights stay as unpainted paper
    + `shape_to_paint = body - cv.shape(highlight_path, soft=4)`
- Shadows come in two layers
    + A dark, narrow contact shadow where the object touches
    + A wide, pale shadow stretching long away from the light
- Thin, curved parts such as handles, spouts and knobs are `g.ribbon(center line, width list)`
- Repeated round units such as grapes or petals are drawn from the back, with size and position jittered at random
- A pale background in the objects' complementary range makes the objects stand out

## Modern Objects

Examples are `examples/anime_night_desk.py` (desk scene), `examples/watercolor_gadget_studies.py` (device studies), `examples/watercolor_doomer_kitchen.py` (cassette radio and glass holder) and `examples/anime_doomer_courtyard.py` (a car extruded from its profile).

- Computers, phones, cups, books and speakers are combinations of boxes and prisms
- Build 3D solids with `solids` and project them with one camera
    + Every object's perspective and face shading follow the same viewpoint and light
    + Each object can be turned freely with yaw and pitch

```python
from codepaint import props
from codepaint import solids as s3

CAMERA = s3.Camera(eye=(0, 50, -70), target=(0, 12, 35), focal=1150, center=(800, 470))
LIGHT = (-0.7, 0.6, -0.2)                       # where the light comes from (3D)
desk = s3.box((0, -2.5, 25), (150, 5, 66))       # center, (width, height, depth) cm
s3.draw(cv, CAMERA, desk, {"top": "#6a4c44", "*": "#4a3236"}, LIGHT)

monitor = props.monitor((8, 0, 40), yaw=-4)
monitor.draw(cv, CAMERA, {"foot": "#3a3f62", "neck": "#2f3456", "panel": {"front": "#0a0c16", "*": "#3a3f62"}},
             LIGHT, line="#0b0d1c", width=1.4)
screen = monitor.faces["screen"]
cv.fill(cv.shape(CAMERA.region(screen, 0.02, 0.04, 0.98, 0.96)), "#151a2c")   # screen content uses 0-1 coordinates on the face
```

| Tool | Use |
|---|---|
| `s3.box(center, size)` | Box. Desks, books, speakers, cartons |
| `s3.slab(center, size, radius)` | Slab with rounded corners. Phones, laptops, monitors, tablets |
| `s3.cylinder(base, radius, height, top_radius)` | Cylinder and frustum. Cups, lenses, lampshades, flowerpots |
| `solid.rotated(yaw, pitch, about)`, `solid.moved(offset)` | Rotate and move |
| `s3.draw(canvas, camera, solid, paint, light, line)` | Paints only visible faces far to near and draws outlines |
| `camera.region(face, u0, v0, u1, v1)` | Rectangle on a face. Screens, keys, labels |
| `camera.face_ellipse(face, u, v, ru, rv)` | Ellipse on a face. Speakers, lens glass, buttons |
| `props.laptop`, `monitor`, `keyboard`, `phone`, `mug`, `book`, `desk_lamp` | Ready-made object parts. Paint them with `Prop.draw` |
| `props.keycaps(canvas, camera, face, color, area=...)` | Key grid on a face |

- Scene coordinates: x right, y up, z depth. cm is convenient for objects
- Paint order
    + `s3.draw` sets the face order within one object
    + Between objects, call them far first or sort them with `camera.order(solids)`
    + Large faces that support other objects, such as desks, floors and walls, are drawn first even when their center is near. `order` sorts by center depth only, so including large faces gives a wrong order
    + If one overlapping object passes through another, order cannot fix it, so move them apart
- Rotation directions
    + Positive yaw is clockwise seen from above and turns the front toward screen left
    + Positive pitch tips the top away from the camera. A slab laid flat is `rotated(pitch=90, about=center)`
    + Laying a cylinder axis forward is `rotated(pitch=-90)`, and the top face then looks at the camera (lens)
- Face names
    + box: front, back, left, right, top, bottom. On top, v runs back to front
    + slab and prism: front, back, side. The top of a slab laid flat is front
    + cylinder: top, bottom, side
- Details such as screens and keys go on after the solid is painted, using face coordinates
    + A glowing screen gets that area painted once more with SCREEN blending at the end, with a soft glow of the same color around it
- When each object reads best from a different angle, give each cell its own camera (study sheets)
- Objects defined by their profile, such as cars, extrude the profile outline by their width with `s3.prism` and stand it up
    + The up component of the face normal picks top faces (roof, hood) and slanted faces (windshield) to paint separately
- Vessels open at the top (glass holders, pot rims) get only their visible side faces painted directly. `s3.draw` fills the top area into the silhouette
- Curved rods such as handles, cables and headphone bands project a 3D point list with `camera.path` and are drawn as thick lines
    + Multiply the width by `camera.scale_at(point)` to match the depth
