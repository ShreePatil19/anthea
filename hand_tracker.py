"""
MediaPipe HandLandmarker wrapper. Returns a list of Hand objects, one per
detected hand, each with smoothed signals derived from the 21 landmarks.
"""
import math
import os
import urllib.request
import numpy as np
import cv2

from util import EMA
import config

# MediaPipe Tasks API
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    _MP_AVAILABLE = True
except Exception:
    _MP_AVAILABLE = False

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = "hand_landmarker.task"


def _ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand_landmarker.task...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Done.")


class Hand:
    """Per-hand signals, all smoothed with EMA."""

    def __init__(self):
        self._pos_ema    = EMA(config.ema_base, config.ema_fast, threshold=15)
        self._open_ema   = EMA(config.ema_base, config.ema_fast, threshold=0.1)
        self._pinch_ema  = EMA(config.ema_base, config.ema_fast, threshold=0.05)
        self._depth_ema  = EMA(config.ema_base, config.ema_fast, threshold=0.05)
        self.position          = (0, 0)
        self.openness          = 0.5
        self.pinch             = 0.5
        self.depth             = 0.5
        self.extended_fingers  = 0
        self.handedness        = "Right"

    def update(self, landmarks, image_w, image_h, handedness):
        self.handedness = handedness
        lm = landmarks

        def px(idx):
            return lm[idx].x * image_w, lm[idx].y * image_h

        wrist   = px(0)
        mcp_mid = px(9)
        tips    = [px(8), px(12), px(16), px(20)]
        palm5   = px(5)
        palm17  = px(17)

        palm_w = math.hypot(palm5[0] - palm17[0], palm5[1] - palm17[1]) or 1
        wrist_pos = np.array(wrist)

        # Openness: mean tip-to-wrist distance, normalised by palm width
        tip_dists = [
            math.hypot(t[0] - wrist[0], t[1] - wrist[1]) for t in tips
        ]
        raw_open = (sum(tip_dists) / len(tip_dists)) / palm_w
        # Calibrated: fist ~0.4, open ~2.0 -> map to 0..1
        open01 = (raw_open - config.openness_min) / (
            config.openness_max - config.openness_min
        )
        open01 = max(0.0, min(1.0, open01))

        # Pinch: thumb tip (4) to index tip (8)
        thumb = px(4)
        index_tip = px(8)
        pinch_d = math.hypot(thumb[0] - index_tip[0],
                              thumb[1] - index_tip[1]) / palm_w
        pinch01 = 1.0 - max(0.0, min(1.0,
                    (pinch_d - 0.0) / (config.pinch_threshold * 4)))

        # Depth: palm width as proxy (bigger = closer)
        palm_frac = palm_w / max(image_w, image_h)
        depth01 = (palm_frac - config.depth_far) / (
            config.depth_near - config.depth_far
        )
        depth01 = max(0.0, min(1.0, depth01))

        # Extended fingers
        ext = 0
        finger_tips   = [8, 12, 16, 20]
        finger_bases  = [6, 10, 14, 18]
        for tip_idx, base_idx in zip(finger_tips, finger_bases):
            tip_y  = lm[tip_idx].y
            base_y = lm[base_idx].y
            if tip_y < base_y:  # tip above base = extended (y flips in image)
                ext += 1
        # Thumb: use x comparison
        if lm[4].x < lm[3].x:
            ext += 1

        # Smooth
        self.position = self._pos_ema.update(mcp_mid)
        self.openness = self._open_ema.update(open01)
        self.pinch    = self._pinch_ema.update(pinch01)
        self.depth    = self._depth_ema.update(depth01)
        self.extended_fingers = ext


class HandTracker:
    """Wraps MediaPipe HandLandmarker in VIDEO mode."""

    def __init__(self):
        self._detector = None
        self._hands = {}    # id -> Hand
        self._last_result = None
        self._ts = 0

        if not _MP_AVAILABLE:
            return
        try:
            _ensure_model()
            BaseOptions = mp_python.BaseOptions
            HandLandmarker = mp_vision.HandLandmarker
            HandLandmarkerOptions = mp_vision.HandLandmarkerOptions
            VisionRunningMode = mp_vision.RunningMode

            opts = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=VisionRunningMode.VIDEO,
                num_hands=2,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._detector = HandLandmarker.create_from_options(opts)
        except Exception as e:
            print(f"HandTracker init error: {e}")

    def process(self, frame_bgr, timestamp_ms):
        """Process one frame. Returns list of Hand objects."""
        if self._detector is None:
            return []
        if config.mirror:
            frame_bgr = cv2.flip(frame_bgr, 1)
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._detector.detect_for_video(mp_image, int(timestamp_ms))

        h, w = frame_bgr.shape[:2]
        detected = []
        for i, (hand_lm, hand_handed) in enumerate(
            zip(result.hand_landmarks, result.handedness)
        ):
            key = i
            if key not in self._hands:
                self._hands[key] = Hand()
            hand = self._hands[key]
            handedness = hand_handed[0].display_name if hand_handed else "Right"
            hand.update(hand_lm, w, h, handedness)
            detected.append(hand)

        # Evict old hands
        for key in list(self._hands.keys()):
            if key >= len(detected):
                del self._hands[key]

        return detected

    def close(self):
        if self._detector:
            self._detector.close()
