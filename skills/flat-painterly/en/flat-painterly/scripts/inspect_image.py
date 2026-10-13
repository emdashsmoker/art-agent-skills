"""Tool for reviewing renders: draws a coordinate grid over an image or enlarges a region, and saves it as a
separate PNG.

It reads positions and checks details in a finished image without touching the scene code.
Usage:
  python inspect_image.py out/final.png --grid 100 --width 1600
  python inspect_image.py out/final.png --crop 800 150 1360 700 --width 1600 --zoom 2
--width is the logical width of the scene. It maps grid ticks and crop coordinates to logical coordinates.
"""
import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codepaint import config, io  # noqa: E402


def load(path):
    pixels = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if pixels is None:
        raise FileNotFoundError(f"cannot read image: {path}")
    return pixels[..., ::-1].astype("float32") / 255.0


def draw_grid(image, scale, step):
    frame = (image * 255.0).astype("uint8")[..., ::-1].copy()
    height, width = frame.shape[:2]
    for index in range(int(width / scale / step) + 1):
        x = int(round(index * step * scale))
        cv2.line(frame, (x, 0), (x, height - 1), config.GUIDE_COLOR, 1)
        cv2.putText(frame, str(index * step), (x + 3, 14), cv2.FONT_HERSHEY_SIMPLEX,
                    config.GUIDE_FONT_SCALE, config.GUIDE_COLOR, 1, cv2.LINE_AA)
    for index in range(int(height / scale / step) + 1):
        y = int(round(index * step * scale))
        cv2.line(frame, (0, y), (width - 1, y), config.GUIDE_COLOR, 1)
        cv2.putText(frame, str(index * step), (3, y - 4), cv2.FONT_HERSHEY_SIMPLEX,
                    config.GUIDE_FONT_SCALE, config.GUIDE_COLOR, 1, cv2.LINE_AA)
    return frame[..., ::-1].astype("float32") / 255.0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image")
    parser.add_argument("--width", type=float, required=True, help="logical width of the scene")
    parser.add_argument("--grid", type=int, default=0, help="grid spacing (logical units). 0 means no grid")
    parser.add_argument("--crop", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="logical coordinate region")
    parser.add_argument("--zoom", type=float, default=1.0)
    parser.add_argument("--out", help="output path. If omitted, _inspect is appended to the original name")
    arguments = parser.parse_args()

    image = load(arguments.image)
    scale = image.shape[1] / arguments.width
    if arguments.grid > 0:
        image = draw_grid(image, scale, arguments.grid)
    if arguments.crop:
        image = io.crop(image, arguments.crop, scale, arguments.zoom)
    source = Path(arguments.image)
    target = Path(arguments.out) if arguments.out else source.with_name(source.stem + "_inspect.png")
    print(io.save(image, target))


if __name__ == "__main__":
    main()
