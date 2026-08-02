"""
Sunflower renderer.
Golden angle seed packing, two offset rows of narrow strap-like ray petals,
hidden green bracts. draw(canvas, cx, cy, bloom, scale, t, opts) is the
public interface.
"""
import math
import cv2
import numpy as np

from util import (
    curved_petal_polygon, scale_polygon, pts_to_np,
    gradient_circle_hsv, gradient_ellipse_hsv, lerp_hsv, lerp_colour,
    apply_gradient_to_poly_dir, hsv_to_bgr,
    shade_bgr, light_factor,
)

GOLDEN_ANGLE = 137.507764  # degrees

# 3/4 viewing angle: vertical compression of the flower head
SQUASH = 0.80


def _foreshorten(angle):
    """Length factor for a petal at screen angle under the 3/4 view squash."""
    s = math.sin(angle)
    c = math.cos(angle)
    return math.sqrt(s * s + (SQUASH * c) ** 2)

# Palette: warm golden amber, no lime
PETAL_BASE    = hsv_to_bgr(24, 235, 245)   # warm amber-gold
PETAL_TIP     = hsv_to_bgr(26, 185, 255)   # bright golden tip (NOT lime: was H=34)
PETAL_MID     = hsv_to_bgr(25, 210, 230)   # mid amber
PETAL_SHADOW  = hsv_to_bgr(19, 225, 120)   # dark amber shadow
PETAL_BACK    = hsv_to_bgr(22, 225, 195)   # back row slightly darker amber

BRACT_BASE    = hsv_to_bgr(62, 160, 85)
BRACT_DARK    = hsv_to_bgr(56, 180, 45)

DISC_OUTER    = hsv_to_bgr(22, 185, 165)
DISC_INNER    = hsv_to_bgr(14, 205, 75)
SEED_DARK     = hsv_to_bgr(10, 210, 16)
SEED_LIGHT    = hsv_to_bgr(15, 205, 52)


VEIN_COL = hsv_to_bgr(22, 200, 175)


def _petal(canvas, px, py, length, width, angle):
    """One strap-like petal: shadow, gradient, centre highlight, vein lines."""
    lf = light_factor(angle)
    pts = curved_petal_polygon(px, py, length, width, angle, curvature=0.015, n_pts=36)
    shadow_pts = scale_polygon(pts, px, py, 1.05)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly_dir(canvas, pts,
                               shade_bgr(PETAL_BASE, lf), shade_bgr(PETAL_TIP, lf),
                               angle)
    # Narrow bright streak down centre
    hi = scale_polygon(pts, px, py, 0.30)
    cv2.fillPoly(canvas, [pts_to_np(hi)], shade_bgr(PETAL_MID, lf))
    # Longitudinal vein: thin line along the petal midrib
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    v0 = (int(px + sin_a * length * 0.10), int(py - cos_a * length * 0.10))
    v1 = (int(px + sin_a * length * 0.88), int(py - cos_a * length * 0.88))
    cv2.line(canvas, v0, v1, shade_bgr(VEIN_COL, lf), 1, cv2.LINE_AA)


def _petal_back(canvas, px, py, length, width, angle):
    lf = light_factor(angle, lo=0.72, hi=1.04)
    pts = curved_petal_polygon(px, py, length, width, angle, curvature=0.015, n_pts=32)
    shadow_pts = scale_polygon(pts, px, py, 1.07)
    cv2.fillPoly(canvas, [pts_to_np(shadow_pts)], PETAL_SHADOW)
    apply_gradient_to_poly_dir(canvas, pts,
                               shade_bgr(PETAL_BACK, lf), shade_bgr(PETAL_MID, lf),
                               angle)


