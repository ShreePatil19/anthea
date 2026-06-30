"""Shared geometry, colour, and smoothing helpers."""
import math
import numpy as np
import cv2


# ---------------------------------------------------------------------------
# Colour helpers (all in BGR, OpenCV convention)
# ---------------------------------------------------------------------------

def hsv_to_bgr(h, s, v):
    """h 0..179, s 0..255, v 0..255 -> (B, G, R) tuple of ints."""
    arr = np.array([[[int(h), int(s), int(v)]]], dtype=np.uint8)
    bgr = cv2.cvtColor(arr, cv2.COLOR_HSV2BGR)[0, 0]
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))


def bgr_to_hsv(b, g, r):
    arr = np.array([[[int(b), int(g), int(r)]]], dtype=np.uint8)
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)[0, 0]
    return (int(hsv[0]), int(hsv[1]), int(hsv[2]))


def lerp_hsv(bgr1, bgr2, t):
    """Interpolate two BGR colours via HSV for natural-looking blends."""
    h1, s1, v1 = bgr_to_hsv(*bgr1)
    h2, s2, v2 = bgr_to_hsv(*bgr2)
    # Shortest path around the hue circle
    dh = h2 - h1
    if dh > 90:
        dh -= 180
    elif dh < -90:
        dh += 180
    h = (h1 + dh * t) % 180
    s = s1 + (s2 - s1) * t
    v = v1 + (v2 - v1) * t
    return hsv_to_bgr(h, s, v)


def lerp_colour(c1, c2, t):
    """Linear interpolate two BGR tuples."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def lerp(a, b, t):
    return a + (b - a) * t


def bezier_cubic(p0, p1, p2, p3, steps=40):
    """Return an array of points along a cubic Bezier curve."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts


def bezier_quadratic(p0, p1, p2, steps=24):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**2*p0[0] + 2*u*t*p1[0] + t**2*p2[0]
        y = u**2*p0[1] + 2*u*t*p1[1] + t**2*p2[1]
        pts.append((x, y))
    return pts


def rotate_point(x, y, cx, cy, angle):
    """Rotate point (x,y) around (cx,cy) by angle radians."""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dx, dy = x - cx, y - cy
    return (cx + dx * cos_a - dy * sin_a,
            cy + dx * sin_a + dy * cos_a)


def rotate_pts(pts, cx, cy, angle):
    return [rotate_point(x, y, cx, cy, angle) for x, y in pts]


def scale_polygon(pts, cx, cy, factor):
    """Scale a list of (x,y) points around (cx,cy)."""
    return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in pts]


def pts_to_np(pts):
    """Convert list of (x,y) to int32 numpy array suitable for cv2.fillPoly."""
    return np.array([[int(round(x)), int(round(y))] for x, y in pts],
                    dtype=np.int32)


def curved_petal_polygon(cx, cy, length, width, angle, curvature=0.3, n_pts=32):
    """
    Return a list of (x,y) points describing a curved petal outline.

    The petal grows along +y from (cx, cy) before rotation. curvature bows
    the sides outward (positive) or inward (negative). Returns 2*n_pts points.
    """
    half = n_pts // 2
    left_side = []
    right_side = []
    for i in range(half + 1):
        t = i / half
        # Longitudinal position along petal axis
        along = t * length
        # Width envelope: wide at base, tapers to tip with slight notch
        w_env = math.sin(t * math.pi) * width * (1.0 - 0.18 * (t ** 3))
        # Side curvature: bow outward, stronger near middle
        bow = curvature * length * math.sin(t * math.pi) * 0.5
        left_side.append((cx - w_env + bow, cy - along))
        right_side.append((cx + w_env - bow, cy - along))
    # Build outline: up left side, tip, back down right side
    tip_x = cx + curvature * 0.05 * width
    tip_y = cy - length
    outline = left_side + [(tip_x, tip_y)] + list(reversed(right_side))
    # Rotate to requested angle
    return rotate_pts(outline, cx, cy, angle)


def wavy_petal_polygon(cx, cy, length, width, angle, waves=5, amp=0.06, n_pts=48):
    """
    Like curved_petal_polygon but with wavy edges for spider lily tepals.
    amp is relative to width.
    """
    half = n_pts // 2
    left_side = []
    right_side = []
    for i in range(half + 1):
        t = i / half
        along = t * length
        # Very narrow tepals, width tapers aggressively
        w_env = math.sin(t ** 0.6 * math.pi) * width * 0.55
        # Wavy edge
        wave = amp * width * math.sin(t * waves * math.pi * 2)
        left_side.append((cx - w_env + wave, cy - along))
        right_side.append((cx + w_env + wave, cy - along))
    tip_x = cx
    tip_y = cy - length
    outline = left_side + [(tip_x, tip_y)] + list(reversed(right_side))
    return rotate_pts(outline, cx, cy, angle)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def filled_poly(canvas, pts, colour, aa=True):
    np_pts = pts_to_np(pts)
    cv2.fillPoly(canvas, [np_pts], colour)


