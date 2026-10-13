"""Seen from behind: a woman at a riverside railing, looking across at the city at dusk.

Pose.turn near 180 shows her back, her long hair falls over it (painted in front of the body),
and a slight turn lets one shoulder catch the low sun. Her arms hang free beside her: seen from
behind, forearms that reach forward disappear behind the body.

Run:  python figure_back_view.py [output.png] [anime|illustration]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, city, finish, save_image, scenery
from paintkit.figure import (ANIME, ILLUSTRATION, Figure, HairSpec, HandSpec, Pose, add_rim_light, aim, draw_figure,
                             framing, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'figure_back_view.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'anime'
WIDTH, HEIGHT = 1100, 1400
WATER_Y = 760
RAIL_Y = 980
SEED = 61
SUN = (330, WATER_Y - 40)
LIGHT = (-0.75, -0.55)              # the sun is low, ahead of her and to the left


def paint_scene(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, WATER_Y)), '#27336e', '#6a5a9a', '#e58a6a', '#ffd08a'))
    scenery.sun_glow(cv, SUN, 560, '#ffe0a0', 0.85)
    cv.fill(cv.ellipse(SUN[0], SUN[1] - 6, 40), '#fff2cc')
    scenery.cloud_bank(cv, (180, 420), count=4, size=(260, 520), color='#ffc8a8', shade='#8a6a9f', light=LIGHT,
                       edge=1.5, seed=SEED)
    city.skyline(cv, WATER_Y, height=(60, 200), width=(40, 110), color='#a88aa8', lit_ratio=0.0, seed=SEED)
    city.skyline(cv, WATER_Y, height=(90, 320), width=(50, 130), color='#6a5f8f', lit='#ffd08a', lit_ratio=0.2,
                 window_px=4, seed=SEED + 1)
    city.skyline(cv, WATER_Y, height=(60, 240), width=(60, 150), color='#3a3a62', lit='#ffe0a0', lit_ratio=0.3,
                 window_px=5, seed=SEED + 2)
    scenery.water_reflection(cv, WATER_Y, darken=0.18, ripple=9.0, tint='#2a2f5f', seed=SEED)
    cv.color = blur(cv.color, 2.2)                                     # the far bank sits behind her, out of focus
    for x in range(-20, WIDTH + 40, 140):                             # railing posts and the top bar
        cv.fill(cv.rect(x, RAIL_Y, x + 16, HEIGHT, radius=4), '#2a2a3a')
    cv.paint_volume(cv.rect(-20, RAIL_Y - 18, WIDTH + 20, RAIL_Y + 8, radius=8), '#3a3a4a', LIGHT, bulge=8)
    cv.fill(cv.rect(-20, RAIL_Y + 120, WIDTH + 20, RAIL_Y + 132, radius=4), '#2a2a3a')


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_scene(cv)
    base = ANIME if STYLE == 'anime' else ILLUSTRATION
    look = replace(base, light=LIGHT, light_height=0.55)
    turn = 160                                                        # her back to us, turned a little to the sun
    # Arms hang a little out from the body. Forearms reaching forward (to the rail) would pass
    # behind her back from this side, and the arms would read as cut off at the elbow.
    pose = Pose(turn=turn, head_yaw=150, head_tilt=-4, hip_tilt=-4, shoulder_tilt=3,
                left_arm=aim(turn, (-0.12, 1.0, 0.05), (-0.02, 1.0, 0.25)),
                right_arm=aim(turn, (0.15, 1.0, 0.02), (0.08, 1.0, 0.15)),
                left_hand=HandSpec('relaxed', 'rest'), right_hand=HandSpec('relaxed', 'rest'))
    figure = Figure(**framing(cv.size, 'thigh', center=0.56), pose=pose, look=look, nude_details=False,
                    hair=HairSpec(color='#3b2a2a', bangs='side', part=20, length=3.4, wave=0.4, fullness=1.05,
                                  shine=0.8, seed=SEED))
    masks = draw_figure(cv, figure, [wardrobe.dress('#f2e8f0', length=3.4, flare=0.30), wardrobe.shoes('#5a3a3a')])
    add_rim_light(cv, masks['all'], look, color='#ffd9a8', width=7, opacity=0.75)
    cv.tint(cv.radial(SUN, 900) ** 2 * masks['all'], '#ffb070', 'soft_light', 0.35)
    if STYLE == 'anime':
        image = finish.finish_anime(cv, glow=0.28, seed=SEED)
    else:
        image = finish.finish_illustration(cv, glow=0.2, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
