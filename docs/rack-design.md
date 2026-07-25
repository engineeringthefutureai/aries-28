# Aries 28 — Rack & Mounting System Design

**Companion to the main design doc. Scope: node bays, rack structure, board retention, cable management, LED integration.**
Version 0.3 — July 2026 · Status: Concept C (rod-and-bead) is lead candidate; carrier/plate rod-hole fit confirmed, bead design + full cartridge assembly still pending
Changelog: v0.3 — initial fit test passed (carrier + top/bottom plates on real 6.35mm rods, plywood test-cut, three Pi 5s mounted); confirms §4's rod-bore-fit risk (item 3) for the plate/carrier side, bead side still open. v0.2 — added Concept C rod-and-bead swing rack (lead), demoted pillars to fallback, updated decision + open questions. v0.1 — concepts A/B, materials, detent ladder, buttons.

---

## 1. Requirements

| # | Requirement | Source |
|---|---|---|
| R1 | Tool-free insert/remove of any node (power unplugged first — cold-swap mechanically, drain-first at cluster level) | live-surgery goal |
| R2 | Every connector that gets pushed/pulled (ethernet, XT30, SD) sits adjacent to a supported mount point | PCB flex rule |
| R3 | Any NVMe-equipped node (Pi 5 + X1001, 3-hole HAT) — every control-plane node plus the storage node — mounts in the same system, in an extended-pitch (42 mm) bay | main doc §3.1, §4.3 |
| R4 | Retention mechanism is a replaceable wear part — worn parts swap without rebuilding the rack | 50-cycle problem |
| R5 | Boards visible as display objects; mounting hardware minimal or concealed | aesthetics (optional) |
| R6 | Cable routing is designed, not incidental — for serviceability and strain management | serviceability |
| R7 | v1 optimizes for simple manufacturing; iteration expected | process |
| R8 | Unused mounting provisions left throughout for unforeseen additions | pegboard's 10% |
| R9 | Rack height not limited by printer build volume | rod-and-bead insight |

---

## 2. Concept A — Direct board mount (ball-detent pillars) — shelved

Boards snap by their own mounting holes onto spring-ball pillar clips. Maximum floating-silicon look, fewest parts — but insertion force and wear land on the PCB (violates R4), the X1001 stack occupies the holes (breaks R3), and connector push demands all four corners engaged. Kept as a bench experiment only: one 4-point set for a spare Pi 4, cycle-tested for hole wear.

## 3. Concept B — Carrier + fixed pillars (fallback)

Per-board carrier plate (board bolted conventionally); carrier hook-and-rotates onto fixed printed pillars, ball detents retain. Solves R2/R3/R4. Remains the fallback if Concept C's geometry tests fail. Carrier design, materials, and detents from this concept carry forward into C unchanged.

## 4. Concept C — Rod-and-bead swing rack (LEAD)

Four vertical **1/4" (6.35mm) smooth stainless rods** between top and bottom plates; printed **spacer beads** threaded onto the rods like an abacus set the bay pitch. The whole cartridge is sandwiched plate-to-plate and bolted into the 2020 frame. Rack height is set by rod length, not printer volume (R9).

**Corner role assignment (each rod has a job):**

| Corner | Role | Carrier feature |
|---|---|---|
| Front-left | **Pivot** — carrier swings out like a gate | closed ring / deep-C bore riding the rod (dry PTFE lube = entire bearing budget) |
| Rear-right | **Latch** — passive notch on the carrier; the **latch bead** on this rod carries the active spring finger + pull tab. Release = right hand pulls tab, left hand rotates. Zero pull force on the board — deliberate two-handed removal by construction. | plain open U-notch + small rectangular engagement notch on the edge |
| Rear-left | bridged support | open C-notch (departs sideways during swing) |
| Front-right | independent stack, open side | open C-notch (exit side) |

Rear pair and front-left are **bridged** bead stacks (printed bridges between adjacent stacks) for rigidity; front-right stays independent, keeping two faces of the rack open for access. Unlatch rear-right → carrier swings out the front-right opening → board inspectable **with cables still attached**. This is the property no slide-in shelf has.

