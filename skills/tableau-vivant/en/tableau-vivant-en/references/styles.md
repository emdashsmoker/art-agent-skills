# Styles

The style list, tuning parameters, how to recreate art movements, and fixes for problems

## How to set

```json
"style": "watercolor"
"style": {"name": "oil", "impasto": 1.0, "saturation": 1.1}
```

- Compare one scene in several styles: `python scripts/render.py spec.json -o sheet.png --styles anime,gouache,oil`
- A style's own finish (`bloom`, `grain` and so on) can be overridden with `post`

## Cel family

| Name | Description | Recommended light |
| --- | --- | --- |
| `anime` | TV anime cel. Two tones, coloured lines, simplified face shadows | `front`, `loop`, `three_quarter` |
| `anime_film` | Realistic feature-film cel. Three tones, thin dark lines, restrained saturation, film grain | `rim`, `rembrandt`, night |
| `webtoon` | Semi-realistic webtoon. Soft tone edges, gradients, thin coloured lines, glow | `rim`, `three_quarter` |
| `comic` | Western comics. Heavy black lines, halftone shadows | `side`, `rembrandt` |
| `manga` | Black-and-white manga inking. Black hair and dark clothes in solid ink, screentone shadows | `side`, `front` |
| `lineart` | Line drawing only | Any |

| Parameter | Default | Effect |
| --- | --- | --- |
| `shadow_threshold` | 0.40 | How wide the shadow area is. Higher means wider shadows |
| `deep_threshold` | None | Edge of the second shadow step (three tones) |
| `shadow_tint`, `skin_shadow_tint` | Auto | Shadow colour multiplier. Skin defaults to a warm pink |
| `band_softness` | 0.012 | Softness of tone edges. 0.1 gives a webtoon look |
| `face_smooth` | 2.6 | Simplifies face shadows. 4-5 gives an anime face |
| `quiet_face` | false | Leaves out nose and cheek lines inside the face, drawing only the outline and features. `anime` defaults to true |
| `relief_lines` | 0 | Thin lines along muscle grooves (abs, under the chest). Darker on the shadow side. `anime` defaults to 0.45 |
| `face_lift` | 0 | Brightens the face's half-tones so only the side turned away from the light keeps shadow. `anime` defaults to 0.45 |
| `gradient` | 0 | A subtle modelling gradient under the tones |
| `highlight_threshold`, `rim_light` | None, 0 | Highlight tone, rim light |
| `gloss_highlight`, `gloss_threshold` | 0.8, 0.16 | Strength and width of the bright patches drawn on glossy materials (glass, lips, glossy skin) |
| `line_width` | 1.6 | Line width (pixels). 0 means no lines |
| `colored_lines` | 0.6 | 0 gives single-colour lines, 1 coloured lines that follow the fill colour |
| `line_taper`, `line_wobble` | 0 | Line pressure variation, hand tremor |
| `thin_in_light` | 0.5 | Thins lines on the lit side |
| `halftone_shadows` | false | Halftone dots for shadows |
| `saturation` | 1.0 | Saturation |
| `background_blur` | 0 | Blurs the background. Separates the figure |

## Flat family

| Name | Description |
| --- | --- |
| `flat` | Flat vector, stock illustration. No outlines, one soft shadow step, grainy gradients |
| `woodblock` | Ukiyo-e woodblock print. Limited inks, even key lines, bokashi in the sky, wood grain |

- `flat` parameters: `shadow_strength` 0.16, `pastel` 0.12, `grain` 0.06, `line_width` 0, `blob [x, y, radius]` and `blob_color` (an organic shape behind the subject)
    + For stock illustration, put a `blob` on a `plain_color` background with `soft` light
- `woodblock` parameters: `line_width` 1.7, `bokashi` 0.55, `bokashi_color`, `grain` 0.35, `misregister` 1.2, `palette` (list of colours), `palette_softness` 0.18

## Water media family

| Name | Description |
| --- | --- |
| `watercolor` | Transparent watercolour. Pencil underdrawing, pigment pooling at edges, paper grain |
| `watercolor_loose` | Wet-in-wet. Large blooms, no underdrawing |
| `ink_wash` | Ink wash. Three ink values, brush lines with pressure, mist, a seal |
| `gouache` | Opaque watercolour. The texture of animation background art |

| `watercolor` parameter | Default | Effect |
| --- | --- | --- |
| `wash_levels` | (0.34, 0.66) | How many shadow washes overlap and where they end |
| `paper_white` | 0.86 | Anything brighter is left as white paper |
| `edge_darkening` | 0.42 | Pigment pooling at the edge of a wash |
| `granulation`, `turbulence` | 0.32, 0.28 | Paper grain granules, water stains |
| `bleed`, `wobble`, `simplify` | 1.6, 2.2, 3.0 | Bleeding, edge wobble, detail simplification |
| `pencil` | 0.30 | Strength of the pencil underdrawing |
| `vignette_wash` | true | On a plain background, paints only around the subject and leaves paper margins |
| `background_wash` | Auto | Colour of the surrounding wash |

