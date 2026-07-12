# Part: Rack

## Purpose & role
An independently-assemblable cartridge of bays at a single pitch, into which carriers mount. The rack is the unit of reconfiguration in the containment hierarchy (see `docs/architecture.md`): its internal pitch can change without affecting the deck it mounts into. Two pitch classes are planned — a dense compute rack and a taller expansion rack for nodes with vertical accessories (storage/AI HATs).

## Fabrication route(s)
`[PRINT]` (rods/beads/plates), with bought rods where appropriate.

See the fabrication legend in [`../README.md`](../README.md) for method tags and material notes (PETG vs. PLA, acrylic, buy-vs-fabricate).

## Status
In progress. An STL is present (`rack.stl`); the two bay pitches are set — 30 mm (dense/compute) and 42 mm (extended/expansion). Final interface fit is pending caliper confirmation against assembled hardware. See `docs/rack-design.md`.

## Dependencies
- Carrier — defines the rack-facing interface (rod/bead or slide).
- Deck — the rack mounts into the facilities/compute deck as a cartridge.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
