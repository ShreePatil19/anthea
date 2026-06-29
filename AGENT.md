# AGENT.md, build spec for anthea

You are working autonomously on **anthea**, a webcam hand gesture flower controller.
This file is the complete specification. It is self contained. Build the project to
match it, verify your work, then commit and push. You may be run more than once on
the same night; read the "Run protocol" section so repeat runs improve the project
instead of duplicating it.

## Hard writing rules (apply to all files, code comments, README, and commit messages)

These override any default habit:

- Do NOT add a `Co-Authored-By:` trailer to any commit. Commits are authored only by
  the repo owner. No co-author line, ever.
- Do NOT use em dashes or en dashes anywhere. Use commas, periods, semicolons, or
  rewrite the sentence. Write "3 to 5", not a dash range.
- Do NOT put any AI vendor branding in shipped text (README, UI, comments, commit
  messages). No "Claude", "Anthropic", "powered by AI", etc. Use neutral terms like
  "the model" or "hand tracking model" if you must refer to it.
- Keep prose terse. No filler, no "I have now done X" summaries in files.

## Objective

A single Python application: the webcam tracks the user's hand and the hand controls
procedurally drawn flowers in real time. This is a controller and visualiser only.
No game, no score, no timer, no plucking. Three flowers, each rendered from maths.

## Stack

- Python 3 (target 3.10+).
- `opencv-python` for capture, drawing, and the window.
- `mediapipe` (Tasks API, HandLandmarker) for hand tracking.
- `numpy` for the procedural geometry and alpha blending.
- No game engine, no image assets, no 3D files. Every petal, stem, and leaf is
  drawn with `cv2.fillPoly`, `cv2.polylines`, and `cv2.addWeighted`.

## Rendering quality, technique, and provenance

Quality is the priority for this project. Spend the effort to make the flowers look
beautiful, not merely correct. Use these proven procedural techniques (build your own
clean implementations in `util.py`, do not copy third party files verbatim):

- A `curved_petal_polygon(cx, cy, length, width, angle, curvature)` helper that returns
  a smooth petal outline with many points (aim for 24+ points per petal so curves are
  smooth, not faceted).
- A `scale_polygon(points, cx, cy, factor)` helper to draw inner color layers.
- Per petal layering: a slightly enlarged dark copy behind for a soft shadow, the main
  fill, then one or two smaller lighter copies on top for a gradient and a highlight.
- `gradient_circle` for flower centres, and fine `cv2.line` plus `cv2.ellipse` for
  stamens and anthers. Everything anti aliased with `cv2.LINE_AA`.
- Composite each finished flower with `cv2.addWeighted` so edges are soft.
- Colours are BGR (OpenCV order). Interpolate palettes in HSV for smooth, natural
  gradients rather than flat fills.

Provenance and credit: the approach above is informed by public reference projects,
chiefly saud-26/Garden-in-Bloom (procedural OpenCV flowers), barmoshe/bloom-garden,
and misalavinash/flower-generator. Write original code, then add a `CREDITS.md` that
thanks these projects as design references and links them. Do not copy their source
files verbatim, since at least one declares MIT in its README but ships no LICENSE
file, so provenance is unclear. Original work plus credit keeps this repo clean.

Aim to exceed the references: real golden angle seed packing, an anatomically correct
spider lily, and smooth HSV gradients are the upgrades that make anthea superior.

## The three flowers (render each as its own module under `flowers/`)

Each flower module exposes `draw(canvas, cx, cy, bloom, scale, t, opts)` where
`bloom` is 0..1 (bud to fully open), `scale` is a size multiplier, and `t` is time
in seconds for gentle wind sway. Render in three passes (soft shadow, main fill,
highlight) with alpha blending so the shapes look hand painted, not flat.

1. **Sunflower** (`flowers/sunflower.py`)
   - Central disc with REAL golden angle seed packing: place 180 to 260 seeds using
     r = c*sqrt(n), theta = n*137.507 degrees. Seed dot size and colour grade from
     small dark brown at the centre to slightly larger golden brown at the rim.
   - Two offset rows of long golden ray petals (about 21 to 34, a Fibonacci count)
     with slightly notched tips, the back row peeking between the front row.
   - Green bracts behind the petals.
   - `bloom` raises petal length and disc size from a tight green bud to full open.
   - Palette: warm yellow into amber petals, deep brown to near black disc gradient.

2. **Blue rose** (`flowers/blue_rose.py`)
   - 4 layers of cupped, overlapping curved petals (about 5 outer, 5 mid, 5 inner,
     3 furled core), each layer rotated so petals nest in the gaps of the layer below
     and get smaller and more closed toward the centre.
   - Each petal carries an HSV gradient from a deep blue base to a lighter cool blue
     or violet edge, plus a soft dewy highlight near the top.
   - Green sepals at the base. `bloom` controls how far the outer layers unfurl, the
     core stays furled until bloom is high.
   - Palette: deep blue into violet, cool blue edges. Keep it clearly blue, not purple.

