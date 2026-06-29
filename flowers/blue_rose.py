"""
Blue rose renderer.
Viewed from slightly above: overlapping cupped petals in concentric rings.
Highlights stay vivid cerulean blue, never white.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, scale_polygon, apply_gradient_to_poly,
    lerp_colour, lerp_hsv, hsv_to_bgr,
    gradient_circle_hsv, curved_petal_polygon,
)

# Vivid cobalt blue palette
DEEP    = hsv_to_bgr(118, 252, 138)   # deep indigo shadow
MID     = hsv_to_bgr(116, 240, 198)   # medium cobalt
EDGE    = hsv_to_bgr(112, 200, 248)   # cerulean lighter edge
SHADOW  = hsv_to_bgr(124, 255,  32)   # near-black navy shadow
SEPAL   = hsv_to_bgr( 80, 170,  78)
SEPAL_D = hsv_to_bgr( 76, 190,  40)


def _petal_pts(cx, cy, r_base, length, half_w, angle, n=30):
    """
    Rose petal from r_base outward. Wider in the upper half (cupped profile).
    Both sides traced independently so the polygon closes at tip and base.
    """
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    perp_x = cos_a
    perp_y = sin_a
    bx = cx + sin_a * r_base
    by = cy - cos_a * r_base
    pts = []
    for i in range(n + 1):
        t = i / n
        # Cupped rose profile: narrows at base, broad from 25% to 75%, tapers to tip
        w = half_w * math.sin(min(t * 2.0, math.pi))
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts.append((sx - perp_x * w, sy - perp_y * w))
    for i in range(n, -1, -1):
        t = i / n
        w = half_w * math.sin(min(t * 2.0, math.pi))
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts.append((sx + perp_x * w, sy + perp_y * w))
    return pts


def _draw_petal(canvas, cx, cy, r_base, length, half_w, angle,
                c_base, c_mid, c_shadow, c_hilight):
    pts = _petal_pts(cx, cy, r_base, length, half_w, angle)

    # Dark shadow ring: scaled outward from flower centre
    shadow = [(cx + (x - cx) * 1.06, cy + (y - cy) * 1.06) for x, y in pts]
    cv2.fillPoly(canvas, [pts_to_np(shadow)], c_shadow)

    # Main petal fill with gradient base to mid
    apply_gradient_to_poly(canvas, pts, c_base, c_mid)

    # Highlight: a softer, subtly lighter blue band toward the upper petal face.
    # Applied with addWeighted so it blends rather than overpainting opaquely.
    hi = _petal_pts(cx, cy, r_base + length * 0.32, length * 0.52,
                    max(4, int(half_w * 0.52)), angle)
    hi_overlay = np.zeros_like(canvas)
    cv2.fillPoly(hi_overlay, [pts_to_np(hi)], c_hilight)
    cv2.addWeighted(canvas, 1.0, hi_overlay, 0.42, 0, canvas)


def _sepal(canvas, cx, cy, radius):
    for i in range(5):
        angle = 2 * math.pi * i / 5 + math.pi / 5
        pts = curved_petal_polygon(cx, cy, int(radius * 1.28),
                                   int(radius * 0.24), angle,
                                   curvature=0.06, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.05))], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


# Ring spec: (n_petals, r_base_frac, length_frac, half_w_frac, bloom_thresh, rot)
# Golden angle (2.399 rad = 137.5 deg) rotation per ring creates organic spiral.
_GA = 2.3998  # golden angle in radians
RINGS = [
    (11, 0.44, 0.58, 0.46, 0.00, 0.000),         # outermost
    ( 9, 0.28, 0.48, 0.42, 0.08, _GA),            # 137.5 deg
    ( 7, 0.15, 0.36, 0.38, 0.26, _GA * 2),        # 275 deg
    ( 5, 0.06, 0.24, 0.30, 0.48, _GA * 3),        # 412.5 deg
    ( 4, 0.02, 0.13, 0.22, 0.68, _GA * 4),        # 550 deg
]


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    base_r = int(scale * 92)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    br = base_r * S

    _sepal(big, bcx, bcy, int(br * 0.50))

    n_rings = len(RINGS)

    for ring_i, (n, r_base_f, len_f, hw_f, threshold, rot) in enumerate(RINGS):
        layer_t = ring_i / (n_rings - 1)

        if bloom <= threshold:
            layer_bloom = 0.0
        else:
            layer_bloom = min(1.0, (bloom - threshold) / max(0.01, 1.0 - threshold))

        if layer_bloom < 0.02:
            continue

        open_s = 0.25 + 0.75 * layer_bloom
        r_base = int(br * r_base_f)
        length = max(r_base + 6, int(br * len_f * open_s))
        half_w = max(4, int(br * hw_f * open_s))

        # Outer rings cerulean, inner rings deep indigo
        h_base = int(119 - layer_t * 6)
        h_mid  = int(115 - layer_t * 3)
        c_base   = hsv_to_bgr(h_base, 250 - int(layer_t * 20), int(148 + layer_t * 30))
        c_mid    = hsv_to_bgr(h_mid,  220 - int(layer_t * 12), int(205 + layer_t * 22))
        # Softer shadow: visible but not near-black, keeps depth without a mosaic look
        c_shadow = hsv_to_bgr(124, 238, max(28, int(55 - layer_t * 14)))
        # Highlight must stay clearly BLUE. Minimum saturation 148 to avoid white.
        hi_s = max(148, int(205 - layer_t * 35))
        hi_v = int(225 + layer_t * 10)
        c_hilight = hsv_to_bgr(112, hi_s, hi_v)

        for i in range(n):
            angle = 2 * math.pi * i / n + rot
            _draw_petal(big, bcx, bcy, r_base, length, half_w, angle,
                        c_base, c_mid, c_shadow, c_hilight)

    # Tight furled centre
    cr = max(5, int(br * 0.055))
    gradient_circle_hsv(big, bcx, bcy, cr + 2, MID, SHADOW, steps=8)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
