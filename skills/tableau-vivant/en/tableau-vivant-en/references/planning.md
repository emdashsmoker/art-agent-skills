# Planning options

The options to offer the user, the recommended defaults, and where each lands in the spec, axis by axis

## How to ask

- Pick only the open axes and ask about them in one batch
    + Offer 3-5 options and one recommended default per axis
    + Do not ask again about an axis the request already settles
- If the user answers "you decide" or "go with the recommendation", apply the defaults and report what was applied once
- Resolve conflicts between axes before asking
    + Example: choosing ink wash makes the colour axis matter less. Leave that axis out of the questions

## Axis 1. Purpose

| Option | Canvas | Note |
| --- | --- | --- |
| Illustration to look at (default) | `aspect "4:5"` | Figure-centred |
| Profile picture, icon | `"1:1"` | Bust or face |
| Poster, cover | `"2:3"` or `"3:4"` | Full figure, leave margins |
| Wallpaper | `"16:9"` | Landscape, or the figure placed to one side |
| Phone wallpaper | `"9:16"` | Vertical composition |
| Stock illustration | `"1:1"` or `"4:3"` | `flat` style, plain background |
| Concept sheet, study | `"3:4"` | `pencil`, `lineart`, `clay` |

## Axis 2. Subject and genre

| Genre | Components | Starting example |
| --- | --- | --- |
| Portrait | One person in `figures`, `studio` or `plain_color` | `portrait_anime.json` |
| Full figure | `figures`, a pose preset | `classical_venus.json`, `webtoon_evening.json` |
| Figure and background | `figures`, `landscape` | `hanbok_ink_wash.json`, `kimono_woodblock.json` |
| Several people | Two or more in `figures`. Two people touching use `pairs`; a row of three or more touching uses `groups`. People in a landscape use the camera's `fit: "people"` | `seaside_walk_watercolor.json`, `couple_dance_classical.json`, `anime_friends_trio.json`, `gouache_picnic.json` |
| Male figure | Male presets, beards, men's hairstyles | `classical_david.json`, `nude_male_anime.json`, `portrait_bearded_oil.json`, `webtoon_suit_city.json` |
| Landscape | A `landscape` preset | `lake_watercolor.json`, `city_night_street.json` |
| Still life | `room`, `props` | `still_life_oil.json`, modern still life `modern_desk_digital.json` |
| Interior scene | `room`, furniture and devices | `living_room_night.json` |
| Stock art | `figures`, `props`, `plain_color` | `stock_office_flat.json` |

## Axis 3. Style

| Family | Style names | Suits |
| --- | --- | --- |
| Cel | `anime`, `anime_film`, `webtoon`, `comic`, `manga`, `lineart` | Characters, action, cities |
| Flat | `flat`, `woodblock` | Stock art, East Asian figures and landscapes |
| Water media | `watercolor`, `watercolor_loose`, `ink_wash`, `gouache` | Landscapes, lyrical figures, background art |
| Oil | `oil`, `impasto`, `classical`, `baroque`, `impressionist`, `pointillist`, `expressionist` | Still life, classical figures, landscapes |
| Dry media | `pastel`, `pencil`, `charcoal`, `pen`, `pen_wash` | Studies, figure studies |
| Digital | `digital` | Semi-realistic figures |

- The default depends on the subject
    + Character figures `anime`, realistic figures `webtoon` or `digital`, classical nudes `classical`
    + Landscapes `watercolor` or `gouache`, still life `oil`, stock art `flat`
- If the user cannot settle on a style, first show a three-style comparison sheet with `--styles`

## Axis 4. Figures

| Item | Options | Default |
| --- | --- | --- |
| Build and face | Women: `woman` (sharp jawline), `woman_curvy`, `woman_slender`, `woman_soft`, `woman_athletic`, `woman_classical`, `woman_mature`, `woman_elder`, `woman_anime` / Men: `man`, `man_athletic`, `man_slim`, `man_classical`, `man_mature`, `man_elder`, `man_anime` / `androgynous` | `woman` |
| Skin | `porcelain`, `fair`, `light`, `medium`, `olive`, `tan`, `brown`, `dark`, `marble` | `light` |
| Hairstyle | `long_straight`, `long_wavy`, `very_long`, `shoulder`, `long_male`, `bob`, `pixie`, `curly`, `afro`, `buzz`, `short_crop`, `textured_crop`, `side_part`, `undercut`, `slick_back`, `ponytail`, `low_ponytail`, `bun`, `chignon`, `man_bun`, `bald` | Women `long_straight`, men `side_part` |
| Beard | `none`, `stubble`, `short_beard`, `full_beard`, `goatee`, `mustache` | `none` |
| Face stylisation | `none`, `semi`, `anime`, `chibi` | Preset default |
| Fringe | `none`, `wispy`, `full`, `side`, `curtain`, `long` | `none` |
| Hair colour | `black`, `dark_brown`, `brown`, `auburn`, `red`, `blonde`, `golden`, `platinum`, `gray`, `white`, `silver`, `blue`, `pink`, `purple`, `teal` | `dark_brown` |
| Eye colour | `dark`, `brown`, `hazel`, `amber`, `green`, `blue`, `gray`, `violet`, `red` | `brown` |
| Expression | `neutral`, `soft_smile`, `smile`, `serene`, `eyes_closed`, `serious`, `determined`, `sad`, `surprised`, `angry`, `melancholy`, `smirk` | `neutral` |
| Outfit | The outfit table in `references/figures.md` | Suggest one to fit the subject |
| Pose | The pose table in `references/figures.md` | `contrapposto` |

