# Render Quality Scores

Graded adversarially against reference photos in refs/. Colour gate results are
objective (HSV median hue from selftest.py); visual scores are self assessed by
a single model and therefore likely generous by 5 to 10 points versus an
independent reviewer. A second, different model judge is the stronger check.

## Objective colour gate (selftest.py)

| Flower      | Gate range (H)      | Measured H | Result |
|-------------|---------------------|------------|--------|
| sunflower   | 20 to 38            | 23         | PASS   |
| blue_rose   | 100 to 135          | 109        | PASS   |
| spider_lily | 0 to 10 or 165 to 179 | 2        | PASS   |

## Sunflower (refs/sunflower.jpg)

Reference: large domed disc, many narrow strap like yellow ray petals with
longitudinal creases, amber bases, golden brown textured disc with a bright
floret ring.

| Criterion                        | Score | Notes                                             |
|----------------------------------|-------|---------------------------------------------------|
| Match to reference (25)          |  20   | Strap petals with creases, amber bases, and irregular lengths and angles as in the reference; still a flat front view versus the domed 3D disc |
| Signature feature fidelity (20)  |  17   | 300 golden angle seeds as oriented ellipses so the spiral lattice reads, floret ring, notched petal tips |
| Colour realism (15)              |  13   | Amber to golden gradient along each petal, lime cast gone |
| Depth and shading (15)           |  13   | Domed disc lit from top left, per petal cast shadows onto the back row |
| Edge and curve quality (10)      |   9   | Supersampled, pointed lanceolate tips, no faceting |
| Bloom dynamics (10)              |   9   | Green wrapped bud opens to full disc convincingly |
| Beauty (5)                       |   4   |                                                    |
| **Overall**                      | **85**|                                                    |

## Blue Rose (refs/blue_rose.jpg)

Reference: vivid cobalt blue rose, spiral of overlapping cupped petals, deep
blue bases with lighter cool edges.

| Criterion                        | Score | Notes                                             |
|----------------------------------|-------|---------------------------------------------------|
| Match to reference (25)          |  20   | Spiral nested layers with light rolled edges and skewed asymmetric petals; reference is a side view bud, render is a top view open rose |
| Signature feature fidelity (20)  |  17   | Golden angle layer offsets give a real spiral; furled crescent core reads as a rose heart |
| Colour realism (15)              |  13   | Clearly cobalt, radial dark to light gradient per petal |
| Depth and shading (15)           |  13   | Directional light across the head, crevice shadows, dark cupping band under each rim |
| Edge and curve quality (10)      |   9   | Smooth waved arcs, no outlines, no faceting |
| Bloom dynamics (10)              |   9   | Sepal wrapped bud, layers unfurl outer first, core opens last |
| Beauty (5)                       |   4   |                                                    |
| **Overall**                      | **85**|                                                    |

## Spider Lily (refs/spider_lily.jpg)

Reference: Lycoris radiata firework silhouette, thin strongly recurved scarlet
tepals plus very long thin arching stamens with small anthers.

| Criterion                        | Score | Notes                                             |
|----------------------------------|-------|---------------------------------------------------|
| Match to reference (25)          |  21   | Firework burst reads immediately; two dim background florets now hint at the reference umbel cluster |
| Signature feature fidelity (20)  |  18   | Six long thin arcing stamens plus style, 1.3 to 1.5x tepal length, tiny anthers; narrow crinkled recurved tepals |
| Colour realism (15)              |  14   | Deep crimson base, bright scarlet mid, pink tip along each tepal and filament |
| Depth and shading (15)           |  12   | Directional tepal shading, offset soft shadows, midrib highlights |
| Edge and curve quality (10)      |   9   | Crinkled wavy edges, smooth bezier arcs |
| Bloom dynamics (10)              |   9   | Closed cluster opens into the full spider shape |
| Beauty (5)                       |   5   | The signature flower, graceful pinwheel |
| **Overall**                      | **87**|                                                    |

## Notes

- Scores now 85/85/87 (sunflower/rose/lily) after the umbel and asymmetry
  pass; the 95 gate is not yet met. Remaining gap: real 3D petal curvature
  versus the flat front view, which caps match and depth criteria.
- Self grading is optimistic. An independent reviewer would likely score 5 to
  10 points lower per flower on visual criteria.
- Live webcam mode was NOT tested (remote headless environment, no camera).
- Headless selftest runs clean; all 16 sample PNGs committed to samples/.
- Imports verified: all modules load without error.
- Iteration count: 8 render iterations in the first run, 2 in this follow up
  cycle (each cycle stays within the 8 iteration limit).
