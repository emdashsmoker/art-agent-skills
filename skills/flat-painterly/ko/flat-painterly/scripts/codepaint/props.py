"""현대 사물 부품: 노트북, 모니터, 키보드, 전화기, 컵, 책, 탁상 전등.

각 함수는 Prop을 돌려준다. 단위는 cm, position은 물건 바닥 중심(책상 면 위)의 장면 좌표다.
yaw는 위에서 볼 때 시계 방향 회전이며 0이면 물건의 정면이 카메라 쪽(-z)을 향한다.
"""
from dataclasses import dataclass, field

import numpy as np

from . import solids as s3


@dataclass
class Prop:
    """사물 1개.

    solids: 부위 이름별 입체. faces: 화면, 자판처럼 내용을 붙일 면.
    lines: 손잡이, 전선, 전등 팔처럼 굵기가 있는 선 {이름: (3차원 점열, 굵기 cm)}.
    points: 전구 위치처럼 장면에서 참조할 점.
    """
    solids: dict
    faces: dict = field(default_factory=dict)
    lines: dict = field(default_factory=dict)
    points: dict = field(default_factory=dict)

    def draw(self, canvas, camera, paints, light=(-0.5, 0.8, -0.4), line=None, width=2.0):
        """부위를 먼 것부터 칠한다. paints는 {부위 이름: 색 또는 면 이름별 색 사전}.

        선 부위는 paints에 색이 있을 때만 그리며 굵기는 깊이에 맞춰 화면 길이로 바뀐다.
        """
        items = [(camera.depth(solid.center), "solid", name) for name, solid in self.solids.items()]
        items += [(camera.depth(np.mean(points, axis=0)), "line", name)
                  for name, (points, _) in self.lines.items() if name in paints]
        shapes = {}
        for _, kind, name in sorted(items, key=lambda item: -item[0]):
            if kind == "solid":
                if name in paints:
                    shapes[name] = s3.draw(canvas, camera, self.solids[name], paints[name], light, line, width)
                continue
            points, thickness = self.lines[name]
            path = camera.path(points)
            scale = camera.scale_at(np.mean(points, axis=0))
            if line is not None:
                canvas.stroke(path, line, width=thickness * scale + 2.0 * width)
            canvas.stroke(path, paints[name], width=thickness * scale)
        return shapes


def _place(solid, position, yaw):
    return solid.rotated(yaw=yaw).moved(position)


def _place_point(point, position, yaw):
    return s3._rotation(yaw, 0.0) @ np.asarray(point, np.float64) + np.asarray(position, np.float64)


def _lying_slab(center, width, depth, thickness, radius):
    """책상에 눕힌 둥근 판. 윗면이 face('front')이며 u는 왼쪽에서 오른쪽, v는 뒤에서 앞으로 간다."""
    return s3.slab(center, (width, depth, thickness), radius).rotated(pitch=90.0, about=center)


def laptop(position, yaw=0.0, size=(31.0, 21.5), open_angle=108.0, base_thickness=1.4, lid_thickness=0.6):
    """열린 노트북. faces: screen(화면), deck(자판이 있는 윗면)."""
    width, depth = size
    base = _lying_slab((0.0, base_thickness / 2.0, 0.0), width, depth, base_thickness, 1.2)
    hinge = (0.0, base_thickness, depth / 2.0)
    lid = s3.slab((0.0, base_thickness + depth / 2.0, depth / 2.0 + lid_thickness / 2.0),
                  (width, depth, lid_thickness), 1.0).rotated(pitch=open_angle - 90.0, about=hinge)
    base, lid = _place(base, position, yaw), _place(lid, position, yaw)
    return Prop({"base": base, "lid": lid}, {"screen": lid.face("front"), "deck": base.face("front")})


LAPTOP_KEY_AREA = (0.08, 0.08, 0.92, 0.58)
LAPTOP_TOUCHPAD = (0.34, 0.66, 0.66, 0.93)


def monitor(position, yaw=0.0, size=(60.0, 34.0), stand_height=11.0, tilt=6.0):
    """받침대에 선 모니터. faces: screen. tilt 양수면 화면 윗부분이 뒤로 젖혀진다."""
    width, height = size
    middle = (0.0, stand_height + height / 2.0, 0.0)
    panel = s3.slab(middle, (width, height, 2.4), 1.0).rotated(pitch=tilt, about=middle)
    neck_height = stand_height + height * 0.35
    neck = s3.box((0.0, neck_height / 2.0, 3.2), (5.5, neck_height, 2.4))
    foot = _lying_slab((0.0, 0.6, 1.5), 22.0, 17.0, 1.2, 3.0)
    parts = {name: _place(solid, position, yaw) for name, solid in
             (("foot", foot), ("neck", neck), ("panel", panel))}
    return Prop(parts, {"screen": parts["panel"].face("front")})