def draw_poly_outline(canvas, pts, colour, thickness=1):
    np_pts = pts_to_np(pts).reshape((-1, 1, 2))
    cv2.polylines(canvas, [np_pts], True, colour, thickness, cv2.LINE_AA)


def gradient_circle(canvas, cx, cy, radius, inner_bgr, outer_bgr, steps=12):
    """Filled circle with a radial gradient from centre to edge."""
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        colour = lerp_colour(inner_bgr, outer_bgr, 1 - t)
        cv2.circle(canvas, (int(cx), int(cy)), r, colour, -1, cv2.LINE_AA)


def gradient_circle_hsv(canvas, cx, cy, radius, inner_bgr, outer_bgr, steps=18):
    """Radial gradient using HSV interpolation."""
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        colour = lerp_hsv(inner_bgr, outer_bgr, 1 - t)
        cv2.circle(canvas, (int(cx), int(cy)), r, colour, -1, cv2.LINE_AA)


def blend_layer(base, overlay, alpha):
    """Alpha-blend overlay onto base in place. alpha in 0..1."""
    cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0, base)


def apply_gradient_to_poly(canvas, pts, bgr_base, bgr_tip, axis='y'):
    """
    Fill a polygon with a linear gradient along the given axis.
    Splits into thin horizontal strips.
    """
    np_pts = pts_to_np(pts)
    x_min = np_pts[:, 0].min()
    x_max = np_pts[:, 0].max()
    y_min = np_pts[:, 1].min()
    y_max = np_pts[:, 1].max()
    if y_max <= y_min or x_max <= x_min:
        filled_poly(canvas, pts, bgr_base)
        return
    # Create mask
    mask = np.zeros(canvas.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [np_pts], 255)
    # Build gradient image for the bounding rect
    h = y_max - y_min + 1
    w = x_max - x_min + 1
    if h <= 0 or w <= 0:
        return
    grad = np.zeros((canvas.shape[0], canvas.shape[1], 3), dtype=np.uint8)
    for row in range(y_min, y_max + 1):
        t = (row - y_min) / (y_max - y_min) if y_max > y_min else 0
        colour = lerp_hsv(bgr_base, bgr_tip, t)
        grad[row, x_min:x_max + 1] = colour
    # Apply mask
    mask3 = cv2.merge([mask, mask, mask])
    canvas_region = canvas.copy()
    np.copyto(canvas, grad, where=(mask3 > 0))


def apply_gradient_to_poly_dir(canvas, pts, bgr_base, bgr_tip, angle):
    """
    Fill a polygon with a gradient along the flower-direction angle.
    angle=0 is up, pi/2 is right (screen y increases downward).
    bgr_base at the near-center end, bgr_tip at the far end.
    Efficient: operates only on the polygon bounding box.
    """
    np_pts = pts_to_np(pts)
    if len(np_pts) < 3:
        return
    h_can, w_can = canvas.shape[:2]
    y_min = max(0, int(np_pts[:, 1].min()))
    y_max = min(h_can - 1, int(np_pts[:, 1].max()))
    x_min = max(0, int(np_pts[:, 0].min()))
    x_max = min(w_can - 1, int(np_pts[:, 0].max()))
    if y_max < y_min or x_max < x_min:
        return

    box_h = y_max - y_min + 1
    box_w = x_max - x_min + 1
    offset_pts = np_pts.copy()
    offset_pts[:, 0] -= x_min
    offset_pts[:, 1] -= y_min
    mask = np.zeros((box_h, box_w), dtype=np.uint8)
    cv2.fillPoly(mask, [offset_pts], 255)
    pixels_in = mask > 0
    if not pixels_in.any():
        return

    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    ys = (np.arange(box_h, dtype=np.float32) + y_min)[:, np.newaxis]
    xs = (np.arange(box_w, dtype=np.float32) + x_min)[np.newaxis, :]
    # Projection increases from near-center (base) to far-from-center (tip)
    proj = xs * sin_a + ys * (-cos_a)

    relevant = proj[pixels_in]
    p_min = float(relevant.min())
    p_max = float(relevant.max())
    if p_max <= p_min:
        box = canvas[y_min:y_max + 1, x_min:x_max + 1]
        box[pixels_in] = bgr_base
        return

    t_map = np.clip((proj - p_min) / (p_max - p_min), 0.0, 1.0)
    b1, g1, r1 = float(bgr_base[0]), float(bgr_base[1]), float(bgr_base[2])
    b2, g2, r2 = float(bgr_tip[0]), float(bgr_tip[1]), float(bgr_tip[2])
    b_ch = np.clip(b1 + (b2 - b1) * t_map, 0, 255).astype(np.uint8)
    g_ch = np.clip(g1 + (g2 - g1) * t_map, 0, 255).astype(np.uint8)
    r_ch = np.clip(r1 + (r2 - r1) * t_map, 0, 255).astype(np.uint8)
    grad_patch = np.stack([b_ch, g_ch, r_ch], axis=2)
    box = canvas[y_min:y_max + 1, x_min:x_max + 1]
    np.copyto(box, grad_patch, where=pixels_in[:, :, np.newaxis])


