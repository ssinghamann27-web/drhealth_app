"""The intro beat sheet.

v8 spent 0-52s on four ideas: a logo, a title, a figure walking in the dark,
and a spotlight. Forty of those seconds had no new information in them, which
is why it played long. This rebuild puts a new idea on every second bar - nine
scenes, each with its own payoff landing on a downbeat - and gives every prop
an eased life so nothing snaps in or out.

Tempo: 80.5 BPM, bar = 2.9814s, first downbeat at 0.520s.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import props
import world
from style import (BONE, DISPLAY, DISPLAY_LIGHT, H, MONO, RED, RED_HOT, W,
                   clamp, ease_in, ease_out, ease_out_back, font, lerp, ramp,
                   smootherstep, smoothstep, text_size, tracked, window)

BAR = 2.9814
PH = 0.520
BEAT = BAR / 4.0


def b(n):
    """Time of downbeat n."""
    return PH + n * BAR


# scene boundaries, all on downbeats
S_BRAND, S_TITLE = 0.0, b(2)          # 6.483
S_ROAD = b(4)                          # 12.446
S_TOWN = b(6)                          # 18.408
S_CROWD = b(8)                         # 24.371
S_MASK = b(10)                         # 30.334
S_HOUSE = b(12)                        # 36.297
S_THREAD = b(14)                       # 42.260
S_LIGHT = b(16)                        # 48.222
S_END = 52.5333                        # v8's hard cut into the first verse

GY = props.GROUND

_rain = world.Rain()
_embers = world.Embers()

_here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_here, "intro_text.json")) as fh:
    TEXT = json.load(fh)


def pulse_at(t, t0, decay=0.22):
    """A quick swell that decays - used to hit the frame on a downbeat."""
    if t < t0:
        return 0.0
    return math.exp(-(t - t0) / decay)


def beat_pulse(t, t0, t1, decay=0.16, every=BEAT):
    """Repeating pulse on the beat grid between t0 and t1."""
    if t < t0 or t > t1:
        return 0.0
    k = math.floor((t - PH) / every)
    return math.exp(-((t - PH) - k * every) / decay)


class Frame:
    """Mask set for one frame. Grouping by colour keeps composites down to ~4."""

    def __init__(self):
        self.bg, self.d_bg = props.new_mask()        # distant set (translucent)
        self.sil, self.d_sil = props.new_mask()      # near occluders (solid)
        self.red, self.d_red = props.new_mask()      # red line work
        self.lit, self.d_lit = props.new_mask()      # emissive (bone)
        self.warm, self.d_warm = props.new_mask()    # emissive (amber)
        self.txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.d_txt = ImageDraw.Draw(self.txt)
        self.flash = 0.0
        self.cool = 0.0
        self.zoom = 1.0
        self.glow_y = 0.70
        self.glow_x = 0.50
        self.intensity = 1.0
        self.pulse = 0.0
        self.rain = 0.0
        self.wind = 0.0
        self.embers = 0.6
        self.haze = 0.0


# --- shared furniture ----------------------------------------------------
def chapter_plate(f, t):
    """Top-right chapter label and the top-left tick, as established in v8."""
    a = window(t, S_ROAD + 2.6, S_ROAD + 3.5, S_END + 1, S_END + 2)
    if a <= 0.01:
        return
    fnt = font(DISPLAY_LIGHT, 21)
    label = TEXT["chapter"]
    col = (222, 214, 212, int(190 * a))
    # label slides in from the right as it fades
    dx = (1 - a) * 26
    wdt, _ = text_size(fnt, label, 5)
    tracked(f.d_txt, (W - 72 - wdt + dx, 46), label, fnt, col, 5)
    # red tick, top-left, draws itself on
    k = ramp(t, S_ROAD + 2.7, S_ROAD + 3.6)
    f.d_txt.rectangle([72, 46, 72 + 150 * k, 49], fill=(RED[0], RED[1], RED[2],
                                                        int(230 * a)))


def chapter_card(f, t):
    """A full chapter title where the story actually starts.

    v8 announced ADHYAY 1 only as a 20px label in the corner. Stating it
    properly tells the audience this is a story in acts, and gives them
    somewhere to stand before the shayari begins.
    """
    t0 = S_ROAD
    a = window(t, t0 + 0.15, t0 + 0.85, t0 + 2.35, t0 + 3.15)
    if a <= 0.01:
        return
    rise = smootherstep(ramp(t, t0 + 0.15, t0 + 0.95))
    dy = (1 - rise) * 18
    cy = H * 0.40

    num = TEXT.get("chapter_number", "")
    name = TEXT.get("chapter_name", "")
    gloss = TEXT.get("chapter_gloss", "")

    if num:
        nf = font(DISPLAY_LIGHT, 27)
        tracked(f.d_txt, (W / 2, cy - 54 + dy), num, nf,
                (RED_HOT[0], RED_HOT[1], RED_HOT[2], int(236 * a)), 13,
                anchor_center=True)
    if name:
        bf = font(DISPLAY, 92)
        wdt, _ = text_size(bf, name, 7)
        f.d_txt.text((W / 2 - wdt / 2 + 3, cy + dy + 4), name, font=bf,
                     fill=(0, 0, 0, int(150 * a)))
        tracked(f.d_txt, (W / 2, cy + dy), name, bf,
                (238, 233, 230, int(246 * a)), 7, anchor_center=True)
        # rule that opens outward from the centre
        sw = smootherstep(ramp(t, t0 + 0.45, t0 + 1.25))
        uw = wdt * 0.5 * sw
        uy = cy + dy + 104
        f.d_txt.rectangle([W / 2 - uw / 2, uy, W / 2 + uw / 2, uy + 3],
                          fill=(RED[0], RED[1], RED[2], int(230 * a)))
    if gloss:
        gf = font(DISPLAY_LIGHT, 21)
        tracked(f.d_txt, (W / 2, cy + dy + 122), gloss, gf,
                (206, 198, 196, int(205 * a)), 9, anchor_center=True)


def shayari_credit(f, t):
    a = window(t, 16.2, 17.3, 22.0, 23.4)
    if a <= 0.01:
        return
    small = font(DISPLAY_LIGHT, 15)
    big = font(DISPLAY_LIGHT, 19)
    tracked(f.d_txt, (72, H - 112), "SHAYARI", small,
            (RED_HOT[0], RED_HOT[1], RED_HOT[2], int(220 * a)), 4)
    tracked(f.d_txt, (72, H - 90), TEXT["shayari_credit"], big,
            (226, 219, 217, int(205 * a)), 4)


def shayari_lines(f, t):
    """The recited couplet, set like the verse captions later in the film.

    Lines live in intro_text.json. Leave them empty and the slot simply does
    not draw, so the cut still plays clean.
    """
    for slot in TEXT.get("shayari", []):
        lines = [l for l in slot.get("lines", []) if l.strip()]
        if not lines:
            continue
        t0, t1 = slot["t"], slot["t"] + slot.get("hold", 5.2)
        a = window(t, t0, t0 + 0.55, t1 - 0.5, t1)
        if a <= 0.01:
            continue
        fnt = font(DISPLAY, 58)
        hot = set(w.upper() for w in slot.get("accent", []))
        y = H * 0.50 - len(lines) * 42
        rise = (1 - smootherstep(ramp(t, t0, t0 + 0.55))) * 22
        for ln in lines:
            words = ln.upper().split()
            widths = [f.d_txt.textlength(w + " ", font=fnt) for w in words]
            x = W / 2 - sum(widths) / 2
            for wd, ww in zip(words, widths):
                key = wd.strip(",.!?-")
                col = RED_HOT if key in hot else (238, 233, 230)
                f.d_txt.text((x, y + rise), wd, font=fnt,
                             fill=(col[0], col[1], col[2], int(236 * a)))
                x += ww
            y += 76


def walker_x(t):
    """The protagonist's path across the whole intro - one continuous walk."""
    if t < S_ROAD:
        return W * 0.16
    k = (t - S_ROAD) / (S_END - S_ROAD)
    # he drifts right, pauses at the house, then commits to the light
    return W * (0.16 + 0.34 * smoothstep(clamp(k * 1.25)))


