"""Night street with a full-body clothed figure: one-point perspective city, lamp light, wet road.

Shows how the figure rig and the city camera share one scale: the figure's
height in pixels comes from Perspective.scale(depth).

Run:  python city_night_walk.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, finish, save_image, scenery, shading
from paintkit.figure import ANIME, FaceSpec, Figure, HairSpec, HandSpec, Physique, Pose, add_rim_light, draw_figure
from paintkit.figure import wardrobe

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'city_night_walk.png'
WIDTH, HEIGHT = 1024, 1536
SEED = 8
VIEW = city.Perspective(vanishing=(600, 760), focal=1000, eye=1.6)
FIGURE_DEPTH = 1.75            # meters from the camera
FIGURE_HEIGHT_M = 1.70
PELVIS_HEIGHT_M = 0.90
LAMP = '#ffcf8a'
LIGHT = (0.7, -0.7)            # key light: the lamp up on the right


def paint_city(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, VIEW.vanishing[1])), '#0d1230', '#2a2a5a', '#6a4a7a', '#c98a8a'))
    stars = cv.noise(scale=3, octaves=1, seed=SEED)
    cv.tint((stars > 0.93) * (1.0 - cv.linear((0, 100), (0, 600))), '#ffffff', 'screen', 0.8)
    city.skyline(cv, VIEW.vanishing[1] + 6, height=(60, 260), width=(34, 90), color='#3a3566', lit_ratio=0.22,
                 window_px=4, seed=SEED)
    masks = city.street(cv, VIEW, lit_ratio=0.5, shade_side=None, walls=('#3d4466', '#4a4460', '#35405f', '#50486a'),
                        glass='#141a30', shops=('#a8405a', '#2f7a86', '#c98a3a'), asphalt='#23263a',
                        paving='#3a3c52', haze='#5a4a78', seed=SEED)
    lamps = [(-5.6, 9), (5.6, 14), (-5.6, 24), (5.6, 32), (-5.6, 48), (5.6, 62)]
    for x, z in lamps:
        city.street_lamp(cv, VIEW, x, z, glow=LAMP)
    # Wet asphalt: every lamp and shop window smears into a vertical streak on the road.
    rng = np.random.default_rng(SEED)
    streaks = []
    for x, z in lamps[1:] + [(rng.uniform(-9, 9), rng.uniform(14, 70)) for _ in range(16)]:
        foot = VIEW.project(np.clip(x, -4.5, 4.5), 0.0, z)
        length = VIEW.scale(z) * rng.uniform(4, 8)
        streaks.append(([foot, (foot[0] + rng.normal(0, 3), foot[1] + length)], VIEW.scale(z) * 0.5, 'taper'))
    cv.tint(blur(cv.ribbons(streaks), 3.0) * masks['road'], LAMP, 'screen', 0.5)
    scenery.sun_glow(cv, VIEW.vanishing, 420, '#ff9f9a', 0.30)
    cv.color = blur(cv.color, 2.6)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_city(cv)
    scale = VIEW.scale(FIGURE_DEPTH)
    pelvis = VIEW.project(-0.42, PELVIS_HEIGHT_M, FIGURE_DEPTH)
    look = replace(ANIME, light=LIGHT)
    pose = Pose(lean=2, hip_tilt=-5, shoulder_tilt=4, head_yaw=18, head_tilt=-5,
                left_arm=(-10, 8), right_arm=(9, 16), right_hand=HandSpec('relaxed', 'back'),
                left_leg=(6, -2), right_leg=(-3, 1), front_leg='left')
    figure = Figure(
        pelvis=pelvis, height=FIGURE_HEIGHT_M * scale, pose=pose, physique=Physique(bust=1.05, hips=1.04),
        face=FaceSpec(skin='#f6d3bd', eye_color='#7a4a5a', eye_half_height=0.102, lip_color='#d0525e',
                      lip_fullness=0.8, smile=0.45, brow_color='#2a2230'),
        hair=HairSpec(color='#2a2238', bangs='side', part=-22, length=1.25, side_length=1.0, wave=0.2, seed=SEED),
        look=look, nude_details=False,
    )
    garments = [wardrobe.skirt('#2d3350', length=3.0, flare=0.32), wardrobe.top('#d9c8a8', sleeve=4.9, hem=-1.7)]
    masks = draw_figure(cv, figure, garments)
    add_rim_light(cv, masks['all'], look, color=LAMP, width=9, opacity=0.9)
    cv.tint(shading.rim(masks['all'], (-1.0, 0.2), 10, soft=4), '#7f8cff', 'screen', 0.35)
    cv.tint(masks['all'] * cv.linear((0, 1050), (0, HEIGHT)), '#1a1f45', 'multiply', 0.35)
    image = finish.finish_anime(cv, glow=0.30, diffusion=0.12, shadows='#3a3f8a', highlights='#ffd9b0', seed=SEED)
    save_image(OUTPUT, finish.vignette(image, 0.22))


if __name__ == '__main__':
    main()
