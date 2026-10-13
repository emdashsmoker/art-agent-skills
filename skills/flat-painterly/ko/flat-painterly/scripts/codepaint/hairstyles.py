"""머리 모양 템플릿과 긴 머리의 드레이프(몸통을 따라 흐르는 다발).

머리 모양(head3d.HairStyle)은 머리카락 선(hairline), 덮개 두께, 다발(Lock) 목록이다.
어깨 위에서 끝나는 다발은 head3d가 머리 좌표만으로 그린다. 어깨 아래로 내려오는 다발에는 drape(front 또는 back)를 주며
lock_layers가 다발 중심선을 몸 좌표로 옮긴 뒤 몸통 단면 안에 든 구간을 그쪽 겉면 밖으로 밀어낸다.
그래서 긴 머리가 어깨를 타고 가슴 앞이나 등 뒤로 흐르며 어느 각도에서도 몸통을 뚫지 않는다.
밀어낸 다발은 몸통 가운데보다 관찰자 쪽이면 몸 다음에(front), 아니면 몸보다 먼저(back) 칠한다.
"""
from dataclasses import dataclass

import numpy as np

from . import geometry
from .figure3d import FRONT_ROUNDNESS
from .head3d import HEAD_SCALE, HairStyle, Lock

DRAPE_CLEARANCE = 0.08     # 다발 중심선과 몸통 겉면 사이 여유(머리 높이). 옷의 부풂과 다발 두께를 덮는다
DRAPE_SAMPLES = 40         # 긴 다발 중심선의 점 수. 어깨에서 꺾이는 곡선이 매끄럽게 나올 만큼
DRAPE_EASE = 12            # 밀어내기를 이 점 수만큼 앞서 조금씩 시작한다. 어깨 위에서 다발이 꺾이지 않고 휘어 넘어간다
DRAPE_PROBE = 0.66         # 앞뒤 층을 정할 때 보는 중심선 위치(뿌리 0, 끝 1)
TUCK_FROM_V, TUCK_TO_V = 0.5, 1.4   # 다발이 얼굴 뒤를 지나는지 볼 높이 구간(두개골 반지름 단위, 광대에서 턱 끝)

BLUNT = (1.0, 1.0, 0.9, 0.6, 0.12)
# 긴 다발은 뿌리를 좁게 시작한다. 뿌리부터 넓으면 다발 윗변의 모서리가 정수리 양옆에 뿔처럼 솟는다.
BLUNT_LONG = (0.35, 1.0, 1.0, 0.95, 0.85, 0.55)   # 어깨 아래까지 오는 일자 단발의 끝
LONG_TAPER = (0.35, 1.0, 1.0, 0.95, 0.85, 0.45)   # 긴 생머리: 끝까지 폭을 유지하다 일자로 끊긴다


# ---------- 드레이프 ----------

def head_to_body(model):
    """머리 좌표 점을 몸 좌표로 옮기는 (원점, 행렬). 몸 좌표 점을 몸으로 투영하면 머리로 투영한 자리와 같다.

    머리 화면 좌표 = 머리 원점 + R(머리 기울기) * (머리 시선 행렬 @ q)[:2] / HEAD_SCALE(몸 단위)이므로
    몸 좌표 p = 두개골 중심 + 몸 시선 행렬^T @ Rz(머리 기울기 - 몸 기울기) @ 머리 시선 행렬 @ q / HEAD_SCALE.
    """
    body, head = model.body, model.head
    roll = np.eye(3)
    roll[:2, :2] = geometry.transform(np.eye(2), rotate=head.frame.rotate - body.frame.rotate).T
    return body.head_center(), body.view.T @ roll @ head.view / HEAD_SCALE


def _surface_z(body, point, side):
    """점이 여유만큼 부풀린 몸통 단면 안이면 밀어낼 겉면의 z, 밖이면 None."""
    x, y, z = point
    section = body.torso_section(y)
    if section is None:
        return None
    center_x, center_z, width, front, back = section
    ratio = abs(x - center_x) / (width + DRAPE_CLEARANCE)
    if ratio >= 1.0:
        return None
    front_z = center_z - (front + DRAPE_CLEARANCE) * (1.0 - ratio ** FRONT_ROUNDNESS) ** (1.0 / FRONT_ROUNDNESS)
    back_z = center_z + (back + DRAPE_CLEARANCE) * np.sqrt(1.0 - ratio * ratio)
    if not front_z < z < back_z:
        return None
    if side not in ("front", "back"):
        side = "front" if z < center_z else "back"
    return front_z if side == "front" else back_z


