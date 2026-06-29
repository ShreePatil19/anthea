"""
anthea: webcam hand-gesture flower controller.
Run with --demo for headless demo mode (no camera required).
"""
import sys
import time
import math
import argparse
import numpy as np
import cv2

import config
from hand_tracker import HandTracker
from controller import Controller, FlowerState
from renderer import render_garden, demo_background, draw_hud
from controller import SPECIES_NAMES


def _demo_garden(t, W, H):
    """Build a synthetic garden for demo mode without a camera.

    Sweeps the flower count 1..5 and back, cycles species, and breathes the
    bloom so the demo exercises the same garden the hands would drive.
    """
    species_idx = int(t / 6.0) % 3
    # Triangle wave 1..max_flowers..1
    span = config.max_flowers - 1
    phase = (t / 2.0) % (2 * span)
    count = int(1 + (phase if phase <= span else 2 * span - phase))
    count = max(1, min(config.max_flowers, count))

    bloom = (math.sin(t * 0.7) + 1) / 2
    size  = 0.8 + 0.5 * ((math.sin(t * 0.4) + 1) / 2)

    cx, cy = W // 2, int(H * 0.5)
    spacing = max(40, int(config.flower_spacing * size))
    flowers = []
    for i in range(count):
        off = (i - (count - 1) / 2.0)
        fx = int(cx + off * spacing)
        norm = off / max((count - 1) / 2.0, 1.0)
        fy = int(cy + (norm ** 2) * config.arc_dip * size)
        f = FlowerState(fx, fy, species_idx)
        f.bloom = bloom
        f.scale = size
        flowers.append(f)
    return flowers


def run_demo(headless=False, n_frames=None):
    """
    Demo mode: animate a garden with no camera and no display.
    If headless=True, never calls cv2.imshow. If n_frames is set, stop after that many.
    """
    W, H = 1280, 720

    hint_start = time.time()
    frame_count = 0
    t0 = time.time()
    canvas = demo_background(W, H, 0.0)

    while True:
        t = time.time() - t0
        flowers = _demo_garden(t, W, H)

        canvas = demo_background(W, H, t)
        render_garden(canvas, flowers, t)
        hint_fade = max(0.0, 1.0 - (time.time() - hint_start) / 5.0)
        draw_hud(canvas, flowers, hand_count=0, fps=30, t=t, hint_fade=hint_fade)

        if not headless:
            cv2.imshow("anthea demo", canvas)
            key = cv2.waitKey(33) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("d"):
                break

        frame_count += 1
        if n_frames is not None and frame_count >= n_frames:
            break

    if not headless:
        cv2.destroyAllWindows()
    return canvas  # return last frame for testing purposes


def run_webcam():
    """Live webcam mode."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No webcam found. Run with --demo for demo mode.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    tracker = HandTracker()
    controller = Controller(W, H)
    t0 = time.time()
    hint_start = t0
    fps = 30.0
    frame_times = []
    demo_mode = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if config.mirror:
                frame = cv2.flip(frame, 1)

            t = time.time() - t0
            ts_ms = t * 1000
            hands = tracker.process(frame, ts_ms)
            flowers = controller.update(hands, t)

            canvas = frame.copy()
            render_garden(canvas, flowers, t)
            hint_fade = max(0.0, 1.0 - (time.time() - hint_start) / 6.0)

            # FPS
            now = time.time()
            frame_times.append(now)
            frame_times = [ft for ft in frame_times if now - ft < 1.0]
            fps = len(frame_times)

            draw_hud(canvas, controller, len(hands), fps, t, hint_fade)
            cv2.imshow("anthea", canvas)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("d"):
                demo_mode = not demo_mode
            if key == ord("h"):
                config.show_hud = not config.show_hud
    finally:
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="anthea: hand-gesture flower controller")
    parser.add_argument("--demo", action="store_true",
                        help="Run in demo mode (no webcam required)")
    parser.add_argument("--headless", action="store_true",
                        help="No display (for CI/cloud environments)")
    args = parser.parse_args()

    if args.demo or args.headless:
        run_demo(headless=args.headless, n_frames=90 if args.headless else None)
    else:
        run_webcam()


if __name__ == "__main__":
    main()