3. **Spider lily** (`flowers/spider_lily.py`), Lycoris radiata, the signature flower
   - 6 very thin, strongly recurved (bent back) tepals with WAVY, crinkled edges,
     radiating evenly. Petals are narrow and long, nothing like a rounded lily petal.
   - 6 extremely long, arching stamens that protrude far past the tepals (about 1.3
     to 1.6 times the petal length), each a thin curved filament tipped with a small
     anther. These long spidery stamens are the defining feature, make them prominent
     and graceful, do not shorten them.
   - `bloom` drives how far the tepals recurve and how far the stamens extend, from a
     closed cluster to the full open spider shape.
   - Palette: vivid scarlet and crimson. Add a `variant` option in `opts` for a pure
     white form (Lycoris albiflora).

A shared `flowers/stem.py` draws a curved stem (cubic Bezier from the bottom of the
frame up to the flower, with a small random lateral bow and time based sway) plus one
or two leaves.

## Hand signals (put this in `hand_tracker.py`)

Use MediaPipe HandLandmarker, VIDEO running mode, up to 2 hands, GPU delegate if
available else CPU. The model file `hand_landmarker.task` should auto download on
first run if missing (fetch from the public MediaPipe model URL). Mirror the frame
(selfie view) so it feels like a mirror.

From the 21 landmarks derive, per hand, and smooth every value with an Exponential
Moving Average (adaptive: faster smoothing when the hand moves quickly):

- `position`: anchor on the middle finger MCP (landmark 9), in pixel coordinates.
- `openness` (0..1): mean distance from the wrist (0) to the four fingertips
  (8, 12, 16, 20), normalised by palm width (distance from landmark 5 to 17) so it is
  invariant to camera distance. Calibrate so a relaxed open hand is near 1.0 and a
  fist near 0.0.
- `pinch` (0..1): distance between thumb tip (4) and index tip (8), normalised by
  palm width.
- `depth` (0..1): use palm width in pixels as a proxy for how close the hand is to
  the camera (bigger palm width means closer). Map to a sensible near/far range.
- `extended_fingers`: integer count of extended fingers, for species selection.

## Control mapping (the heart of the project, keep it discoverable)

- Hand `position` moves the active flower around the canvas.
- `pinch` (or `openness` if you prefer, expose which in config) drives `bloom`:
  fingers together is a tight bud, fingers spread is full bloom.
- `depth` drives `scale`: hand closer to the camera grows the flower, further shrinks
  it. Clamp to a min and max so it never disappears or fills the screen.
- `extended_fingers` selects species: 1 = sunflower, 2 = blue rose, 3 = spider lily.
- Two hand mode (when both hands are visible): left hand selects species and position,
  right hand controls bloom. One hand mode: that hand does position plus bloom, and a
  quick pinch cycles species. Implement one hand mode first, add two hand if time.
- Flowers sway gently when the hand is still. Bloom and scale interpolate smoothly,
  nothing snaps.

## Architecture (many small files, each focused)

```
main.py              # entry: webcam loop, demo mode, HUD, key handling
hand_tracker.py      # MediaPipe wrapper -> list of hands with the signals above
controller.py        # maps hand signals -> active species, bloom, scale, position
renderer.py          # composites flowers + stems over the (mirrored) frame
config.py            # ALL tunables in one place (see below)
util.py              # bezier, polygon, lerp, EMA, color/alpha helpers
flowers/
  __init__.py
  sunflower.py
  blue_rose.py
  spider_lily.py
  stem.py
requirements.txt
selftest.py          # headless render check, see Verification
CREDITS.md           # design references and thanks, see provenance section
SCORES.md            # self grade scorecard per flower, see Self grading loop
samples/             # rendered PNG proofs, committed so the user can see them
refs/                # optional user supplied reference photos (may be empty)
```

## config.py tunables

`pinch_threshold`, `openness_min`, `openness_max`, `depth_near`, `depth_far`,
`scale_min`, `scale_max`, `ema_base`, `ema_fast`, `sway_amplitude`, `sway_speed`,
`mirror` (bool), `show_hud` (bool), `bloom_driver` ("pinch" or "openness"), plus a
palette dict per species. No magic numbers scattered in the code, pull them from here.

## Demo mode (required, this is how you and the user verify without a webcam)

`main.py --demo` and a `d` key toggle must run the full visual with NO webcam: drive
`bloom`, `scale`, and `position` from sine waves and cycle through the three species,
rendering over a soft gradient background instead of the camera frame. This must work
in a headless cloud environment where no camera and no display exist (guard all
`cv2.imshow` calls so headless does not crash).

## HUD

A small toggleable overlay showing: active species, bloom percent, scale, hand count,
and FPS. A one line gesture hint on screen at startup.

## Self grading loop (accept only at 95 or above)

After rendering the sample PNGs, you must grade your own work with your vision and
iterate until it is genuinely good. Do not skip this and do not inflate scores.

How to grade:

