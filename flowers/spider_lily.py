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
    bezier_cubic, bezier_quadratic, lerp_colour, hsv_to_bgr,
)

# Scarlet/crimson palette
T_BASE    = hsv_to_bgr(1,  235, 225)   # vivid scarlet
T_DEEP    = hsv_to_bgr(175, 210, 160)  # deep crimson (wraps near 0)
T_MID     = hsv_to_bgr(3,  245, 248)   # bright mid scarlet
T_SHADOW  = hsv_to_bgr(0,  210,  90)   # dark crimson shadow
T_HILIGHT = hsv_to_bgr(5,  100, 255)   # pale highlight stripe

S_COL  = hsv_to_bgr(2,  215, 210)   # filament scarlet
A_COL  = hsv_to_bgr(22, 220, 210)   # anther golden orange

# White variant
W_BASE    = hsv_to_bgr(28,  35, 250)
W_DEEP    = hsv_to_bgr(28,  55, 200)
W_MID     = hsv_to_bgr(28,  20, 255)
W_SHADOW  = hsv_to_bgr(26,  70, 195)
W_HILIGHT = hsv_to_bgr(28,  15, 255)
W_STAMEN  = hsv_to_bgr(28,  60, 240)
W_ANTHER  = hsv_to_bgr(52, 180, 230)

N_TEPALS  = 6
N_STAMENS = 6


def _tepal_colours(variant):
    if variant == "white":
        return W_BASE, W_DEEP, W_MID, W_SHADOW, W_HILIGHT
    return T_BASE, T_DEEP, T_MID, T_SHADOW, T_HILIGHT


def _stamen_colours(variant):
    if variant == "white":
        return W_STAMEN, T_SHADOW, W_ANTHER
    return S_COL, T_SHADOW, A_COL


