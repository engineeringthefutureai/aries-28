# Part: Rack

## Purpose & role
An independently-assemblable cartridge of bays at a single pitch, into which carriers mount. The rack is the unit of reconfiguration in the containment hierarchy (see `docs/architecture.md`): its internal pitch can change without affecting the deck it mounts into. Two pitch classes are planned — a dense compute rack and a taller expansion rack for nodes with vertical accessories (storage/AI HATs).

## Fabrication route(s)
Mixed by component: `[SHEET]` (top/bottom plates, laser-cut), `[PRINT]` (bases and posts, including the anchor and latch variants), `[BUY]` (stainless rods).

See the fabrication legend in [`../README.md`](../README.md) for method tags and material notes (PETG vs. PLA, acrylic, buy-vs-fabricate).

## Files in this folder
| File | Route | Purpose |
|---|---|---|
| `rack-top-bottom.svg` | `[SHEET]` | Laser-cut top and bottom plates for the rod-and-bead cartridge (`docs/rack-design.md` §4), with the rod holes that seat the four 6.35mm rods. |
| `rack-bay-base.stl` | `[PRINT]` | The bay base: four rod stations tied together by three webs, with the carrier riding in the 3mm band above them. PETG. Pitch-independent — the same part serves the 30mm and 42mm racks. |
| `rack-bay-post-30.stl` | `[PRINT]` | The bay post: one of the four collars that fill the rest of a 30mm bay, keyed into the base above so a stack cannot rotate out of register. PETG. Four per bay, all identical. Named for the pitch it sets — the 42mm post is still to come. |
| `bay_base_generator.py`, `bay_post_generator.py` | — | Generators for the two parts above. |
| `rack_plate_generator.py`, `rods_generator.py` | — | Generators for the plates and the rods. |

**All three fabrication files above are exports from the parametric model, not drawings maintained here** — see [`../MODEL.md`](../MODEL.md) for how to run it and re-export. Change the generator, not the `.svg` or the `.stl`.

`rack-top-bottom.svg` is a single-color, cut-only file (no engrave layer, unlike the carrier). It carries no Shaper Origin metadata; it is a plain FreeCAD export whose stroke colour is set to the cut-layer convention described in [`../carrier/README.md`](../carrier/README.md).

## Status
In progress. The top/bottom plates moved from a printed STL to the laser-cut `rack-top-bottom.svg` above; the two bay pitches are set — 30 mm (dense/compute) and 42 mm (extended/expansion). The whole cartridge is now generated (see [`../MODEL.md`](../MODEL.md)), and the pitch is a single parameter: `Rack_Base.BayPitch`. See `docs/rack-design.md`.

**The bead is now two parts.** What used to be one four-tube bead per bay is a **bay base** plus four identical **bay posts**. The base is only the bottom 6 mm — three webs, then a 3 mm band that matches the carrier's thickness — and the carrier rides in that band, resting on the webs and held down by the posts standing on it. Everything above is post. Three things fall out of the split: the base is the same part at every pitch, so only the post has to be reprinted for a 42 mm rack; each post's 225° opening faces the rack's diagonal, which hands the board back the 0.5 mm the old bead clipped off it; and the post being a plain collar retired the swept, flaring tube geometry that made the bead expensive to rebuild.

**A post stands on a landing pad.** A pad is a plain sector of the station's tube — bore, outer wall, two straight radial cuts, four rounded corners. It reaches as far round as the carrier lets it, which is measured rather than carved: cutting the pad to the carrier's actual silhouette gives a crescent tapering to knife points against the rod, with half its corners impossible to fillet. The pads are small on the front pair — a fifth of the annulus at the front-left, a third at the front-right — with the rest of each post's foot resting on the carrier plate itself. That is deliberate: it is what traps the carrier vertically, and a post carries only grams.

**Rod-hole placement is a shared interface — critical.** The rod holes in the plates and the carrier's rod/pivot bores must agree on rod spacing; a carrier that doesn't ride the same four rods as the plates it mounts between can't engage the rack. That agreement is now structural rather than a matter of care: both come from `calculate_rod_centers()` in the model, so the two cannot drift apart. Any change to rod placement is a change to that one function.

**The earlier fit test no longer certifies these files.** Plywood test-cuts of the *previous* SVG pair threaded cleanly onto the real 6.35mm rods, three carriers each holding a Pi 5 — that proved the rod-hole interface as it stood then. The model was not built to reproduce that geometry (its rod gap and front-left rod position both differ), and both files have since been re-exported from it. The interface is self-consistent, but the current geometry is unproven in plywood.

**Next milestone — assembly.** The bay base and bay post now exist and print: together they set the bay pitch, key into each other, and the base is relieved for the carrier's swing. What has not happened is putting plates + rods + bases + posts + carriers together into one working cartridge and confirming a carrier actually swings out of a populated rack. Known gaps that will bite there — the top plate's four blind key holes not yet being modelled, how much of each post's foot lands on the carrier rather than on its landing pad, and whether 45° of swing is enough to extract a carrier at all — are listed in [`../MODEL.md`](../MODEL.md#known-gaps).

**The top plate needs four holes that are not in the SVG.** The topmost bay's posts key into the top plate, and those holes are blind — a laser cuts through, and a through-hole would show on the rack's outside face — so they are drilled by hand after cutting. `rack-top-bottom.svg` is one file for both plates and deliberately does not carry them. See `docs/rack-design.md` §4.

## Dependencies
- Carrier — defines the rack-facing interface (rod/bead or slide); shares rod-hole placement with the top/bottom plates (see above).
- Deck — the rack mounts into the facilities/compute deck as a cartridge.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