def walker(f, t, h=176, depth=1.0):
    x = walker_x(t)
    ph = t * 5.4
    props.figure(f.d_sil, x, GY, h, phase=ph)
    return x


# --- S0  BRAND  0 -> 6.48 ------------------------------------------------
def s_brand(f, t):
    f.intensity = 0.30 + 0.70 * ramp(t, 0.30, 2.2)
    f.glow_y = 0.67
    f.embers = 0.35 + 0.65 * ramp(t, 0.2, 2.5)
    f.pulse = 0.55 * pulse_at(t, b(0), 0.30) + 0.22 * pulse_at(t, b(1), 0.25)

    a = window(t, b(0), b(0) + 0.42, b(1) + 1.55, b(2) - 0.08)
    if a <= 0.01:
        return
    # wordmark settles in with a touch of overshoot, then pushes in slowly
    k = ramp(t, b(0), b(0) + 0.55)
    sc = lerp(1.10, 1.0, ease_out_back(k, 0.9)) * lerp(1.0, 1.045,
                                                       ramp(t, b(1), b(2)))
    size = max(10, int(132 * sc))
    fnt = font(DISPLAY, size)
    wdt, _ = text_size(fnt, "AMAN", int(14 * sc))
    x = W / 2 - wdt / 2
    y = H * 0.40 - size * 0.5

    f.d_txt.text((x + 4, y + 5), "AMAN", font=fnt, fill=(0, 0, 0, int(150 * a)))
    tracked(f.d_txt, (x, y), "AMAN", fnt, (238, 233, 230, int(248 * a)), int(14 * sc))

    # the rule sweeps out from under the mark
    sweep = smootherstep(ramp(t, b(0) + 0.30, b(0) + 1.05))
    if sweep > 0.01:
        uw = wdt * sweep
        uy = y + size * 1.00
        f.d_txt.rectangle([W / 2 - uw / 2, uy, W / 2 + uw / 2, uy + 4],
                          fill=(RED[0], RED[1], RED[2], int(240 * a)))

    sa = window(t, b(0) + 0.95, b(0) + 1.7, b(1) + 1.55, b(2) - 0.08)
    if sa > 0.01:
        sf = font(DISPLAY_LIGHT, 23)
        tracked(f.d_txt, (W / 2, y + size * 1.18), TEXT["production"], sf,
                (214, 206, 204, int(215 * sa)), 11, anchor_center=True)
    f.flash = 0.30 * pulse_at(t, b(0), 0.10)


