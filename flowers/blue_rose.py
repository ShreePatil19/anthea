"""
Blue rose renderer.
Viewed from slightly above: overlapping cupped petals in concentric rings.
Each petal has a rich HSV gradient from deep indigo at the base to cerulean at the edge.
Highlights are subtle (clearly blue, never white).
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
DEEP      = hsv_to_bgr(120, 252, 145)   # deep indigo-blue shadow
MID       = hsv_to_bgr(117, 238, 200)   # medium cobalt blue
EDGE      = hsv_to_bgr(113, 205, 248)   # bright cerulean edge
HILIGHT   = hsv_to_bgr(110, 168, 255)   # pale blue highlight (CLEARLY blue, not white)
SHADOW    = hsv_to_bgr(125, 255,  32)   # very dark navy shadow
SEPAL     = hsv_to_bgr( 82, 165,  80)
SEPAL_D   = hsv_to_bgr( 78, 185,  38)
CENTRE    = hsv_to_bgr(118, 252, 120)   # deep indigo centre knob


def _petal_pts(cx, cy, r_base, length, half_w, angle, n=28):
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
        # Width envelope: zero at base, widest ~42% along, tapers to point at tip
        w = half_w * math.sin(min(t * 2.35, math.pi))
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts.append((sx - perp_x * w, sy - perp_y * w))
    for i in range(n, -1, -1):
        t = i / n
        w = half_w * math.sin(min(t * 2.35, math.pi))
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts.append((sx + perp_x * w, sy + perp_y * w))
    return pts


def _edge_pts(cx, cy, r_base, length, half_w, angle, n=18):
    """Thin strip for the lit outer edge of each petal."""
    # Only covers the outer 30% of the petal, narrow width
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    perp_x = cos_a
    perp_y = sin_a
    start_frac = 0.68
    bx = cx + sin_a * (r_base + length * start_frac)
    by = cy - cos_a * (r_base + length * start_frac)
    rem_len = length * (1.0 - start_frac)
    pts = []
    for i in range(n + 1):
        t = i / n
        w = half_w * 0.22 * math.sin(t * math.pi)
        sx = bx + sin_a * rem_len * t
        sy = by - cos_a * rem_len * t
        pts.append((sx - perp_x * w, sy - perp_y * w))
    for i in range(n, -1, -1):
        t = i / n
        w = half_w * 0.22 * math.sin(t * math.pi)
        sx = bx + sin_a * rem_len * t
        sy = by - cos_a * rem_len * t
        pts.append((sx + perp_x * w, sy + perp_y * w))
    return pts


def _hi_pts(cx, cy, r_base, length, half_w, angle, n=22):
    """Elongated central highlight stripe along the petal face (not a round tip blob)."""
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    perp_x = cos_a
    perp_y = sin_a
    start_frac = 0.28
    bx = cx + sin_a * (r_base + length * start_frac)
    by = cy - cos_a * (r_base + length * start_frac)
    rem_len = length * 0.58   # covers 28%-86% of petal length
    pts = []
    for i in range(n + 1):
        t = i / n
        w = half_w * 0.24 * math.sin(t * math.pi)
        sx = bx + sin_a * rem_len * t
        sy = by - cos_a * rem_len * t
        pts.append((sx - perp_x * w, sy - perp_y * w))
    for i in range(n, -1, -1):
        t = i / n
        w = half_w * 0.24 * math.sin(t * math.pi)
        sx = bx + sin_a * rem_len * t
        sy = by - cos_a * rem_len * t
        pts.append((sx + perp_x * w, sy + perp_y * w))
    return pts


def _draw_petal(canvas, cx, cy, r_base, length, half_w, angle,
                c_base, c_mid, c_edge, c_shadow, c_hilight, bright_alt=False):
    pts = _petal_pts(cx, cy, r_base, length, half_w, angle)
    # Dark shadow behind (enlarged) - creates visible separation between adjacent petals
    shadow = [(cx + (x - cx) * 1.09, cy + (y - cy) * 1.09) for x, y in pts]
    cv2.fillPoly(canvas, [pts_to_np(shadow)], c_shadow)
    # Rich gradient fill: deep blue at base to medium blue at face
    apply_gradient_to_poly(canvas, pts, c_base, c_mid)
    # Lit outer edge: thin bright cerulean strip
    edge = _edge_pts(cx, cy, r_base, length, half_w, angle)
    cv2.fillPoly(canvas, [pts_to_np(edge)], c_edge)
    # Elongated central highlight stripe (gradient, not flat blob)
    hi = _hi_pts(cx, cy, r_base, length, half_w, angle)
    apply_gradient_to_poly(canvas, hi, c_hilight, c_edge)


def _sepal(canvas, cx, cy, radius):
    for i in range(5):
        angle = 2 * math.pi * i / 5 + math.pi / 5
        pts = curved_petal_polygon(cx, cy, int(radius * 1.30),
                                   int(radius * 0.22), angle,
                                   curvature=0.06, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.05))], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


# Ring spec: (n_petals, r_base_frac, length_frac, half_w_frac, bloom_thresh, rot)
# Fewer, larger outer petals to read as a side-view cupped rose.
RINGS = [
    (5,  0.40, 0.62, 0.60, 0.00, 0.00),  # outermost: 5 large cupped petals
    (6,  0.27, 0.46, 0.46, 0.10, 0.30),  # mid-outer
    (6,  0.14, 0.34, 0.35, 0.28, 0.80),  # mid-inner
    (5,  0.06, 0.23, 0.27, 0.50, 1.20),  # inner
    (4,  0.02, 0.13, 0.21, 0.70, 1.62),  # tight core
]


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    base_r = int(scale * 94)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    br = base_r * S

    _sepal(big, bcx, bcy, int(br * 0.50))

    # Background fill: flat deep blue circle behind all petals.
    # Fills the angular gaps so the silhouette reads round, not octagonal.
    # Using a flat fill avoids a dark gradient ring at the outer edge.
    bg_r = int(br * 1.12)
    cv2.circle(big, (int(bcx), int(bcy)), bg_r, DEEP, -1, cv2.LINE_AA)

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

        # Outer rings cerulean edge; inner rings deep indigo
        # layer_t=0 -> outermost ring; layer_t=1 -> innermost
        h_base = int(119 - layer_t * 3)
        h_mid  = int(116 - layer_t * 3)
        h_edge = int(112 - layer_t * 2)
        s_base = int(250 - layer_t * 12)
        v_base = int(148 + layer_t * 30)
        v_mid  = int(205 + layer_t * 18)
        c_base    = hsv_to_bgr(h_base, s_base, v_base)
        c_mid     = hsv_to_bgr(h_mid,  int(230 - layer_t * 10), v_mid)
        c_edge    = hsv_to_bgr(h_edge, 205, 252)
        c_shadow  = hsv_to_bgr(125, 255, max(16, int(44 - layer_t * 12)))
        # Highlight: always clearly blue (S >= 155), never pale/white
        c_hilight = hsv_to_bgr(110, int(168 - layer_t * 18), 255)

        for i in range(n):
            angle = 2 * math.pi * i / n + rot
            # Perspective: upward-pointing petals foreshortened (side-view illusion).
            # angle=0 points up; cos(angle) peaks at 1 when pointing straight up.
            up_frac = max(0.0, math.cos(angle))
            persp = 1.0 - 0.28 * up_frac
            eff_len = max(r_base + 4, int(length * persp))
            eff_hw  = max(3, int(half_w * (1.0 - 0.14 * up_frac)))
            # Slight alternating brightness between adjacent petals
            alt = 0.12 * (i % 2)
            cb = lerp_hsv(c_base, c_mid, alt)
            cm = lerp_hsv(c_mid, c_edge, alt)
            _draw_petal(big, bcx, bcy, r_base, eff_len, eff_hw, angle,
                        cb, cm, c_edge, c_shadow, c_hilight)

    # Tight centre knob
    cr = max(5, int(br * 0.058))
    gradient_circle_hsv(big, bcx, bcy, cr + 2, MID, SHADOW, steps=8)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
