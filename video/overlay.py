"""Lift v8's text layer off its background so new backgrounds can go behind it.

The lyrics, their karaoke highlights, the chapter plates and the credits are
the part of the original that works, and re-typesetting them would risk the
timing. Instead they are keyed out of the source frames and composited over
the new artwork, so the original typography survives exactly as cut.

The key is colour (bright and near-neutral, or hot red) gated by local edge
energy, because glyphs have hard edges and light cones do not.
"""
import numpy as np
from PIL import Image, ImageFilter

from style import H, W

FLASH_LO, FLASH_HI = 88.0, 150.0


def text_matte(a):
    """a: float32 HxWx3 source frame -> float32 HxW alpha in 0..1."""
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx = a.max(2)
    mn = a.min(2)

    white = np.clip((mn - 92.0) / 70.0, 0, 1) * np.clip(1.0 - (mx - mn) / 95.0, 0, 1)
    red = (np.clip((r - 115.0) / 80.0, 0, 1)
           * np.clip((r - g - 50.0) / 60.0, 0, 1)
           * np.clip((r - b - 40.0) / 60.0, 0, 1))
    key = np.clip(white + red, 0, 1)

    # The gate is only a region selector, so it is built at half resolution:
    # PIL's MaxFilter is O(k^2) per pixel and ruinous at full size.
    hw, hh = W // 2, H // 2
    lum = Image.fromarray(mx.astype(np.uint8)).resize((hw, hh), Image.BILINEAR)
    edge = lum.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(7))
    # dilate once more at half scale to close glyph interiors, still cheaply
    edge = edge.filter(ImageFilter.MaxFilter(3))
    gate = np.asarray(edge.resize((W, H), Image.BILINEAR), dtype=np.float32)
    gate = np.clip((gate - 18.0) / 40.0, 0, 1)

    return np.clip(key * gate * 1.6, 0, 1) * key


def flash_amount(a):
    """1 where the source frame is a full-frame flash, which must pass through
    whole rather than being keyed."""
    mean = float(a.mean())
    return float(np.clip((mean - FLASH_LO) / (FLASH_HI - FLASH_LO), 0, 1))


def composite(bg, src):
    """bg, src: float32 HxWx3. Returns bg with v8's text laid over it."""
    m = text_matte(src)[:, :, None]
    out = bg * (1.0 - m) + src * m
    f = flash_amount(src)
    if f > 0.004:
        out = out * (1.0 - f) + src * f
    return out
