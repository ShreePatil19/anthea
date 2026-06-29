"""
Sunflower renderer.
Golden angle seed packing, two interleaved rows of broad petals, visible bracts.
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

# Palette
PETAL_BASE    = hsv_to_bgr(30, 240, 255)   # bright golden yellow
PETAL_MID     = hsv_to_bgr(26, 230, 230)   # amber mid
PETAL_TIP     = hsv_to_bgr(34, 200, 255)   # pale warm tip
PETAL_SHADOW  = hsv_to_bgr(22, 220, 140)   # dark amber shadow
PETAL_BACK    = hsv_to_bgr(24, 230, 200)   # back row slightly darker

BRACT_BASE    = hsv_to_bgr(62, 170, 90)
BRACT_TIP     = hsv_to_bgr(70, 150, 130)
BRACT_DARK    = hsv_to_bgr(58, 180, 50)

DISC_OUTER    = hsv_to_bgr(24, 180, 175)   # medium warm golden brown disc rim
DISC_INNER    = hsv_to_bgr(16, 200, 90)    # darker brown disc centre
SEED_DARK     = hsv_to_bgr(10, 210, 18)    # very dark near-black seeds at centre
SEED_LIGHT    = hsv_to_bgr(15, 215, 55)    # dark brown seeds at rim


def _petal(canvas, px, py, length, width, angle):
    """Draw one petal with shadow, gradient fill, and highlight."""
    pts = curved_petal_polygon(px, py, length, width, angle,
                               curvature=0.14, n_pts=36)
    shadow_pts = scale_polygon(pts, px, py, 1.09)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly(canvas, pts, PETAL_MID, PETAL_TIP)
    hi = scale_polygon(pts, px, py, 0.40)
    cv2.fillPoly(canvas, [pts_to_np(hi)], PETAL_TIP)


def _petal_back(canvas, px, py, length, width, angle):
    pts = curved_petal_polygon(px, py, length, width, angle,
                               curvature=0.10, n_pts=32)
    shadow_pts = scale_polygon(pts, px, py, 1.07)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly(canvas, pts, PETAL_BACK, PETAL_MID)


def _bracts(canvas, cx, cy, disc_r, petal_len, n=16):
    blen = int(petal_len * 1.12)
    bw   = int(disc_r * 0.30)
    for i in range(n):
        angle = 2 * math.pi * i / n + math.pi / n
        pts = curved_petal_polygon(cx, cy, blen, bw, angle,
                                   curvature=0.06, n_pts=24)
        shadow = scale_polygon(pts, cx, cy, 1.05)
        cv2.fillPoly(canvas, [pts_to_np(shadow)], BRACT_DARK)
        apply_gradient_to_poly(canvas, pts, BRACT_BASE, BRACT_TIP)


def _seeds(canvas, cx, cy, disc_r, n=120):
    """Golden angle seed packing with visible spacing. Use fewer, smaller dots."""
    for k in range(1, n + 1):
        r_frac = math.sqrt(k / n)
        r = disc_r * r_frac * 0.90   # stay inside disc edge
        theta = math.radians(k * GOLDEN_ANGLE)
        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta)
        # Keep dots small enough that gaps between seeds are visible
        dot = max(3, int(disc_r * 0.055 * (0.65 + 0.45 * r_frac)))
        # Dark center seeds, slightly lighter at rim
        col = lerp_colour(SEED_DARK, SEED_LIGHT, r_frac)
        cv2.circle(canvas, (int(round(sx)), int(round(sy))), dot,
                   col, -1, cv2.LINE_AA)


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    # Sizes at target resolution (will be 3x inside big canvas)
    base_r    = int(scale * 110)
    disc_r    = max(14, int(base_r * 0.42 * (0.22 + 0.78 * bloom)))
    petal_len = max(8,  int(base_r * 0.85 * (0.15 + 0.85 * bloom)))
    # Petal width: substantial fraction of petal length for broad look
    petal_w   = max(6,  int(petal_len * 0.44))
    n_petals  = 21  # Fibonacci count

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    bdisc     = disc_r * S
    bplen     = petal_len * S
    bpw       = petal_w * S
    bbase     = base_r * S

    # 1. Bracts behind petals
    _bracts(big, bcx, bcy, bdisc, bplen)

    # 2. Back row (offset by half a petal gap, slightly longer)
    if bloom > 0.04:
        row_off = math.pi / n_petals
        for i in range(n_petals):
            angle = 2 * math.pi * i / n_petals + row_off
            # Place petal base right at disc edge so they radiate cleanly
            px = bcx + bdisc * math.sin(angle)
            py = bcy - bdisc * math.cos(angle)
            _petal_back(big, px, py, int(bplen * 1.10), int(bpw * 0.92), angle)

    # 3. Front row
    if bloom > 0.04:
        for i in range(n_petals):
            angle = 2 * math.pi * i / n_petals
            px = bcx + bdisc * math.sin(angle)
            py = bcy - bdisc * math.cos(angle)
            _petal(big, px, py, bplen, bpw, angle)

    # 4. Disc gradient
    gradient_circle_hsv(big, bcx, bcy, bdisc + 4, DISC_OUTER, DISC_INNER, steps=24)

    # 5. Golden angle seeds (n matches function default; spacing visible at this scale)
    _seeds(big, bcx, bcy, bdisc * 0.88)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