- `ink_wash` parameters: `levels`, `line_width` 2.2, `mist` 0.5, `dry_brush` 0.45, `color_hint` 0.12 (light colour), `seal` true, `paper_color`
    + Empty space matters. Lower the camera `fill` to 0.5-0.65 and use `offset` to place the subject to one side

## Oil family

| Name | Description | Recommended light |
| --- | --- | --- |
| `oil` | Alla prima. Visible brushwork, a warm ground | `rembrandt`, `three_quarter` |
| `impasto` | Thick paint, palette-knife touches | `side` |
| `classical` | Renaissance and academic oil. Sfumato, glazes, varnish, craquelure | `rembrandt` + `old_master` |
| `baroque` | Tenebrism. Figures emerging from darkness | `side`, `rembrandt` + `candle` |
| `impressionist` | Short strokes, broken colour, a bright palette | Outdoors `day`, `golden_hour` |
| `pointillist` | Dots of pure colour | Outdoors |
| `expressionist` | Long, heavy strokes, heightened colour, swirls | Free |
| `pastel` | Soft pastel. Toned paper, chalk catching on the paper grain | `soft` |

| `oil` parameter | Default | Effect |
| --- | --- | --- |
| `brush_radii` | (26, 12, 6, 3, 1.6) | Brush size steps. Painted over from large brush to small |
| `stroke_length` | 9 | Stroke length |
| `fidelity` | 0.35 | How finely faces and hands are finished |
| `color_jitter`, `hue_jitter` | 0.05, 0 | Value change per stroke, hue change per stroke |
| `impasto` | 0.5 | Paint thickness |
| `ground` | Brown | Ground colour. Shows between strokes |
| `along_form` | false | Switches brush direction from wrapping the form to following it |
| `swirl` | 0.3 | How much brush direction swirls in sky and background |
| `terminator_saturation` | 0.3 | Saturation boost at the light-shadow edge |
| `contrast`, `saturation` | 1.0 | Observed contrast and saturation |
| `coverage`, `density` | 1.0 | How much ground shows, stroke density |

| `classical` parameter | Default | Effect |
| --- | --- | --- |
| `finish` | 0.62 | 0 is rough brushwork, 1 a smooth academic finish |
| `sfumato` | 1.6 | Blur of contours |
| `lost_edges` | 0.5 | How far shadow-side contours melt into the background |
| `chiaroscuro` | 1.2 | Light-dark contrast |
| `umber` | Dark umber | Underpainting colour the shadows sink into |
| `glaze`, `varnish` | Amber, 0.30 | Yellowing of the varnish |
| `craquelure`, `vignette` | 0.35, 0.35 | Cracking, darkening at the edges |

## Dry and digital family

| Name | Description | Main parameters |
| --- | --- | --- |
| `pencil` | Graphite hatching | `hatch_spacing` 5, `darkness` 0.85, `smudge` 0.25, `line_width` 1.3 |
| `charcoal` | Charcoal. Rough paper | `darkness` 1.0 |
| `pen`, `pen_wash` | Pen cross-hatching, sepia wash | `hatch_spacing` 4, `wash` |
| `digital` | Semi-realistic digital painting | `smooth` 0.55, `stroke_opacity` 0.5, `edge_line` 0.35, `rim_light` 0.25, `skin_glow` 0.18 |
| `clay` | Plain shading for checking the underdrawing | None |

## Doomer family (this skill's signature)

The mood of post-Soviet post-punk records and internet doomer drawings. Panel apartment estates at night, sodium street lamps, the ember of a cigarette

| Name | Description | Recommended scenes |
| --- | --- | --- |
| `doomer` | A night drained to grey-blue. Only warm, bright things keep their colour: sodium lamps, lit windows, embers. Film grain, edge falloff | `estate`, `estate_street` at night, a kitchen under a bare bulb |
| `doomer_mono` | A coarse-grained black-and-white film photograph. Deep blacks and a grey sky | An estate at dusk, a bleak winter field |

| Parameter | Default | Effect |
| --- | --- | --- |
| `desaturate` | 0.6 | How far colours that are not warm are drained to grey |
| `keep_warm` | 1.0 | How much warm, bright colours are kept. 0 drains everything |
| `contrast` | 1.25 | Black-and-white contrast of `doomer_mono` |

- Composition tips
    + Keep people small and the repeating window grid large
    + Warm light in only one or two places. One street lamp, one ember
    + Lower the moonlight (`"light": {"key": 0.3, "ambient": 0.2}`)
    + Dress people in dark clothes (`hoodie_jeans`, `long_coat`) with a `beanie`
- Examples: `doomer_man`, `doomer_woman`, `doomer_pair`, `doomer_establishing`, `doomer_city`, `doomer_landscape`, `doomer_still`
- Do not copy the composition or people of a particular record cover. Take only the mood