1. For each flower, OPEN its rendered sample PNGs with the Read tool so you actually
   SEE them (grade the bloom = 1.0 render as the main judgement, and glance at the
   0.5 render to confirm a believable half open state). If files exist under `refs/`
   for that species, open them too and compare your render against them.
2. Score each flower out of 100 using this weighted rubric. Be a harsh, honest critic.
   List the specific points deducted per criterion in `SCORES.md`.

   - Botanical form and arrangement (25): correct petal count, shape, and layout for
     the species; the silhouette reads unmistakably as this flower.
   - Signature feature fidelity (20): sunflower shows a real golden angle seed spiral;
     blue rose shows nested cupped petal layers and is clearly blue not purple; spider
     lily shows thin recurved wavy tepals AND long protruding curved stamens.
   - Colour realism (15): correct hue range with a natural HSV gradient, not flat or
     garish, not neon.
   - Depth and shading (15): layered shadow, fill, and highlight give a sense of 3D;
     soft edges, not a flat cutout.
   - Edge and curve quality (10): smooth anti aliased petal curves, no faceting; edges
     are organic and wavy where the species calls for it.
   - Bloom dynamics (10): the bud to open transition reads correctly across steps.
   - Overall beauty and gift worthiness (5): it looks intentional and lovely.

3. Acceptance gate: every flower must reach 95 or above. Any flower below 95, identify
   the largest deductions, improve that flower's renderer specifically, re render its
   samples, and grade again.
4. Bound the loop: do at most 6 improve and regrade iterations per run. If a flower
   still falls short of 95 when you run out of iterations or the run is ending, commit
   your best version and record the real score and the remaining gaps honestly in
   `SCORES.md` and the PR body. Never write a score you did not earn, and never loop
   forever burning tokens.
5. Write `SCORES.md` every run: a table of the three flowers with their latest score,
   a short per criterion breakdown, and a one line note on what still needs work. Over
   the night's 3 runs the scores should climb toward and past 95.

## Verification (you have no webcam and no display in the cloud, so verify like this)

1. `python -c "import main, hand_tracker, controller, renderer, config, util"` and an
   import of every file under `flowers/`, to prove there are no syntax or import
   errors. `pip install -r requirements.txt` first.
2. `python selftest.py`: for each species, render frames at bloom = 0.0, 0.5, 1.0 and
   at two scales, with no exceptions, to an offscreen numpy canvas. Save the results
   as PNG files into `samples/` (for example `samples/sunflower_bloom_100.png`). Also
   render a few demo mode frames to `samples/`.
3. Commit the `samples/` PNGs so the user can SEE the flowers in the morning without
   running anything. These sample renders are the proof the build works.
4. In the PR description, state honestly what was verified (imports, headless self
   test, sample renders) and what was NOT (live webcam and hand tracking, which need a
   real camera the cloud cannot drive). Do not claim the webcam path was tested.

## Run protocol (you may be run 2 to 3 times tonight, each run is a fresh session)

1. `git fetch` and work on a single branch named `nightly-build`. If it already
   exists (a previous run tonight created it), check it out and `git pull` so you
   build on the prior run instead of starting over.
2. Decide state:
   - If the project does not exist yet, build it fully per this spec.
   - If it exists, read `SCORES.md` and spend this run driving the lowest scoring
     flowers up: improve the renderers of any flower below 95, then any other polish
     (smoother smoothing, two hand mode, richer HUD). Refresh `samples/`.
3. Always run the Verification steps AND the Self grading loop before committing. If
   the self test fails, fix it before you commit, do not commit a broken self test.
   Commit the updated `samples/` and `SCORES.md` so the user can see both the renders
   and the grades.
4. Commit with a clear conventional message (for example `feat: initial anthea build`
   or `polish: smoother bloom interpolation`), following the hard writing rules above
   (no co-author trailer, no dashes, no vendor branding). Push to `nightly-build`.
5. Ensure exactly one pull request from `nightly-build` into the default branch is
   open. If none exists, open one with `gh pr create`. If one already exists, just
   push, the PR updates itself. PR title: "anthea nightly build". PR body: a short
   gesture guide plus the honest verification note from step 4 of Verification.

## Success criteria

- All modules import, `selftest.py` passes, and `samples/` contains clear renders of
  all three distinct flowers at several bloom and scale steps.
- The three flowers are visually distinct in shape and palette, and the spider lily
  has its long protruding stamens.
- The renderers are original code (not copied verbatim from the reference repos) and
  `CREDITS.md` thanks and links the design references.
- Rendering looks polished: smooth petal curves, soft shadows, HSV gradients, anti
  aliased edges. Plain flat shapes are not acceptable, this is a gift.
- `python main.py --demo` is written so it would animate without a camera or display.
- `SCORES.md` exists with honest, vision based grades for all three flowers, and the
  target is every flower at 95 or above. If a flower is below 95 at the end, that is
  stated plainly with the reasons, not hidden or inflated.
- One open PR titled "anthea nightly build" with an honest verification note and the
  current flower scores.
