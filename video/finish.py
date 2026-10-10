"""Finishing pass.

Nothing here changes what is in the frame - no geometry, no type, no colour
decisions. It is the grade and lens work that sits on top of a finished
render: local contrast, a filmic highlight rolloff, a whisper of split-tone,
anamorphic streaks off the hot points, a light sharpen and a dither.

Everything low-frequency runs on a quarter-scale grid and is expanded.
"""
import numpy as np
from PIL import Image

from style import H, W

LW, LH = W // 4, H // 4


def _down(a):
    return np.asarray(Image.fromarray(a, "F").resize((LW, LH), Image.BILINEAR),
                      dtype=np.float32)


def _up(a):
    return np.asarray(Image.fromarray(a, "F").resize((W, H), Image.BILINEAR),
                      dtype=np.float32)


def _box(a, r):
    if r < 1:
        return a
    h, w = a.shape
    p = np.pad(a, ((0, 0), (r + 1, r)), mode="edge")
    c = np.cumsum(p, axis=1, dtype=np.float32)
    a = (c[:, 2 * r + 1:] - c[:, :w]) * np.float32(1.0 / (2 * r + 1))
    p = np.pad(a, ((r + 1, r), (0, 0)), mode="edge")
    c = np.cumsum(p, axis=0, dtype=np.float32)
    return (c[2 * r + 1:, :] - c[:h, :]) * np.float32(1.0 / (2 * r + 1))


def _blur(a, r, passes=2):
    for _ in range(passes):
        a = _box(a, r)
    return a


_RNG = np.random.default_rng(4242)
_DITHER = _RNG.random((H + 64, W + 64)).astype(np.float32) - 0.5


def clarity(img, amount=0.58, radius=13):
    """Local contrast. The single biggest step between 'rendered' and 'graded'."""
    if amount <= 0.01:
        return img
    lum = _down(np.ascontiguousarray(img.mean(axis=2)))
    base = _up(_blur(lum, radius))
    detail = img.mean(axis=2) - base
    return img + detail[:, :, None] * amount


def highlight_rolloff(img, knee=168.0, ceiling=268.0):
    """Shoulder the top end so whites bloom off instead of clipping flat."""
    x = img
    over = x > knee
    if not over.any():
        return x
    span = max(1.0, ceiling - knee)
    # evaluate the shoulder only above the knee: below it 1+t crosses zero
    t = np.maximum(0.0, x - knee) / span
    rolled = knee + span * (t / (1.0 + t)) * 1.52
    return np.where(over, rolled, x)


def split_tone(img, shadow=(-2.0, 0.0, 5.0), highlight=(8.0, 2.0, -4.0),
               pivot=96.0, amount=1.0):
    """Cool the shadows a touch, warm the highlights a touch.

    Kept deliberately small: the red has to stay the colour of the film.
    """
    if amount <= 0.01:
        return img
    lum = img.mean(axis=2, keepdims=True)
    k = np.clip(lum / pivot, 0, 1)
    sh = np.asarray(shadow, np.float32)
    hi = np.asarray(highlight, np.float32)
    return img + (sh * (1.0 - k) + hi * k) * amount


def anamorphic(img, threshold=118.0, amount=0.70, length=260,
               tint=(0.62, 0.80, 1.0)):
    """Horizontal streaks off the hot points, the way a wide lens flares."""
    lum = _down(np.ascontiguousarray(img.max(axis=2)))
    hot = np.maximum(0.0, lum - threshold)
    if hot.max() < 1.0:
        return img
    r = max(2, length // 8)
    s = _box(hot, r)
    s = _box(s, r)
    s = _blur(s, 2, passes=1)
    return img + _up(s)[:, :, None] * amount * np.asarray(tint, np.float32)


def glow(img, threshold=52.0, amount=0.50, radius=13, tint=(1.0, 0.80, 0.74)):
    """A wide soft bloom off everything bright - lights, highlights and type.

    This is most of what reads as 'shine': light in a modern grade does not
    stop at the edge of the thing emitting it.
    """
    lum = _down(np.ascontiguousarray(img.max(axis=2)))
    hot = np.maximum(0.0, lum - threshold)
    if hot.max() < 1.0:
        return img
    g = _up(_blur(hot, radius, passes=3))[:, :, None]
    return img + g * amount * np.asarray(tint, np.float32)


def sparkle(img, threshold=186.0, amount=0.42, arm=58):
    """Cross glints on the very hottest points."""
    lum = _down(np.ascontiguousarray(img.max(axis=2)))
    hot = np.maximum(0.0, lum - threshold)
    if hot.max() < 1.0:
        return img
    r = max(1, arm // 8)
    h = np.pad(hot, ((0, 0), (r + 1, r)), mode="edge")
    c = np.cumsum(h, axis=1, dtype=np.float32)
    hz = (c[:, 2 * r + 1:] - c[:, :hot.shape[1]]) / (2 * r + 1)
    v = np.pad(hot, ((r + 1, r), (0, 0)), mode="edge")
    c = np.cumsum(v, axis=0, dtype=np.float32)
    vt = (c[2 * r + 1:, :] - c[:hot.shape[0], :]) / (2 * r + 1)
    return img + _up(hz + vt)[:, :, None] * amount * np.float32([1.0, 0.95, 0.92])


def sharpen(img, amount=0.34):
    """A light unsharp mask so edges and type read crisp."""
    if amount <= 0.01:
        return img
    a = img
    blur = (np.roll(a, 1, 0) + np.roll(a, -1, 0)
            + np.roll(a, 1, 1) + np.roll(a, -1, 1) + a * 2.0) * 0.1666667
    return a + (a - blur) * amount


def dither(img, t, amount=1.1):
    oy = int((t * 311) % 64)
    ox = int((t * 457) % 64)
    return img + _DITHER[oy:oy + H, ox:ox + W][:, :, None] * amount


def lift(img, gamma=0.945, gain=1.045, black=1.0):
    """Open the midtones a little.

    The film is graded very dark - mean luma sits around 12-25 of 255 - so
    without this there is almost nothing above any sensible glow threshold
    and the whole finishing pass has nothing to act on.
    """
    x = np.clip(img - black, 0, None) * gain
    return np.power(x / 255.0, gamma) * 255.0


def finish(frame_u8, t):
    """frame_u8: HxWx3 uint8 -> HxWx3 uint8."""
    img = frame_u8.astype(np.float32)
    img = lift(img)
    img = clarity(img)
    img = glow(img)
    img = anamorphic(img)
    img = sparkle(img)
    img = split_tone(img)
    img = highlight_rolloff(img)
    img = sharpen(img)
    img = dither(img, t)
    return np.clip(img, 0, 255).astype(np.uint8)