- If the user has stated a taste, replace the defaults with it
- Figures under 18 are drawn clothed only. No nudity, underwear or sexual staging (the engine checks the outfit)

## Axis 5. Composition

| Item | Options | Default |
| --- | --- | --- |
| Shot | `full` (full figure), `knee`, `cowboy` (from mid-thigh), `medium` (from the waist), `bust`, `closeup`, `face`, `over_shoulder` (two people talking) | `bust` for portraits, `full` for full figures |
| Eye height | `pitch` negative (looking up; -15 or lower goes wide-angle near the ground), 0-5 (eye level), 15 or more (looking down) | 3 |
| Tilt | `roll` angle (dutch tilt: unease, tension) | 0 |
| Direction | `yaw` 0 (front), ±20 (slightly off), ±45 (three-quarter), ±90 (profile), 180 (from behind) | -15 |
| Placement | `offset` [x, y] in frame fractions. Around ±0.12 is the thirds | [0, 0] |
| Margin | `fill` 0.6 (lots of margin) to 0.9 (filled) | 0.82 |

## Axis 6. Lighting

| Preset | Impression | Suits |
| --- | --- | --- |
| `three_quarter` (default) | Natural modelling | Everything |
| `front`, `loop`, `butterfly` | Few face shadows, bright | `anime`, `flat`, beauty portraits |
| `rembrandt` | A triangle of light on one cheek, dramatic | `classical`, `oil`, `baroque` |
| `side`, `split` | Hard light and dark split | `charcoal`, `comic`, noir |
| `rim`, `back` | Edge light, atmosphere | `anime_film`, `webtoon`, `digital` |
| `soft`, `flat` | Weak shadows | `flat`, `watercolor` |
| `top`, `under` | Stage, horror | Special effects |

- Mood colour (`mood`): `neutral`, `warm`, `cool`, `candle`, `moon`, `old_master`, `pastel`, `neon`, `noir`
- Outdoors, the time of day sets the lighting: `day`, `golden_hour`, `sunset`, `dawn`, `overcast`, `dusk`, `night`

## Axis 7. Colour

| Option (`post.grade`) | Impression |
| --- | --- |
| `natural` (default) | Keeps the style's own colours |
| `warm`, `cool` | Shifts colour temperature |
| `vivid`, `muted`, `pastel` | Adjusts saturation |
| `monochrome`, `sepia`, `noir` | Single-hue families |
| `vintage`, `cinematic`, `dreamy`, `neon` | Staged looks |

- Individual colours can be set directly
    + Outfit colours in `figures[].colors`, prop colours in `props[].colors`, background colours in `environment`

## Axis 8. Detail

| Option (`canvas.detail`) | Long side | Use | Time |
| --- | --- | --- | --- |
| `draft` | 640px | Drafts, style comparison | Seconds |
| `standard` (default) | 1024px | General viewing | 10-30 s |
| `fine` | 1536px | Print, face detail | 30-90 s |
| `max` | 2048px | Large output | 1-3 min |

> (Timing basis) Measured on 2 CPU cores. The oil family is the slowest

## Axis 9. Background

| Option | Description |
| --- | --- |
| `plain_color` | A single colour. Stock art, studies |
| `studio` | A gradient backdrop and floor shadow. The portrait default |
| `room` | Walls and floor. Still life, people indoors |
| `landscape` | `meadow`, `hills`, `mountain_lake`, `seaside`, `forest`, `desert`, `snow`, `garden`, `city`, `plain` |

## Design direction document template

Before writing the spec, write `brief.md` in the form below

```markdown
# (Title of the picture)

## Core impression
- One sentence: the impression the viewer should feel first

## Composition
- (Subject) Who or what is where
- (Framing) Shot, viewpoint, placement in the frame and margins
- (Eye path) Where the eye lands first and how it moves

## Colour and tone
- (Dominant colours) One or two colours that rule the frame
- (Accent colour) One colour that draws the eye, and where it is
- (Value) A light picture or a dark one, and how strong the contrast is

## Light
- Direction and character of the light source, mood colour

## Style
- The style chosen and why
- Parameters to adjust and the intent

## Choices settled and defaults applied
- Items the user decided
- Items filled with defaults
```
