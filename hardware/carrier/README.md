# Part: Carrier (board holder)

The carrier is the standardized tray that holds one single-board computer and mounts it into the rack. It is the core interchangeability element of the whole machine: **the rack interfaces only with the carrier, never with the board directly**, so any board — a Raspberry Pi 4, a Pi 5, or a different SBC entirely — can occupy any bay as long as it sits on a compatible carrier.

---

## Purpose & role

- Holds one SBC on standoffs/spacers, lifting it off the carrier for airflow and connector clearance.
- Presents a **single, standard mechanical interface to the rack** (the rod/bead engagement or slide, depending on rack variant) regardless of what board is on it.
- Carries per-node identification (engraved node name/number) and, in the styled build, decorative engraving that doubles as edge-lit lighting.
- Makes a node a **field-replaceable unit**: to service or swap a node, you handle its carrier, not loose boards and cables.

## Design status

- **Geometry / interface:** the rack-facing geometry is the fixed spec. Do not change it per board — that is what keeps bays interchangeable.
- **Board mounting pattern:** varies by board (hole spacing differs between SBCs). This is the *only* part of the carrier that changes between board types; the outer/rack interface stays constant.
- **Fabrication method:** intentionally left as an option — see below.

## Interchangeability

The carrier is what makes future upgrades and expansion possible without rebuilding the machine:

- **Same bay, any board.** Because the rack sees only the carrier, a newer or different board can replace an older one in the same bay. Empty bays can be populated later.
- **Accommodates slightly different board shapes.** The carrier is designed with enough margin to hold boards whose outlines differ modestly; substantially larger boards may need a carrier variant and possibly a bay-pitch adjustment (the rack architecture is designed to absorb this rather than require a rebuild).
- **Board-specific detail lives here, not in the rack.** Hole pattern and any board-specific clearance are properties of the carrier; the cabling absorbs connector-position differences separately (see the cable-management part).

---

## Fabrication — options, not a ranking

The carrier can be made by more than one method. Pick per your tools, materials, and preference; neither is "the final" version.

| Route | Process | Material | Notes |
|---|---|---|---|
| **Printed** | 3D print (FDM) | **PETG** | Integrates standoffs/bosses directly (no separate spacers). Tougher and more heat-tolerant than PLA — see material note. Best when you want an all-in-one part. STL pending (see below). |
| **Sheet-cut** | Laser (or CNC, or careful hand-cutting + drill) | **Acrylic**, any color, ~3 mm | Flat plate; the spacers needed for vertical isolation are **nested in the same laser file**, cut from the plate's own cutout waste rather than a separately-designed part — see `carrier-rpi-b.svg`. Clear/translucent acrylic transmits light for edge-lit effects; opaque gives contrast. |

**Requirement, not tool.** What the carrier needs is a flat, rigid plate of the specified outer geometry with the board's mounting holes at the correct coordinates and the rack-interface features accurate. Any process that achieves that — FDM printer, CO2 or diode laser, CNC router, or a saw and a drill press following the drawing — is valid. The provided `.svg` / `.stl` / `.step` files are references for those routes; the dimensioned drawing is the actual spec.

### Material note — PETG vs. PLA (printed route)

Use **PETG**, not PLA, for the printed carrier:
- **Heat:** PLA softens (~50–60 °C) and can creep under sustained load or warmth; carriers may sit near the power bay or in a warm environment. PETG tolerates ~80 °C.
- **Toughness:** PLA is brittle and can crack at thin sections or retention features; PETG flexes before failing, which matters for any snap/latch geometry and for a part that is handled during service.
- PLA is fine for **test-fit mockups** — print a cheap PLA carrier first to check board fit and rack engagement, then commit the real part in PETG.

### Material note — acrylic (sheet route)

- Any color works; the choice is aesthetic and depends on tool access and material on hand. Clear/translucent gives more light transmission and edge-lit highlights; opaque/black gives contrast and hides what is behind it.
- Sheet carriers need spacers to lift the board off the plate for vertical isolation; `carrier-rpi-b.svg` cuts these from the carrier's own cutout waste in the same laser pass — see the spacer part for the rationale, though the standalone spacer design there is superseded for this route.
- Some tools cannot cut some materials (e.g. certain lasers vs. clear acrylic); this is a *tool* constraint, not a design one. Follow the dimensions with whatever cuts your chosen stock.

---

## Files in this folder

*(Populated as the design is finalized — filenames indicative.)*

