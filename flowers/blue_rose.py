"""
Blue rose renderer.
Viewed from slightly above: overlapping teardrop petals in concentric rings.
Outer ring open/cupped, inner rings furled. Clearly vivid blue.
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

# Deep vivid blue palette (BGR)
DEEP    = hsv_to_bgr(118, 250, 150)   # deep indigo-blue
MID     = hsv_to_bgr(116, 235, 200)   # medium blue
EDGE    = hsv_to_bgr(112, 200, 245)   # cerulean lighter edge
HILIGHT = hsv_to_bgr(108,  55, 255)   # dewy pale highlight
SHADOW  = hsv_to_bgr(123, 255,  40)   # very dark navy shadow
SEPAL   = hsv_to_bgr( 80, 170,  78)
SEPAL_D = hsv_to_bgr( 76, 188,  40)


def _petal_pts(cx, cy, r_base, length, half_w, angle, n=24):
    """Teardrop rose petal from r_base outward along angle direction."""
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    perp_x = cos_a
    perp_y = sin_a
    bx = cx + sin_a * r_base
    by = cy - cos_a * r_base
    pts = []
    for i in range(n + 1):
        t = i / n
        # Narrow at base, widest ~38% along, tapers to point at tip
        w = half_w * math.sin(min(t * 2.6, math.pi))
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts.append((sx - perp_x * w, sy - perp_y * w))
    for i in range(n, -1, -1):
        t = i / n
        w = half_w * math.sin(min(t * 2.6, math.pi))
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts.append((sx + perp_x * w, sy + perp_y * w))
    return pts


def _draw_petal(canvas, cx, cy, r_base, length, half_w, angle,
                c_base, c_mid, c_edge, c_shadow, c_hilight):
    pts = _petal_pts(cx, cy, r_base, length, half_w, angle)
    # Dark shadow behind (enlarged from flower centre)
    shadow = [(cx + (x - cx) * 1.06, cy + (y - cy) * 1.06) for x, y in pts]
    cv2.fillPoly(canvas, [pts_to_np(shadow)], c_shadow)
    # Base fill
    cv2.fillPoly(canvas, [pts_to_np(pts)], c_base)
    # Outer ~55% of petal slightly lighter
    outer = _petal_pts(cx, cy, r_base + length * 0.45, length * 0.56,
                       int(half_w * 0.88), angle)
    cv2.fillPoly(canvas, [pts_to_np(outer)], c_mid)
    # Small highlight near tip
    hi = _petal_pts(cx, cy, r_base + length * 0.68, length * 0.26,
                    int(half_w * 0.36), angle)
    cv2.fillPoly(canvas, [pts_to_np(hi)], c_hilight)


def _sepal(canvas, cx, cy, radius):
    for i in range(5):
        angle = 2 * math.pi * i / 5 + math.pi / 5
        pts = curved_petal_polygon(cx, cy, int(radius * 1.28),
                                   int(radius * 0.24), angle,
                                   curvature=0.06, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.05))], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


# Ring spec: (n_petals, r_base_frac, length_frac, half_w_frac, bloom_thresh, rot)
# Wide half_w_frac ensures heavy petal overlap for rose-like look
RINGS = [
    (8, 0.48, 0.52, 0.44, 0.00, 0.00),   # outermost: wide overlapping
    (7, 0.28, 0.44, 0.38, 0.10, 0.40),   # mid-outer
    (6, 0.15, 0.33, 0.32, 0.28, 0.82),   # mid-inner
    (5, 0.06, 0.22, 0.26, 0.50, 1.22),   # inner
    (4, 0.02, 0.12, 0.20, 0.70, 1.65),   # tight core
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

        open_s  = 0.25 + 0.75 * layer_bloom
        r_base  = int(br * r_base_f)
        length  = max(r_base + 6, int(br * len_f * open_s))
        half_w  = max(4, int(br * hw_f * open_s))

        # Outer rings cerulean, inner rings deep indigo
        h_base = int(117 - layer_t * 4)
        h_mid  = int(114 - layer_t * 3)
        h_edge = int(111 - layer_t * 2)
        c_base    = hsv_to_bgr(h_base, 248 - int(layer_t * 14), int(155 + layer_t * 28))
        c_mid     = hsv_to_bgr(h_mid,  228 - int(layer_t * 10), int(210 + layer_t * 20))
        c_edge    = hsv_to_bgr(h_edge, 205 - int(layer_t * 8),  int(245 + layer_t * 10))
        c_shadow  = hsv_to_bgr(122, 255, max(18, int(48 - layer_t * 14)))
        c_hilight = hsv_to_bgr(109, max(30, int(62 - layer_t * 24)), 255)

        for i in range(n):
            angle = 2 * math.pi * i / n + rot
            _draw_petal(big, bcx, bcy, r_base, length, half_w, angle,
                        c_base, c_mid, c_edge, c_shadow, c_hilight)

    # Tight centre
    cr = max(5, int(br * 0.055))
    gradient_circle_hsv(big, bcx, bcy, cr + 2, MID, SHADOW, steps=8)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
