"""All tunables in one place. No magic numbers in the rest of the code."""

# Hand tracking
pinch_threshold = 0.15          # normalised distance considered a pinch
openness_min = 0.4              # fist
openness_max = 2.0              # open hand
depth_near = 0.25               # palm width fraction considered "near"
depth_far = 0.06                # palm width fraction considered "far"
scale_min = 0.5
scale_max = 2.2
ema_base = 0.15                 # exponential moving average base alpha
ema_fast = 0.45                 # alpha used when hand moves quickly
mirror = True                   # selfie view
show_hud = True
bloom_driver = "openness"       # "openness" or "pinch"

# Wind sway
sway_amplitude = 0.018          # radians peak
sway_speed = 0.7                # Hz

# Rendering
supersample_factor = 3          # render at this multiple then downscale

# Per-species palettes (BGR)
palettes = {
    "sunflower": {
        "petal_outer": (0, 180, 255),    # golden yellow
        "petal_inner": (0, 120, 220),    # amber
        "petal_tip":   (30, 200, 255),   # bright tip
        "disc_outer":  (10, 60, 140),    # golden brown rim
        "disc_inner":  (0, 10, 20),      # near black centre
        "bract":       (20, 80, 30),
        "shadow":      (0, 40, 80),
    },
    "blue_rose": {
        "petal_base":  (160, 60, 60),    # deep blue (BGR)
        "petal_edge":  (220, 140, 110),  # lighter cool blue
        "petal_highlight": (255, 200, 170),
        "sepal":       (30, 80, 20),
        "shadow":      (100, 20, 20),
    },
    "spider_lily": {
        "tepal_base":  (0, 30, 220),     # vivid scarlet (BGR: low B, low G, high R)
        "tepal_edge":  (30, 10, 180),    # deeper crimson
        "tepal_mid":   (10, 50, 240),    # brighter mid
        "stamen":      (0, 60, 230),
        "anther":      (0, 80, 255),
        "shadow":      (0, 10, 120),
        "highlight":   (80, 100, 255),
    },
}
