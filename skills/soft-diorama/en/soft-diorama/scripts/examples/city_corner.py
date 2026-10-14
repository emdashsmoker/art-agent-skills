"""Street corner at dusk in two-point perspective: a city block seen across the crossing,
its two facades running away to vanishing points at the left and right edges.

The camera stands in the crossing and looks diagonally at the corner (yaw 45) and a
little up (negative pitch), so the towers lean in. Buildings are boxes; their faces are
flat facades painted by city.facade() and pasted on.

Run:  python city_corner.py [output.png] [dusk|night]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, adjust, blur, city, finish, save_image, scenery, solids

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'city_corner.png'
NIGHT = (sys.argv[2] if len(sys.argv) > 2 else 'dusk') == 'night'
WIDTH, HEIGHT = 1400, 1000
SEED = 31
VIEW = city.Camera(center=(700, 560), focal=720, position=(-10.0, 1.6, -10.0), yaw=45, pitch=-7)
LIT_RATIO = 0.55 if NIGHT else 0.22
SKY = ('#141a3a', '#3a2f5a', '#7a4a6a') if NIGHT else ('#2f3f7a', '#c76a7a', '#f6b26b')
PAVEMENT = 3.0                       # meters between the kerb and the buildings
ROAD = 10.0                          # width of each road
# The block on the far side of the crossing: (x0, x1, z0, z1, height, wall, shop).
BLOCK = [
    (0, 14, 0, 14, 52, '#b9aa98', '#2f5a5a'),        # corner tower
    (14, 24, 0, 14, 24, '#9a8f86', '#7a3b3b'),       # along the right-hand street
    (24, 40, 0, 14, 33, '#8a8f9a', '#5a4a7a'),
    (40, 58, 0, 14, 20, '#a39a8c', '#7a3b3b'),
    (58, 90, 0, 14, 28, '#8f8478', '#2f5a5a'),
    (0, 14, 14, 26, 28, '#a39a8c', '#5a4a7a'),       # along the left-hand street
    (0, 14, 26, 42, 38, '#7f8794', '#7a3b3b'),
    (0, 14, 42, 60, 22, '#9a8f86', '#2f5a5a'),
    (0, 14, 60, 92, 30, '#8a8f9a', '#5a4a7a'),
]


def paint_sky(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, VIEW.horizon_y() + 60)), *SKY))
    if NIGHT:
        rng = np.random.default_rng(SEED)
        stars = cv.empty()
        for _ in range(140):
            stars = np.maximum(stars, cv.ellipse(rng.uniform(0, WIDTH), rng.uniform(0, 420), rng.uniform(0.6, 1.6)))
        cv.tint(stars, '#ffffff', 'screen', 0.8)
    else:
        scenery.sun_glow(cv, (1120, VIEW.horizon_y() - 40), 420, '#ffd9a0', 0.7)
        scenery.clouds(cv, (60, 380), color='#ffc9b0', coverage=0.40, scale=320, opacity=0.55, seed=SEED)


def paint_ground(cv):
    asphalt = '#2f323c' if NIGHT else '#4a4a55'
    paving = '#5a5866' if NIGHT else '#8a8480'
    far = 400.0
    cv.fill(cv.polygon(city.project_polygon(VIEW, [(-far, 0, -far), (far, 0, -far), (far, 0, far), (-far, 0, far)])),
            asphalt)
    kerb = PAVEMENT
    walks = [(-kerb, -kerb, far, far),                                         # around the block
             (-far, -kerb - ROAD - far, -kerb - ROAD, -kerb - ROAD),           # the corner behind the camera
             (-far, 0.0, -kerb - ROAD, far), (0.0, -far, far, -kerb - ROAD)]   # the blocks to either side
    cv.fill(city.ground_rects(cv, VIEW, walks, y=0.02), paving)
    edges = [(-kerb - 0.25, -kerb, -kerb, far), (-kerb, -kerb - 0.25, far, -kerb),
             (-kerb - ROAD, 0.0, -kerb - ROAD + 0.25, far), (0.0, -kerb - ROAD, far, -kerb - ROAD + 0.25)]
    cv.fill(city.ground_rects(cv, VIEW, edges, y=0.03), '#c9c2b6' if not NIGHT else '#8a8698')
    middle = -kerb - ROAD / 2
    dashes = [(middle - 0.08, z, middle + 0.08, z + 3.0) for z in np.arange(2.0, 300, 7.0)]
    dashes += [(x, middle - 0.08, x + 3.0, middle + 0.08) for x in np.arange(2.0, 300, 7.0)]
    # Crosswalks just past the crossing, one over each road; stripes run along the walking direction.
    zebra = [(x, -kerb + 0.4, x + 0.5, -kerb + 3.4) for x in np.arange(-kerb - ROAD + 0.6, -kerb - 0.4, 1.0)]
    zebra += [(-kerb + 0.4, z, -kerb + 3.4, z + 0.5) for z in np.arange(-kerb - ROAD + 0.6, -kerb - 0.4, 1.0)]
    cv.fill(city.ground_rects(cv, VIEW, dashes + zebra, y=0.01), '#e9e2c8', 0.85)
    wet = cv.linear((0, VIEW.horizon_y()), (0, HEIGHT))
    cv.tint(wet * cv.noise(scale=60, octaves=2, seed=SEED, stretch=(1, 5)), SKY[-1], 'screen', 0.18)


def paint_block(cv):
    """Far buildings first; each shows its street faces and, where it rises above a nearer neighbor, its side."""
    camera = np.array(VIEW.position)
    order = sorted(BLOCK, key=lambda b: -np.hypot((b[0] + b[1]) / 2 - camera[0], (b[2] + b[3]) / 2 - camera[2]))
    rng = np.random.default_rng(SEED)
    lit = ('#ffd98a', '#fff1c4', '#ffb86a')
    for x0, x1, z0, z1, height, wall, shop in order:
        faces = solids.box(cv, VIEW, (x0, 0.0, z0), (x1 - x0, height, z1 - z0), wall, edge=0)
        for name, tone, strength in (('front', '#ffc48a', 0.18), ('left', '#4a5288', 0.45)):
            quad = faces[name]
            if quad is None:
                continue
            width = (x1 - x0) if name == 'front' else (z1 - z0)
            middle = np.mean([(x0, 0, z0), (x1, height, z1)], axis=0)
            detail = int(np.clip(VIEW.scale_at(*middle) * 0.6, 14, 40))
            tone_of_wall = adjust(wall, lightness=-0.30, chroma=0.8) if NIGHT else wall   # walls go dark, windows glow
            texture = city.facade(width, height, tone_of_wall, '#1f2740' if NIGHT else '#27324a', lit=lit, lit_ratio=LIT_RATIO, shop=shop,
                                  resolution=detail, seed=int(rng.integers(1 << 30)))
            cover = cv.paste(texture, quad)
            mode = 'screen' if name == 'front' and not NIGHT else 'multiply'
            cv.tint(cover * cv.linear((0, HEIGHT * 0.2), (0, HEIGHT)), tone, mode, strength)
            distance = np.clip((np.hypot(*(middle[[0, 2]] - camera[[0, 2]])) - 25) / 80, 0, 1)
            cv.tint(cover, SKY[-1], 'normal', 0.45 * distance)                      # air between us and far walls
        if faces['front'] is not None and faces['left'] is not None:                # the corner edge catches light
            (ax, ay), (bx, by) = faces['front'][0], faces['front'][3]
            cv.tint(cv.ribbon([(ax, ay), (bx, by)], 2.0, 'flat', smooth=False), '#ffe6c0', 'screen', 0.5)


def paint_lamps(cv):
    for x, z in ((-2.4, 4.0), (-2.4, 22.0), (-2.4, 44.0), (6.0, -2.4), (26.0, -2.4), (50.0, -2.4)):
        foot, top = VIEW.project(x, 0.0, z), VIEW.project(x, 5.5, z)
        scale = VIEW.scale_at(x, 5.5, z)
        cv.fill(cv.ribbon([foot, top], max(0.14 * scale, 1.2), 'flat', smooth=False), '#24262e')
        head = cv.ellipse(top[0], top[1], max(0.22 * scale, 1.5), max(0.30 * scale, 2.0))
        cv.fill(head, '#fff2d0')
        cv.tint(cv.radial(top, 3.4 * scale) ** 2.0, '#ffd9a0', 'screen', 0.75 if NIGHT else 0.45)
        pool = city.ground_rects(cv, VIEW, [(x - 2.5, z - 2.5, x + 2.5, z + 2.5)])
        cv.tint(blur(pool, max(0.8 * scale, 2.0)), '#ffd9a0', 'screen', 0.22 if NIGHT else 0.10)
        # Wet asphalt: each light leaves a long vertical streak below its foot.
        length = (foot[1] - top[1]) * 1.6
        streak = cv.ribbon([(foot[0], foot[1] + 4), (foot[0], foot[1] + length)], max(0.35 * scale, 2.0), 'in')
        cv.tint(blur(streak, max(0.25 * scale, 1.5)), '#ffd9a0', 'screen', 0.35 if NIGHT else 0.2)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_sky(cv)
    paint_ground(cv)
    paint_block(cv)
    paint_lamps(cv)
    if not NIGHT:
        cv.tint(cv.radial((1120, VIEW.horizon_y() - 40), 900) ** 2, '#ffb070', 'screen', 0.25)
    image = finish.finish_anime(cv, glow=0.30 if NIGHT else 0.22, diffusion=0.06, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
