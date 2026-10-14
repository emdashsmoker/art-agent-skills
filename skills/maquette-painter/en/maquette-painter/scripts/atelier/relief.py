"""Relief: a height field built by sweeping ellipsoids along construction lines.

Why: a figure must stay anatomically consistent from any angle. Artists solve this with a
construction mannequin (masses on a skeleton). This is the same idea in numbers: every mass is
an ellipsoid swept along a bone; the nearest surface per pixel becomes a height field.
No mesh, no external 3D tool. The height field then yields silhouettes, overlaps,
form shading and line art.

Device space: x right, y down, z toward the viewer (larger z = nearer).
"""
import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

EMPTY = -1.0e6
STAMP_ROUNDNESS = 0.8        # along-axis radius of each stamp relative to its thinner cross radius
STAMP_SPACING = 0.12         # stamp spacing relative to the along-axis radius
STEP_REACH = 0.004           # head units over which a depth step is measured for overlap lines


class Relief:
    def __init__(self, width, height):
        self.W, self.H = int(width), int(height)
        self.z = np.full((self.H, self.W), EMPTY, np.float32)
        self.part = np.zeros((self.H, self.W), np.int16)
        self.parts = {"": 0}
        self.flow = None             # (H, W, 2) direction of the sweep that owns each pixel (hair strands follow it)

    def part_id(self, name):
        if name not in self.parts:
            self.parts[name] = len(self.parts)
        return self.parts[name]

    def ellipsoid(self, centre, axes, radii, part, flow=None):
        """Stamp one ellipsoid. axes: 3x3 with unit axis vectors as columns (device space)."""
        pid = self.part_id(part) if isinstance(part, str) else part
        radii = np.maximum(np.asarray(radii, np.float64), 0.3)
        axes = np.asarray(axes, np.float64)
        spread = (axes * radii ** 2) @ axes.T
        ex, ey = np.sqrt(max(spread[0, 0], 1e-9)), np.sqrt(max(spread[1, 1], 1e-9))
        x0, x1 = int(np.floor(centre[0] - ex)), int(np.ceil(centre[0] + ex)) + 1
        y0, y1 = int(np.floor(centre[1] - ey)), int(np.ceil(centre[1] + ey)) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, self.W), min(y1, self.H)
        if x1 <= x0 or y1 <= y0:
            return
        m = (axes / radii ** 2) @ axes.T
        dx = (np.arange(x0, x1) - centre[0])[None, :]
        dy = (np.arange(y0, y1) - centre[1])[:, None]
        a = m[2, 2]
        b = 2 * (m[0, 2] * dx + m[1, 2] * dy)
        c = m[0, 0] * dx * dx + 2 * m[0, 1] * dx * dy + m[1, 1] * dy * dy - 1
        disc = b * b - 4 * a * c
        hit = disc > 0
        if not hit.any():
            return
        z = centre[2] + (-b + np.sqrt(np.where(hit, disc, 0))) / (2 * a)
        zs = self.z[y0:y1, x0:x1]
        win = hit & (z > zs)
        zs[win] = z[win]
        self.part[y0:y1, x0:x1][win] = pid
        if flow is not None:
            if self.flow is None:
                self.flow = np.zeros((self.H, self.W, 2), np.float32)
            self.flow[y0:y1, x0:x1][win] = flow

    def sweep(self, points, lateral, sagittal, width, front, back=None, part="",
              roundness=STAMP_ROUNDNESS, spacing=STAMP_SPACING, flow=False):
        """Sweep an elliptical cross-section along a path.

        points    (n, 3) device-space path
        lateral   sideways axis of the cross-section, (3,) or (n, 3)
        sagittal  front axis of the cross-section, (3,) or (n, 3)
        width     half-width along lateral
        front / back   half-depths toward +sagittal / -sagittal (back defaults to front)
        """
        pts = np.asarray(points, np.float64)
        n = len(pts)
        lat = np.broadcast_to(np.asarray(lateral, np.float64), (n, 3))
        sag = np.broadcast_to(np.asarray(sagittal, np.float64), (n, 3))
        width = np.broadcast_to(np.asarray(width, np.float64), (n,))
        front = np.broadcast_to(np.asarray(front, np.float64), (n,))
        back = front if back is None else np.broadcast_to(np.asarray(back, np.float64), (n,))
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)])
        if s[-1] < 1e-6:
            return
        keep = np.concatenate([[True], seg > 1e-9])          # PCHIP needs strictly increasing s
        pts, lat, sag, width, front, back, s = (v[keep] for v in (pts, lat, sag, width, front, back, s))
        n = len(pts)
        # Stamps are spaced by the local thickness, so a sweep that tapers stays smooth to its thin end.
        probe = np.linspace(0, s[-1], 240)
        thin = np.minimum(np.interp(probe, s, width), (np.interp(probe, s, front) + np.interp(probe, s, back)) / 2)
        step = np.maximum(roundness * thin * spacing, 0.75)
        count_along = np.concatenate([[0], np.cumsum((probe[1] - probe[0]) / ((step[1:] + step[:-1]) / 2))])
        count = max(int(count_along[-1]) + 1, 2)
        t = np.interp(np.linspace(0, count_along[-1], count), count_along, probe)
        if n > 2:
            pos = PchipInterpolator(s, pts, axis=0)(t)
            w, f, bk = (PchipInterpolator(s, v)(t) for v in (width, front, back))
        else:
            pos = np.stack([np.interp(t, s, pts[:, k]) for k in range(3)], axis=1)
            w, f, bk = (np.interp(t, s, v) for v in (width, front, back))
        lat_i = np.stack([np.interp(t, s, lat[:, k]) for k in range(3)], axis=1)
        sag_i = np.stack([np.interp(t, s, sag[:, k]) for k in range(3)], axis=1)
        tangent = np.gradient(pos, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
        pid = self.part_id(part) if isinstance(part, str) else part
        for i in range(count):
            tan = tangent[i]
            u = lat_i[i] - (lat_i[i] @ tan) * tan
            if np.linalg.norm(u) < 1e-6:
                continue
            u /= np.linalg.norm(u)
            v = sag_i[i] - (sag_i[i] @ tan) * tan - (sag_i[i] @ u) * u
            if np.linalg.norm(v) < 1e-6:
                continue
            v /= np.linalg.norm(v)
            depth = max((f[i] + bk[i]) / 2, 0.3)
            centre = pos[i] + v * (f[i] - bk[i]) / 2
            along = max(roundness * min(w[i], depth), 0.5)
            direction = tan[:2] / (np.linalg.norm(tan[:2]) + 1e-6) if flow else None
            self.ellipsoid(centre, np.stack([u, v, tan], axis=1), (max(w[i], 0.3), depth, along), pid, direction)

    def surface(self, grid, part, spacing=0.7, strip=24):
        """Stamp a smooth closed surface given as an (n, m, 3) grid of device-space points.

        The grid is refined until neighbouring samples are closer than a pixel and then written to the
        height field point by point (nearest wins), so the surface can carry fine modelling such as a face.
        """
        pid = self.part_id(part) if isinstance(part, str) else part
        grid = np.asarray(grid, np.float32)
        n, m = grid.shape[:2]
        x0, y0 = np.floor(grid[..., :2].min(axis=(0, 1))).astype(int) - 1
        x1, y1 = np.ceil(grid[..., :2].max(axis=(0, 1))).astype(int) + 2
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, self.W), min(y1, self.H)
        if x1 <= x0 or y1 <= y0:
            return
        width, height = x1 - x0, y1 - y0
        buf = np.full(width * height, EMPTY, np.float32)
        for start in range(0, n - 1, strip):
            part_grid = grid[start:start + strip + 1]
            rows = part_grid.shape[0]
            step_u = float(np.linalg.norm(np.diff(part_grid[..., :2], axis=1), axis=2).max())
            step_v = float(np.linalg.norm(np.diff(part_grid[..., :2], axis=0), axis=2).max())
            dense = cv2.resize(part_grid, (max(int(m * step_u / spacing), m), max(int(rows * step_v / spacing), rows)),
                               interpolation=cv2.INTER_LINEAR).reshape(-1, 3)
            ix, iy = np.rint(dense[:, 0]).astype(np.int32) - x0, np.rint(dense[:, 1]).astype(np.int32) - y0
            ok = (ix >= 0) & (ix < width) & (iy >= 0) & (iy < height)
            np.maximum.at(buf, iy[ok] * width + ix[ok], dense[ok, 2])
        buf = buf.reshape(height, width)
        kernel = np.ones((3, 3), np.uint8)                      # pinholes between samples take their neighbours' height
        closed = cv2.erode(cv2.dilate(buf, kernel), kernel)
        buf = np.where(buf > EMPTY / 2, buf, closed)
        zs = self.z[y0:y1, x0:x1]
        win = buf > zs
        zs[win] = buf[win]
        self.part[y0:y1, x0:x1][win] = pid

    def smooth_union(self, other, blend):
        """Join another relief into this one with a fillet of `blend` px where the two surfaces meet.

        A hard maximum leaves a crease along the line where two forms intersect. The polynomial smooth
        maximum lifts the surface by up to blend/4 near that line and is exact elsewhere, so a breast or
        a buttock grows out of the torso the way soft tissue does.
        """
        a, b = self.z, other.z
        h = np.clip(0.5 + 0.5 * (b - a) / blend, 0, 1)
        joined = a * (1 - h) + b * h + blend * h * (1 - h)
        both = (a > EMPTY / 2) & (b > EMPTY / 2)
        self.z = np.where(both, joined, np.maximum(a, b)).astype(np.float32)
        take = b > a
        for name, pid in other.parts.items():
            if name:
                mine = self.part_id(name)
                self.part[take & (other.part == pid)] = mine

    # ----- results -----
    def mask(self):
        return self.z > EMPTY / 2

    def smooth(self, sigma_space, sigma_depth):
        """Blend creases between touching masses while keeping real depth steps (bilateral)."""
        inside = self.mask()
        if not inside.any():
            return
        floor = float(self.z[inside].min()) - sigma_depth * 4
        work = np.where(inside, self.z, floor).astype(np.float32)
        d = int(max(sigma_space * 2.5, 3)) | 1
        work = cv2.bilateralFilter(work, d, float(sigma_depth), float(sigma_space))
        self.z = np.where(inside, work, EMPTY).astype(np.float32)

    def _extended(self):
        """Height field continued a little past the silhouette, falling away, so edges get finite gradients."""
        inside = self.mask()
        filled = np.where(inside, self.z, 0).astype(np.float32)
        weight = inside.astype(np.float32)
        for _ in range(3):
            num = cv2.GaussianBlur(filled, (0, 0), 2.0)
            den = cv2.GaussianBlur(weight, (0, 0), 2.0)
            spread = num / np.maximum(den, 1e-4)
            grow = (weight < 0.5) & (den > 1e-3)
            filled[grow] = spread[grow] - 2.5
            weight[grow] = 1.0
        return filled, inside

    def normals(self, blur=1.0):
        filled, inside = self._extended()
        if not inside.any():
            n = np.zeros((self.H, self.W, 3), np.float32)
            n[..., 2] = 1
            return n
        if blur:
            filled = cv2.GaussianBlur(filled, (0, 0), blur)
        gy, gx = np.gradient(filled)
        n = np.dstack([-gx, -gy, np.ones_like(filled)])
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        return n.astype(np.float32)

    def _falling(self, fall=2.0):
        """Height field continued outside the silhouette, dropping `fall` px of depth per px of distance.

        A form keeps curving away past its outline. Treating the outside as missing would make every
        rim look like the bottom of a bowl, so occlusion reads the continued surface instead.
        """
        inside = self.mask()
        outside = (~inside).astype(np.uint8)
        dist, labels = cv2.distanceTransformWithLabels(outside, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        ys, xs = np.nonzero(outside == 0)
        lookup = np.zeros(labels.max() + 1, np.float32)
        lookup[labels[ys, xs]] = self.z[ys, xs]
        return np.where(inside, self.z, lookup[labels] - dist * fall).astype(np.float32), inside

    def occlusion(self, unit):
        """Ambient occlusion 0..1: how deep a point sits below its surroundings (creases, armpits, between limbs)."""
        if not self.mask().any():
            return np.zeros((self.H, self.W), np.float32)
        z, inside = self._falling()
        total = np.zeros((self.H, self.W), np.float32)
        for sigma, depth, gain in ((0.035 * unit, 0.02 * unit, 0.55), (0.11 * unit, 0.07 * unit, 0.6)):
            near = cv2.GaussianBlur(z, (0, 0), sigma)
            total += np.clip((near - z) / depth, 0, 1) * gain
        return np.clip(total, 0, 1) * inside

    def lines(self, unit, silhouette=1.0, overlap=0.8, crease=0.5, width=1.3, part_pairs=None,
              crease_mask=None, family=None):
        """Line art from the relief: outer silhouette, overlaps (depth steps) and creases (valleys).

        unit        pixels per head unit, sets what counts as a 'step'
        part_pairs   set of (id, id) boundaries that always get a line (fingers side by side)
        crease_mask  where crease lines are allowed (skin yes, hair no)
        """
        inside = self.mask()
        z = np.where(inside, self.z, 0)
        alpha = np.zeros((self.H, self.W), np.float32)
        kernel = np.ones((3, 3), np.uint8)
        if silhouette:
            edge = inside & (cv2.erode(inside.astype(np.uint8), kernel) == 0)
            alpha = np.maximum(alpha, edge * silhouette)
        if overlap:
            zf = z.astype(np.float32)
            # A step is measured across a small distance, not one pixel: where a jaw or a breast turns under
            # before meeting the form behind, the jump is spread over a few pixels at high resolution.
            reach = 2 * max(int(round(STEP_REACH * unit)), 1) + 1
            wide = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (reach, reach))
            rise = cv2.dilate(zf, wide) - zf
            fall = zf - cv2.erode(np.where(inside, zf, 1e6).astype(np.float32), wide)
            # A real overlap is one-sided: a jump up to the nearer form while this surface runs on smoothly.
            # A steep but continuous slope rises and falls by similar amounts and is not a line.
            step = (rise > 0.04 * unit) & (rise > 3.0 * np.abs(fall) + 0.01 * unit)
            # Within one part (the modelling of a face, a torso) only a big jump earns a line;
            # small steps there are form, and belong to the shading.
            ids = (self.part if family is None else family).astype(np.float32)   # family: parts that count as one form
            mixed = (cv2.dilate(ids, kernel) != ids) | (cv2.erode(ids, kernel) != ids)
            step &= mixed | (rise > 0.12 * unit)
            step &= inside & (cv2.erode(inside.astype(np.uint8), kernel) > 0)
            alpha = np.maximum(alpha, step * overlap)
        if part_pairs:
            pid = self.part
            for shift in ((0, 1), (1, 0)):
                other = np.roll(pid, shift, axis=(0, 1))
                lo, hi = np.minimum(pid, other), np.maximum(pid, other)
                hit = np.zeros_like(inside)
                for a, b in part_pairs:
                    hit |= (lo == min(a, b)) & (hi == max(a, b))
                alpha = np.maximum(alpha, hit * overlap)
        if crease:
            sigma = 0.02 * unit
            soft = cv2.GaussianBlur(z.astype(np.float32), (0, 0), sigma)
            wide = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), sigma)
            valley = (soft / np.maximum(wide, 1e-3) - z) * (wide > 0.97)
            # Creases are where forms meet without a jump (under a breast, between toes); keep clear of
            # overlaps and the outline, which already have their own line.
            reach = int(sigma * 3) | 1
            busy = cv2.dilate((alpha > 0).astype(np.uint8), np.ones((reach, reach), np.uint8)) > 0
            fold = np.clip((valley - 0.006 * unit) / (0.006 * unit), 0, 1) * crease * inside * ~busy
            if crease_mask is not None:
                fold = fold * crease_mask
            alpha = np.maximum(alpha, fold)
        return thicken(alpha, width)

    def cast_shadow(self, light_direction, reach, steps=28, bias=1.5, softness=1.5):
        """Self-shadowing of the relief: march from every pixel toward the light across the height field.

        light_direction  unit vector pointing to the light (x right, y down, z toward viewer)
        reach            how far (pixels) an occluder can throw its shadow
        """
        inside = self.mask()
        lx, ly, lz = (float(v) for v in light_direction)
        flat = np.hypot(lx, ly)
        if flat < 1e-3 or not inside.any():
            return np.zeros((self.H, self.W), np.float32)
        z = np.where(inside, self.z, EMPTY).astype(np.float32)
        shadow = np.zeros((self.H, self.W), np.float32)
        step = reach / steps
        for k in range(1, steps + 1):
            dist = k * step
            shift = np.float32([[1, 0, -lx / flat * dist], [0, 1, -ly / flat * dist]])
            toward = cv2.warpAffine(z, shift, (self.W, self.H), flags=cv2.INTER_NEAREST, borderValue=EMPTY)
            ray = self.z + dist * lz / flat + bias
            shadow = np.maximum(shadow, np.clip((toward - ray) / (0.5 * step + 1e-3), 0, 1))
        shadow *= inside
        return cv2.GaussianBlur(shadow, (0, 0), softness) if softness else shadow


def thicken(edges, width):
    """Turn a thin edge map into anti-aliased lines of roughly `width` pixels."""
    size = max(int(round(width)), 1)
    if size > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        edges = cv2.dilate(edges, kernel)
    return np.clip(cv2.GaussianBlur(edges, (0, 0), 0.8) * 1.25, 0, 1)
