"""
Spider lily (Lycoris radiata) renderer.
6 thin strongly recurved wavy tepals + 6 very long arching stamens and a style.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
opts may include {'variant': 'white'} for Lycoris albiflora.
"""
import math
import cv2
import numpy as np

from util import (
    pts_to_np, bezier_cubic, lerp_hsv, hsv_to_bgr,
)

# Scarlet/crimson palette
T_BASE    = hsv_to_bgr(1,  235, 215)   # vivid scarlet at the throat
T_TIP     = hsv_to_bgr(176, 225, 235)  # crimson pink toward the tip
T_MID     = hsv_to_bgr(4,  245, 250)   # bright mid scarlet
T_SHADOW  = hsv_to_bgr(178, 220,  80)  # dark crimson shadow
T_HILIGHT = hsv_to_bgr(6,  130, 255)   # pale warm highlight

S_BASE = hsv_to_bgr(2,  230, 200)   # filament scarlet at the base
S_TIP  = hsv_to_bgr(174, 150, 250)  # filament fades to bright pink
A_COL  = hsv_to_bgr(14, 200, 220)   # anther burnt orange

# White variant (Lycoris albiflora)
W_BASE    = hsv_to_bgr(26,  45, 250)
W_TIP     = hsv_to_bgr(24,  18, 255)
W_MID     = hsv_to_bgr(28,  25, 255)
W_SHADOW  = hsv_to_bgr(24,  70, 170)
W_HILIGHT = hsv_to_bgr(28,  10, 255)
W_S_BASE  = hsv_to_bgr(26,  60, 240)
W_S_TIP   = hsv_to_bgr(24,  20, 255)
W_ANTHER  = hsv_to_bgr(48, 170, 235)

N_TEPALS  = 6
N_STAMENS = 6
SS = 3   # supersampling factor


def _palette(variant):
    if variant == "white":
        return {
            "base": W_BASE, "tip": W_TIP, "mid": W_MID,
            "shadow": W_SHADOW, "hilight": W_HILIGHT,
            "s_base": W_S_BASE, "s_tip": W_S_TIP, "anther": W_ANTHER,
        }
    return {
        "base": T_BASE, "tip": T_TIP, "mid": T_MID,
        "shadow": T_SHADOW, "hilight": T_HILIGHT,
        "s_base": S_BASE, "s_tip": S_TIP, "anther": A_COL,
    }


def _jitter(i, k=1.0):
    """Deterministic pseudo random in -1..1 per index."""
    return math.sin(i * 12.9898 + k * 78.233) % 1.0 * 2.0 - 1.0


def _tepal_spine(cx, cy, length, angle, recurve, curl, steps=40):
    """
    Spine of one tepal as a cubic Bezier in (outward, lateral) space.
    recurve pulls the tip back toward the throat, curl sweeps it sideways,
    together they give the hooked, curled Lycoris silhouette.
    """
    ox, oy = math.sin(angle), -math.cos(angle)     # outward unit vector
    lx, ly = math.cos(angle),  math.sin(angle)     # lateral unit vector

    def at(u_out, u_lat):
        return (cx + ox * length * u_out + lx * length * u_lat,
                cy + oy * length * u_out + ly * length * u_lat)

    p0 = at(0.0, 0.0)
    p1 = at(0.46, curl * 0.04)
    p2 = at(0.96, curl * 0.22)
    p3 = at(1.0 - recurve * 0.34, curl * (0.30 + recurve * 0.22))
    return bezier_cubic(p0, p1, p2, p3, steps=steps)


def _ribbon(spine, half_width_fn):
    """Build a closed outline around a spine given a half width per t."""
    n = len(spine)
    left, right = [], []
    for j, (sx, sy) in enumerate(spine):
        if j == 0:
            dx = spine[1][0] - sx; dy = spine[1][1] - sy
        elif j == n - 1:
            dx = sx - spine[-2][0]; dy = sy - spine[-2][1]
        else:
            dx = spine[j + 1][0] - spine[j - 1][0]
            dy = spine[j + 1][1] - spine[j - 1][1]
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        t = j / (n - 1)
        wl, wr = half_width_fn(t)
        left.append((sx - px * wl, sy - py * wl))
        right.append((sx + px * wr, sy + py * wr))
    return left + list(reversed(right))


