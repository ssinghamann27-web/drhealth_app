#!/usr/bin/env python3
"""Render the rebuilt intro and hand off to the existing cut.

Frames 0..1575 (0 -> 52.5333s) are generated here; everything from v8's hard
cut into the first verse is kept untouched. Audio is never re-encoded.

  python3 render.py --out intro.mp4            full intro
  python3 render.py --start 30 --end 36        a slice, for checking a beat
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FPS = 30
SPLICE_FRAME = 1576          # 52.5333s - v8's existing cut
SPLICE_TIME = SPLICE_FRAME / FPS


def _render_one(n):
    import scenes
    return n, scenes.render(n / FPS).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="intro.mp4")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=SPLICE_TIME)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--crf", type=int, default=20)
    a = ap.parse_args()

    f0, f1 = int(round(a.start * FPS)), int(round(a.end * FPS))
    frames = list(range(f0, f1))
    print("rendering %d frames (%.2fs -> %.2fs) on %d workers"
          % (len(frames), a.start, a.end, a.jobs), flush=True)

    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "1920x1080", "-r", str(FPS), "-i", "-",
         "-an", "-c:v", "libx264", "-preset", "medium", "-tune", "grain",
         "-crf", str(a.crf), "-pix_fmt", "yuv420p", a.out],
        stdin=subprocess.PIPE)

    t0 = time.time()
    pending = {}
    nxt = f0
    with Pool(a.jobs) as pool:
        for n, buf in pool.imap_unordered(_render_one, frames, chunksize=4):
            pending[n] = buf
            while nxt in pending:            # keep output strictly in order
                ff.stdin.write(pending.pop(nxt))
                nxt += 1
                done = nxt - f0
                if done % 60 == 0 or nxt == f1:
                    el = time.time() - t0
                    print("  %4d/%d  %5.1f%%  %.2fs/frame  eta %4.0fs"
                          % (done, len(frames), 100 * done / len(frames),
                             el / done, el / done * (len(frames) - done)),
                          flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg failed")
    print("wrote %s in %.0fs" % (a.out, time.time() - t0))


if __name__ == "__main__":
    main()
