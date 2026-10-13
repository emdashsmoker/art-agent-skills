"""Cut away an edge defect with the smallest crop, then resize back (skipped with --no-resize).
Defect boxes are read from the grid made by grid_measure.py.

WHY: a defect touching the frame edge disappears for certain when cut away, cheaper than inpainting, and the rest stays untouched
HOW: for each of the four edges, find the largest window that excludes the defect box, keep the edge that leaves the most area
     (same-ratio track, default) the window keeps the input aspect ratio and is resized back to the input size
     (free-ratio track, --ratio) the window ratio is W:H or free, the fallback when a same-ratio window would cut the head or other kept parts
     no detection model, Pillow is the only dependency
"""
import argparse
import sys
from enum import Enum

from PIL import Image, ImageDraw

# WHY: the cut line adds only a small margin to the defect box, a large margin cuts healthy parts too
DEFAULT_PAD_PX = 4
# WHY: the cut depth comes from the defect box and applicability from the keep box, a fixed cap ignores defect depth so none by default
DEFAULT_MAX_TRIM_RATIO = None
# WHY: free cuts only the chosen edge and keeps the whole other axis, the ratio follows from the result
FREE_RATIO = "free"
# WHY: integer truncation can leave a same-ratio window 1px off the panel, snap within this range
PREVIEW_SNAP_PX = 1
PREVIEW_GAP = 16
PREVIEW_DIM = 0.35
WINDOW_COLOR = (255, 255, 255)
DEFECT_COLOR = (31, 58, 104)
LINE_WIDTH = 3


