"""The intro beat sheet.

Nine scenes across 0 -> 52.53s, one new idea every two bars, each payoff
landing on a downbeat. Tempo 80.5 BPM, bar 2.9814s, first downbeat 0.520s.

Three things carry the production value: depth (a far set, a mid set, an
action plane and a defocused foreground), light that behaves (reflection,
bloom, halation, shafts) and a type system with real contrast in it.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import post
import props
import world
from style import (BONE, DISPLAY, DISPLAY_LIGHT, EDITORIAL, H, LABEL,
                   LABEL_MED, MONO, RED, RED_HOT, VERSE, VERSE_UP, W, clamp,
                   ease_in, ease_out, ease_out_back, font, lerp, ramp,
                   smootherstep, smoothstep, text_size, tracked, window)

BAR = 2.9814
PH = 0.520
BEAT = BAR / 4.0


def b(n):
    return PH + n * BAR


S_BRAND, S_TITLE = 0.0, b(2)           # 6.483
S_ROAD = b(4)                           # 12.446
S_TOWN = b(6)                           # 18.408
S_CROWD = b(8)                          # 24.371
S_MASK = b(10)                          # 30.334
S_HOUSE = b(12)                         # 36.297
S_THREAD = b(14)                        # 42.260
S_LIGHT = b(16)                         # 48.222
S_END = 52.5333                         # hand-off to the original cut
S_BHEED = b(18)      # 54.19  the crowd
S_PARCH = b(22)      # 66.11  the shadow
S_DHAAGE = b(26)     # 78.04  breaking threads
S_PAANI = b(30)      # 89.96  deep water
S_SACH = b(34)       # 101.89 the lonely truth
S_OUTRO = b(38)      # 113.81
S_FIN = 138.667

GY = props.GROUND

_rain = world.Rain(n=760)
_embers = world.Embers(n=120)
_bokeh = world.Bokeh()
_wisps = world.Wisps()

_here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_here, "intro_text.json")) as fh:
    TEXT = json.load(fh)


def _edge_mask():
    """1 at the frame edges, 0 across the middle - keeps the defocused
    foreground acting as a vignette of branches rather than a smear."""
    x = np.linspace(0, 1, W, dtype=np.float32)
    ex = np.clip(1.0 - np.minimum(x, 1 - x) / 0.22, 0, 1) ** 1.3
    y = np.linspace(0, 1, H, dtype=np.float32)
    ey = np.clip(1.0 - np.minimum(y, 1 - y) / 0.16, 0, 1) ** 1.3
    m = np.maximum(ex[None, :], ey[:, None])
    return Image.fromarray((m * 255).astype(np.uint8), "L")


_EDGE_MASK = _edge_mask()


def pulse_at(t, t0, decay=0.22):
    if t < t0:
        return 0.0
    return math.exp(-(t - t0) / decay)


class Frame:
    """Mask set for one frame, grouped so the whole scene resolves in a few
    composites regardless of how much is in it."""

    def __init__(self):
        self.far, self.d_far = props.new_mask()    # horizon, faded by fog
        self.bg, self.d_bg = props.new_mask()      # mid set, translucent
        self.sil, self.d_sil = props.new_mask()    # action plane, solid
        self.fg, self.d_fg = props.new_mask()      # defocused foreground
        self.red, self.d_red = props.new_mask()    # red line work
        self.lit, self.d_lit = props.new_mask()    # emissive, cool
        self.warm, self.d_warm = props.new_mask()  # emissive, warm
        self.rays, self.d_rays = props.new_mask()  # light-shaft source
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
        self.reflect = 0.0
        self.ray_at = None
        self.ray_amt = 0.0
        self.backlights = []
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.set_amt = 1.0
        self.texture = 1.0
        self.fog = 0.30


# --- typography ----------------------------------------------------------
def rule(d, cx, y, w, col, a, h=2):
    if w <= 1 or a <= 0.01:
        return
    d.rectangle([cx - w / 2, y, cx + w / 2, y + h],
                fill=(col[0], col[1], col[2], int(245 * a)))


def eyebrow(d, cx, y, text, a, col=(214, 206, 204), size=19, trk=12, flank=0):
    """A tracked micro-label, optionally flanked by hairlines."""
    if a <= 0.01 or not text:
        return 0
    f = font(LABEL_MED, size)
    w, _ = text_size(f, text, trk)
    tracked(d, (cx, y), text, f, (col[0], col[1], col[2], int(232 * a)), trk,
            anchor_center=True)
    if flank:
        for s in (-1, 1):
            x0 = cx + s * (w / 2 + 22)
            x1 = x0 + s * flank
            d.rectangle([min(x0, x1), y + size * 0.42, max(x0, x1),
                         y + size * 0.42 + 1],
                        fill=(col[0], col[1], col[2], int(150 * a)))
    return w


def display_line(d, cx, y, text, size, a, trk=4, col=(240, 236, 234),
                 shadow=True, fnt_path=DISPLAY):
    f = font(fnt_path, size)
    w, _ = text_size(f, text, trk)
    if shadow:
        d.text((cx - w / 2 + 5, y + 6), text, font=f, fill=(0, 0, 0, int(165 * a)))
    tracked(d, (cx, y), text, f, (col[0], col[1], col[2], int(250 * a)), trk,
            anchor_center=True)
    return w


def chapter_plate(f, t):
    """Running corner furniture: the chapter name and a tick rule."""
    a = window(t, S_ROAD + 2.9, S_ROAD + 3.8, S_END + 1, S_END + 2)
    if a <= 0.01:
        return
    fnt = font(LABEL, 19)
    label = TEXT["chapter"]
    w, _ = text_size(fnt, label, 6)
    dx = (1 - a) * 26
    tracked(f.d_txt, (W - 74 - w + dx, 46), label, fnt,
            (224, 216, 214, int(196 * a)), 6)
    k = ramp(t, S_ROAD + 3.0, S_ROAD + 3.9)
    f.d_txt.rectangle([74, 47, 74 + 158 * k, 49],
                      fill=(RED[0], RED[1], RED[2], int(228 * a)))


def chapter_card(f, t):
    """The chapter title, set as a proper editorial plate."""
    t0 = S_ROAD
    a = window(t, t0 + 0.15, t0 + 0.95, t0 + 2.55, t0 + 3.45)
    if a <= 0.01:
        return
    rise = smootherstep(ramp(t, t0 + 0.15, t0 + 1.05))
    dy = (1 - rise) * 16
    cx = W / 2
    cy = H * 0.395 + dy

    eyebrow(f.d_txt, cx, cy - 74, TEXT.get("chapter_number", ""), a,
            col=RED_HOT, size=18, trk=15, flank=46)

    name = TEXT.get("chapter_name", "")
    w = display_line(f.d_txt, cx, cy, name, 104, a, trk=10, fnt_path=EDITORIAL)

    sw = smootherstep(ramp(t, t0 + 0.5, t0 + 1.4))
    rule(f.d_txt, cx, cy + 128, (w + 150) * sw, (190, 176, 172), a * 0.55, 1)

    gloss = TEXT.get("chapter_gloss", "")
    if gloss:
        eyebrow(f.d_txt, cx, cy + 146, gloss, a * 0.92, col=(204, 196, 194),
                size=17, trk=11)


def shayari_credit(f, t):
    a = window(t, 16.4, 17.5, 22.2, 23.6)
    if a <= 0.01:
        return
    f_s = font(LABEL, 14)
    f_b = font(EDITORIAL, 26)
    tracked(f.d_txt, (76, H - 126), TEXT.get("credit_label", "WORDS BY"), f_s,
            (RED_HOT[0], RED_HOT[1], RED_HOT[2], int(216 * a)), 7)
    f.d_txt.text((76, H - 104), TEXT["shayari_credit"], font=f_b,
                 fill=(228, 221, 219, int(212 * a)))
    f.d_txt.rectangle([76, H - 62, 76 + 92 * a, H - 61],
                      fill=(RED[0], RED[1], RED[2], int(180 * a)))


def shayari_lines(f, t):
    """The recited couplet, set in italic serif - deliberately a different
    voice from the verse captions later in the film.

    Lines live in intro_text.json. An empty slot draws nothing, so the cut
    still plays clean before they are filled in.
    """
    for slot in TEXT.get("shayari", []):
        lines = [l for l in slot.get("lines", []) if l.strip()]
        if not lines:
            continue
        t0 = slot["t"]
        t1 = t0 + slot.get("hold", 5.2)
        a = window(t, t0, t0 + 0.6, t1 - 0.55, t1)
        if a <= 0.01:
            continue
        fnt = font(VERSE, 62)
        hot = set(w.upper() for w in slot.get("accent", []))
        y = H * 0.50 - len(lines) * 44
        rise = (1 - smootherstep(ramp(t, t0, t0 + 0.6))) * 20
        for ln in lines:
            words = ln.split()
            widths = [f.d_txt.textlength(w + " ", font=fnt) for w in words]
            x = W / 2 - sum(widths) / 2
            for wd, ww in zip(words, widths):
                key = wd.strip(",.!?-—").upper()
                col = RED_HOT if key in hot else (240, 235, 232)
                f.d_txt.text((x + 3, y + rise + 4), wd, font=fnt,
                             fill=(0, 0, 0, int(140 * a)))
                f.d_txt.text((x, y + rise), wd, font=fnt,
                             fill=(col[0], col[1], col[2], int(240 * a)))
                x += ww
            y += 82


def backlight(f, cx, cy, w, h, amt, warm=False):
    """Queue a soft pool of light behind the action, so ranks of silhouettes
    read as separate shapes instead of one mass. Resolved in render()."""
    if amt <= 0.004:
        return
    f.backlights.append((cx, cy, w, h, amt,
                         (244, 176, 142) if warm else (226, 188, 182)))


def walker_x(t):
    if t < S_ROAD:
        return W * 0.16
    k = (t - S_ROAD) / (S_END - S_ROAD)
    return W * (0.16 + 0.34 * smoothstep(clamp(k * 1.25)))


def walker(f, t, h=176):
    x = walker_x(t)
    props.figure(f.d_sil, x, GY, h, phase=t * 5.4)
    return x


# --- S0  BRAND  0 -> 6.48 ------------------------------------------------
def s_brand(f, t):
    f.intensity = 0.30 + 0.70 * ramp(t, 0.30, 2.2)
    f.glow_y = 0.60
    f.embers = 0.4 + 0.6 * ramp(t, 0.2, 2.5)
    f.fog = 0.18
    f.pulse = 0.55 * pulse_at(t, b(0), 0.30) + 0.22 * pulse_at(t, b(1), 0.25)

    a = window(t, b(0), b(0) + 0.42, b(1) + 1.55, b(2) - 0.08)
    if a <= 0.01:
        return
    k = ramp(t, b(0), b(0) + 0.55)
    sc = lerp(1.09, 1.0, ease_out_back(k, 0.9)) * lerp(1.0, 1.035, ramp(t, b(1), b(2)))
    size = max(10, int(146 * sc))
    cx = W / 2
    y = H * 0.40 - size * 0.5

    w = display_line(f.d_txt, cx, y, "AMAN", size, a, trk=int(6 * sc))

    sweep = smootherstep(ramp(t, b(0) + 0.30, b(0) + 1.05))
    rule(f.d_txt, cx, y + size * 0.98, w * 1.05 * sweep, RED, a, 4)

    sa = window(t, b(0) + 0.95, b(0) + 1.7, b(1) + 1.55, b(2) - 0.08)
    eyebrow(f.d_txt, cx, y + size * 1.14, TEXT["production"], sa, size=21,
            trk=14)

    # the mark throws a little light of its own
    mf = font(DISPLAY, size)
    mw, _ = text_size(mf, "AMAN", int(14 * sc))
    f.d_rays.rectangle([cx - mw / 2, y + size * 0.22, cx + mw / 2, y + size * 0.86],
                       fill=int(150 * a))
    f.ray_at = (cx, y + size * 0.55)
    f.ray_amt = 0.30 * a
    f.flash = 0.30 * pulse_at(t, b(0), 0.10)


# --- S1  TITLE  6.48 -> 12.45 -------------------------------------------
def s_title(f, t):
    """The title lands on a world. By seven seconds we are inside the story."""
    k = ramp(t, S_TITLE, S_TITLE + 1.4)
    f.glow_y = 0.69
    f.embers = 0.9
    f.haze = 0.60 * k
    f.fog = 0.42
    f.reflect = 0.42 * k
    f.rain = 0.10 * k
    f.pulse = 0.60 * pulse_at(t, S_TITLE, 0.28) + 0.25 * pulse_at(t, b(3), 0.22)
    f.flash = 0.38 * pulse_at(t, S_TITLE, 0.09)
    f.zoom = lerp(1.0, 1.055, smoothstep(ramp(t, S_TITLE, S_ROAD)))

    # The title owns a clean field first, as in the original; the world only
    # comes up underneath it once the type starts to leave.
    rv = smootherstep(ramp(t, b(3) + 0.35, S_ROAD))
    f.set_amt = rv
    f.haze = 0.60 * rv
    f.reflect = 0.42 * rv
    f.rain = 0.10 * rv

    if rv > 0.01:
        # four planes of depth instead of one gradient
        props.ridge(f.d_far, GY - 236, 268, 91, span=(-0.4, 1.4), rough=0.6,
                    floor=GY + 30)
        props.pylon(f.d_far, W * 0.19, GY - 150, 190, lw=2)
        props.pylon(f.d_far, W * 0.33, GY - 160, 150, lw=2)
        props.ridge(f.d_bg, GY - 150, 210, 31, span=(-0.35, 1.35), rough=0.8,
                    floor=GY + 54)
        props.ridge(f.d_bg, GY - 74, 132, 77, span=(-0.25, 1.25), rough=1.1,
                    floor=GY + 54)

        mr = 38
        mx, my = W * 0.715, GY - 352
        f.d_warm.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=120)
        f.d_rays.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=235)
        f.ray_at = (mx, my)
        f.ray_amt = 0.42 * rv

        props.dead_tree(f.d_bg, W * 0.845, GY - 46, 250, seed=14, t=t, wind=0.5)
        props.dead_tree(f.d_bg, W * 0.075, GY - 30, 190, seed=57, t=t, wind=0.5)
        props.ridge(f.d_bg, GY + 30, 46, 5, span=(-0.2, 1.2), rough=1.3,
                    floor=GY + 96)
        props.bird_flock(f.d_bg, W * 0.33, GY - 400, 150, t * 0.5, n=8, seed=3)
        props.grass(f.d_sil, -60, W + 60, GY + 46, 34, seed=12, n=120,
                    wind=0.5, t=t)
        props.debris(f.d_sil, -40, W + 40, GY + 58, seed=21, n=22)
        props.fg_frame(f.d_fg, t, seed=8, side_only=True)

    a = window(t, S_TITLE, S_TITLE + 0.40, b(3) + 1.35, S_ROAD - 0.06)
    if a > 0.01:
        ks = ramp(t, S_TITLE, S_TITLE + 0.5)
        sc = lerp(1.11, 1.0, ease_out(ks, 3.2))
        size = max(10, int(152 * sc))
        cx = W / 2
        y = H * 0.395 - size * 0.5 - 46 * ease_in(ramp(t, b(3) + 1.0, S_ROAD), 2.2)

        off = (1 - ks) * 11
        if off > 0.4:
            fnt = font(DISPLAY, size)
            ww, _ = text_size(fnt, TEXT["title"], int(3 * sc))
            tracked(f.d_txt, (cx - ww / 2 - off, y), TEXT["title"], fnt,
                    (RED_HOT[0], RED_HOT[1], RED_HOT[2], int(150 * a)), int(3 * sc))
        w = display_line(f.d_txt, cx, y, TEXT["title"], size, a, trk=int(3 * sc))

        sw = smootherstep(ramp(t, S_TITLE + 0.22, S_TITLE + 0.95))
        rule(f.d_txt, cx, y + size * 0.98, w * 0.62 * sw, RED, a, 6)

        # subtitle rides with the title, as in the original, not a beat later
        sa = window(t, S_TITLE + 0.30, S_TITLE + 0.95, b(3) + 1.35,
                    S_ROAD - 0.06)
        eyebrow(f.d_txt, cx, y + size * 0.98 + 30, TEXT["subtitle"], sa,
                size=20, trk=13)


# --- S2  THE ROAD  12.45 -> 18.41 ---------------------------------------
def s_road(f, t):
    """Somewhere to walk, and a full roadside to walk it past."""
    f.cam_x = lerp(-30, 30, smoothstep(ramp(t, S_ROAD, S_TOWN)))
    k = ramp(t, S_ROAD, S_ROAD + 1.3)
    f.glow_y = 0.69
    f.haze = 0.64
    f.fog = 0.46
    f.reflect = 0.62
    f.rain = 0.22 + 0.78 * ramp(t, S_ROAD + 0.2, S_ROAD + 2.6)
    f.wind = 0.26
    f.embers = 0.45
    f.pulse = 0.34 * pulse_at(t, S_ROAD, 0.26)

    props.ridge(f.d_far, GY - 240, 272, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    props.ridge(f.d_bg, GY - 150, 210, 31, span=(-0.35, 1.35), rough=0.8,
                floor=GY + 54)
    props.ridge(f.d_bg, GY - 74, 132, 77, span=(-0.25, 1.25), rough=1.1,
                floor=GY + 54)

    # distant town glow on the horizon - somewhere he is walking away from
    f.d_red.ellipse([W * 0.02, GY - 78, W * 0.32, GY - 30], fill=22)

    vy = GY - 6
    scroll = (t * 0.30) % 1.0
    rs, drs = props.new_mask()
    props.road(f.d_red, vy, W * 0.58, 540, fill=int(58 * k), lanes=9,
               scroll=scroll, surface=drs)
    f.red.paste(rs.point(lambda v: int(v * 0.075)), (0, 0), rs)

    # poles and wires marching past: the clearest read of forward motion here
    pm, pm_d = props.new_mask()
    span = 430.0
    off = (t * 72.0) % span
    prev = None
    for i in range(-1, 6):
        px = W * 1.14 - i * span + off
        ph = max(90, 250 - abs(px - W * 0.6) * 0.050)
        if -240 < px < W + 240:
            props.pole(pm_d, px, GY - 26, ph, arms=2)
            if prev is not None:
                props.wire(pm_d, prev[0], prev[1] - prev[2] * 0.84, px,
                           GY - 26 - ph * 0.84, 34, lw=2, t=t, sway=3)
        prev = (px, GY - 26, ph)
    f.sil.paste(pm, (0, 0), pm)
    f.red.paste(pm.point(lambda v: int(v * 0.30)), (0, 0), pm)

    # pylons behind, a lamp in front
    props.pylon(f.d_bg, W * 0.80 - (t - S_ROAD) * 14, GY - 110, 240, lw=3)
    props.pylon(f.d_bg, W * 1.06 - (t - S_ROAD) * 14, GY - 120, 200, lw=3)
    lx = W * 0.90 - (t - S_ROAD) * 40
    if -100 < lx < W + 100:
        lm, dlm = props.new_mask()
        lamp = props.street_lamp(dlm, lx, GY + 10, 300, bend=-1)
        f.sil.paste(lm, (0, 0), lm)
        f.red.paste(lm.point(lambda v: int(v * 0.34)), (0, 0), lm)
        f.d_warm.ellipse([lamp[0] - 16, lamp[1] - 14, lamp[0] + 16, lamp[1] + 14],
                         fill=180)
        f.d_rays.ellipse([lamp[0] - 14, lamp[1] - 12, lamp[0] + 14, lamp[1] + 12],
                         fill=210)
        f.ray_at = (lamp[0], lamp[1])
        f.ray_amt = 0.26
        f.d_warm.ellipse([lamp[0] - 150, GY + 16, lamp[0] + 150, GY + 56], fill=20)

    backlight(f, W * 0.55, GY - 24, W * 1.20, 400, 0.042)
    props.fence(f.d_sil, -40, W + 40, GY + 40, 34, lw=3, step=58)
    props.grass(f.d_sil, -60, W + 60, GY + 50, 36, seed=5, n=140, wind=0.8, t=t)
    props.debris(f.d_sil, -40, W + 40, GY + 62, seed=9, n=26)
    props.puddle(f.d_red, W * 0.34, GY + 56, 280, 26, fill=30)
    props.puddle(f.d_red, W * 0.72, GY + 70, 200, 20, fill=26)
    props.splashes(f.d_lit, -40, W + 40, GY + 46, t, n=48, seed=4,
                   strength=f.rain, fill=120)
    props.fg_frame(f.d_fg, t, seed=15, side_only=True)
    walker(f, t)

    # lightning: one frame of the whole landscape at full contrast
    lt = b(5)
    if lt <= t < lt + 0.16:
        f.flash = 0.80 * math.exp(-(t - lt) / 0.055)
        f.intensity *= 1.5
    ct = ramp(t, lt, lt + 2.4)
    if 0.01 < ct < 0.995:
        props.crow(f.d_sil, lerp(W * 0.42, W * 1.05, ct),
                   lerp(GY - 230, GY - 430, ease_out(ct, 2.0)), 26, t * 13.0)


# --- S3  THE TOWN  18.41 -> 24.37 ---------------------------------------
def s_town(f, t):
    """A town that lights up and then closes itself to him, told with windows."""
    f.cam_x = lerp(40, -40, smoothstep(ramp(t, S_TOWN, S_CROWD)))
    k = smootherstep(ramp(t, S_TOWN, S_TOWN + 1.5))
    f.glow_y = 0.71
    f.haze = 0.72
    f.fog = 0.46
    f.reflect = 0.66
    f.rain = 0.64 * (1 - 0.45 * ramp(t, b(7), S_CROWD))
    f.wind = 0.34
    f.embers = 0.6
    f.pulse = 0.30 * pulse_at(t, S_TOWN, 0.26) + 0.26 * pulse_at(t, b(7), 0.3)

    props.ridge(f.d_far, GY - 250, 280, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    drift = (t - S_TOWN) * 11.0
    props.skyline(f.d_far, GY - 60, -140 - drift * 0.4, W + 180, 190, 420,
                  seed=77, n=12, lean=0.14)

    slide = lerp(W * 0.55, 0.0, k) - drift
    sk = Image.new("L", (W, H), 0)
    dsk = ImageDraw.Draw(sk)
    wins = props.skyline(dsk, GY - 18, 120 + slide, W * 1.35 + slide, 150, 380,
                         seed=4, n=13, lean=0.22)
    f.bg.paste(sk, (0, 0), sk)

    props.water_tower(f.d_bg, W * 0.22 + slide * 0.7, GY - 300, 170)
    for i, ax in enumerate([0.42, 0.58, 0.79]):
        props.antenna(f.d_bg, W * ax + slide * 0.7, GY - 250 - i * 30,
                      130 + i * 24, seed=i)
    props.laundry_line(f.d_bg, W * 0.30 + slide, GY - 190,
                       W * 0.48 + slide, GY - 215, seed=2, n=5)
    props.smoke_column(f.d_bg, W * 0.63 + slide * 0.7, GY - 330, 330, t,
                       fill=52, seed=6, width=22)

    # windows: lit, then going out left to right after the bar
    douse = ramp(t, b(7), b(7) + 2.1)
    for (wx, wy, ww, wh, r) in wins:
        if wx < -40 or wx > W + 40:
            continue
        on = 1.0 - clamp((douse * 1.45 - clamp(wx / W)) * 2.4)
        amt = on * (0.78 + 0.22 * math.sin(t * (2.0 + r * 5) + r * 9)) * k
        if amt <= 0.04:
            continue
        f.d_warm.rectangle([wx, wy, wx + ww, wy + wh], fill=int(120 * amt))

    for lx in (W * 0.16, W * 0.56, W * 0.93):
        lm, dlm = props.new_mask()
        lamp = props.street_lamp(dlm, lx + slide * 0.25, GY + 12, 290,
                                 bend=1 if lx < W / 2 else -1)
        f.sil.paste(lm, (0, 0), lm)
        f.red.paste(lm.point(lambda v: int(v * 0.34)), (0, 0), lm)
        glowk = k * (1 - 0.55 * douse)
        f.d_warm.ellipse([lamp[0] - 15, lamp[1] - 13, lamp[0] + 15, lamp[1] + 13],
                         fill=int(170 * glowk))
        f.d_warm.ellipse([lamp[0] - 140, GY + 18, lamp[0] + 140, GY + 58],
                         fill=int(19 * glowk))

    props.fence(f.d_sil, -40, W + 40, GY + 44, 40, lw=3, step=56)
    props.grass(f.d_sil, -60, W + 60, GY + 52, 34, seed=18, n=130, wind=0.9, t=t)
    props.debris(f.d_sil, -40, W + 40, GY + 64, seed=11, n=24)
    props.puddle(f.d_red, W * 0.46, GY + 60, 320, 28, fill=30)
    props.splashes(f.d_lit, -40, W + 40, GY + 48, t, n=44, seed=7,
                   strength=f.rain, fill=110)
    props.dead_tree(f.d_sil, W * 0.10 + slide * 0.3, GY + 16, 260, seed=22,
                    t=t, wind=0.8)
    props.fg_frame(f.d_fg, t, seed=23, side_only=True)
    walker(f, t)


# --- S4  THE CROWD  24.37 -> 30.33 --------------------------------------
_CROWD = None


def _crowd_layout():
    """Five ranks, clustered toward the middle. An even line reads as a fence;
    a cluster with depth reads as a crowd."""
    global _CROWD
    if _CROWD is None:
        r = np.random.default_rng(99)
        rows = []
        for (yy, hh, n, spread) in [(GY - 58, 92, 14, 0.44),
                                    (GY - 24, 126, 12, 0.38),
                                    (GY + 24, 168, 9, 0.34),
                                    (GY + 84, 214, 7, 0.28),
                                    (GY + 150, 272, 5, 0.22)]:
            xs = W * 0.5 + r.normal(0, W * spread, n)
            rows.append([(float(x), yy, hh * r.uniform(0.88, 1.12),
                          float(r.random())) for x in xs])
        _CROWD = rows
    return _CROWD


def crowd(f, t, amount, turn_to=None, eyes=0.0, arms_up=0.0, scale=1.0,
          umbrellas=0.0):
    if amount <= 0.01:
        return
    for ri, row in enumerate(_crowd_layout()):
        ra = clamp((amount - ri * 0.11) * 1.7)
        if ra <= 0.02:
            continue
        for (x, y, h, seed) in row:
            hh = h * scale * (0.3 + 0.7 * ra)
            ht = 0.0
            if turn_to is not None:
                ht = clamp((turn_to - x) / (W * 0.45), -1, 1)
            head = props.figure(f.d_sil, x, y, hh, phase=seed * 6.3,
                                walking=False, head_turn=ht, arms_up=arms_up)
            if umbrellas > 0.01 and seed > 1.0 - umbrellas:
                uw = hh * 0.40
                uy = y - hh * 1.02
                f.d_sil.chord([x - uw, uy - hh * 0.34, x + uw, uy + hh * 0.18],
                              180, 360, fill=255)
                for rb in (-0.55, 0.0, 0.55):
                    f.d_sil.line([(x, uy - hh * 0.07),
                                  (x + uw * rb, uy + hh * 0.045)],
                                 fill=255, width=max(1, int(hh * 0.022)))
                f.d_sil.line([(x, uy), (x, y - hh * 0.60)], fill=255,
                             width=max(1, int(hh * 0.030)))
            e = clamp((eyes * 1.5) - (x / W))
            if e > 0.03 and head:
                props.eye(f.d_red, head[0], head[1], head[2] * 0.42 * e, 1.0)


def s_crowd(f, t):
    f.glow_y = 0.71
    f.haze = 0.74
    f.fog = 0.44
    f.reflect = 0.58
    f.rain = 0.30
    f.wind = 0.2
    f.embers = 0.5
    f.zoom = lerp(1.0, 1.07, smoothstep(ramp(t, S_CROWD, S_MASK)))
    f.pulse = 0.30 * pulse_at(t, S_CROWD, 0.26) + 0.5 * pulse_at(t, b(9), 0.3)

    props.ridge(f.d_far, GY - 250, 280, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    props.skyline(f.d_bg, GY - 18, -80, W + 80, 110, 280, seed=4, n=13, lean=0.18)
    props.smoke_column(f.d_bg, W * 0.78, GY - 300, 300, t, fill=44, seed=9)

    # a wall of light behind them, so the ranks separate as silhouettes
    backlight(f, W * 0.5, GY - 70, W * 1.05, 520, 0.085)
    f.d_rays.ellipse([W * 0.26, GY - 210, W * 0.74, GY + 30], fill=130)
    f.ray_at = (W * 0.5, GY - 120)
    f.ray_amt = 0.30

    amount = ramp(t, S_CROWD, S_CROWD + 2.0) + 0.45 * ramp(t, b(9), b(9) + 1.4)
    snap = smootherstep(ramp(t, b(9), b(9) + 0.45))
    crowd(f, t, amount, turn_to=lerp(walker_x(t), W / 2, snap),
          eyes=ramp(t, b(9), b(9) + 1.9), umbrellas=0.17)
    props.grass(f.d_sil, -60, W + 60, GY + 52, 32, seed=31, n=110, wind=0.7, t=t)
    props.splashes(f.d_lit, -40, W + 40, GY + 50, t, n=36, seed=12,
                   strength=f.rain, fill=100)
    props.fg_frame(f.d_fg, t, seed=33, side_only=True)
    walker(f, t)
    f.flash = 0.42 * pulse_at(t, b(9), 0.07)


# --- S5  THE MASK  30.33 -> 36.30 ---------------------------------------
def s_mask(f, t):
    """The one real image v8 had - the red eye - built up to and paid off."""
    f.glow_y = 0.60
    f.haze = 0.52
    f.fog = 0.38
    f.reflect = 0.48
    f.rain = 0.16
    f.embers = 0.95
    f.pulse = 0.34 * pulse_at(t, S_MASK, 0.26)
    f.zoom = lerp(1.07, 1.0, smoothstep(ramp(t, S_MASK, S_MASK + 1.6)))

    props.ridge(f.d_far, GY - 250, 280, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    props.skyline(f.d_bg, GY - 18, -80, W + 80, 100, 250, seed=4, n=13, lean=0.18)
    backlight(f, W * 0.5, GY - 40, W * 1.00, 470, 0.070)
    crowd(f, t, 1.0 - 0.3 * ramp(t, b(11), S_HOUSE), scale=0.75, umbrellas=0.12)
    props.grass(f.d_sil, -60, W + 60, GY + 52, 30, seed=41, n=100, wind=0.6, t=t)

    rise = smootherstep(ramp(t, S_MASK, S_MASK + 1.5))
    burst = ease_out(ramp(t, b(11), b(11) + 1.5), 2.0)
    a_mask = window(t, S_MASK, S_MASK + 1.2, b(11) + 0.9, S_HOUSE - 0.2)
    cx, cy = W * 0.5, lerp(H * 0.80, H * 0.44, rise)
    r = lerp(120, 304, rise) * (1 + 0.10 * burst)

    if a_mask > 0.02:
        crack = clamp((t - (S_MASK + 1.2)) / (b(11) - (S_MASK + 1.2)))
        solid, d_solid = props.new_mask()
        lines, d_lines = props.new_mask()
        props.mask_face(d_lines, cx, cy, r, crack=crack, lw=8, burst=burst,
                        d_fill=d_solid)
        body = a_mask * (1.0 - smootherstep(clamp(burst * 1.35)))
        f.sil.paste(solid.point(lambda v: int(v * body)), (0, 0), solid)
        f.red.paste(lines.point(lambda v: int(v * 0.62 * a_mask)), (0, 0), lines)

        # shards drifting off once it goes
        if burst > 0.02:
            rr = np.random.default_rng(13)
            for i in range(22):
                ang = rr.uniform(0, 6.283)
                dist = r * (0.6 + 2.1 * burst * rr.uniform(0.5, 1.4))
                sx = cx + math.cos(ang) * dist
                sy = cy + math.sin(ang) * dist * 1.1 + burst * 70
                sz = rr.uniform(5, 17) * (1 - burst * 0.4)
                if sz < 1:
                    continue
                f.d_red.polygon([(sx, sy - sz), (sx + sz * 0.7, sy),
                                 (sx, sy + sz), (sx - sz * 0.7, sy)],
                                fill=int(150 * a_mask * (1 - burst * 0.5)))

    ea = window(t, S_MASK + 1.9, b(11) - 0.5, S_HOUSE - 1.0, S_HOUSE + 0.3)
    if ea > 0.02:
        er = r * (0.19 + 0.10 * burst)
        glow = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 3.1))
        f.d_red.ellipse([cx - er, cy - er * 0.72, cx + er, cy + er * 0.72],
                        fill=int(248 * ea))
        f.d_lit.ellipse([cx - er * 0.34, cy - er * 0.25, cx + er * 0.34,
                         cy + er * 0.25], fill=int(150 * ea * glow))
        f.d_rays.ellipse([cx - er, cy - er * 0.72, cx + er, cy + er * 0.72],
                         fill=int(230 * ea))
        f.ray_at = (cx, cy)
        f.ray_amt = 0.52 * ea * (0.7 + 0.5 * burst)
    f.flash = 0.62 * pulse_at(t, b(11), 0.085)


# --- S6  THE HOUSE  36.30 -> 42.26 --------------------------------------
def s_house(f, t):
    """The door that closes - a scene with a beginning and an end."""
    f.cam_x = lerp(-25, 25, smoothstep(ramp(t, S_HOUSE, S_THREAD)))
    f.intensity = 0.95
    f.glow_y = 0.71
    f.haze = 0.70
    f.fog = 0.46
    f.reflect = 0.60
    f.rain = 0.34 + 0.46 * ramp(t, b(13), b(13) + 1.6)
    f.wind = 0.30
    f.embers = 0.55
    f.pulse = 0.30 * pulse_at(t, S_HOUSE, 0.26) + 0.28 * pulse_at(t, b(13), 0.3)

    props.ridge(f.d_far, GY - 244, 274, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    props.ridge(f.d_bg, GY - 152, 212, 31, span=(-0.35, 1.35), rough=0.8,
                floor=GY + 54)
    props.ridge(f.d_bg, GY - 70, 124, 77, span=(-0.25, 1.25), rough=1.1,
                floor=GY + 54)

    backlight(f, W * 0.42, GY - 30, W * 1.15, 430, 0.045)
    rise = smootherstep(ramp(t, S_HOUSE, S_HOUSE + 1.7))
    hy = GY + 26 + (1 - rise) * 200
    hx = W * 0.665
    hw = 320
    shut = smootherstep(ramp(t, b(13), b(13) + 0.75))

    # neighbours, already dark
    for nx, nw in ((W * 0.16, 190), (W * 1.02, 230)):
        nm, dnm = props.new_mask()
        props.house(dnm, nx, hy - 24, nw, lw=3)
        f.bg.paste(nm, (0, 0), nm)

    hm, dhm = props.new_mask()
    door_rect = props.house(dhm, hx, hy, hw, lw=5)
    f.sil.paste(hm, (0, 0), hm)
    f.red.paste(hm.point(lambda v: int(v * 0.46)), (0, 0), hm)

    props.smoke_column(f.d_bg, hx + hw * 0.26, hy - hw * 0.78 - 60, 260, t,
                       fill=46, seed=5, width=16)
    props.fence(f.d_sil, hx - hw * 1.9, hx + hw * 1.3, hy + 20, 42, lw=3, step=52)
    props.dead_tree(f.d_sil, hx + hw * 0.80, hy + 14, 300, seed=31, t=t, wind=0.7)
    props.dead_tree(f.d_bg, hx - hw * 1.7, hy + 6, 230, seed=63, t=t, wind=0.7)
    props.laundry_line(f.d_sil, hx - hw * 1.1, hy - 110, hx - hw * 0.5, hy - 130,
                       seed=4, n=3)
    # mailbox and path
    f.d_sil.line([(hx - hw * 0.95, hy + 20), (hx - hw * 0.95, hy - 46)],
                 fill=255, width=4)
    f.d_sil.rectangle([hx - hw * 0.95 - 17, hy - 70, hx - hw * 0.95 + 17, hy - 44],
                      fill=255)
    props.grass(f.d_sil, -60, W + 60, GY + 52, 36, seed=51, n=140, wind=0.9, t=t)
    props.debris(f.d_sil, -40, W + 40, GY + 64, seed=19, n=26)
    props.puddle(f.d_red, W * 0.30, GY + 62, 300, 26, fill=30)
    props.splashes(f.d_lit, -40, W + 40, GY + 50, t, n=46, seed=15,
                   strength=f.rain, fill=112)

    lit = rise * (1 - shut)
    if lit > 0.02:
        x0, y0, x1, y1 = door_rect
        f.d_warm.rectangle([x0 + 3, y0 + 3, x1 - 3, y1], fill=int(142 * lit))
        sp = (x1 - x0) * 1.9
        f.d_warm.polygon([(x0 + 3, y1), (x1 - 3, y1),
                          (hx + sp * 0.5, y1 + 62), (hx - sp * 0.5, y1 + 62)],
                         fill=int(46 * lit))
        f.d_rays.rectangle([x0 + 3, y0 + 3, x1 - 3, y1], fill=int(205 * lit))
        f.ray_at = ((x0 + x1) / 2, (y0 + y1) / 2)
        f.ray_amt = 0.34 * lit
        props.figure(f.d_sil, (x0 + x1) / 2, y1 - 2, (y1 - y0) * 0.84,
                     walking=False, lean=0.1)

    props.fg_frame(f.d_fg, t, seed=43, side_only=True)
    walker(f, t)
    f.haze += 0.1 * shut


# --- S7  THE THREADS  42.26 -> 48.22 ------------------------------------
def s_thread(f, t):
    """Strings come down out of the dark. Everyone is on one except him."""
    f.intensity = 0.92
    f.glow_y = 0.67
    f.haze = 0.62
    f.fog = 0.40
    f.reflect = 0.50
    f.rain = 0.30
    f.wind = 0.48
    f.embers = 0.8
    f.pulse = 0.30 * pulse_at(t, S_THREAD, 0.26) + 0.40 * pulse_at(t, b(15), 0.3)

    props.ridge(f.d_far, GY - 250, 280, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)

    reach = smootherstep(ramp(t, S_THREAD, S_THREAD + 2.2))
    reach *= 1.0 - 0.25 * ramp(t, b(15) + 0.4, S_LIGHT)
    if reach > 0.02:
        for sd in (41, 67, 103, 151):
            side = -1 if sd % 2 else 1
            props.branch_curtain(f.d_red, side, reach, sd, t=t, lw=7, fill=76)
            props.branch_curtain(f.d_bg, side, reach * 0.92, sd, t=t, lw=10)
        props.dead_tree(f.d_bg, W * 0.08, GY + 20, 420, seed=71, t=t, wind=1.2)
        props.dead_tree(f.d_bg, W * 0.94, GY + 20, 390, seed=83, t=t, wind=1.2)

    snapped = ease_out(ramp(t, b(15), b(15) + 1.9), 1.6)
    hooked = ramp(t, S_THREAD + 0.6, S_THREAD + 2.4)
    arm = hooked * (1 - snapped) * 0.85
    backlight(f, W * 0.5, GY - 50, W * 1.05, 480, 0.080)
    crowd(f, t, 1.0, scale=0.8, arms_up=arm)

    # every string lands on a raised hand and follows it back down
    ends = []
    for ri, row in enumerate(_crowd_layout()[:3]):
        for (x, y, hgt, seed) in row:
            if seed < 0.58:
                continue
            hh = hgt * 0.8
            sho = y - hh * 0.74
            sgn = 1 if seed > 0.5 else -1
            ends.append((x + sgn * hh * lerp(0.17, 0.28, arm),
                         lerp(sho + hh * 0.33, sho - hh * 0.19, arm) - 6))
    props.threads(f.d_red, [], -20, GY - 118, t, snapped=snapped, fill=62,
                  ends=ends)

    props.leaves(f.d_sil, t, n=34, seed=5, strength=1.0)
    props.grass(f.d_sil, -60, W + 60, GY + 52, 34, seed=61, n=120, wind=1.1, t=t)
    props.fg_frame(f.d_fg, t, seed=53)
    walker(f, t)
    f.flash = 0.34 * pulse_at(t, b(15), 0.08)


# --- S8  THE LIGHT  48.22 -> 52.53 --------------------------------------
def s_light(f, t):
    """Into the light, watched. Hands off to the first verse on a white frame."""
    k = smootherstep(ramp(t, S_LIGHT, S_LIGHT + 1.1))
    f.intensity = lerp(1.0, 0.70, k)
    f.glow_y = 0.69
    f.haze = 0.48
    f.fog = 0.34
    f.reflect = 0.72
    f.rain = 0.46
    f.wind = 0.22
    f.embers = 0.35
    f.cool = 0.58 * k
    f.pulse = 0.5 * pulse_at(t, S_LIGHT, 0.3)

    tighten = smootherstep(ramp(t, b(17), S_END))
    apex_x = W * 0.5
    spread = lerp(300, 196, tighten) * k

    # two rakers behind the main key, so the stage has shape
    if k > 0.02:
        cone, dc = props.new_mask()
        for ax, sp, br in ((W * 0.20, 120 * k, 30), (W * 0.82, 130 * k, 30)):
            props.spot_cone(dc, ax, -70, sp, GY + 40, fill=br)
        if spread > 4:
            props.spot_cone(dc, apex_x, -70, spread, GY + 40, fill=96)
            props.dust(dc, apex_x, spread, -60, GY + 30, t, n=96, fill=190)
        f.lit.paste(cone, (0, 0), cone)
        f.rays.paste(cone.point(lambda v: int(v * 1.6)), (0, 0), cone)
        f.ray_at = (apex_x, 0)
        f.ray_amt = 0.30 * k
        f.d_lit.ellipse([apex_x - spread * 1.18, GY - 26,
                         apex_x + spread * 1.18, GY + 34], fill=int(120 * k))

    wx = lerp(walker_x(S_LIGHT), apex_x, smootherstep(ramp(t, S_LIGHT, b(17))))
    sh, dsh = props.new_mask()
    dsh.polygon([(wx - 24, GY), (wx + 24, GY),
                 (wx + 150, GY + 128), (wx - 150, GY + 128)], fill=170)
    f.sil.paste(sh, (0, 0), sh)
    props.figure(f.d_sil, wx, GY, 150, phase=t * 5.4, walking=t < b(17) + 0.4)

    close = smootherstep(ramp(t, b(17), S_END))
    crowd(f, t, 1.0, scale=lerp(0.85, 1.12, close), umbrellas=0.14)
    props.splashes(f.d_lit, -40, W + 40, GY + 48, t, n=56, seed=17,
                   strength=f.rain, fill=150)
    props.grass(f.d_sil, -60, W + 60, GY + 52, 30, seed=71, n=100, wind=0.6, t=t)
    props.fg_frame(f.d_fg, t, seed=63, side_only=True)

    # No whiteout here any more: the film is rendered continuously now, and
    # the original's own flash arrives through the keyed text layer.
    f.flash = 0.45 * pulse_at(t, S_LIGHT, 0.09)


# --- assembly ------------------------------------------------------------
def build(t, scene_fn=None):
    f = Frame()
    if scene_fn is None:
        for t0, t1, fn in SCENES:
            if t0 <= t < t1:
                scene_fn = fn
                break
    if scene_fn is not None:
        scene_fn(f, t)
    if t < S_END:
        # past the hand-off, v8's own plates and credits are keyed back in
        chapter_plate(f, t)
        chapter_card(f, t)
        shayari_credit(f, t)
        shayari_lines(f, t)
    return f


def _compose(t, scene_fn):
    """Compose one frame for one scene. Returns HxWx3 uint8 RGB."""
    f = build(t, scene_fn)
    img = world.background(t, glow_y=f.glow_y, glow_x=f.glow_x,
                           intensity=f.intensity, pulse=f.pulse, cool=f.cool)

    # far set first, lifted by fog so distance reads as distance
    if f.texture > 0.01:
        for lay, gain in ((_wisps.draw(t, f.texture), 0.55),
                          (_bokeh.draw(t, f.texture), 0.75)):
            if lay is not None:
                arr = np.asarray(lay, dtype=np.float32)
                img += arr[:, :, :3] * (arr[:, :, 3:4] / 255.0) * gain

    img = props.paint(img, f.far, (16, 5, 6), 0.62 * f.set_amt, 2.8)
    img = post.depth_fog(img, near=0.58, far=0.90, strength=f.fog)
    img = props.paint(img, f.bg, (6, 2, 3), 0.78 * f.set_amt, 2.0)

    for (cx, cy, bw, bh, amt, col) in f.backlights:
        img = post.soft_glow(img, cx, cy, bw, bh, amt, col)

    if f.haze > 0.01:
        hz = world.haze_band(t, 0.76, 1.02, f.haze)
        if hz is not None:
            arr = np.asarray(hz, dtype=np.float32)
            a = arr[:, :, 3:4] / 255.0
            img += (arr[:, :, :3] - img) * a * 0.55

    img = props.emit(img, f.warm, (255, 146, 68), gain=0.30, blur=6.0)
    img = props.emit(img, f.warm, (255, 198, 134), gain=0.26, blur=1.0)
    img = props.emit(img, f.lit, (226, 222, 230), gain=1.05, blur=3.0)
    img = props.paint(img, f.sil, (0, 0, 0), max(0.0, min(1.0, f.set_amt)), 0.75)

    if f.reflect > 0.01:
        refl = ImageChops.lighter(f.bg, f.sil)
        img = post.reflection(img, refl, GY + 46, strength=f.reflect, t=t)

    img = props.emit(img, f.red, RED_HOT, gain=1.0, blur=1.4)

    if f.ray_at is not None and f.ray_amt > 0.01:
        img = post.god_rays(img, f.rays, f.ray_at[0], f.ray_at[1],
                            strength=f.ray_amt)

    rn = _rain.draw(t, f.rain, f.wind)
    if rn is not None:
        arr = np.asarray(rn, dtype=np.float32)
        img += arr[:, :, :3] * (arr[:, :, 3:4] / 255.0) * 0.55
    em = _embers.draw(t, f.embers)
    if em is not None:
        arr = np.asarray(em, dtype=np.float32)
        img += arr[:, :, :3] * (arr[:, :, 3:4] / 255.0) * 0.8

    # defocused foreground, last of the geometry, confined to the frame edges
    if f.fg.getbbox() is not None:
        fg = ImageChops.multiply(f.fg, _EDGE_MASK)
        img = props.paint(img, fg, (0, 0, 0), 0.80, 11.0)

    img = post.glow(img)

    txt = np.asarray(f.txt, dtype=np.float32)
    ta = txt[:, :, 3:4] / 255.0
    if ta.max() > 0.003:
        img += (txt[:, :, :3] - img) * ta

    img = world.apply_grain(img, t, 6.0)
    img = world.apply_vignette(img, 1.0)

    if f.flash > 0.004:
        img += 255.0 * min(1.0, f.flash)

    img = post.grade(img)
    img = post.gate_weave(img, t, 1.0)
    img = world.letterbox(img, t)

    if f.zoom > 1.001 or abs(f.cam_x) > 0.5 or abs(f.cam_y) > 0.5:
        z = max(1.001, f.zoom)
        cw, ch = int(W / z), int(H / z)
        x0 = int(np.clip((W - cw) // 2 + f.cam_x, 0, W - cw))
        y0 = int(np.clip((H - ch) // 2 + f.cam_y, 0, H - ch))
        pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        out = np.asarray(pil.crop((x0, y0, x0 + cw, y0 + ch))
                         .resize((W, H), Image.BICUBIC))
    else:
        out = np.clip(img, 0, 255).astype(np.uint8)

    return post.chromatic_u8(out, 2.0)


# =========================================================================
#  ADHYAY 2 - 6 : the backgrounds behind the original lyric layer.
#  v8's typography is keyed off its own frames and composited over these,
#  so the words, their timing and their highlights are untouched.
# =========================================================================


def s_bheed(f, t):
    """He is swallowed by the mass. The crowd fills the frame to the lens."""
    f.cam_x = lerp(-40, 40, smoothstep(ramp(t, S_BHEED, S_PARCH)))
    k = ramp(t, S_BHEED, S_BHEED + 2.0)
    f.glow_y = 0.66
    f.haze = 0.56
    f.fog = 0.40
    f.reflect = 0.30
    f.rain = 0.22
    f.embers = 0.5
    f.pulse = 0.34 * pulse_at(t, S_BHEED, 0.3) + 0.22 * pulse_at(t, b(20), 0.3)
    f.zoom = lerp(1.0, 1.08, smoothstep(ramp(t, S_BHEED, S_PARCH)))

    props.ridge(f.d_far, GY - 250, 280, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    props.skyline(f.d_bg, GY - 14, -80, W + 80, 110, 300, seed=4, n=14, lean=0.18)
    backlight(f, W * 0.5, GY - 90, W * 1.1, 560, 0.095)

    density = 0.45 + 0.55 * k + 0.25 * ramp(t, b(20), S_PARCH)
    props.crowd_sea(f.d_sil, t, density, rows=8, seed=5,
                    eye_d=f.d_red, eyes=ramp(t, S_BHEED + 1.2, b(21)))
    props.leaves(f.d_sil, t, n=20, seed=8, strength=0.7)
    props.fg_frame(f.d_fg, t, seed=73, side_only=True)
    f.flash = 0.30 * pulse_at(t, b(20), 0.08)


def s_parchhai(f, t):
    """His own shadow stands up behind him and stops copying him."""
    f.cam_x = lerp(50, -50, smoothstep(ramp(t, S_PARCH, S_DHAAGE)))
    k = smootherstep(ramp(t, S_PARCH, S_PARCH + 2.2))
    f.glow_y = 0.62
    f.haze = 0.50
    f.fog = 0.34
    f.reflect = 0.44
    f.rain = 0.20
    f.embers = 0.8
    f.pulse = 0.34 * pulse_at(t, S_PARCH, 0.3) + 0.3 * pulse_at(t, b(24), 0.3)
    f.zoom = lerp(1.08, 1.0, smoothstep(ramp(t, S_PARCH, S_PARCH + 2.0)))

    props.ridge(f.d_far, GY - 250, 280, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    # a wall of light that casts him
    backlight(f, W * 0.5, GY - 150, W * 1.25, 700, 0.14)
    f.d_rays.ellipse([W * 0.30, GY - 320, W * 0.70, GY - 40], fill=150)
    f.ray_at = (W * 0.5, GY - 180)
    f.ray_amt = 0.30 * k

    # the shadow: locked to him at first, then it drifts off on its own
    free = smootherstep(ramp(t, b(24), b(25)))
    wx = W * (0.40 + 0.10 * math.sin(t * 0.45))
    sx = lerp(wx, W * (0.62 + 0.16 * math.sin(t * 0.3 + 1.7)), free)
    sh_h = lerp(260, H * 0.92, k)
    head = props.looming_shadow(f.d_sil, sx, GY + 120, sh_h, t,
                                head_turn=free * 0.9, lean=free * 0.6)
    if head and free > 0.05:
        props.eye(f.d_red, head[0], head[1], head[2] * 0.34 * free, 1.0)
        f.d_rays.ellipse([head[0] - head[2] * 0.4, head[1] - head[2] * 0.3,
                          head[0] + head[2] * 0.4, head[1] + head[2] * 0.3],
                         fill=int(200 * free))
        f.ray_at = (head[0], head[1])
        f.ray_amt = 0.34 * free

    props.crowd_sea(f.d_sil, t, 0.55, rows=4, seed=9, top=0.05, sway=0.6)
    props.figure(f.d_sil, wx, GY + 30, 190, phase=t * 4.2)
    props.grass(f.d_sil, -60, W + 60, GY + 60, 32, seed=81, n=100, wind=0.7, t=t)
    props.fg_frame(f.d_fg, t, seed=83, side_only=True)
    f.flash = 0.40 * pulse_at(t, b(24), 0.08)


def s_dhaage(f, t):
    """Everything was hanging on a thread. The threads go."""
    f.zoom = lerp(1.0, 1.05, smoothstep(ramp(t, S_DHAAGE, S_PAANI)))
    f.cam_y = lerp(-30, 30, smoothstep(ramp(t, S_DHAAGE, S_PAANI)))
    f.glow_y = 0.66
    f.haze = 0.52
    f.fog = 0.38
    f.reflect = 0.34
    f.rain = 0.26
    f.wind = 0.5
    f.embers = 0.85
    f.pulse = 0.34 * pulse_at(t, S_DHAAGE, 0.3) + 0.45 * pulse_at(t, b(28), 0.3)

    props.ridge(f.d_far, GY - 250, 280, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    backlight(f, W * 0.5, GY - 70, W * 1.05, 520, 0.075)

    cut = ease_out(ramp(t, S_DHAAGE + 1.6, b(29)), 1.5)
    rng = np.random.default_rng(31)

    # the set itself is suspended, and drops out piece by piece
    items = []
    for i in range(7):
        x = (i + 0.5) / 7 * W + rng.uniform(-60, 60)
        items.append((x, rng.uniform(0.0, 0.85), rng.uniform(150, 320)))
    for i, (x, thr, size) in enumerate(items):
        drop = clamp((cut - thr) * 2.2)
        y = GY - 150 - (i % 3) * 90

        def draw_house(px, py, s=size):
            hm, dhm = props.new_mask()
            props.house(dhm, px, py, s, lw=4)
            f.sil.paste(hm, (0, 0), hm)
            f.red.paste(hm.point(lambda v: int(v * 0.42)), (0, 0), hm)

        props.hanging(f.d_red, draw_house, x, y, t, drop, fill=90)
        if 0.01 < drop < 0.3:
            f.d_lit.ellipse([x - 26, y - 150, x + 26, y - 100], fill=120)

    # and so are the people
    for i in range(11):
        x = (i + 0.5) / 11 * W + rng.uniform(-30, 30)
        thr = rng.uniform(0.0, 0.95)
        drop = clamp((cut - thr) * 2.4)
        y = GY + 20

        def draw_fig(px, py):
            props.figure(f.d_sil, px, py, 150, phase=0, walking=False,
                         arms_up=0.9 * (1 - drop))

        props.hanging(f.d_red, draw_fig, x, y, t, drop, fill=84)

    props.figure(f.d_sil, W * 0.44, GY + 40, 190, phase=t * 4.6)
    props.leaves(f.d_sil, t, n=40, seed=12, strength=1.2)
    props.grass(f.d_sil, -60, W + 60, GY + 62, 32, seed=91, n=90, wind=1.2, t=t)
    props.fg_frame(f.d_fg, t, seed=93, side_only=True)
    f.flash = 0.42 * pulse_at(t, b(28), 0.08)


def s_paani(f, t):
    """Under. Cold, slow, and everything sinking past him."""
    k = smootherstep(ramp(t, S_PAANI, S_PAANI + 2.4))
    f.glow_y = 0.50
    f.haze = 0.30
    f.fog = 0.50
    f.reflect = 0.0
    f.rain = 0.0
    f.embers = 0.0
    f.cool = 0.88 * k
    f.intensity = lerp(1.0, 0.62, k)
    f.pulse = 0.30 * pulse_at(t, S_PAANI, 0.3)
    f.zoom = lerp(1.0, 1.06, smoothstep(ramp(t, S_PAANI, S_SACH)))

    sh, dsh = props.new_mask()
    props.water_shafts(dsh, t, n=8, seed=2, fill=70, strength=k)
    f.lit.paste(sh, (0, 0), sh)
    f.rays.paste(sh.point(lambda v: int(v * 2.0)), (0, 0), sh)
    f.ray_at = (W * 0.5, -40)
    f.ray_amt = 0.34 * k

    props.sinking_figures(f.d_sil, t, n=8, seed=4, strength=k)
    props.bubbles(f.d_lit, t, n=90, seed=6, fill=130, strength=k)

    # him, descending through it
    dy = lerp(-H * 0.1, H * 0.34, smoothstep(ramp(t, S_PAANI, S_SACH)))
    props.figure(f.d_sil, W * 0.5 + math.sin(t * 0.4) * 50, H * 0.46 + dy, 210,
                 phase=0, walking=False, arms_up=0.35)
    props.fg_frame(f.d_fg, t, seed=97, side_only=True)


def s_sach(f, t):
    """Everything strips away. One figure, one light, and what is left."""
    f.cam_y = lerp(20, -20, smoothstep(ramp(t, S_SACH, S_OUTRO)))
    k = smootherstep(ramp(t, S_SACH, S_SACH + 2.0))
    f.glow_y = 0.70
    f.haze = 0.26
    f.fog = 0.22
    f.reflect = 0.68
    f.rain = 0.16
    f.embers = 0.30
    f.cool = lerp(0.88, 0.22, k)
    f.intensity = lerp(0.62, 0.80, k)
    f.pulse = 0.34 * pulse_at(t, S_SACH, 0.3)
    f.zoom = lerp(1.06, 1.0, k)

    apex = W * 0.5
    spread = lerp(90, 210, k)
    cone, dc = props.new_mask()
    props.spot_cone(dc, apex, -70, spread, GY + 40, fill=104)
    props.dust(dc, apex, spread, -60, GY + 30, t, n=70, fill=180)
    f.lit.paste(cone, (0, 0), cone)
    f.rays.paste(cone.point(lambda v: int(v * 1.5)), (0, 0), cone)
    f.ray_at = (apex, 0)
    f.ray_amt = 0.26 * k
    f.d_lit.ellipse([apex - spread * 1.2, GY - 26, apex + spread * 1.2, GY + 34],
                    fill=int(130 * k))

    sh, dsh = props.new_mask()
    dsh.polygon([(apex - 26, GY), (apex + 26, GY),
                 (apex + 170, GY + 150), (apex - 170, GY + 150)], fill=160)
    f.sil.paste(sh, (0, 0), sh)
    props.figure(f.d_sil, apex, GY, 180, phase=0, walking=False)

    # the watchers thin out and are gone
    leave = 1.0 - smootherstep(ramp(t, S_SACH + 1.6, b(36)))
    if leave > 0.02:
        props.crowd_sea(f.d_sil, t, 0.55 * leave, rows=3, seed=13, top=0.02,
                        sway=0.4)

    # one last eye, far off, and then nothing
    ea = window(t, b(36), b(36) + 0.8, b(37), b(37) + 1.2)
    if ea > 0.02:
        ex, ey = W * 0.80, GY - 230
        er = 16 * ea
        f.d_red.ellipse([ex - er, ey - er * 0.75, ex + er, ey + er * 0.75],
                        fill=int(250 * ea))
        f.d_rays.ellipse([ex - er, ey - er, ex + er, ey + er], fill=int(220 * ea))
        f.ray_at = (ex, ey)
        f.ray_amt = 0.30 * ea
    props.fg_frame(f.d_fg, t, seed=101, side_only=True)


def s_outro(f, t):
    """Back to the first image, emptied. The credits run over this."""
    f.zoom = lerp(1.04, 1.0, smoothstep(ramp(t, S_OUTRO, 128.0)))
    k = ramp(t, S_OUTRO, S_OUTRO + 3.0)
    f.glow_y = 0.68
    f.haze = 0.44
    f.fog = 0.42
    f.reflect = 0.40
    f.rain = 0.18 * (1 - ramp(t, 128.0, 136.0))
    f.embers = 0.9
    f.intensity = lerp(0.80, 1.0, k) * (1.0 - 0.85 * ramp(t, 133.0, 138.2))
    f.pulse = 0.30 * pulse_at(t, S_OUTRO, 0.3)

    props.ridge(f.d_far, GY - 236, 268, 91, span=(-0.4, 1.4), rough=0.6,
                floor=GY + 30)
    props.ridge(f.d_bg, GY - 150, 210, 31, span=(-0.35, 1.35), rough=0.8,
                floor=GY + 54)
    props.ridge(f.d_bg, GY - 74, 132, 77, span=(-0.25, 1.25), rough=1.1,
                floor=GY + 54)
    props.dead_tree(f.d_bg, W * 0.845, GY - 46, 250, seed=14, t=t, wind=0.5)
    props.dead_tree(f.d_bg, W * 0.075, GY - 30, 190, seed=57, t=t, wind=0.5)

    mr = 36
    mx, my = W * 0.715, GY - 348
    f.d_warm.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=int(118 * k))
    f.d_rays.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=int(230 * k))
    f.ray_at = (mx, my)
    f.ray_amt = 0.38 * k

    props.grass(f.d_sil, -60, W + 60, GY + 46, 34, seed=12, n=110, wind=0.5, t=t)
    props.debris(f.d_sil, -40, W + 40, GY + 58, seed=21, n=20)

    # he walks out of frame and does not come back
    gone = ramp(t, S_OUTRO, 124.0)
    if gone < 0.995:
        props.figure(f.d_sil, lerp(W * 0.46, W * 1.12, gone), GY, 168,
                     phase=t * 5.0)
    props.fg_frame(f.d_fg, t, seed=8, side_only=True)


SCENES = [
    (S_BRAND, S_TITLE, s_brand),
    (S_TITLE, S_ROAD, s_title),
    (S_ROAD, S_TOWN, s_road),
    (S_TOWN, S_CROWD, s_town),
    (S_CROWD, S_MASK, s_crowd),
    (S_MASK, S_HOUSE, s_mask),
    (S_HOUSE, S_THREAD, s_house),
    (S_THREAD, S_LIGHT, s_thread),
    (S_LIGHT, S_BHEED, s_light),
    (S_BHEED, S_PARCH, s_bheed),
    (S_PARCH, S_DHAAGE, s_parchhai),
    (S_DHAAGE, S_PAANI, s_dhaage),
    (S_PAANI, S_SACH, s_paani),
    (S_SACH, S_OUTRO, s_sach),
    (S_OUTRO, S_FIN + 1.0, s_outro),
]


DISSOLVE = 0.40


def render(t):
    """Compose one frame.

    Scenes cross-dissolve into each other rather than swapping their whole
    set on a downbeat, which is what made the earlier cut read as a slideshow.
    """
    idx = len(SCENES) - 1
    for i, (t0, t1, fn) in enumerate(SCENES):
        if t0 <= t < t1:
            idx = i
            break
    t0, _, fn = SCENES[idx]

    if idx > 0 and (t - t0) < DISSOLVE:
        a = smootherstep((t - t0) / DISSOLVE)
        prev = SCENES[idx - 1][2]
        A = _compose(t, prev).astype(np.float32)
        B = _compose(t, fn).astype(np.float32)
        return np.clip(A + (B - A) * a, 0, 255).astype(np.uint8)

    return _compose(t, fn)
