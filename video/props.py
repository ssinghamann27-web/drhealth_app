"""The cast and the set.

Everything is a silhouette drawn into a single-channel mask, so a whole scene
resolves in a handful of composites. Props take a `fade` and a `rise` so they
can be eased on and off instead of cutting in - v8's props popped, which is
what made the intro feel like a slideshow.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from style import H, W, clamp, lerp, smoothstep

GROUND = int(H * 0.815)


def new_mask():
    m = Image.new("L", (W, H), 0)
    return m, ImageDraw.Draw(m)


def _prep(mask, blur):
    """Crop to the mask's bbox first, then blur - so cost scales with the prop,
    not with the frame."""
    bb = mask.getbbox()
    if bb is None:
        return None, None
    pad = int(blur * 3) + 2
    x0 = max(0, bb[0] - pad); y0 = max(0, bb[1] - pad)
    x1 = min(W, bb[2] + pad); y1 = min(H, bb[3] + pad)
    crop = mask.crop((x0, y0, x1, y1))
    if blur > 0:
        crop = crop.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(crop, dtype=np.float32), (y0, y1, x0, x1)


def paint(base, mask, colour, alpha=1.0, blur=0.7):
    """Composite a flat-coloured mask over the float frame (occluding)."""
    if alpha <= 0.002:
        return base
    a, box = _prep(mask, blur)
    if a is None:
        return base
    y0, y1, x0, x1 = box
    a = a[:, :, None] * (alpha / 255.0)
    sub = base[y0:y1, x0:x1]
    if colour == (0, 0, 0):
        sub *= (1.0 - a)
    else:
        sub += (np.asarray(colour, dtype=np.float32) - sub) * a
    return base


def emit(base, mask, colour, gain=1.0, blur=1.6):
    """Additive composite - for anything that gives off light."""
    if gain <= 0.002:
        return base
    a, box = _prep(mask, blur)
    if a is None:
        return base
    y0, y1, x0, x1 = box
    base[y0:y1, x0:x1] += (a[:, :, None] * (gain / 255.0)) * np.asarray(
        colour, dtype=np.float32)
    return base


# --- cast ----------------------------------------------------------------
def figure(d, x, y, h, phase=0.0, walking=True, fill=255, lean=0.0,
           head_turn=0.0, arms_up=0.0):
    """A figure. `y` is the ground its feet stand on.

    A standing figure gets a real stance - feet apart, arms hanging clear of
    the body. Collapsing both legs onto one line makes a crowd read as a row
    of pins rather than as people.
    """
    if h < 3:
        return
    lw = max(1, int(round(h * 0.055)))
    bob = math.sin(phase * 2) * h * 0.012 if walking else 0.0
    hip = y - h * 0.44 + bob
    sho = y - h * 0.74 + bob
    headr = h * 0.105
    hcy = y - h * 0.87 + bob
    hcx = x + lean * h * 0.10

    sw = math.sin(phase) if walking else 0.0

    # legs
    for s in (1, -1):
        if walking:
            a = sw * s
            kx, ky = x + a * h * 0.15, hip + h * 0.22
            fx, fy = x + a * h * 0.26, y - abs(a) * h * 0.05
        else:
            kx, ky = x + s * h * 0.055, hip + h * 0.23
            fx, fy = x + s * h * 0.085, y
        d.line([(x, hip), (kx, ky)], fill=fill, width=lw)
        d.line([(kx, ky), (fx, fy)], fill=fill, width=lw)

    # torso
    d.line([(x, hip), (hcx * 0.3 + x * 0.7, sho)], fill=fill, width=lw)

    # arms
    for s in (1, -1):
        if arms_up > 0:
            # marionette pose: elbows out, hands up near head height
            ex = x + s * h * lerp(0.13, 0.21, arms_up)
            ey = lerp(sho + h * 0.17, sho - h * 0.02, arms_up)
            hx2 = x + s * h * lerp(0.17, 0.28, arms_up)
            hy2 = lerp(sho + h * 0.33, sho - h * 0.19, arms_up)
        elif walking:
            a = -sw * s
            ex, ey = x + a * h * 0.13 + s * h * 0.05, sho + h * 0.17
            hx2, hy2 = x + a * h * 0.21 + s * h * 0.06, sho + h * 0.33
        else:
            ex, ey = x + s * h * 0.085, sho + h * 0.17
            hx2, hy2 = x + s * h * 0.115, sho + h * 0.34
        d.line([(x + s * h * 0.012, sho + h * 0.02), (ex, ey)], fill=fill, width=lw)
        d.line([(ex, ey), (hx2, hy2)], fill=fill, width=lw)

    # head
    hx = hcx + head_turn * headr * 0.45
    d.ellipse([hx - headr, hcy - headr, hx + headr, hcy + headr], fill=fill)
    return (hx, hcy, headr)


def eye(d, cx, cy, r, open_amt=1.0, fill=255):
    if open_amt <= 0.02 or r < 0.6:
        return
    rr = r * open_amt
    d.ellipse([cx - rr, cy - rr * 0.78, cx + rr, cy + rr * 0.78], fill=fill)


# --- set -----------------------------------------------------------------
def ridge(d, y, amp, seed, fill=255, span=(-0.3, 1.3), steps=120, rough=1.0,
          floor=None):
    """A mountain ridge line, filled down to `floor` (not to the frame edge -
    flooding the bottom of frame is what buried every prop in the first pass)."""
    r = np.random.default_rng(seed)
    offs = r.normal(0, 1, steps + 1)
    pts = []
    x0, x1 = span[0] * W, span[1] * W
    for i in range(steps + 1):
        u = i / steps
        x = lerp(x0, x1, u)
        env = math.sin(u * math.pi) ** 0.6
        hgt = (math.sin(u * 7.1 + seed) * 0.5 + math.sin(u * 2.3 + seed * 2) * 0.9
               + offs[i] * 0.35 * rough)
        pts.append((x, y - amp * env * (0.55 + 0.45 * hgt)))
    fy = H + 10 if floor is None else floor
    pts += [(x1, fy), (x0, fy)]
    d.polygon(pts, fill=fill)


def road(d, vy, vx, near_w, fill=255, lanes=7, t=0.0, scroll=0.0, surface=None):
    """A road running back to a vanishing point. Dashes alone read as a red
    wedge; the surface and converging edges are what sell the perspective."""
    if surface is not None:
        surface.polygon([(vx - near_w * 1.6, H + 20), (vx + near_w * 1.6, H + 20),
                         (vx + near_w * 0.05, vy), (vx - near_w * 0.05, vy)],
                        fill=fill)
    for s in (-1, 1):
        d.line([(vx + s * near_w * 0.05, vy), (vx + s * near_w * 1.6, H + 20)],
               fill=fill, width=2)
    for i in range(lanes):
        u = ((i / lanes) + scroll) % 1.0
        p_ = u ** 2.6
        y = lerp(vy, H + 40, p_)
        wdt = max(1.0, near_w * 0.075 * (0.08 + p_))
        ln = max(2.0, 70 * (0.05 + p_))
        d.polygon([(vx - wdt, y), (vx + wdt, y),
                   (vx + wdt * 1.3, y + ln), (vx - wdt * 1.3, y + ln)], fill=fill)


def pole(d, x, base_y, h, fill=255, arms=2, lw=None):
    """Telephone pole with crossbars."""
    lw = lw or max(1, int(h * 0.022))
    d.line([(x, base_y), (x, base_y - h)], fill=fill, width=lw)
    for i in range(arms):
        ay = base_y - h * (0.84 - i * 0.13)
        aw = h * (0.20 - i * 0.05)
        d.line([(x - aw, ay), (x + aw, ay)], fill=fill, width=max(1, lw - 1))
        for s in (-1, 1):
            d.line([(x + s * aw * 0.92, ay), (x + s * aw * 0.92, ay - h * 0.028)],
                   fill=fill, width=max(1, lw - 1))


def wire(d, x0, y0, x1, y1, sag, fill=255, lw=2, t=0.0, sway=0.0):
    """Catenary between two poles, with a slow wind sway."""
    pts = []
    n = 22
    for i in range(n + 1):
        u = i / n
        x = lerp(x0, x1, u)
        y = lerp(y0, y1, u) + math.sin(u * math.pi) * sag
        y += math.sin(u * 3.1 + t * 1.4) * sway
        pts.append((x, y))
    d.line(pts, fill=fill, width=lw, joint="curve")


def dead_tree(d, x, base_y, h, seed=1, fill=255, depth=5, wind=0.0, t=0.0):
    """Recursive bare tree. The branches drift, so it never looks pasted on."""
    r = np.random.default_rng(seed)

    def limb(px, py, ang, ln, w, lvl):
        gust = math.sin(t * 0.9 + lvl * 0.7 + x * 0.01) * wind * (lvl / depth)
        a = ang + gust * 0.14
        ex = px + math.cos(a) * ln
        ey = py + math.sin(a) * ln
        d.line([(px, py), (ex, ey)], fill=fill, width=max(1, int(w)))
        if lvl >= depth:
            return
        n = 2 if r.random() < 0.78 else 3
        for i in range(n):
            spread = r.uniform(0.32, 0.72) * (1 if i % 2 == 0 else -1)
            limb(ex, ey, a + spread + r.uniform(-0.12, 0.12),
                 ln * r.uniform(0.62, 0.78), w * 0.64, lvl + 1)

    limb(x, base_y, -math.pi / 2 + r.uniform(-0.12, 0.12), h * 0.33,
         max(2, h * 0.030), 1)


def building(d, x, base_y, bw, bh, seed=0, fill=255, lean=0.0):
    """One crooked building. Returns window rects for the light pass."""
    r = np.random.default_rng(seed)
    sk = lean * bh * 0.10
    d.polygon([(x - bw / 2, base_y), (x + bw / 2, base_y),
               (x + bw / 2 + sk, base_y - bh), (x - bw / 2 + sk, base_y - bh)],
              fill=fill)
    if r.random() < 0.45:  # water tank / aerial
        tw = bw * 0.22
        d.rectangle([x + sk - tw, base_y - bh - bh * 0.10,
                     x + sk + tw, base_y - bh], fill=fill)
    windows = []
    cols = max(1, int(bw / 26))
    rows = max(1, int(bh / 34))
    for cy in range(rows):
        for cx in range(cols):
            if r.random() < 0.72:
                continue
            wx = x - bw / 2 + (cx + 0.32) * (bw / cols)
            wy = base_y - bh + (cy + 0.34) * (bh / rows)
            k = (wy - (base_y - bh)) / max(1.0, bh)
            wx += sk * (1 - k)
            windows.append((wx, wy, bw / cols * 0.34, bh / rows * 0.40, r.random()))
    return windows


def skyline(d, base_y, x0, x1, hmin, hmax, seed=0, fill=255, n=11, lean=0.25):
    r = np.random.default_rng(seed)
    wins = []
    x = x0
    i = 0
    while x < x1 and i < 60:
        bw = r.uniform(70, 165)
        bh = r.uniform(hmin, hmax)
        wins += building(d, x + bw / 2, base_y, bw, bh, seed=seed * 97 + i,
                         fill=fill, lean=r.uniform(-lean, lean))
        x += bw * r.uniform(0.80, 1.02)
        i += 1
    return wins


def house(d, x, base_y, w, fill=255, lw=3, door=1.0):
    """The house. Outline only, like v8 - but with a roof, chimney and porch.

    `door` 1 = open and lit, 0 = shut.
    """
    h = w * 0.78
    left, right = x - w / 2, x + w / 2
    top = base_y - h
    d.line([(left, base_y), (left, top)], fill=fill, width=lw)
    d.line([(right, base_y), (right, top)], fill=fill, width=lw)
    d.line([(left, base_y), (right, base_y)], fill=fill, width=lw)
    # roof
    apex = (x, top - h * 0.46)
    d.line([(left - w * 0.07, top), apex], fill=fill, width=lw)
    d.line([(right + w * 0.07, top), apex], fill=fill, width=lw)
    d.line([(left - w * 0.07, top), (right + w * 0.07, top)], fill=fill, width=lw)
    # chimney
    cx = x + w * 0.26
    d.line([(cx, top - h * 0.22), (cx, top - h * 0.52)], fill=fill, width=lw)
    d.line([(cx + w * 0.10, top - h * 0.27), (cx + w * 0.10, top - h * 0.52)],
           fill=fill, width=lw)
    d.line([(cx, top - h * 0.52), (cx + w * 0.10, top - h * 0.52)], fill=fill, width=lw)
    # door + window
    dw, dh = w * 0.21, h * 0.46
    dx0 = x - dw / 2
    d.rectangle([dx0, base_y - dh, dx0 + dw, base_y], outline=fill, width=lw)
    ww = w * 0.17
    d.rectangle([left + w * 0.10, top + h * 0.18, left + w * 0.10 + ww,
                 top + h * 0.18 + ww * 0.8], outline=fill, width=lw)
    return (dx0, base_y - dh, dx0 + dw, base_y)


def fence(d, x0, x1, base_y, h, fill=255, lw=2, step=34):
    x = x0
    while x < x1:
        d.line([(x, base_y), (x, base_y - h)], fill=fill, width=lw)
        x += step
    d.line([(x0, base_y - h * 0.64), (x1, base_y - h * 0.64)], fill=fill, width=lw)


def crow(d, x, y, s, phase, fill=255):
    """Bird silhouette, wings beating."""
    f = math.sin(phase)
    d.line([(x - s, y - f * s * 0.62), (x, y), (x + s, y - f * s * 0.62)],
           fill=fill, width=max(1, int(s * 0.17)), joint="curve")
    d.ellipse([x - s * 0.17, y - s * 0.13, x + s * 0.17, y + s * 0.13], fill=fill)


def mask_face(d_line, cx, cy, r, crack=0.0, seed=5, fill=255, lw=4, burst=0.0,
              d_fill=None):
    """A blank face that fractures on the beat and then flies apart.

    Featureless on purpose - the only feature it ever gets is the eye that
    opens behind it once the mask fails.
    """
    rng = np.random.default_rng(seed)
    box = [cx - r, cy - r * 1.18, cx + r, cy + r * 1.18]
    if d_fill is not None:
        d_fill.ellipse(box, fill=255)
    d_line.ellipse(box, outline=fill, width=lw)
    # a sealed mouth, nothing else
    d_line.line([(cx - r * 0.26, cy + r * 0.54), (cx + r * 0.26, cy + r * 0.54)],
                fill=fill, width=max(2, lw - 1))
    if crack <= 0.01:
        return
    n = 14
    for i in range(n):
        if crack < (i + 1) / n * 0.92:
            continue
        a0 = rng.uniform(0, 6.283)
        px, py = cx, cy
        ang = a0
        seg = 4 + int(rng.random() * 3)
        pts = [(px, py)]
        for k in range(seg):
            ang += rng.uniform(-0.75, 0.75)
            ln = r * rng.uniform(0.12, 0.24)
            nx = px + math.cos(ang) * ln
            ny = py + math.sin(ang) * ln * 1.1
            if ((nx - cx) / r) ** 2 + ((ny - cy) / (r * 1.18)) ** 2 > 0.93:
                break
            px, py = nx, ny
            pts.append((px, py))
        if len(pts) < 2:
            continue
        if burst > 0:
            dx = math.cos(a0) * r * 1.5 * burst
            dy = math.sin(a0) * r * 1.5 * burst
            pts = [(q[0] + dx, q[1] + dy) for q in pts]
        d_line.line(pts, fill=fill, width=max(1, lw - 1), joint="curve")


def threads(d, xs, y_top, y_bot, t, snapped=0.0, fill=255, seed=11,
            ends=None):
    """Puppet strings coming down out of the dark."""
    rng = np.random.default_rng(seed)
    pairs = ends if ends is not None else [(x, y_bot) for x in xs]
    for i, (x, y_bot) in enumerate(pairs):
        cut = rng.random()
        if snapped > cut:
            # snapped: the loose end curls and falls away
            k = clamp((snapped - cut) * 3.0)
            ytip = lerp(y_bot, y_top + (y_bot - y_top) * 0.35, smoothstep(k))
            drop = smoothstep(k) * 120
            rig = W * 0.5 + (x - W * 0.5) * 0.28
            pts = [(rig + math.sin(t * 1.1 + i) * 4, y_top),
                   (lerp(rig, x, 0.58) + math.sin(t * 1.3 + i) * 10,
                    lerp(y_top, ytip, 0.5)),
                   (x + math.sin(t * 1.7 + i) * 26 + drop * 0.25, ytip + drop * 0.2)]
        else:
            # converge toward a rig point above frame: a fan, not a barricade
            rig = W * 0.5 + (x - W * 0.5) * 0.28
            pts = [(rig + math.sin(t * 1.1 + i) * 3, y_top),
                   (lerp(rig, x, 0.58) + math.sin(t * 1.3 + i * 0.7) * 9,
                    (y_top + y_bot) / 2),
                   (x + math.sin(t * 1.6 + i * 1.3) * 5, y_bot)]
        d.line(pts, fill=fill, width=2, joint="curve")


def branch_curtain(d, side, reach, base_seed, fill=255, t=0.0, lw=5):
    """Branches reaching in from a frame edge - the forest closing in."""
    rng = np.random.default_rng(base_seed)
    for i in range(3):
        y = rng.uniform(0.05, 0.92) * H
        x = 0 if side < 0 else W
        ang = rng.uniform(-0.5, 0.5) + (0 if side > 0 else math.pi)
        ln = rng.uniform(0.22, 0.46) * W * reach

        def limb(px, py, a, L, w, lvl):
            a += math.sin(t * 0.8 + lvl + i) * 0.05
            ex = px + math.cos(a) * L * (-1 if side > 0 else 1)
            ey = py + math.sin(a) * L
            d.line([(px, py), (ex, ey)], fill=fill, width=max(1, int(w)))
            if lvl >= 4:
                return
            for k in range(2):
                limb(ex, ey, a + rng.uniform(0.25, 0.8) * (1 if k else -1),
                     L * rng.uniform(0.58, 0.74), w * 0.66, lvl + 1)

        limb(x, y, ang, ln * 0.4, lw, 1)


def spot_cone(d, apex_x, apex_y, spread, bottom_y, fill=255):
    d.polygon([(apex_x, apex_y),
               (apex_x - spread, bottom_y),
               (apex_x + spread, bottom_y)], fill=fill)


def dust(d, cx, half, y0, y1, t, n=70, seed=4, fill=255):
    """Motes swirling inside the light cone."""
    rng = np.random.default_rng(seed)
    for i in range(n):
        ph = rng.random() * 6.283
        yy = y0 + ((rng.random() * (y1 - y0)) + t * rng.uniform(6, 26)) % (y1 - y0)
        k = (yy - y0) / max(1.0, y1 - y0)
        xx = cx + math.sin(t * 0.5 + ph) * half * k * rng.uniform(0.2, 0.95)
        r = rng.uniform(0.9, 2.4)
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=int(fill * rng.uniform(0.3, 1.0)))


# --- density pass --------------------------------------------------------
# Everything below exists to fill the frame. The first cut of this intro read
# as empty because each shot carried one idea and nothing around it; these are
# the things that live at the edges of a real exterior.

def grass(d, x0, x1, base_y, h, fill=255, seed=0, n=90, wind=0.0, t=0.0):
    """Tufts along the ground. Cheap, and it stops the floor reading as a void."""
    r = np.random.default_rng(seed)
    for i in range(n):
        x = r.uniform(x0, x1)
        hh = h * r.uniform(0.45, 1.0)
        lean = math.sin(t * 1.3 + x * 0.01) * wind * hh * 0.28
        for k in range(r.integers(2, 5)):
            sp = r.uniform(-1, 1) * hh * 0.3
            d.line([(x, base_y), (x + sp + lean, base_y - hh * r.uniform(0.7, 1.0))],
                   fill=fill, width=max(1, int(hh * 0.07)))


def debris(d, x0, x1, base_y, fill=255, seed=0, n=26, scale=1.0):
    """Stones and junk scattered on the ground plane."""
    r = np.random.default_rng(seed)
    for i in range(n):
        x = r.uniform(x0, x1)
        y = base_y + r.uniform(-6, 26)
        w = r.uniform(3, 13) * scale
        h = w * r.uniform(0.3, 0.7)
        d.ellipse([x - w, y - h, x + w, y + h], fill=fill)


def puddle(d, cx, cy, w, h, fill=255):
    d.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=fill)


def street_lamp(d, x, base_y, h, fill=255, lw=None, arm=0.14, bend=1):
    """Lamp post with a curved head. Returns the lamp position for the light pass."""
    lw = lw or max(2, int(h * 0.028))
    d.line([(x, base_y), (x, base_y - h)], fill=fill, width=lw)
    hx = x + bend * h * arm
    pts = [(x, base_y - h),
           (x + bend * h * arm * 0.55, base_y - h - h * 0.055),
           (hx, base_y - h - h * 0.035)]
    d.line(pts, fill=fill, width=lw, joint="curve")
    d.ellipse([hx - h * 0.030, base_y - h - h * 0.030,
               hx + h * 0.030, base_y - h + h * 0.012], fill=fill)
    return (hx, base_y - h - h * 0.012)


def pylon(d, x, base_y, h, fill=255, lw=3):
    """Lattice transmission tower - reads as distance and industry."""
    hw = h * 0.20
    tw = h * 0.055
    d.line([(x - hw, base_y), (x - tw, base_y - h)], fill=fill, width=lw)
    d.line([(x + hw, base_y), (x + tw, base_y - h)], fill=fill, width=lw)
    steps = 9
    for i in range(steps + 1):
        u = i / steps
        y = base_y - h * u
        w = lerp(hw, tw, u)
        d.line([(x - w, y), (x + w, y)], fill=fill, width=max(1, lw - 1))
        if i < steps:
            u2 = (i + 1) / steps
            y2 = base_y - h * u2
            w2 = lerp(hw, tw, u2)
            d.line([(x - w, y), (x + w2, y2)], fill=fill, width=max(1, lw - 2))
            d.line([(x + w, y), (x - w2, y2)], fill=fill, width=max(1, lw - 2))
    for i, (ay, aw) in enumerate([(0.78, 0.30), (0.90, 0.24)]):
        y = base_y - h * ay
        d.line([(x - h * aw, y), (x + h * aw, y)], fill=fill, width=lw)
        for s in (-1, 1):
            d.line([(x + s * h * aw, y), (x + s * h * aw, y - h * 0.035)],
                   fill=fill, width=max(1, lw - 1))


def water_tower(d, x, base_y, h, fill=255, lw=3):
    tw = h * 0.30
    ty = base_y - h
    d.polygon([(x - tw, ty + h * 0.22), (x + tw, ty + h * 0.22),
               (x + tw * 0.82, ty), (x - tw * 0.82, ty)], fill=fill)
    d.polygon([(x - tw * 0.82, ty), (x + tw * 0.82, ty), (x, ty - h * 0.12)],
              fill=fill)
    for s in (-1, 1, 0):
        d.line([(x + s * tw * 0.72, ty + h * 0.22),
                (x + s * tw * 0.34, base_y)], fill=fill, width=lw)


def antenna(d, x, base_y, h, fill=255, lw=2, seed=0):
    r = np.random.default_rng(seed)
    d.line([(x, base_y), (x, base_y - h)], fill=fill, width=lw)
    for i in range(int(r.integers(2, 5))):
        y = base_y - h * r.uniform(0.35, 0.95)
        w = h * r.uniform(0.10, 0.26)
        d.line([(x - w, y), (x + w, y)], fill=fill, width=max(1, lw - 1))


def laundry_line(d, x0, y0, x1, y1, fill=255, seed=0, n=5):
    r = np.random.default_rng(seed)
    sag = abs(x1 - x0) * 0.07
    pts = [(lerp(x0, x1, i / 16), lerp(y0, y1, i / 16) + math.sin(i / 16 * math.pi) * sag)
           for i in range(17)]
    d.line(pts, fill=fill, width=2, joint="curve")
    for i in range(n):
        u = (i + 0.6) / (n + 0.2)
        x = lerp(x0, x1, u)
        y = lerp(y0, y1, u) + math.sin(u * math.pi) * sag
        w = r.uniform(10, 22)
        hh = r.uniform(20, 46)
        d.polygon([(x - w, y), (x + w, y), (x + w * 0.8, y + hh),
                   (x - w * 0.8, y + hh)], fill=fill)


def smoke_column(d, x, y, h, t, fill=255, seed=0, width=26):
    """A drifting column of smoke, drawn as overlapping soft blobs."""
    r = np.random.default_rng(seed)
    n = 16
    for i in range(n):
        u = (i / n + (t * 0.06) % 1.0) % 1.0
        yy = y - u * h
        ww = width * (0.35 + u * 1.9)
        drift = math.sin(u * 3.0 + t * 0.6 + seed) * h * 0.14
        a = int(fill * (1.0 - u) ** 1.2 * 0.85)
        if a <= 3:
            continue
        d.ellipse([x + drift - ww, yy - ww * 0.7, x + drift + ww, yy + ww * 0.7],
                  fill=a)


def bird_flock(d, cx, cy, spread, t, fill=255, n=9, seed=0, drift=1.0):
    r = np.random.default_rng(seed)
    for i in range(n):
        ph = r.random() * 6.283
        x = cx + r.uniform(-1, 1) * spread + t * 42 * drift
        y = cy + r.uniform(-1, 1) * spread * 0.32 + math.sin(t * 1.1 + ph) * 12
        s = r.uniform(7, 15)
        crow(d, x, y, s, t * 9 + ph, fill=fill)


def leaves(d, t, fill=255, n=26, seed=0, strength=1.0):
    """Debris blowing through frame."""
    if strength <= 0.02:
        return
    r = np.random.default_rng(seed)
    for i in range(n):
        ph = r.random() * 6.283
        sp = r.uniform(70, 230)
        x = (r.random() * W * 1.4 + t * sp) % (W * 1.4) - W * 0.2
        y = (r.random() * H + math.sin(t * 1.4 + ph) * 70 + t * sp * 0.22) % H
        s = r.uniform(3, 8) * strength
        d.polygon([(x, y - s), (x + s * 0.8, y), (x, y + s), (x - s * 0.8, y)],
                  fill=fill)


def fg_frame(d, t, fill=255, seed=0, side_only=False):
    """Big near-camera silhouettes that frame the shot. Blurred on composite,
    they read as depth of field and give the frame corners something to hold."""
    r = np.random.default_rng(seed)
    sway = math.sin(t * 0.55) * 14
    for s in (-1, 1):
        x0 = 0 if s < 0 else W
        for i in range(3):
            y = r.uniform(-0.1, 0.95) * H
            ln = r.uniform(0.10, 0.19) * W

            def limb(px, py, ang, L, w, lvl):
                ex = px + math.cos(ang) * L * (1 if s < 0 else -1) + sway * 0.3
                ey = py + math.sin(ang) * L
                d.line([(px, py), (ex, ey)], fill=fill, width=max(2, int(w)))
                if lvl >= 3:
                    return
                for k in range(2):
                    limb(ex, ey, ang + r.uniform(0.3, 0.9) * (1 if k else -1),
                         L * r.uniform(0.55, 0.72), w * 0.62, lvl + 1)

            limb(x0 + sway * s, y, r.uniform(-0.40, 0.40), ln * 0.45, 30, 1)
    if side_only:
        return
    for i in range(4):
        x = r.uniform(0, W)
        hh = r.uniform(0.08, 0.20) * H
        grass(d, x - 60, x + 60, H + 14, hh, fill=fill, seed=seed * 31 + i,
              n=14, wind=0.5, t=t)


def splashes(d, x0, x1, base_y, t, fill=255, n=40, seed=0, strength=1.0):
    """Rain hitting the ground. Small, but it ties the weather to the floor."""
    if strength <= 0.02:
        return
    r = np.random.default_rng(seed)
    for i in range(n):
        x = r.uniform(x0, x1)
        ph = r.random()
        k = ((t * 1.9 + ph) % 1.0)
        if k > 0.45:
            continue
        rr = (2 + k * 17) * strength
        y = base_y + r.uniform(-4, 30)
        a = int(fill * (1.0 - k / 0.45) * 0.8)
        if a <= 3:
            continue
        d.ellipse([x - rr, y - rr * 0.30, x + rr, y + rr * 0.30], outline=a, width=1)


# --- chapter two onward --------------------------------------------------
def crowd_sea(d, t, density, rows=8, seed=5, base_y=None, top=0.30,
              sway=1.0, fill=255, eye_d=None, eyes=0.0):
    """A crowd that fills the frame from horizon to camera.

    Ranks are drawn far-to-near so the near ones occlude, which is what makes
    a mass of silhouettes read as deep rather than as a pattern.
    """
    base_y = GROUND if base_y is None else base_y
    r = np.random.default_rng(seed)
    for ri in range(rows):
        u = ri / max(1, rows - 1)
        amt = clamp((density - u * 0.22) * 1.5)
        if amt <= 0.02:
            continue
        y = lerp(base_y - H * top, base_y + H * 0.26, u)
        h = lerp(44, 430, u ** 1.5)
        n = max(3, int(26 - ri * 2.6))
        for i in range(n):
            x = (i + 0.5) / n * W + r.uniform(-1, 1) * (W / n) * 0.45
            x += math.sin(t * 0.8 + ri * 1.3 + i) * 12 * sway * (0.3 + u)
            hh = h * r.uniform(0.86, 1.14) * (0.35 + 0.65 * amt)
            head = figure(d, x, y, hh, phase=r.random() * 6.3, walking=False,
                          fill=fill)
            if eye_d is not None and eyes > 0.02 and head and u < 0.8:
                k = clamp(eyes * 1.6 - u)
                if k > 0.05 and r.random() < 0.55:
                    eye(eye_d, head[0], head[1], head[2] * 0.40 * k, 1.0)


def looming_shadow(d, cx, base_y, h, t, fill=255, head_turn=0.0, lean=0.0):
    """An oversized silhouette standing behind the action."""
    lw = max(6, int(h * 0.055))
    hip = base_y - h * 0.44
    sho = base_y - h * 0.74
    headr = h * 0.105
    hcy = base_y - h * 0.87
    drift = math.sin(t * 0.5) * h * 0.012
    for s in (1, -1):
        d.line([(cx, hip), (cx + s * h * 0.07, hip + h * 0.23)], fill=fill, width=lw)
        d.line([(cx + s * h * 0.07, hip + h * 0.23), (cx + s * h * 0.11, base_y)],
               fill=fill, width=lw)
    d.line([(cx, hip), (cx + lean * h * 0.04, sho)], fill=fill, width=lw)
    for s in (1, -1):
        d.line([(cx + s * h * 0.015, sho + h * 0.02),
                (cx + s * h * 0.10, sho + h * 0.18)], fill=fill, width=lw)
        d.line([(cx + s * h * 0.10, sho + h * 0.18),
                (cx + s * h * 0.14, sho + h * 0.35)], fill=fill, width=lw)
    hx = cx + lean * h * 0.05 + head_turn * headr * 0.5
    d.ellipse([hx - headr, hcy + drift - headr, hx + headr, hcy + drift + headr],
              fill=fill)
    return (hx, hcy + drift, headr)


def hanging(d, obj_fn, x, y, t, drop, sway=1.0, thread_top=-30, fill=255):
    """Draw a prop suspended on a thread, optionally cut and falling."""
    dy = drop * H * 1.3
    xx = x + math.sin(t * 1.1 + x * 0.01) * 9 * sway + drop * 60
    yy = y + dy
    if drop < 0.02:
        d.line([(x + math.sin(t * 0.9 + x * 0.02) * 4, thread_top), (xx, yy)],
               fill=fill, width=2)
    obj_fn(xx, yy)


def bubbles(d, t, n=70, seed=0, fill=255, strength=1.0):
    if strength <= 0.02:
        return
    r = np.random.default_rng(seed)
    for i in range(n):
        ph = r.random() * 6.283
        sp = 40 + r.random() * 130
        x = r.random() * W + math.sin(t * 0.7 + ph) * 26
        y = (r.random() * H - t * sp) % (H + 120) - 60
        rr = (2 + r.random() * 9) * strength
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=int(fill * 0.9),
                  width=max(1, int(rr * 0.35)))


def water_shafts(d, t, n=7, seed=0, fill=255, strength=1.0):
    """Caustic light columns coming down through water."""
    if strength <= 0.02:
        return
    r = np.random.default_rng(seed)
    for i in range(n):
        x = (i + 0.5) / n * W + math.sin(t * 0.33 + i) * 70
        w_top = r.uniform(26, 70)
        w_bot = w_top * r.uniform(2.4, 4.6)
        a = int(fill * r.uniform(0.35, 1.0) * strength
                * (0.6 + 0.4 * math.sin(t * 0.6 + i * 1.7)))
        if a <= 3:
            continue
        d.polygon([(x - w_top, -40), (x + w_top, -40),
                   (x + w_bot, H + 40), (x - w_bot, H + 40)], fill=a)


def sinking_figures(d, t, n=7, seed=0, fill=255, strength=1.0):
    if strength <= 0.02:
        return
    r = np.random.default_rng(seed)
    for i in range(n):
        ph = r.random()
        sp = 24 + r.random() * 44
        y = ((ph * (H + 500)) + t * sp) % (H + 500) - 160
        x = r.random() * W + math.sin(t * 0.4 + i) * 38
        h = 90 + r.random() * 170
        figure(d, x, y, h, phase=0, walking=False, arms_up=0.85, fill=fill)
