# Doomer Mood

A mood document for the lonely urban feeling of post-Soviet coldwave album covers. It uses the same color, light, subject and composition rules in every style and changes only the per-style recipes. Read it together with the style document when the user asks for "doomer", "doomer vibe", "post-Soviet", "panel apartment blocks", "coldwave mood" or "the loneliness of a winter estate".

## Contents

- Core feeling
- Color
- Light
- Subjects and tools
- Composition
- Recipes by style
- Post-processing values
- Examples
- Common defects
- Boundaries

## Core Feeling

- A winter evening in an estate of gray panel apartment blocks
- The only warm light comes from sodium streetlights and a few windows
- Structures are bigger than people, and figures are alone or seen from behind

## Color

- The dominant color is one dull gray-blue family (sky, concrete, snow shade)
- Only two warm colors are allowed, sodium orange and window yellow, covering one tenth of the frame or less
    + A faded red on one figure prop (scarf) and the reddish gray of chimney bands are allowed exceptions
- Post-processing pushes saturation down to 0.78-0.9

| Role | Night | Dusk | Watercolor daylight |
|---|---|---|---|
| Upper sky | `#0b1018` | `#2a3442` | `#6f7b93` |
| Lower sky | `#253041` | `#9a7a78`, afterglow `#d8925e` | `#c4aaa0` |
| Concrete wall | `#242b36`, `#2e3642` | `#4a5260`, `#3b4250` | `#a3abb6`, side `#7f8896` |
| Snow | `#59626e`, shade `#3a424d` | `#8f9aa8`, shade `#6b7685` | paper white, shade `#c3ccd8` |
| Dark window | `#1a2029` | `#232a35` | `#626c7c` |
| Lit window | `#e9b86a` | `#f0c070` | `#f3c977` |
| TV window (cold light, 1-2 cells) | `#8fb3c9` | `#8fb3c9` | `#9cc0d6` |
| Sodium streetlight | `#f2a65a`, glow `#ffcf8a`, core `#fff1d0` | same | `#f2a65a` pale |
| Steel (poles, wires, towers) | `#1a1d22` | `#1e2228` | `#343944` |
| Chimney bands | red `#8e4a43`, white `#b9b3ad` | same | same |

## Light

- Fix one light source (streetlight, set sun, overhead lamp)
- Turn the figure's Ink toward that source: `ch.Ink(...).lit_from(light direction, 3D light direction)`
    + For a streetlight at the upper right, `(0.55, -0.85)`, `(0.45, -0.8, -0.4)`
- Increase mass shadows above the default (`body_shadow` 0.46-0.5)
- Lay a soft glow of the same color around lit windows and streetlights with SCREEN, and let the bloom of the compositing pass enlarge it
- The sun appears only as a dim disc behind clouds or an afterglow band below the horizon

## Subjects and Tools

| Subject | Tool | Example |
|---|---|---|
| Frontal panel apartment block | `Perspective.front_wall`, `front_wall_grid`, floor joint lines, balcony bands on one cell in three | `anime_doomer_bus_stop.py` |
| Blocks at an angle and estates | `s3.box` block boxes, windows and balconies with `camera.region`, far blocks first with `camera.order` | `anime_doomer_courtyard.py`, `illustration_doomer_rooftop.py` |
| Block seen from below (three-point) | `s3.Camera` at eye level tilted up, projecting balconies as rectangles pushed along the face normal plus their undersides | `watercolor_doomer_block.py` |
| Windowless gable wall | Only the floor and panel joint grid on the end face | `watercolor_doomer_block.py` |
| Striped chimney and steam | Bands clipped to a trapezoid body, `g.blob` steam that grows and drifts to one side from the top | `oil_doomer_overpass.py`, `oil_doomer_pylons.py` |
| Line of power pylons | Legs, cross bracing and two tiers of arms drawn as lines from a one-point depth list, with sagging wires joining the insulator ends of neighboring towers | `oil_doomer_pylons.py` |
| Trolley wires, streetlights | Two sagging lines across the top of the frame, a silhouette of pole, arm and shade | `anime_doomer_bus_stop.py`, `anime_doomer_courtyard.py` |
| Birches, bare branches | White ribbon trunks with black bark marks, tapering branches and twigs | `anime_doomer_courtyard.py`, `watercolor_doomer_block.py` |
| Snow-covered car | Body extruded from the profile with `s3.prism`, snow on upward faces, glass on slanted faces | `anime_doomer_courtyard.py` |
| Kitchen objects | Tea in a glass holder (glass, tea, metal ring open at the top), cassette radio, cassette tape | `watercolor_doomer_kitchen.py` |
| Falling snow | Soft dots with sizes from cubed random values. Orange-white inside the light cone | `anime_doomer_bus_stop.py`, `watercolor_doomer_block.py` |

## Composition

- Let structures take a large share of the frame
    + Keep figures at half the frame height or less, or show them from behind
    + Single-figure pictures use a knee-up or full-figure composition layered over background structures
- Repeated grids (windows, balconies, towers, wires) make a rhythm, and a few lit windows break it
- Keep the horizon low or close the frame with a facing wall
- Make one light the focal point and press the rest dark

