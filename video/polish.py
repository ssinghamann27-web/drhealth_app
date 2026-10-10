#!/usr/bin/env python3
"""Apply the finishing pass to an already-rendered film.

Nothing is re-rendered: frames are decoded, graded and re-encoded, so a look
change costs a few minutes instead of a full render.

  python3 polish.py --in film.mp4 --out shine.mp4
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

W, H, FPS = 1920, 1080, 30
FRAME = W * H * 3


def _one(job):
    import numpy as np
    import finish
    n, buf = job
    a = np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 3)
    return n, finish.finish(a, n / FPS).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--crf", type=int, default=19)
    a = ap.parse_args()

    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", a.src, "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=FRAME * 4)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
         "-an", "-c:v", "libx264", "-preset", "medium", "-tune", "grain",
         "-crf", str(a.crf), "-pix_fmt", "yuv420p", a.out],
        stdin=subprocess.PIPE)

    def feed():
        n = 0
        while True:
            buf = dec.stdout.read(FRAME)
            if len(buf) < FRAME:
                return
            yield (n, buf)
            n += 1

    t0 = time.time()
    pending = {}
    nxt = 0
    done = 0
    with Pool(a.jobs) as pool:
        for n, out in pool.imap_unordered(_one, feed(), chunksize=2):
            pending[n] = out
            while nxt in pending:
                enc.stdin.write(pending.pop(nxt))
                nxt += 1
                done += 1
                if done % 150 == 0:
                    el = time.time() - t0
                    print("  %4d  %.2fs/frame  %.0fs elapsed"
                          % (done, el / done, el), flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print("polished %d frames in %.0fs -> %s" % (done, time.time() - t0, a.out))


if __name__ == "__main__":
    main()
