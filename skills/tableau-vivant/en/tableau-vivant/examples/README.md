# Example specs

Every file renders as is. Copying the nearest example and editing it is the fastest way

```bash
python scripts/render.py examples/portrait_anime.json -o out.png
```

| File | Genre | Style | Settings worth a look |
| --- | --- | --- | --- |
| `portrait_anime.json` | Bust portrait | `anime` | `woman_anime`, a palm laid flat on the chest with `reach` and `lay`, hand shape `rest` |
| `classical_venus.json` | Classical figure study | `classical` | Pose `venus`, a dark background and `old_master` lighting |
| `figure_study_odalisque_oil.json` | Reclining figure study | `classical` | Pose `recline`, `daybed` and `cloth`, figure height set |
| `figure_study_anime.json` | Anime-style figure study | `anime` | `woman_anime`, glossy skin (`skin_gloss`) |
| `figure_study_back_watercolor.json` | Figure study from behind | `watercolor` | Pose `look_over_shoulder`, camera `yaw` 158 |
| `film_cel_agent.json` | Figure and city at night | `anime_film` | `city` at night, `tactical` outfit, low viewpoint |
| `webtoon_evening.json` | Semi-realistic figure | `webtoon` | Rim light, `post.grade` |
| `hanbok_ink_wash.json` | Figure and empty space | `ink_wash` | Hanbok, a composition with empty space (`fill`, `offset`) |
| `kimono_woodblock.json` | Figure and garden | `woodblock` | Kimono, a hand laid on the belly (`lay`), a cherry grove set explicitly |
| `seaside_walk_watercolor.json` | Two people | `watercolor` | Walking hand in hand with `pairs` `hold_hands`, camera set directly |
| `couple_dance_classical.json` | Couple dance | `classical` | `pairs` `dance`, candlelit interior mood |
| `stock_office_flat.json` | Stock illustration | `flat` | Seated pose, office props, `blob` background |
| `still_life_oil.json` | Still life | `oil` | Placing on a table with `on` |
| `modern_desk_digital.json` | Modern still life | `digital` | Monitor (`screen: code`), keyboard, phone, bookshelf, wall clock |
| `living_room_night.json` | Interior at night | `anime_film` | A figure lit by a TV (`screen: game`), sofa, low key light and `glow` |
| `lake_watercolor.json` | Landscape | `watercolor` | Snowy mountains and lake reflections, forest clumps, a framing foreground tree |
| `city_night_street.json` | Cityscape | `anime_film` | Night street, neon, wet road |
| `garden_impressionist.json` | Figure in a landscape | `impressionist` | A small figure, a bench |
| `pencil_figure_study.json` | Figure study | `pencil` | Male build, side light |
| `classical_david.json` | Classical male figure study | `classical` | `man_classical`, pose `david`, `perizoma` |
| `figure_study_male_anime.json` | Anime-style male figure study | `anime` | `man_anime`, `muscle_definition`, low viewpoint |
| `male_back_watercolor.json` | Man from behind | `watercolor` | `man_athletic`, `undercut`, `stubble` |
| `portrait_bearded_oil.json` | Bearded male portrait | `oil` | `man_mature`, `full_beard`, suit |
| `webtoon_suit_city.json` | Man in the city | `webtoon` | `hands_in_pockets`, suit colours set (`colors`), `stubble`, city at dusk, placed on the pavement |
| `doomer_man.json` | Doomer man | `doomer` | `estate` at night, a figure behind a street lamp, `hoodie_jeans` and `beanie`, pose `smoke` with a held `cigarette` |
| `doomer_woman.json` | Doomer woman | `doomer` | `estate_street` at night, a figure seated inside a `bus_stop`, `long_coat` |
| `doomer_pair.json` | Doomer two-shot | `doomer` | A bench in the estate courtyard, `sit_smoke`, two people looking different ways, a light with no visible source on their faces (`lights`) |
| `doomer_establishing.json` | Doomer establishing shot | `doomer_mono` | `estate` at dusk, a small figure crossing the courtyard, utility poles |
| `doomer_city.json` | Doomer city | `doomer` | `estate_street` at night, road and crossing, a row of sodium lamps |
| `doomer_landscape.json` | Doomer landscape | `doomer_mono` | A bleak winter field, `power_line`, distant `panel_block` and a band of conifers |
| `doomer_still.json` | Doomer still life | `doomer` | A hanging bare bulb (`lightbulb` with `cord`), `ashtray`, `radio`, a phone face down |
| `comic_desert_duel.json` | Duel two-shot | `comic` | Desert at dusk, two people in `fight_stance` facing off, turned slightly toward the camera (`facing` with coordinates), low angle, `fit: "people"` |
| `manga_farewell_hug.json` | Farewell hug | `manga` | `pairs` `hug`, a single panel on white, a `medium` shot from behind at an angle, black clothes and hair in solid ink |
| `gouache_picnic.json` | Picnic group | `gouache` | Three people sitting round a blanket (`cloth`) and one reclining in front, `facing` with coordinates, high angle, `fit` with figure and prop names |
| `impasto_cafe_talk.json` | Café conversation | `impasto` | Round table and chairs, a seated hand holding a cup (`held_by`), over-the-shoulder shot |
| `baroque_candle_reading.json` | Reading by candlelight | `baroque` | `read_seated` with an open `book`, `candle` light, `fit` on the figure and the candle |
| `pointillist_lakeside_park.json` | Lakeside park | `pointillist` | Two people walking away hand in hand (`pairs` `facing` 180), a figure reading on the grass |
| `expressionist_leap.json` | Leap | `expressionist` | `jump`, low angle and dutch tilt (`roll`) |
| `pastel_dance_rehearsal.json` | Dance rehearsal | `pastel` | `pairs` `dance` with `distance`, a third figure warming up |
| `charcoal_studio_trio.json` | Three models study | `charcoal` | Standing, kneeling, sitting propped up. `chiton`, `perizoma`, figure study |
| `pen_office_meeting.json` | Meeting room | `pen` | Desk, office chairs, laptops, a chart screen (`tv` `screen: chart`), a presenter standing and pointing |
| `pen_wash_park_bench.json` | Old couple on a bench | `pen_wash` | Seated `arm_around`, `man_elder` and `woman_elder`, `long_coat` open at the front |
| `watercolor_loose_beach_play.json` | Beach ball game | `watercolor_loose` | `run`, `jump`, `arms_up`, a `ball` in the air (`at` height), three swimwear outfits |
| `lineart_fashion_lineup.json` | Outfit lineup | `lineart` | Five people side by side, five outfits and five poses |
| `anime_film_dusk_phone.json` | Two people looking at a phone | `anime_film` | `hand_on_shoulder`, `look_at_phone` with a held `phone`, city at dusk |
| `digital_portrait_closeup.json` | Close-up portrait | `digital` | `closeup`, `man_mature`, `short_beard`, `rembrandt` lighting |
| `anime_friends_trio.json` | Three with arms round shoulders | `anime` | `groups` `arm_around`, cherry garden, group waist-up framing (`fit: "people"`, `shot: "cowboy"`) |
