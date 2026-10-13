"""The drawing process in four panels: line art, flat colors, shading, finished picture.

Shows how one scene function serves every stage: only the look and the finish change.

Run:  python process_sheet.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import ANIME, BodySpec, Character, FaceSpec, HairSpec, Head, Outfit, add_rim_light, draw_character

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'process_sheet.png'
WIDTH, HEIGHT = 640, 800
SEED = 4


def paint_scene(look, with_background):
    cv = Canvas(WIDTH, HEIGHT, '#ffffff')
    if with_background:
        scenery.sky(cv, top='#6f7fc0', bottom='#f6b79a')
        scenery.cloud_bank(cv, (260, 700), count=5, size=(200, 460), color='#ffd9c0', shade='#b98aa8',
                           light=look.light, seed=SEED)
        scenery.sun_glow(cv, (560, 160), 380, '#ffe0b0', 0.45)
        cv.color = blur(cv.color, 1.5)
    character = Character(
        head=Head(center=(330, 320), size=320, yaw=16, tilt=5),
        face=FaceSpec(eye_color='#9a5a3a', smile=0.6, lip_fullness=0.6),
        hair=HairSpec(color='#5a3a4a', bangs='wispy', part=-16, length=2.6, side_length=1.4, wave=0.5, seed=SEED),
        body=BodySpec(turn=8, lean=-3),
        outfit=Outfit(kind='offshoulder', color='#f3efe6', trim='#d98a8a'),
        look=look,
    )
    masks = draw_character(cv, character)
    if with_background:
        add_rim_light(cv, masks['all'], look, color='#ffe2b0', width=5, opacity=0.8)
    return cv


def main():
    look = replace(ANIME, light=(0.6, -1.0))
    flat_look = replace(look, shade_depth=0.0, highlight=0.0)
    lines = finish.line_art(paint_scene(look, False))
    flats = paint_scene(flat_look, False).flatten()
    shaded = paint_scene(look, False).flatten()
    final = finish.finish_anime(paint_scene(look, True), seed=SEED)
    save_image(OUTPUT, finish.contact_sheet([lines, flats, shaded, final], columns=4))


if __name__ == '__main__':
    main()
