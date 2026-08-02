"""
Sunflower renderer.
Two interleaved rows of strap-like ray petals with creases, a large disc
with golden angle seed packing and a bright floret ring, green bracts.
draw(canvas, cx, cy, bloom, scale, t, opts) is the public interface.
"""
import math
import cv2
import numpy as np

from util import (
    curved_petal_polygon, scale_polygon, pts_to_np,
    gradient_circle_hsv, lerp_hsv, lerp_colour, hsv_to_bgr,
)

GOLDEN_ANGLE = 137.507764  # degrees
SS = 3

# Palette
P_BASE   = hsv_to_bgr(21, 245, 235)   # deep amber orange at the disc
P_MID    = hsv_to_bgr(26, 235, 255)   # golden yellow
P_TIP    = hsv_to_bgr(30, 205, 255)   # warm yellow tip
P_CREASE = hsv_to_bgr(20, 240, 170)   # darker amber crease lines
P_BACK_D = hsv_to_bgr(22, 240, 185)   # back row darker
SHADOW   = hsv_to_bgr(16, 230,  60)

BRACT_BASE = hsv_to_bgr(55, 190,  95)
BRACT_TIP  = hsv_to_bgr(48, 170, 135)
BRACT_DARK = hsv_to_bgr(58, 200,  45)

DISC_RIM   = hsv_to_bgr(23, 200, 165)  # golden brown rim
DISC_MID   = hsv_to_bgr(18, 215, 105)
DISC_CORE  = hsv_to_bgr(14, 210,  55)  # dark umber centre
SEED_DARK  = hsv_to_bgr(12, 200,  28)
SEED_GOLD  = hsv_to_bgr(24, 225, 160)
FLORET     = hsv_to_bgr(27, 235, 230)  # bright golden open florets


def _jit(i, k=1.0):
    return math.sin(i * 12.9898 + k * 78.233) % 1.0 * 2.0 - 1.0


def _ray_petal(canvas, bx, by, length, max_hw, angle, bow,
               c_base, c_mid, c_tip, crease_col, n=30, cast_shadow=False,
               notch=False):
    """
    One strap-like ray petal from (bx,by) outward along angle.
    Gradient follows the petal spine; 3 crease lines run along it.
    notch=True gives the tip a small V split instead of a single point.
    """
    ox, oy = math.sin(angle), -math.cos(angle)
    lx, ly = math.cos(angle),  math.sin(angle)

    spine = []
    for i in range(n + 1):
        t = i / n
        lat = bow * length * (t ** 2) * 0.22
        spine.append((bx + ox * length * t + lx * lat,
                      by + oy * length * t + ly * lat))

    def hw(t):
        env = (t ** 0.40) * ((1 - t) ** 0.85)
        w = max_hw * env / 0.325   # normalise peak to ~1
        if notch and t > 0.86:
            w = max(w, max_hw * 0.24 * (1.0 - (t - 0.86) / 0.14 * 0.45))
        return w

    left, right = [], []
    for j, (sx, sy) in enumerate(spine):
        t = j / n
        if j == 0:
            dx = spine[1][0] - sx; dy = spine[1][1] - sy
        elif j == n:
            dx = sx - spine[-2][0]; dy = sy - spine[-2][1]
        else:
            dx = spine[j + 1][0] - spine[j - 1][0]
            dy = spine[j + 1][1] - spine[j - 1][1]
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        w = hw(t)
        left.append((sx - px * w, sy - py * w))
        right.append((sx + px * w, sy + py * w))
    if notch:
        outline = left + [spine[int(n * 0.90)]] + list(reversed(right))
    else:
        outline = left + list(reversed(right))
    np_out = pts_to_np(outline)

    if cast_shadow:
        off = 3.0 * SS
        shifted = np_out + np.array([int(off), int(off)])
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [shifted], SHADOW)
        cv2.addWeighted(overlay, 0.30, canvas, 0.70, 0, canvas)

    # Gradient fill in bands along the spine
    x0 = max(0, int(np_out[:, 0].min())); x1 = min(canvas.shape[1] - 1, int(np_out[:, 0].max()))
    y0 = max(0, int(np_out[:, 1].min())); y1 = min(canvas.shape[0] - 1, int(np_out[:, 1].max()))
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=np.uint8)
    cv2.fillPoly(mask, [np_out - [x0, y0]], 255)
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    d = np.hypot(xx - bx, yy - by) / max(1.0, length)
    d = np.clip(d, 0.0, 1.0)
    region = canvas[y0:y1 + 1, x0:x1 + 1]
    bands = 12
    for b in range(bands):
        t = (b + 0.5) / bands
        if t < 0.45:
            colour = lerp_hsv(c_base, c_mid, t / 0.45)
        else:
            colour = lerp_hsv(c_mid, c_tip, (t - 0.45) / 0.55)
        hi = (b + 1) / bands if b < bands - 1 else 1.01
        sel = (mask > 0) & (d >= b / bands) & (d < hi)
        region[sel] = np.array(colour, dtype=np.uint8)
    canvas[y0:y1 + 1, x0:x1 + 1] = region

    # Crease lines along the spine
    overlay = canvas.copy()
    for off in (-0.42, 0.0, 0.42):
        line = []
        for j, (sx, sy) in enumerate(spine[2:n - 1], start=2):
            t = j / n
            if j == 2:
                dx = spine[3][0] - sx; dy = spine[3][1] - sy
            else:
                dx = spine[j + 1][0] - spine[j - 1][0]
                dy = spine[j + 1][1] - spine[j - 1][1]
            L = math.hypot(dx, dy) or 1.0
            px, py = -dy / L, dx / L
            w = hw(t) * off
            line.append((sx + px * w, sy + py * w))
        np_line = pts_to_np(line).reshape((-1, 1, 2))
        cv2.polylines(overlay, [np_line], False, crease_col, SS, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.30, canvas, 0.70, 0, canvas)