def _gradient_fill_poly(canvas, pts, spine, c_base, c_tip):
    """Fill polygon with a gradient that follows the spine base to tip."""
    np_pts = pts_to_np(pts)
    x0 = max(0, int(np_pts[:, 0].min())); x1 = min(canvas.shape[1] - 1, int(np_pts[:, 0].max()))
    y0 = max(0, int(np_pts[:, 1].min())); y1 = min(canvas.shape[0] - 1, int(np_pts[:, 1].max()))
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=np.uint8)
    cv2.fillPoly(mask, [np_pts - [x0, y0]], 255)
    # Distance along spine approximated by distance from spine start point
    sx, sy = spine[0]
    ex, ey = spine[-1]
    span = math.hypot(ex - sx, ey - sy) or 1.0
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    d = np.hypot(xx - sx, yy - sy) / (span * 1.15)
    d = np.clip(d, 0.0, 1.0)
    # Blend colours in a small number of bands (cheap, smooth after AA downscale)
    region = canvas[y0:y1 + 1, x0:x1 + 1]
    bands = 14
    for b in range(bands):
        t = (b + 0.5) / bands
        colour = np.array(lerp_hsv(c_base, c_tip, t), dtype=np.uint8)
        sel = (mask > 0) & (d >= b / bands) & (d < (b + 1) / bands + (1 if b == bands - 1 else 0))
        region[sel] = colour
    canvas[y0:y1 + 1, x0:x1 + 1] = region


