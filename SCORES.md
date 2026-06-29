# Render Quality Scores

Graded adversarially against reference photos in refs/. Colour gate results are
objective (HSV median hue from selftest.py); visual scores are self-assessed and
likely generous by 5-10 points vs an independent reviewer.

## Objective colour gate (selftest.py)

| Flower      | Gate range (H)      | Measured H | Result |
|-------------|---------------------|------------|--------|
| sunflower   | 20-38               | 27         | PASS   |
| blue_rose   | 100-135             | 115        | PASS   |
| spider_lily | 0-10 or 165-179     | 177        | PASS   |

## Sunflower (refs/sunflower.jpg)

Reference: front-facing, large domed disc (~40% of flower width), many narrow
strap-like yellow ray petals radiating straight outward, prominent golden-brown disc.

| Criterion                  | Score | Notes                                                        |
|----------------------------|-------|--------------------------------------------------------------|
| Colour accuracy            |  88   | Warm golden yellow H=27; tip H=29 avoids lime; passes gate  |
| Petal shape                |  76   | Thin center vein added; still broader than strap-like ref    |
| Disc realism               |  80   | Golden-angle seeds visible, correct size ratio               |
| Bract/sepal visibility     |  72   | Bracts reduced to 38% of petal length; barely visible now    |
| Species recognizability    |  84   | Clearly reads as sunflower; back row no longer spiking       |
| **Overall**                | **80**|                                                              |

## Blue Rose (refs/blue_rose.jpg)

Reference: vivid cobalt-blue dyed rose, side view, tight spiral of overlapping petals.

| Criterion                  | Score | Notes                                                        |
|----------------------------|-------|--------------------------------------------------------------|
| Colour accuracy            |  88   | Vivid cobalt blue H=115; highlights cerulean not white       |
| Petal shape                |  74   | Blended cerulean highlights; cleaner teardrop profiles       |
| Structural form            |  74   | 11 petals in outer ring; rounder silhouette; golden angle rotation |
| Depth/cupping illusion     |  67   | Inner rings darker/smaller; reads as slightly recessed       |
| Species recognizability    |  75   | Reads as a rose viewed from above                            |
| **Overall**                | **75**|                                                              |

## Spider Lily (refs/spider_lily.jpg)

Reference: Lycoris radiata in full bloom: 6 strongly recurved scarlet tepals
sweeping outward then curling back, 6 long gracefully arching stamens with orange anthers.

| Criterion                  | Score | Notes                                                        |
|----------------------------|-------|--------------------------------------------------------------|
| Colour accuracy            |  86   | Vivid scarlet H=177 passes gate; anthers golden orange       |
| Tepal shape/recurve        |  78   | Lateral side-curl (curl_side=0.32); wider ribbon body visible |
| Stamen proportion          |  72   | 45-deg offset (no stamen along stem); thicker filaments      |
| Firework burst silhouette  |  75   | 6-point burst readable; tepals and stamens both prominent    |
| Species recognizability    |  77   | Reads as spider lily with recurved tepals and long stamens   |
| **Overall**                | **77**|                                                              |

## Notes

- Self-grading is optimistic. An independent reviewer would likely score 5-10
  points lower per flower on visual criteria.
- None of the three flowers reached the 95-point target. Remaining gaps are
  documented per-criterion above. Key open issues: sunflower petals still broader
  than strap-like reference; blue rose shows top-down geometry rather than the
  side-view spiral in the reference; spider lily tepal backward recurve reads more
  as a lateral curl than the sharp hook visible in the reference photo.
- Live webcam mode was NOT tested (remote headless environment, no camera).
- Headless selftest runs clean; all 16 sample PNGs committed to samples/.
- Imports verified: all modules load without error.
- Iteration count: 6 render iterations total across all flowers (3 prior run, 3
  this run); within the 8-iteration limit per flower.