def _bracts(canvas, cx, cy, disc_r, petal_len, n=13):
    blen = int(disc_r + petal_len * 0.52)
    bw   = int(disc_r * 0.20)
    for i in range(n):
        angle = 2 * math.pi * i / n + math.pi / n
        pts = curved_petal_polygon(cx, cy, blen, bw, angle,
                                   curvature=0.03, n_pts=20)
        cv2.fillPoly(canvas, [pts_to_np(scale_polygon(pts, cx, cy, 1.04))], BRACT_DARK)
        cv2.fillPoly(canvas, [pts_to_np(pts)], BRACT_BASE)
        tip = scale_polygon(pts, cx, cy, 0.94)
        cv2.fillPoly(canvas, [pts_to_np(tip)], BRACT_TIP)


def _disc(canvas, cx, cy, disc_r):
    """Layered disc: gradient base, dense golden angle seeds, floret ring."""
    overlay = canvas.copy()
    cv2.circle(overlay, (int(cx), int(cy)), int(disc_r + 3 * SS),
               SHADOW, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.55, canvas, 0.45, 0, canvas)
    gradient_circle_hsv(canvas, cx, cy, int(disc_r), DISC_RIM, DISC_CORE, steps=26)

    # Seeds as small oriented ellipses so the spiral lattice reads
    n = 300
    for k in range(1, n + 1):
        r_frac = math.sqrt(k / n)
        r = disc_r * r_frac * 0.97
        theta = math.radians(k * GOLDEN_ANGLE)
        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta)
        dot = max(2, int(disc_r * 0.048 * (0.55 + 0.55 * r_frac)))
        col = lerp_hsv(SEED_DARK, SEED_GOLD, r_frac ** 1.4)
        vjit = int(14 * _jit(k))
        col = tuple(int(np.clip(c + vjit, 0, 255)) for c in col)
        ori = math.degrees(theta) + 28
        cv2.ellipse(canvas, (int(round(sx)), int(round(sy))),
                    (dot, max(1, int(dot * 0.62))), ori, 0, 360,
                    col, -1, cv2.LINE_AA)
        if r_frac > 0.35:
            hi = lerp_hsv(col, SEED_GOLD, 0.5)
            cv2.ellipse(canvas, (int(round(sx - dot * 0.25)), int(round(sy - dot * 0.25))),
                        (max(1, int(dot * 0.4)), max(1, int(dot * 0.22))), ori, 0, 360,
                        hi, -1, cv2.LINE_AA)

    # Ring of bright open florets near the rim
    n_fl = 42
    for k in range(n_fl):
        theta = 2 * math.pi * k / n_fl + 0.07 * _jit(k)
        r = disc_r * (0.86 + 0.05 * _jit(k, 2.0))
        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta)
        dot = max(1, int(disc_r * 0.030))
        cv2.circle(canvas, (int(round(sx)), int(round(sy))), dot,
                   FLORET, -1, cv2.LINE_AA)

    _dome_shade(canvas, cx, cy, disc_r)


