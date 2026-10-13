"""Example: a sheet of hand studies (five poses seen from the back, two from the palm).

Usage: python examples/hands.py --style anime|illust|painterly --out hands.png
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepainter import Painting, backdrop
from codepainter.figure import hand
from codepainter.styles import finish, get_style

WIDTH, HEIGHT = 1500, 1000
SKIN = "#f4d6c0"
HAND_LENGTH = 300


def render(style_name, seed=0):
    style = get_style(style_name)
    painting = Painting(WIDTH, HEIGHT)
    backdrop.gradient(painting, "#d9cfc0", "#b9a994")
    backdrop.mottle(painting, "#a89880", amount=0.25, scale=1.0, seed=1)
    # top row: fingers up (angle 180), back of the hand, thumb toward the screen left
    for column, name in enumerate(["relaxed", "open", "fist", "point", "peace"]):
        hand.draw_hand(painting, (170 + column * 290, 440), 180, HAND_LENGTH, SKIN, style, pose=hand.HAND_POSES[name], thumb_side=-1.0)
    # bottom row: palms, and one hand reaching across
    hand.draw_hand(painting, (300, 960), 180, HAND_LENGTH, SKIN, style, pose=hand.OPEN, thumb_side=1.0, view="palm")
    hand.draw_hand(painting, (640, 960), 170, HAND_LENGTH, SKIN, style, pose=hand.RELAXED, thumb_side=1.0, view="palm")
    hand.draw_hand(painting, (1050, 800), 75, HAND_LENGTH, SKIN, style, pose=hand.RELAXED, thumb_side=1.0)
    return painting, finish(painting, style, seed=seed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="illust", choices=["anime", "illust", "painterly"])
    parser.add_argument("--out", default="hands.png")
    args = parser.parse_args()
    painting, image = render(args.style)
    painting.save(args.out, image)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