class Edge(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


def parse_box(text: str) -> tuple:
    box = tuple(int(v) for v in text.split(","))
    if len(box) != 4 or box[0] >= box[2] or box[1] >= box[3]:
        raise argparse.ArgumentTypeError("box must be x0,y0,x1,y1 with x0<x1 and y0<y1")
    return box


def parse_size(text: str) -> tuple:
    width, height = (int(v) for v in text.lower().split("x"))
    return width, height


def parse_ratio(text: str):
    if text.lower() == FREE_RATIO:
        return FREE_RATIO
    try:
        unit_w, unit_h = (int(v) for v in text.split(":"))
    except ValueError:
        raise argparse.ArgumentTypeError("ratio must be W:H with positive integers, or free")
    if unit_w <= 0 or unit_h <= 0:
        raise argparse.ArgumentTypeError("ratio must be W:H with positive integers, or free")
    return unit_w, unit_h


def ratio_unit(ratio, size: tuple, free_size: tuple) -> tuple:
    """Unit of the window ratio, the same-ratio track uses the input size as the unit"""
    if ratio is None:
        return size
    if ratio == FREE_RATIO:
        return free_size
    return ratio


def union(boxes: list) -> tuple:
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def place(free_low: int, free_high: int, length: int, keep_low, keep_high):
    """Place a window of this length inside the free span, None when it cannot contain the keep span"""
    if length > free_high - free_low:
        return None
    if keep_low is None:
        return free_low + (free_high - free_low - length) // 2
    if keep_high - keep_low > length or keep_low < free_low or keep_high > free_high:
        return None
    centered = (keep_low + keep_high - length) // 2
    return min(max(centered, free_low), free_high - length)


def window_for_edge(edge: Edge, size: tuple, defect: tuple, keep, pad: int, ratio=None):
    """Largest window that removes the defect by cutting this edge, same ratio as the input when ratio is None, None if impossible"""
    width, height = size
    free = {Edge.TOP: (0, defect[3] + pad, width, height), Edge.BOTTOM: (0, 0, width, defect[1] - pad),
            Edge.LEFT: (defect[2] + pad, 0, width, height), Edge.RIGHT: (0, 0, defect[0] - pad, height)}[edge]
    free_w, free_h = free[2] - free[0], free[3] - free[1]
    if free_w <= 0 or free_h <= 0:
        return None
    unit_w, unit_h = ratio_unit(ratio, size, (free_w, free_h))
    scale = min(free_w / unit_w, free_h / unit_h)
    win_w, win_h = int(unit_w * scale), int(unit_h * scale)
    if win_w <= 0 or win_h <= 0:
        return None
    keep_x = (keep[0], keep[2]) if keep else (None, None)
    keep_y = (keep[1], keep[3]) if keep else (None, None)
    left = place(free[0], free[2], win_w, *keep_x)
    top = place(free[1], free[3], win_h, *keep_y)
    if left is None or top is None:
        return None
    # WHY: upright subjects must keep the head, so without a keep box the window sticks to the top
    #      (same-ratio windows on the top or bottom edge already touch the top, this matters for side edges and free ratios)
    if keep is None:
        top = free[1]
    return (left, top, left + win_w, top + win_h)


def window_area(window: tuple) -> int:
    return (window[2] - window[0]) * (window[3] - window[1])


def choose_window(size: tuple, defect: tuple, keep, pad: int, edges: list, ratio=None) -> tuple:
    candidates = [(edge, window_for_edge(edge, size, defect, keep, pad, ratio)) for edge in edges]
    candidates = [(edge, win) for edge, win in candidates if win]
    if not candidates:
        sys.exit("NOT_APPLICABLE: no window excludes the defect while containing the keep box")
    # WHY: for same-ratio windows, ranking by area equals ranking by width, so one area rule serves both tracks
    return max(candidates, key=lambda item: window_area(item[1]))


def fit_long_side(window: tuple, long_side: int) -> tuple:
    """Size with the window ratio and the long side set to long_side"""
    win_w, win_h = window[2] - window[0], window[3] - window[1]
    scale = long_side / max(win_w, win_h)
    return round(win_w * scale), round(win_h * scale)


def fit_into_panel(result: Image.Image, panel: tuple) -> Image.Image:
    """Fit into the preview panel keeping the ratio, so a free-ratio result is not squashed"""
    scale = min(panel[0] / result.width, panel[1] / result.height)
    fitted = (round(result.width * scale), round(result.height * scale))
    if abs(fitted[0] - panel[0]) <= PREVIEW_SNAP_PX and abs(fitted[1] - panel[1]) <= PREVIEW_SNAP_PX:
        fitted = panel
    return result.resize(fitted, Image.LANCZOS)


def render_preview(image: Image.Image, window: tuple, defects: list, result: Image.Image, path: str) -> None:
    marked = Image.blend(image, Image.new("RGB", image.size, (0, 0, 0)), 1 - PREVIEW_DIM)
    marked.paste(image.crop(window), window[:2])
    draw = ImageDraw.Draw(marked)
    draw.rectangle(window, outline=WINDOW_COLOR, width=LINE_WIDTH)
    for box in defects:
        # WHY: a light underline keeps the box visible on the dimmed area
        draw.rectangle((box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2), outline=WINDOW_COLOR, width=2)
        draw.rectangle(box, outline=DEFECT_COLOR, width=LINE_WIDTH)
        draw.line((box[0], box[1], box[2], box[3]), fill=DEFECT_COLOR, width=LINE_WIDTH)
        draw.line((box[0], box[3], box[2], box[1]), fill=DEFECT_COLOR, width=LINE_WIDTH)
    shown = fit_into_panel(result, image.size)
    sheet = Image.new("RGB", (image.width * 2 + PREVIEW_GAP, image.height), (255, 255, 255))
    sheet.paste(marked, (0, 0))
    sheet.paste(shown, (image.width + PREVIEW_GAP + (image.width - shown.width) // 2, (image.height - shown.height) // 2))
    sheet.save(path)


def trim_same_ratio(image: Image.Image, window: tuple, edge: Edge, args) -> tuple:
    trim_ratio = 1 - (window[2] - window[0]) / image.width
    report = "edge=%s window=%s trim_ratio=%.3f upscale=%.3f area_kept=%.3f" % (
        edge.value, window, trim_ratio, 1 / (1 - trim_ratio), (1 - trim_ratio) ** 2)
    if args.max_ratio is not None and trim_ratio > args.max_ratio:
        sys.exit("NOT_APPLICABLE: %s exceeds max ratio %.2f, the defect is not close enough to an edge" % (
            report, args.max_ratio))
    result = image.crop(window)
    if not args.no_resize:
        result = result.resize(args.out_size or image.size, Image.LANCZOS)
    return result, report


def trim_free_ratio(image: Image.Image, window: tuple, edge: Edge, args) -> tuple:
    """WHY: a ratio change changes the deliverable format, so report the numbers and let the user decide instead of rejecting by a loss cap"""
    win_w, win_h = window[2] - window[0], window[3] - window[1]
    target = fit_long_side(window, args.long_side or max(image.size))
    report = "track=free-ratio edge=%s window=%s ratio=%.3f kept_w=%.3f kept_h=%.3f area_kept=%.3f upscale=%.3f target=%dx%d" % (
        edge.value, window, win_w / win_h, win_w / image.width, win_h / image.height,
        win_w * win_h / (image.width * image.height), target[0] / win_w, target[0], target[1])
    result = image.crop(window)
    if not args.no_resize:
        result = result.resize(target, Image.LANCZOS)
    return result, report


def main() -> None:
    parser = argparse.ArgumentParser(description="trim an edge defect and resize back")
    parser.add_argument("in_path")
    parser.add_argument("out_path")
    parser.add_argument("--defect", type=parse_box, action="append", required=True, help="x0,y0,x1,y1, repeatable")
    parser.add_argument("--keep", type=parse_box, help="box that must stay inside the frame, e.g. the face")
    parser.add_argument("--edge", choices=[e.value for e in Edge], help="force one edge instead of automatic choice")
    parser.add_argument("--pad", type=int, default=DEFAULT_PAD_PX)
    parser.add_argument("--max-ratio", type=float, default=DEFAULT_MAX_TRIM_RATIO,
                        help="optional loss cap of one side, default is no cap")
    parser.add_argument("--out-size", type=parse_size, help="WxH, default is the input size")
    # WHY: with final upscaling chosen, skip the resize here, finalize.py reaches the target size by 4x upscaling then downscaling
    parser.add_argument("--no-resize", action="store_true", help="keep the cropped window size, for a later super-resolution step")
    parser.add_argument("--ratio", type=parse_ratio,
                        help="free-ratio track, W:H or free, default keeps the input ratio")
    parser.add_argument("--long-side", type=int, help="free-ratio track, long side of the restored size, default is the input long side")
    parser.add_argument("--preview", help="save a before/after sheet here")
    args = parser.parse_args()
    # WHY: without a cap, the keep box is what protects the composition on the same-ratio track, so one of them is required
    if not args.ratio and args.keep is None and args.max_ratio is None:
        parser.error("same-ratio track needs --keep (box of what must stay in frame) or --max-ratio")
    if args.ratio and args.out_size:
        parser.error("--out-size fixes the input ratio, use --long-side with --ratio")
    if args.long_side is not None and (not args.ratio or args.long_side <= 0):
        parser.error("--long-side needs --ratio and a positive value")

    image = Image.open(args.in_path).convert("RGB")
    defect = union(args.defect)
    edges = [Edge(args.edge)] if args.edge else list(Edge)
    edge, window = choose_window(image.size, defect, args.keep, args.pad, edges, args.ratio)
    trim = trim_free_ratio if args.ratio else trim_same_ratio
    result, report = trim(image, window, edge, args)
    result.save(args.out_path)
    if args.preview:
        render_preview(image, window, args.defect, result, args.preview)
    print(args.out_path, report)


if __name__ == "__main__":
    main()
