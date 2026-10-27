# paintkit API

Use it as `from paintkit import ...` after `sys.path.insert(0, '<skill>/scripts')`.
Colors are `'#rrggbb'` or `'#rgb'` strings or three floats in 0-1. Coordinates are pixels with the origin at the top left, y positive downward.

## Contents

1. Canvas
2. Mask operations
3. Shading (shading)
4. Color (color)
5. Scenery (scenery)
6. City (city)
7. Modern objects (solids)
8. Finish (finish)
9. Doomer mood (doomer)
10. Width profiles
11. Settings

## 1. Canvas

`Canvas(width=1024, height=1280, background='#ffffff')`

### Making shapes (return a mask)

| Method | Description |
|---|---|
| `blob(points, smooth=True)` | Closed area through control points. `smooth=False` gives a straight-edged polygon |
| `polygon(*polygons)` | Union of several polygons |
| `ellipse(cx, cy, rx, ry=None, rotation_deg=0)` | Ellipse |
| `rect(x0, y0, x1, y1, radius=0)` | Axis-aligned rectangle. `radius` rounds the corners (screens, keys, buttons) |
| `ribbon(points, width, profile='taper', smooth=True)` | Variable-width band along a centerline |
| `ribbons([(points, width, profile), ...])` | Many bands at once (fast) |
| `contour(points, left, right, bend=0)` | Band with separate widths on each side of the centerline. `left`, `right` are `[(t, px), ...]` (t is the 0-1 position, left is the left-hand side walking from the first point to the last). `bend` is the radius in px that rounds a bent joint. Asymmetric limbs, slanted bottles |
| `empty()`, `full()` | All 0, all 1 |

### Scalar fields (return 0-1 arrays)

| Method | Description |
|---|---|
| `linear(p0, p1)` | 0 at p0, 1 at p1 |
| `radial(center, rx, ry=None, rotation_deg=0)` | 1 at the center, 0 at the edge |
| `noise(scale=64, octaves=4, seed=None, stretch=(1,1))` | Smooth noise. `stretch=(6,1)` gives horizontal streaks |
| `ramp(field, *stops)` | Turns a field into a color gradient image. Stops are a list of colors or of `(position, color)` |

Multiply a field with a mask, or build a color image with `ramp` and pass it as the color of `fill`.

### Painting

| Method | Description |
|---|---|
| `fill(mask, color, opacity=1)` | Paints a new surface. Erases the lines under it |
| `tint(mask, color, mode='multiply', opacity=1)` | Changes existing color. mode: `normal`, `multiply`, `screen`, `overlay`, `soft_light`, `add` |
| `paint_form(mask, color, light, shadow=0.12, soft=1.2, line_width=2.5, shadow_color=None, line_color=None, rim=0)` | Fill + form shadow + outline in one call. The quickest way to add a prop |
| `paint_volume(mask, color, light, bulge=None, depth=1, gloss=0, shadow_color=None, light_color=None, line_width=0)` | Round shading that runs continuously from shadow through base to light. For subjects where volume matters, such as fruit, bottles, cloth and skin. `bulge` is the rounding radius in px, `gloss` a glossy spot |
| `paste(source, quad, opacity=1)` | Attaches a flat picture (Canvas or image) to a four-point quad in perspective. Counts as a new surface and erases the lines under it. Returns the mask of the pasted area |
| `ink(points, width, color, profile='taper', opacity=1, clip=None)` | One pen stroke |
| `ink_mask(mask, color, opacity=1, clip=None)` | Puts any mask on the line layer |
| `outline(mask, width, color, weight_dir=(0.4,1), weight_gain=0.45, wobble=0.12, clip=None)` | Traces the edge of a mask with a line of varying weight. Heavier on the `weight_dir` side |

- The `color` argument is a flat color or an (H, W, 3) image (gradient)
- `clip` keeps lines inside a given mask

### Tracking and output

| Method | Description |
|---|---|
| `track(name)` | Starts recording the union of every following `fill` |
| `tracked(name, stop=True)` | Returns the recorded mask |
| `flatten(line_opacity=1)` | Color + lines composited into one image |
| `save(path)` | Saves without a finish |

Attributes: `cv.color` (H,W,3), `cv.line_alpha` (H,W), `cv.size`, `cv.width`, `cv.height`.
Blur the background with `cv.color = blur(cv.color, 2.0)`.

## 2. Mask operations

`from paintkit import blur, shift, grow, smoothstep`

| Function | Description |
|---|---|
| `blur(mask, radius)` | Gaussian blur. Works on images too |
| `shift(mask, dx, dy)` | Translation |
| `grow(mask, px)` | Dilates when positive, erodes when negative |
| `smoothstep(field, low, high)` | Turns a field into a mask with a soft edge |
| `raster.fill_holes(mask, threshold=0.5)` | Fills only fully enclosed gaps. Gaps open to the outside stay |