# --- S1  TITLE  6.48 -> 12.45 -------------------------------------------
def s_title(f, t):
    """The title lands on a world, not on black - we are inside the story by 7s."""
    k = ramp(t, S_TITLE, S_TITLE + 1.4)
    f.intensity = 1.0
    f.glow_y = 0.69
    f.embers = 0.85
    f.haze = 0.55 * k
    f.pulse = 0.60 * pulse_at(t, S_TITLE, 0.28) + 0.25 * pulse_at(t, b(3), 0.22)
    f.flash = 0.38 * pulse_at(t, S_TITLE, 0.09)
    f.zoom = lerp(1.0, 1.055, smoothstep(ramp(t, S_TITLE, S_ROAD)))

    rv = window(t, S_TITLE - 0.1, S_TITLE + 1.1, S_END, S_END + 1)
    if rv > 0.01:
        # three ridge planes - the depth v8's single gradient never had
        props.ridge(f.d_bg, GY - 150, 210, 31, span=(-0.35, 1.35), rough=0.8,
                    floor=GY + 54)
        props.ridge(f.d_bg, GY - 74, 132, 77, span=(-0.25, 1.25), rough=1.1,
                    floor=GY + 54)
        # blood moon low on the ridge
        mr = 36
        mx, my = W * 0.715, GY - 348
        f.d_warm.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=115)
        props.dead_tree(f.d_bg, W * 0.845, GY - 46, 250, seed=14, t=t, wind=0.5)
        props.ridge(f.d_bg, GY + 30, 46, 5, span=(-0.2, 1.2), rough=1.3,
                    floor=GY + 96)

    a = window(t, S_TITLE, S_TITLE + 0.40, b(3) + 1.35, S_ROAD - 0.06)
    if a > 0.01:
        ks = ramp(t, S_TITLE, S_TITLE + 0.5)
        sc = lerp(1.11, 1.0, ease_out(ks, 3.2))
        size = max(10, int(152 * sc))
        fnt = font(DISPLAY, size)
        title = TEXT["title"]
        trk = int(3 * sc)
        wdt, _ = text_size(fnt, title, trk)
        x = W / 2 - wdt / 2
        # lifts away at the end instead of cutting
        y = H * 0.405 - size * 0.5 - 46 * ease_in(ramp(t, b(3) + 1.0, S_ROAD), 2.2)

        off = (1 - ks) * 11
        if off > 0.4:  # a hint of mis-registration that settles on the beat
            tracked(f.d_txt, (x - off, y), title, fnt,
                    (RED_HOT[0], RED_HOT[1], RED_HOT[2], int(150 * a)), trk)
        f.d_txt.text((x + 5, y + 6), title, font=fnt, fill=(0, 0, 0, int(165 * a)))
        tracked(f.d_txt, (x, y), title, fnt, (240, 236, 234, int(250 * a)), trk)

        sw = smootherstep(ramp(t, S_TITLE + 0.25, S_TITLE + 1.05))
        uw = wdt * 0.46 * sw
        uy = y + size * 1.00
        f.d_txt.rectangle([W / 2 - uw / 2, uy, W / 2 + uw / 2, uy + 5],
                          fill=(RED[0], RED[1], RED[2], int(245 * a)))

        sa = window(t, b(3) - 0.45, b(3) + 0.35, b(3) + 1.35, S_ROAD - 0.06)
        if sa > 0.01:
            sf = font(DISPLAY_LIGHT, 25)
            tracked(f.d_txt, (W / 2, uy + 26), TEXT["subtitle"], sf,
                    (219, 211, 209, int(225 * sa)), 10, anchor_center=True)


