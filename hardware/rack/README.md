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

Bead files (`[PRINT]`) are pending.

## Status
In progress. The top/bottom plates moved from a printed STL to the laser-cut `rack-top-bottom.svg` above; the two bay pitches are set — 30 mm (dense/compute) and 42 mm (extended/expansion). Final interface fit is pending caliper confirmation against assembled hardware. See `docs/rack-design.md`.

**Rod-hole placement is a shared interface — critical.** The rod holes in `rack-top-bottom.svg` and the carrier's rod/pivot bores in [`../carrier/carrier-rpi-b.svg`](../carrier/carrier-rpi-b.svg) must agree on rod spacing; they're designed together, not independently, since a carrier that doesn't ride the same four rods as the plates it mounts between can't engage the rack. Any change to one requires checking the other.

## Dependencies
- Carrier — defines the rack-facing interface (rod/bead or slide); shares rod-hole placement with the top/bottom plates (see above).
- Deck — the rack mounts into the facilities/compute deck as a cartridge.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