| Scene | Composition | Example |
|---|---|---|
| Man | 3/4 front full figure at a bus stop at night, streetlight beyond the upper right, estate behind | `anime_doomer_bus_stop.py` |
| Woman | Knee-up 3/4 side view from waist height looking up, chimney and estate rising behind | `oil_doomer_overpass.py` |
| Two-shot | Two people with their backs turned holding hands on a roof, the night estate seen from above | `illustration_doomer_rooftop.py` |
| Establishing shot | Wide two-point courtyard without people | `anime_doomer_courtyard.py` |
| Cityscape | One block seen from below and its gable wall | `watercolor_doomer_block.py` |
| Landscape | Panorama of a snowfield and a line of pylons from eye level on a railway embankment | `oil_doomer_pylons.py` |
| Objects | Three objects on a kitchen table at night with the estate outside the window | `watercolor_doomer_kitchen.py` |

## Recipes by Style

- Anime style
    + Paint figures on a transparent layer and put an orange rim on the streetlight-side contour with `anime.rim_light`
    + Lay the streetlight glow first and paint the shade silhouette over it
- Oil style
    + Sky `direct(angle=-6)`, snowfield `angle=0-1`, figure silhouette `angle=85`
    + Chimneys get an area 10 wider than the outline at `angle=90`
    + Areas crowded with thin lines such as towers gather the smallest brush with `detail`
- Watercolor style
    + Lit windows get yellow on paper reserved from the wall wash
    + Walls that sit on a sky wash first cover the wall area with white and then paint with multiply
    + Falling snow returns spots to paper color with white dots at the end
- Illustration style
    + The sky is bands of five navy steps with stippled borders, and clouds are long thin bands with warm stipple only on their lower edges
    + Estate blocks paint only lit windows. Drawing dark windows too clumps far blocks into gray grids

## Post-processing Values

| Style | Values |
|---|---|
| Anime style | `anime.finish(diffusion=0.2-0.22, bloom=0.4-0.45, shadows="#0e1a2a", highlights="#ffcf8a", grade_amount=0.14, grain=0.025-0.03)` then `post.grade(contrast=1.04, saturation=0.82)`, `vignette(0.3-0.38)` |
| Oil style | `post.grade(shadows="#0e1a26", highlights="#ffd9a0", amount=0.1-0.14, contrast=1.05-1.06, saturation=0.78-0.8)`, `vignette(0.3-0.36)` |
| Watercolor style | `watercolor.render(wobble=1.0-1.2, bleed=0.4-0.45, edge=0.45-0.5, turbulence=0.18-0.2)` then `post.grade(shadows="#1a2a3a", highlights="#ffe8c8", amount=0.08, saturation=0.9)` |
| Illustration style | `illustration.render(paper_tint="#e9e4d8", ink_mottle=0.08)` |

## Examples

| Example | Scene | Style |
|---|---|---|
| `anime_doomer_bus_stop.py` | A man at a bus stop on a snowy night | Anime style |
| `oil_doomer_overpass.py` | A woman on an overpass just after sunset | Oil style |
| `illustration_doomer_rooftop.py` | Two people looking down at the night estate from a roof | Illustration style |
| `anime_doomer_courtyard.py` | Establishing shot of an estate courtyard at a winter dusk | Anime style background |
| `watercolor_doomer_block.py` | A 9-floor panel apartment block seen from below | Watercolor style |
| `oil_doomer_pylons.py` | Snowfield and a line of pylons | Oil style |
| `watercolor_doomer_kitchen.py` | Tea and a cassette radio on a kitchen table at night | Watercolor style |

## Common Defects

| Symptom | Remedy |
|---|---|
| Lit windows in watercolor turn muddy brown | Reserve the window spots from the wall wash and lay yellow there. Multiply glazing cannot lighten a dark wall |
| The watercolor wall color splits above and below the horizon | Cover the wall area on the sky wash with white, then paint |
| The bottom of an estate seen from above is empty | Place blocks within the view width on every depth row. Random x drops blocks of near rows outside the view |
| Oil chimney stripes smear sideways | Give a vertical stroke direction to an area slightly wider than the chimney outline |
| A streetlight looks like a disc floating in the air | Lay the glow first and paint the shade silhouette and rim light on top |
| The shelter glass covers the frame and blurs the estate behind | Let only the end of the shelter enter at the frame edge |
| A parked car floats | Put the lower edge of the body on the ground, lay a shadow under the car and draw only the wheel arches |
| The glass holder looks like a cup with a lid | Paint only the front side faces of the holder. `s3.draw` fills the top area into the silhouette |
| Every pylon looks like it stands on the horizon | Raise the eye level to the embankment height (5) so the tower bases spread over the ground |

## Boundaries

- Draw figures as original characters
    + Avoid the signature combination of specific meme characters (black beanie, hoodie, cigarette)
    + Include no smoking
- Do not copy the composition of real album covers, photos or specific buildings
    + Use only the genre's rules of color, light and subject
- Work within engine limits
    + Keep arms down or in held hands. A forearm pointing at the viewer makes the sleeve look like a square lump
    + Check two-shots for penetration with `stage.collisions` before painting