def _bracts(canvas, cx, cy, disc_r, n=14):
    # Kept short so the disc covers them entirely; just a hint of green at base
    blen = max(5, int(disc_r * 0.78))
    bw   = max(3, int(disc_r * 0.17))
    for i in range(n):
        angle = 2 * math.pi * i / n + math.pi / n
        blen_f = int(blen * _foreshorten(angle))
        pts = curved_petal_polygon(cx, cy, blen_f, bw, angle, curvature=0.04, n_pts=18)
        shadow = scale_polygon(pts, cx, cy, 1.04)
        cv2.fillPoly(canvas, [pts_to_np(shadow)], BRACT_DARK)
        cv2.fillPoly(canvas, [pts_to_np(pts)], BRACT_BASE)


def _seeds(canvas, cx, cy, disc_r, n=175):
    """
    Golden angle seed packing on the tilted disc: y positions compressed by
    the 3/4 view squash and each seed lit by its position relative to the light.
    """
    inv = 1.0 / math.sqrt(2.0)
    for k in range(1, n + 1):
        r_frac = math.sqrt(k / n)
        r = disc_r * r_frac * 0.92
        theta = math.radians(k * GOLDEN_ANGLE)
        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta) * SQUASH
        dot = max(2, int(disc_r * 0.044 * (0.60 + 0.50 * r_frac)))
        col = lerp_colour(SEED_DARK, SEED_LIGHT, r_frac)
        # Dome lighting: seeds on the up-left side of the disc catch the light
        lit = ((cx - sx) * inv + (cy - sy) * inv) / max(1.0, disc_r)
        col = shade_bgr(col, 1.0 + 0.30 * lit)
        cv2.circle(canvas, (int(round(sx)), int(round(sy))), dot, col, -1, cv2.LINE_AA)


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))

    base_r    = int(scale * 112)
    disc_r    = max(14, int(base_r * 0.50 * (0.20 + 0.80 * bloom)))
    petal_len = max(8,  int(base_r * 0.92 * (0.15 + 0.85 * bloom)))
    # Narrow strap petals: 15% width-to-length ratio, like real sunflower rays
    petal_w   = max(4,  int(petal_len * 0.15))
    n_petals  = 26  # Fibonacci-adjacent count

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    bdisc = disc_r * S
    bplen = petal_len * S
    bpw   = petal_w * S

    # 1. Bracts (hidden beneath disc, just peek at base)
    _bracts(big, bcx, bcy, bdisc)

    # 2. Back row petals (offset by half a petal gap, slightly longer)
    if bloom > 0.04:
        row_off = math.pi / n_petals
        for i in range(n_petals):
            # Small per-petal organic jitter
            jitter = 0.028 * math.sin(i * 11.3 + 2.7)
            angle = 2 * math.pi * i / n_petals + row_off + jitter
            fsh = _foreshorten(angle)
            len_j = int(bplen * fsh
                        * (1.08 + 0.09 * math.cos(i * 5.1) + 0.04 * math.sin(i * 8.3)))
            px = bcx + bdisc * math.sin(angle)
            py = bcy - bdisc * SQUASH * math.cos(angle)
            _petal_back(big, px, py, len_j, int(bpw * 0.90), angle)

    # 3. Front row petals
    if bloom > 0.04:
        for i in range(n_petals):
            jitter = 0.028 * math.sin(i * 7.9 + 1.1)
            angle = 2 * math.pi * i / n_petals + jitter
            fsh = _foreshorten(angle)
            len_j = int(bplen * fsh
                        * (1.00 + 0.09 * math.cos(i * 3.7) + 0.04 * math.sin(i * 6.1)))
            px = bcx + bdisc * math.sin(angle)
            py = bcy - bdisc * SQUASH * math.cos(angle)
            _petal(big, px, py, len_j, bpw, angle)

    # 4. Disc: tilted ellipse with the dark centre pushed away from the light
    gradient_ellipse_hsv(big, bcx, bcy, bdisc + 5, int((bdisc + 5) * SQUASH),
                         DISC_OUTER, DISC_INNER, steps=28,
                         off_x=bdisc * 0.12, off_y=bdisc * SQUASH * 0.12)

    # 5. Golden angle seeds on the tilted disc
    _seeds(big, bcx, bcy, int(bdisc * 0.90))

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
