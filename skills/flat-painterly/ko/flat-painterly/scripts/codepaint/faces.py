"""얼굴 템플릿: 얼굴형(턱 단면)과 이목구비(눈, 눈썹, 코, 입, 볼)의 좌표 묶음.

모든 좌표는 references/craft.md 얼굴 표와 같은 정면 기준 좌표다(두개골 반지름 1, 얼굴 가운데 x 0, 눈썹 근처 y 0.3).
character.paint_face가 이 좌표를 head3d.FaceFrame으로 얼굴 겉면에 붙여 각도만큼 찌그러뜨려 그린다.
눈 좌표(EyeShape)는 눈 중심이 원점이고 눈 반폭이 1인 하위 좌표계, 눈썹 좌표는 얼굴 반쪽 좌표계(오른쪽 눈 쪽)다.
템플릿을 바꾸면 같은 몸과 각도에서 얼굴 인상만 달라진다. 장면 코드는 character.restyle로 고른다.
"""
from dataclasses import dataclass

from .head3d import FEMALE_HEAD, MALE_HEAD, HeadSpec


@dataclass(frozen=True)
class EyeShape:
    """눈 1개. white와 lid는 닫힌 윤곽(꺾이는 점 인덱스는 *_corners), lower와 crease는 열린 선.

    iris는 (cx, cy, rx, ry), pupil은 (rx, ry), gleam은 (빛 쪽 x 거리, y, 반지름), iris_span은 홍채 그라데이션의 (위 y, 아래 y).
    line_style은 (굵기, taper, 짙기).
    """
    white: tuple
    white_corners: tuple
    iris: tuple
    pupil: tuple
    gleam: tuple
    lid: tuple
    lid_corners: tuple
    lower: tuple
    lower_style: tuple
    iris_span: tuple
    sclera: str
    pupil_color: str
    crease: tuple = ()
    crease_style: tuple = (1.3, (0.2, 1, 0.2), 0.6)


@dataclass(frozen=True)
class BrowShape:
    """눈썹. fill이면 닫힌 덩어리(corners로 꺾음), 아니면 굵기 width의 붓선."""
    points: tuple
    fill: bool = False
    corners: tuple = ()
    width: float = 2.8
    taper: tuple = (0.7, 1, 0.1)


@dataclass(frozen=True)
class MouthShape:
    """입. lips면 아랫입술(lower)과 윗입술 그늘(upper)을 칠한 뒤 입술선(line), 아니면 입술선 뒤 아랫입술 그늘(shade).

    philtrum은 인중 선. 비우면 긋지 않는다.
    """
    lips: bool
    line: tuple
    line_width: float
    line_taper: tuple
    lower: tuple = ()
    upper: tuple = ()
    shade: tuple = ()
    philtrum: tuple = ()


@dataclass(frozen=True)
class FaceSpec:
    """얼굴 템플릿 1개. head는 얼굴형(턱 단면, 코 높이, 귀), 나머지는 이목구비.

    eye_center와 eye_unit은 오른쪽 눈 중심과 눈 반폭(얼굴 표 좌표). 왼쪽 눈은 좌우 반전.
    nose_bridge는 콧대 선의 (x, y, 얼굴면에서 뜬 높이) 점열, nose_tip_y는 코끝 그늘의 높이.
    blush는 ((좌우 부호, 짙기), ...)로 비우면 볼 터치가 없다. chin_shade는 턱 끝 그늘 윤곽, stubble은 수염 자국.
    """
    head: HeadSpec
    eye: EyeShape
    eye_center: tuple
    eye_unit: float
    brow: BrowShape
    nose_bridge: tuple
    nose_tip_y: float
    mouth: MouthShape
    blush: tuple = ()
    blush_at: tuple = (0.55, 0.74)
    blush_radii: tuple = (0.2, 0.08)
    chin_shade: tuple = ()
    stubble: float = 0.0     # 입 둘레와 턱의 수염 자국 점묘 짙기. 0이면 없음


# ---------- 기본 얼굴(성숙한 성인 여성, 성인 남성) ----------