def drape(body, points, side):
    """몸 좌표 중심선을 위에서부터 따라가며 몸통에 든 점을 side 쪽 겉면 밖으로 민다.

    한 번 밀린 다발은 그 자리에서 곧게 늘어지므로 아래 점도 같은 만큼 민다(가슴 아래 허리로 다시 붙지 않는다).
    """
    shift, required = 0.0, []
    for point in points:
        moved = np.array(point, np.float64) + (0.0, 0.0, shift)
        target = _surface_z(body, moved, side)
        if target is not None:
            shift += target - moved[2]
        required.append(shift)
    eased = []
    for index, value in enumerate(required):
        for ahead in range(1, DRAPE_EASE + 1):
            if index + ahead < len(required):
                # 앞쪽 점의 밀림을 코사인 곡선으로 줄여 미리 받는다. 직선 비율보다 꺾이는 자리가 부드럽다.
                early = required[index + ahead] * 0.5 * (1.0 + np.cos(np.pi * ahead / (DRAPE_EASE + 1.0)))
                value = min(value, early) if side == "front" else max(value, early)
        eased.append(value)
    return [np.array(point, np.float64) + (0.0, 0.0, value) for point, value in zip(points, eased)]


def _tucked(head, samples):
    """다발의 얼굴 높이 구간이 머리 가운데보다 관찰자에게서 먼지. 멀면 얼굴 뒤로 지나가는 다발이다."""
    depths = [head.depth(point) for point, _ in samples if TUCK_FROM_V <= point[1] <= TUCK_TO_V]
    return bool(depths) and float(np.mean(depths)) > 0.0


def draped_lock(model, lock):
    """긴 다발 1개의 (화면 윤곽, 층, 머리 기준 깊이, 얼굴 뒤로 지나가는지). head3d.Head3D.lock에 마지막 값을 더한 형식."""
    body, head, style = model.body, model.head, model.look.hair
    center, matrix = head_to_body(model)
    samples = head.lock_samples(style, lock, DRAPE_SAMPLES)
    points = [center + matrix @ point for point, _ in samples]
    draped = drape(body, points, lock.drape)
    centerline = body.project_path(np.array(draped))
    widths = [width * lock.width * head.frame.unit for width in lock.taper]
    path = geometry.ribbon(geometry.densify(centerline, 12), widths)[0]
    probe = draped[int(round((len(draped) - 1) * DRAPE_PROBE))]
    section = body.torso_section(probe[1])
    reference = center if section is None else np.array([section[0], probe[1], section[1]])
    layer = "front" if body.depth_of(probe) < body.depth_of(reference) else "back"
    return path, layer, (body.depth_of(probe) - body.depth_of(center)) * HEAD_SCALE, _tucked(head, samples)


def lock_layers(model):
    """모든 다발을 층별로 나눠 먼 것부터 정렬한 {'back': [...], 'tucked': [...], 'front': [...]}.

    back은 몸보다 먼저, tucked와 front는 얼굴과 덮개 다음에 칠한다. tucked는 몸 앞으로 흐르지만 얼굴 높이에서는
    얼굴 뒤를 지나는 긴 다발(3/4 각도의 먼 쪽 옆머리)이라 얼굴 자리를 빼고 칠한다. drape 없는 다발은 head3d가 그린다.
    """
    head, style = model.head, model.look.hair
    layers = {"back": [], "tucked": [], "front": []}
    for lock in style.locks:
        if lock.drape:
            path, layer, depth, tucked = draped_lock(model, lock)
            layer = "tucked" if layer == "front" and tucked else layer
        else:
            path, layer, depth = head.lock(style, lock)
        layers[layer].append((depth, path))
    return {name: [path for _, path in sorted(items, key=lambda item: -item[0])] for name, items in layers.items()}


# ---------- 여성 ----------

BOB_HAIRLINE = ((0, -0.45), (60, -0.2), (85, 0.1), (120, 0.5), (180, 0.8))
# 옆 가르마 앞머리. 눈썹 높이에서 끝난다.
SIDE_BANGS = tuple(Lock((tip * 0.3 - 18, -0.92), (tip, v), 0.3, lift=0.1, bulge=0.04)
                   for tip, v in ((-58, 0.12), (-40, 0.18), (-22, 0.1), (-4, 0.15), (14, 0.06), (32, 0.1), (50, 0.02)))