# --- S2  THE ROAD  12.45 -> 18.41 ---------------------------------------
def s_road(f, t):
    """Somewhere to walk. v8 put the figure on an empty gradient; here there is
    a road under him, poles going past and weather coming down."""
    k = ramp(t, S_ROAD, S_ROAD + 1.3)
    f.intensity = 1.0
    f.glow_y = 0.69
    f.haze = 0.62
    f.rain = 0.18 + 0.82 * ramp(t, S_ROAD + 0.2, S_ROAD + 2.6)
    f.wind = 0.26
    f.embers = 0.45
    f.pulse = 0.34 * pulse_at(t, S_ROAD, 0.26)

    props.ridge(f.d_bg, GY - 150, 210, 31, span=(-0.35, 1.35), rough=0.8,
                floor=GY + 54)
    props.ridge(f.d_bg, GY - 74, 132, 77, span=(-0.25, 1.25), rough=1.1,
                floor=GY + 54)

    vy = GY - 6
    scroll = (t * 0.30) % 1.0
    rs, drs = props.new_mask()
    props.road(f.d_red, vy, W * 0.58, 540, fill=int(58 * k), lanes=9,
               scroll=scroll, surface=drs)
    f.red.paste(rs.point(lambda v: int(v * 0.075)), (0, 0), rs)

    # poles march past: the clearest read of forward motion in the whole intro
    span = 520.0
    off = (t * 72.0) % span
    prev = None
    pm, pm_d = props.new_mask()
    for i in range(-1, 5):
        px = W * 1.12 - i * span + off
        depth = 1.0
        ph = 240 - abs(px - W * 0.6) * 0.055
        ph = max(90, ph)
        if -220 < px < W + 220:
            props.pole(pm_d, px, GY - 26, ph, arms=2)
            if prev is not None:
                props.wire(pm_d, prev[0], prev[1] - prev[2] * 0.84, px,
                           GY - 26 - ph * 0.84, 34, lw=2, t=t, sway=3)
        prev = (px, GY - 26, ph)
    f.sil.paste(pm, (0, 0), pm)
    f.red.paste(pm.point(lambda v: int(v * 0.30)), (0, 0), pm)

    props.fence(f.d_sil, -40, W + 40, GY + 40, 34, lw=3, step=72)
    walker(f, t)

    # lightning on the bar: one frame of the whole landscape at full contrast
    lt = b(5)
    if lt <= t < lt + 0.16:
        f.flash = 0.80 * math.exp(-(t - lt) / 0.055)
        f.intensity *= 1.5
    # a crow lifts off the wire as it strikes
    ct = ramp(t, lt, lt + 2.4)
    if 0.01 < ct < 0.995:
        cx = lerp(W * 0.42, W * 1.05, ct)
        cy = lerp(GY - 230, GY - 430, ease_out(ct, 2.0))
        props.crow(f.d_sil, cx, cy, 26, t * 13.0)


