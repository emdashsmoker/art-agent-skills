"""Look closer at a render: overlay a coordinate grid and/or crop and enlarge a region.

The grid tells you the pixel coordinates of whatever looks wrong, so the fix
in the scene script can be aimed instead of guessed.

Usage:
  python inspect_render.py render.png out.png --grid 100
  python inspect_render.py render.png out.png --crop 280,200,780,800 --zoom 2
"""
import argparse

import cv2

GRID_COLOR = (255, 0, 255)       # magenta: rarely present in a painting, so it stays readable
LABEL_SCALE = 0.45


def overlay_grid(image, step):
    out = image.copy()
    height, width = out.shape[:2]
    for x in range(0, width, step):
        cv2.line(out, (x, 0), (x, height - 1), GRID_COLOR, 1)
        cv2.putText(out, str(x), (x + 3, 14), cv2.FONT_HERSHEY_SIMPLEX, LABEL_SCALE, GRID_COLOR, 1, cv2.LINE_AA)
    for y in range(0, height, step):
        cv2.line(out, (0, y), (width - 1, y), GRID_COLOR, 1)
        cv2.putText(out, str(y), (3, y + 14), cv2.FONT_HERSHEY_SIMPLEX, LABEL_SCALE, GRID_COLOR, 1, cv2.LINE_AA)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--grid', type=int, default=0, help='grid spacing in source pixels (0 = no grid)')
    parser.add_argument('--crop', default='', help='x0,y0,x1,y1 in source pixels')
    parser.add_argument('--zoom', type=float, default=1.0, help='enlargement factor after cropping')
    args = parser.parse_args()

    image = cv2.imread(args.source)
    if image is None:
        raise SystemExit(f'cannot read image: {args.source}')
    if args.grid > 0:
        image = overlay_grid(image, args.grid)
    if args.crop:
        x0, y0, x1, y1 = (int(v) for v in args.crop.split(','))
        image = image[max(y0, 0):y1, max(x0, 0):x1]
    if args.zoom != 1.0:
        image = cv2.resize(image, None, fx=args.zoom, fy=args.zoom, interpolation=cv2.INTER_CUBIC)
    if not cv2.imwrite(args.output, image):
        raise SystemExit(f'cannot write image: {args.output}')
    print(f'wrote {args.output} ({image.shape[1]}x{image.shape[0]})')


if __name__ == '__main__':
    main()