## Recreating art movements and genres

| Goal | Setup |
| --- | --- |
| Renaissance nude, Venus | `woman_classical`, pose `venus` or `contrapposto`, long wavy blonde hair, `nude` or `chiton`, a dark `studio` with `glow`, lighting `rembrandt` + `old_master`, style `classical`, `look.flesh_variation` 0.6 |
| Odalisque, reclining nude | Pose `recline`, props `daybed` and `cloth`, figure `position` z 0.47, style `classical` or `oil` |
| Anime-style nude | `woman_anime` or `woman_curvy`, pose `arms_behind_head` or `s_curve`, `look.skin_gloss` 0.4, lighting `loop` + `pastel`, style `anime` or `webtoon` |
| Classical male nude, David | `man_classical`, pose `david`, short curls (`curly`, `length_scale` 0.45), `perizoma`, a dark `studio`, lighting `rembrandt` + `old_master`, style `classical` |
| Anime-style male nude | `man_anime` or `man_athletic`, pose `arms_behind_head` or `heroic`, `briefs`, `look.muscle_definition` 0.45, lighting `loop`, style `anime` |
| Bearded male portrait | `man_mature`, `beard: full_beard`, `slick_back`, `suit`, lighting `rembrandt`, style `oil` or `classical` |
| Nude from behind | Pose `look_over_shoulder`, camera `yaw` 160, style `watercolor` or `pastel` |
| Baroque portrait | Lighting `side` + `candle`, style `baroque`, `ambient` 0.12 |
| Dutch still life | `room` (dark walls), `table`, `cloth`, vessels and fruit, lighting `rembrandt` + `old_master`, style `oil` or `classical` |
| Impressionist outdoors | `meadow` or `garden`, time `day`, style `impressionist`, small figures |
| Post-impressionist swirls | Style `expressionist`, `swirl` 1.0, a night landscape |
| Pointillism | Style `pointillist`, outdoors, `canvas.detail` `fine` |
| Ink-wash landscape | `hills` or `mountain_lake`, time `overcast`, `haze_distance` 60, style `ink_wash`, `mist` 0.7 |
| Ink-wash figure, beauty painting | `hanbok`, `chignon`, a composition with lots of empty space, style `ink_wash`, `color_hint` 0.2 |
| Ukiyo-e beauty print | `kimono`, `chignon`, `sakura` in a `garden`, style `woodblock` |
| Ukiyo-e landscape | `seaside` or `snow`, time `dawn`, style `woodblock` |
| TV anime character | `woman_anime`, lighting `loop` + `pastel`, style `anime` |
| Realistic feature-film cel | `woman_athletic` or `woman`, `tactical`, `city` + `night`, lighting `rim`, style `anime_film` |
| Night street after rain | `city` + `night` (wet road and neon automatic), style `anime_film` or `gouache`, `post.bloom` 0.3 |
| Sea at sunset | `seaside` + `sunset`, `sun_side` `front`, style `watercolor` or `oil` |
| Semi-realistic webtoon | `woman` or `man_slim`, lighting `rim` + `warm`, style `webtoon`, `post.grade` `cinematic` |
| Semi-realistic illustration | Style `digital`, lighting `rembrandt` or `rim`, `canvas.detail` `fine` |
| Stock illustration | `plain_color`, office props, lighting `soft`, style `flat` + `blob` |
| Pop art | Style `comic`, `post.grade` `vivid` |
| Noir | Lighting `split` + `noir`, style `charcoal` or `comic`, `post.grade` `noir` |
| Figure study | `plain_color`, lighting `side`, style `pencil` or `charcoal` |

## Problems and fixes

| Symptom | Fix |
| --- | --- |
| Messy shadow fragments on the face (cel) | Lighting `front` or `loop`, `face_smooth` 4-5, `face_lift` 0.4-0.6, `shadow_threshold` 0.3 |
| Everything sunk in shadow | `light.azimuth` to 0-45, `ambient` to 0.4 or more |
| Too many, too complex lines | `crease_deg` to 50, reduce `line_width` |
| Face smeared in oil | `canvas.detail` to `fine`, a closer shot, `fidelity` 0.6 |
| Oil brushwork too rough | Smaller `brush_radii`, `color_jitter` 0.03, or switch to `classical` |
| Classical oil looks blurry | `finish` 0.8, `sfumato` 1.0, `chiaroscuro` 1.4 |
| Muddy watercolour | One wash step `wash_levels` `(0.5,)`, `saturation` 1.15, `lift` 0.2 |
| No paper margins in watercolour | A white `plain_color` background instead of `studio`, `vignette_wash` true |
| Background competes with the subject | `background_blur`, lower `haze_distance`, `post.vignette` |
| Flat colour | Change `mood`, `post.grade` `vivid` or `cinematic`, one accent colour in the outfit |
| Subject too small | One step closer shot, `fill` 0.9 |
| Monotonous picture | Thirds placement with `offset`, `yaw` ±20, add props or trees |
