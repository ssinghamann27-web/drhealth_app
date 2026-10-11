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
    # dimensions come from the source frame, not the render size: in reel mode
    # the render is vertical while the frame being keyed is still 16:9
    sh, sw = mx.shape
    hw, hh = sw // 2, sh // 2
    lum = Image.fromarray(mx.astype(np.uint8)).resize((hw, hh), Image.BILINEAR)
    edge = lum.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(7))
    # dilate once more at half scale to close glyph interiors, still cheaply
    edge = edge.filter(ImageFilter.MaxFilter(3))
    gate = np.asarray(edge.resize((sw, sh), Image.BILINEAR), dtype=np.float32)
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


# --- vertical (reel) placement -------------------------------------------
SRC_W, SRC_H = 1920, 1080
BAR_TOP = 1070          # the original's progress bar starts here
BAR_COLOUR = (196, 30, 38)


def composite_vertical(bg, src, y_offset=430):
    """Lay the original's text layer into a natively vertical frame.

    The text is keyed at source resolution, then the whole layer - lyrics,
    highlights, chapter plate, section labels, credits - is scaled to the
    reel's full width as one piece. Scaling to width rather than cropping is
    what keeps every line complete: the furniture runs from x 85 to x 1916 of
    1920, so there is no crop that keeps it.

    bg: H x W x 3 float32 (the vertical render)
    src: 1080 x 1920 x 3 float32 (the original frame)
    """
    h, w = bg.shape[:2]
    m = text_matte(src)

    # The original carries a progress bar on its last rows. Keyed as-is it
    # lands as a red line across the middle of a vertical frame, so it is cut
    # from the text layer and redrawn where it belongs - the bottom edge.
    bar_rows = src[BAR_TOP:, :, 0].mean(axis=0)
    m[BAR_TOP:] = 0.0

    scale = w / float(SRC_W)
    tw, th = w, max(1, int(round(SRC_H * scale)))

    lay = Image.fromarray(np.clip(src, 0, 255).astype(np.uint8)).resize(
        (tw, th), Image.LANCZOS)
    alpha = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize(
        (tw, th), Image.LANCZOS)

    y0 = int(np.clip(y_offset, 0, max(0, h - th)))
    y1 = y0 + th

    a = (np.asarray(alpha, dtype=np.float32) / 255.0)[:, :, None]
    t = np.asarray(lay, dtype=np.float32)
    bg[y0:y1] = bg[y0:y1] * (1.0 - a) + t * a

    lit = np.nonzero(bar_rows > 40)[0]
    if len(lit) > 4:
        bx = int(round(lit[-1] * scale))
        bh = max(3, int(round(h * 0.0028)))
        bg[h - bh:, :bx] = np.asarray(BAR_COLOUR, dtype=np.float32)

    f = flash_amount(src)
    if f > 0.004:
        bg = bg * (1.0 - f) + float(src.mean()) * f
    return bg