# --- S3  THE TOWN  18.41 -> 24.37 ---------------------------------------
def s_town(f, t):
    """A town that lights up, then closes itself to him - told with windows."""
    k = smootherstep(ramp(t, S_TOWN, S_TOWN + 1.5))
    f.intensity = 1.0
    f.glow_y = 0.70
    f.haze = 0.70
    f.rain = 0.62 * (1 - 0.5 * ramp(t, b(7), S_CROWD))
    f.wind = 0.34
    f.embers = 0.6
    f.pulse = 0.30 * pulse_at(t, S_TOWN, 0.26) + 0.26 * pulse_at(t, b(7), 0.3)

    props.ridge(f.d_bg, GY - 158, 218, 31, span=(-0.35, 1.35), rough=0.8,
                floor=GY + 54)

    # the skyline slides in from the right as the camera drifts
    slide = lerp(W * 0.55, 0.0, k) - (t - S_TOWN) * 11.0
    sk = Image.new("L", (W, H), 0)
    dsk = ImageDraw.Draw(sk)
    wins = props.skyline(dsk, GY - 18, 120 + slide, W * 1.35 + slide, 150, 380,
                         seed=4, n=13, lean=0.22)
    f.bg.paste(sk, (0, 0), sk)

    # windows: lit, then going out left to right after the bar
    douse = ramp(t, b(7), b(7) + 2.1)
    for (wx, wy, ww, wh, r) in wins:
        if wx < -40 or wx > W + 40:
            continue
        u = clamp(wx / W)
        on = 1.0 - clamp((douse * 1.45 - u) * 2.4)
        flick = 0.78 + 0.22 * math.sin(t * (2.0 + r * 5) + r * 9)
        amt = on * flick * k
        if amt <= 0.04:
            continue
        f.d_warm.rectangle([wx, wy, wx + ww, wy + wh], fill=int(120 * amt))

    props.fence(f.d_sil, -40, W + 40, GY + 44, 40, lw=3, step=64)
    props.dead_tree(f.d_sil, W * 0.12 + slide * 0.3, GY + 10, 250, seed=22,
                    t=t, wind=0.8)
    walker(f, t)


# --- S4  THE CROWD  24.37 -> 30.33 --------------------------------------
_CROWD = None


def _crowd_layout():
    """Three ranks, clustered toward the middle of frame rather than spread in
    an even line - an even line reads as a fence, a cluster reads as a crowd."""
    global _CROWD
    if _CROWD is None:
        r = np.random.default_rng(99)
        rows = []
        for (yy, hh, n, spread) in [(GY - 24, 126, 9, 0.38),
                                    (GY + 24, 168, 7, 0.34),
                                    (GY + 84, 214, 5, 0.26)]:
            xs = W * 0.5 + r.normal(0, W * spread, n)
            rows.append([(float(x), yy, hh * r.uniform(0.88, 1.12),
                          float(r.random())) for x in xs])
        _CROWD = rows
    return _CROWD


def crowd(f, t, amount, turn_to=None, eyes=0.0, arms_up=0.0, scale=1.0):
    """The onlookers. They fade up row by row and turn their heads to track him,
    so the shot keeps changing without anything cutting."""
    if amount <= 0.01:
        return
    for ri, row in enumerate(_crowd_layout()):
        ra = clamp((amount - ri * 0.16) * 1.7)
        if ra <= 0.02:
            continue
        for (x, y, h, seed) in row:
            hh = h * scale * (0.3 + 0.7 * ra)
            ht = 0.0
            if turn_to is not None:
                ht = clamp((turn_to - x) / (W * 0.45), -1, 1)
            e = clamp((eyes * 1.5) - (x / W))
            head = props.figure(f.d_sil, x, y, hh, phase=seed * 6.3,
                                walking=False, head_turn=ht, arms_up=arms_up)
            if e > 0.03 and head:
                props.eye(f.d_red, head[0], head[1], head[2] * 0.42 * e, 1.0)


def s_crowd(f, t):
    f.intensity = 1.0
    f.glow_y = 0.71
    f.haze = 0.72
    f.rain = 0.22
    f.wind = 0.2
    f.embers = 0.5
    f.zoom = lerp(1.0, 1.07, smoothstep(ramp(t, S_CROWD, S_MASK)))
    f.pulse = 0.30 * pulse_at(t, S_CROWD, 0.26) + 0.5 * pulse_at(t, b(9), 0.3)

    props.ridge(f.d_bg, GY - 158, 218, 31, span=(-0.35, 1.35), rough=0.8,
                floor=GY + 54)
    props.skyline(f.d_bg, GY - 10, -80, W + 80, 110, 280, seed=4, n=13, lean=0.18)

    amount = ramp(t, S_CROWD, S_CROWD + 2.0) + 0.45 * ramp(t, b(9), b(9) + 1.4)
    wx = walker_x(t)
    # before the bar they watch him; on it, every head turns to camera at once
    snap = smootherstep(ramp(t, b(9), b(9) + 0.45))
    crowd(f, t, amount, turn_to=lerp(wx, W / 2, snap),
          eyes=ramp(t, b(9), b(9) + 1.9))
    walker(f, t)
    f.flash = 0.42 * pulse_at(t, b(9), 0.07)


