"""
Record a demo video of all three flowers cycling through bloom states.
Outputs samples/anthea_demo.mp4 (H.264, 30 fps, 1280x720).
No webcam or display required.
"""
import math
import time
import numpy as np
import cv2

from controller import FlowerState
from renderer import render_flower, demo_background, draw_hud

W, H = 1280, 720
FPS = 30
DURATION = 24.0  # seconds: 4 full species cycles (6s each)

out_path = "samples/anthea_demo.mp4"
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(out_path, fourcc, FPS, (W, H))

flower = FlowerState(W // 2, H // 2, species_idx=0)
n_frames = int(DURATION * FPS)

for f in range(n_frames):
    t = f / FPS
    species_period = 6.0
    species_idx = int(t / species_period) % 3

    bloom = (math.sin(t * 0.7) + 1) / 2
    scale = 0.8 + 0.6 * ((math.sin(t * 0.4) + 1) / 2)
    cx = int(W / 2 + math.sin(t * 0.3) * W * 0.2)
    cy = int(H * 0.45 + math.cos(t * 0.25) * H * 0.1)

    flower.species_idx = species_idx
    flower.cx = cx
    flower.cy = cy
    flower.bloom = bloom
    flower.scale = scale

    canvas = demo_background(W, H, t)
    render_flower(canvas, flower, t)
    hint_fade = max(0.0, 1.0 - t / 5.0)
    draw_hud(canvas, flower, hand_count=0, fps=FPS, t=t, hint_fade=hint_fade)

    writer.write(canvas)

    if (f + 1) % (FPS * 3) == 0:
        print(f"  {f + 1}/{n_frames} frames ({t:.1f}s)")

writer.release()
print(f"Saved {out_path} ({DURATION}s, {n_frames} frames, {FPS} fps)")
