"""
Blue rose renderer.
Viewed from slightly above: concentric rings of broad overlapping petals.
Outer ring cupped, inner furled. Clearly vivid blue, not purple.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, scale_polygon, apply_gradient_to_poly,
    lerp_colour, lerp_hsv, hsv_to_bgr, bezier_quadratic,
    rotate_pts, gradient_circle_hsv, curved_petal_polygon,
)

# Deep vivid blue palette (BGR)
DEEP    = hsv_to_bgr(118, 250, 150)   # deep indigo-blue
MID     = hsv_to_bgr(116, 235, 200)   # medium blue
EDGE    = hsv_to_bgr(112, 205, 240)   # cerulean lighter edge
HILIGHT = hsv_to_bgr(109,  80, 255)   # dewy pale highlight
SHADOW  = hsv_to_bgr(123, 255,  45)   # very dark navy shadow
INNER_D = hsv_to_bgr(120, 255,  80)   # inner shadow between petals
SEPAL   = hsv_to_bgr( 80, 170,  78)
SEPAL_D = hsv_to_bgr( 76, 188,  40)


def _arc_petal_pts(cx, cy, r_inner, r_outer, a_start, a_end, n=28):
    """
    Outer ring petal: a thick ring segment with curved edges, viewed from above.
    Returns polygon points.
    """
    pts = []
    # Outer arc with slight bulge at midpoint
    for i in range(n + 1):
        t = i / n
        a = a_start + (a_end - a_start) * t
        # Bulge outer edge slightly outward at mid for rounded petal shape
        r_bulge = r_outer * (1.0 + 0.12 * math.sin(t * math.pi))
        pts.append((cx + r_bulge * math.cos(a), cy + r_bulge * math.sin(a)))
    # Inner edge (arc back, with concave shape toward centre)
    for i in range(n, -1, -1):
        t = i / n
        a = a_start + (a_end - a_start) * t
        r_conc = r_inner * (1.0 - 0.10 * math.sin(t * math.pi))
        pts.append((cx + r_conc * math.cos(a), cy + r_conc * math.sin(a)))
    return pts


def _pointed_petal_pts(cx, cy, r_inner, r_outer, a_start, a_end, n=28):
    """
    Inner furled petal: like _arc_petal_pts but more pointed, for tight inner layers.
    """
    a_mid = (a_start + a_end) / 2
    pts = []
    for i in range(n + 1):
        t = i / n
        a = a_start + (a_end - a_start) * t
        # Taper strongly toward side edges (pointed petal tips)
        edge_taper = 1.0 - 0.6 * (2 * abs(t - 0.5)) ** 1.4
        r_bulge = r_inner + (r_outer - r_inner) * edge_taper
        pts.append((cx + r_bulge * math.cos(a), cy + r_bulge * math.sin(a)))
    for i in range(n, -1, -1):
        t = i / n
        a = a_start + (a_end - a_start) * t
        r_conc = r_inner * 0.55
        pts.append((cx + r_conc * math.cos(a), cy + r_conc * math.sin(a)))
    return pts


def _draw_ring(canvas, cx, cy, n, r_in, r_out, rot, col_base, col_edge,
               shadow_col, hilight_col, petal_fn, layer_t):
    """Draw one ring of n petals using petal_fn for shape."""
    arc_per_petal  = 2 * math.pi / n
    overlap_frac   = 0.28  # petals overlap neighbours
    arc_span       = arc_per_petal * (1.0 + overlap_frac)

    for i in range(n):
        a_centre = 2 * math.pi * i / n + rot
        a_start  = a_centre - arc_span / 2
        a_end    = a_centre + arc_span / 2

        pts = petal_fn(cx, cy, r_in, r_out, a_start, a_end)
        np_pts = pts_to_np(pts)

        # Shadow strip (draw slightly enlarged in shadow colour first)
        shadow = [(cx + (x - cx) * 1.05, cy + (y - cy) * 1.05) for x, y in pts]
        cv2.fillPoly(canvas, [pts_to_np(shadow)], shadow_col)

        # Gradient fill radially (base=r_in side, edge=r_out side)
        apply_gradient_to_poly(canvas, pts, col_base, col_edge)

        # Dark gap between petals: shadow arc along one edge
        gap_pts = []
        n_gap = 12
        for k in range(n_gap + 1):
            t = k / n_gap
            a_gap = a_start + (a_start + arc_span / 3 * 2 - a_start) * t
            r_g = r_in + (r_out - r_in) * 0.35
            gap_pts.append((cx + r_g * math.cos(a_gap), cy + r_g * math.sin(a_gap)))
        # Shadow edge line
        np_gap = pts_to_np(gap_pts).reshape((-1, 1, 2))
        cv2.polylines(canvas, [np_gap], False, shadow_col, 3, cv2.LINE_AA)

        # Dewy highlight on the outer petal face
        hi_pts = []
        a_hi_start = a_centre - arc_span * 0.25
        a_hi_end   = a_centre + arc_span * 0.25
        r_hi_in    = r_in  + (r_out - r_in) * 0.55
        r_hi_out   = r_in  + (r_out - r_in) * 0.85
        for k in range(10):
            t = k / 9
            a = a_hi_start + (a_hi_end - a_hi_start) * t
            hi_pts.append((cx + r_hi_out * math.cos(a), cy + r_hi_out * math.sin(a)))
        for k in range(9, -1, -1):
            t = k / 9
            a = a_hi_start + (a_hi_end - a_hi_start) * t
            hi_pts.append((cx + r_hi_in * math.cos(a), cy + r_hi_in * math.sin(a)))
        cv2.fillPoly(canvas, [pts_to_np(hi_pts)], hilight_col)


def _sepal(canvas, cx, cy, radius):
    n = 5
    for i in range(n):
        angle = 2 * math.pi * i / n + math.pi / n
        pts = curved_petal_polygon(cx, cy, int(radius * 1.28),
                                   int(radius * 0.24), angle,
                                   curvature=0.06, n_pts=20)
        shadow = scale_polygon(pts, cx, cy, 1.05)
        cv2.fillPoly(canvas, [pts_to_np(shadow)], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


# Ring spec: (n_petals, r_inner_frac, r_outer_frac, bloom_threshold, rot_offset)
RINGS = [
    (5, 0.60, 1.00, 0.00, 0.00),    # outermost ring
    (5, 0.38, 0.70, 0.10, 0.63),    # mid-outer
    (5, 0.22, 0.48, 0.28, 1.26),    # mid-inner
    (5, 0.10, 0.30, 0.50, 1.88),    # inner
    (4, 0.03, 0.15, 0.70, 2.60),    # core
]


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    base_r = int(scale * 90)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    br = base_r * S

    # Sepals behind everything
    _sepal(big, bcx, bcy, int(br * 0.50))

    n_rings = len(RINGS)

    for ring_i, (n, r_in_f, r_out_f, threshold, rot) in enumerate(RINGS):
        layer_t = ring_i / (n_rings - 1)

        if bloom <= threshold:
            layer_bloom = 0.0
        else:
            layer_bloom = min(1.0, (bloom - threshold) / max(0.01, 1.0 - threshold))

        if layer_bloom < 0.02:
            continue

        # Scale ring by bloom
        open_scale = 0.20 + 0.80 * layer_bloom
        r_in  = int(br * r_in_f)
        r_out = max(r_in + 6, int(br * r_out_f * open_scale
                                   + br * r_in_f * (1.0 - open_scale)))

        # Colour: deepen slightly toward inner rings
        h_base = int(118 - layer_t * 5)
        h_edge = int(112 - layer_t * 3)
        c_base    = hsv_to_bgr(h_base, 250 - int(layer_t * 10), int(150 + layer_t * 25))
        c_edge    = hsv_to_bgr(h_edge, 205, int(240 + layer_t * 8))
        c_shadow  = hsv_to_bgr(122, 255, max(20, int(50 - layer_t * 10)))
        c_hilight = hsv_to_bgr(109, max(40, int(80 - layer_t * 20)), 255)

        petal_fn = _pointed_petal_pts if ring_i >= 3 else _arc_petal_pts
        _draw_ring(big, bcx, bcy, n, r_in, r_out, rot,
                   c_base, c_edge, c_shadow, c_hilight, petal_fn, layer_t)

    # Tight spiral centre
    cr = max(5, int(br * 0.045))
    gradient_circle_hsv(big, bcx, bcy, cr + 2, MID, SHADOW, steps=8)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