# --- S5  THE MASK  30.33 -> 36.30 ---------------------------------------
def s_mask(f, t):
    """The one real image v8 had - the red eye - now built up to and paid off."""
    f.intensity = 1.0
    f.glow_y = 0.60
    f.haze = 0.5
    f.rain = 0.12
    f.embers = 0.9
    f.pulse = 0.34 * pulse_at(t, S_MASK, 0.26)
    f.zoom = lerp(1.07, 1.0, smoothstep(ramp(t, S_MASK, S_MASK + 1.6)))

    crowd(f, t, 1.0 - 0.3 * ramp(t, b(11), S_HOUSE), scale=0.75)

    rise = smootherstep(ramp(t, S_MASK, S_MASK + 1.5))
    burst = ease_out(ramp(t, b(11), b(11) + 1.5), 2.0)
    a_mask = window(t, S_MASK, S_MASK + 1.2, b(11) + 0.9, S_HOUSE - 0.2)
    cx, cy = W * 0.5, lerp(H * 0.80, H * 0.44, rise)
    r = lerp(120, 304, rise) * (1 + 0.10 * burst)

    if a_mask > 0.02:
        # cracks advance one step per beat, so the fracture is on the music
        crack = clamp((t - (S_MASK + 1.2)) / (b(11) - (S_MASK + 1.2)))
        solid, d_solid = props.new_mask()
        lines, d_lines = props.new_mask()
        props.mask_face(d_lines, cx, cy, r, crack=crack, lw=8, burst=burst,
                        d_fill=d_solid)
        body = a_mask * (1.0 - smootherstep(clamp(burst * 1.35)))
        f.sil.paste(solid.point(lambda v: int(v * body)), (0, 0), solid)
        f.red.paste(lines.point(lambda v: int(v * 0.62 * a_mask)), (0, 0), lines)

    # the eye behind it, burning brighter as the mask fails
    ea = window(t, S_MASK + 1.9, b(11) - 0.5, S_HOUSE - 1.0, S_HOUSE + 0.3)
    if ea > 0.02:
        er = r * (0.19 + 0.10 * burst)
        glow = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 3.1))
        f.d_red.ellipse([cx - er, cy - er * 0.72, cx + er, cy + er * 0.72],
                        fill=int(248 * ea))
        f.d_lit.ellipse([cx - er * 0.34, cy - er * 0.25, cx + er * 0.34,
                         cy + er * 0.25], fill=int(150 * ea * glow))
    f.flash = 0.62 * pulse_at(t, b(11), 0.085)


# --- S6  THE HOUSE  36.30 -> 42.26 --------------------------------------
def s_house(f, t):
    """The door that closes. v8 flashed a house outline for three seconds and
    moved on; here it is a scene with a beginning and an end."""
    f.intensity = 0.95
    f.glow_y = 0.71
    f.haze = 0.68
    f.rain = 0.30 + 0.45 * ramp(t, b(13), b(13) + 1.6)
    f.wind = 0.30
    f.embers = 0.55
    f.pulse = 0.30 * pulse_at(t, S_HOUSE, 0.26) + 0.28 * pulse_at(t, b(13), 0.3)

    props.ridge(f.d_bg, GY - 152, 212, 31, span=(-0.35, 1.35), rough=0.8,
                floor=GY + 54)
    props.ridge(f.d_bg, GY - 70, 124, 77, span=(-0.25, 1.25), rough=1.1,
                floor=GY + 54)

    rise = smootherstep(ramp(t, S_HOUSE, S_HOUSE + 1.7))
    hy = GY + 26 + (1 - rise) * 200
    hx = W * 0.665
    hw = 320

    shut = smootherstep(ramp(t, b(13), b(13) + 0.75))
    hm, dhm = props.new_mask()
    door_rect = props.house(dhm, hx, hy, hw, lw=5)
    f.sil.paste(hm, (0, 0), hm)
    f.red.paste(hm.point(lambda v: int(v * 0.46)), (0, 0), hm)
    props.fence(f.d_sil, hx - hw * 1.5, hx + hw * 1.1, hy + 20, 42, lw=3, step=58)
    props.dead_tree(f.d_sil, hx + hw * 0.80, hy + 14, 300, seed=31, t=t, wind=0.7)
    # mailbox
    f.d_sil.line([(hx - hw * 0.95, hy + 20), (hx - hw * 0.95, hy - 46)],
                 fill=255, width=4)
    f.d_sil.rectangle([hx - hw * 0.95 - 17, hy - 70, hx - hw * 0.95 + 17, hy - 44],
                      fill=255)

    # warm light spilling out of the doorway, and someone standing in it
    lit = rise * (1 - shut)
    if lit > 0.02:
        x0, y0, x1, y1 = door_rect
        f.d_warm.rectangle([x0 + 3, y0 + 3, x1 - 3, y1], fill=int(142 * lit))
        # the light falls onto the ground in front of the door
        sp = (x1 - x0) * 1.9
        f.d_warm.polygon([(x0 + 3, y1), (x1 - 3, y1),
                          (hx + sp * 0.5, y1 + 62), (hx - sp * 0.5, y1 + 62)],
                         fill=int(46 * lit))
        props.figure(f.d_sil, (x0 + x1) / 2, y1 - 2, (y1 - y0) * 0.84,
                     walking=False, lean=0.1)

    walker(f, t)
    f.haze += 0.1 * shut