## 3. Shading (shading)

`from paintkit import shading`. The light direction is a 2D vector from the surface toward the light. A light at the top left is `(-1, -1)`.

| Function | Description |
|---|---|
| `crescent(mask, toward_light, distance, soft=0)` | Crescent shadow along the edge away from the light. The basis of cel shading |
| `rim(mask, toward_light, width, soft=0)` | Thin band along the edge facing the light. Backlight, rim light |
| `cast(caster, receiver, offset, soft=0)` | Shadow the caster drops on the receiver. offset in px, away from the light |
| `form_shadow(mask, toward_light, threshold=0.55, soft=0.02)` | Terminator computed by inflating the form. Suits round masses |
| `form_light(mask, toward_light)` | The raw field behind it (-1..1). For cutting it yourself with `band(field, t, soft)` |
| `volume(mask, toward_light, bulge, height=0.9)` | Continuous field from 0 (deep shadow) to 1 (light). For coloring it yourself through `cv.ramp`. A lower `height` makes the light graze from the side |
| `occlusion(neighbor, receiver, radius)` | Soft contact shadow near a neighboring object |
| `inner_glow(mask, radius)` | Soft band just inside the edge |

The results are masks, applied as in `cv.tint(mask, shadow_of(color), 'normal', 0.9)`.

## 4. Color (color)

`from paintkit import rgb, adjust, shadow_of, light_of, mix`

| Function | Description |
|---|---|
| `shadow_of(color, depth=1)` | Shadow color: darker, a little more saturated, hue shifted cooler |
| `light_of(color, amount=1)` | Light color: lighter, a little less saturated, hue shifted warmer |
| `adjust(color, lightness=0, chroma=1, hue=0, toward_hue=None, toward=0)` | Lightness offset, chroma scale and hue rotation in OKLCH space |
| `mix(a, b, t)` | Linear mix of two colors |

For skin shadows use `paintkit.figure.look.skin_shadow(color)` (shifts toward red).

## 5. Scenery (scenery)

`from paintkit import scenery`. Painted before the subject.

| Function | Description |
|---|---|
| `sky(cv, top, bottom, horizon_y=None)` | Sky as a vertical gradient |
| `cumulus(cv, center, width, height, color, shade, light, puffs=22, edge=1)` | One cumulus cloud (two tones) |
| `cloud_bank(cv, y_range, count, size, color, shade, light, seed)` | Several cumulus clouds |
| `clouds(cv, y_range, color, coverage, scale, edge, opacity)` | Hazy noise-based cloud layer (cirrus, mist) |
| `sun_glow(cv, center, radius, color, opacity)` | Light bleeding around a light source |
| `light_rays(cv, origin, angle_deg, spread_deg, count)` | Rays of light |
| `bokeh(cv, count, colors, radius, region, opacity)` | Out-of-focus light discs |
| `mountains(cv, base_y, height, color, jagged, scale, snow, light)` | Mountain ridge. Layer them lighter and bluer toward the back |
| `hills(cv, base_y, amplitude, color, scale)` | Gentle hills |
| `horizon_sea(cv, horizon_y, far, near, sparkle)` | Sea below the horizon with glints |
| `water_reflection(cv, water_y, darken, ripple, tint)` | Mirrors the picture above the water line. Call after everything to be reflected is painted |
| `tree(cv, base, height, kind='round'\|'pine', leaf, trunk, light, line_width=0)` | Tree. `round` has a three-tone mass of leaves |
| `grass(cv, y_range, count, colors, blade)` | Blades of grass |
| `leaves(cv, center, reach, count, colors, size, blur_px)` | Cluster of leaves. Placed at a corner it frames the picture |
| `petals(cv, count, color, size, region, blur_range)` | Drifting petals |
| `wash_backdrop(cv, colors, scale, strength)` | Abstract background of bleeding color |

## 6. City (city)

`from paintkit import city`. Details and examples in `references/city.md`.

| Function | Description |
|---|---|
| `facade(width_m, height_m, wall, glass, lit, lit_ratio, shop, resolution, seed)` | One building face as a flat Canvas |
| `skyline(cv, base_y, height, width, color, lit, lit_ratio, window_px, seed)` | One row of distant building silhouettes |
| `Perspective(vanishing, focal, eye)` | One-point camera. `project`, `scale`, `wall_quad`, `front_quad`, `ground_quad`, `quad(corners)` (any 3D quad) |
| `Camera(center, focal, position, yaw=0, pitch=0)` | Turnable, tiltable camera (two- and three-point perspective). `project`, `quad`, `depth`, `scale_at`, `vanishing_point`, `horizon_y` |
| `project_polygon(view, points, near=0.3)` | Projects a flat polygon that runs behind the camera, keeping only the part in front |
| `ground_rects(cv, view, rects, y=0)` | Mask of rectangles on the ground `[(x0, z0, x1, z1)]` |
| `street(cv, view, ...)` | Road, pavements and rows of buildings on both sides |
| `road_texture(width_m, length_m, asphalt, line, lanes, crosswalk_at)` | A road seen from above, flat |
| `street_lamp(cv, view, x, z, height, glow, on)` | Street lamp |

