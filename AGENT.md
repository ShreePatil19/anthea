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

### Anti aliasing and gradients (required, this is the biggest quality lever)

OpenCV does not anti alias polygon edges well, which is why naive `cv2.fillPoly`
flowers look faceted and flat. Fix it with supersampling:

- Render every flower onto an offscreen canvas at 3x to 4x the target size, then
  downscale to target with `cv2.resize(..., interpolation=cv2.INTER_AREA)` (or Pillow
  `Image.resize(..., Image.LANCZOS)`). This gives smooth, soft, professional edges.
- Use true gradients on petals, not flat fills: build a per petal radial or linear
  gradient by interpolating two HSV colours across a mask, or use `cv2.addWeighted`
  between gradient stops. Petal base darker and richer, tip lighter and cooler.
- Petal outlines: 32 or more points so curves are smooth at supersampled resolution.
- Optional, only if it installs cleanly in a try/except during setup: use `pycairo`
  or `drawsvg` for native vector anti aliasing and gradients. If the import or install
  fails, fall back to the supersampling path above. An optional dependency must never
  break the build or the run.
- Pillow (`pillow`) is an allowed, safe dependency for the downscale step. `pycairo`
  is optional only.

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
refs/                # reference photos (downloaded or user supplied), gitignored
refs/SOURCES.md      # provenance and licences for any downloaded references
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

## Self grading loop (reference anchored, bias resistant, accept only at 95+)

A model grading its own renders tends to be too kind (this is called self enhancement
bias, and it is well documented). Counter it three ways: grade against a real reference
image, run a cheap objective colour check in code, and grade adversarially.

### Step A, get a reference image per species (do this once per run, before grading)

Reference based grading is far more reliable than rubric only grading. For each
species, obtain one real reference photo into `refs/`:

1. If a user supplied image already exists in `refs/` for the species (for example
   `refs/spider_lily.jpg`), use it and skip downloading.
2. Otherwise fetch a freely licensed photo from Wikimedia Commons. Use WebSearch and
   WebFetch to find a suitable Commons file, then download the direct image with Bash
   `curl`. Use the MediaWiki API to get the direct URL and the licence, for example:
   `https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=Lycoris%20radiata&gsrnamespace=6&gsrlimit=5&prop=imageinfo&iiprop=url|extmetadata&format=json`
   Pick a result whose `extmetadata.LicenseShortName` is Public domain, CC0, or CC BY.
   Save the file as `refs/<species>.jpg`.
3. Record provenance in `refs/SOURCES.md`: species, file, author, licence, and source
   URL. This keeps the public repo clean. Prefer Public domain or CC0; if CC BY, the
   attribution in SOURCES.md is required.
4. Gitignore the downloaded binaries (add `refs/*.jpg`, `refs/*.png` to `.gitignore`)
   so the repo stays light, but always commit `refs/SOURCES.md`. Re download on later
   runs if the files are missing.
5. If there is no network and no user image, fall back to rubric only grading and say
   so honestly in `SCORES.md`.

### Step B, objective colour gate (code, runs in selftest)

Add a function that, for a rendered flower, masks out the background and centre and
computes the median petal hue in OpenCV HSV (H is 0 to 179). Assert the dominant petal
hue is in range, this is a hard automatic fail independent of any vision score:

- Sunflower petals: H in 20 to 38 (yellow to amber).
- Blue rose petals: H in 100 to 135 (clearly blue, NOT purple 135 to 160, NOT red).
- Spider lily tepals: H in 0 to 10 or 165 to 179 (scarlet to crimson).

If a flower fails its colour gate it cannot pass, regardless of the vision score. This
is the cheap guard that stops a purple rose or an orange lily from sneaking through.

### Step C, adversarial vision grading

For each flower, OPEN with the Read tool: the reference photo AND your rendered samples
(grade the bloom = 1.0 render as the main judgement, glance at 0.5 for a believable
half open state). Grade as a skeptical critic who assumes the render is flawed and must
be convinced otherwise. When in doubt, deduct. Treat the reference photo as ground
truth for shape, proportion, and colour. Score out of 100 on this rubric and write the
specific deductions per criterion into `SCORES.md`:

- Match to reference photo (25): silhouette, proportions, and colour match the real
  flower in `refs/`.
- Signature feature fidelity (20): sunflower shows a real golden angle seed spiral;
  blue rose shows nested cupped petal layers and is clearly blue; spider lily shows
  thin recurved wavy tepals AND long protruding curved stamens.
- Colour realism (15): correct hue with a natural HSV gradient, not flat, not neon.
- Depth and shading (15): layered shadow, fill, highlight, a real sense of 3D.
- Edge and curve quality (10): smooth anti aliased curves from supersampling, no
  faceting, organic wavy edges where the species calls for it.
- Bloom dynamics (10): the bud to open transition reads correctly across steps.
- Overall beauty and gift worthiness (5): intentional and lovely.

### Step D, the loop and the honesty rules

- Acceptance gate: every flower must pass its colour gate AND score 95 or above.
- For any flower below 95, identify the largest deductions, improve that specific
  renderer, re render, and regrade. At most 8 improve and regrade iterations per run.
- If a flower still falls short when iterations or time run out, commit the best
  version and record the real score and remaining gaps honestly in `SCORES.md` and the
  PR body. Never write a score you did not earn, never loop forever burning tokens.
- Note in SCORES.md that this is single model self grading and therefore optimistic by
  nature; a second, different model judge (for example an Opus reviewer) is the stronger
  check the user can enable later.
- Write `SCORES.md` every run: a table of the three flowers with latest score, colour
  gate pass or fail, a short per criterion breakdown, and one line on what still needs
  work. Across the night's 3 runs the scores should climb toward and past 95.

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
3. Always run the Verification steps AND the full Self grading loop before committing:
   fetch or reuse reference images (Step A), run the objective colour gate (Step B),
   grade adversarially against the references (Step C), and iterate (Step D). If the
   self test or a colour gate fails, fix it before you commit. Commit the updated
   `samples/`, `SCORES.md`, and `refs/SOURCES.md` so the user sees the renders, the
   grades, and where the references came from.
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
  aliased edges from supersampling. Plain flat shapes are not acceptable, this is a gift.
- Every flower passes its objective colour gate (sunflower yellow, blue rose blue,
  spider lily scarlet) and is graded against a real reference photo in `refs/`.
- `python main.py --demo` is written so it would animate without a camera or display.
- `SCORES.md` exists with honest, vision based grades for all three flowers, and the
  target is every flower at 95 or above. If a flower is below 95 at the end, that is
  stated plainly with the reasons, not hidden or inflated.
- One open PR titled "anthea nightly build" with an honest verification note and the
  current flower scores.
