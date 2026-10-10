# Delusion Is Death — intro rebuild

Regenerates the first 52.5 seconds of the video and splices it onto the
existing cut. Everything from the first verse onward is untouched, and the
audio track is copied, never re-encoded.

## Build

```bash
cd video
./build.sh /path/to/Aman_Delusion_Is_Death_v8.mp4 Aman_Delusion_Is_Death_v9.mp4
```

Takes about 8 minutes on 4 cores.

To look at one beat while tuning:

```bash
python3 render.py --out /tmp/beat.mp4 --start 30 --end 36.5
```

## What changed, and why

v8's intro ran 52 seconds on four ideas — a logo, a title, a figure walking in
the dark, and a spotlight. Roughly forty of those seconds introduced nothing
new, which is what made it feel long. Two other things worked against it: every
prop cut in and out at full opacity, and the background was a static gradient,
so held shots had no motion in them at all.

**Nine scenes instead of four**, one new idea every two bars, each payoff
landing on a downbeat:

| Time | Beat | Pays off on |
|------|------|-------------|
| 0.00 | Brand — mark strikes in, rule sweeps out under it | 0.52 |
| 6.48 | Title lands *on a landscape*, not on black | 6.48 |
| 12.45 | **ADHYAY 1 · SHAYARI** chapter plate, then the road | 15.43 |
| 18.41 | The town — windows lit, then going dark one by one as he passes | 21.39 |
| 24.37 | The crowd — heads turn to track him, then snap to camera, eyes open | 27.35 |
| 30.33 | The mask — fractures a step per beat, shatters, the eye burns through | 33.32 |
| 36.30 | The house — a lit door with someone in it, which closes | 39.28 |
| 42.26 | The threads — everyone on a string except him, then they snap | 45.24 |
| 48.22 | The light — he steps in, watched, and the crowd closes | 51.20 |

**Smoothness.** Every prop runs through `style.window()` — an eased
in/hold/out envelope — so nothing appears or disappears on a hard edge. The
house rises out of the dark, the skyline slides in, the mask dissolves as it
bursts, the crowd fades up rank by rank.

**Detail.** Three ridge planes, a crooked skyline with practical windows,
telephone poles with sagging wires, a dead tree, fences, a mailbox, a house
with roof and chimney, a crow, drifting branches, puppet strings, dust inside
the light cone. Rain carries wind, embers rise, the glow breathes on the bar.

## Production pass

Three things carry the look:

**Depth.** Four planes — a fog-lifted far horizon (ridges, pylons, a second
skyline), a mid set, the action plane, and a defocused foreground confined to
the frame edges by a gradient mask so it reads as depth of field rather than a
smear.

**Light that behaves.** Wet-ground reflection with ripple and falloff, bloom,
halation, volumetric shafts from every practical source, soft backlight pools
that separate ranks of silhouettes, chromatic aberration, gate weave, and a
final S-curve grade.

**Density.** Transmission pylons, lamp posts with spill, a water tower,
antennae, laundry lines, chimney smoke, puddles, rain splashes on the ground,
grass, debris, bird flocks, blowing leaves, umbrellas in the crowd.

## Type system

Four roles with real contrast between them:

| Role | Face | Used for |
|------|------|----------|
| Title | Big Shoulders Bold | `DELUSION IS DEATH` — keeps the established brand |
| Chapter | Gloock | `SHAYARI` — high-contrast editorial serif |
| Verse | Instrument Serif Italic | the recited shayari, a different voice from the rap captions |
| Label | Jura | tracked micro-labels, eyebrows, credits |

## The one thing still missing

There are ~40 seconds of recited shayari under this intro with **nothing on
screen**. The verses later get full typography; the poetry gets none, so the
audience has nothing to hold on to during the part that already felt long.
That is the single biggest remaining win.

The text layer is built and timed — open `intro_text.json` and type the lines
into the slots:

```json
{"t": 12.45, "hold": 5.3, "lines": ["FIRST LINE", "SECOND LINE"], "accent": ["WORD"]}
```

`accent` words draw in red, matching the verse captions. Empty slots simply do
not draw, so the cut plays clean either way. Re-run `build.sh` after editing.

## Files

- `style.py` — palette, fonts, easing, text helpers
- `world.py` — background glow, haze, grain, vignette, rain, embers
- `props.py` — the cast and the set
- `scenes.py` — the beat sheet and frame assembly
- `render.py` — parallel frame renderer
- `intro_text.json` — all on-screen copy, including the shayari slots