## 7. Modern objects (solids)

`from paintkit import solids`. Details and recipes in `references/objects.md`.

| Function | Description |
|---|---|
| `box(cv, view, origin, size, color, light_from, top_color, edge, turn=0)` | Box on the ground. Paints the visible faces only and returns the face quads and masks. `turn` rotates it about the vertical axis |
| `patch(quad, left, top, right, bottom)` | Part of a face cut by fractions (perspective-correct) |
| `disc(cv, view, center, y, radius, depth_radius)` | Circle lying on a horizontal plane |
| `contact_shadow(cv, view, center, y, radius, ...)` | Contact shadow on the ground |
| `cylinder(cv, view, center, y, radius, height, color, top_radius, light, gloss, top_color, hollow)` | Standing cylinder, truncated cone, open cup |
| `barrel(cv, view, center, z_back, z_front, radius, color, ...)` | Cylinder facing the viewer (lens) |
| `slab(cv, view, points, y, thickness, color, light, ...)` | Flat object raised from an outline seen from above |
| `flat_shape(cv, view, points, y)`, `flat_path(view, points, y)` | Mask and path of an outline on a horizontal plane |

New tools of the figure rigs (details in `references/fullbody.md`)

| Function | Description |
|---|---|
| `figure.aim(turn, upper, lower)` | Turns limbs given as 3D directions into screen angles and length shares. Seated poses, foreshortening, arms in profile and back views |
| `figure.seen_from_behind(pose)` | Whether the back of the body faces the viewer (`turn` from about 105 degrees). For picking back-view props in scene code |
| `figure.framing(size, shot, center=0.5, headroom=0.55)` | `pelvis`, `height` zooming the full-body rig. shot: `full`, `knee`, `thigh`, `waist`, `bust`, `face` |
| `figure.fit(box, pose, sex, align, scale)` | `pelvis`, `height` that fit a posed figure into a box as large as possible |
| `figure.thirds(size, column, margin)` | Box centered on a rule-of-thirds line (`left`, `center`, `right`) |
| `figure.group(box, poses, sexes, scales, gap, shot=None, headroom)` | Placements of several figures side by side on one floor line. `shot='waist'` and so on for group close-ups |
| `figure.pose_bounds(figure)` | Screen box a figure occupies |
| `figure.poses.*` | 12 pose presets (`contrapposto`, `arms_crossed`, `hands_on_hips`, `hands_in_pockets(pouch=False)`, `stretch`, `walk`, `run`, `cross_legged_seat`, `squat`, `sit_floor`, `lean_wall`, `lie_side`). `poses.POSES` is a table of names and functions |
| `wardrobe.bikini`, `innerwear`, `hoodie`, `crop_top`, `hot_pants`, `suit` | Outfits (`references/fullbody.md` section 11) |
| `wardrobe.long_coat`, `padded_jacket`, `scarf`, `beanie`, `boots` | Winter outerwear, scarf, beanie, boots. `beanie` is painted after the head (`references/fullbody.md` section 11) |
| `Figure(sex='male')`, `MALE_FACE`, `MALE_HAIR` | Male build, face and hair presets |
| `figure.hairstyle(name, **changes)` | 24 named hairstyles (`FEMALE_STYLES` 12, `MALE_STYLES` 12, combined table `HAIRSTYLES`). Tied styles and clipper cuts included (`references/fullbody.md` section 16) |
| `figure.face_style(sex, name, **changes)` | 4 face styles per sex (`FACE_STYLES`) |
| `figure.expression(face, name, amount=1.0)` | Puts one of 8 expressions (`EXPRESSIONS`) on a face. `amount` sets its strength (`references/fullbody.md` section 17) |
| `skeleton.chest.surface(x, y)`, `.back_surface(x, y)` | Screen position on the front or back of the turned torso. For attaching cloth patterns or tattoos to the body |
| `skeleton.chest.facing(x, y, back=False)` | How much that point faces the viewer (1 head-on, 0 on the outline, negative hidden). For fading marks drawn on top |

## 8. Finish (finish)

`from paintkit import finish`