def keyboard(position, yaw=0.0, size=(44.0, 13.5), height=2.0):
    """키보드 몸체. faces: keys(윗면). 자판은 keycaps()로 윗면에 그린다."""
    body = _place(s3.box((0.0, height / 2.0, 0.0), (size[0], height, size[1])), position, yaw)
    return Prop({"body": body}, {"keys": body.face("top")})


def keycaps(canvas, camera, face, color, rows=5, columns=15, gap=0.18, light_edge=None, area=(0.0, 0.0, 1.0, 1.0)):
    """면 위에 자판을 격자로 그린다. 맨 아래 줄 가운데는 긴 스페이스 바.

    area는 자판이 차지할 면 위의 영역 (u0, v0, u1, v1). 노트북은 앞쪽에 터치패드 자리를 남긴다.
    """
    area_u0, area_v0, area_u1, area_v1 = area
    cell_u, cell_v = (area_u1 - area_u0) / columns, (area_v1 - area_v0) / rows
    for row in range(rows):
        keys = [(area_u0 + column * cell_u, area_u0 + (column + 1) * cell_u) for column in range(columns)]
        if row == rows - 1:
            keys = keys[:4] + [(keys[4][0], keys[columns - 5][1])] + keys[columns - 4:]
        for u0, u1 in keys:
            v0, v1 = area_v0 + row * cell_v, area_v0 + (row + 1) * cell_v
            inset_u, inset_v = cell_u * gap, cell_v * gap
            cap = camera.region(face, u0 + inset_u, v0 + inset_v, u1 - inset_u, v1 - inset_v)
            canvas.fill(canvas.shape(cap), color)
            if light_edge is not None:
                canvas.stroke(cap[:2], light_edge, width=1.0, opacity=0.7)


def phone(position, yaw=0.0, size=(7.2, 15.0), thickness=0.8):
    """책상에 눕힌 전화기. faces: screen."""
    body = _place(_lying_slab((0.0, thickness / 2.0, 0.0), size[0], size[1], thickness, 0.9), position, yaw)
    return Prop({"body": body}, {"screen": body.face("front")})


def mug(position, radius=4.2, height=9.5, handle=True):
    """컵. top 면이 음료의 수면이다. lines: handle."""
    x, y, z = position
    body = s3.cylinder((x, y, z), radius, height, top_radius=radius * 1.06)
    lines = {}
    if handle:
        angles = np.linspace(-1.2, 1.2, 14)
        reach = radius * 0.62
        points = [(x + radius * 1.0 + reach * np.cos(angle), y + height * 0.52 + height * 0.3 * np.sin(angle), z)
                  for angle in angles]
        lines["handle"] = (np.array(points), radius * 0.26)
    return Prop({"body": body}, {"surface": body.face("top")}, lines)


def book(position, yaw=0.0, size=(15.0, 2.6, 22.0)):
    """눕힌 책. 칠할 때 {"top": 표지, "left": 책등, "*": 종이} 사전을 쓴다."""
    body = _place(s3.box((0.0, size[1] / 2.0, 0.0), size), position, yaw)
    return Prop({"body": body}, {"cover": body.face("top")})


def desk_lamp(position, yaw=0.0, reach=26.0, height=38.0, shade_radius=7.0):
    """탁상 전등. lines: arm. points: bulb(전구 위치, 빛의 출발점). 갓의 bottom 면이 빛나는 입구다."""
    base = s3.cylinder((0.0, 0.0, 0.0), 7.5, 2.2)
    elbow = (reach * 0.25, height * 0.62, 4.0)
    head = (reach, height, 0.0)
    shade = s3.cylinder((0.0, -shade_radius * 0.9, 0.0), shade_radius, shade_radius * 1.15,
                        top_radius=shade_radius * 0.32).rotated(pitch=-28.0).moved(head)
    parts = {"base": _place(base, position, yaw), "shade": _place(shade, position, yaw)}
    # 팔은 전등갓의 좁은 꼭대기에 붙는다. 갓 중심까지 이으면 팔이 갓 앞을 가로지른다.
    cap = np.asarray(head) + s3._rotation(0.0, -28.0) @ np.array([0.0, shade_radius * 0.25, 0.0])
    joints = [_place_point(point, position, yaw) for point in ((0.0, 2.0, 0.0), elbow, cap)]
    lines = {"arm": (np.array(joints), 1.0)}
    bulb = _place_point((head[0], head[1] - shade_radius * 0.8, head[2] - shade_radius * 0.3), position, yaw)
    return Prop(parts, {}, lines, {"bulb": bulb})
