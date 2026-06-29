"""
Maps hand signals to active species, bloom, scale, and position.
"""
import time
import config
from util import EMA, lerp

SPECIES_NAMES = ["sunflower", "blue_rose", "spider_lily"]
SPECIES_FINGER_MAP = {1: 0, 2: 1, 3: 2}   # extended_fingers -> species index

_PINCH_CYCLE_COOLDOWN = 0.6  # seconds between pinch-triggered species cycles


class FlowerState:
    """Current state for one on-screen flower."""

    def __init__(self, cx, cy, species_idx=0):
        self.cx = cx
        self.cy = cy
        self.species_idx = species_idx
        self.bloom = 0.5
        self.scale = 1.0
        self._bloom_ema = EMA(0.12, 0.35, threshold=0.1)
        self._scale_ema = EMA(0.10, 0.30, threshold=0.05)

    @property
    def species(self):
        return SPECIES_NAMES[self.species_idx]

    def update(self, bloom_target, scale_target):
        self.bloom = self._bloom_ema.update(bloom_target) or bloom_target
        self.scale = self._scale_ema.update(scale_target) or scale_target


class Controller:
    def __init__(self, canvas_w, canvas_h):
        self.w = canvas_w
        self.h = canvas_h
        self.flower = FlowerState(canvas_w // 2, canvas_h // 2, species_idx=0)
        self._pinch_cycle_last = 0.0
        self._last_pinch_high  = False

    def update(self, hands, t):
        """
        hands: list of Hand objects from HandTracker.
        t: current time in seconds.
        Returns the updated FlowerState.
        """
        flower = self.flower

        if not hands:
            # No hand detected: gentle idle sway, no state change
            return flower

        if len(hands) == 1:
            self._one_hand_mode(hands[0], t)
        else:
            self._two_hand_mode(hands, t)

        return flower

    # ------------------------------------------------------------------

    def _one_hand_mode(self, hand, t):
        flower = self.flower

        # Position: middle finger MCP in pixel coords
        px, py = hand.position
        flower.cx = int(px) if px else flower.cx
        flower.cy = int(py) if py else flower.cy

        # Species from extended fingers (if 1, 2, or 3 fingers clear)
        ef = hand.extended_fingers
        if ef in SPECIES_FINGER_MAP:
            flower.species_idx = SPECIES_FINGER_MAP[ef]
        else:
            # Tight pinch cycles species
            pinch_high = hand.pinch > 0.75
            if pinch_high and not self._last_pinch_high:
                now = t
                if now - self._pinch_cycle_last > _PINCH_CYCLE_COOLDOWN:
                    flower.species_idx = (flower.species_idx + 1) % 3
                    self._pinch_cycle_last = now
            self._last_pinch_high = pinch_high

        # Bloom
        if config.bloom_driver == "pinch":
            bloom_target = 1.0 - hand.pinch
        else:
            bloom_target = hand.openness

        # Scale from depth
        scale_target = lerp(config.scale_min, config.scale_max, hand.depth)

        flower.update(bloom_target, scale_target)

    def _two_hand_mode(self, hands, t):
        flower = self.flower
        # Identify left vs right; if ambiguous, use order (first = left, second = right)
        left  = next((h for h in hands if h.handedness == "Left"),  hands[0])
        right = next((h for h in hands if h.handedness == "Right"), hands[-1])

        # Left hand: position and species
        px, py = left.position
        flower.cx = int(px) if px else flower.cx
        flower.cy = int(py) if py else flower.cy
        ef = left.extended_fingers
        if ef in SPECIES_FINGER_MAP:
            flower.species_idx = SPECIES_FINGER_MAP[ef]

        # Right hand: bloom
        if config.bloom_driver == "pinch":
            bloom_target = 1.0 - right.pinch
        else:
            bloom_target = right.openness
        scale_target = lerp(config.scale_min, config.scale_max, right.depth)

        flower.update(bloom_target, scale_target)
