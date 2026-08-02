"""
Blue rose renderer.
Golden angle spiral of overlapping cupped petals, like a real rose seen from
slightly above: innermost petals furled and dark, outer petals broad and
bright. A global light direction shades each petal; soft ambient occlusion
darkens the core. draw(canvas, cx, cy, bloom, scale, t, opts) is the
public interface.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, scale_polygon, apply_gradient_to_poly_dir,
    lerp_colour, lerp_hsv, hsv_to_bgr,
    gradient_circle_hsv, curved_petal_polygon,
    shade_bgr, light_factor, darken_center,
)

GOLDEN_ANGLE = math.radians(137.507764)

# 3/4 viewing angle: vertical compression of the flower head
SQUASH = 0.82


def _foreshorten(angle):
    s = math.sin(angle)
    c = math.cos(angle)
    return math.sqrt(s * s + (SQUASH * c) ** 2)

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
    Cupped rose petal: narrow at base, broadens outward, curled inward at tip.
    Left and right sides are asymmetric to suggest the petal curling toward
    the viewer on one side (cupping).
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
        w_env = half_w * (math.sin(t * math.pi) ** 0.65)
        curl = half_w * 0.14 * max(0.0, (t - 0.75) / 0.25)
        w = max(0.5, w_env - curl)
        # Asymmetric cupping: one side slightly wider than the other
        w_left  = w * 1.10
        w_right = w * 0.92
        sx = bx + sin_a * length * t
        sy = by - cos_a * length * t
        pts_left.append( (sx - perp_x * w_left,  sy - perp_y * w_left))
        pts_right.append((sx + perp_x * w_right, sy + perp_y * w_right))
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
    # Crease along inner edge of each petal (simulates cupped shape);
    # uses the dark petal colour, not black, so it reads as a fold not a mark
    crease_pts = _petal_pts(cx, cy, r_base, length * 0.60,
                            max(2, int(half_w * 0.06)), angle)
    cv2.fillPoly(canvas, [pts_to_np(crease_pts)], c_dark)


def _sepal(canvas, cx, cy, radius):
    for i in range(5):
        angle = 2 * math.pi * i / 5 + math.pi / 5
        pts = curved_petal_polygon(cx, cy, int(radius * 1.30),
                                   int(radius * 0.22), angle,
                                   curvature=0.06, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.06))], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


# Spiral petal count: i = 0 is the innermost furled petal
N_PETALS = 26


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    base_r = int(scale * 92)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    br = base_r * S

    _sepal(big, bcx, bcy, int(br * 0.50))

    # Golden angle spiral, drawn outermost first so inner petals sit on top
    for i in range(N_PETALS - 1, -1, -1):
        t_i = i / (N_PETALS - 1)          # 0 = innermost, 1 = outermost
        angle = i * GOLDEN_ANGLE + 0.7 + 0.05 * math.sin(i * 3.1)

        # Outer petals unfurl first; the core stays furled until bloom is high
        threshold = 0.70 * (1.0 - t_i)
        if bloom <= threshold:
            continue
        layer_bloom = min(1.0, (bloom - threshold) / max(0.01, 1.0 - threshold))
        if layer_bloom < 0.02:
            continue
        open_s = 0.25 + 0.75 * layer_bloom

        fsh = _foreshorten(angle)
        r_base = int(br * (0.05 + 0.42 * (t_i ** 0.85)) * (0.35 + 0.65 * open_s) * fsh)
        length = max(8, int(br * (0.16 + 0.40 * t_i) * open_s * fsh))
        half_w = max(4, int(br * (0.15 + 0.30 * t_i) * open_s))

        # Inner petals deep and shadowed, outer petals bright cerulean
        lf = light_factor(angle)
        c_dark    = shade_bgr(hsv_to_bgr(int(120 - 8 * t_i), 250, int(100 + 60 * t_i)), lf)
        c_mid     = shade_bgr(hsv_to_bgr(int(116 - 5 * t_i), 232, int(170 + 45 * t_i)), lf)
        c_edge    = shade_bgr(hsv_to_bgr(int(112 - 2 * t_i), 205, int(200 + 55 * t_i)), lf)
        c_shadow  = hsv_to_bgr(124, 255, max(14, int(20 + 14 * t_i)))
        c_hilight = shade_bgr(hsv_to_bgr(111, 155, 212), lf)

        _draw_petal(big, bcx, bcy, r_base, length, half_w, angle,
                    c_dark, c_mid, c_edge, c_shadow, c_hilight)

    # Ambient occlusion: the heart of the rose sits in shadow
    darken_center(big, bcx, bcy, int(br * 0.50), strength=0.32)

    # Tight centre, large enough to cover the sepal base
    cr = max(6, int(br * 0.075))
    gradient_circle_hsv(big, bcx, bcy, cr + 3, MID, SHADOW, steps=10)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
