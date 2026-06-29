# anthea

Flowers that open at the wave of a hand.

anthea turns your webcam into a small garden you conduct with your bare hands. Move
your hand and a flower follows it. Open and close your fingers and it blooms or
folds. Bring your hand closer and it grows. Three flowers live here, each chosen
for what it means:

- Sunflower, for adoration and loyalty
- Blue rose, for the rare and the longed for
- Spider lily, for memory and reunion

Everything is drawn from scratch with maths, no photos and no 3D files, so each
petal is generated live, one frame at a time.

## How you control it

| Gesture | What it does |
| --- | --- |
| Move your hand | The flower follows your hand around the screen |
| Pinch and spread thumb and index | Closes the flower to a bud or opens it into full bloom |
| Hand closer to / further from the camera | The flower grows larger or smaller |
| Hold up 1, 2 or 3 fingers | Switches between sunflower, blue rose and spider lily |

No webcam handy? There is a built in demo mode that animates the flowers on their
own so you can still see them bloom.

## Run it

```bash
pip install -r requirements.txt
python main.py
```

Press `1`, `2`, `3` to force a species, `d` to toggle demo mode, and `q` or `Esc`
to quit. The hand tracking model downloads itself the first time you run it.

## Built with

Python, OpenCV, MediaPipe and numpy. Pure procedural rendering. Made as a gift.
