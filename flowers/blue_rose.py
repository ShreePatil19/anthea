"""
Blue rose renderer.
Viewed from slightly above: overlapping cupped petals in concentric rings,
graduating from deep indigo at the base to bright cerulean at the tips.
Direction-aware gradients give each petal realistic colour flow.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, scale_polygon, apply_gradient_to_poly_dir,
    lerp_colour, lerp_hsv, hsv_to_bgr,
    gradient_circle_hsv, curved_petal_polygon,
)

# Palette: vivid cobalt, clearly blue (H 112-120 range, never purple)
DEEP    = hsv_to_bgr(120, 255,  90)   # near-black deep navy (base shadows)
DARK    = hsv_to_bgr(118, 252, 140)   # deep indigo
MID     = hsv_to_bgr(115, 240, 195)   # medium cobalt blue
EDGE    = hsv_to_bgr(111, 205, 248)   # bright cerulean edge
HILIGHT = hsv_to_bgr(108,  28, 218)   # very subtle pale dewy tip
SHADOW  = hsv_to_bgr(124, 255,  30)   # very dark navy shadow
SEPAL   = hsv_to_bgr( 80, 165,  72)
SEPAL_D = hsv_to_bgr( 74, 188,  36)


def _petal_pts(cx, cy, r_base, length, half_w, angle, n=28):
    """
    Cupped rose petal: narrow at base (near flower centre), broadens outward,
    slightly curled inward at the outer tip to suggest depth.
    """
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    perp_x = cos_a
    perp_y = sin_a
    bx = cx + sin_a * r_base
    by = cy - cos_a * r_base
    pts_left  = []
    pts_right = []
    for i in range(n + 1):
        t = i / n
        # Width: stays wide through most of length, rolls inward near tip
        w_env = half_w * (math.sin(t * math.pi) ** 0.65)
        # Slight inward curl at the outer 20% of petal (petal edge rolls toward viewer)
        curl = half_w * 0.12 * max(0.0, (t - 0.80) / 0.20)
        w = max(0.5, w_env - curl)
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts_left.append( (sx - perp_x * w, sy - perp_y * w))
        pts_right.append((sx + perp_x * w, sy + perp_y * w))
    return pts_left + list(reversed(pts_right))


def _draw_petal(canvas, cx, cy, r_base, length, half_w, angle,
                c_dark, c_mid, c_edge, c_shadow, c_hilight):
    pts = _petal_pts(cx, cy, r_base, length, half_w, angle)
    # Dark navy shadow behind (simulates depth under adjacent petals)
    shadow = [(cx + (x - cx) * 1.07, cy + (y - cy) * 1.07) for x, y in pts]
    cv2.fillPoly(canvas, [pts_to_np(shadow)], c_shadow)
    # Main petal: direction-aware gradient from dark-base to cerulean-edge
    apply_gradient_to_poly_dir(canvas, pts, c_dark, c_edge, angle)
    # Edge overlay (outer 38%): slightly lighter cerulean, no harsh blobs
    edge_pts = _petal_pts(cx, cy, r_base + length * 0.62, length * 0.38,
                          max(3, int(half_w * 0.70)), angle)
    apply_gradient_to_poly_dir(canvas, edge_pts, c_mid, c_edge, angle)
    # Tiny dewy highlight at tip only: very subtle, not a white oval
    hi = _petal_pts(cx, cy, r_base + length * 0.84, length * 0.13,
                    max(2, int(half_w * 0.10)), angle)
    cv2.fillPoly(canvas, [pts_to_np(hi)], c_hilight)
    # Crease shadow on inner edge of each petal (simulates cupped shape)
    crease_pts = _petal_pts(cx, cy, r_base, length * 0.85,
                            max(2, int(half_w * 0.08)), angle)
    cv2.fillPoly(canvas, [pts_to_np(crease_pts)], c_shadow)


def _sepal(canvas, cx, cy, radius):
    for i in range(5):
        angle = 2 * math.pi * i / 5 + math.pi / 5
        pts = curved_petal_polygon(cx, cy, int(radius * 1.30),
                                   int(radius * 0.22), angle,
                                   curvature=0.06, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.06))], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


# Ring spec: (n_petals, r_base_frac, length_frac, half_w_frac, bloom_thresh, rot)
# Wider petals and more per outer ring for proper coverage and a rose-like look
RINGS = [
    (10, 0.46, 0.54, 0.50, 0.00, 0.00),   # outermost: 10 wide petals
    ( 8, 0.27, 0.46, 0.44, 0.08, 0.38),   # mid-outer
    ( 6, 0.14, 0.34, 0.38, 0.26, 0.80),   # mid-inner
    ( 5, 0.06, 0.22, 0.30, 0.48, 1.22),   # inner
    ( 4, 0.02, 0.13, 0.22, 0.68, 1.65),   # tight core
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
        h_dark = int(120 - layer_t * 2)
        h_mid  = int(116 - layer_t * 2)
        h_edge = int(111 - layer_t * 1)
        sat_d  = min(255, int(252 - layer_t * 12))
        val_d  = int(130 + layer_t * 40)
        sat_e  = min(255, int(205 - layer_t * 8))
        val_e  = int(248 + layer_t * 7)

        c_dark    = hsv_to_bgr(h_dark, sat_d, val_d)
        c_mid     = hsv_to_bgr(h_mid,  230,   int(198 + layer_t * 18))
        c_edge    = hsv_to_bgr(h_edge, sat_e, val_e)
        c_shadow  = hsv_to_bgr(124, 255, max(14, int(36 - layer_t * 12)))
        c_hilight = hsv_to_bgr(111, max(140, int(175 - layer_t * 35)), 210)

        for i in range(n):
            angle = 2 * math.pi * i / n + rot
            _draw_petal(big, bcx, bcy, r_base, length, half_w, angle,
                        c_dark, c_mid, c_edge, c_shadow, c_hilight)

    # Tight centre
    cr = max(5, int(br * 0.055))
    gradient_circle_hsv(big, bcx, bcy, cr + 3, MID, SHADOW, steps=10)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
