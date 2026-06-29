"""Curved stem with leaves, drawn as a cubic Bezier with wind sway."""
import math
import cv2
import numpy as np
from util import bezier_cubic, pts_to_np, lerp_hsv


STEM_GREEN = (30, 100, 30)
STEM_DARK  = (15, 60, 15)
LEAF_BASE  = (20, 90, 25)
LEAF_TIP   = (40, 130, 40)


def draw(canvas, cx, cy_flower, cy_bottom, scale=1.0, t=0.0, sway=0.0):
    """
    Draw a cubic Bezier stem from (cx, cy_bottom) up to (cx, cy_flower).
    sway is a lateral displacement applied to the mid control points.
    """
    h = cy_bottom - cy_flower
    # Base of stem at bottom of frame
    p0 = (cx, cy_bottom)
    # Two control points with lateral bow + sway
    bow = scale * 12
    p1 = (cx - bow + sway * 0.6, cy_bottom - h * 0.35)
    p2 = (cx + bow * 0.5 + sway, cy_bottom - h * 0.72)
    p3 = (cx, cy_flower)

    pts = bezier_cubic(p0, p1, p2, p3, steps=60)
    np_pts = pts_to_np(pts).reshape((-1, 1, 2))

    thickness = max(2, int(scale * 4))
    # Dark outline
    cv2.polylines(canvas, [np_pts], False, STEM_DARK, thickness + 2, cv2.LINE_AA)
    # Green stem
    cv2.polylines(canvas, [np_pts], False, STEM_GREEN, thickness, cv2.LINE_AA)

    # One or two leaves at 1/3 and 2/3 along the stem
    _draw_leaf(canvas, pts, 0.35, scale, left=True)
    if scale > 0.7:
        _draw_leaf(canvas, pts, 0.65, scale, left=False)


def _draw_leaf(canvas, stem_pts, frac, scale, left=True):
    idx = int(frac * (len(stem_pts) - 1))
    base_x, base_y = stem_pts[idx]

    # Leaf tip direction: perpendicular to stem tangent
    i0 = max(0, idx - 3)
    i1 = min(len(stem_pts) - 1, idx + 3)
    dx = stem_pts[i1][0] - stem_pts[i0][0]
    dy = stem_pts[i1][1] - stem_pts[i0][1]
    tang_len = math.hypot(dx, dy) or 1
    # Perpendicular
    perp_x = -dy / tang_len
    perp_y = dx / tang_len
    if not left:
        perp_x, perp_y = -perp_x, -perp_y

    leaf_len = scale * 40
    ctrl_scale = 0.55
    tip_x = base_x + perp_x * leaf_len
    tip_y = base_y + perp_y * leaf_len
    # Bezier leaf shape: base -> outward control -> tip, back side mirrored
    tang_unit = (dy / tang_len, -dx / tang_len)
    off = leaf_len * 0.28
    ctrl1 = (base_x + perp_x * leaf_len * ctrl_scale + tang_unit[0] * off,
              base_y + perp_y * leaf_len * ctrl_scale + tang_unit[1] * off)
    ctrl2 = (base_x + perp_x * leaf_len * ctrl_scale - tang_unit[0] * off,
              base_y + perp_y * leaf_len * ctrl_scale - tang_unit[1] * off)

    from util import bezier_quadratic
    side1 = bezier_quadratic((base_x, base_y), ctrl1, (tip_x, tip_y), steps=16)
    side2 = bezier_quadratic((tip_x, tip_y), ctrl2, (base_x, base_y), steps=16)
    leaf_pts = side1 + side2
    np_leaf = pts_to_np(leaf_pts)
    cv2.fillPoly(canvas, [np_leaf], LEAF_BASE)
    # Midrib
    mid_pts = pts_to_np(
        bezier_quadratic((base_x, base_y), ctrl1, (tip_x, tip_y), steps=12)
    ).reshape((-1, 1, 2))
    cv2.polylines(canvas, [mid_pts], False, STEM_DARK, 1, cv2.LINE_AA)
