# Render Quality Scores

Graded adversarially against reference photos in refs/. Colour gate results are
objective (HSV median hue from selftest.py); visual scores are self-assessed and
likely generous by 5-10 points vs an independent reviewer.

## Objective colour gate (selftest.py)

| Flower      | Gate range (H)      | Measured H | Result |
|-------------|---------------------|------------|--------|
| sunflower   | 20-38               | 24         | PASS   |
| blue_rose   | 100-135             | 111        | PASS   |
| spider_lily | 0-10 or 165-179     | 3          | PASS   |

## Iteration 3 upgrades

Detail polish on top of the structural changes from iteration 2:

1. Sunflower petal veins: thin midrib line down each ray petal, shaded by the
   global light direction. Adds anatomical detail without clutter.
2. Blue rose asymmetric cupping: left side of each petal is 10% wider than the
   right, breaking the perfect symmetry and giving an organic, hand-cupped look.
3. Spider lily tepal fold-over: when recurve exceeds 0.35, the outer third of
   each tepal renders a separate darker underside polygon. This simulates the
   defining Lycoris trait of tepals curling back toward the viewer.

## Sunflower

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  22   | 3/4 tilted head, elliptical domed disc, foreshortened rays |
| Signature feature fidelity (20) | 18  | Golden-angle seed spiral on tilted disc, 175 seeds, midrib veins |
| Colour realism (15)           |  14   | Warm amber-gold; light side brighter, shade side deeper; vein colour matched |
| Depth and shading (15)        |  13   | Dome shading, per-petal light, offset dark disc centre   |
| Edge and curve quality (10)   |   8   | Smooth curves, 3x supersampling                          |
| Bloom dynamics (10)           |   8   | Clean bud to open transition                             |
| Overall beauty (5)            |   4   | Reads as a lit, tilted sunflower with botanical detail   |
| **Overall**                   | **87**|                                                          |

Remaining gaps: petal arrangement still fairly regular; no petal twist or curl
out of plane; disc texture is dots, not true florets.

## Blue Rose

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  22   | Spiral petal packing, bumpy organic silhouette           |
| Signature feature fidelity (20) | 17  | Golden angle spiral, furled shadowed core, asymmetric cupping |
| Colour realism (15)           |  13   | Cobalt blue, lit side vs shade side variation            |
| Depth and shading (15)        |  14   | Ambient occlusion core, per-petal light, crease folds, asymmetric widths break uniformity |
| Edge and curve quality (10)   |   8   | Organic outer edge; dark outlines still slightly heavy   |
| Bloom dynamics (10)           |   8   | Outer petals unfurl first, core opens last               |
| Overall beauty (5)            |   4   | Reads as a rose with natural irregularity                |
| **Overall**                   | **86**|                                                          |

Remaining gaps: dark outline between petals still visible; petals mostly flat
in plane (no true cupping toward the viewer in 3D).

## Spider Lily

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  20   | Scarlet burst with long stamens; fold-over shows recurve depth |
| Signature feature fidelity (20) | 16  | Stamens 1.55x tepals; fold-over underside visible past bend |
| Colour realism (15)           |  12   | Vivid scarlet, light-shaded radial gradient              |
| Depth and shading (15)        |  12   | Per-tepal light, darker underside past fold line adds volume |
| Edge and curve quality (10)   |   8   | Smooth Bezier tepals and stamen arcs, wavier edges       |
| Bloom dynamics (10)           |   7   | Recurve and stamen reach driven by bloom; fold-over triggers at bloom > 0.5 |
| Overall beauty (5)            |   3   | Distinctive silhouette; fold-over reads but still flat compared to real Lycoris |
| **Overall**                   | **78**|                                                          |

Remaining gaps: the fold-over technique shows depth but is not a true 3D
recurve. Real Lycoris tepals curl nearly 180 degrees back; the 2D
approximation can only hint at it. More aggressive recurve geometry and
per-tepal twist would help.

## Score history

| Iteration | Sunflower | Blue Rose | Spider Lily | Notes                        |
|-----------|-----------|-----------|-------------|------------------------------|
| 1         | 80        | 72        | 70          | Baseline                     |
| 2         | 86        | 84        | 72          | Light model, 3/4 view, spiral rose |
| 3         | 87        | 86        | 78          | Veins, asymmetric cupping, fold-over |

## Notes

- 95 acceptance gate not reached. Scores moved from 86/84/72 to 87/86/78 after
  the detail polish pass. The spider lily saw the biggest improvement (+6)
  from the fold-over technique. Sunflower and blue rose gains were smaller (+1,
  +2) since the structural work was done in iteration 2.
- Self-grading is optimistic by nature. An independent reviewer would likely
  score 5-10 points lower per flower on visual criteria.
- Live webcam mode was NOT tested (remote headless environment, no camera).
- Headless selftest runs clean; all 16 sample PNGs committed to samples/.
- Imports verified: all modules load without error.
- Iteration count this run: 3 render iterations (within the 8-iter limit).
