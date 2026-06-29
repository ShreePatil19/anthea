"""
Spider lily (Lycoris radiata) renderer.
6 thin strongly recurved wavy tepals + 6 very long gracefully arching stamens.
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
T_BASE    = hsv_to_bgr(1,  238, 220)   # vivid scarlet
T_DEEP    = hsv_to_bgr(175, 215, 155)  # deep crimson (wraps near 0)
T_MID     = hsv_to_bgr(3,  248, 245)   # bright mid scarlet
T_SHADOW  = hsv_to_bgr(0,  215,  82)   # dark crimson shadow
T_HILIGHT = hsv_to_bgr(6,   90, 255)   # pale highlight stripe

S_COL  = hsv_to_bgr(2,  220, 205)   # filament scarlet
A_COL  = hsv_to_bgr(20, 225, 215)   # anther golden-orange
A_DARK = hsv_to_bgr(0,  210,  70)   # anther dark shadow

# White variant (Lycoris albiflora)
W_BASE    = hsv_to_bgr(28,  32, 252)
W_DEEP    = hsv_to_bgr(28,  52, 205)
W_MID     = hsv_to_bgr(28,  18, 255)
W_SHADOW  = hsv_to_bgr(26,  68, 195)
W_HILIGHT = hsv_to_bgr(28,  12, 255)
W_STAMEN  = hsv_to_bgr(28,  55, 240)
W_ANTHER  = hsv_to_bgr(50, 185, 228)

N_TEPALS  = 6
N_STAMENS = 6


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
    Build the outline of one tepal as a list of (x,y).
    Spine: cubic Bezier from centre outward then curves back (recurved tip).
    recurve 0 = straight, 1 = strongly bent back.
    Width tapers to zero at both ends; wavy edges add organic crinkle.
    """
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)

    # Spine as cubic Bezier.
    # Goes outward to ~85% of length then curves back toward centre.
    # Less extreme than before: tip returns to ~60% of length at full recurve.
    p0 = (cx, cy)
    p1 = (cx + sin_a * length * 0.42, cy - cos_a * length * 0.42)
    p2 = (cx + sin_a * length * 0.85, cy - cos_a * length * 0.85)
    tip_frac = 0.85 - recurve * 0.42   # at recurve=0.70: 0.85-0.294=0.556
    p3 = (cx + sin_a * length * tip_frac,
          cy - cos_a * length * tip_frac)

    spine = bezier_cubic(p0, p1, p2, p3, steps=40)

    def width_at(t):
        # Narrow at base, widest at ~30%, tapers to fine tip at t=1
        base_w = half_width * math.sin(min(t * 1.8, 1.0) * math.pi) * 0.90
        # 5 gentle ripples: the wavy crinkled edges of Lycoris radiata
        wave = half_width * 0.18 * math.sin(t * 5 * math.pi * 2)
        return max(0.4, base_w + wave)

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

    outline = left_side + list(reversed(right_side))
    return outline, spine


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom   = max(0.0, min(1.0, bloom))
    variant = (opts or {}).get("variant", "scarlet")

    # Longer tepals: more of the arm is visible beyond the recurve zone
    tepal_len  = int(scale * 188 * (0.24 + 0.76 * bloom))
    half_width = max(5, int(scale * 13))
    # Stamen length: 1.40 to 1.50x tepal length (the defining feature)
    stamen_len = int(tepal_len * (1.40 + 0.08 * bloom))
    # Less extreme recurve: tip comes back to ~56% at full bloom (not 43%)
    recurve    = 0.38 + 0.32 * bloom   # 0.38 at bud, 0.70 at full open

    c_base, c_deep, c_mid, c_shadow, c_hilight = _tepal_colours(variant)
    s_col, s_shadow, a_col = _stamen_colours(variant)

    S = 3
    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * S, H * S), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * S, cy * S
    blen  = tepal_len * S
    bw    = half_width * S
    bstem = stamen_len * S

    # Wind sway: gentle lateral oscillation of the whole head
    sway_x = scale * S * 4.0 * math.sin(t * 0.9)
    sway_y = scale * S * 1.5 * math.sin(t * 0.7 + 0.4)

    # --- Draw tepals (behind stamens) ---
    # Angle offset: pi/12 rotation so distribution is visually balanced
    base_angle = -math.pi / 2 + math.pi / 12
    for i in range(N_TEPALS):
        angle = 2 * math.pi * i / N_TEPALS + base_angle
        cos_a = math.cos(angle)

        # Perspective: tepals pointing downward appear shorter (viewed from above)
        downward_t = max(0.0, -cos_a)
        t_persp = max(0.60, 1.0 - 0.38 * downward_t)
        eff_blen = int(blen * t_persp)

        outline, spine = _build_tepal_outline(
            bcx + sway_x * 0.4, bcy + sway_y * 0.4,
            eff_blen, bw, angle, recurve
        )

        # Shadow (enlarged behind)
        shadow_pts = scale_polygon(outline, bcx, bcy, 1.08)
        cv2.fillPoly(big, [pts_to_np(shadow_pts)], c_shadow)

        # Gradient fill from vivid scarlet at base to deep crimson at tip
        apply_gradient_to_poly(big, outline, c_base, c_deep)

        # Bright mid stripe along central spine (midrib)
        hi = scale_polygon(outline, bcx, bcy, 0.28)
        cv2.fillPoly(big, [pts_to_np(hi)], c_mid)

        # Draw the spine itself as a thin bright line (visible midrib)
        spine_np = pts_to_np(spine).reshape((-1, 1, 2))
        cv2.polylines(big, [spine_np], False, c_hilight, 2, cv2.LINE_AA)

    # --- Draw stamens in front of tepals ---
    # Stamens sit between tepals, angle offset by pi/N_STAMENS from tepals
    stamen_base = base_angle + math.pi / N_STAMENS
    up_bias = bstem * 0.40   # strong upward arc: stamens sweep up before fanning out

    for i in range(N_STAMENS):
        angle = 2 * math.pi * i / N_STAMENS + stamen_base
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        # Perspective foreshortening: stamens pointing downward appear shorter,
        # simulating a 3D flower viewed from slightly above the horizontal plane.
        downward = max(0.0, -cos_a)  # 0 for up/side, positive for down-pointing
        persp = max(0.55, 1.0 - 0.42 * downward)
        slen = int(bstem * (0.22 + 0.78 * bloom) * persp)

        # Tip of stamen (radially out in direction angle)
        tip_x = bcx + sin_a * slen + sway_x * 0.6
        tip_y = bcy - cos_a * slen + sway_y * 0.6

        # Graceful arching Bezier: strong upward lift on control points
        # makes every stamen sweep upward before arching to its tip.
        # This creates the characteristic "fountain" silhouette of Lycoris radiata.
        lateral_off = scale * S * 3.0 * (((i % 3) - 1))
        perp_x = cos_a
        perp_y = sin_a

        p0 = (bcx + sway_x * 0.2, bcy + sway_y * 0.2)
        p1 = (bcx + sin_a * slen * 0.26 + perp_x * lateral_off + sway_x * 0.35,
              bcy - cos_a * slen * 0.26 - up_bias + perp_y * lateral_off + sway_y * 0.35)
        p2 = (bcx + sin_a * slen * 0.66 + perp_x * lateral_off * 0.35 + sway_x * 0.55,
              bcy - cos_a * slen * 0.66 - up_bias * 0.18 + perp_y * lateral_off * 0.35 + sway_y * 0.55)
        p3 = (tip_x, tip_y)

        fil_pts = bezier_cubic(p0, p1, p2, p3, steps=48)
        np_fil  = pts_to_np(fil_pts).reshape((-1, 1, 2))

        # Shadow filament (thick)
        cv2.polylines(big, [np_fil], False, s_shadow, 14, cv2.LINE_AA)
        # Main filament (clearly visible)
        cv2.polylines(big, [np_fil], False, s_col, 8, cv2.LINE_AA)

        # Anther: elongated ellipse at tip, dark body with golden face
        tip_xi, tip_yi = int(tip_x), int(tip_y)
        ar = max(6, int(scale * S * 6.5))
        ar_b = max(4, ar // 2)
        rot_deg = math.degrees(angle)
        cv2.ellipse(big, (tip_xi, tip_yi), (ar + 2, ar_b + 2),
                    rot_deg, 0, 360, A_DARK, -1, cv2.LINE_AA)
        cv2.ellipse(big, (tip_xi, tip_yi), (ar, ar_b),
                    rot_deg, 0, 360, a_col, -1, cv2.LINE_AA)

    # Centre: small disc where stamens emerge
    cr = max(6, int(scale * S * 6))
    cv2.circle(big, (int(bcx), int(bcy)), cr + 4, c_shadow, -1, cv2.LINE_AA)
    cv2.circle(big, (int(bcx), int(bcy)), cr, c_base, -1, cv2.LINE_AA)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
