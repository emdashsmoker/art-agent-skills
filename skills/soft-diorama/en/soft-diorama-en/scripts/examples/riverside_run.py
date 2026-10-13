"""Anime solo action: a morning run along the river, seen side on, ponytail flying.

Run:  python riverside_run.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, finish, save_image, scenery, smoothstep
from paintkit.figure import ANIME, Figure, draw_figure, expression, face_style, fit, hairstyle, poses, wardrobe

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'riverside_run.png'
WIDTH, HEIGHT = 1600, 1000
SEED = 102
HORIZON = 640
LOOK = replace(ANIME, light=(-0.6, -0.8))


def paint_riverside(cv):
    scenery.sky(cv, top='#5c9ae0', bottom='#d6ecf7', horizon_y=HORIZON)
    for x, y, w in ((300, 180, 380), (1150, 140, 460), (760, 300, 260)):
        scenery.cumulus(cv, (x, y), w, w * 0.42, seed=SEED + x)
    scenery.hills(cv, HORIZON, 50, '#8fb8a0', scale=500, seed=SEED)
    river = cv.rect(0, HORIZON, WIDTH, HORIZON + 90)
    cv.fill(river, cv.ramp(cv.linear((0, HORIZON), (0, HORIZON + 90)), '#8cc0e0', '#5f9cc8'))
    bank = cv.rect(0, HORIZON + 90, WIDTH, HEIGHT)
    cv.fill(bank, cv.ramp(cv.linear((0, HORIZON + 90), (0, HEIGHT)), '#86b860', '#5c9446'))
    path = cv.rect(0, 880, WIDTH, 960)
    cv.fill(path, '#d8c8a8')
    cv.tint(smoothstep(cv.noise(scale=60, seed=SEED, stretch=(8.0, 1.0)), 0.5, 0.8) * path, '#b8a888', 'normal', 0.5)
    scenery.grass(cv, (HORIZON + 100, 880), count=220, seed=SEED)
    streaks = cv.ribbons([([(x, y), (x + 200, y)], 3.0, 'taper')
                          for x, y in ((120, 420), (180, 520), (90, 610), (240, 700))])
    cv.tint(blur(streaks, 1.5), '#ffffff', 'screen', 0.6)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_riverside(cv)
    pose = poses.run(turn=80, phase=0.1)
    figure = Figure(**fit((380, 140, 1000, 935), pose), pose=pose, look=LOOK, body_details=False,
                    hair=hairstyle('ponytail', color='#2a2026', tail_length=2.2, flow=0.7, seed=SEED),
                    face=expression(face_style('female', 'sharp', eye_color='#5a3a2a'), 'grin', 0.8))
    cv.tint(blur(cv.ellipse(figure.pelvis[0], 935, 140, 12), 8), '#4a5a3a', 'multiply', 0.4)
    draw_figure(cv, figure, [wardrobe.bottoms('#2a2e3a', length=0.55, loose=0.04),
                             wardrobe.top('#ff7a62', sleeve=1.2, hem=-0.6, scoop=0.35),
                             wardrobe.shoes('#f4f4f4')])
    save_image(OUTPUT, finish.finish_anime(cv, glow=0.25, seed=SEED))


if __name__ == '__main__':
    main()