# 가로로 긴 아몬드 꼴, 반쯤 내린 윗눈꺼풀, 날개처럼 뻗은 눈꼬리.
ALMOND_EYE = EyeShape(
    white=((-1.0, 0.05), (-0.55, -0.32), (0.1, -0.42), (0.7, -0.3), (1.08, -0.08), (0.7, 0.26), (0.0, 0.36),
           (-0.6, 0.26)),
    white_corners=(0, 4), iris=(-0.02, 0.02, 0.44, 0.5), pupil=(0.18, 0.22), gleam=(0.16, -0.14, 0.11),
    lid=((-1.12, 0.06), (-0.72, -0.36), (0.0, -0.5), (0.72, -0.4), (1.2, -0.12), (1.5, -0.24), (1.12, 0.02),
         (0.7, -0.2), (0.0, -0.24), (-0.66, -0.12)),
    lid_corners=(0, 5), lower=((-0.7, 0.24), (0.0, 0.38), (0.72, 0.26), (1.04, 0.0)),
    lower_style=(1.5, (0.1, 1, 1, 0.3), 1.0), iris_span=(-0.45, 0.5), sclera="#fbf4f2", pupil_color="#100808")
# 높이가 폭의 3분의 1인 가는 꼴, 날개 없는 윗눈꺼풀, 쌍꺼풀 선.
NARROW_EYE = EyeShape(
    white=((-1.0, 0.02), (-0.5, -0.28), (0.2, -0.34), (0.8, -0.22), (1.1, -0.04), (0.7, 0.2), (0.0, 0.26),
           (-0.6, 0.18)),
    white_corners=(0, 4), iris=(0.0, 0.0, 0.4, 0.44), pupil=(0.16, 0.2), gleam=(0.14, -0.12, 0.08),
    lid=((-1.1, 0.04), (-0.7, -0.32), (0.0, -0.44), (0.8, -0.32), (1.16, -0.06), (0.8, -0.2), (0.0, -0.26),
         (-0.66, -0.14)),
    lid_corners=(0, 4), lower=((-0.6, 0.18), (0.0, 0.28), (0.7, 0.2)), lower_style=(1.3, (0.1, 1, 0.2), 0.7),
    iris_span=(-0.4, 0.4), sclera="#f8f2ee", pupil_color="#080606",
    crease=((-0.6, -0.62), (0.1, -0.74), (0.86, -0.6)))

FEMALE_MATURE = FaceSpec(
    head=FEMALE_HEAD, eye=ALMOND_EYE, eye_center=(0.45, 0.4), eye_unit=0.24,
    brow=BrowShape(points=((0.18, -0.02), (0.46, -0.12), (0.8, -0.04))),
    nose_bridge=((0.1, 0.42, 0.03), (0.11, 0.72, 0.09), (0.05, 0.86, 0.14)), nose_tip_y=0.88,
    mouth=MouthShape(lips=True, line=((-0.22, 1.1), (-0.08, 1.07), (0.0, 1.09), (0.08, 1.07), (0.22, 1.1)),
                     line_width=2.0, line_taper=(0.4, 1, 1, 1, 0.4),
                     lower=((-0.18, 1.12), (0.18, 1.12), (0.1, 1.2), (-0.1, 1.2)),
                     upper=((-0.2, 1.1), (0.0, 1.06), (0.2, 1.1), (0.0, 1.11))),
    blush=((-1.0, 0.28), (1.0, 0.2)))
MALE_CLEAN = FaceSpec(
    head=MALE_HEAD, eye=NARROW_EYE, eye_center=(0.44, 0.38), eye_unit=0.235,
    brow=BrowShape(points=((0.1, -0.02), (0.5, -0.12), (0.88, -0.06), (0.86, 0.02), (0.5, -0.04), (0.12, 0.06)),
                   fill=True, corners=(0, 2, 3, 5)),
    nose_bridge=((0.12, 0.34, 0.03), (0.13, 0.7, 0.1), (0.07, 0.88, 0.17)), nose_tip_y=0.92,
    mouth=MouthShape(lips=False, line=((-0.22, 1.14), (-0.06, 1.12), (0.08, 1.13), (0.22, 1.11)), line_width=2.1,
                     line_taper=(0.3, 1, 1, 0.3), shade=((-0.1, 1.2), (0.1, 1.2), (0.06, 1.25), (-0.06, 1.25)),
                     philtrum=((0.0, 1.0), (0.01, 1.08))),
    chin_shade=((-0.24, 1.36), (0.24, 1.36), (0.13, 1.47), (-0.13, 1.47)))


