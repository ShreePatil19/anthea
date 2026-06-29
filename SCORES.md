# Render Quality Scores

Graded adversarially against reference photos in refs/. Colour gate results are
objective (HSV median hue from selftest.py); visual scores are self-assessed and
likely generous by 5-10 points vs an independent reviewer.

## Objective colour gate (selftest.py)

| Flower      | Gate range (H)      | Measured H | Result |
|-------------|---------------------|------------|--------|
| sunflower   | 20-38               | 23         | PASS   |
| blue_rose   | 100-135             | 114        | PASS   |
| spider_lily | 0-10 or 165-179     | 177        | PASS   |

## Sunflower (refs/sunflower.jpg)

Reference: front-facing, large domed disc (~40% of flower width), many narrow
strap-like yellow ray petals radiating straight outward, prominent golden-brown disc.

| Criterion                  | Score | Notes                                              |
|----------------------------|-------|----------------------------------------------------|
| Colour accuracy            |  88   | Warm golden yellow, passes gate; slightly too lime |
| Petal shape                |  74   | Straight radial (pinwheel fixed); still broad vs strap-like ref |
| Disc realism               |  80   | Golden-angle seeds visible, correct size ratio     |
| Bract/sepal visibility     |  65   | Present but green tips still slightly prominent    |
| Species recognizability    |  82   | Clearly reads as sunflower                         |
| **Overall**                | **78**|                                                    |

## Blue Rose (refs/blue_rose.jpg)

Reference: vivid cobalt-blue dyed rose, closed bud, overlapping spiral petals.

| Criterion                  | Score | Notes                                              |
|----------------------------|-------|----------------------------------------------------|
| Colour accuracy            |  88   | Vivid cobalt blue, clearly not purple; passes gate |
| Petal shape                |  68   | Overlapping teardrops read as rose petals; highlights slightly over-bright |
| Structural form            |  70   | Concentric ring layout; less spiral than ref       |
| Depth/cupping illusion     |  65   | Inner rings smaller/darker gives some depth        |
| Species recognizability    |  72   | Reads as a rose from above                         |
| **Overall**                | **73**|                                                    |

## Spider Lily (refs/spider_lily.jpg)

Reference: Lycoris radiata in full bloom - 6 strongly recurved scarlet tepals
curving backward + 6 long gracefully arching scarlet stamens with dark anthers.

| Criterion                  | Score | Notes                                              |
|----------------------------|-------|----------------------------------------------------|
| Colour accuracy            |  85   | Vivid scarlet, passes gate                         |
| Tepal shape/recurve        |  72   | Backward hook recurve visible; tepals wider now    |
| Stamen proportion          |  62   | Stamens visible as lines; one stamen runs along stem |
| Firework burst silhouette  |  68   | 6-point burst readable; tepals dominate more now  |
| Species recognizability    |  70   | Reads as spider lily with recurved petals          |
| **Overall**                | **71**|                                                    |

## Notes

- Self-grading is optimistic. An independent reviewer would likely score 5-10
  points lower per flower on visual criteria.
- Live webcam mode was NOT tested (remote headless environment, no camera).
- Headless selftest runs clean; all 16 sample PNGs committed to samples/.
- Imports verified: all modules load without error.
- Iteration count: 4 render iterations across all flowers (within the 8-iter limit).