# --- S7  THE THREADS  42.26 -> 48.22 ------------------------------------
def s_thread(f, t):
    """Strings come down out of the dark. Everyone is on one except him -
    and then they snap."""
    f.intensity = 0.92
    f.glow_y = 0.67
    f.haze = 0.60
    f.rain = 0.28
    f.wind = 0.42
    f.embers = 0.75
    f.pulse = 0.30 * pulse_at(t, S_THREAD, 0.26) + 0.40 * pulse_at(t, b(15), 0.3)

    reach = smootherstep(ramp(t, S_THREAD, S_THREAD + 2.2))
    reach *= 1.0 - 0.25 * ramp(t, b(15) + 0.4, S_LIGHT)
    if reach > 0.02:
        props.branch_curtain(f.d_red, -1, reach, 41, t=t, lw=7, fill=82)
        props.branch_curtain(f.d_red, +1, reach, 67, t=t, lw=7, fill=82)
        props.branch_curtain(f.d_sil, -1, reach * 0.92, 41, t=t, lw=9)
        props.branch_curtain(f.d_sil, +1, reach * 0.92, 67, t=t, lw=9)

    snapped = ease_out(ramp(t, b(15), b(15) + 1.9), 1.6)
    hooked = ramp(t, S_THREAD + 0.6, S_THREAD + 2.4)
    crowd(f, t, 1.0, scale=0.8, arms_up=hooked * (1 - snapped) * 0.85)

    # anchor each string to a raised hand rather than letting it hang in space
    ends = []
    for row in _crowd_layout()[:2]:
        for (x, y, hgt, seed) in row:
            hh = hgt * 0.8
            sho = y - hh * 0.74
            sgn = 1 if seed > 0.5 else -1
            ends.append((x + sgn * hh * 0.28,
                         lerp(sho + hh * 0.33, sho - hh * 0.19, hooked) - 6))
    props.threads(f.d_red, [], -20, GY - 118, t, snapped=snapped, fill=86,
                  ends=ends)
    walker(f, t)
    f.flash = 0.34 * pulse_at(t, b(15), 0.08)


# --- S8  THE LIGHT  48.22 -> 52.53 --------------------------------------
def s_light(f, t):
    """Into the light, watched. Hands off to v8's first verse on a white frame."""
    k = smootherstep(ramp(t, S_LIGHT, S_LIGHT + 1.1))
    f.intensity = lerp(1.0, 0.72, k)
    f.glow_y = 0.69
    f.haze = 0.45
    f.rain = 0.40
    f.wind = 0.22
    f.embers = 0.35
    f.cool = 0.58 * k
    f.pulse = 0.5 * pulse_at(t, S_LIGHT, 0.3)

    tighten = smootherstep(ramp(t, b(17), S_END))
    spread = lerp(300, 196, tighten) * k
    apex_x = W * 0.5
    if spread > 4:
        cone, dc = props.new_mask()
        props.spot_cone(dc, apex_x, -70, spread, GY + 40, fill=96)
        props.dust(dc, apex_x, spread, -60, GY + 30, t, n=80, fill=190)
        f.lit.paste(cone, (0, 0), cone)

    # pool on the ground
    if k > 0.02:
        f.d_lit.ellipse([apex_x - spread * 1.18, GY - 26,
                         apex_x + spread * 1.18, GY + 34], fill=int(120 * k))

    # he walks in, and his shadow runs back out of the light
    wx = lerp(walker_x(S_LIGHT), apex_x, smootherstep(ramp(t, S_LIGHT, b(17))))
    sh, dsh = props.new_mask()
    dsh.polygon([(wx - 24, GY), (wx + 24, GY),
                 (wx + 150, GY + 128), (wx - 150, GY + 128)], fill=170)
    f.sil.paste(sh, (0, 0), sh)
    props.figure(f.d_sil, wx, GY, 150, phase=t * 5.4,
                 walking=t < b(17) + 0.4)

    # the crowd rings the light, closing in on the last bar
    close = smootherstep(ramp(t, b(17), S_END))
    crowd(f, t, 1.0, scale=lerp(0.85, 1.12, close))

    f.flash = 0.45 * pulse_at(t, S_LIGHT, 0.09)
    # whiteout that meets v8's existing cut frame-for-frame
    if t > S_END - 0.24:
        f.flash = max(f.flash, ease_in(ramp(t, S_END - 0.24, S_END), 2.4) * 1.5)