# ---------- 추가 얼굴 ----------
# 성인 표지를 지키려고 눈 반폭은 0.25 이하, 턱 끝은 1.42 아래로 둔다(craft.md: 눈을 키우고 턱을 줄일수록 어려 보임).

SOFT_FEMALE_HEAD = HeadSpec(
    jaw=((0.6, 0.87, -0.25, 0.65, 0.6), (0.85, 0.76, -0.33, 0.58, 0.58), (1.0, 0.65, -0.36, 0.52, 0.55),
         (1.2, 0.47, -0.45, 0.4, 0.3), (1.33, 0.3, -0.56, 0.26, 0.18), (1.43, 0.08, -0.7, 0.07, 0.05)),
    nose=(0.86, 0.13), ear=(0.42, 0.13, 0.24, 25.0))
SHARP_FEMALE_HEAD = HeadSpec(
    jaw=((0.6, 0.85, -0.25, 0.64, 0.6), (0.85, 0.7, -0.33, 0.56, 0.58), (1.0, 0.56, -0.36, 0.48, 0.54),
         (1.2, 0.38, -0.47, 0.35, 0.28), (1.35, 0.22, -0.6, 0.22, 0.16), (1.47, 0.05, -0.74, 0.05, 0.03)),
    nose=(0.88, 0.16), ear=(0.42, 0.13, 0.24, 25.0))
GENTLE_MALE_HEAD = HeadSpec(
    jaw=((0.66, 0.9, -0.25, 0.66, 0.62), (0.9, 0.79, -0.3, 0.6, 0.6), (1.1, 0.64, -0.36, 0.54, 0.5),
         (1.32, 0.38, -0.52, 0.34, 0.26), (1.44, 0.18, -0.62, 0.19, 0.13), (1.48, 0.06, -0.66, 0.07, 0.05)),
    nose=(0.9, 0.18), ear=(0.42, 0.15, 0.27, 25.0))
RUGGED_MALE_HEAD = HeadSpec(
    jaw=((0.7, 0.94, -0.25, 0.68, 0.63), (0.95, 0.86, -0.3, 0.62, 0.6), (1.15, 0.74, -0.36, 0.56, 0.52),
         (1.4, 0.4, -0.57, 0.32, 0.24), (1.5, 0.2, -0.66, 0.2, 0.14), (1.54, 0.12, -0.68, 0.12, 0.08)),
    nose=(0.92, 0.22), ear=(0.42, 0.15, 0.27, 25.0))

# 눈꼬리가 처지는 둥근 아몬드 꼴, 쌍꺼풀.
DROOPY_EYE = EyeShape(
    white=((-1.0, 0.02), (-0.6, -0.36), (0.05, -0.46), (0.65, -0.36), (1.02, 0.1), (0.7, 0.3), (0.0, 0.4),
           (-0.62, 0.28)),
    white_corners=(0, 4), iris=(0.0, 0.04, 0.46, 0.52), pupil=(0.19, 0.23), gleam=(0.16, -0.12, 0.12),
    lid=((-1.1, 0.04), (-0.7, -0.4), (0.0, -0.54), (0.7, -0.42), (1.12, 0.06), (1.25, 0.16), (1.06, 0.14),
         (0.68, -0.26), (0.0, -0.3), (-0.64, -0.16)),
    lid_corners=(0, 5), lower=((-0.66, 0.28), (0.0, 0.42), (0.7, 0.32), (1.0, 0.12)),
    lower_style=(1.4, (0.1, 1, 1, 0.3), 0.8), iris_span=(-0.46, 0.56), sclera="#fbf4f2", pupil_color="#100808",
    crease=((-0.55, -0.66), (0.15, -0.76), (0.85, -0.58)), crease_style=(1.2, (0.2, 1, 0.2), 0.45))
