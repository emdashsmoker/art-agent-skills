"""Draw a grid labelled with original pixel coordinates, to read defect positions as numbers

WHY: guessing coordinates by eye is error prone, a trim meant for fingers can spread to the waist or thighs
HOW: Pillow only, no detection model. With a region, that part is enlarged and gets a finer grid
"""
import sys

from PIL import Image, ImageDraw, ImageFont

# WHY: too many lines make labels overlap, too few make reading coarse, so cap the lines per side
MAX_LINES_PER_SIDE = 16
NICE_STEPS = (5, 10, 20, 25, 50, 100, 200, 250, 500)
VIEW_LONG_SIDE = 1024
LABEL_FONT_SIZE = 15
LINE_DARK = (31, 58, 104)
LINE_LIGHT = (255, 255, 255)


def parse_region(text: str, width: int, height: int) -> tuple:
    box = [int(v) for v in text.split(",")]
    if len(box) != 4 or not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
        sys.exit("region must be x0,y0,x1,y1 inside the image (%dx%d)" % (width, height))
    return tuple(box)


def choose_step(region: tuple) -> int:
    long_side = max(region[2] - region[0], region[3] - region[1])
    for step in NICE_STEPS:
        if long_side / step <= MAX_LINES_PER_SIDE:
            return step
    return NICE_STEPS[-1]


def load_font() -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=LABEL_FONT_SIZE)
    except TypeError:  # WHY: Pillow before 10.1 has no size argument
        return ImageFont.load_default()


def draw_label(draw: ImageDraw.ImageDraw, position: tuple, text: str, font) -> None:
    box = draw.textbbox(position, text, font=font)
    draw.rectangle((box[0] - 2, box[1] - 1, box[2] + 2, box[3] + 1), fill=LINE_DARK)
    draw.text(position, text, fill=LINE_LIGHT, font=font)


def draw_grid(view: Image.Image, region: tuple, step: int) -> Image.Image:
    """view is the enlarged region, labels are original pixel coordinates"""
    draw, font = ImageDraw.Draw(view), load_font()
    scale_x = view.width / (region[2] - region[0])
    scale_y = view.height / (region[3] - region[1])
    for x in range(-(-region[0] // step) * step, region[2] + 1, step):
        vx = round((x - region[0]) * scale_x)
        # WHY: a dark line next to a light line stays visible on any background
        draw.line((vx, 0, vx, view.height), fill=LINE_DARK, width=1)
        draw.line((vx + 1, 0, vx + 1, view.height), fill=LINE_LIGHT, width=1)
        draw_label(draw, (vx + 4, 2), str(x), font)
    for y in range(-(-region[1] // step) * step, region[3] + 1, step):
        vy = round((y - region[1]) * scale_y)
        draw.line((0, vy, view.width, vy), fill=LINE_DARK, width=1)
        draw.line((0, vy + 1, view.width, vy + 1), fill=LINE_LIGHT, width=1)
        draw_label(draw, (2, vy + 4), str(y), font)
    return view


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: python3 grid_measure.py IN_PATH OUT_PATH [x0,y0,x1,y1] [STEP]")
    image = Image.open(sys.argv[1]).convert("RGB")
    region = parse_region(sys.argv[3], *image.size) if len(sys.argv) > 3 else (0, 0, *image.size)
    step = int(sys.argv[4]) if len(sys.argv) > 4 else choose_step(region)
    zoom = VIEW_LONG_SIDE / max(region[2] - region[0], region[3] - region[1])
    view = image.crop(region).resize(
        (round((region[2] - region[0]) * zoom), round((region[3] - region[1]) * zoom)), Image.LANCZOS)
    draw_grid(view, region, step).save(sys.argv[2])
    print("%s region=%s step=%dpx zoom=%.2f (labels are original pixel coordinates)" % (sys.argv[2], region, step, zoom))


if __name__ == "__main__":
    main()
