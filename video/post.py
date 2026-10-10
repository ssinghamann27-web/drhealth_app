"""Post-processing: the pass that makes it look photographed rather than drawn.

Reflection, bloom, light shafts, halation and chromatic aberration all run on
the assembled float frame. Everything expensive happens on a quarter-scale
grid and is bilinearly expanded - these are all low-frequency effects, so the
result is indistinguishable and roughly twenty times cheaper.
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from style import H, W, clamp, lerp

LW, LH = W // 4, H // 4
_lyy, _lxx = np.mgrid[0:LH, 0:LW].astype(np.float32)
_lnx = _lxx / LW
_lny = _lyy / LH


def _boxblur(a, r):
    if r < 1:
        return a
    h, w = a.shape
    pad = np.pad(a, ((0, 0), (r + 1, r)), mode="edge")
    c = np.cumsum(pad, axis=1, dtype=np.float32)
    a = (c[:, 2 * r + 1:] - c[:, :w]) * np.float32(1.0 / (2 * r + 1))
    pad = np.pad(a, ((r + 1, r), (0, 0)), mode="edge")
    c = np.cumsum(pad, axis=0, dtype=np.float32)
    return (c[2 * r + 1:, :] - c[:h, :]) * np.float32(1.0 / (2 * r + 1))


def fblur(a, sigma):
    """Gaussian-ish blur for float arrays. PIL's GaussianBlur rejects mode F,
    and three box passes are both valid and faster."""
    r = max(1, int(round(sigma * 0.85)))
    for _ in range(3):
        a = _boxblur(a, r)
    return a


def _up(a):
    return np.asarray(Image.fromarray(a, "F").resize((W, H), Image.BILINEAR),
                      dtype=np.float32)


def _down(a):
    return np.asarray(Image.fromarray(a, "F").resize((LW, LH), Image.BILINEAR),
                      dtype=np.float32)


def reflection(base, mask, ground_y, strength=0.55, squash=0.42, wobble=2.6,
               t=0.0, tint=(150, 40, 38)):
    """Mirror everything standing on the ground into wet tarmac below it.

    Nothing sells a night exterior faster than the floor giving something back.
    The copy is squashed, blurred with depth, rippled, and falls off fast.
    """
    if strength <= 0.01:
        return base
    top = max(0, ground_y - int(H * 0.46))
    src = mask.crop((0, top, W, ground_y))
    sh = ground_y - top
    if sh < 8:
        return base
    refl = src.transpose(Image.FLIP_TOP_BOTTOM)
    rh = max(4, int(sh * squash))
    refl = refl.resize((W, rh), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2.6))

    a = np.asarray(refl, dtype=np.float32) / 255.0
    # vertical falloff - the reflection dies away from the water line
    fall = np.linspace(1.0, 0.0, rh, dtype=np.float32)[:, None] ** 1.5
    # horizontal ripple, so it reads as a wet surface and not a mirror
    rows = np.arange(rh, dtype=np.float32)
    shift = (np.sin(rows * 0.09 + t * 1.7) * wobble
             + np.sin(rows * 0.031 + t * 0.9) * wobble * 0.6)
    idx = np.clip(np.arange(W)[None, :] + shift[:, None], 0, W - 1).astype(np.int32)
    a = np.take_along_axis(a, idx, axis=1) * fall * strength

    y0 = ground_y
    y1 = min(H, ground_y + rh)
    if y1 <= y0:
        return base
    a = a[:y1 - y0, :, None]
    sub = base[y0:y1]
    col = np.asarray(tint, dtype=np.float32)
    # darken toward the tint, then let a little of it glow back
    base[y0:y1] = sub * (1.0 - a * 0.82) + col * a * 0.30
    return base


def glow(base, bloom_thr=118.0, bloom_amt=0.42, bloom_r=9.0,
         halo_thr=152.0, halo_amt=0.26, halo_r=26.0):
    """Bloom and halation in one pass.

    Both read the same downsampled luminance, so the expensive part is paid
    once. The red channel stands in for luminance - on a grade this red the
    difference is invisible and it avoids a full-frame mean.
    """
    lum = _down(np.ascontiguousarray(base[:, :, 0]))
    out = None

    hi = lum - bloom_thr
    if hi.max() > 1.0:
        np.maximum(hi, 0.0, out=hi)
        out = _up(fblur(hi, bloom_r))[:, :, None] * (
            np.float32([1.0, 0.86, 0.82]) * bloom_amt)

    hh = lum - halo_thr
    if hh.max() > 1.0:
        np.maximum(hh, 0.0, out=hh)
        h = _up(fblur(hh, halo_r))[:, :, None] * (
            np.float32([1.0, 0.22, 0.16]) * halo_amt)
        out = h if out is None else out + h

    if out is None:
        return base
    base += out
    return base


def god_rays(base, src_mask, cx, cy, strength=0.5, decay=0.92, samples=12,
             tint=(236, 214, 206)):
    """Radial light shafts streaming out of a bright source.

    A cheap iterative zoom-blur toward the source point, run at quarter scale.
    """
    if strength <= 0.01:
        return base
    m = np.asarray(src_mask, dtype=np.float32)
    small = _down(m) / 255.0
    if small.max() < 0.01:
        return base

    acc = np.zeros_like(small)
    w = 1.0
    img = Image.fromarray(small, "F")
    for i in range(1, samples + 1):
        sc = 1.0 + 0.055 * i
        nw, nh = max(2, int(LW * sc)), max(2, int(LH * sc))
        big = img.resize((nw, nh), Image.BILINEAR)
        ox = int((nw - LW) * clamp(cx / W))
        oy = int((nh - LH) * clamp(cy / H))
        acc += np.asarray(big.crop((ox, oy, ox + LW, oy + LH)),
                          dtype=np.float32) * w
        w *= decay
    acc /= max(1e-6, samples * 0.55)
    acc = fblur(acc, 3.0)
    return base + _up(acc)[:, :, None] * strength * np.asarray(tint, np.float32) / 255.0


def chromatic_u8(img, amount=2.0):
    """Radial colour fringing at the edges, as a fast lens would give.

    Runs last, on the 8-bit frame, where PIL's resize is several times cheaper
    than the float path.
    """
    if amount <= 0.05:
        return img
    out = img.copy()
    for ch, k in ((0, amount), (2, -amount)):
        nw, nh = W + int(k * 2), H + int(k * 2 * H / W)
        if nw <= 0 or nh <= 0:
            continue
        lay = Image.fromarray(img[:, :, ch]).resize((nw, nh), Image.BILINEAR)
        ox, oy = (nw - W) // 2, (nh - H) // 2
        if ox < 0 or oy < 0:
            lay = lay.resize((W, H), Image.BILINEAR)
            out[:, :, ch] = np.asarray(lay)
        else:
            out[:, :, ch] = np.asarray(lay.crop((ox, oy, ox + W, oy + H)))
    return out


def gate_weave(base, t, amount=1.2):
    """A hair of frame float, like film through a gate."""
    dx = math.sin(t * 2.3) * amount + math.sin(t * 7.1) * amount * 0.3
    dy = math.cos(t * 1.7) * amount * 0.7
    if abs(dx) < 0.05 and abs(dy) < 0.05:
        return base
    return np.roll(np.roll(base, int(round(dy)), axis=0), int(round(dx)), axis=1)


_ly = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]


_fog_cache = {}


def depth_fog(base, colour=(42, 10, 12), near=0.60, far=0.92, strength=0.30):
    """Lift the far ground toward the fog colour so layers separate by depth."""
    if strength <= 0.01:
        return base
    key = (round(near, 3), round(far, 3), round(strength, 3))
    k = _fog_cache.get(key)
    if k is None:
        k = (1.0 - np.clip((_ly - near) / max(1e-6, far - near), 0, 1) ** 1.4)
        k = (k * strength).astype(np.float32)
        _fog_cache[key] = k
    return base + (np.asarray(colour, np.float32) - base) * k


_lut_cache = {}


def grade(img, contrast=1.14, pivot=52.0, lift=3.0, sat=1.06):
    """A gentle S-curve and a touch of saturation.

    Density only reads if the midtones separate; without this the dense
    frames turn into one flat brown mass.
    """
    out = (img - pivot) * contrast + pivot + lift
    if sat != 1.0:
        lum = out.mean(axis=2, keepdims=True)
        out = lum + (out - lum) * sat
    return out


def soft_glow(img, cx, cy, w, h, amt, colour=(236, 206, 198)):
    """A wide, edgeless pool of light added straight into the frame.

    Drawing this as a mask ellipse gives a hard-edged disc no matter how much
    blur follows it; evaluating the falloff directly is both smooth and cheap.
    """
    if amt <= 0.004:
        return img
    dx = (_lnx - cx / W) / max(1e-4, (w * 0.5) / W)
    dy = (_lny - cy / H) / max(1e-4, (h * 0.5) / H)
    g = np.clip(1.0 - np.sqrt(dx * dx + dy * dy), 0.0, 1.0) ** 2.3
    return img + _up(g)[:, :, None] * (amt * np.asarray(colour, np.float32))
