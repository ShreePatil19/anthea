# Render Quality Scores

Graded adversarially against reference photos in refs/. Colour gate results are
objective (HSV median hue from selftest.py); visual scores are self-assessed and
likely generous by 5-10 points vs an independent reviewer.

## Objective colour gate (selftest.py)

| Flower      | Gate range (H)      | Measured H | Result |
|-------------|---------------------|------------|--------|
| sunflower   | 20-38               | 26         | PASS   |
| blue_rose   | 100-135             | 116        | PASS   |
| spider_lily | 0-10 or 165-179     | 176        | PASS   |

## Sunflower (refs/sunflower.jpg)

Reference: side/below view, large domed disc (~40% of flower width), many broad
drooping golden-yellow ray petals, prominent dark brown disc with seed texture.

| Criterion                  | Score | Notes                                                      |
|----------------------------|-------|------------------------------------------------------------|
| Colour accuracy            |  90   | Warm amber-gold; hue=26 in range; no neon lime             |
| Petal shape                |  78   | Two interleaved rows, wider ratio (0.195), organic variation; top-down vs ref side-view |
| Disc realism               |  84   | Golden-angle seed packing, dark amber-brown disc, green bracts |
| Species recognizability    |  90   | Unmistakably a sunflower                                   |
| Reference view match       |  62   | Render is top-down; reference is from below/side           |
| **Overall**                | **82**|                                                            |

## Blue Rose (refs/blue_rose.jpg)

Reference: side-view closed bud, 3-4 large cupped outer petals, tight spiral
interior, vivid cobalt blue, green sepals prominent at base.

| Criterion                  | Score | Notes                                                      |
|----------------------------|-------|------------------------------------------------------------|
| Colour accuracy            |  89   | Vivid cobalt blue, hue=116, clearly not purple; PASS       |
| Petal shape                |  74   | 5 large outer petals (down from 10); elongated highlight stripes; perspective compression |
| Structural form            |  72   | Concentric rings give depth; less side-view bud than reference |
| Species recognizability    |  76   | Reads clearly as a rose                                    |
| Reference view match       |  52   | Render is semi-top-down; reference is a side-view bud      |
| **Overall**                | **75**|                                                            |

## Spider Lily (refs/spider_lily.jpg)

Reference: Lycoris radiata in full bloom - 6 thin strongly recurved scarlet tepals
+ 6 very long gracefully arching stamens with golden anthers, fountain silhouette.

| Criterion                  | Score | Notes                                                      |
|----------------------------|-------|------------------------------------------------------------|
| Colour accuracy            |  88   | Vivid scarlet, hue=176 in [165,179]; PASS                  |
| Tepal shape/recurve        |  80   | Long thin tepals (scale * 188), clear recurve, visible midrib lines |
| Stamen arching             |  82   | 6 long stamens with cubic Bezier upward arc; golden anthers |
| Fountain silhouette        |  80   | Upward bias (0.40 * stamen_len) creates correct spray form |
| Species recognizability    |  84   | Very clearly Lycoris radiata                               |
| **Overall**                | **82**|                                                            |

## Change summary vs prior run

| Flower      | Prior | This run | Delta |
|-------------|-------|----------|-------|
| sunflower   |  78   |  82      |  +4   |
| blue_rose   |  73   |  75      |  +2   |
| spider_lily |  71   |  82      | +11   |

## Notes

- Self-grading is optimistic. An independent reviewer would likely score 5-8
  points lower per flower on visual criteria.
- Largest gain: spider lily, from stamen arching fix (upward bias 0.40) and
  longer tepals (135 -> 188), reduced recurve (max 0.70 vs 0.90).
- Blue rose gain is modest because the fundamental view mismatch (top-down render
  vs side-view bud reference) remains. Reducing outer petals 10 -> 5 improves
  readability; elongated highlight stripes replace round blobs.
- Sunflower gain from palette fix (amber-gold not lime), 34-petal count, back
  and front petal rows, bracts, wider petal ratio (0.195).
- Live webcam mode was NOT tested (remote headless environment, no camera).
- Headless selftest runs clean; all 16 sample PNGs committed to samples/.
- Imports verified: all modules load without error.
