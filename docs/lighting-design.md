# Aries 28 — Lighting Design

**Companion to the main design doc. Scope: all illumination — ambient frame glow, status signaling, fan lighting, power-bay accent.**
Version 1.0 — July 2026 · Status: Tier 1 specified; Tier 2 planned

> Lighting is an **optional** layer. A build may omit it entirely with no effect on the compute, power, or network design. This document describes one implementation's approach for those who want it.

---

## 1. Design principle — two independent tiers

Lighting is split into two systems by **complexity and purpose**, decoupled so ambient illumination works from the start without depending on the status-signaling system.

| | Tier 1 — Ambient | Tier 2 — Status |
|---|---|---|
| **Purpose** | Resting aesthetic; structural edge glow | Information: reflects live cluster state |
| **Behavior** | Static single color (ice blue), always on | Addressable, color-changes per node/cluster state |
| **Hardware** | Non-addressable COB strip, power only | WS2812-class addressable + driver |
| **Controller** | **None** — straight off the fuse block | Arduino Nano (serial-driven by face node) |
| **When** | Now / early build | Later, when face node + daemon exist |
| **Depends on** | Nothing but 5V power | Face node, LED daemon, Arduino sketch |

**Rationale for the split:** a constant ambient glow (frame) reads as "mood" while a color-changing accent (status) reads as "signal." Separating the two keeps the information channel from being lost in decorative noise: constant ice-blue indicates the tower at rest, while any change in color conveys cluster state. This is a deliberate information-design choice, not only a convenience.

**Color discipline:** ambient stays a single cool color (ice blue). Status lighting owns the meaningful colors (cyan Ready / amber draining / red NotReady). Avoid colored translucent *panels* — they'd tint and corrupt the status colors; all color comes from the LEDs against smoked/black acrylic.

---

## 2. Tier 1 — Ambient frame glow (no controller)

### 2.1 Hardware
- **2× 5V COB LED strip, Ice Blue, 3.28 ft (1 m) each = 2 m total.** COB = continuous diffused emitter (no visible dots), which is exactly the look for frame edge-lighting.
- Currently USB-terminated. **Plan: cut the USB connector off ("butcher the strip") and hard-wire the leads directly to the 5V distribution fuse block.** No converter needed — the strips are native 5V and the main rail is 5V.

### 2.2 Wiring
- **Source:** dedicated circuit on the 12-circuit fuse block, off the 5V bus. One fuse (1–2 A is plenty — 2 m of COB draws only a few watts).
- **No microcontroller, no level shifter, no boost converter.** A static single-color strip is just a load on a rail: apply 5V, it glows. Any of those parts here would be overengineering.
- **Polarity matters** — COB strips are DC; observe + / − when re-wiring the cut end. Mark the positive lead before cutting.
- **Optional:** a switch on the circuit if independent on/off is wanted; otherwise it's on whenever the tower is powered.
- **Voltage-drop note:** at 5V, long runs of thin strip wire lose brightness toward the far end. 2 m is short enough to be fine, but if daisy-chaining, feed power to both ends (inject at the far end too) to keep brightness even.

### 2.3 Placement
- **Frame edges / T-slots** on the visible members (front verticals, top rails) → the structural glow lines that outline the tower. COB in the slot or in a 2020 LED diffuser channel clipped into the T-slot.
- Ice-blue COB behind/around the smoked panels reads as an even glow, not dots — the intended "lit from within" effect.
- 2 m budget: prioritize the front-facing and left (access-side) visible edges; the back/right can go unlit or get the second strip depending on how the power bay is styled.

### 2.4 Cut-and-rewire ("butcher") procedure

Goal: strip off the USB wiring and cut the strips into segments sized to the frame edges they'll light.

1. Note strip voltage (5V) and **mark polarity** before any cut.
2. **Measure the frame edges** to be lit and plan segment lengths against the strip's periodic **cut points** (COB strips cut only at marked pads; arbitrary lengths are not possible, so segments should be chosen to land near cut marks).
3. Remove the USB connector and its wiring entirely; power is fed from the fuse block, not USB.
4. Cut segments at the marked cut lines only (cutting between pads kills the downstream segment).
5. Solder leads to the segment pads and heatshrink each joint.
6. Where multiple segments meet at a frame corner, either bridge with short jumper wire (keeps the glow continuous around the corner) or feed each segment independently from the bus.
7. Run leads to the fuse-block circuit (fused 1–2 A), observing polarity.
8. Test each segment at low stakes (bench 5V) before committing it into the frame.

