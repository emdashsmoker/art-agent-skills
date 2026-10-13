"""회화풍(수채화) 예제: 현대 기기 습작 여섯 가지(펜과 담채 제품 스케치).

공정: 칸마다 카메라 배치 → 배경 번짐 → 입체 칠과 펜 선 → 화면, 렌즈, 스피커 같은 면 위 세부 → 그림자 → 수채화 패스.
칸마다 카메라를 따로 두면 물건마다 가장 잘 읽히는 각도를 고를 수 있다.
실행: python watercolor_gadget_studies.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, io, props  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402

WIDTH, HEIGHT = 1500, 1000
LIGHT = (-0.55, 0.75, -0.45)
INK = "#2e2a30"
SHADOW = "#7a74a8"
WASHES = ["#dfe9ee", "#f1e3d3", "#e6e0ee", "#e2ecdf", "#f3e6dc", "#e3e3ee"]
CELLS = [(260, 270), (750, 270), (1240, 270), (260, 740), (750, 740), (1240, 740)]


def camera_for(cell, eye, target=(0.0, 0.0, 0.0), focal=1300.0):
    return s3.Camera(eye=eye, target=target, focal=focal, center=cell)


def ground_shadow(cv, camera, center, radius_x, radius_z):
    points = [(center[0] + radius_x * np.cos(a) + radius_x * 0.25, 0.0, center[2] + radius_z * np.sin(a) + radius_z * 0.2)
              for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
    cv.fill(cv.shape(camera.path(points), soft=8), SHADOW, opacity=0.45, blend=Blend.MULTIPLY)


def smartphone(cv, cell):
    camera = camera_for(cell, eye=(-14.0, 14.0, -40.0), target=(0.0, 7.0, 0.0), focal=800.0)
    ground_shadow(cv, camera, (0, 0, 2), 6.0, 2.5)
    phone = s3.slab((0.0, 8.0, 0.0), (7.4, 15.6, 0.85), 1.0).rotated(yaw=-24.0, pitch=8.0, about=(0.0, 0.5, 0.0))
    s3.draw(cv, camera, phone, {"front": "#1c1e26", "*": "#8a8e98"}, LIGHT, line=INK, width=1.4)
    screen = phone.face("front")
    corners = camera.region(screen, 0.06, 0.03, 0.94, 0.97)
    cv.fill(cv.shape(corners), Linear(["#2f5ab8", "#7ad0f0", "#f0b8d8"], corners[0], corners[2]))
    for row in range(4):
        for column in range(4):
            u, v = 0.14 + column * 0.19, 0.12 + row * 0.12
            cv.fill(cv.shape(camera.face_ellipse(screen, u + 0.06, v + 0.03, 0.06, 0.028)), "#ffffff", opacity=0.75)
    cv.fill(cv.shape(camera.region(screen, 0.36, 0.035, 0.64, 0.06)), "#111318")


def laptop(cv, cell):
    camera = camera_for(cell, eye=(30.0, 32.0, -42.0), target=(0.0, 7.0, 2.0), focal=600.0)
    ground_shadow(cv, camera, (0, 0, 0), 17.0, 12.0)
    device = props.laptop((0.0, 0.0, 0.0), yaw=-10.0, size=(30.0, 21.0), open_angle=112.0)
    device.draw(cv, camera, {"base": {"front": "#c9ccd4", "*": "#a6aab4"}, "lid": {"front": "#16181e", "*": "#c9ccd4"}},
                LIGHT, line=INK, width=1.4)
    screen = device.faces["screen"]
    corners = camera.region(screen, 0.04, 0.05, 0.96, 0.95)
    cv.fill(cv.shape(corners), Linear(["#f2c46a", "#e86a5a", "#5a3a8a"], corners[0], corners[3]))
    cv.fill(cv.shape(camera.region(screen, 0.04, 0.72, 0.96, 0.95)), "#2a2440", opacity=0.85)
    props.keycaps(cv, camera, device.faces["deck"], "#6a6e7a", rows=6, columns=13, area=props.LAPTOP_KEY_AREA)
    cv.fill(cv.shape(camera.region(device.faces["deck"], *props.LAPTOP_TOUCHPAD)), "#b9bcc6")
    cv.stroke(camera.region(device.faces["deck"], *props.LAPTOP_TOUCHPAD), INK, width=1.0, closed=True, opacity=0.6)


def compact_camera(cv, cell):
    camera = camera_for(cell, eye=(-16.0, 12.0, -30.0), target=(0.5, 3.5, -1.0), focal=950.0)
    ground_shadow(cv, camera, (0, 0, 1), 7.0, 3.0)
    body = s3.slab((0.0, 3.6, 0.0), (11.0, 6.6, 3.6), 0.8)
    lens_ring = s3.cylinder((0.0, 0.0, 0.0), 2.2, 1.6).rotated(pitch=-90.0).moved((0.6, 3.4, -1.8))
    lens_barrel = s3.cylinder((0.0, 0.0, 0.0), 1.7, 1.2).rotated(pitch=-90.0).moved((0.6, 3.4, -3.4))
    button = s3.cylinder((3.4, 6.9, 0.0), 0.6, 0.45)
    flash = s3.box((-3.6, 5.4, -1.85), (1.8, 0.7, 0.2))
    turn = dict(yaw=-28.0, about=(0.0, 0.0, 0.0))
    s3.draw(cv, camera, body.rotated(**turn), {"front": "#24252c", "*": "#b9bcc4"}, LIGHT, line=INK, width=1.4)
    s3.draw(cv, camera, flash.rotated(**turn), "#eef0f4", LIGHT, line=INK, width=1.0)
    s3.draw(cv, camera, button.rotated(**turn), {"side": "#9a9ea8", "top": "#c9ccd4"}, LIGHT, line=INK, width=1.0)
    s3.draw(cv, camera, lens_ring.rotated(**turn), {"side": "#9a9ea8", "top": "#3a3c44"}, LIGHT, line=INK, width=1.2)
    barrel = lens_barrel.rotated(**turn)
    s3.draw(cv, camera, barrel, {"side": "#6a6e78", "top": "#1a1c24"}, LIGHT, line=INK, width=1.2)
    glass = barrel.face("top")
    cv.fill(cv.shape(camera.face_ellipse(glass, 0.5, 0.5, 0.32)), "#2a4a7a")
    cv.fill(cv.shape(camera.face_ellipse(glass, 0.38, 0.36, 0.1)), "#e8f2ff", opacity=0.9)
    cv.stroke(camera.face_ellipse(glass, 0.5, 0.5, 0.42), "#c9ccd4", width=1.2, closed=True, opacity=0.8)


def headphones(cv, cell):
    camera = camera_for(cell, eye=(-12.0, 16.0, -46.0), target=(0.0, 9.0, 0.0), focal=640.0)
    ground_shadow(cv, camera, (0, 0, 0), 11.0, 4.0)
    cups = []
    for side in (-1.0, 1.0):
        # 원기둥 축을 좌우(x)로 눕혀 귀 덮개가 서로 마주 보게 한다.
        cup = s3.cylinder((0.0, 0.0, 0.0), 4.4, 3.2).rotated(yaw=-90.0 * side, pitch=90.0).moved((7.5 * side, 4.6, 0.0))
        cups.append(cup.rotated(yaw=-22.0))
    band = np.array([(8.6 * np.cos(t), 4.6 + 13.0 * np.sin(t), 0.0) for t in np.linspace(0.0, np.pi, 40)])
    band = (s3._rotation(-22.0, 0.0) @ band.T).T
    path = camera.path(band)
    width = 1.8 * camera.scale_at(band.mean(axis=0))
    far, near = sorted(cups, key=lambda cup: -camera.depth(cup.center))
    s3.draw(cv, camera, far, {"side": "#6f8f74", "top": "#3a4a3e", "bottom": "#8fae92"}, LIGHT, line=INK, width=1.3)
    cv.stroke(path, INK, width=width + 2.8)
    cv.stroke(path, "#8fae92", width=width)
    cv.stroke(path, "#c9dcc8", width=width * 0.3, opacity=0.8)
    s3.draw(cv, camera, near, {"side": "#6f8f74", "top": "#3a4a3e", "bottom": "#8fae92"}, LIGHT, line=INK, width=1.3)


def speaker(cv, cell):
    camera = camera_for(cell, eye=(18.0, 30.0, -42.0), target=(0.0, 8.5, 0.0), focal=680.0)
    ground_shadow(cv, camera, (0, 0, 0), 8.0, 6.0)
    cabinet = s3.box((0.0, 9.0, 0.0), (12.0, 18.0, 12.0)).rotated(yaw=25.0)
    s3.draw(cv, camera, cabinet, {"front": "#4a4e5c", "*": "#b8865a"}, LIGHT, line=INK, width=1.4)
    front = cabinet.face("front")
    for v, radius, tone in ((0.3, 0.18, "#2a2c36"), (0.68, 0.32, "#2a2c36")):
        cv.fill(cv.shape(camera.face_ellipse(front, 0.5, v, radius, radius * 12 / 18)), tone)
        cv.stroke(camera.face_ellipse(front, 0.5, v, radius, radius * 12 / 18), "#9a9ea8", width=1.6, closed=True)
        cv.fill(cv.shape(camera.face_ellipse(front, 0.5, v, radius * 0.3, radius * 0.3 * 12 / 18)), "#6a6e7a")
    top = cabinet.face("top")
    for index in range(5):
        u = 0.15 + index * 0.17
        cv.stroke(camera.path([top.point(u, 0.1), top.point(u, 0.9)]), "#8a5a3a", width=0.8, opacity=0.5)


def tablet(cv, cell):
    camera = camera_for(cell, eye=(0.0, 34.0, -30.0), target=(1.5, 0.0, 0.0), focal=560.0)
    device = props.phone((0.0, 0.0, 2.0), yaw=14.0, size=(17.0, 24.0), thickness=0.7)
    ground_shadow(cv, camera, (0, 0, 2), 10.0, 12.0)
    device.draw(cv, camera, {"body": {"front": "#1a1c22", "*": "#e3b8a8"}}, LIGHT, line=INK, width=1.4)
    screen = device.faces["screen"]
    corners = camera.region(screen, 0.04, 0.03, 0.96, 0.97)
    cv.fill(cv.shape(corners), "#fbf6ec")
    spine = g.spline(camera.path([screen.point(u, 0.5 + 0.25 * np.sin(u * 7.0)) for u in np.linspace(0.12, 0.88, 9)]),
                     closed=False)
    cv.stroke(spine, "#e86a5a", width=3.0, taper=(0.3, 1, 0.6))
    cv.fill(cv.shape(camera.face_ellipse(screen, 0.3, 0.3, 0.12, 0.085)), "#7ac0e8", opacity=0.8)
    stylus = s3.cylinder((0.0, 0.0, 0.0), 0.45, 16.0, segments=24).rotated(yaw=58.0, pitch=90.0).moved((4.0, 0.45, -12.0))
    s3.draw(cv, camera, stylus, {"*": "#f4f2ee"}, LIGHT, line=INK, width=1.1)


def main(out_dir="out", scale=1.0, seed=47):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    for (x, y), tone in zip(CELLS, WASHES):
        watercolor.wash(cv, g.blob(x, y, 200, 0.25, 9, rng), tone, 0.85, soft=30, rough=18)
    for draw, cell in zip((smartphone, laptop, compact_camera, headphones, speaker, tablet), CELLS):
        draw(cv, cell)
    io.save(cv.guide_image(), out_dir / "gadgets_1_underpainting_guide.png")
    return io.save(watercolor.render(cv, wobble=1.0, bleed=0.4, edge=0.45), out_dir / "watercolor_gadget_studies.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
