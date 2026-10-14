"""paintkit.props: small things a figure holds, and smoke.

A cigarette is a short paper stroke with a tan filter and a glowing tip, held
between the index and middle fingers (in hand units, so it turns with the hand)
or at the corner of the mouth (in head units, so it turns with the head). Smoke
rises from the tip as a few thin, widening, wavering strands that fade upward.
`smoke` is also used on its own (an ashtray in a still life).
"""
from __future__ import annotations

import numpy as np

from . import core as pk
from . import light as lt
from .anatomy import MOUTH_Y

CIGARETTE_HOLDS = ("left", "right", "mouth")
PAPER, FILTER, EMBER, ASH = "#f1eee6", "#d49a55", "#ff5a1f", "#8e8c8a"
GLOW = "#ff9a4a"
FILTER_SHARE, EMBER_SHARE = 0.28, 0.07
# Hand units (wrist at the origin, fingers along +y, thumb on -x): the filter sits in the
# fork of index and middle finger, the lit end points out past the index side.
HAND_GRIP = ((-0.02, 0.64), (-0.50, 0.70))
HAND_WIDTH = 0.055
# Head units: from the mouth corner down and out (front rig), forward and down (profile rig).
MOUTH_FRONT = ((0.030, MOUTH_Y + 0.010), (0.290, MOUTH_Y + 0.120))
MOUTH_PROFILE = ((0.020, 0.010), (0.300, 0.110))      # offsets from the profile's lip line point
MOUTH_WIDTH = 0.032
SMOKE_RISE = 1.3                  # smoke column height (head units)
SMOKE_STRANDS = 4
SMOKE_WIDTH, SMOKE_OPACITY = 1.0, 0.62   # strand width (times the cigarette's) and paint strength


def check(hold):
    if hold is not None and hold not in CIGARETTE_HOLDS:
        raise ValueError(f"unknown cigarette hold '{hold}', expected one of {list(CIGARETTE_HOLDS)}")
    return hold


def smoke(layer: pk.Layer, start, rise_px: float, width_px: float, seed: int = 0, color="#d9dbe2",
          opacity: float = 0.5, drift: float = 0.25) -> np.ndarray:
    """Strands rising from `start` (pixels) by `rise_px`, drifting sideways by `drift` of the rise."""
    shape = layer.a.shape
    rng = np.random.default_rng(seed)
    start = np.asarray(start, np.float32)
    strands = []
    t = np.linspace(0.0, 1.0, 40)
    for _ in range(SMOKE_STRANDS):
        freq, phase = rng.uniform(1.2, 2.4), rng.uniform(0, 2 * np.pi)
        sway = rise_px * rng.uniform(0.04, 0.10) * t ** 1.3
        xs = start[0] + drift * rise_px * t ** 1.5 + sway * np.sin(2 * np.pi * (freq * t + phase))
        ys = start[1] - rise_px * t * rng.uniform(0.75, 1.0)
        widths = width_px * (0.5 + 3.5 * t ** 1.4) * rng.uniform(0.7, 1.2)
        strands.append((np.stack([xs, ys], 1).astype(np.float32), widths.astype(np.float32)))
    mask = pk.blur(pk.stroke_mask(shape, strands), max(width_px * 0.8, 0.8))
    fade = 1.0 - pk.linear_ramp(shape, start, start + np.array([0.0, -rise_px], np.float32))
    mask = np.clip(mask * 1.4, 0.0, 1.0) * fade
    layer.paint(mask, color, opacity)
    return mask


def paint_cigarette(layer: pk.Layer, base, tip, width: float, line_color=None, line_opacity: float = 0.6):
    """Paper, filter and glowing tip between two pixel points (filter end first)."""
    shape = layer.a.shape
    base, tip = np.asarray(base, np.float32), np.asarray(tip, np.float32)

    def piece(t0, t1):
        return pk.stroke_mask(shape, (pk.resample(np.array([base + (tip - base) * t0, base + (tip - base) * t1]), 6),
                                      width))

    body = piece(0.0, 1.0)
    layer.paint(body, PAPER)
    layer.paint(piece(0.0, FILTER_SHARE), FILTER)
    layer.paint(piece(1.0 - EMBER_SHARE * 1.8, 1.0 - EMBER_SHARE), ASH)
    ember = piece(1.0 - EMBER_SHARE, 1.0)
    layer.paint(ember, EMBER)
    layer.paint(pk.radial_ramp(shape, tip, width * 3.0), GLOW, 0.55)
    if line_color is not None:
        layer.paint(lt.outline_mask(body, 1.0), line_color, line_opacity)


def _grip(fig, side: str):
    hand = fig.hands[side]
    if hand.hidden:
        raise ValueError(f"cigarette in the {side} hand, but that hand is out of sight (pocket or tucked)")
    base, tip = hand.to_px(np.array(HAND_GRIP, np.float32))
    return base, tip, fig.px(fig.plan.hand_length * HAND_WIDTH)


def _mouth(fig):
    """Mouth hold for whichever head rig the figure uses; None from behind."""
    look = getattr(fig, "look", None)
    if look == "away" and not getattr(fig, "three_quarter", False):
        return None
    profile = getattr(fig, "profile", None)
    if profile is not None and not getattr(fig, "three_quarter", False):
        lip = np.array(profile.points["stomion"], np.float32)
        base, tip = (profile.frame.to((lip + np.array(offset, np.float32))[None])[0] for offset in MOUTH_PROFILE)
        return base, tip, fig.px(MOUTH_WIDTH)
    side = -1.0 if fig.spec.head_turn > 0 else 1.0       # keep it on the side turned toward the viewer
    pts = np.array([[x * side, y] for x, y in MOUTH_FRONT], np.float32)
    base, tip = np.asarray(fig.head.to(pts), np.float32).reshape(-1, 2)
    return base, tip, fig.px(MOUTH_WIDTH)


def paint(fig):
    """The figure's cigarette (figure.cigarette) and its smoke, over everything painted so far."""
    hold = getattr(fig, "cigarette", None)
    if not hold:
        return
    placed = _mouth(fig) if hold == "mouth" else _grip(fig, hold)
    if placed is None:
        return
    base, tip, width = placed
    st = fig.style
    paint_cigarette(fig.cv.layer("props"), base, tip, width, fig.line_color(PAPER) if st.line_width > 0 else None,
                    0.6 * st.line_opacity)
    smoke(fig.cv.layer("smoke"), tip, fig.px(SMOKE_RISE), width * SMOKE_WIDTH, seed=fig.spec.hair_seed,
          opacity=SMOKE_OPACITY, drift=0.25 * fig.light_side)
