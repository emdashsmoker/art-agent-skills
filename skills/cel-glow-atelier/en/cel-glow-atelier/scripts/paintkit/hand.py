"""paintkit.hand: articulated 2D hand.

A hand is a palm plus five chains of phalanges. Geometry is written in
"hand units" (1.0 = wrist to middle fingertip) with the wrist at the origin
and the fingers pointing along +y. Curling a finger toward the palm is
drawn as foreshortening: each phalanx is shortened by the cosine of its
bend, and a phalanx bent past 90 degrees folds back over the palm.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from . import core as pk
from . import light as lt

# Finger layout seen from the back of a right hand (thumb on -x):
# knuckle position, resting splay (deg), length, width at the base.
FINGERS = {
    "index": ((-0.158, 0.500), -6.0, 0.430, 0.110),
    "middle": ((-0.052, 0.520), -1.0, 0.480, 0.112),
    "ring": ((0.054, 0.500), 4.0, 0.445, 0.106),
    "pinky": ((0.152, 0.450), 11.0, 0.355, 0.092),
}
PHALANX_SHARE = (0.46, 0.30, 0.24)       # proximal, middle, distal share of finger length
# Out-of-plane angle reached by each phalanx at full curl (cumulative, degrees).
FULL_CURL_DEG = (80.0, 180.0, 250.0)
TIP_TAPER = 0.80                          # fingertip width relative to the base
THUMB_BASE = (-0.120, 0.110)
THUMB_LENGTHS = (0.210, 0.165, 0.140)     # metacarpal (inside the palm), proximal, distal
THUMB_WIDTHS = (0.190, 0.135, 0.120, 0.100)
THUMB_REST_DEG = -24.0                    # metacarpal direction when held alongside
THUMB_ARC_DEG = (0.0, 10.0, 18.0)         # each joint turns slightly back toward the fingers
THUMB_CURL_DEG = (0.0, 85.0, 135.0)       # extra turn per joint at full curl (across the palm)
PALM_BACK_DEPTH, PALM_FRONT_DEPTH = 0.06, 0.10   # palm slab: back of the hand and palm surface (hand units)
THUMB_BASE_DEPTH = -0.05                  # the thumb root sits on the palm side
THUMB_LIFT = 0.55                         # depth gained per unit of thumb length (it stands out in front)
THUMB_HIDE_DEPTH = 0.05                   # a thumb this far behind the palm plane is painted behind it
PALM_OUTLINE = np.array([
    [-0.125, 0.000], [0.118, 0.000], [0.190, 0.200], [0.208, 0.420],
    [0.120, 0.490], [0.010, 0.545], [-0.100, 0.540], [-0.200, 0.500],
    [-0.228, 0.330], [-0.185, 0.120],
], np.float32)


@dataclass
class HandPose:
    """curl: 0 straight ... 1 fully folded, per finger (index, middle, ring, pinky).
    spread: extra splay in degrees per finger. thumb_out: degrees the thumb
    swings away from the palm. thumb_curl: 0 straight ... 1 folded across."""
    curl: tuple = (0.0, 0.0, 0.0, 0.0)
    spread: tuple = (0.0, 0.0, 0.0, 0.0)
    thumb_out: float = 30.0
    thumb_curl: float = 0.0


POSES = {
    "open": HandPose(spread=(-9.0, -2.0, 5.0, 12.0), thumb_out=34.0),
    "relaxed": HandPose(curl=(0.18, 0.24, 0.30, 0.36), spread=(0.0, 1.0, 0.0, -3.0), thumb_out=18.0,
                        thumb_curl=0.15),
    "together": HandPose(spread=(5.0, 1.0, -4.0, -11.0), thumb_out=6.0),
    "point": HandPose(curl=(0.0, 1.0, 1.0, 1.0), thumb_out=-6.0, thumb_curl=0.75),
    "peace": HandPose(curl=(0.0, 0.0, 1.0, 1.0), spread=(-10.0, 9.0, 0.0, 0.0), thumb_out=-8.0,
                      thumb_curl=0.8),
    "fist": HandPose(curl=(1.0, 1.0, 1.0, 1.0), thumb_out=-4.0, thumb_curl=0.7),
    "grip": HandPose(curl=(0.55, 0.6, 0.62, 0.66), thumb_out=22.0, thumb_curl=0.30),
}


HIDDEN_POSES = ("pocket", "tucked")     # hands out of sight; a figure decides how the wrist ends


@dataclass
class HandPiece:
    """One paintable part of a hand, in pixels."""
    name: str
    mask: np.ndarray
    folded: bool = False      # bent past 90 degrees (lies on the palm side)
    paths: list = field(default_factory=list)


def _direction(deg: float) -> np.ndarray:
    rad = np.deg2rad(deg)
    return np.array([np.sin(rad), np.cos(rad)], np.float32)     # 0 deg = +y (toward fingertips)


def finger_segments(name: str, curl: float, spread: float) -> list:
    """[(start, end, width_start, width_end, folded)] for the three phalanges.

    Points are (x, y, z): z is depth out of the back of the hand (curling
    fingers bend toward the palm, -z). The front view ignores z; a rolled or
    tipped hand shows it."""
    (bx, by), splay, length, width = FINGERS[name]
    direction = _direction(splay + spread)
    point = np.array([bx, by, 0.0], np.float32)
    widths = np.linspace(width, width * TIP_TAPER, 4)
    segments = []
    for index, share in enumerate(PHALANX_SHARE):
        angle = np.deg2rad(FULL_CURL_DEG[index] * curl)
        # A folded phalanx still shows its thickness, so it never shrinks to nothing.
        reach = length * share * np.cos(angle)
        end = point + np.array([direction[0] * reach, direction[1] * reach, -length * share * np.sin(angle)],
                               np.float32)
        segments.append((point.copy(), end, widths[index], widths[index + 1], np.cos(angle) < 0.0))
        point = end
    return segments


def thumb_segments(thumb_out: float, thumb_curl: float) -> list:
    point = np.array([THUMB_BASE[0], THUMB_BASE[1], THUMB_BASE_DEPTH], np.float32)
    angle = THUMB_REST_DEG - thumb_out
    segments = []
    for index, length in enumerate(THUMB_LENGTHS):
        # Curling swings the thumb tip back across the palm (toward +x).
        bend = THUMB_ARC_DEG[index] + THUMB_CURL_DEG[index] * thumb_curl
        flat = _direction(angle + bend) * length * (1.0 - 0.25 * thumb_curl * (index > 0))
        # The thumb also stands out in front of the palm, which shows once the hand turns.
        end = point + np.array([flat[0], flat[1], -THUMB_LIFT * length], np.float32)
        segments.append((point.copy(), end, THUMB_WIDTHS[index], THUMB_WIDTHS[index + 1], False))
        point = end
    return segments


class Hand:
    """Builds and paints one hand.

    frame: pk.Frame mapping hand units to pixels (origin = wrist, scale =
    hand length in px, rot_deg = rotation; 0 points the fingers down the
    screen because the canvas y axis points down).
    mirror: True for the other hand (thumb on +x).
    view: "back" shows knuckles and nails, "palm" shows the palm side.
    roll: degrees the hand turns about its long axis (positive brings the
    thumb side toward the viewer; 90 = seen edge-on from the thumb side).
    pitch: degrees the fingers tip toward the viewer (foreshortened).
    """

    def __init__(self, shape, frame: pk.Frame, pose="relaxed", mirror: bool = False, view: str = "back",
                 widen: float = 1.0, roll: float = 0.0, pitch: float = 0.0):
        # A hand out of sight (in a pocket, under the other arm) keeps the API but draws nothing.
        self.hidden = pose in HIDDEN_POSES
        if self.hidden:
            pose = "relaxed"
        if isinstance(pose, str):
            if pose not in POSES:
                raise ValueError(f"unknown hand pose '{pose}', expected one of {list(POSES) + list(HIDDEN_POSES)}")
            pose = POSES[pose]
        if view not in ("back", "palm"):
            raise ValueError(f"unknown hand view '{view}', expected 'back' or 'palm'")
        self.shape = shape
        self.frame = frame
        self.pose = pose
        self.flip = np.array([-1.0 if mirror else 1.0, 1.0], np.float32)
        self.view = view
        self.widen = widen            # thicker fingers and a broader palm (male hands)
        roll_rad = np.deg2rad(float(np.clip(roll, -90.0, 90.0)))
        pitch_rad = np.deg2rad(float(np.clip(pitch, 0.0, 75.0)))
        self.turned = roll_rad != 0.0 or pitch_rad != 0.0
        self.roll_cs = (float(np.cos(roll_rad)), float(np.sin(roll_rad)))
        self.pitch_cs = (float(np.cos(pitch_rad)), float(np.sin(pitch_rad)))
        # Seen from the palm side, the palm faces the viewer: depth is reversed.
        self.facing = 1.0 if view == "back" else -1.0
        self.pieces = self._build()
        self.mask = np.maximum.reduce([piece.mask for piece in self.pieces])
        if self.hidden:
            self.mask = np.zeros_like(self.mask)

    def rotate(self, pts) -> np.ndarray:
        """(x, y, z) hand points after roll and pitch: columns x, y on screen, z toward the viewer."""
        pts = np.asarray(pts, np.float32).reshape(-1, 3)
        x, y, z = pts[:, 0], pts[:, 1], pts[:, 2] * self.facing
        rc, rs = self.roll_cs
        pc, ps = self.pitch_cs
        x1, z1 = x * rc + z * rs, -x * rs + z * rc
        y2, z2 = y * pc - z1 * ps, y * ps + z1 * pc
        return np.stack([x1, y2, z2], axis=1)

    def to_px(self, pts) -> np.ndarray:
        """Hand points (x, y) or (x, y, z) to pixels."""
        pts = np.asarray(pts, np.float32)
        if pts.shape[-1] == 2:
            pts = np.concatenate([pts, np.zeros((*pts.shape[:-1], 1), np.float32)], axis=-1)
        return self.frame.to(self.rotate(pts)[:, :2] * self.flip)

    def depth(self, segments) -> float:
        """Mean depth of a chain of segments toward the viewer (larger = nearer)."""
        pts = np.array([point for start, end, *_ in segments for point in (start, end)], np.float32)
        return float(self.rotate(pts)[:, 2].mean())

    def _chain_mask(self, segments) -> tuple:
        strokes, paths = [], []
        for start, end, w0, w1, _ in segments:
            path = pk.resample(self.to_px(np.array([start, end])), 8)
            # Never thinner than a knuckle seen end-on, even when foreshortened to a dot.
            widths = np.linspace(w0, w1, len(path)) * self.frame.scale * self.widen
            strokes.append((path, widths))
            paths.append(path)
        return pk.stroke_mask(self.shape, strokes), paths

    def _palm_mask(self) -> np.ndarray:
        outline = pk.spline(PALM_OUTLINE * [np.sqrt(self.widen), 1.0], closed=True)
        if not self.turned:
            return pk.fill_mask(self.shape, self.to_px(outline))
        # A turned palm is a slab: the silhouette of its back and front faces together.
        faces = [np.concatenate([outline, np.full((len(outline), 1), depth, np.float32)], axis=1)
                 for depth in (PALM_BACK_DEPTH * self.widen, -PALM_FRONT_DEPTH * self.widen)]
        hull = cv2.convexHull(self.to_px(np.vstack(faces)).astype(np.float32))[:, 0, :]
        return pk.fill_mask(self.shape, hull)

    def _build(self) -> list:
        pose = self.pose
        palm = HandPiece("palm", self._palm_mask())
        visible, folded = [], []
        for index, name in enumerate(FINGERS):
            segments = finger_segments(name, pose.curl[index], pose.spread[index])
            shown = [s for s in segments if not s[4]]
            hidden = [s for s in segments if s[4]]
            if shown:
                mask, paths = self._chain_mask(shown)
                visible.append((self.depth(shown), HandPiece(name, mask, False, paths)))
            if hidden:
                mask, paths = self._chain_mask(hidden)
                folded.append((self.depth(hidden), HandPiece(name + "_folded", mask, True, paths)))
        if self.turned:
            # A turned hand stacks its fingers: the ones nearer the viewer are painted last.
            visible.sort(key=lambda item: item[0])
            folded.sort(key=lambda item: item[0])
        visible = [piece for _, piece in visible]
        folded = [piece for _, piece in folded]
        thumb_segs = thumb_segments(pose.thumb_out, pose.thumb_curl)
        thumb_mask, thumb_paths = self._chain_mask(thumb_segs)
        thumb = HandPiece("thumb", thumb_mask, False, thumb_paths)
        thumb_hidden = self.turned and self.depth(thumb_segs) < -THUMB_HIDE_DEPTH
        if self.view == "back":
            # Seen from the back, folded phalanges and a crossing thumb sit behind the hand,
            # and so does a thumb the turn has carried behind the palm.
            thumb_behind = pose.thumb_curl > 0.5 or thumb_hidden
            order = folded + ([thumb] if thumb_behind else []) + [palm] + visible
            return order + ([] if thumb_behind else [thumb])
        if thumb_hidden:
            return [thumb, palm] + visible + folded
        return [palm] + visible + folded + [thumb]

    def paint(self, layer: pk.Layer, skin, shadow, line_color, light, softness: float = 0.03,
              line_width: float = 0.012, line_opacity: float = 1.0, strength: float = 1.0) -> None:
        """Fill, shade and ink the hand piece by piece, back to front."""
        if self.hidden:
            return
        scale = self.frame.scale
        palm = next(piece.mask for piece in self.pieces if piece.name == "palm")
        palm_index = next(i for i, piece in enumerate(self.pieces) if piece.name == "palm")
        for index, piece in enumerate(self.pieces):
            layer.paint(piece.mask, skin)
            radius = scale * (0.10 if piece.name == "palm" else 0.045)
            lit = lt.lambert(lt.normals_from_height(lt.inflate(piece.mask, radius)), light)
            shade = lt.form_shadow(lit, 0.22, softness) * piece.mask
            # Pieces painted later lie on top and throw a small shadow on this one.
            above = [later.mask for later in self.pieces[index + 1:]]
            if above:
                over = np.maximum.reduce(above)
                shade = np.maximum(shade, lt.cast_shadow(over, piece.mask, light, scale * 0.014))
            layer.paint(shade, shadow, strength)
            if line_width > 0 and piece.name != "palm":
                band = lt.outline_mask(piece.mask, max(scale * line_width, 1.0), light, 0.5)
                # A finger grows out of the palm: its edge is inked only where it
                # leaves the palm, unless it lies folded on top of the palm.
                lying_on_palm = index > palm_index and self.view == "palm" and (
                    piece.folded or piece.name == "thumb")
                if not lying_on_palm:
                    band = band * (1.0 - palm)
                layer.paint(band, line_color, line_opacity)
        if line_width > 0:
            silhouette = lt.outline_mask(self.mask, max(scale * line_width, 1.0), light, 0.5)
            layer.paint(silhouette, line_color, line_opacity)
        if self.view == "back":
            self._paint_nails(layer, skin, line_color, line_opacity if line_width > 0 else 0.4)

    def _paint_nails(self, layer: pk.Layer, skin, line_color, opacity: float) -> None:
        scale = self.frame.scale
        palm_index = next(i for i, piece in enumerate(self.pieces) if piece.name == "palm")
        for index, piece in enumerate(self.pieces):
            # Pieces painted before the palm are hidden behind the hand.
            if index < palm_index or piece.folded or len(piece.paths) < 3:
                continue
            tip_path = piece.paths[-1]
            if np.linalg.norm(tip_path[-1] - tip_path[0]) < scale * 0.05:
                continue                    # too foreshortened to show a nail
            nail = pk.resample(np.array([tip_path[2], tip_path[-1]]), 6)
            mask = pk.stroke_mask(self.shape, (nail, scale * 0.052)) * piece.mask
            layer.paint(mask, pk.mix(skin, "#ffffff", 0.45), 0.9)
            layer.paint(lt.outline_mask(mask, max(scale * 0.006, 1.0)), line_color, opacity * 0.5)