def _draw_filament(big, pts, thickness, c_base, c_tip, shadow):
    """Polyline drawn in colour graded segments from base to tip."""
    n = len(pts)
    np_all = pts_to_np(pts).reshape((-1, 1, 2))
    cv2.polylines(big, [np_all], False, shadow, thickness + 3, cv2.LINE_AA)
    seg = 8
    for k in range(0, n - 1, seg):
        chunk = pts[k:min(k + seg + 1, n)]
        t = k / (n - 1)
        colour = lerp_hsv(c_base, c_tip, t)
        np_chunk = pts_to_np(chunk).reshape((-1, 1, 2))
        cv2.polylines(big, [np_chunk], False, colour, thickness, cv2.LINE_AA)


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom   = max(0.0, min(1.0, bloom))
    variant = (opts or {}).get("variant", "scarlet")
    pal     = _palette(variant)
    ease    = bloom ** 0.85

    tepal_len  = scale * 120 * (0.30 + 0.70 * ease)
    stamen_len = tepal_len * (1.28 + 0.24 * ease)
    recurve    = 0.25 + 0.55 * ease          # tips hook back as it opens
    curl       = 0.55 + 0.25 * ease          # pinwheel sweep, one direction
    spread     = 0.30 + 0.70 * ease          # bud = tight cluster pointing up
    base_rot   = 0.26 + 0.03 * math.sin(t * 0.8)   # keep off the stem axis

    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * SS, H * SS), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * SS, cy * SS
    blen  = tepal_len * SS
    bslen = stamen_len * SS

    # --- Tepals: narrow crinkled ribbons, curled and recurved ---
    max_hw = blen * 0.085
    tepal_order = sorted(range(N_TEPALS), key=lambda i: -abs(_jitter(i)))
    for i in tepal_order:
        offs = (i / N_TEPALS) * 2 * math.pi - math.pi
        angle = -math.pi / 2 + base_rot + offs * spread + _jitter(i) * 0.05
        spine = _tepal_spine(bcx, bcy, blen, angle, recurve, curl)

        phase_l = _jitter(i, 2.0) * math.pi
        phase_r = _jitter(i, 3.0) * math.pi

        def hw(tt, pl=phase_l, pr=phase_r):
            env = math.sin(min(tt * 1.25, 1.0) * math.pi) ** 0.8
            w = max_hw * (0.20 + 0.80 * env)
            crinkle = 0.28 * w
            wl = w + crinkle * math.sin(tt * 6.0 * math.pi + pl)
            wr = w + crinkle * math.sin(tt * 6.0 * math.pi + pr)
            return max(1.0, wl), max(1.0, wr)

        outline = _ribbon(spine, hw)

        # Soft shadow pass, offset down right
        shadow = [(x + 2.5 * SS, y + 2.5 * SS) for x, y in outline]
        overlay = big.copy()
        cv2.fillPoly(overlay, [pts_to_np(shadow)], pal["shadow"])
        cv2.addWeighted(overlay, 0.45, big, 0.55, 0, big)

        # Main fill with spine following gradient
        _gradient_fill_poly(big, outline, spine, pal["base"], pal["tip"])

        # Bright midrib stripe along the spine
        def hw_mid(tt):
            env = math.sin(min(tt * 1.25, 1.0) * math.pi) ** 0.8
            w = max_hw * (0.06 + 0.28 * env)
            return max(0.8, w), max(0.8, w)
        mid = _ribbon(spine, hw_mid)
        overlay = big.copy()
        cv2.fillPoly(overlay, [pts_to_np(mid)], pal["hilight"])
        cv2.addWeighted(overlay, 0.5, big, 0.5, 0, big)

    # --- Stamens: long thin arcs sweeping past the tepals ---
    thickness = max(2, int(round(1.1 * scale * SS)))
    n_fils = N_STAMENS + 1   # 6 stamens plus the style
    for i in range(n_fils):
        offs = ((i + 0.5) / N_STAMENS) * 2 * math.pi - math.pi
        is_style = (i == N_STAMENS)
        if is_style:
            offs = _jitter(17) * 0.4    # style leans off centre near the top
        angle = -math.pi / 2 + base_rot + offs * spread + _jitter(i, 5.0) * 0.06

        length = bslen * (1.0 + 0.06 * _jitter(i, 7.0))
        if is_style:
            length *= 1.12

        ox, oy = math.sin(angle), -math.cos(angle)
        lx, ly = math.cos(angle),  math.sin(angle)
        sweep = 0.22 + 0.08 * _jitter(i, 9.0)

        def at(u_out, u_lat):
            return (bcx + ox * length * u_out + lx * length * u_lat,
                    bcy + oy * length * u_out + ly * length * u_lat)

        p0 = at(0.02, 0.0)
        p1 = at(0.40, sweep * 0.05)
        p2 = at(0.78, sweep * 0.55)
        p3 = at(0.96, sweep)
        pts = bezier_cubic(p0, p1, p2, p3, steps=48)

        _draw_filament(big, pts, thickness, pal["s_base"], pal["s_tip"],
                       pal["shadow"])

        # Anther: tiny bar riding the filament tip, perpendicular-ish
        tx, ty = pts[-1]
        dx = pts[-1][0] - pts[-3][0]
        dy = pts[-1][1] - pts[-3][1]
        tip_deg = math.degrees(math.atan2(dy, dx))
        ar = max(4, int(3.4 * scale * SS))
        if is_style:
            cv2.circle(big, (int(tx), int(ty)), max(2, ar // 2),
                       pal["s_tip"], -1, cv2.LINE_AA)
        else:
            cv2.ellipse(big, (int(tx), int(ty)), (ar, max(2, ar // 3)),
                        tip_deg + 65, 0, 360, pal["shadow"], -1, cv2.LINE_AA)
            cv2.ellipse(big, (int(tx), int(ty)), (max(2, ar - 1), max(1, ar // 3)),
                        tip_deg + 65, 0, 360, pal["anther"], -1, cv2.LINE_AA)

    # --- Throat: small, deep, no big disc ---
    cr = max(3, int(3.2 * scale * SS))
    cv2.circle(big, (int(bcx), int(bcy)), cr + 2, pal["shadow"], -1, cv2.LINE_AA)
    cv2.circle(big, (int(bcx), int(bcy)), cr, pal["base"], -1, cv2.LINE_AA)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
