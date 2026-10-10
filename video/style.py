"""Shared look-and-feel for the Delusion Is Death intro.

Palette, fonts, easing and canvas helpers. Everything here is tuned to match
the existing v8 grade: near-black frame, a deep red glow behind the subject,
bone-white condensed caps and a single hot red accent.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 30
SS = 2  # supersample factor for vector layers

FONT_DIR = "/mnt/skills/examples/canvas-design/canvas-fonts"
DISPLAY = os.path.join(FONT_DIR, "BigShoulders-Bold.ttf")
DISPLAY_LIGHT = os.path.join(FONT_DIR, "BigShoulders-Regular.ttf")
MONO = os.path.join(FONT_DIR, "DMMono-Regular.ttf")

# --- palette -------------------------------------------------------------
BONE = (238, 233, 230)
RED = (196, 30, 38)
RED_HOT = (236, 64, 54)
GLOW = (120, 20, 20)
INK = (6, 3, 4)

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# --- easing --------------------------------------------------------------
def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def smoothstep(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def smootherstep(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_out(x, p=3.0):
    return 1 - (1 - clamp(x)) ** p


def ease_in(x, p=3.0):
    return clamp(x) ** p


def ease_out_back(x, overshoot=1.25):
    x = clamp(x)
    c3 = overshoot + 1
    return 1 + c3 * (x - 1) ** 3 + overshoot * (x - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def ramp(t, t0, t1):
    """0 before t0, 1 after t1, smooth between."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return smoothstep((t - t0) / (t1 - t0))


def window(t, t_in, t_full, t_out, t_gone, ease=smootherstep):
    """Smooth 0->1->0 envelope. Nothing in this film pops."""
    if t < t_in or t > t_gone:
        return 0.0
    if t < t_full:
        return ease((t - t_in) / max(1e-6, t_full - t_in))
    if t <= t_out:
        return 1.0
    return 1.0 - ease((t - t_out) / max(1e-6, t_gone - t_out))


def tracked(draw, xy, text, fnt, fill, tracking=0, anchor_center=False):
    """Letter-spaced text. Returns total width."""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + tracking
    return total


def text_size(fnt, text, tracking=0):
    img = Image.new("L", (1, 1))
    d = ImageDraw.Draw(img)
    widths = [d.textlength(ch, font=fnt) for ch in text]
    box = d.textbbox((0, 0), text, font=fnt)
    return sum(widths) + tracking * max(0, len(text) - 1), box[3] - box[1]


class Layer:
    """An RGBA scratch canvas drawn at SS resolution then resolved down.

    Drawing supersampled is what keeps every silhouette edge soft instead of
    stair-stepped, which matters a lot at this grade where shapes are nearly
    the same value as the background.
    """

    def __init__(self, ss=SS):
        self.ss = ss
        self.img = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def s(self, v):
        return v * self.ss

    def resolve(self, blur=0.0):
        out = self.img.resize((W, H), Image.LANCZOS)
        if blur > 0:
            out = out.filter(ImageFilter.GaussianBlur(blur))
        return out


def over(base_rgb, layer_rgba):
    """Composite an RGBA PIL layer onto a float32 HxWx3 numpy base."""
    arr = np.asarray(layer_rgba, dtype=np.float32)
    a = arr[:, :, 3:4] / 255.0
    return base_rgb * (1 - a) + arr[:, :, :3] * a


def add_light(base_rgb, layer_rgba, gain=1.0):
    """Additive composite - for anything that emits rather than blocks."""
    arr = np.asarray(layer_rgba, dtype=np.float32)
    a = arr[:, :, 3:4] / 255.0
    return base_rgb + arr[:, :, :3] * a * gain
