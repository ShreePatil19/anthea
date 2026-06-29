"""
Headless self test. Renders each flower at multiple bloom and scale values,
saves PNGs to samples/, checks colour gates, and returns pass/fail.
Run: python selftest.py
"""
import os
import sys
import math
import time
import numpy as np
import cv2

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from flowers import sunflower, blue_rose, spider_lily
from flowers import stem
import config

os.makedirs("samples", exist_ok=True)

W, H = 900, 700

# -----------------------------------------------------------------------
# Colour gate
# -----------------------------------------------------------------------

# Expected HSV hue ranges for each species (H 0..179 in OpenCV)
COLOUR_GATES = {
    "sunflower":   [(20, 38)],           # yellow to amber
    "blue_rose":   [(100, 135)],         # blue
    "spider_lily": [(0, 10), (165, 179)],  # scarlet/crimson
}


def _median_petal_hue(img_bgr, cx, cy, radius, centre_mask_r=None):
    """
    Return the median hue (0..179) of pixels in the outer petal ring,
    excluding the centre disc area.
    """
    h, w = img_bgr.shape[:2]
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Outer annulus mask
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (int(cx), int(cy)), int(radius), 255, -1)
    if centre_mask_r:
        cv2.circle(mask, (int(cx), int(cy)), int(centre_mask_r), 0, -1)

    # Exclude near-black, near-white, and very low saturation (background and highlights)
    sat = img_hsv[:, :, 1]
    val = img_hsv[:, :, 2]
    colour_mask = (sat > 80) & (val > 60) & (val < 252)
    combined = mask & colour_mask.astype(np.uint8) * 255

    hue_vals = img_hsv[:, :, 0][combined > 0]
    if len(hue_vals) < 50:
        return None
    return int(np.median(hue_vals))


def colour_gate(species, img_bgr, cx, cy, radius):
    """Return (passed: bool, hue: int or None, reason: str)."""
    # Exclude only the small central disc, not the petals
    centre_r = max(12, int(radius * 0.18))
    hue = _median_petal_hue(img_bgr, cx, cy, radius, centre_r)
    if hue is None:
        return False, None, "too few coloured pixels to measure"
    ranges = COLOUR_GATES[species]
    for lo, hi in ranges:
        if lo <= hue <= hi:
            return True, hue, f"hue={hue} in [{lo},{hi}]"
    range_str = " or ".join(f"[{lo},{hi}]" for lo, hi in ranges)
    return False, hue, f"hue={hue} not in {range_str}"


# -----------------------------------------------------------------------
# Render helpers
# -----------------------------------------------------------------------

def _blank():
    return np.zeros((H, W, 3), dtype=np.uint8)


def _bg():
    bg = np.zeros((H, W, 3), dtype=np.uint8)
    for row in range(H):
        frac = row / H
        bg[row, :] = (int(30 + frac * 20), int(30 + frac * 15), int(40 + frac * 10))
    return bg


def render_and_save(module, species, bloom, scale, filename):
    canvas = _bg()
    cx, cy = W // 2, H // 2 - 30
    # Draw stem first, then flower on top
    stem.draw(canvas, cx, cy, H - 20, scale=scale, t=0.0, sway=0.0)
    module.draw(canvas, cx, cy, bloom=bloom, scale=scale, t=0.0, opts=None)

    out_path = os.path.join("samples", filename)
    cv2.imwrite(out_path, canvas)
    print(f"  saved {out_path}")
    return canvas, cx, cy


# -----------------------------------------------------------------------
# Test suite
# -----------------------------------------------------------------------

TESTS = [
    ("sunflower",   sunflower,   [(0.0, 1.0, "sunflower_bloom_0.png"),
                                   (0.5, 1.0, "sunflower_bloom_50.png"),
                                   (1.0, 1.0, "sunflower_bloom_100.png"),
                                   (1.0, 1.5, "sunflower_bloom_100_lg.png"),
                                   (1.0, 0.7, "sunflower_bloom_100_sm.png")]),
    ("blue_rose",   blue_rose,   [(0.0, 1.0, "blue_rose_bloom_0.png"),
                                   (0.5, 1.0, "blue_rose_bloom_50.png"),
                                   (1.0, 1.0, "blue_rose_bloom_100.png"),
                                   (1.0, 1.5, "blue_rose_bloom_100_lg.png"),
                                   (1.0, 0.7, "blue_rose_bloom_100_sm.png")]),
    ("spider_lily", spider_lily, [(0.0, 1.0, "spider_lily_bloom_0.png"),
                                   (0.5, 1.0, "spider_lily_bloom_50.png"),
                                   (1.0, 1.0, "spider_lily_bloom_100.png"),
                                   (1.0, 1.5, "spider_lily_bloom_100_lg.png"),
                                   (1.0, 0.7, "spider_lily_bloom_100_sm.png")]),
]


class _FakeHand:
    """Minimal stand-in for a tracked hand, for headless gesture tests."""
    def __init__(self, handedness, position, openness=0.5, pinch=0.0,
                 depth=0.5, extended_fingers=0):
        self.handedness = handedness
        self.position = position
        self.openness = openness
        self.pinch = pinch
        self.depth = depth
        self.extended_fingers = extended_fingers