def apply_gradient_radial(canvas, pts, bgr_inner, bgr_outer, cx, cy):
    """
    Fill a polygon with a radial gradient based on distance from (cx, cy).
    bgr_inner at the closest point to center, bgr_outer at the farthest.
    """
    np_pts = pts_to_np(pts)
    if len(np_pts) < 3:
        return
    h_can, w_can = canvas.shape[:2]
    y_min = max(0, int(np_pts[:, 1].min()))
    y_max = min(h_can - 1, int(np_pts[:, 1].max()))
    x_min = max(0, int(np_pts[:, 0].min()))
    x_max = min(w_can - 1, int(np_pts[:, 0].max()))
    if y_max < y_min or x_max < x_min:
        return

    box_h = y_max - y_min + 1
    box_w = x_max - x_min + 1
    offset_pts = np_pts.copy()
    offset_pts[:, 0] -= x_min
    offset_pts[:, 1] -= y_min
    mask = np.zeros((box_h, box_w), dtype=np.uint8)
    cv2.fillPoly(mask, [offset_pts], 255)
    pixels_in = mask > 0
    if not pixels_in.any():
        return

    ys = (np.arange(box_h, dtype=np.float32) + y_min)[:, np.newaxis]
    xs = (np.arange(box_w, dtype=np.float32) + x_min)[np.newaxis, :]
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)

    relevant = dist[pixels_in]
    d_min = float(relevant.min())
    d_max = float(relevant.max())
    if d_max <= d_min:
        box = canvas[y_min:y_max + 1, x_min:x_max + 1]
        box[pixels_in] = bgr_inner
        return

    t_map = np.clip((dist - d_min) / (d_max - d_min), 0.0, 1.0)
    b1, g1, r1 = float(bgr_inner[0]), float(bgr_inner[1]), float(bgr_inner[2])
    b2, g2, r2 = float(bgr_outer[0]), float(bgr_outer[1]), float(bgr_outer[2])
    b_ch = np.clip(b1 + (b2 - b1) * t_map, 0, 255).astype(np.uint8)
    g_ch = np.clip(g1 + (g2 - g1) * t_map, 0, 255).astype(np.uint8)
    r_ch = np.clip(r1 + (r2 - r1) * t_map, 0, 255).astype(np.uint8)
    grad_patch = np.stack([b_ch, g_ch, r_ch], axis=2)
    box = canvas[y_min:y_max + 1, x_min:x_max + 1]
    np.copyto(box, grad_patch, where=pixels_in[:, :, np.newaxis])


# ---------------------------------------------------------------------------
# Exponential Moving Average (adaptive)
# ---------------------------------------------------------------------------

class EMA:
    """Adaptive EMA: faster when values change quickly."""

    def __init__(self, alpha_base=0.15, alpha_fast=0.45, threshold=20.0):
        self.alpha_base = alpha_base
        self.alpha_fast = alpha_fast
        self.threshold = threshold
        self._value = None

    def update(self, new_val):
        if self._value is None:
            self._value = new_val
            return self._value
        diff = abs(new_val - self._value) if not hasattr(new_val, '__len__') else 0
        alpha = self.alpha_fast if diff > self.threshold else self.alpha_base
        if hasattr(new_val, '__len__'):
            self._value = tuple(
                self._value[i] + self.alpha_base * (new_val[i] - self._value[i])
                for i in range(len(new_val))
            )
        else:
            self._value = self._value + alpha * (new_val - self._value)
        return self._value

    @property
    def value(self):
        return self._value

    def reset(self):
        self._value = None