**Bead system:**
- Standard (compute) bead: sets the **30 mm** compute pitch, keyed to neighbors by interlocking tabs; bottom bead keys into the base plate → whole stack inherits orientation (round rods can't key themselves).
- **Anchor beads:** special beads with tabs/T-nut bosses bolting the cartridge to the 2020 frame at mid-heights — attachment and rod anti-bowing brace in one part.
- Other special beads as needed: cable-comb beads, LED-strip beads, button-mount beads (R8 lives here — the bead is the expansion slot).
- Extended bead: sets the **42 mm** extended pitch for the tall rack — nodes with a vertical HAT, such as a Pi 5 + NVMe stack (etcd on a control-plane node, or bulk storage — R3). Two pitches → two bead sizes; each rack cartridge uses one size throughout (architecture.md §6).

**Tolerance & preload (the failure mode to engineer against):** all-smooth rods mean pitch is set purely by the bead stack — printed height error accumulates. Countermeasures: print each rod's beads in one batch (same profile, same squish); design the **topmost bead as compliant** (printed wave-spring profile, or an O-ring under the top plate) so plate clamping preloads the stack solid regardless of ±0.5mm accumulated error; carriers get ±1mm vertical compliance at the latch.

**Rod ends:** blind pockets in top/bottom plates; frame bolts provide clamping force. No threads, no e-clips in v1. Top/bottom plates are laser-cut sheet (`hardware/rack/rack-top-bottom.svg`) rather than printed; their rod-hole placement is shared with the carrier's rod/pivot bores (`hardware/carrier/carrier-rpi-b.svg`) and the two are designed together.

**Assembly property:** the entire populated rack is a **cartridge** — build, wire, and bench-test it outside the tower, then drop it in as one unit.

**Known geometry risks (test before committing the fleet):**
1. Swing arc: rear-right corner sweeps the largest radius — must clear rear-left rod + beads. Sets minimum rod spacing vs carrier depth. Cardboard/scrap-print mockup first.
2. Hand clearance: reaching the rear-right latch between bays at the 30 mm compute pitch. Escape hatch: front-actuated pushrod along the carrier edge.
3. Bead bore fit on 6.35mm rod: coupon-test printed bore (start 6.5mm, ream to slip fit). **Carrier pivot bores confirmed** — initial fit test (v0.3) threaded laser-cut carriers and top/bottom plates onto the real rods cleanly. **Bead bore still open** — beads aren't designed/printed yet.

## 5. Decision

**v1 = Concept C**, pending the three geometry tests above. Concept B is the fallback (its carrier, material, and detent work transfers 1:1). Concept A stays a bench curiosity.

---

## 6. Carrier material study

| Material | Method | Pros | Cons | Verdict |
|---|---|---|---|---|
| PETG print | 3D print | Detent flexures printable-in-place; bosses, tabs, pivot ring free-form | Opaque; layer lines | Workhorse. v1 default |
| **Clear acrylic 3mm** | Laser | **Edge-lights spectacularly** — carrier becomes the LED element; engraving glows; board floats on light | Brittle at hooks/latch; no compliant geometry; pivot bore wears | v1.1 target |
| Smoked acrylic | Laser | Subtle; glows only when lit | Same brittleness | Alternate skin |
| Hybrid: acrylic plate + printed corner blocks | Laser + print | Acrylic glows, PETG flexes and pivots — each material does its job | Two parts, bolted | **Likely end-state** |

**LED integration:** per-bay WS2812B segment aimed into the carrier's polished edge → engraved traces + node glyph glow in status color. The carriers *are* the status display. Engrave on back face for forward glow; polish light-entry edges.

## 7. Latch — wear ladder (lives in the latch bead, not the carrier)

The carrier's latch feature is a passive notch; all spring/wear geometry is in the **latch bead** — a $0.20 replaceable part, iterated independently of the fleet's carriers. Escalate only when the previous rung measurably fails (100-cycle bench test, logged):
1. **v1** — printed PETG cantilever finger + pull tab, tip engaging the carrier notch (~1mm engagement, ramped on the insert side so closing self-latches, square on the release side so opening requires the tab).
2. **v1.5** — finger tip carries a pressed-in 4.5mm steel BB riding the carrier notch — wear moves to the cheap plate edge.
3. **v2** — ball-nose spring plunger (M3/M4 brass, ~$1) threaded into the bead body, adjustable preload.

## 8. Cable management (structural + aesthetic)

- Ethernet and XT30 exit toward the **rear/latch zone** — push/pull forces land next to supported corners (R2 by construction). Verify against swing direction in CAD: cables must feed the swing, not fight it.
- Cable-comb beads on the rear rods; one labeled lane per bay.
- Slack loops sized to run out *before* the swing completes if still plugged — forgetting a cable stops rotation instead of ripping a connector.
- SD slots face the open front-right side; card swaps never disturb cables.

## 9. Stretch — per-bay power buttons

One recessed momentary button per bay, mounted on the rack (button-mount bead), wired into the bay's power harness.
- **Pi 5 nodes:** J2 header (dedicated 2-pin) — momentary = graceful shutdown; press while halted = **power on**. No GPIO consumed.
- **Pi 4/3 nodes:** GPIO3 + GND with `dtoverlay=gpio-shutdown` — identical semantics incl. boot-from-halt. (GPIO3 = I2C1 SCL, unused.)
- **Harness:** one 4-pin bay connector (5V, GND, BTN, GND) or XT30 + 2-pin JST — decide before crimping the fleet.
- **Cluster-graceful everywhere, zero wiring:** fleet-wide systemd shutdown hook (self-cordon + drain, timeout) ordered before k3s stop. Every shutdown path — bay button, CLI, master toggle (main doc §4.4) — becomes cluster-aware; face node's master sequence simplifies to "trigger each node's own hook, in reverse order."
- **Theater:** buttons double as per-node boot buttons — press a bay, watch its carrier fade up to cyan.
- **Toddler-class threat model:** recess, don't hold-to-activate (long hold on J2 is *force* off — don't train the dangerous gesture).

## 10. Open questions for CAD session

1. Measure: Pi 5 + X1001 stack height w/ standoffs; SD slot clearance vs carrier plane; XT30 pigtail exit; J2 header position on Pi 5.
2. Swing-arc check: rod spacing vs carrier depth so rear-right corner clears rear-left stack (mockup first — this can kill the concept).
3. Hand/latch clearance at the 30 mm compute pitch; pushrod fallback geometry if cramped.
4. Bead bore fit on 6.35mm rod — coupon 6.4/6.5/6.6mm. (Carrier pivot bore fit confirmed by the v0.3 initial fit test — no longer open.)
5. Bead stack tolerance: measure a 10-bead batch stack height; size the compliant top bead accordingly.
6. Detent engagement depth for PETG finger — coupon 0.3/0.4/0.6mm.
7. Carrier outline: full plate vs skeletal vs acrylic — one of each behind glass with an LED before fleet commit.
8. Rod length + plate pocket depth vs frame interior height; cartridge drop-in clearance.
9. Bay button: recessed panel-mount part that fits a button bead; J2 mating connector part number (1.0mm pitch — verify).
