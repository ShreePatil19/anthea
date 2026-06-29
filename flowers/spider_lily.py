"""
Spider lily (Lycoris radiata) renderer.
6 thin strongly recurved wavy tepals + 6 very long arching stamens.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
opts may include {'variant': 'white'} for Lycoris albiflora.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, scale_polygon, apply_gradient_to_poly,
    bezier_cubic, lerp_colour, hsv_to_bgr,
)

# Vivid scarlet/crimson palette
T_BASE    = hsv_to_bgr(1,  242, 232)   # vivid scarlet
T_DEEP    = hsv_to_bgr(175, 215, 150)  # deep crimson (wraps near 0)
T_MID     = hsv_to_bgr(3,  252, 255)   # bright mid scarlet
T_SHADOW  = hsv_to_bgr(0,  218,  84)   # dark crimson shadow
T_HILIGHT = hsv_to_bgr(5,  110, 255)   # pale highlight ridge

S_COL  = hsv_to_bgr(2,  222, 218)   # filament scarlet
A_COL  = hsv_to_bgr(22, 230, 220)   # anther golden orange

# White variant (Lycoris albiflora)
W_BASE    = hsv_to_bgr(28,  32, 252)
W_DEEP    = hsv_to_bgr(28,  52, 200)
W_MID     = hsv_to_bgr(28,  18, 255)
W_SHADOW  = hsv_to_bgr(26,  72, 192)
W_HILIGHT = hsv_to_bgr(28,  12, 255)
W_STAMEN  = hsv_to_bgr(28,  60, 242)
W_ANTHER  = hsv_to_bgr(52, 182, 228)

N_TEPALS  = 6
N_STAMENS = 6

# 45 degree rotation avoids any stamen pointing straight down along the stem
STAMEN_ROT = math.pi / 4


def _tepal_colours(variant):
    if variant == "white":
        return W_BASE, W_DEEP, W_MID, W_SHADOW, W_HILIGHT
    return T_BASE, T_DEEP, T_MID, T_SHADOW, T_HILIGHT


def _stamen_colours(variant):
    if variant == "white":
        return W_STAMEN, W_SHADOW, W_ANTHER
    return S_COL, T_SHADOW, A_COL


def _build_tepal_outline(cx, cy, length, half_width, angle, recurve):
    """
    Narrow tepal ribbon following a cubic Bezier spine.
    The spine sweeps outward to ~88% of length, then the tip curls gracefully
    to the SIDE (lateral curl), faithfully showing the Lycoris recurve in 2D.
    Width peaks at ~43% along the bezier for a long visible ribbon body.
    recurve: 0=straight outward, 1=full signature backward curl.
    """
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    # Perpendicular direction for lateral curl
    perp_x =  cos_a
    perp_y =  sin_a

    p0 = (cx, cy)
    # Strong early push outward so the ribbon body is prominent
    p1 = (cx + sin_a * length * 0.50, cy - cos_a * length * 0.50)
    p2 = (cx + sin_a * length * 0.90, cy - cos_a * length * 0.90)
    # Tip: minimal backward pull, meaningful lateral curl to show the recurve in 2D
    curl_back = recurve * 0.10    # small axial pullback
    curl_side = recurve * 0.32    # prominent lateral curl
    p3 = (cx + sin_a * length * (0.90 - curl_back) + perp_x * length * curl_side,
          cy - cos_a * length * (0.90 - curl_back) + perp_y * length * curl_side)

    spine = bezier_cubic(p0, p1, p2, p3, steps=48)

    def width_at(t):
        # Peak at t~0.43, zero at both ends; wavy crinkled Lycoris edges
        base_w = half_width * math.sin(min(t * 1.15, 1.0) * math.pi) * 0.92
        wave   = half_width * 0.22 * math.sin(t * 3.8 * math.pi * 2)
        return max(0.5, base_w + wave)

    def perp_at(j):
        if j == 0:
            dx, dy = spine[1][0] - spine[0][0], spine[1][1] - spine[0][1]
        elif j == len(spine) - 1:
            dx, dy = spine[-1][0] - spine[-2][0], spine[-1][1] - spine[-2][1]
        else:
            dx, dy = spine[j+1][0] - spine[j-1][0], spine[j+1][1] - spine[j-1][1]
        L = math.hypot(dx, dy) or 1.0
        return -dy / L, dx / L

    left_side  = []
    right_side = []
    n = len(spine)
    for j, (sx, sy) in enumerate(spine):
        t = j / (n - 1)
        w = width_at(t)
        px, py = perp_at(j)
        left_side.append( (sx - px * w, sy - py * w))
        right_side.append((sx + px * w, sy + py * w))

    return left_side + list(reversed(right_side)), spine


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom   = max(0.0, min(1.0, bloom))
    variant = (opts or {}).get("variant", "scarlet")

    tepal_len  = int(scale * 148 * (0.22 + 0.78 * bloom))
    # Tepals wider than before for visible ribbon body; still narrow vs length
    half_width = max(6, int(scale * 14))
    stamen_len = int(tepal_len * (1.40 + 0.10 * bloom))
    recurve    = 0.35 + 0.60 * bloom   # 0.35 at bud, 0.95 at full open

    c_base, c_deep, c_mid, c_shadow, c_hilight = _tepal_colours(variant)
    s_col, s_shadow, a_col = _stamen_colours(variant)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    blen  = tepal_len * S
    bw    = half_width * S
    bstem = stamen_len * S

    # Tepals (behind stamens)
    for i in range(N_TEPALS):
        angle = 2 * math.pi * i / N_TEPALS - math.pi / 2

        outline, spine = _build_tepal_outline(bcx, bcy, blen, bw, angle, recurve)

        shadow_pts = scale_polygon(outline, bcx, bcy, 1.08)
        cv2.fillPoly(big, [pts_to_np(shadow_pts)], c_shadow)
        apply_gradient_to_poly(big, outline, c_base, c_deep)
        # Narrow central ridge highlight
        ridge = scale_polygon(outline, bcx, bcy, 0.24)
        cv2.fillPoly(big, [pts_to_np(ridge)], c_mid)

    # Stamens in front of tepals.
    # STAMEN_ROT = 45 degrees ensures no stamen points straight down along stem.
    for i in range(N_STAMENS):
        angle = (2 * math.pi * i / N_STAMENS - math.pi / 2
                 + math.pi / N_STAMENS + STAMEN_ROT)

        slen = int(bstem * (0.22 + 0.78 * bloom))

        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        # Gracefully arching filament: cubic Bezier with lateral sweep
        perp_offset = scale * S * 3.8 * ((i % 3) - 1)
        perp_x =  cos_a
        perp_y =  sin_a
        p0 = (bcx, bcy)
        p1 = (bcx + sin_a * slen * 0.35 + perp_x * perp_offset,
              bcy - cos_a * slen * 0.35 + perp_y * perp_offset)
        p2 = (bcx + sin_a * slen * 0.70 - perp_x * perp_offset * 0.55,
              bcy - cos_a * slen * 0.70 - perp_y * perp_offset * 0.55)
        p3 = (bcx + sin_a * slen, bcy - cos_a * slen)

        fil_pts = bezier_cubic(p0, p1, p2, p3, steps=52)
        np_fil  = pts_to_np(fil_pts).reshape((-1, 1, 2))

        # Shadow (wider) then main filament (thicker for prominence at 3x superscale)
        cv2.polylines(big, [np_fil], False, c_shadow, 10, cv2.LINE_AA)
        cv2.polylines(big, [np_fil], False, s_col, 6, cv2.LINE_AA)

        # Anther at tip
        tip_x, tip_y = int(p3[0]), int(p3[1])
        ar = max(5, int(scale * S * 5.8))
        cv2.ellipse(big, (tip_x, tip_y), (ar, max(3, ar // 2)),
                    math.degrees(angle), 0, 360, c_shadow, -1, cv2.LINE_AA)
        cv2.ellipse(big, (tip_x, tip_y), (max(3, ar - 2), max(2, ar // 2 - 1)),
                    math.degrees(angle), 0, 360, a_col, -1, cv2.LINE_AA)

    # Small centre disc
    cr = max(4, int(scale * S * 4.5))
    cv2.circle(big, (int(bcx), int(bcy)), cr + 3, c_shadow, -1, cv2.LINE_AA)
    cv2.circle(big, (int(bcx), int(bcy)), cr, c_base, -1, cv2.LINE_AA)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
