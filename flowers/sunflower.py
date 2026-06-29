"""
Sunflower renderer.
Golden angle seed packing, two interleaved rows of ray petals, short green bracts.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import (
    curved_petal_polygon, scale_polygon, pts_to_np,
    gradient_circle_hsv, lerp_colour,
    apply_gradient_to_poly, hsv_to_bgr,
)

GOLDEN_ANGLE = 137.507764  # degrees

# Palette: warm bright yellow. Tip stays H<=31 to avoid lime shift.
PETAL_BASE    = hsv_to_bgr(27, 228, 240)   # warm golden yellow
PETAL_TIP     = hsv_to_bgr(29, 192, 255)   # slightly lighter warm tip
PETAL_SHADOW  = hsv_to_bgr(19, 222, 105)   # dark amber shadow
PETAL_BACK    = hsv_to_bgr(25, 215, 200)   # back row slightly deeper
PETAL_BACK_TIP= hsv_to_bgr(27, 188, 230)   # back row tip
PETAL_VEIN    = hsv_to_bgr(31, 158, 255)   # subtle warm centre vein

BRACT_BASE    = hsv_to_bgr(64, 160, 86)
BRACT_TIP     = hsv_to_bgr(70, 140, 120)
BRACT_DARK    = hsv_to_bgr(60, 170, 42)

DISC_OUTER    = hsv_to_bgr(22, 190, 165)
DISC_INNER    = hsv_to_bgr(14, 210, 70)
SEED_DARK     = hsv_to_bgr(10, 218, 14)
SEED_LIGHT    = hsv_to_bgr(16, 202, 54)


def _petal(canvas, px, py, length, width, angle):
    """Three-layer ray petal: dark shadow, gradient fill, thin centre vein."""
    pts = curved_petal_polygon(px, py, length, width, angle, curvature=0.03, n_pts=40)
    shadow_pts = scale_polygon(pts, px, py, 1.03)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly(canvas, pts, PETAL_BASE, PETAL_TIP)
    # Thin vein: a narrow strip along the petal axis rather than a blob
    vein = curved_petal_polygon(px, py, int(length * 0.80), max(2, int(width * 0.14)),
                                angle, curvature=0.0, n_pts=18)
    cv2.fillPoly(canvas, [pts_to_np(vein)], PETAL_VEIN)


def _petal_back(canvas, px, py, length, width, angle):
    """Back row petals: slightly darker, no vein."""
    pts = curved_petal_polygon(px, py, length, width, angle, curvature=0.03, n_pts=36)
    shadow_pts = scale_polygon(pts, px, py, 1.08)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly(canvas, pts, PETAL_BACK, PETAL_BACK_TIP)


def _bracts(canvas, cx, cy, disc_r, petal_len, n=13):
    """Short bracts behind petals. 38% of petal length so they barely peep out."""
    blen = int(petal_len * 0.38)
    bw   = int(disc_r * 0.18)
    for i in range(n):
        angle = 2 * math.pi * i / n + math.pi / n
        pts = curved_petal_polygon(cx, cy, blen, bw, angle,
                                   curvature=0.04, n_pts=18)
        shadow = scale_polygon(pts, cx, cy, 1.04)
        cv2.fillPoly(canvas, [pts_to_np(shadow)], BRACT_DARK)
        apply_gradient_to_poly(canvas, pts, BRACT_BASE, BRACT_TIP)


def _seeds(canvas, cx, cy, disc_r, n=155):
    """Golden angle seed spiral. Visible spacing, dark centre grading to golden rim."""
    for k in range(1, n + 1):
        r_frac = math.sqrt(k / n)
        r = disc_r * r_frac * 0.87
        theta = math.radians(k * GOLDEN_ANGLE)
        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta)
        dot = max(2, int(disc_r * 0.051 * (0.60 + 0.50 * r_frac)))
        col = lerp_colour(SEED_DARK, SEED_LIGHT, r_frac)
        cv2.circle(canvas, (int(round(sx)), int(round(sy))), dot,
                   col, -1, cv2.LINE_AA)


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    base_r    = int(scale * 112)
    disc_r    = max(14, int(base_r * 0.48 * (0.22 + 0.78 * bloom)))
    petal_len = max(8,  int(base_r * 0.90 * (0.15 + 0.85 * bloom)))
    # Moderate width: real sunflower petals are strap-like but not extremely narrow
    petal_w   = max(4,  int(petal_len * 0.22))
    n_petals  = 21  # Fibonacci count

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    bdisc = disc_r * S
    bplen = petal_len * S
    bpw   = petal_w * S

    # 1. Short bracts, mostly hidden behind petals
    _bracts(big, bcx, bcy, bdisc, bplen)

    # 2. Back row of petals (very slightly longer so they peek between front row tips)
    if bloom > 0.04:
        row_off = math.pi / n_petals
        for i in range(n_petals):
            angle = 2 * math.pi * i / n_petals + row_off
            px = bcx + bdisc * math.sin(angle)
            py = bcy - bdisc * math.cos(angle)
            _petal_back(big, px, py, int(bplen * 1.04), int(bpw * 0.92), angle)

    # 3. Front row of petals
    if bloom > 0.04:
        for i in range(n_petals):
            angle = 2 * math.pi * i / n_petals
            px = bcx + bdisc * math.sin(angle)
            py = bcy - bdisc * math.cos(angle)
            _petal(big, px, py, bplen, bpw, angle)

    # 4. Disc with radial gradient
    gradient_circle_hsv(big, bcx, bcy, bdisc + 5, DISC_OUTER, DISC_INNER, steps=28)

    # 5. Golden angle seeds
    _seeds(big, bcx, bcy, bdisc * 0.87)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