# --- assembly ------------------------------------------------------------
SCENES = [
    (S_BRAND, S_TITLE, s_brand),
    (S_TITLE, S_ROAD, s_title),
    (S_ROAD, S_TOWN, s_road),
    (S_TOWN, S_CROWD, s_town),
    (S_CROWD, S_MASK, s_crowd),
    (S_MASK, S_HOUSE, s_mask),
    (S_HOUSE, S_THREAD, s_house),
    (S_THREAD, S_LIGHT, s_thread),
    (S_LIGHT, S_END + 0.2, s_light),
]


def build(t):
    f = Frame()
    for t0, t1, fn in SCENES:
        if t0 <= t < t1:
            fn(f, t)
            break
    chapter_plate(f, t)
    chapter_card(f, t)
    shayari_credit(f, t)
    shayari_lines(f, t)
    return f


def render(t):
    """Compose one frame. Returns HxWx3 uint8 RGB."""
    f = build(t)
    img = world.background(t, glow_y=f.glow_y, glow_x=f.glow_x,
                           intensity=f.intensity, pulse=f.pulse, cool=f.cool)

    # the distant set is dark but translucent, so near silhouettes still read
    img = props.paint(img, f.bg, (6, 2, 3), 0.76, 2.0)

    if f.haze > 0.01:
        hz = world.haze_band(t, 0.76, 1.02, f.haze)
        if hz is not None:
            arr = np.asarray(hz, dtype=np.float32)
            a = arr[:, :, 3:4] / 255.0
            img += (arr[:, :, :3] - img) * a * 0.55

    # emissive passes sit behind the near occluders
    img = props.emit(img, f.warm, (255, 146, 68), gain=0.30, blur=6.0)
    img = props.emit(img, f.warm, (255, 198, 134), gain=0.26, blur=1.0)
    img = props.emit(img, f.lit, (226, 222, 230), gain=1.05, blur=3.0)

    img = props.paint(img, f.sil, (0, 0, 0), 1.0, 0.75)
    img = props.emit(img, f.red, RED_HOT, gain=1.0, blur=1.4)

    rn = _rain.draw(t, f.rain, f.wind)
    if rn is not None:
        arr = np.asarray(rn, dtype=np.float32)
        img += arr[:, :, :3] * (arr[:, :, 3:4] / 255.0) * 0.55
    em = _embers.draw(t, f.embers)
    if em is not None:
        arr = np.asarray(em, dtype=np.float32)
        img += arr[:, :, :3] * (arr[:, :, 3:4] / 255.0) * 0.8

    img = world.apply_grain(img, t, 6.5)
    img = world.apply_vignette(img, 1.0)

    txt = np.asarray(f.txt, dtype=np.float32)
    ta = txt[:, :, 3:4] / 255.0
    if ta.max() > 0.003:
        img += (txt[:, :, :3] - img) * ta

    if f.flash > 0.004:
        img += 255.0 * min(1.0, f.flash)

    img = world.letterbox(img, t)

    if f.zoom > 1.001:
        z = f.zoom
        cw, ch = int(W / z), int(H / z)
        x0, y0 = (W - cw) // 2, (H - ch) // 2
        pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        pil = pil.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BICUBIC)
        return np.asarray(pil)

    return np.clip(img, 0, 255).astype(np.uint8)
