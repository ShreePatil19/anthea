"""
Blue rose renderer.
Viewed from slightly above: a spiral of broad overlapping cupped petals.
Soft blurred shadows in the recesses and faint highlights on the faces give
depth; deep indigo at the petal base, brighter cerulean at the rim.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, scale_polygon, apply_gradient_to_poly,
    lerp_colour, hsv_to_bgr, composite_soft, jitter,
    gradient_circle_hsv, curved_petal_polygon,
)

SEPAL   = hsv_to_bgr( 80, 170,  78)
SEPAL_D = hsv_to_bgr( 76, 188,  40)
CORE    = hsv_to_bgr(120, 245,  70)


def _petal_pts(cx, cy, r_base, length, half_w, angle, n=26):
    """Broad rounded cupped petal from r_base outward along angle."""
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    perp_x = cos_a
    perp_y = sin_a
    bx = cx + sin_a * r_base
    by = cy - cos_a * r_base

    def w_at(t):
        # Full, rounded body: stays wide most of the length, rounds at tip.
        return half_w * (math.sin(t * math.pi) ** 0.55)

    left, right = [], []
    for i in range(n + 1):
        t = i / n
        w = w_at(t)
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        left.append((sx - perp_x * w, sy - perp_y * w))
        right.append((sx + perp_x * w, sy + perp_y * w))
    return left + list(reversed(right))


def _sepal(canvas, cx, cy, radius):
    for i in range(5):
        angle = 2 * math.pi * i / 5 + math.pi / 5
        pts = curved_petal_polygon(cx, cy, int(radius * 1.28),
                                   int(radius * 0.24), angle,
                                   curvature=0.06, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.05))], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


# Ring spec: (n_petals, r_base_frac, length_frac, half_w_frac, bloom_thresh, rot)
RINGS = [
    (8, 0.46, 0.56, 0.46, 0.00, 0.00),
    (7, 0.30, 0.46, 0.40, 0.10, 0.42),
    (6, 0.17, 0.36, 0.34, 0.28, 0.86),
    (5, 0.08, 0.25, 0.28, 0.50, 1.30),
    (4, 0.02, 0.15, 0.22, 0.70, 1.80),
]


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))
    soft = (opts or {}).get("soft", True)

    base_r = int(scale * 95)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    br = base_r * S

    _sepal(big, bcx, bcy, int(br * 0.50))

    # Accumulator layers for soft shadow and highlight (one blur each, cheap).
    shadow_layer = np.zeros_like(big)
    shadow_mask = np.zeros(big.shape[:2], dtype=np.uint8)
    hi_layer = np.zeros_like(big)
    hi_mask = np.zeros(big.shape[:2], dtype=np.uint8)

    n_rings = len(RINGS)
    rings = []

    # Pre-compute petal geometry so shadows can go down first, faces after.
    for ring_i, (n, r_base_f, len_f, hw_f, threshold, rot) in enumerate(RINGS):
        if bloom <= threshold:
            continue
        layer_bloom = min(1.0, (bloom - threshold) / max(0.01, 1.0 - threshold))
        if layer_bloom < 0.02:
            continue
        layer_t = ring_i / (n_rings - 1)
        open_s = 0.30 + 0.70 * layer_bloom
        r_base = int(br * r_base_f)
        length = max(r_base + 8, int(br * len_f * open_s))
        half_w = max(5, int(br * hw_f * open_s))

        h_base = int(120 - layer_t * 4)
        h_rim  = int(112 - layer_t * 2)
        c_base = hsv_to_bgr(h_base, 250 - int(layer_t * 18), int(95 + layer_t * 30))
        c_rim  = hsv_to_bgr(h_rim,  200 - int(layer_t * 18), int(230 + layer_t * 12))
        for i in range(n):
            angle = 2 * math.pi * i / n + rot + jitter(ring_i * 11 + i, 0.10)
            jl = 1.0 + jitter(ring_i * 7 + i + 3, 0.10)
            rings.append((layer_t, r_base, int(length * jl), half_w, angle,
                          c_base, c_rim))

    # 1. Soft shadow halo: enlarged dark petals into the shadow accumulator.
    for layer_t, r_base, length, half_w, angle, c_base, c_rim in rings:
        pts = _petal_pts(bcx, bcy, r_base, int(length * 1.12),
                         int(half_w * 1.16), angle)
        cv2.fillPoly(shadow_layer, [pts_to_np(pts)], hsv_to_bgr(123, 255, 18))
        cv2.fillPoly(shadow_mask, [pts_to_np(pts)], 255)
    if soft:
        composite_soft(big, shadow_layer, shadow_mask, blur=41, alpha=0.85)

    # 2. Petal faces with vertical gradient, outer rings first (under inner).
    for layer_t, r_base, length, half_w, angle, c_base, c_rim in rings:
        pts = _petal_pts(bcx, bcy, r_base, length, half_w, angle)
        apply_gradient_to_poly(big, pts, c_base, c_rim)

    # 3. Soft highlights: a thin sliver near each petal rim, not a centre blob.
    for layer_t, r_base, length, half_w, angle, c_base, c_rim in rings:
        hi = _petal_pts(bcx, bcy, r_base + length * 0.58, length * 0.34,
                        int(half_w * 0.42), angle)
        hue = int(110 - layer_t * 2)
        cv2.fillPoly(hi_layer, [pts_to_np(hi)],
                     hsv_to_bgr(hue, 95, 248))
        cv2.fillPoly(hi_mask, [pts_to_np(hi)], 255)
    if soft:
        composite_soft(big, hi_layer, hi_mask, blur=37, alpha=0.22)

    # 4. Tight furled centre.
    cr = max(6, int(br * 0.07))
    gradient_circle_hsv(big, bcx, bcy, cr + 3, hsv_to_bgr(116, 230, 150), CORE, steps=10)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
