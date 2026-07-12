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
| **Printed** | 3D print (FDM) | **PETG** | Can integrate standoffs/bosses directly (no separate spacers). Tougher and more heat-tolerant than PLA — see material note. Best when you want an all-in-one part. |
| **Sheet-cut** | Laser or CNC (or careful hand-cutting + drill) | **Acrylic**, any color, ~3 mm | Flat plate; requires **separate spacers** (see the spacer part) to lift the board. Clear/translucent acrylic transmits light for edge-lit effects; opaque gives contrast. |

**Requirement, not tool.** What the carrier needs is a flat, rigid plate of the specified outer geometry with the board's mounting holes at the correct coordinates and the rack-interface features accurate. Any process that achieves that — FDM printer, CO2 or diode laser, CNC router, or a saw and a drill press following the drawing — is valid. The provided `.svg` / `.stl` / `.step` files are references for those routes; the dimensioned drawing is the actual spec.

### Material note — PETG vs. PLA (printed route)

Use **PETG**, not PLA, for the printed carrier:
- **Heat:** PLA softens (~50–60 °C) and can creep under sustained load or warmth; carriers may sit near the power bay or in a warm environment. PETG tolerates ~80 °C.
- **Toughness:** PLA is brittle and can crack at thin sections or retention features; PETG flexes before failing, which matters for any snap/latch geometry and for a part that is handled during service.
- PLA is fine for **test-fit mockups** — print a cheap PLA carrier first to check board fit and rack engagement, then commit the real part in PETG.

### Material note — acrylic (sheet route)

- Any color works; the choice is aesthetic and depends on tool access and material on hand. Clear/translucent gives more light transmission and edge-lit highlights; opaque/black gives contrast and hides what is behind it.
- Sheet carriers need **separate spacers** to lift the board off the plate — see the spacer part.
- Some tools cannot cut some materials (e.g. certain lasers vs. clear acrylic); this is a *tool* constraint, not a design one. Follow the dimensions with whatever cuts your chosen stock.

---

## Files in this folder

*(Populated as the design is finalized — filenames indicative.)*

| File | Route | Purpose |
|---|---|---|
| `carrier-holder.stl` | `[PRINT]` | Printable holder (PETG) with integrated standoff bosses and vent — the print route, no separate spacers needed. |
| `carrier-holder-source.svg` | source | The 2D source profile the holder was modeled from. |

Note: these are current working files, not final released parts. Bay-pitch and interface dimensions are pending caliper confirmation (see the rack design doc). A dimensioned reference drawing will be added as the design is finalized.

Board variants (different hole patterns) are named by board, e.g. `carrier-rpi5.*`, `carrier-rpi4.*` — identical rack interface, different mounting holes.

---

## Dependencies

- **Spacers** (sheet-cut route only) — lift the board off the plate. See the spacer part.
- **Rack** — defines the carrier's rack-interface geometry (rod/bead or slide). See the rack design doc.
- **Cable management** — connector-position differences between boards are absorbed by adjustable-slack cabling, not by the carrier. See the cable-management part.

## Related documentation

- `docs/rack-design.md` — the rack the carrier mounts into, and the mounting-mechanism options.
- `docs/design-doc.md` — overall physical design, bay pitch, board fleet, and where carriers sit in the build.
