"""Tile candidate images into one numbered contact sheet.

WHY: when the user picks candidates, one image with numbers is quicker to compare than separate
     files, and a number is easier to answer with than a file name. The sheet is for choosing
     composition and expression only, small defects are judged on the original candidate files.
HOW: each input is fitted inside a fixed square cell without cropping, its number sits in a strip
     above the cell so the label never covers the picture. Wildcards are expanded here, so the same
     command works in shells that pass them through unexpanded (Windows). Prints the number-to-file
     mapping as JSON so the agent can match the user's numbers to files. Pillow only.
"""
import common  # noqa: F401  (shared exit codes and logging)

import argparse
import glob
import json
import math
import sys
from pathlib import Path

from common import EXIT_MISSING_DEPENDENCY, EXIT_OK, EXIT_QUERY_OR_ARGUMENT, EXIT_WRITE_FAILURE, IMAGE_SUFFIXES, fail

CELL_SIZE = 384            # longest side of each picture on the sheet, in pixels
GAP = 16                   # space between cells and around the sheet
LABEL_HEIGHT = 48          # strip above each cell that holds the number
LABEL_FONT_SIZE = 36
MAX_COLUMNS = 4            # wider sheets shrink each picture too much on a normal screen
SHEET_BACKGROUND = (255, 255, 255)
CELL_BACKGROUND = (232, 232, 232)  # shows the letterbox of non-square inputs
LABEL_COLOR = (0, 0, 0)
WILDCARD_CHARACTERS = "*?["


def expand_inputs(patterns, sheet_path):
    """Expand wildcards in input order, skip the sheet itself, refuse missing files."""
    paths = []
    for pattern in patterns:
        if any(character in pattern for character in WILDCARD_CHARACTERS):
            matches = sorted(glob.glob(pattern))
            if not matches:
                fail(EXIT_QUERY_OR_ARGUMENT, "no file matches %s" % pattern)
            paths.extend(matches)
        else:
            paths.append(pattern)
    # WHY: a wildcard over the output folder would otherwise pick up an earlier sheet
    paths = [path for path in paths if Path(path).resolve() != sheet_path.resolve()]
    missing = [path for path in paths if not Path(path).is_file()]
    if missing:
        fail(EXIT_QUERY_OR_ARGUMENT, "input not found: %s" % ", ".join(missing))
    if not paths:
        fail(EXIT_QUERY_OR_ARGUMENT, "no input image")
    return paths


def grid_shape(count):
    """Columns and rows that keep the sheet balanced, at most MAX_COLUMNS wide."""
    rows = math.ceil(count / MAX_COLUMNS)
    columns = math.ceil(count / rows)
    return columns, rows


def label_font(image_font):
    try:
        return image_font.load_default(size=LABEL_FONT_SIZE)
    except TypeError:  # WHY: Pillow before 10.1 has only the small bitmap font, the numbers stay readable but small
        return image_font.load_default()


def fit_into_cell(image, image_module):
    """Scale to fit the square cell without cropping, so the whole composition stays visible."""
    scale = CELL_SIZE / max(image.size)
    fitted = image.convert("RGB").resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                                         image_module.LANCZOS)
    cell = image_module.new("RGB", (CELL_SIZE, CELL_SIZE), CELL_BACKGROUND)
    cell.paste(fitted, ((CELL_SIZE - fitted.width) // 2, (CELL_SIZE - fitted.height) // 2))
    return cell


def build_sheet(paths, image_module, draw_module, font):
    columns, rows = grid_shape(len(paths))
    width = columns * CELL_SIZE + (columns + 1) * GAP
    height = rows * (LABEL_HEIGHT + CELL_SIZE) + (rows + 1) * GAP
    sheet = image_module.new("RGB", (width, height), SHEET_BACKGROUND)
    draw = draw_module.Draw(sheet)
    for index, path in enumerate(paths):
        column, row = index % columns, index // columns
        left = GAP + column * (CELL_SIZE + GAP)
        top = GAP + row * (LABEL_HEIGHT + CELL_SIZE + GAP)
        try:
            with image_module.open(path) as source:
                sheet.paste(fit_into_cell(source, image_module), (left, top + LABEL_HEIGHT))
        except OSError as error:
            fail(EXIT_QUERY_OR_ARGUMENT, "cannot read %s (%s)" % (path, error))
        number = str(index + 1)
        box = draw.textbbox((0, 0), number, font=font)
        text_x = left + (CELL_SIZE - (box[2] - box[0])) // 2 - box[0]
        text_y = top + (LABEL_HEIGHT - (box[3] - box[1])) // 2 - box[1]
        draw.text((text_x, text_y), number, fill=LABEL_COLOR, font=font)
    return sheet


def main(argv=None):
    parser = argparse.ArgumentParser(description="numbered contact sheet of candidate images")
    parser.add_argument("inputs", nargs="+", help="image files or wildcard patterns, numbered in this order")
    parser.add_argument("--out", required=True, help="sheet file path (.png or .jpg)")
    args = parser.parse_args(argv)
    sheet_path = Path(args.out).expanduser()
    if sheet_path.suffix.lower() not in IMAGE_SUFFIXES:
        fail(EXIT_QUERY_OR_ARGUMENT, "--out must end with .png, .jpg or .jpeg")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        fail(EXIT_MISSING_DEPENDENCY, "Pillow missing, install the dependencies in the skill environment")
    paths = expand_inputs(args.inputs, sheet_path)
    sheet = build_sheet(paths, Image, ImageDraw, label_font(ImageFont))
    try:
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(sheet_path)
    except OSError as error:
        fail(EXIT_WRITE_FAILURE, "could not save %s (%s)" % (sheet_path, error))
    print(json.dumps({"path": str(sheet_path), "size": "%dx%d" % sheet.size,
                      "candidates": [{"number": index + 1, "path": path} for index, path in enumerate(paths)]},
                     ensure_ascii=False))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
