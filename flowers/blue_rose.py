"""
Blue rose renderer.
Top view: spiral nested layers of broad cupped petals, deep blue bases
fading to lighter cool blue edges, with a furled spiral core.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import pts_to_np, lerp_hsv, hsv_to_bgr, curved_petal_polygon, scale_polygon

SEPAL   = hsv_to_bgr( 80, 170,  82)
SEPAL_D = hsv_to_bgr( 76, 190,  42)
SHADOW  = hsv_to_bgr(122, 255,  38)

SS = 3
GOLDEN = 2.39996  # golden angle in radians

# Layer spec, outer first: (n_petals, r_outer_frac, half_ang_frac, bloom_thresh)
LAYERS = [
    (7, 1.00, 1.30, 0.00),
    (6, 0.74, 1.28, 0.12),
    (5, 0.53, 1.24, 0.30),
    (4, 0.36, 1.18, 0.52),
]


def _jit(i, k=1.0):
    return math.sin(i * 12.9898 + k * 78.233) % 1.0 * 2.0 - 1.0


def _petal_poly(cx, cy, th0, half_ang, r0, r1, wave_phase, n=56):
    """Rounded fan petal spanning +-half_ang at angle th0, radius r0 to r1."""
    pts = []
    for i in range(n + 1):
        u = i / n
        a = th0 + (u * 2 - 1) * half_ang
        shoulder = math.sin(u * math.pi) ** 0.42
        rr = r0 + (r1 - r0) * (0.50 + 0.50 * shoulder)
        rr *= 1.0 + 0.030 * math.sin(u * 3.1 * math.pi + wave_phase)
        rr *= 1.0 - 0.035 * math.exp(-((u - 0.5) ** 2) / 0.006)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    for i in range(9):
        u = i / 8
        a = th0 + (1 - 2 * u) * half_ang * 0.50
        pts.append((cx + math.cos(a) * r0, cy + math.sin(a) * r0))
    return pts


def _radial_gradient_fill(canvas, pts, cx, cy, r0, r1, c_base, c_edge):
    """Fill polygon with colour graded by distance from the flower centre."""
    np_pts = pts_to_np(pts)
    x0 = max(0, int(np_pts[:, 0].min())); x1 = min(canvas.shape[1] - 1, int(np_pts[:, 0].max()))
    y0 = max(0, int(np_pts[:, 1].min())); y1 = min(canvas.shape[0] - 1, int(np_pts[:, 1].max()))
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=np.uint8)
    cv2.fillPoly(mask, [np_pts - [x0, y0]], 255)
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    d = (np.hypot(xx - cx, yy - cy) - r0) / max(1.0, (r1 - r0))
    d = np.clip(d, 0.0, 1.0)
    region = canvas[y0:y1 + 1, x0:x1 + 1]
    bands = 16
    for b in range(bands):
        colour = np.array(lerp_hsv(c_base, c_edge, (b + 0.5) / bands), dtype=np.uint8)
        hi = (b + 1) / bands if b < bands - 1 else 1.01
        sel = (mask > 0) & (d >= b / bands) & (d < hi)
        region[sel] = colour
    canvas[y0:y1 + 1, x0:x1 + 1] = region


def _crescent(cx, cy, r_mid, thick, a0, a1, n=36):
    pts = []
    for i in range(n + 1):
        u = i / n
        a = a0 + (a1 - a0) * u
        w = thick * (math.sin(u * math.pi) ** 0.6) / 2
        pts.append((cx + math.cos(a) * (r_mid + w), cy + math.sin(a) * (r_mid + w)))
    for i in range(n, -1, -1):
        u = i / n
        a = a0 + (a1 - a0) * u
        w = thick * (math.sin(u * math.pi) ** 0.6) / 2
        pts.append((cx + math.cos(a) * (r_mid - w), cy + math.sin(a) * (r_mid - w)))
    return pts


def _sepals(canvas, cx, cy, radius):
    for i in range(5):
        angle = 2 * math.pi * i / 5 + math.pi / 5
        pts = curved_petal_polygon(cx, cy, int(radius * 1.30),
                                   int(radius * 0.22), angle,
                                   curvature=0.06, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.05))], SEPAL_D)
        cv2.fillPoly(canvas, [pts_to_np(pts)], SEPAL)


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))
    ease = bloom ** 0.9

    base_r = scale * 95 * (0.40 + 0.60 * ease)

    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * SS, H * SS), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * SS, cy * SS
    br = base_r * SS

    _sepals(big, bcx, bcy, int(br * 0.55 + scale * SS * 14))

    sway = 0.04 * math.sin(t * 0.7)

    n_layers = len(LAYERS)
    for li, (n, r_f, ang_f, thresh) in enumerate(LAYERS):
        lt = li / (n_layers - 1)          # 0 outer -> 1 inner
        if bloom < thresh:
            continue
        unfurl = min(1.0, (bloom - thresh) / max(0.01, 1.0 - thresh))
        open_s = 0.32 + 0.68 * unfurl

        r1 = br * r_f * open_s
        r0 = r1 * (0.28 + 0.10 * lt)
        half_ang = (math.pi / n) * ang_f
        rot = li * GOLDEN + sway

        # Deep blue bases, lighter cool blue edges; inner layers darker
        c_base = hsv_to_bgr(117 - lt * 2, 252, 105 + (1 - lt) * 35)
        c_edge = hsv_to_bgr(106 + lt * 3, 165 - lt * 25, 240 + lt * 15)
        c_rim  = hsv_to_bgr(104, 95, 255)

        for i in range(n):
            th0 = rot + 2 * math.pi * i / n + _jit(li * 10 + i) * 0.05
            wave_phase = _jit(li * 10 + i, 3.0) * math.pi
            rr1 = r1 * (1.0 + 0.04 * _jit(li * 10 + i, 5.0))
            pts = _petal_poly(bcx, bcy, th0, half_ang, r0, rr1, wave_phase)

            # Crevice shadow beneath the petal for depth
            overlay = big.copy()
            sh = scale_polygon(pts, bcx, bcy, 1.045)
            cv2.fillPoly(overlay, [pts_to_np(sh)], SHADOW)
            cv2.addWeighted(overlay, 0.42, big, 0.58, 0, big)

            _radial_gradient_fill(big, pts, bcx, bcy, r0, rr1, c_base, c_edge)

            # Rolled rim light along the outer arc only
            arc = pts[:57]
            np_arc = pts_to_np(arc).reshape((-1, 1, 2))
            overlay = big.copy()
            cv2.polylines(overlay, [np_arc], False, c_rim,
                          max(2, int(1.4 * scale * SS)), cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.55, big, 0.45, 0, big)

    # Furled spiral core, opens only at high bloom
    core_r = br * 0.22 * (0.6 + 0.4 * ease)
    core_open = max(0.0, (bloom - 0.55) / 0.45)
    c_dark = hsv_to_bgr(119, 255, 80)
    cv2.circle(big, (int(bcx), int(bcy)), max(3, int(core_r * 1.02)),
               hsv_to_bgr(117, 250, 120), -1, cv2.LINE_AA)
    for k in range(4):
        u = k / 3.0
        rm = core_r * (0.30 + 0.70 * (1 - u)) * (0.7 + 0.3 * core_open)
        a0 = k * 2.1 + GOLDEN + sway
        arc_span = 3.6 - u * 0.8
        cres = _crescent(bcx, bcy, rm, rm * 0.62, a0, a0 + arc_span)
        col = lerp_hsv(c_dark, hsv_to_bgr(108, 170, 235), 0.40 + 0.45 * u)
        overlay = big.copy()
        cv2.fillPoly(overlay, [pts_to_np(cres)], col)
        cv2.addWeighted(overlay, 0.9, big, 0.1, 0, big)
    cv2.circle(big, (int(bcx), int(bcy)), max(2, int(core_r * 0.16)),
               hsv_to_bgr(113, 220, 150), -1, cv2.LINE_AA)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
