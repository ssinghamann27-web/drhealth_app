"""Atmosphere: the living background the props sit inside.

v8's background was a static red gradient, which is a large part of why the
intro read as empty. Here the glow breathes on the bar, haze drifts, embers
rise and rain carries wind - so even a held frame has motion in it.

The glow, haze and vignette are smooth gradients, so they are evaluated on a
quarter-scale grid and bilinearly expanded: visually identical, ~20x cheaper.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from style import H, W, clamp, lerp, smoothstep

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_ny = (_yy / H)

LW, LH = W // 4, H // 4
_lyy, _lxx = np.mgrid[0:LH, 0:LW].astype(np.float32)
_lnx = _lxx / LW
_lny = _lyy / LH

_rng = np.random.default_rng(20251010)
_GRAIN = _rng.normal(0, 1, (H + 64, W + 64)).astype(np.float32)
# White noise per pixel is both un-filmic and ruinous to encode. A little
# spatial correlation makes it read as film stock and compress sanely.
def _soften(a):
    p = np.pad(a, 1, mode="wrap")
    a = 0.25 * p[:-2, 1:-1] + 0.5 * p[1:-1, 1:-1] + 0.25 * p[2:, 1:-1]
    p = np.pad(a, 1, mode="wrap")
    return (0.25 * p[1:-1, :-2] + 0.5 * p[1:-1, 1:-1] + 0.25 * p[1:-1, 2:])


_GRAIN = _soften(_GRAIN).astype(np.float32)
_GRAIN *= np.float32(1.0 / max(1e-6, float(_GRAIN.std())))

_cloud_small = _rng.random((18, 32)).astype(np.float32)
_LCLOUD = np.asarray(
    Image.fromarray((_cloud_small * 255).astype(np.uint8)).resize((LW, LH), Image.BICUBIC),
    dtype=np.float32,
) / 255.0

_TOPFALL = np.clip(_ny / 0.09, 0, 1)[:, :, None]


def _upscale(a):
    """float32 LHxLW -> HxW, bilinear."""
    return np.asarray(Image.fromarray(a, "F").resize((W, H), Image.BILINEAR),
                      dtype=np.float32)


def _lradial(cx, cy, rx, ry):
    dx = (_lnx - cx) / rx
    dy = (_lny - cy) / ry
    return np.sqrt(dx * dx + dy * dy)


def background(t, glow_y=0.62, glow_x=0.5, intensity=1.0, pulse=0.0, cool=0.0):
    """Deep red field with a breathing core. Returns float32 HxWx3 in 0..255."""
    breathe = 1.0 + 0.07 * math.sin(t * 1.9) + pulse
    r = _lradial(glow_x, glow_y, 0.58 + 0.03 * math.sin(t * 0.5), 0.48)
    core = np.clip(1.0 - r, 0.0, 1.0) ** 2.1

    drift = 0.72 + 0.56 * np.roll(_LCLOUD, int((t * 2.25) % LW), axis=1)

    amp = 96.0 * intensity * breathe
    base = core * drift * amp
    horizon = np.clip((_lny - 0.74) / 0.26, 0, 1) ** 1.5

    red = base + horizon * 16.0 * intensity
    grn = base * 0.17 + horizon * 2.4 * intensity
    blu = base * 0.19 + horizon * 3.0 * intensity

    if cool > 0:
        grey = (red + grn + blu) / 3.0
        red = red + (grey * 0.95 - red) * cool
        grn = grn + (grey * 0.98 - grn) * cool
        blu = blu + (grey * 1.18 - blu) * cool

    return np.stack([_upscale(red), _upscale(grn), _upscale(blu)], axis=2)


def apply_grain(img, t, amount=7.0):
    oy = int((t * 137) % 64)
    ox = int((t * 263) % 64)
    g = _GRAIN[oy:oy + H, ox:ox + W][:, :, None]
    return img + g * amount


_vig_cache = {}


def _vignette_mask(strength):
    key = round(strength, 3)
    if key not in _vig_cache:
        r = _lradial(0.5, 0.52, 0.80, 0.78)
        v = np.clip(1.0 - (r ** 2.4) * 0.92 * strength, 0.0, 1.0)
        _vig_cache[key] = _upscale(v)[:, :, None] * (0.12 + 0.88 * _TOPFALL)
    return _vig_cache[key]


def apply_vignette(img, strength=1.0):
    return img * _vignette_mask(strength)


def letterbox(img, t):
    """Thin film bars that ease open over the first beat."""
    o = 1.0 - smoothstep(clamp(t / 1.2))
    bar = int(26 + 58 * o)
    if bar > 0:
        img[:bar] = 0.0
        img[H - bar:] = 0.0
    return img


def haze_band(t, y0, y1, strength, colour=(150, 36, 34)):
    """A soft horizontal fog bank - used to bed props into the ground."""
    if strength <= 0.003:
        return None
    band = np.clip(1 - np.abs((_lny - (y0 + y1) / 2) / ((y1 - y0) / 2)), 0, 1) ** 1.6
    wob = 0.82 + 0.18 * np.sin(_lnx * 11 + t * 0.8)
    a = _upscale(band * wob * strength * 150).astype(np.uint8)
    lay = np.zeros((H, W, 4), dtype=np.uint8)
    lay[:, :, 0], lay[:, :, 1], lay[:, :, 2] = colour
    lay[:, :, 3] = a
    return Image.fromarray(lay, "RGBA")


class Rain:
    """Wind-driven rain, drawn as one additive layer."""

    def __init__(self, n=520, seed=7):
        r = np.random.default_rng(seed)
        self.x = r.random(n) * (W * 1.6) - W * 0.3
        self.y = r.random(n) * H
        self.spd = 760 + r.random(n) * 1250
        self.len = 16 + r.random(n) * 46
        self.a = 0.16 + r.random(n) * 0.5

    def draw(self, t, strength, wind=0.0):
        if strength <= 0.003:
            return None
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        gust = wind + 0.42 * math.sin(t * 0.7) + 0.16 * math.sin(t * 2.3)
        y = (self.y + t * self.spd) % (H + 120) - 60
        x = (self.x + y * gust) % (W * 1.4) - W * 0.2
        dy = self.len
        dx = dy * gust
        for i in range(len(x)):
            a = int(self.a[i] * 190 * strength)
            if a <= 2:
                continue
            d.line([(x[i], y[i]), (x[i] + dx[i], y[i] + dy[i])],
                   fill=(206, 176, 178, a), width=1)
        return lay


class Embers:
    """Slow red motes rising - the one warm thing in the frame."""

    def __init__(self, n=90, seed=3):
        r = np.random.default_rng(seed)
        self.x = r.random(n) * W
        self.y = r.random(n) * H
        self.spd = 16 + r.random(n) * 52
        self.rad = 1.0 + r.random(n) * 2.8
        self.ph = r.random(n) * 6.283
        self.sw = 10 + r.random(n) * 44

    def draw(self, t, strength=1.0):
        if strength <= 0.003:
            return None
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for i in range(len(self.x)):
            y = (self.y[i] - t * self.spd[i]) % (H + 80) - 40
            x = self.x[i] + math.sin(t * 0.5 + self.ph[i]) * self.sw[i]
            fade = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 1.3 + self.ph[i]))
            a = int(150 * fade * strength)
            if a <= 3:
                continue
            r = self.rad[i]
            d.ellipse([x - r, y - r, x + r, y + r], fill=(240, 96, 62, a))
        return lay.filter(ImageFilter.GaussianBlur(1.6))
