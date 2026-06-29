"""
Composites flowers and stems over the (mirrored) camera frame or demo background.
"""
import math
import numpy as np
import cv2

import config
from flowers import sunflower, blue_rose, spider_lily
from flowers import stem

SPECIES_MODULES = {
    "sunflower":   sunflower,
    "blue_rose":   blue_rose,
    "spider_lily": spider_lily,
}

# Sway parameters
_SWAY_AMP = config.sway_amplitude     # radians
_SWAY_SPD = config.sway_speed         # Hz


def _sway_offset(t, scale):
    """Lateral displacement in pixels for wind sway."""
    return math.sin(2 * math.pi * _SWAY_SPD * t) * _SWAY_AMP * scale * 30


def render_flower(canvas, flower_state, t):
    """Render the active flower and its stem onto canvas."""
    h, w = canvas.shape[:2]
    cx = flower_state.cx
    cy = flower_state.cy
    bloom = flower_state.bloom
    scale = flower_state.scale
    species = flower_state.species

    sway = _sway_offset(t, scale)

    # Stem from bottom to flower centre
    stem_bottom = h - 10
    if cy < stem_bottom:
        stem.draw(canvas, cx, cy, stem_bottom, scale=scale, t=t, sway=sway)

    # Flower
    module = SPECIES_MODULES.get(species)
    if module:
        module.draw(canvas, cx, cy, bloom=bloom, scale=scale, t=t, opts=None)


def render_garden(canvas, flowers, t):
    """Render every flower, nearer ones (lower on screen) drawn last/on top."""
    for f in sorted(flowers, key=lambda fl: fl.cy):
        render_flower(canvas, f, t)


def demo_background(w, h, t):
    """Soft gradient background for demo mode (no camera)."""
    bg = np.zeros((h, w, 3), dtype=np.uint8)
    # Subtle vertical gradient: deep blue-green at top to warm cream at bottom
    for row in range(h):
        frac = row / h
        r = int(20 + frac * 60)
        g = int(25 + frac * 50)
        b = int(40 + frac * 30)
        bg[row, :] = (b, g, r)
    # Gentle shimmer: time-varying brightness band
    band_y = int((math.sin(t * 0.4) * 0.3 + 0.5) * h)
    cv2.ellipse(bg, (w // 2, band_y), (w // 2, h // 6),
                0, 0, 360, (55, 55, 60), -1, cv2.LINE_AA)
    cv2.GaussianBlur(bg, (91, 91), 0, dst=bg)
    return bg


def draw_hud(canvas, garden, hand_count, fps, t, hint_fade=1.0):
    """garden may be a Controller, a list of FlowerState, or a single FlowerState."""
    if not config.show_hud:
        return
    h, w = canvas.shape[:2]

    # Normalise the argument into a small summary.
    if hasattr(garden, "flowers"):                 # Controller
        flowers = garden.flowers
        species_name = garden.species
        bloom = garden.bloom
        scale_val = garden.scale
    elif isinstance(garden, (list, tuple)):        # list of FlowerState
        flowers = list(garden)
        first = flowers[0] if flowers else None
        species_name = first.species if first else "-"
        bloom = (sum(f.bloom for f in flowers) / len(flowers)) if flowers else 0.0
        scale_val = first.scale if first else 0.0
    else:                                          # single FlowerState
        flowers = [garden]
        species_name = garden.species
        bloom = garden.bloom
        scale_val = garden.scale

    species_name = species_name.replace("_", " ").title()
    lines = [
        f"Flowers: {len(flowers)}",
        f"Species: {species_name}",
        f"Bloom: {int(bloom * 100)}%",
        f"Size: {scale_val:.2f}",
        f"Hands: {hand_count}",
        f"FPS: {fps:.0f}",
    ]
    y0 = 22
    for line in lines:
        cv2.putText(canvas, line, (14, y0), cv2.FONT_HERSHEY_SIMPLEX,
                    0.52, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(canvas, line, (14, y0), cv2.FONT_HERSHEY_SIMPLEX,
                    0.52, (230, 230, 230), 1, cv2.LINE_AA)
        y0 += 22

    # Gesture hint fades after a few seconds
    if hint_fade > 0.05:
        hint = ("right hand fingers = how many   left hand open = bloom   "
                "spread hands = size   left pinch = change flower")
        alpha = min(1.0, hint_fade)
        ov = canvas.copy()
        cv2.rectangle(ov, (0, h - 36), (w, h), (20, 20, 20), -1)
        cv2.putText(ov, hint, (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX,
                    0.46, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.addWeighted(ov, alpha, canvas, 1 - alpha, 0, canvas)