def _dome_shade(canvas, cx, cy, r):
    """Smooth directional shading so the disc reads as a dome, lit top left."""
    x0 = max(0, int(cx - r)); x1 = min(canvas.shape[1] - 1, int(cx + r))
    y0 = max(0, int(cy - r)); y1 = min(canvas.shape[0] - 1, int(cy + r))
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=np.uint8)
    cv2.circle(mask, (int(cx) - x0, int(cy) - y0), int(r), 255, -1, cv2.LINE_AA)
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    lx, ly = cx - r * 0.28, cy - r * 0.28
    d = np.hypot(xx - lx, yy - ly) / (r * 1.9)
    f = np.clip(1.16 - 0.42 * d, 0.72, 1.16)
    region = canvas[y0:y1 + 1, x0:x1 + 1].astype(np.float32)
    shaded = np.clip(region * f[..., None], 0, 255).astype(np.uint8)
    sel = mask > 0
    region = canvas[y0:y1 + 1, x0:x1 + 1]
    region[sel] = shaded[sel]
    canvas[y0:y1 + 1, x0:x1 + 1] = region


def draw(canvas, cx, cy, bloom=1.0, scale=1.0, t=0.0, opts=None):
    bloom = max(0.0, min(1.0, bloom))
    ease = bloom ** 0.9

    base_r    = scale * 112
    disc_r    = max(12, base_r * 0.46 * (0.30 + 0.70 * ease))
    petal_len = max(6,  base_r * 0.80 * (0.12 + 0.88 * ease))
    n_petals  = 21

    H, W = canvas.shape[:2]
    big = cv2.resize(canvas, (W * SS, H * SS), interpolation=cv2.INTER_LINEAR)
    bcx, bcy = cx * SS, cy * SS
    bdisc = disc_r * SS
    bplen = petal_len * SS
    max_hw = bplen * 0.14
    sway = 0.02 * math.sin(t * 0.9)

    _bracts(big, bcx, bcy, bdisc, bplen)

    if bloom > 0.04:
        # Back row: darker, slightly longer, offset half a gap
        for i in range(n_petals):
            angle = (2 * math.pi * i / n_petals + math.pi / n_petals + sway
                     + 0.025 * _jit(i, 13.0))
            L = bplen * (1.06 + 0.08 * _jit(i, 4.0))
            bx = bcx + (bdisc * 0.88) * math.sin(angle)
            by = bcy - (bdisc * 0.88) * math.cos(angle)
            _ray_petal(big, bx, by, L, max_hw * 0.94, angle,
                       _jit(i, 6.0), P_BACK_D, P_BACK_D, P_MID, P_CREASE)

        # Front row
        for i in range(n_petals):
            angle = 2 * math.pi * i / n_petals + sway + 0.030 * _jit(i, 11.0)
            L = bplen * (1.0 + 0.10 * _jit(i))
            bx = bcx + (bdisc * 0.88) * math.sin(angle)
            by = bcy - (bdisc * 0.88) * math.cos(angle)
            _ray_petal(big, bx, by, L, max_hw, angle,
                       _jit(i, 2.0), P_BASE, P_MID, P_TIP, P_CREASE,
                       cast_shadow=True, notch=(_jit(i, 8.0) > -0.1))

    _disc(big, bcx, bcy, bdisc)

    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    np.copyto(canvas, out)