---

## 3. Tier 2 — Addressable status system (planned, later)

### 3.1 Purpose
Per-node and cluster-state signaling: carrier trace glow, front-panel Aries glyph backlight, fan ring color, optional per-node CPU matrix. Driven by the **LED daemon** on the face node (Pi 3A+), polling the k3s API.

State → color (from main doc §3.4): **cyan** Ready · **amber** cordoned/draining · **red pulse** NotReady · **orange sweep** control-plane degraded.

### 3.2 Controller decision — Arduino Nano as serial LED driver
An Arduino Nano (e.g. Elegoo Nano) is the **preferred** Tier-2 controller over driving WS2812s from the Pi directly:

- **Native 5V logic** → drives WS2812 data cleanly with **no 74AHCT125 level shifter** (the Pi's 3.3V data is marginal for WS2812 and normally needs the shifter; the Nano eliminates that part).
- **Real-time timing** → WS2812 protocol is nanosecond-sensitive; a Linux Pi can glitch under load (preemption), an Arduino never does. Rock-solid color.
- **Offloads LED work** → face node sends high-level commands ("node 3 = red") over **USB serial**; the Nano runs FastLED and generates the signal.
- **Cheap** → an Arduino Nano (or clone) is a few dollars.

**Architecture:** face node (Pi 3A+) → USB serial → Arduino Nano → WS2812 strips/rings (carriers, glyph, fan ARGB).

Tradeoff vs. direct-drive: a small Arduino sketch (serial-command parser + FastLED) plus Pi-side serial code, in exchange for no level shifter and bulletproof timing. Worth it.

### 3.3 Fan ARGB joins this chain
The ARCTIC P14 Pro's ARGB connector is a WS2812-style 5V addressable data line (3-pin: 5V / Data / GND, keyed). It chains into the Nano's WS2812 output as just more pixels — fan ring color = cluster state, same daemon. (Fan **PWM** speed control is separate — hardware-PWM GPIO on the face node, 25 kHz, 3.3V works; see main doc fan notes.)

### 3.4 Power
- Addressable strips/rings run on **5V** from the distribution bus (not through the Nano — the Nano supplies *data* only; power comes from the rail, common ground with the Nano).
- Budget per WS2812 pixel: up to 60 mA at full white. The daemon's `MAX_BRIGHTNESS = 0.5` cap (main doc §4) bounds worst-case draw. Size the fuse-block circuit for the actual pixel count when known.

---

## 4. Power-bay accent (Tier 1-class)

- Warm **amber** static strip underlighting the PSU/fuse block, giving the exposed power wiring a distinct visual treatment through the smoked right panel.
- Non-addressable single-color, off the fuse block like the ambient blue — no controller.
- Deliberately the **one warm zone** against the otherwise cool (ice-blue/cyan) palette — the contrast is the point (see the render/mood board).
- Optional later upgrade: tie to PSU/AC-present state, but not worth the complexity now.

---

## 5. Build order

1. **Now:** Tier 1 ice-blue COB — butcher the USB strips, wire to fuse block, mount in frame edges. Tower glows immediately, zero controller.
2. **Now/early:** amber power-bay accent strip, same simple wiring.
3. **Later (face-node era):** Tier 2 — flash a Nano with the FastLED serial-driver sketch, wire WS2812 strips for carriers/glyph, chain the fan ARGB, write the daemon's serial output. Level shifter avoided by using the Nano.
4. **Bonus:** per-node CPU matrix (main doc Phase 5) on the same Nano chain.

---

## 6. Bill of materials (lighting)

| Item | Qty | Source | Notes |
|---|---|---|---|
| 5V COB ice-blue strip, 1 m | 2 | **owned** | Tier 1 frame glow; cut USB, hard-wire |
| Amber COB/strip, short | 1 | buy (~$5) | power-bay accent |
| 2020 LED diffuser channel (optional) | — | buy (~$1–2/edge) | pro even-glow on directly-visible edges |
| Arduino Nano (or clone) | 1 | buy (~$4) | Tier 2 serial LED driver (replaces 74AHCT125) |
| WS2812B addressable strip/rings | — | buy, Tier 2 | carriers, glyph, matrix |
| Fuse-block circuits | — | existing | 1–2 A each for non-addressable strips |

**Not needed:** no ARGB controller (Nano does it), no level shifter (Nano is 5V-native), no boost converter for lighting (all strips 5V; the XL6019 is for the 12V fan motor only).
