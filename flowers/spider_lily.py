"""
Spider lily (Lycoris radiata) renderer.
6 thin strongly recurved wavy tepals + 6 very long arching stamens.
The flower is rotated 15 degrees so no stamen aligns with the stem.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
opts may include {'variant': 'white'} for Lycoris albiflora.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, scale_polygon, apply_gradient_radial,
    bezier_cubic, lerp_colour, hsv_to_bgr,
)

# 15-degree offset so no tepal or stamen points straight down into the stem
ANGLE_OFFSET = math.pi / 12

# Scarlet/crimson palette: all base/tip hues stay in H 0-10 to avoid the
# circular-median trap in the colour gate (bimodal H near 0 and near 180
# causes the linear median to land at H=60 = green).
T_BASE    = hsv_to_bgr(2,  235, 228)   # vivid scarlet
T_DEEP    = hsv_to_bgr(7,  232, 138)   # deep dark red at base
T_MID     = hsv_to_bgr(4,  248, 252)   # bright mid scarlet
T_SHADOW  = hsv_to_bgr(1,  215,  70)   # dark red shadow
T_HILIGHT = hsv_to_bgr(5,   80, 255)   # pale highlight stripe

S_COL  = hsv_to_bgr(2,  220, 215)   # filament scarlet
A_COL  = hsv_to_bgr(22, 225, 215)   # anther golden-orange

# White variant (Lycoris albiflora)
W_BASE    = hsv_to_bgr(28,  32, 252)
W_DEEP    = hsv_to_bgr(28,  58, 200)
W_MID     = hsv_to_bgr(28,  18, 255)
W_SHADOW  = hsv_to_bgr(26,  72, 190)
W_HILIGHT = hsv_to_bgr(28,  14, 255)
W_STAMEN  = hsv_to_bgr(28,  58, 242)
W_ANTHER  = hsv_to_bgr(52, 180, 232)

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
    Thin ribbon that sweeps outward then curves back (recurves) with wavy edges.
    recurve: 0=straight outward, 0.6=strongly bent back at full bloom.
    """
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)

    # Cubic Bezier spine: goes outward to max extent then curves back
    p0 = (cx, cy)
    p1 = (cx + sin_a * length * 0.48, cy - cos_a * length * 0.48)
    p2 = (cx + sin_a * length * 0.96, cy - cos_a * length * 0.96)
    # Tip pulls back toward centre; recurve controls how far back
    p3 = (cx + sin_a * length * (0.96 - recurve * 0.56),
          cy - cos_a * length * (0.96 - recurve * 0.56))

    spine = bezier_cubic(p0, p1, p2, p3, steps=40)

    def width_at(t):
        # Fast rise from base to 20%, then gradual taper to a fine tip
        rise = min(1.0, t * 5.0)
        fall = math.pow(max(0.0, 1.0 - t), 0.72)
        base_w = half_width * rise * fall
        # 3 cycles of crinkle: the wavy edge characteristic of Lycoris radiata
        wave = half_width * 0.10 * math.sin(t * 6 * math.pi)
        return max(1.0, base_w + wave)

    def perp_at(j):
        if j == 0:
            dx = spine[1][0] - spine[0][0]
            dy = spine[1][1] - spine[0][1]
        elif j == len(spine) - 1:
            dx = spine[-1][0] - spine[-2][0]
            dy = spine[-1][1] - spine[-2][1]
        else:
            dx = spine[j + 1][0] - spine[j - 1][0]
            dy = spine[j + 1][1] - spine[j - 1][1]
        L = math.hypot(dx, dy) or 1.0
        return -dy / L, dx / L

    left_side  = []
    right_side = []
    n_pts = len(spine)
    for j, (sx, sy) in enumerate(spine):
        t = j / (n_pts - 1)
        w = width_at(t)
        px, py = perp_at(j)
        left_side.append( (sx - px * w, sy - py * w))
        right_side.append((sx + px * w, sy + py * w))

    outline = left_side + list(reversed(right_side))
    return outline, spine


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom   = max(0.0, min(1.0, bloom))
    variant = (opts or {}).get("variant", "scarlet")

    # Thin, long tepals; half_width kept narrow for ribbon-like appearance
    tepal_len    = int(scale * 138 * (0.20 + 0.80 * bloom))
    half_width   = max(5, int(scale * 13))
    # Stamens 1.55x tepal length; long protruding stamens are the signature feature
    stamen_len   = int(tepal_len * 1.55)
    # Recurve: modest at bud (0.25), strong at full bloom (0.60)
    recurve      = 0.25 + 0.55 * bloom

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
        angle = 2 * math.pi * i / N_TEPALS - math.pi / 2 + ANGLE_OFFSET

        outline, spine = _build_tepal_outline(bcx, bcy, blen, bw, angle, recurve)

        # Shadow (enlarged from flower centre)
        shadow_pts = scale_polygon(outline, bcx, bcy, 1.08)
        cv2.fillPoly(big, [pts_to_np(shadow_pts)], c_shadow)

        # Radial gradient: crimson at base, vivid scarlet outward
        apply_gradient_radial(big, outline, c_deep, c_base, bcx, bcy)

        # Bright centre stripe (inner 28% scaled)
        hi = scale_polygon(outline, bcx, bcy, 0.28)
        cv2.fillPoly(big, [pts_to_np(hi)], c_mid)

    # --- Draw stamens (in front of tepals) ---
    for i in range(N_STAMENS):
        # Stamens between tepals, also offset by ANGLE_OFFSET
        angle = (2 * math.pi * i / N_STAMENS - math.pi / 2
                 + ANGLE_OFFSET + math.pi / N_STAMENS)

        slen = int(bstem * (0.18 + 0.82 * bloom))

        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        # Down-aware upward arc: stamens pointing downward get a stronger upward pull
        # so none droop into the stem area
        down_comp  = max(0.0, -cos_a)          # 0 when pointing up, 1 when down
        upward_pull = slen * (0.15 + 0.45 * down_comp)

        # Graceful outward-arching Bezier filament
        p0 = (bcx, bcy)
        p1 = (bcx + sin_a * slen * 0.34,
              bcy - cos_a * slen * 0.34)
        p2 = (bcx + sin_a * slen * 0.70,
              bcy - cos_a * slen * 0.70 - upward_pull * 0.42)
        p3 = (bcx + sin_a * slen * 0.96,
              bcy - cos_a * slen * 0.96 - upward_pull)

        fil_pts = bezier_cubic(p0, p1, p2, p3, steps=48)
        np_fil  = pts_to_np(fil_pts).reshape((-1, 1, 2))

        # Draw stamen: shadow then main filament (thicker for prominence)
        cv2.polylines(big, [np_fil], False, s_shadow, 8, cv2.LINE_AA)
        cv2.polylines(big, [np_fil], False, s_col,   4, cv2.LINE_AA)

        # Anther at tip: elongated ellipse
        tip_x, tip_y = int(p3[0]), int(p3[1])
        ar = max(6, int(scale * S * 6.5))
        cv2.ellipse(big, (tip_x, tip_y), (ar, max(3, ar // 2)),
                    math.degrees(angle), 0, 360, s_shadow, -1, cv2.LINE_AA)
        cv2.ellipse(big, (tip_x, tip_y), (max(4, ar - 2), max(2, ar // 2 - 1)),
                    math.degrees(angle), 0, 360, a_col, -1, cv2.LINE_AA)

    # Small centre disc
    cr = max(5, int(scale * S * 5))
    cv2.circle(big, (int(bcx), int(bcy)), cr + 4, c_shadow, -1, cv2.LINE_AA)
    cv2.circle(big, (int(bcx), int(bcy)), cr, c_base, -1, cv2.LINE_AA)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