def _garden_test():
    """Drive the Controller with synthetic hands and verify count control."""
    from controller import Controller
    from renderer import render_garden, demo_background, draw_hud

    ctrl = Controller(W, H)
    ok = True

    # Right hand shows 3 fingers, left hand open. Hold past the debounce window.
    for step in range(20):
        t = step * 0.05
        left  = _FakeHand("Left",  (W * 0.40, H * 0.5), openness=0.9, pinch=0.0)
        right = _FakeHand("Right", (W * 0.60, H * 0.5), extended_fingers=3)
        flowers = ctrl.update([left, right], t)
    n3 = len(flowers)
    print(f"  3 fingers -> {n3} flowers {'PASS' if n3 == 3 else 'FAIL'}")
    ok = ok and n3 == 3

    # Now show 5 fingers; count should climb to 5.
    for step in range(20):
        t = 2.0 + step * 0.05
        left  = _FakeHand("Left",  (W * 0.30, H * 0.5), openness=0.9)
        right = _FakeHand("Right", (W * 0.70, H * 0.5), extended_fingers=5)
        flowers = ctrl.update([left, right], t)
    n5 = len(flowers)
    print(f"  5 fingers -> {n5} flowers {'PASS' if n5 == 5 else 'FAIL'}")
    ok = ok and n5 == 5

    # Fist (0 fingers) clears the garden.
    for step in range(20):
        t = 4.0 + step * 0.05
        right = _FakeHand("Right", (W * 0.70, H * 0.5), extended_fingers=0)
        left  = _FakeHand("Left",  (W * 0.30, H * 0.5), openness=0.1)
        flowers = ctrl.update([left, right], t)
    n0 = len(flowers)
    print(f"  fist     -> {n0} flowers {'PASS' if n0 == 0 else 'FAIL'}")
    ok = ok and n0 == 0

    # Render a 5-flower garden frame for visual inspection. Hands held a
    # moderate distance apart so five blooms sit at a sensible size.
    ctrl2 = Controller(W, H)
    for step in range(24):
        t = step * 0.05
        left  = _FakeHand("Left",  (W * 0.44, H * 0.42), openness=0.85)
        right = _FakeHand("Right", (W * 0.56, H * 0.42), extended_fingers=5)
        flowers = ctrl2.update([left, right], t)
    canvas = demo_background(W, H, 3.0)
    render_garden(canvas, flowers, 3.0)
    draw_hud(canvas, ctrl2, hand_count=2, fps=30, t=3.0, hint_fade=1.0)
    cv2.imwrite("samples/garden_5.png", canvas)
    print("  saved samples/garden_5.png")

    # Also render a 3-flower blue rose garden to show species + count together.
    ctrl3 = Controller(W, H)
    ctrl3.species_idx = 1
    for step in range(24):
        t = step * 0.05
        left  = _FakeHand("Left",  (W * 0.46, H * 0.46), openness=0.8)
        right = _FakeHand("Right", (W * 0.54, H * 0.46), extended_fingers=3)
        flowers = ctrl3.update([left, right], t)
    canvas = demo_background(W, H, 2.0)
    render_garden(canvas, flowers, 2.0)
    draw_hud(canvas, ctrl3, hand_count=2, fps=30, t=2.0, hint_fade=0.0)
    cv2.imwrite("samples/garden_3_rose.png", canvas)
    print("  saved samples/garden_3_rose.png")

    return ok


def run():
    print("=== anthea selftest ===")
    gate_results = {}
    all_passed = True

    for species, module, cases in TESTS:
        print(f"\n-- {species} --")
        gate_img = None
        for bloom, scale, fname in cases:
            img, cx, cy = render_and_save(module, species, bloom, scale, fname)
            # Use the full-bloom image for colour gate
            if bloom == 1.0 and scale == 1.0:
                gate_img = img
                gate_cx, gate_cy = cx, cy

        # Colour gate on full bloom render
        # radius covers petal extent at scale=1.0; inner exclusion skips the disc
        if gate_img is not None:
            radius = 90
            passed, hue, reason = colour_gate(species, gate_img, gate_cx, gate_cy, radius)
            gate_results[species] = (passed, hue, reason)
            status = "PASS" if passed else "FAIL"
            print(f"  colour gate: {status}  ({reason})")
            if not passed:
                all_passed = False
        else:
            gate_results[species] = (False, None, "no full-bloom render")
            all_passed = False

    # Demo frames
    print("\n-- demo frames --")
    try:
        from main import run_demo
        run_demo(headless=True, n_frames=3)
        print("  demo mode: ok")
        # Save a demo frame
        from controller import FlowerState
        from renderer import render_flower, demo_background, draw_hud
        flower = FlowerState(W // 2, H // 2, species_idx=1)
        flower.bloom = 0.8
        flower.scale = 1.1
        canvas = demo_background(W, H, 5.0)
        render_flower(canvas, flower, 5.0)
        draw_hud(canvas, flower, 0, 30, 5.0, hint_fade=1.0)
        demo_path = "samples/demo_frame.png"
        cv2.imwrite(demo_path, canvas)
        print(f"  saved {demo_path}")
    except Exception as e:
        print(f"  demo mode error: {e}")
        all_passed = False

    # Garden gesture control test (synthetic hands, no camera)
    print("\n-- garden gesture control --")
    try:
        if not _garden_test():
            all_passed = False
    except Exception as e:
        print(f"  garden test error: {e}")
        all_passed = False

    print(f"\n=== colour gate results ===")
    for species, (passed, hue, reason) in gate_results.items():
        print(f"  {species}: {'PASS' if passed else 'FAIL'} - {reason}")

    print(f"\n=== selftest {'PASSED' if all_passed else 'FAILED'} ===")
    return all_passed, gate_results


if __name__ == "__main__":
    ok, gates = run()
    sys.exit(0 if ok else 1)
