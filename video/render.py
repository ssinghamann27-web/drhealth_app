#!/usr/bin/env python3
"""Render the video.

Frames 0..1575 (0 -> 52.5333s) are the rebuilt intro, drawn outright.
From 52.5333s on, new backgrounds are drawn and the ORIGINAL frame's text
layer - lyrics, karaoke highlights, chapter plates, credits - is keyed off
the source and composited over them, so the typography and its timing are
exactly as cut.

  python3 render.py --out film.mp4 --src v8.mp4 --cache /tmp/src
  python3 render.py --out beat.mp4 --start 66 --end 78 --src v8.mp4 --cache /tmp/src
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FPS = 30
HANDOFF_FRAME = 1576          # 52.5333s
TOTAL_FRAMES = 4160           # 138.6667s
_CACHE = None


def _init(cache):
    global _CACHE
    _CACHE = cache


REEL = bool(os.environ.get("REEL"))
FINISH = bool(os.environ.get("FINISH"))


def _render_one(n):
    import numpy as np
    import scenes
    img = scenes.render(n / FPS)
    if _CACHE and n >= HANDOFF_FRAME:
        from PIL import Image
        import overlay
        p = os.path.join(_CACHE, "%05d.jpg" % (n - HANDOFF_FRAME + 1))
        if os.path.exists(p):
            src = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
            fn = overlay.composite_vertical if REEL else overlay.composite
            img = np.clip(fn(img.astype(np.float32), src), 0, 255).astype(np.uint8)
    if FINISH:
        import finish
        img = finish.finish(img, n / FPS)
    return n, img.tobytes()


def prep(src, cache):
    """One sequential decode of the source frames we need to key from."""
    os.makedirs(cache, exist_ok=True)
    have = len([f for f in os.listdir(cache) if f.endswith(".jpg")])
    want = TOTAL_FRAMES - HANDOFF_FRAME
    if have >= want:
        print("source cache ready (%d frames)" % have, flush=True)
        return
    print("extracting %d source frames for the text key..." % want, flush=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", src,
         "-vf", "select='gte(n\\,%d)'" % HANDOFF_FRAME, "-vsync", "0",
         "-q:v", "2", os.path.join(cache, "%05d.jpg")], check=True)
    print("  cached %d" % len([f for f in os.listdir(cache)
                               if f.endswith(".jpg")]), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="film.mp4")
    ap.add_argument("--src", default=None, help="the original, for the text key")
    ap.add_argument("--cache", default=None)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=TOTAL_FRAMES / FPS)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--crf", type=int, default=20)
    a = ap.parse_args()

    cache = a.cache
    if a.src and cache:
        prep(a.src, cache)

    f0, f1 = int(round(a.start * FPS)), int(round(a.end * FPS))
    f1 = min(f1, TOTAL_FRAMES)
    frames = list(range(f0, f1))
    print("rendering %d frames (%.2fs -> %.2fs) on %d workers"
          % (len(frames), f0 / FPS, f1 / FPS, a.jobs), flush=True)

    import style
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (style.W, style.H), "-r", str(FPS), "-i", "-",
         "-an", "-c:v", "libx264", "-preset", "medium", "-tune", "grain",
         "-crf", str(a.crf), "-pix_fmt", "yuv420p", a.out],
        stdin=subprocess.PIPE)

    t0 = time.time()
    pending = {}
    nxt = f0
    with Pool(a.jobs, initializer=_init, initargs=(cache,)) as pool:
        for n, buf in pool.imap_unordered(_render_one, frames, chunksize=4):
            pending[n] = buf
            while nxt in pending:
                ff.stdin.write(pending.pop(nxt))
                nxt += 1
                done = nxt - f0
                if done % 120 == 0 or nxt == f1:
                    el = time.time() - t0
                    print("  %4d/%d  %5.1f%%  %.2fs/frame  eta %5.0fs"
                          % (done, len(frames), 100 * done / len(frames),
                             el / done, el / done * (len(frames) - done)),
                          flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg failed")
    print("wrote %s in %.0fs" % (a.out, time.time() - t0))


if __name__ == "__main__":
    main()
