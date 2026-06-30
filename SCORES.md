# Render Quality Scores

Graded adversarially against reference photos in refs/. Colour gate results are
objective (HSV median hue from selftest.py); visual scores are self-assessed and
likely generous by 5-10 points vs an independent reviewer.

## Objective colour gate (selftest.py)

| Flower      | Gate range (H)      | Measured H | Result |
|-------------|---------------------|------------|--------|
| sunflower   | 20-38               | 24         | PASS   |
| blue_rose   | 100-135             | 113        | PASS   |
| spider_lily | 0-10 or 165-179     | 3          | PASS   |

## Sunflower (refs/sunflower.jpg)

Reference: front-facing, large domed disc (~40% of flower width), many narrow
strap-like yellow ray petals radiating straight outward, prominent golden-brown disc.

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  20   | Strap petals, correct proportion, warm golden; disc flat not domed |
| Signature feature fidelity (20) | 17  | Golden-angle seed spiral clearly visible; two offset petal rows |
| Colour realism (15)           |  12   | Warm amber-gold gradient, not neon, passes gate          |
| Depth and shading (15)        |  11   | Directional gradient per petal, shadow layer, disc gradient |
| Edge and curve quality (10)   |   8   | Smooth 36-point curves, 3x supersampling, no faceting    |
| Bloom dynamics (10)           |   8   | Clean 0 to 1 transition, disc and petals scale correctly |
| Overall beauty (5)            |   4   | Seed spiral is lovely; reads as a gift flower            |
| **Overall**                   | **80**|                                                          |

Remaining gaps: disc has no 3D dome (flat); petals too mathematically even despite jitter; dark gaps at petal bases look slightly unnatural.

## Blue Rose (refs/blue_rose.jpg)

Reference: vivid cobalt-blue dyed rose, closed bud, overlapping spiral petals.

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  17   | Blue, layered rings, rose silhouette; reference is closed bud, ours is open top-down |
| Signature feature fidelity (20) | 15  | 5 concentric petal rings, cupped shape, deep indigo centre |
| Colour realism (15)           |  12   | Cobalt blue throughout, directional gradient, shadow defines edges |
| Depth and shading (15)        |  11   | Ring layering creates depth; crease shadow on inner petal |
| Edge and curve quality (10)   |   7   | Smooth petal curves; slight geometric regularity         |
| Bloom dynamics (10)           |   7   | Rings unfurl in sequence, inner rings stay closed longer |
| Overall beauty (5)            |   3   | Reads clearly as blue rose; somewhat mathematical         |
| **Overall**                   | **72**|                                                          |

Remaining gaps: concentric ring layout reads as top-down not as closed bud; petal arrangement more geometric than the natural spiral of the reference; inner ring petal count too small relative to outer.

## Spider Lily (refs/spider_lily.jpg)

Reference: Lycoris radiata in full bloom, 6 strongly recurved scarlet tepals
curving far backward plus 6 long gracefully arching scarlet stamens with orange anthers.

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  17   | Scarlet, 6 tepals, long stamens; recurve less dramatic than reference |
| Signature feature fidelity (20) | 14  | Stamens 1.55x tepal length, arching upward; tepals narrow; recurve to ~50% return |
| Colour realism (15)           |  12   | Vivid scarlet H=3, radial gradient from deep crimson at base |
| Depth and shading (15)        |   9   | Shadow poly behind tepals, centre disc; stamen filament shadow |
| Edge and curve quality (10)   |   8   | Bezier spine for tepals, smooth stamen arcs, 3x supersampling |
| Bloom dynamics (10)           |   7   | Recurve and stamen extension driven by bloom parameter    |
| Overall beauty (5)            |   3   | Firework silhouette is distinctive; tepals still a bit stiff |
| **Overall**                   | **70**|                                                          |

Remaining gaps: tepal recurve still short of the dramatic backward hook of real Lycoris (tepals should nearly parallel the stem at full bloom); tepal waviness visible in outline but subtle at render resolution; stamen shadow colour too similar to background.

## Notes

- 95 acceptance gate not reached this run. Honest assessment: procedural 2D rendering without geometry or light transport cannot easily reproduce the 3D dome of a sunflower disc, the tight spiral coil of a rose bud, or the dramatic recurve of spider lily tepals. Maximum plausible score with the current supersampling-plus-gradients approach is approximately 82-85 per flower.
- Self-grading is optimistic by nature. An independent reviewer would likely score 5-10 points lower per flower on visual criteria.
- Improvements this run: sunflower petal length jitter increased; blue rose near-white highlight replaced with saturated icy-blue (removed distracting white tip artifacts); spider lily recurve increased from max 0.60 to max 0.80 and Bezier p2 extended to 0.96x for more dramatic hook.
- Live webcam mode was NOT tested (remote headless environment, no camera).
- Headless selftest runs clean; all 16 sample PNGs committed to samples/.
- Imports verified: all modules load without error.
- Iteration count this run: 6 total across both nightly runs (within the 8-iter limit).
