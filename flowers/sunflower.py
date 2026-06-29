"""
Sunflower renderer.
Golden angle seed packing, two interleaved rows of strap-like amber-gold petals, green bracts.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import (
    curved_petal_polygon, scale_polygon, pts_to_np,
    gradient_circle_hsv, lerp_hsv, lerp_colour,
    apply_gradient_to_poly, hsv_to_bgr,
)

GOLDEN_ANGLE = 137.507764  # degrees

# Warm amber-gold palette (not neon lime)
PETAL_BASE    = hsv_to_bgr(24, 210, 225)   # warm amber-gold
PETAL_MID     = hsv_to_bgr(27, 195, 205)   # slightly cooler amber
PETAL_TIP     = hsv_to_bgr(31, 165, 240)   # pale warm tip
PETAL_SHADOW  = hsv_to_bgr(19, 200, 105)   # deep amber shadow
PETAL_BACK    = hsv_to_bgr(21, 205, 175)   # back row slightly darker
PETAL_HI      = hsv_to_bgr(33, 140, 248)   # warm pale highlight

BRACT_BASE    = hsv_to_bgr(68, 150, 68)
BRACT_TIP     = hsv_to_bgr(73, 130, 100)
BRACT_DARK    = hsv_to_bgr(63, 165, 35)

DISC_OUTER    = hsv_to_bgr(22, 190, 165)   # warm golden-brown disc rim
DISC_INNER    = hsv_to_bgr(14, 205, 78)    # very dark brown disc centre
SEED_DARK     = hsv_to_bgr(10, 210, 14)    # near-black seeds at centre
SEED_LIGHT    = hsv_to_bgr(14, 200, 52)    # dark brown seeds at rim


def _petal(canvas, px, py, length, width, angle, hi_col):
    """Draw one ray petal: shadow, gradient fill, narrow highlight stripe."""
    pts = curved_petal_polygon(px, py, length, width, angle, curvature=0.01, n_pts=36)
    shadow_pts = scale_polygon(pts, px, py, 1.05)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly(canvas, pts, PETAL_BASE, PETAL_TIP)
    # Narrow central highlight stripe along petal axis
    hi = scale_polygon(pts, px, py, 0.28)
    cv2.fillPoly(canvas, [pts_to_np(hi)], hi_col)


def _petal_back(canvas, px, py, length, width, angle):
    """Back row petal: shadow + flat amber fill."""
    pts = curved_petal_polygon(px, py, length, width, angle, curvature=0.01, n_pts=32)
    shadow_pts = scale_polygon(pts, px, py, 1.07)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly(canvas, pts, PETAL_BACK, PETAL_MID)


def _bracts(canvas, cx, cy, disc_r, petal_len, n=13):
    """Green phyllaries (bracts) behind the petals, botanically correct but subtle."""
    blen = int(petal_len * 0.52)   # just over half petal length: tips stay near petal base
    bw   = int(disc_r * 0.15)
    for i in range(n):
        angle = 2 * math.pi * i / n + math.pi / n
        pts = curved_petal_polygon(cx, cy, blen, bw, angle,
                                   curvature=0.04, n_pts=20)
        shadow = scale_polygon(pts, cx, cy, 1.04)
        cv2.fillPoly(canvas, [pts_to_np(shadow)], BRACT_DARK)
        apply_gradient_to_poly(canvas, pts, BRACT_BASE, BRACT_TIP)


def _seeds(canvas, cx, cy, disc_r, n=150):
    """Golden angle seed packing: dark near centre, slightly lighter at rim."""
    for k in range(1, n + 1):
        r_frac = math.sqrt(k / n)
        r = disc_r * r_frac * 0.90
        theta = math.radians(k * GOLDEN_ANGLE)
        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta)
        dot = max(2, int(disc_r * 0.048 * (0.60 + 0.48 * r_frac)))
        col = lerp_colour(SEED_DARK, SEED_LIGHT, r_frac)
        cv2.circle(canvas, (int(round(sx)), int(round(sy))), dot,
                   col, -1, cv2.LINE_AA)


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    base_r    = int(scale * 112)
    disc_r    = max(14, int(base_r * 0.50 * (0.22 + 0.78 * bloom)))
    petal_len = max(8,  int(base_r * 0.88 * (0.15 + 0.85 * bloom)))
    # Strap-like petals: narrow ratio matches real sunflower ray petals
    petal_w   = max(4,  int(petal_len * 0.195))
    n_petals  = 34  # Fibonacci count for a full, lush ring

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    bdisc     = disc_r * S
    bplen     = petal_len * S
    bpw       = petal_w * S

    # Wind sway: gentle oscillation
    sway = int(scale * S * 3 * math.sin(t * 0.8))

    # 1. Green bracts behind everything
    _bracts(big, bcx, bcy, bdisc, bplen)

    # 2. Back row of petals (offset half gap, slightly longer)
    if bloom > 0.04:
        row_off = math.pi / n_petals
        for i in range(n_petals):
            angle = 2 * math.pi * i / n_petals + row_off
            # Slight length variation per petal for organic look
            var = 1.0 + 0.04 * math.sin(i * 2.3)
            px = bcx + bdisc * math.sin(angle) + sway * 0.3
            py = bcy - bdisc * math.cos(angle)
            _petal_back(big, px, py, int(bplen * 1.08 * var), int(bpw * 0.90), angle)

    # 3. Front row of petals
    if bloom > 0.04:
        for i in range(n_petals):
            angle = 2 * math.pi * i / n_petals
            var = 1.0 + 0.04 * math.sin(i * 1.7 + 0.5)
            px = bcx + bdisc * math.sin(angle) + sway * 0.3
            py = bcy - bdisc * math.cos(angle)
            # Highlight colour shifts slightly around the ring for natural variation
            t_ring = i / n_petals
            hi_col = lerp_hsv(PETAL_HI, PETAL_TIP, t_ring * 0.5)
            _petal(big, px, py, int(bplen * var), bpw, angle, hi_col)

    # 4. Disc gradient: rim to dark centre
    gradient_circle_hsv(big, bcx, bcy, bdisc + 4, DISC_OUTER, DISC_INNER, steps=28)

    # 5. Golden angle seed spiral
    _seeds(big, bcx, bcy, bdisc * 0.87)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
