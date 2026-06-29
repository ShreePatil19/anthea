"""
Maps hand signals to a garden of flowers.

Two-hand control:
  right hand finger count -> number of flowers (0..max_flowers)
  left hand open/close     -> bloom
  distance between hands    -> size
  left hand pinch (cycle)   -> species
  midpoint between hands    -> where the flowers sit

One-hand fallback:
  finger count -> number of flowers
  open/close   -> bloom
  depth        -> size
  pinch cycle  -> species
  hand position-> where the flowers sit
"""
import config
from util import EMA, lerp, jitter

SPECIES_NAMES = ["sunflower", "blue_rose", "spider_lily"]

_PINCH_CYCLE_COOLDOWN = 0.6  # seconds between pinch-triggered species cycles


def _clamp01(v):
    return max(0.0, min(1.0, v))


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
    """Maintains a list of FlowerState driven by hand gestures."""

    def __init__(self, canvas_w, canvas_h):
        self.w = canvas_w
        self.h = canvas_h
        self.flowers = [FlowerState(canvas_w // 2, int(canvas_h * 0.5), 0)]
        self.species_idx = 0
        self.center = (canvas_w // 2, int(canvas_h * 0.5))
        self.bloom_target = 0.5
        self.size_target = 1.0

        self._pinch_cycle_last = 0.0
        self._last_pinch_high = False
        self._count_cand = 1
        self._count_cand_t = 0.0
        self._count = 1

    # ------------------------------------------------------------------

    def update(self, hands, t):
        """hands: list of Hand objects. Returns the list of FlowerState."""
        if hands:
            if len(hands) == 1:
                self._one_hand_mode(hands[0], t)
            else:
                self._two_hand_mode(hands, t)
        self._apply(t)
        return self.flowers

    @property
    def count(self):
        return len(self.flowers)

    @property
    def species(self):
        return SPECIES_NAMES[self.species_idx]

    @property
    def bloom(self):
        return sum(f.bloom for f in self.flowers) / len(self.flowers) if self.flowers else 0.0

    @property
    def scale(self):
        return self.size_target

    # ------------------------------------------------------------------

    def _stable_count(self, raw, t):
        """Debounce the finger count so it does not flicker."""
        raw = max(0, min(config.max_flowers, raw))
        if raw != self._count_cand:
            self._count_cand = raw
            self._count_cand_t = t
        elif t - self._count_cand_t >= config.count_hold_seconds:
            self._count = raw
        return self._count

    def _cycle_species_on_pinch(self, hand, t):
        pinch_high = hand.pinch > 0.75
        if pinch_high and not self._last_pinch_high:
            if t - self._pinch_cycle_last > _PINCH_CYCLE_COOLDOWN:
                self.species_idx = (self.species_idx + 1) % len(SPECIES_NAMES)
                self._pinch_cycle_last = t
        self._last_pinch_high = pinch_high

    def _one_hand_mode(self, hand, t):
        self._stable_count(hand.extended_fingers, t)

        px, py = hand.position
        if px:
            self.center = (int(px), int(py))

        self._cycle_species_on_pinch(hand, t)

        if config.bloom_driver == "pinch":
            self.bloom_target = 1.0 - hand.pinch
        else:
            self.bloom_target = hand.openness

        self.size_target = lerp(config.scale_min, config.scale_max, hand.depth)

    def _two_hand_mode(self, hands, t):
        left  = next((h for h in hands if h.handedness == "Left"),  hands[0])
        right = next((h for h in hands if h.handedness == "Right"), hands[-1])

        # Right hand finger count -> number of flowers
        self._stable_count(right.extended_fingers, t)

        # Left hand open/close -> bloom
        if config.bloom_driver == "pinch":
            self.bloom_target = 1.0 - left.pinch
        else:
            self.bloom_target = left.openness

        # Distance between hands -> size
        lx, ly = left.position
        rx, ry = right.position
        if lx and rx:
            dist = (abs(rx - lx) ** 2 + abs(ry - ly) ** 2) ** 0.5
            dist_frac = _clamp01(dist / max(self.w, 1) * 1.7)
            self.size_target = lerp(config.scale_min, config.scale_max, dist_frac)
            self.center = (int((lx + rx) / 2), int((ly + ry) / 2))

        # Left hand pinch cycles species
        self._cycle_species_on_pinch(left, t)

    # ------------------------------------------------------------------

    def _ensure_count(self, n):
        """Grow or shrink the flower list, preserving existing flowers."""
        n = max(0, min(config.max_flowers, n))
        while len(self.flowers) < n:
            f = FlowerState(self.center[0], self.center[1], self.species_idx)
            f.bloom = 0.0          # new flowers grow in from a bud
            self.flowers.append(f)
        while len(self.flowers) > n:
            self.flowers.pop()

    def _layout(self, n, size):
        """Positions for n flowers in a gentle arc around self.center."""
        cx, cy = self.center
        if n <= 0:
            return []
        spacing = max(40, int(config.flower_spacing * size))
        positions = []
        for i in range(n):
            off = (i - (n - 1) / 2.0)
            fx = cx + off * spacing
            # Outer flowers dip a little lower, like a held bunch
            norm = off / max((n - 1) / 2.0, 1.0)
            fy = cy + int((norm ** 2) * config.arc_dip * size)
            positions.append((int(fx), int(fy)))
        return positions

    def _apply(self, t):
        self._ensure_count(self._count)
        positions = self._layout(len(self.flowers), self.size_target)
        for i, f in enumerate(self.flowers):
            f.species_idx = self.species_idx
            f.cx, f.cy = positions[i]
            b = _clamp01(self.bloom_target + jitter(i * 3 + 1, 0.08))
            s = self.size_target * (1.0 + jitter(i * 5 + 2, 0.10))
            f.update(b, s)