# 옆 가르마 앞머리와 턱선에서 끝나는 단발. 앞쪽 옆머리가 가장 길고 뒤로 갈수록 짧다.
BOB = HairStyle(
    thickness=0.12, hairline=BOB_HAIRLINE,
    locks=tuple(
        list(SIDE_BANGS)
        + [Lock((phi * 0.85, -0.6), (phi, 1.34 - 0.0035 * (abs(phi) - 66)), 0.5, lift=0.09, bulge=0.06, taper=BLUNT)
           for phi in (-150, -128, -106, -86, -66, 66, 86, 106, 128, 150)]
        + [Lock((phi, -0.75), (phi, 1.0), 0.55, lift=0.09, bulge=0.07, taper=BLUNT) for phi in (165, 180, -165)]))
# 등 가운데까지 오는 긴 생머리. 얼굴 옆 다발은 어깨를 타고 가슴 앞으로, 나머지는 등 뒤로 흐른다.
LONG_STRAIGHT = HairStyle(
    thickness=0.12, hairline=BOB_HAIRLINE,
    locks=tuple(
        list(SIDE_BANGS)
        # 앞 다발은 관자놀이에서 시작해 귀 쪽(phi +22)으로 비켜 내려온다. 같은 phi로 곧게 늘어뜨리면
        # 볼 겉면 위에 얹혀 3/4 각도에서 가까운 쪽 눈을 덮는다.
        + [Lock((phi * 0.8, -0.65), (phi + np.sign(phi) * 22, 4.4), 0.55, lift=0.1, bulge=0.05, taper=LONG_TAPER,
                drape="front", spread=spread)
           for phi, spread in ((-90, 0.13), (-78, 0.08), (-66, 0.03), (66, 0.03), (78, 0.08), (90, 0.13))]
        + [Lock((phi, -0.8), (phi, 5.0), 0.6, lift=0.1, bulge=0.08, taper=LONG_TAPER, drape="back",
                spread=0.06 * abs(np.sin(np.deg2rad(phi)))) for phi in (-162, -144, -126, -108, 108, 126, 144, 162, 180)]),
    hang_from=0.45)
# 어깨에 닿는 중단발. 앞쪽 옆머리는 어깨 앞, 뒤쪽은 어깨 뒤로 얹힌다.
SHOULDER = HairStyle(
    thickness=0.12, hairline=BOB_HAIRLINE,
    locks=tuple(
        list(SIDE_BANGS)
        + [Lock((phi * 0.85, -0.6), (phi + np.sign(phi) * 20, 2.55), 0.5, lift=0.1, bulge=0.06, taper=BLUNT_LONG,
                drape="front") for phi in (-84, -68, 68, 84)]
        + [Lock((phi, -0.75), (phi, 2.5), 0.58, lift=0.1, bulge=0.07, taper=BLUNT_LONG, drape="back")
           for phi in (-162, -140, -118, -100, 100, 118, 140, 162, 180)]),
    hang_from=0.4)
# 뒤로 넘겨 묶은 머리. 이마가 드러나고 얼굴 옆으로 가는 다발 2개, 뒤통수에서 등으로 늘어진 꼬리.
PONYTAIL = HairStyle(
    thickness=0.1, hairline=((0, -0.55), (40, -0.48), (70, -0.15), (85, 0.15), (120, 0.4), (180, 0.55)),
    locks=(Lock((-60, -0.55), (-70, 0.95), 0.18, lift=0.08, bulge=0.03),
           Lock((60, -0.55), (70, 0.95), 0.18, lift=0.08, bulge=0.03),
           Lock((180, -0.2), (180, 0.05), 0.32, lift=0.26, taper=(0.9, 1.0, 1.0, 1.0, 0.9)),
           Lock((180, -0.1), (180, 3.7), 0.56, lift=0.3, bulge=0.22, taper=(0.6, 1.0, 1.0, 0.7, 0.15),
                drape="back")),
    hang_from=0.0)


# ---------- 남성 ----------

SHORT_HAIRLINE = ((0, -0.52), (35, -0.48), (62, -0.2), (74, 0.42), (82, 0.42), (88, 0.1), (112, 0.1), (130, 0.5),
                  (180, 0.78))
NAPE = tuple(Lock((phi, 0.25), (phi, 0.84), 0.3, lift=0.03) for phi in (158, 180, -158))
# 귀가 드러나는 짧은 머리. 이마로 흘러내린 앞머리, 귀 앞 구레나룻, 목덜미의 짧은 끝.
SHORT = HairStyle(
    thickness=0.15, hairline=SHORT_HAIRLINE,
    locks=tuple(
        [Lock((phi * 0.6, -0.95), (phi + 8, -0.3 + 0.002 * abs(phi)), 0.3, lift=0.15, bulge=0.05)
         for phi in (-44, -22, 0, 22, 44)]
        + list(NAPE)),
    hang_from=0.9)
