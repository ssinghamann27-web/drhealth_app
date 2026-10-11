#!/usr/bin/env python3
"""Make a 9:16 reel without losing anything off the sides.

A centre crop of a 16:9 frame throws away 44% of the width, which on this film
means the ends of every lyric line. So the full frame is kept, fitted to the
reel's width, and the vertical space above and below is grown out of the
frame's own top and bottom edges - which are a smooth gradient and ground haze
anyway, so the join reads as one continuous image rather than as letterboxing.

  python3 reel.py --in film.mp4 --out reel.mp4
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageFilter

SW, SH = 1920, 1080          # source
RW, RH = 1080, 1920          # reel
FPS = 30
SRC_FRAME = SW * SH * 3
OUT_FRAME = RW * RH * 3

PANEL_H = RW * SH // SW      # 607
TOP = 560                    # sits above centre, clear of the player's UI
BOT = TOP + PANEL_H

_yy = np.arange(RH, dtype=np.float32)[:, None, None]


def _edge_fade():
    """Fall off toward the very top and bottom so the field recedes behind
    the panel instead of competing with it."""
    up = np.clip(_yy / (TOP * 0.9), 0, 1) ** 0.8
    dn = np.clip((RH - _yy) / ((RH - BOT) * 0.9), 0, 1) ** 0.8
    return np.minimum(np.minimum(up, dn), 1.0) * 0.46 + 0.16


_FADE = _edge_fade()
_FIELD_GRAIN = (np.random.default_rng(9).random((RH, RW, 1)).astype(np.float32)
                - 0.5) * 3.4
_COVER_W = int(round(RH * SW / SH))     # 3413: cover the reel by height


def to_reel(frame):
    """frame: SH x SW x 3 uint8 -> RH x RW x 3 uint8.

    The whole 16:9 frame is kept - nothing is cropped off the sides, so no
    lyric line loses its ends. The space around it is filled with the same
    frame blown up to cover and heavily defocused, so the reel reads as one
    image rather than as a letterboxed video.
    """
    src = Image.fromarray(frame)
    panel = np.asarray(src.resize((RW, PANEL_H), Image.LANCZOS), dtype=np.float32)

    # The field is a clean gradient taken from the panel's own top and bottom
    # edge colours. Blurring the frame itself drags the title and lyric bands
    # into it and leaves ghost words floating around the panel.
    top_col = panel[:10].mean(axis=(0, 1))
    bot_col = panel[-10:].mean(axis=(0, 1))

    out = np.empty((RH, RW, 3), dtype=np.float32)
    ka = (np.arange(TOP, dtype=np.float32) / max(1, TOP))[:, None, None] ** 0.8
    out[:TOP] = top_col * (0.18 + 0.82 * ka)
    kb = (np.arange(RH - BOT, dtype=np.float32) / max(1, RH - BOT))[:, None, None]
    out[BOT:] = bot_col * (1.0 - 0.82 * kb ** 0.8)
    out[TOP:BOT] = panel

    # a little grain in the field so it does not band on a phone screen
    g = _FIELD_GRAIN
    out[:TOP] += g[:TOP]
    out[BOT:] += g[BOT:]

    # a thin bright edge top and bottom, so the panel reads as a deliberate frame
    out[TOP - 2:TOP] = np.clip(out[TOP - 2:TOP] + 26, 0, 255)
    out[BOT:BOT + 2] = np.clip(out[BOT:BOT + 2] + 26, 0, 255)

    return np.clip(out, 0, 255).astype(np.uint8)


def _one(job):
    n, buf = job
    a = np.frombuffer(buf, dtype=np.uint8).reshape(SH, SW, 3)
    return n, to_reel(a).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--crf", type=int, default=19)
    a = ap.parse_args()

    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", a.src, "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=SRC_FRAME * 4)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (RW, RH), "-r", str(FPS), "-i", "-",
         "-an", "-c:v", "libx264", "-preset", "medium", "-tune", "grain",
         "-crf", str(a.crf), "-pix_fmt", "yuv420p", a.out],
        stdin=subprocess.PIPE)

    def feed():
        n = 0
        while True:
            buf = dec.stdout.read(SRC_FRAME)
            if len(buf) < SRC_FRAME:
                return
            yield (n, buf)
            n += 1

    t0 = time.time()
    pending, nxt, done = {}, 0, 0
    with Pool(a.jobs) as pool:
        for n, out in pool.imap_unordered(_one, feed(), chunksize=2):
            pending[n] = out
            while nxt in pending:
                enc.stdin.write(pending.pop(nxt))
                nxt += 1
                done += 1
                if done % 200 == 0:
                    el = time.time() - t0
                    print("  %4d  %.2fs/frame  %.0fs" % (done, el / done, el),
                          flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print("reel: %d frames in %.0fs -> %s" % (done, time.time() - t0, a.out))


if __name__ == "__main__":
    main()
