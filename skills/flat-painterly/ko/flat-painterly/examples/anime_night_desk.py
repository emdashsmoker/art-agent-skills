"""애니메풍 예제: 비 내리는 밤, 창가의 작업 책상(현대 사물화).

공정: 카메라 설정 → 벽과 창 밖 도시 → 책상 → 사물(먼 것부터) → 화면 내용 → 빛(전등, 화면) → 촬영.
사물은 props가 만든 3차원 입체이며 카메라 한 대로 투영하므로 모든 물건의 원근이 서로 맞는다.
화면, 자판, 라벨은 면 위의 0-1 좌표(camera.region)로 붙인다.
실행: python anime_night_desk.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, io, post, props  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1600, 900
CAMERA = s3.Camera(eye=(0.0, 50.0, -70.0), target=(0.0, 12.0, 35.0), focal=1150.0, center=(800.0, 470.0))
LAMP_LIGHT = (-0.7, 0.6, -0.2)   # 왼쪽 탁상 전등에서 오는 빛
WALL_Z, WINDOW = 62.0, (-60.0, 6.0, 60.0, 130.0)   # 창: x0, y0, x1, y1 (cm)

# 팔레트: 남보라 밤빛이 지배색. 전등의 주황과 화면의 하늘색이 두 광원이며 도시의 분홍 네온이 강조색이다.
SKY = [(0.0, "#0a0e2a"), (0.55, "#2a2456"), (0.85, "#6a3a72"), (1.0, "#b0507a")]
CITY = ["#1c1a3e", "#15142e", "#0e0d22"]
CITY_LIGHTS = ["#ffd38a", "#7fd8ff", "#ff7ab0", "#fff2d0"]
WALL, WALL_DARK = "#1e2346", "#141834"
FRAME = "#0f1228"
DESK, DESK_EDGE = "#6a4c44", "#4a3236"
INK = "#0b0d1c"
LAMP_GLOW, SCREEN_GLOW = "#ffb866", "#5ab8ff"
CODE = ["#ff7aa8", "#7fd4ff", "#c3e88d", "#ffcb6b", "#a6acd0"]


def wall_point(x, y):
    return (x, y, WALL_Z)


def paint_wall_and_window(cv, rng):
    wall = CAMERA.path([wall_point(-200, -10), wall_point(200, -10), wall_point(200, 200), wall_point(-200, 200)])
    cv.fill(cv.shape(wall), Linear([WALL, WALL_DARK], (0, 0), (0, 500)))
    x0, y0, x1, y1 = WINDOW
    window_path = CAMERA.path([wall_point(x0, y1), wall_point(x1, y1), wall_point(x1, y0), wall_point(x0, y0)])
    glass = cv.shape(window_path)
    top, bottom = window_path[:, 1].min(), window_path[:, 1].max()
    left, right = window_path[:, 0].min(), window_path[:, 0].max()
    cv.fill(glass, Linear(SKY, (0, top), (0, bottom)))

    # 도시: 먼 줄일수록 낮고 옅다. 창 아래쪽 가장자리가 지평선 근처에 오게 한다.
    for layer, (base_color, height_range, width_range) in enumerate(
            ((CITY[0], (60, 150), (30, 70)), (CITY[1], (40, 110), (40, 90)), (CITY[2], (20, 70), (50, 120)))):
        x = left - 20
        while x < right:
            width = rng.uniform(*width_range)
            tower_top = bottom - rng.uniform(*height_range)
            tower = cv.shape(g.rect(x, tower_top, width, bottom - tower_top + 2))
            cv.fill(tower, base_color, clip=glass)
            for wy in np.arange(tower_top + 8, bottom - 4, 9 + layer * 2):
                for wx in np.arange(x + 5, x + width - 5, 7 + layer * 2):
                    if rng.random() < 0.22:
                        lit = CITY_LIGHTS[int(rng.integers(len(CITY_LIGHTS)))]
                        cv.fill(cv.shape(g.rect(wx, wy, 3 + layer, 4 + layer)), lit, opacity=0.5 + 0.2 * layer,
                                clip=glass)
            if rng.random() < 0.25:
                sign = cv.shape(g.rect(x + width * 0.3, tower_top + 12, width * 0.4, 10 + layer * 4))
                cv.fill(sign, CITY_LIGHTS[2] if rng.random() < 0.6 else CITY_LIGHTS[1], clip=glass)
            x += width + rng.uniform(2, 12)
    # 초점이 맞지 않은 먼 불빛(보케)과 유리의 빗방울.
    for _ in range(40):
        bx, by = rng.uniform(left, right), rng.uniform(bottom - 220, bottom)
        bokeh = cv.shape(g.ellipse(bx, by, rng.uniform(6, 18)), soft=4)
        cv.fill(bokeh, CITY_LIGHTS[int(rng.integers(len(CITY_LIGHTS)))], opacity=0.35, blend=Blend.SCREEN,
                clip=glass)
    for _ in range(160):
        rx, ry = rng.uniform(left, right), rng.uniform(top, bottom)
        length = rng.uniform(8, 26)
        cv.stroke([(rx, ry), (rx - length * 0.18, ry + length)], "#c9d6ff", width=1.1, opacity=0.25, clip=glass)
        if rng.random() < 0.3:
            cv.fill(cv.shape(g.ellipse(rx, ry + length, 2.2, 2.6)), "#dfe8ff", opacity=0.45, clip=glass)

    # 창틀: 가운데 세로 창살과 아래 문틀. 벽보다 어두워 창 밖을 액자처럼 두른다.
    for mullion in ((-1.5, 1.5), ):
        bar = CAMERA.path([wall_point(mullion[0], y1), wall_point(mullion[1], y1), wall_point(mullion[1], y0),
                           wall_point(mullion[0], y0)])
        cv.fill(cv.shape(bar), FRAME)
    sill = CAMERA.path([wall_point(x0 - 4, y0 + 1), wall_point(x1 + 4, y0 + 1), wall_point(x1 + 4, y0 - 3),
                        wall_point(x0 - 4, y0 - 3)])
    cv.fill(cv.shape(sill), FRAME)
    cv.stroke(window_path, FRAME, width=10, closed=True)

    # 창 오른쪽 벽의 메모지.
    for index, (nx, ny, tone) in enumerate(((70, 40, "#ffd36e"), (78, 30, "#8ef0c6"), (72, 22, "#ff9ec4"))):
        note = CAMERA.path([wall_point(nx, ny + 6), wall_point(nx + 6, ny + 6.4), wall_point(nx + 6, ny),
                            wall_point(nx, ny - 0.3)])
        cv.fill(cv.shape(note), tone, opacity=0.75)
    return glass


def paint_desk(cv):
    desk = s3.box((0.0, -2.5, 25.0), (150.0, 5.0, 66.0))
    s3.draw(cv, CAMERA, desk, {"top": DESK, "front": DESK_EDGE, "*": DESK_EDGE}, LAMP_LIGHT, ambient=0.5)


def paint_headphones(cv):
    cups = [s3.cylinder(center, 4.6, 3.0) for center in ((-41.0, 0.0, -1.0), (-25.0, 0.0, -4.0))]
    band = np.array([(-33.0 + 8.2 * np.cos(t), 2.6, -2.5 + 9.0 * np.sin(t)) for t in np.linspace(0.15, np.pi - 0.15, 24)])
    path = CAMERA.path(band)
    width = 1.6 * CAMERA.scale_at(band.mean(axis=0))
    cv.stroke(path, INK, width=width + 2.6)
    cv.stroke(path, "#3a3f66", width=width)
    for cup in cups:
        s3.draw(cv, CAMERA, cup, {"side": "#2e3358", "top": "#151830"}, LAMP_LIGHT, line=INK, width=1.3)
        rim = CAMERA.path(s3.circle((cup.face("top").center[0], 3.0, cup.face("top").center[2]), 3.2))
        cv.stroke(rim, "#ff7ab0", width=1.6, closed=True, opacity=0.8)


def paint_plant(cv, rng):
    pot = s3.cylinder((60.0, 5.2, 46.0), 5.0, 9.0, top_radius=6.2)
    s3.draw(cv, CAMERA, pot, {"side": "#e7d8c6", "top": "#3a2a24"}, LAMP_LIGHT, line=INK, width=1.3)
    base = np.array([60.0, 14.2, 46.0])
    for angle in np.linspace(0, 2 * np.pi, 9, endpoint=False) + rng.uniform(0, 0.5):
        lean = rng.uniform(0.25, 0.5)
        height = rng.uniform(16, 27)
        tip = base + (np.cos(angle) * height * lean, height, np.sin(angle) * height * lean)
        middle = base + (np.cos(angle) * height * lean * 0.4 + rng.normal(0, 0.8), height * 0.55,
                         np.sin(angle) * height * lean * 0.4)
        spine = g.spline(CAMERA.path([base + (np.cos(angle) * 1.5, 0, np.sin(angle) * 1.5), middle, tip]),
                         closed=False)
        unit = CAMERA.scale_at(middle)
        leaf = cv.shape(*g.ribbon(spine, (1.6 * unit, 2.6 * unit, 1.8 * unit, 0.0)))
        cv.fill(leaf, "#2f6a52")
        cv.fill(cv.edge_light(leaf, (-0.8, -0.6), width=3), "#7ac8a0", opacity=0.8)
        cv.fill(cv.contour(leaf, 1.2), INK)


def paint_monitor_screen(cv, screen, rng):
    cv.fill(cv.shape(CAMERA.region(screen, 0.02, 0.035, 0.98, 0.965)), "#151a2c")
    cv.fill(cv.shape(CAMERA.region(screen, 0.02, 0.035, 0.2, 0.965)), "#1c2238")
    cv.fill(cv.shape(CAMERA.region(screen, 0.02, 0.035, 0.98, 0.09)), "#22294a")
    for row in range(16):
        v = 0.15 + row * 0.048
        cv.fill(cv.shape(CAMERA.region(screen, 0.04, v, 0.04 + rng.uniform(0.06, 0.12), v + 0.02)), "#4a5280")
        indent = 0.24 + (row % 4 in (1, 2)) * 0.03 + (row % 4 == 2) * 0.03
        u = indent
        for _ in range(int(rng.integers(1, 4))):
            length = rng.uniform(0.05, 0.18)
            if u + length > 0.95:
                break
            cv.fill(cv.shape(CAMERA.region(screen, u, v, u + length, v + 0.02)), CODE[int(rng.integers(len(CODE)))])
            u += length + 0.015
    cv.fill(cv.shape(CAMERA.region(screen, 0.24, 0.15 + 9 * 0.048, 0.243, 0.17 + 9 * 0.048)), "#ffffff")


def paint_laptop_screen(cv, screen):
    cv.fill(cv.shape(CAMERA.region(screen, 0.03, 0.04, 0.97, 0.96)), "#1a1830")
    art = cv.shape(CAMERA.region(screen, 0.08, 0.12, 0.42, 0.7))
    corners = CAMERA.region(screen, 0.08, 0.12, 0.42, 0.7)
    cv.fill(art, Linear(["#ff7ab0", "#7a5aff", "#3ad8ff"], corners[0], corners[2]))
    cv.fill(cv.shape(CAMERA.region(screen, 0.5, 0.2, 0.88, 0.26)), "#e8e6ff")
    cv.fill(cv.shape(CAMERA.region(screen, 0.5, 0.32, 0.76, 0.36)), "#8a86b8")
    for index in range(22):
        height = 0.05 + 0.16 * abs(np.sin(index * 1.7))
        u = 0.5 + index * 0.017
        cv.fill(cv.shape(CAMERA.region(screen, u, 0.62 - height, u + 0.01, 0.62)), "#7fd4ff")
    cv.fill(cv.shape(CAMERA.region(screen, 0.08, 0.8, 0.92, 0.815)), "#3a3866")
    cv.fill(cv.shape(CAMERA.region(screen, 0.08, 0.8, 0.46, 0.815)), "#ff7ab0")


def paint_phone_screen(cv, screen):
    corners = CAMERA.region(screen, 0.06, 0.03, 0.94, 0.97)
    cv.fill(cv.shape(corners), Linear(["#3a2a7a", "#ff7ab0"], corners[0], corners[2]))
    for v in (0.55, 0.68):
        cv.fill(cv.shape(CAMERA.region(screen, 0.12, v, 0.88, v + 0.1)), "#ffffff", opacity=0.75)


def paint_objects(cv, rng):
    lamp = props.desk_lamp((-62.0, 0.0, 44.0), yaw=-32.0, reach=27.0, height=40.0)
    books = [props.book((60.0, 0.0, 46.0), yaw=8.0, size=(17.0, 2.8, 24.0)),
             props.book((60.5, 2.8, 46.0), yaw=-4.0, size=(15.0, 2.4, 22.0))]
    monitor = props.monitor((8.0, 0.0, 40.0), yaw=-4.0)
    laptop = props.laptop((-46.0, 0.0, 20.0), yaw=30.0, size=(30.0, 21.0))
    keyboard = props.keyboard((6.0, 0.0, 9.0), yaw=-3.0)
    mug = props.mug((38.0, 0.0, 8.0), radius=4.0, height=9.0)
    phone = props.phone((45.0, 0.0, -2.0), yaw=-22.0)

    lamp.draw(cv, CAMERA, {"base": "#2a2f52", "shade": {"side": "#e2a14a", "top": "#e2a14a", "bottom": "#fff0c0"},
                           "arm": "#2a2f52"}, LAMP_LIGHT, line=INK, width=1.3)
    for book, cover in zip(books, ("#5a3a7a", "#2f6a8a")):
        book.draw(cv, CAMERA, {"body": {"top": cover, "left": cover, "*": "#e6dcc6"}}, LAMP_LIGHT, line=INK,
                  width=1.2)
    paint_plant(cv, rng)
    monitor.draw(cv, CAMERA, {"foot": "#3a3f62", "neck": "#2f3456", "panel": {"front": "#0a0c16", "*": "#3a3f62"}},
                 LAMP_LIGHT, line=INK, width=1.4)
    paint_monitor_screen(cv, monitor.faces["screen"], rng)
    laptop.draw(cv, CAMERA, {"base": {"front": "#8a8eb0", "*": "#6a6e92"}, "lid": {"front": "#0a0c16", "*": "#8a8eb0"}},
                LAMP_LIGHT, line=INK, width=1.3)
    paint_laptop_screen(cv, laptop.faces["screen"])
    props.keycaps(cv, CAMERA, laptop.faces["deck"], "#2a2c48", rows=6, columns=13, area=props.LAPTOP_KEY_AREA)
    cv.fill(cv.shape(CAMERA.region(laptop.faces["deck"], *props.LAPTOP_TOUCHPAD)), "#9a9ec0", opacity=0.6)
    paint_headphones(cv)
    keyboard.draw(cv, CAMERA, {"body": "#2a2e50"}, LAMP_LIGHT, line=INK, width=1.3)
    props.keycaps(cv, CAMERA, keyboard.faces["keys"], "#3e4370", light_edge="#7fd4ff")
    mug.draw(cv, CAMERA, {"body": {"side": "#f2ece4", "top": "#5a3424"}, "handle": "#f2ece4"}, LAMP_LIGHT, line=INK,
             width=1.3)
    phone.draw(cv, CAMERA, {"body": {"front": "#0a0c16", "*": "#5a5e86"}}, LAMP_LIGHT, line=INK, width=1.2)
    paint_phone_screen(cv, phone.faces["screen"])
    return lamp, monitor, mug


def paint_light(cv, lamp, monitor, mug, rng):
    """두 광원의 빛. 전등은 책상에 따뜻한 원을, 화면은 자판과 손 앞쪽에 차가운 빛을 떨어뜨린다."""
    bulb = np.asarray(lamp.points["bulb"])
    pool_center = bulb + (14.0, -bulb[1], -6.0)
    pool = CAMERA.path(s3.circle(tuple(pool_center), 26.0))
    cv.fill(cv.shape(pool, soft=40), LAMP_GLOW, opacity=0.45, blend=Blend.SCREEN)
    cone = np.vstack([CAMERA.path([bulb]), pool[np.argsort(pool[:, 0])[[0, -1]]]])
    cv.fill(cv.shape(cone, soft=24), LAMP_GLOW, opacity=0.12, blend=Blend.SCREEN)
    cv.fill(cv.shape(g.ellipse(*CAMERA.project(bulb), 26, 18), soft=14), "#fff2c8", opacity=0.9,
            blend=Blend.SCREEN)

    screen = monitor.faces["screen"]
    spill = CAMERA.path(s3.circle((screen.center[0], 0.2, 14.0), 38.0))
    cv.fill(cv.shape(spill, soft=60), SCREEN_GLOW, opacity=0.3, blend=Blend.SCREEN)
    cv.fill(cv.shape(CAMERA.region(screen, -0.04, -0.06, 1.04, 1.06), soft=30), SCREEN_GLOW, opacity=0.2,
            blend=Blend.SCREEN)

    # 컵에서 오르는 김.
    top = mug.solids["body"].face("top").center
    for offset in (-1.4, 0.0, 1.4):
        points = [(top[0] + offset + 1.2 * np.sin(t * 2.4 + offset), top[1] + 1.0 + t * 9.0, top[2])
                  for t in np.linspace(0.0, 1.0, 12)]
        cv.stroke(g.spline(CAMERA.path(points), closed=False), "#ffffff", width=5, taper=(0.2, 1, 0),
                  opacity=0.26, soft=2.5)


def main(out_dir="out", scale=1.0, seed=43):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    cv.fill(cv.full(), WALL_DARK)
    paint_wall_and_window(cv, rng)
    paint_desk(cv)
    lamp, monitor, mug = paint_objects(cv, rng)
    paint_light(cv, lamp, monitor, mug, rng)
    io.save(cv.guide_image(), out_dir / "desk_1_guide.png")
    image = anime.finish(cv, diffusion=0.2, bloom=0.4, shadows="#1a1a4a", highlights="#ffe0c0", grade_amount=0.1)
    return io.save(post.vignette(image, strength=0.22), out_dir / "anime_night_desk.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