| File | Route | Purpose |
|---|---|---|
| `carrier-rpi-b.svg` | `[SHEET]` | Laser-cut carrier for the Pi 3B/4B/5 shared footprint. Its rod/pivot bores share rod-hole placement with [`../rack/rack-top-bottom.svg`](../rack/rack-top-bottom.svg); both come from the same function in the model, so they cannot drift apart. Nests the vertical-isolation spacers as cutouts within the same file — one laser pass produces the carrier plate and its spacers together, no separate spacer part to cut. |
| `carrier_plate_generator.py` | — | Generator for the carrier: hook on the left, fork on the right, spacer bosses for the board. |
| `pcb_generator.py` | — | The board and its port block — **the parameter source for the whole model**. Board size, hole spacing and hole diameter are set here and everything else follows. |
| `animate_carrier.FCMacro` | — | Swings one bay's carrier and board out of the rack, to check the mechanism. FreeCAD GUI only; `BAY` picks which bay. |

**`carrier-rpi-b.svg` is an export from the parametric model, not a drawing maintained here** — see [`../MODEL.md`](../MODEL.md). Change the generator and re-export; edits made directly to the SVG will be lost.

Printed (`[PRINT]`) route: STL pending. The model already builds the spacers as bosses integrated into the plate rather than separate pieces, which is what the printed part wants — the sheet route's nested cutouts are the adaptation, not the other way round.

The board's mounting pattern follows the Pi 3B/4B/5 footprint: M2.5 holes on 58 × 49mm, 3.5mm in from each edge of an 85 × 56mm board. Those are `pcb_generator.py`'s defaults; a different board is a different set of numbers there, not a different carrier design.

### Laser color convention (cut vs. engrave)

`carrier-rpi-b.svg` uses stroke **color** to separate the two operations it contains, since that's what both LightBurn and Creality Studio use to auto-split an imported SVG into independently-assignable layers — neither program reads a "cut this, engrave that" flag from the file itself:
- **Gray `#7F7F7F`, unfilled hairline** — outer profile, mounting holes, and the nested spacer cutouts. Assign this layer to **Cut**.
- **Blue `#0000FF`, unfilled** — the Aries glyph. Assign this layer to **Line/engrave the contour** (trace the outline, not a filled-region Scan/Fill). Unfilled on purpose — it's a contour engrave, not a solid-fill one.

Each program only auto-*groups* paths by color; you still assign Cut vs. Engrave to each color-layer once inside the software. In LightBurn that assignment persists across re-imports of an updated SVG as long as the colors stay consistent, so this is a one-time setup per color, not per re-export.

The file has repeatedly carried Shaper Origin–specific metadata (`xmlns:shaper` namespace, `shaper:cutType`/`cutOffset`/`toolDia` on every path) picked up from passing through that tool. It is stripped whenever it reappears — consistent with the project's "fabrication by requirement, not by tool" approach (`../README.md`) — so the file does not assume a specific machine. Worth checking after any round-trip through Shaper.

Note: these are current working files, not final released parts. The bay pitches are set at 30 mm (standard) / 42 mm (extended).

**The earlier fit test does not cover this file.** Three plywood carrier plates threaded onto the real 6.35mm rods alongside the plates, each carrying a Pi 5 — that passed, and validated the rod-hole interface *as it stood then*. The parametric model was not built to reproduce that geometry, and this SVG has since been re-exported from it, so the rod placement is no longer the placement that was tested. Carrier and plates still agree with each other by construction (both read `calculate_rod_centers()`), but the pair is unproven in plywood. A dimensioned reference drawing will be added as the design is finalized.

Beads now exist and print — see [`../rack/README.md`](../rack/README.md). Assembling carrier + plates + beads + rods into one working cartridge, and confirming a carrier swings out of a populated rack, is the outstanding milestone.

Board variants are named by **hole-pattern group**, not by individual board, since the Pi 3B/4B/5 share one 85×56mm footprint and M2.5 holes on 58×49mm — one carrier fits all three (`design-doc.md` §3.2):
- `carrier-rpi-b.*` — Pi 3B / 4B / 5 (shared footprint)
- `carrier-rpi-a.*` — Pi 3A+ (65×56mm, same hole spacing, shorter)
- extensible: `carrier-<board>.*` for any additional board type whose hole pattern doesn't match an existing group

All variants share the same rack-facing interface; only the mounting-hole pattern changes between groups.

---

## Dependencies

- **Spacers** (sheet-cut route only) — lift the board off the plate for vertical isolation; nested directly in `carrier-rpi-b.svg` rather than a separate file. See the spacer part for the general rationale.
- **Rack** — defines the carrier's rack-interface geometry (rod/bead or slide). See the rack design doc.
- **Cable management** — connector-position differences between boards are absorbed by adjustable-slack cabling, not by the carrier. See the cable-management part.

## Related documentation

- `docs/rack-design.md` — the rack the carrier mounts into, and the mounting-mechanism options.
- `docs/design-doc.md` — overall physical design, bay pitch, board fleet, and where carriers sit in the build.