def _build_tepal_outline(cx, cy, length, half_width, angle, recurve):
    """
    Build the outline of one tepal as a list of (x,y).
    The tepal is a narrow ribbon that sweeps outward then curves back (recurves).
    recurve: 0=straight outward, 1=strongly bent back.
    """
    # We parameterise the tepal spine as a Bezier:
    # starts at (cx,cy), goes outward to distance ~0.55*length along angle,
    # then bends back toward angle+pi for the recurved tip.

    sin_a = math.sin(angle)
    cos_a = math.cos(angle)

    # Spine as cubic Bezier.
    # The tepal sweeps outward to ~0.75*length then gently recurves at the tip.
    # Even at full recurve the tip stays out at ~0.80 length from centre.
    p0 = (cx, cy)
    # First control: outward along angle direction
    p1 = (cx + sin_a * length * 0.40, cy - cos_a * length * 0.40)
    # Second control: mostly outward, with perpendicular curl for recurve shape
    perp_x =  cos_a  # perpendicular to outward direction
    perp_y =  sin_a
    p2 = (cx + sin_a * length * 0.80 + perp_x * recurve * length * 0.22,
          cy - cos_a * length * 0.80 + perp_y * recurve * length * 0.22)
    # Tip: outward but tip curves back slightly via perpendicular offset
    p3 = (cx + sin_a * length * 0.90 + perp_x * recurve * length * 0.30,
          cy - cos_a * length * 0.90 + perp_y * recurve * length * 0.30)

    spine = bezier_cubic(p0, p1, p2, p3, steps=36)

    # Build left/right outlines by offsetting perpendicular to spine direction
    def width_at(t):
        # Narrow at base, swell in lower-middle, taper to tip; add waviness
        base_w = half_width * math.sin(min(t * 1.6, 1.0) * math.pi) * 0.85
        # Wavy edge: 4 small ripples along length
        wave = half_width * 0.14 * math.sin(t * 4 * math.pi * 2)
        return max(0.5, base_w + wave)

    def perp_at(j):
        if j == 0:
            dx = spine[1][0] - spine[0][0]
            dy = spine[1][1] - spine[0][1]
        elif j == len(spine) - 1:
            dx = spine[-1][0] - spine[-2][0]
            dy = spine[-1][1] - spine[-2][1]
        else:
            dx = spine[j+1][0] - spine[j-1][0]
            dy = spine[j+1][1] - spine[j-1][1]
        L = math.hypot(dx, dy) or 1.0
        return -dy / L, dx / L   # perpendicular

    left_side  = []
    right_side = []
    n = len(spine)
    for j, (sx, sy) in enumerate(spine):
        t = j / (n - 1)
        w = width_at(t)
        px, py = perp_at(j)
        left_side.append( (sx - px * w, sy - py * w))
        right_side.append((sx + px * w, sy + py * w))

    outline = left_side + list(reversed(right_side))
    return outline, spine


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom   = max(0.0, min(1.0, bloom))
    variant = (opts or {}).get("variant", "scarlet")

    # Tepal length: long and graceful
    tepal_len    = int(scale * 135 * (0.22 + 0.78 * bloom))
    half_width   = max(5, int(scale * 13))
    stamen_len   = int(tepal_len * (1.45 + 0.15 * bloom))
    recurve      = 0.45 + 0.45 * bloom   # 0.45 at bud, 0.90 at full open

    c_base, c_deep, c_mid, c_shadow, c_hilight = _tepal_colours(variant)
    s_col, s_shadow, a_col = _stamen_colours(variant)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    blen  = tepal_len * S
    bw    = half_width * S
    bstem = stamen_len * S

    # --- Draw tepals (behind stamens) ---
    for i in range(N_TEPALS):
        angle = 2 * math.pi * i / N_TEPALS - math.pi / 2

        outline, spine = _build_tepal_outline(bcx, bcy, blen, bw, angle, recurve)

        # Shadow (enlarged behind)
        shadow_pts = scale_polygon(outline, bcx, bcy, 1.07)
        cv2.fillPoly(big, [pts_to_np(shadow_pts)], c_shadow)

        # Gradient fill from base to tip
        apply_gradient_to_poly(big, outline, c_base, c_deep)

        # Bright mid stripe
        hi = scale_polygon(outline, bcx, bcy, 0.30)
        cv2.fillPoly(big, [pts_to_np(hi)], c_mid)

    # --- Draw stamens (in front of tepals) ---
    for i in range(N_STAMENS):
        # Stamens between tepals
        angle = 2 * math.pi * i / N_STAMENS - math.pi / 2 + math.pi / N_STAMENS

        slen = int(bstem * (0.20 + 0.80 * bloom))

        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        # Gracefully arching filament: starts at centre, arcs outward then curves gently
        p0 = (bcx, bcy)
        # Small perpendicular offset per stamen for natural spread
        perp_offset = scale * S * 2.5 * (((i % 3) - 1))
        perp_x =  cos_a
        perp_y =  sin_a
        p1 = (bcx + sin_a * slen * 0.38 + perp_x * perp_offset,
              bcy - cos_a * slen * 0.38 + perp_y * perp_offset)
        p2 = (bcx + sin_a * slen * 0.72 - perp_x * perp_offset * 0.5,
              bcy - cos_a * slen * 0.72 - perp_y * perp_offset * 0.5)
        p3 = (bcx + sin_a * slen, bcy - cos_a * slen)

        fil_pts = bezier_cubic(p0, p1, p2, p3, steps=44)
        np_fil  = pts_to_np(fil_pts).reshape((-1, 1, 2))

        # Shadow filament
        cv2.polylines(big, [np_fil], False, c_shadow, 4, cv2.LINE_AA)
        # Main filament
        cv2.polylines(big, [np_fil], False, s_col, 2, cv2.LINE_AA)

        # Anther at tip: small elongated ellipse
        tip_x, tip_y = int(p3[0]), int(p3[1])
        ar = max(5, int(scale * S * 5.5))
        cv2.ellipse(big, (tip_x, tip_y), (ar, max(3, ar // 2)),
                    math.degrees(angle), 0, 360, c_shadow, -1, cv2.LINE_AA)
        cv2.ellipse(big, (tip_x, tip_y), (max(3, ar - 2), max(2, ar // 2 - 1)),
                    math.degrees(angle), 0, 360, a_col, -1, cv2.LINE_AA)

    # Centre disc
    cr = max(5, int(scale * S * 5))
    cv2.circle(big, (int(bcx), int(bcy)), cr + 3, c_shadow, -1, cv2.LINE_AA)
    cv2.circle(big, (int(bcx), int(bcy)), cr, c_base, -1, cv2.LINE_AA)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
