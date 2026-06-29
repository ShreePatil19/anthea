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
from controller import Controller
from renderer import render_flower, demo_background, draw_hud
from controller import SPECIES_NAMES


def _demo_signals(t, canvas_w, canvas_h):
    """Generate synthetic hand signals from sine waves for demo mode."""
    species_period = 6.0   # seconds per species
    species_idx = int(t / species_period) % 3

    bloom  = (math.sin(t * 0.7) + 1) / 2
    scale  = 0.8 + 0.6 * ((math.sin(t * 0.4) + 1) / 2)
    cx = int(canvas_w  / 2 + math.sin(t * 0.3) * canvas_w  * 0.2)
    cy = int(canvas_h * 0.45 + math.cos(t * 0.25) * canvas_h * 0.1)
    return species_idx, bloom, scale, cx, cy


def run_demo(headless=False, n_frames=None):
    """
    Demo mode: animate flowers with no camera and no display.
    If headless=True, never calls cv2.imshow. If n_frames is set, stop after that many.
    """
    W, H = 1280, 720
    # Synthetic flower state container
    from controller import FlowerState
    flower = FlowerState(W // 2, H // 2, species_idx=0)

    hint_start = time.time()
    frame_count = 0
    t0 = time.time()

    while True:
        t = time.time() - t0
        species_idx, bloom, scale, cx, cy = _demo_signals(t, W, H)
        flower.species_idx = species_idx
        flower.cx = cx
        flower.cy = cy
        flower.bloom = bloom
        flower.scale = scale

        canvas = demo_background(W, H, t)
        render_flower(canvas, flower, t)
        hint_fade = max(0.0, 1.0 - (time.time() - hint_start) / 5.0)
        draw_hud(canvas, flower, hand_count=0, fps=30, t=t, hint_fade=hint_fade)

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
            flower = controller.update(hands, t)

            canvas = frame.copy()
            render_flower(canvas, flower, t)
            hint_fade = max(0.0, 1.0 - (time.time() - hint_start) / 6.0)

            # FPS
            now = time.time()
            frame_times.append(now)
            frame_times = [ft for ft in frame_times if now - ft < 1.0]
            fps = len(frame_times)

            draw_hud(canvas, flower, len(hands), fps, t, hint_fade)
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