# 눈꼬리가 올라간 가는 꼴, 위로 뺀 날개.
CAT_EYE = EyeShape(
    white=((-1.0, 0.08), (-0.55, -0.24), (0.1, -0.34), (0.72, -0.28), (1.1, -0.16), (0.72, 0.18), (0.0, 0.28),
           (-0.6, 0.22)),
    white_corners=(0, 4), iris=(0.0, 0.0, 0.4, 0.46), pupil=(0.17, 0.21), gleam=(0.14, -0.1, 0.09),
    lid=((-1.1, 0.08), (-0.7, -0.3), (0.0, -0.44), (0.75, -0.38), (1.22, -0.24), (1.62, -0.42), (1.16, -0.1),
         (0.72, -0.18), (0.0, -0.18), (-0.66, -0.06)),
    lid_corners=(0, 5), lower=((-0.72, 0.2), (0.0, 0.3), (0.74, 0.2), (1.08, -0.1)),
    lower_style=(1.4, (0.1, 1, 1, 0.2), 0.9), iris_span=(-0.4, 0.46), sclera="#fbf4f2", pupil_color="#100808")
# 남성의 조금 큰 눈, 처진 눈꼬리, 쌍꺼풀.
GENTLE_EYE = EyeShape(
    white=((-1.0, 0.0), (-0.5, -0.3), (0.2, -0.38), (0.8, -0.24), (1.08, 0.06), (0.7, 0.24), (0.0, 0.3),
           (-0.6, 0.2)),
    white_corners=(0, 4), iris=(0.0, 0.02, 0.42, 0.46), pupil=(0.17, 0.21), gleam=(0.14, -0.12, 0.09),
    lid=((-1.08, 0.02), (-0.7, -0.34), (0.0, -0.48), (0.8, -0.34), (1.14, 0.06), (0.8, -0.2), (0.0, -0.3),
         (-0.66, -0.16)),
    lid_corners=(0, 4), lower=((-0.6, 0.2), (0.0, 0.32), (0.72, 0.22)), lower_style=(1.3, (0.1, 1, 0.2), 0.6),
    iris_span=(-0.42, 0.44), sclera="#f8f2ee", pupil_color="#080606",
    crease=((-0.55, -0.66), (0.1, -0.78), (0.86, -0.62)), crease_style=(1.2, (0.2, 1, 0.2), 0.5))
# 깊게 들어간 가는 눈과 두꺼운 윗눈꺼풀, 눈두덩 그늘 선.
DEEP_EYE = EyeShape(
    white=((-1.0, 0.04), (-0.5, -0.2), (0.2, -0.26), (0.8, -0.18), (1.1, -0.02), (0.7, 0.16), (0.0, 0.2),
           (-0.6, 0.14)),
    white_corners=(0, 4), iris=(0.0, 0.0, 0.38, 0.42), pupil=(0.15, 0.19), gleam=(0.12, -0.1, 0.07),
    lid=((-1.12, 0.06), (-0.7, -0.28), (0.0, -0.38), (0.82, -0.28), (1.18, -0.02), (0.8, -0.12), (0.0, -0.18),
         (-0.66, -0.06)),
    lid_corners=(0, 4), lower=((-0.62, 0.16), (0.0, 0.24), (0.72, 0.17)), lower_style=(1.4, (0.1, 1, 0.2), 0.8),
    iris_span=(-0.36, 0.36), sclera="#f4ede8", pupil_color="#080606",
    crease=((-0.7, -0.52), (0.1, -0.62), (0.9, -0.5)), crease_style=(1.6, (0.3, 1, 0.3), 0.7))

FEMALE_SOFT = FaceSpec(
    head=SOFT_FEMALE_HEAD, eye=DROOPY_EYE, eye_center=(0.45, 0.41), eye_unit=0.245,
    brow=BrowShape(points=((0.15, -0.06), (0.48, -0.17), (0.82, -0.08)), width=3.0, taper=(0.8, 1, 0.2)),
    nose_bridge=((0.09, 0.5, 0.03), (0.1, 0.74, 0.08), (0.05, 0.86, 0.12)), nose_tip_y=0.87,
    mouth=MouthShape(lips=True, line=((-0.2, 1.1), (-0.07, 1.07), (0.0, 1.09), (0.07, 1.07), (0.2, 1.1)),
                     line_width=1.9, line_taper=(0.4, 1, 1, 1, 0.4),
                     lower=((-0.16, 1.12), (0.16, 1.12), (0.1, 1.22), (-0.1, 1.22)),
                     upper=((-0.18, 1.1), (0.0, 1.055), (0.18, 1.1), (0.0, 1.115))),
    blush=((-1.0, 0.34), (1.0, 0.26)), blush_radii=(0.22, 0.09))
