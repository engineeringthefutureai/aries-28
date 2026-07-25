# Part: Rack

## Purpose & role
An independently-assemblable cartridge of bays at a single pitch, into which carriers mount. The rack is the unit of reconfiguration in the containment hierarchy (see `docs/architecture.md`): its internal pitch can change without affecting the deck it mounts into. Two pitch classes are planned — a dense compute rack and a taller expansion rack for nodes with vertical accessories (storage/AI HATs).

## Fabrication route(s)
Mixed by component: `[SHEET]` (top/bottom plates, laser-cut), `[PRINT]` (spacer/anchor/latch beads), `[BUY]` (stainless rods).

See the fabrication legend in [`../README.md`](../README.md) for method tags and material notes (PETG vs. PLA, acrylic, buy-vs-fabricate).

## Files in this folder
| File | Route | Purpose |
|---|---|---|
| `rack-top-bottom.svg` | `[SHEET]` | Laser-cut top and bottom plates for the rod-and-bead cartridge (`docs/rack-design.md` §4), with the rod holes that seat the four 6.35mm rods. |

Bead files (`[PRINT]`) are pending. `rack-top-bottom.svg` is a single-color, cut-only file (no engrave layer, unlike the carrier) — Shaper Origin–specific metadata from the authoring tool has been stripped, same as `carrier-rpi-b.svg` (see that README's laser-color-convention note).

## Status
In progress. The top/bottom plates moved from a printed STL to the laser-cut `rack-top-bottom.svg` above; the two bay pitches are set — 30 mm (dense/compute) and 42 mm (extended/expansion). See `docs/rack-design.md`.

**Rod-hole placement is a shared interface — critical.** The rod holes in `rack-top-bottom.svg` and the carrier's rod/pivot bores in [`../carrier/carrier-rpi-b.svg`](../carrier/carrier-rpi-b.svg) must agree on rod spacing; they're designed together, not independently, since a carrier that doesn't ride the same four rods as the plates it mounts between can't engage the rack. Any change to one requires checking the other. **Confirmed by an initial fit test:** plywood test-cuts of both files threaded cleanly onto the real 6.35mm rods, three carriers each holding a Pi 5.

**Next milestone — beads.** This fit test only proves the rod-hole interface; it did not use beads, which is where the actual bay pitch (30/42mm spacing between carriers), the swing/latch mechanism, and rack engagement all live (`docs/rack-design.md` §4, §7). Designing and printing the beads, then assembling plates + rods + beads + carriers into one working cartridge, is the next step — not yet done.

## Dependencies
- Carrier — defines the rack-facing interface (rod/bead or slide); shares rod-hole placement with the top/bottom plates (see above).
- Deck — the rack mounts into the facilities/compute deck as a cartridge.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
