"""Tunable constants shared by every module (no magic numbers elsewhere)."""

# --- rasterization ---------------------------------------------------------
MASK_SUBSAMPLE = 4          # coverage samples per pixel axis for anti-aliased masks
BBOX_PAD = 6                # px of slack around a part so blurs/lines are not cut

# --- form shading ----------------------------------------------------------
POISSON_MAX_SIDE = 220      # inflation is solved on a grid this large, then upsampled
RIBBON_FIELD_SCALE = 0.5    # ribbon normal fields are smooth, half resolution is enough
RIBBON_MAX_SEGMENTS = 48    # axis is decimated to this many segments for field lookup
DEFAULT_LIGHT = (-0.48, -0.58, 0.66)   # toward the light: upper-left, in front

# --- line art --------------------------------------------------------------
LINE_STEP = 2.5             # px between samples when a stroke becomes a ribbon
LINE_MIN_WIDTH = 0.35       # px, thinnest point of a tapered stroke

# --- painterly pass --------------------------------------------------------
PAINT_RADII = (26, 13, 6, 3)     # brush radii at the reference size, large to small
PAINT_REFERENCE_SIDE = 1024      # short side the radii above are tuned for
PAINT_BLUR_FACTOR = 0.4          # reference blur sigma = radius * factor
PAINT_ERROR_THRESHOLD = 14.0     # mean abs RGB error (0-255) that triggers a stroke
PAINT_COLOR_TOLERANCE = 54.0     # summed RGB drift that ends a stroke (stay in one color area)
PAINT_MAX_STROKE_STEPS = 10      # control points per stroke
PAINT_MIN_STROKE_STEPS = 3
PAINT_CURVATURE_FILTER = 0.6     # 1 = follow field exactly, lower = straighter strokes
PAINT_COLOR_JITTER = 5.0         # per-stroke value jitter (0-255), gives broken color
PAINT_RELIEF = 0.15              # strength of impasto lighting
PAINT_BRISTLE = 0.022            # bristle streak height relative to stroke height
PAINT_FIDELITY = 0.75            # how strongly stray brushwork is pulled back to the reference
PAINT_DETAIL_BLEND = 0.40        # share of the reference kept in fully focused areas

# --- output ----------------------------------------------------------------
DEFAULT_SIZE = (1024, 1280)      # width, height