FEMALE_SHARP = FaceSpec(
    head=SHARP_FEMALE_HEAD, eye=CAT_EYE, eye_center=(0.46, 0.39), eye_unit=0.24,
    brow=BrowShape(points=((0.14, -0.04), (0.5, -0.12), (0.86, -0.14)), width=3.0, taper=(1.0, 0.9, 0.15)),
    nose_bridge=((0.1, 0.36, 0.03), (0.11, 0.72, 0.1), (0.05, 0.88, 0.16)), nose_tip_y=0.89,
    mouth=MouthShape(lips=True, line=((-0.24, 1.11), (-0.09, 1.08), (0.0, 1.1), (0.09, 1.08), (0.24, 1.11)),
                     line_width=2.0, line_taper=(0.4, 1, 1, 1, 0.4),
                     lower=((-0.2, 1.13), (0.2, 1.13), (0.1, 1.18), (-0.1, 1.18)),
                     upper=((-0.22, 1.11), (0.0, 1.07), (0.22, 1.11), (0.0, 1.115))),
    blush=((-1.0, 0.18), (1.0, 0.12)))
MALE_GENTLE = FaceSpec(
    head=GENTLE_MALE_HEAD, eye=GENTLE_EYE, eye_center=(0.44, 0.39), eye_unit=0.245,
    brow=BrowShape(points=((0.14, -0.06), (0.5, -0.16), (0.86, -0.08), (0.85, -0.04), (0.5, -0.11), (0.15, -0.01)),
                   fill=True, corners=(0, 2, 3, 5)),
    nose_bridge=((0.11, 0.44, 0.03), (0.12, 0.72, 0.09), (0.06, 0.88, 0.14)), nose_tip_y=0.9,
    # 입꼬리를 조금 올린 선. 온화한 인상의 가장 큰 단서다.
    mouth=MouthShape(lips=False, line=((-0.21, 1.1), (-0.07, 1.125), (0.07, 1.125), (0.21, 1.1)), line_width=2.0,
                     line_taper=(0.3, 1, 1, 0.3), shade=((-0.1, 1.19), (0.1, 1.19), (0.06, 1.24), (-0.06, 1.24)),
                     philtrum=((0.0, 1.0), (0.01, 1.07))),
    chin_shade=((-0.16, 1.36), (0.16, 1.36), (0.08, 1.44), (-0.08, 1.44)))
MALE_RUGGED = FaceSpec(
    head=RUGGED_MALE_HEAD, eye=DEEP_EYE, eye_center=(0.44, 0.4), eye_unit=0.225,
    brow=BrowShape(points=((0.08, 0.0), (0.5, -0.08), (0.92, -0.06), (0.9, 0.06), (0.5, 0.03), (0.1, 0.1)), fill=True,
                   corners=(0, 2, 3, 5)),
    nose_bridge=((0.14, 0.32, 0.04), (0.15, 0.7, 0.12), (0.09, 0.9, 0.2)), nose_tip_y=0.93,
    mouth=MouthShape(lips=False, line=((-0.25, 1.15), (-0.08, 1.14), (0.08, 1.145), (0.25, 1.14)), line_width=2.3,
                     line_taper=(0.3, 1, 1, 0.3), shade=((-0.12, 1.21), (0.12, 1.21), (0.07, 1.27), (-0.07, 1.27)),
                     philtrum=((0.0, 1.0), (0.01, 1.09))),
    chin_shade=((-0.3, 1.4), (0.3, 1.4), (0.16, 1.52), (-0.16, 1.52)), stubble=0.35)

FEMALE_FACES = {"mature": FEMALE_MATURE, "soft": FEMALE_SOFT, "sharp": FEMALE_SHARP}
MALE_FACES = {"clean": MALE_CLEAN, "gentle": MALE_GENTLE, "rugged": MALE_RUGGED}
