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

## Renderer upgrades this run

Three structural changes aimed at the plateau documented in the previous run:

1. Global light model (util.py): single light direction from the upper left.
   Every petal's gradient is scaled by its angle to the light; hue preserved.
2. 3/4 viewing angle: sunflower and rose heads are vertically compressed
   (squash 0.80 to 0.82) with per-petal foreshortening. The sunflower disc is
   now a tilted ellipse shaded as a dome, with seed brightness following the
   light across the dome.
3. Blue rose rebuilt as a golden angle spiral (26 petals, innermost on top)
   instead of concentric rings, with ambient occlusion darkening the core.

## Sunflower (refs/sunflower.jpg)

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  22   | 3/4 tilted head, elliptical domed disc, foreshortened rays |
| Signature feature fidelity (20) | 18  | Golden-angle seed spiral on the tilted disc, 175 seeds   |
| Colour realism (15)           |  13   | Warm amber-gold; light side brighter, shade side deeper  |
| Depth and shading (15)        |  13   | Dome shading, per-petal light, offset dark disc centre   |
| Edge and curve quality (10)   |   8   | Smooth curves, 3x supersampling                          |
| Bloom dynamics (10)           |   8   | Clean bud to open transition                             |
| Overall beauty (5)            |   4   | Reads as a lit, tilted sunflower                         |
| **Overall**                   | **86**|                                                          |

Remaining gaps: petal arrangement still fairly regular; no petal twist or curl out of plane; disc texture is dots, not true florets.

## Blue Rose (refs/blue_rose.jpg)

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  21   | Spiral petal packing and bumpy organic silhouette match the bud form |
| Signature feature fidelity (20) | 17  | Golden angle spiral, furled shadowed core, cupped petals |
| Colour realism (15)           |  13   | Cobalt blue, lit side vs shade side variation            |
| Depth and shading (15)        |  13   | Ambient occlusion core, per-petal light, crease folds    |
| Edge and curve quality (10)   |   8   | Organic outer edge; outline shadow slightly heavy        |
| Bloom dynamics (10)           |   8   | Outer petals unfurl first, core opens last; believable half bloom |
| Overall beauty (5)            |   4   | Reads as a rose, not a rosette                           |
| **Overall**                   | **84**|                                                          |

Remaining gaps: dark outline between petals a touch heavy; petals lie flat in plane (no true cupping toward the viewer); reference bud is more closed than our full bloom.

## Spider Lily (refs/spider_lily.jpg)

| Criterion                     | Score | Notes                                                    |
|-------------------------------|-------|----------------------------------------------------------|
| Match to reference (25)       |  18   | Scarlet burst with long stamens; tepals lit per angle    |
| Signature feature fidelity (20) | 14  | Stamens 1.55x tepals; recurve to 0.80 but still in plane |
| Colour realism (15)           |  12   | Vivid scarlet, light-shaded radial gradient              |
| Depth and shading (15)        |  10   | Per-tepal light adds volume; no out-of-plane recurve     |
| Edge and curve quality (10)   |   8   | Smooth Bezier tepals and stamen arcs                     |
| Bloom dynamics (10)           |   7   | Recurve and stamen reach driven by bloom                 |
| Overall beauty (5)            |   3   | Distinctive silhouette; still stiffer than the reference |
| **Overall**                   | **72**|                                                          |

Remaining gaps: the defining Lycoris recurve happens out of the image plane (tepals curl toward the viewer); a flat 2D bend cannot reproduce it. Needs a fold-over rendering of the tepal tip (draw the underside past the fold line) to go further.

## Notes

- 95 acceptance gate not reached. Scores moved from 80/72/70 to 86/84/72 after
  the light model, 3/4 view, and spiral rose rebuild. The remaining distance to
  95 requires out-of-plane petal geometry (fold-overs, cupping toward the
  viewer) and floret-level disc texture; both are planned next.
- Self-grading is optimistic by nature. An independent reviewer would likely
  score 5-10 points lower per flower on visual criteria.
- Live webcam mode was NOT tested (remote headless environment, no camera).
- Headless selftest runs clean; all 16 sample PNGs committed to samples/.
- Imports verified: all modules load without error.
- Iteration count this run: 2 render iterations (within the 8-iter limit).