# 옆 가르마: 화면 왼쪽 위의 가르마에서 앞머리를 오른쪽으로 쓸어 넘긴다.
SIDE_PART = HairStyle(
    thickness=0.16, hairline=((0, -0.6), (35, -0.55), (62, -0.22), (74, 0.42), (82, 0.42), (88, 0.1), (112, 0.1),
                              (130, 0.5), (180, 0.78)),
    locks=tuple(
        [Lock((-34, -0.98), (tip, v), 0.34, lift=0.2, bulge=0.07) for tip, v in ((-6, -0.5), (16, -0.46), (38, -0.4),
                                                                                   (60, -0.26))]
        + [Lock((-46, -0.9), (-62, -0.3), 0.26, lift=0.12, bulge=0.04)]
        + list(NAPE)),
    hang_from=0.9)
# 아주 짧게 친 머리. 다발 없이 얇은 덮개만 있다.
CROPPED = HairStyle(
    thickness=0.06, hairline=((0, -0.62), (35, -0.58), (62, -0.3), (74, 0.3), (82, 0.3), (88, 0.05), (112, 0.05),
                              (130, 0.4), (180, 0.62)),
    locks=(), hang_from=0.9)
# 목을 덮는 남성 긴 머리. 가운데 가르마 앞머리가 양 볼로 흘러내리고 뒷머리가 목덜미를 덮는다.
MALE_LONG = HairStyle(
    thickness=0.14, hairline=((0, -0.5), (35, -0.46), (62, -0.18), (85, 0.15), (120, 0.55), (180, 0.9)),
    locks=tuple(
        [Lock((sign * 6, -0.98), (sign * 46, 0.35), 0.3, lift=0.14, bulge=0.06) for sign in (-1, 1)]
        + [Lock((sign * 24, -0.9), (sign * 66, 1.1), 0.3, lift=0.12, bulge=0.05) for sign in (-1, 1)]
        + [Lock((phi * 0.85, -0.6), (phi, 1.75), 0.45, lift=0.1, bulge=0.06, taper=BLUNT_LONG) for phi in (-86, 86)]
        + [Lock((phi, -0.7), (phi, 2.15), 0.58, lift=0.1, bulge=0.07, taper=BLUNT_LONG, drape="back")
           for phi in (-160, -138, -116, 116, 138, 160, 180)]),
    hang_from=0.35)

FEMALE_HAIRS = {"bob": BOB, "long_straight": LONG_STRAIGHT, "shoulder": SHOULDER, "ponytail": PONYTAIL}
MALE_HAIRS = {"short": SHORT, "side_part": SIDE_PART, "cropped": CROPPED, "male_long": MALE_LONG}


# ---------- 머리색 ----------

@dataclass(frozen=True)
class HairColor:
    """머리색 1개: 밑색, 그림자, 정수리 빛 띠, 윤곽선. 눈썹은 윤곽선 색을 따른다.

    애니풍 머리는 그림자를 밑색보다 어둡고 조금 차가운 쪽으로, 빛 띠는 밝고 채도를 낮춘 쪽으로 잡는다.
    """
    base: str
    shade: str
    light: str
    line: str


HAIR_COLORS = {
    # 자연색
    "black": HairColor("#23252f", "#111219", "#56607a", "#08080c"),        # 푸른 기가 도는 애니풍 검정
    "dark_brown": HairColor("#3c2b25", "#221713", "#7c5c4a", "#140b09"),
    "chestnut": HairColor("#7a4630", "#4c281c", "#ba7a52", "#28120c"),
    "blonde": HairColor("#e6c47a", "#b48a4c", "#fff0c4", "#5e4220"),
    "silver": HairColor("#c6cad8", "#8a90a8", "#f4f6fc", "#464a5e"),
    # 애니 원색
    "pink": HairColor("#efa2ba", "#bd6a8a", "#ffdbe6", "#682840"),
    "sky_blue": HairColor("#8ec2ea", "#5888bc", "#daf0ff", "#223e68"),
    "navy": HairColor("#2f3f7a", "#1a244e", "#6c82c4", "#0b0f28"),
    "red": HairColor("#c63a3c", "#88202c", "#f08672", "#460c14"),
    "purple": HairColor("#8a6ac0", "#58408a", "#cab2ee", "#281848"),
    "mint": HairColor("#7ccab4", "#4a988a", "#cbf2e6", "#1c4840"),
    "orange": HairColor("#f0984a", "#be662c", "#ffd29c", "#58280c"),
}