| Function | Main arguments |
|---|---|
| `finish_anime(cv, glow=0.22, diffusion=0.10, contrast=1.05, saturation=1.06, shadows, highlights, aberration=0.8, grain_amount=0.012)` | glow: bloom strength. diffusion: overall soft filter |
| `finish_illustration(cv, glow=0.24, line_soften=0.7, texture=0.035, contrast, saturation)` | texture: strength of the paper grain |
| `finish_watercolor(cv, paper, wash=0.14, edge_darkening=1.3, bleed=3.5, turbulence=0.34, granulation=0.24, wobble=2.5, line_color, line_opacity=0.7, border=0.06)` | wash: how watery. border: margin share, 0 for no margin |
| `finish_oil(cv, radii=(28,14,7,3), impasto=0.35, canvas_weave=0.025, keep_lines=1.0, ground, detail=None)` | radii: brush radii (largest first). detail: mask of the area repainted carefully |

Parts for assembling your own: `bloom`, `grade`, `vignette`, `grain`, `chromatic_aberration`, `light_wash(image, field, color, mode, opacity)`, `paper_texture`, `line_art(cv)`, `contact_sheet(images, columns)`.

- Every finish function takes a `seed`
- Oil takes 20-30 seconds at 1024x1280, the others under 10 seconds
- Oil brush strokes never start on a form edge. They pull back into the side their color belongs to, so no grey dotted line of two mixed colors forms on the edge

## 9. Doomer mood (doomer)

`from paintkit import doomer`. A mood preset. Design direction and examples in `references/doomer.md`

| Function | Main arguments |
|---|---|
| `PALETTE` | Table of named colors (`night`, `concrete`, `sodium`, `snow`, `ember` and so on) |
| `panel_facade(width_m, floors, wall=None, lit_ratio=0.2, balconies=0.45, glazed=0.5, entrances=0, windows=True, resolution=None)` | Canvas of one face of a panel apartment block. Attach it with `paste()` |
| `panel_block(cv, view, x0, x1, z0, z1, floors, wall=None, lit_ratio=0.2, balconies=0.45, glazed=0.5, entrances=2, antennas=2, shade=0.45, haze=None, haze_amount=0.0)` | Box-shaped apartment block on the ground. Paints only the faces the eye sees. Windows on the long faces, a shaded blank wall on the short ones. Works with both `Perspective` and `Camera` |
| `utility_pole(cv, base, height, color=None, arm=True)` | Utility pole. Returns the list of points to hang wires on |
| `pylon(cv, base, height, color=None)` | Lattice transmission tower. List of arm-tip points (lower arms first, left first) |
| `wires(cv, spans, sag=0.05, width=1.2, color=None, opacity=0.9)` | `spans`: list of (start, end) points. `sag`: droop relative to the span length |
| `bare_tree(cv, base, height, color=None, birch=False, spread=26.0, lean=0.0)` | Leafless tree. With `birch=True` the trunk and main limbs have white bark |
| `snowfall(cv, count, size=2.2, color=None, region=None, opacity=0.85)` | Snowflakes. Some come large and blurred, close to the camera |
| `smoke(cv, start, rise, drift=0.0, width=3.0, color, opacity=0.45, strands=4)` | Wavering, spreading strands of smoke and a faint haze |
| `lamp_glow(cv, point, radius, color=None, strength=0.8)` | Light bleeding from a lamp with a bright core |
| `cigarette(cv, base, tip, width, lit=True)` | Filter, paper, ember. Returns the position of the ember |
| `mouth_point(head, side=1.0)` | Pixel position of the mouth corner and the screen direction the face points to |
| `finish(cv, glow=0.3, warmth=0.5, fade=0.35, saturation=0.68, grain_amount=0.045, vignette_strength=0.32, posterize=0.18)` | Doomer finish. `warmth`: sodium orange in the lights. `fade`: how far blacks are lifted toward navy |

- Functions that use randomness (`panel_facade`, `panel_block`, `bare_tree`, `snowfall`, `smoke`, `finish`) take a `seed`

## 10. Width profiles

The `profile` argument of `ribbon` and `ink`. How the width changes from the start (0) to the end (1) of a stroke.

| Name | Shape | Use |
|---|---|---|
| `taper` | thin-thick-thin | General pen lines, leaves, petals |
| `in` | Starts heavy, ends in a point | Lashes, blades of grass, crease lines |
| `out` | Starts in a point, ends heavy | |
| `flat` | Constant width, ends closed round | Strings, rims, bands. For square-ended bars use `polygon` |
| `brush` | Swells fast, long release | Brush touches |
| `lock` | Narrow root, broad body, pointed tip | Hanging locks of hair |
| `clump` | Broad body that closes sharply at the end | Clumps of bangs |
| `finger` | Tapers slightly, ends rounded | Fingers, toes, round bars |

A list of numbers `[0.3, 1.0, 0.6]` or a function `lambda t: ...` works too.

## 11. Settings

`paintkit/config.py`: `SUPERSAMPLE` (edge quality), `SPLINE_SAMPLES`, `RIBBON_STEP_PX`, `DEFAULT_WIDTH/HEIGHT`, `DEFAULT_SEED`.
