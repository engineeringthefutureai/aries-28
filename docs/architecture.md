# Aries 28 — Physical Architecture: Hierarchical Reconfigurability

**The organizing principle of the entire physical design. Every mechanical decision refers back to this.**
Version 1.0 — July 2026

---

## 1. The idea

Aries 28 is decomposed into a strict containment hierarchy, where **each level absorbs a class of change so that change does not propagate upward.** The blast radius of any modification is bounded to exactly one unit at one level. This is the same principle as good software modularity — encapsulation behind stable interfaces — expressed in aluminum and acrylic.

The goal is a machine that never needs to be *rebuilt*, only *reconfigured locally* — and where the effort of any given change is proportional to how deep in the hierarchy it reaches. Routine changes touch the bottom of the hierarchy and are trivial; only radical, unforeseeable changes reach the top, and the design is built so that they almost never need to.

---

## 2. The hierarchy

| Level | Unit | Contains | What it is | Stable interface it presents upward |
|---|---|---|---|---|
| 0 | **System** | decks | The whole box: frame, panels, all contents | Its footprint / place on the shelf |
| 1 | **Deck** | racks *or* facilities gear | A horizontal sub-box within the system (e.g. facilities deck, compute deck) | A standard footprint mounting to the system frame |
| 2 | **Rack** | bays | An independently-assemblable cartridge of bays at one pitch | A standard cartridge mount to its deck |
| 3 | **Bay** | one carrier | A single slot at a defined pitch within a rack | A standard carrier interface (rod/bead or slide) |
| 4 | **Carrier** | one board | The tray holding one single-board computer | A standard mechanical face to the bay |
| (5) | **Board** | — | The compute unit itself | Its mounting-hole pattern + connectors |

Real data centers use the same shape: room → row → rack → shelf/U → server. Aries 28 is that logic scaled to a desktop: **system → deck → rack → bay → carrier → board.**

---

## 3. Bounded reconfiguration — change stops at its level

Each level is the unit of a particular kind of change. A change enters at the lowest level that can contain it and does not disturb anything above.

| Change | Enters at | Blast radius | Cost | Frequency |
|---|---|---|---|---|
| Reflash / replace a node with the same board type | **Carrier / Bay** | one node | trivial | routine |
| Swap a board for a different type that fits the pitch | **Bay** | one node (+ a carrier variant) | trivial | occasional |
| New board class needs a different pitch/size | **Rack** | one rack (re-bead or rebuild the cartridge; remount affected nodes) | moderate | rare |
| Add capacity of an existing class | **Rack** | add a rack cartridge, or populate empty bays | low–moderate | as needed |
| Facilities change (second switch, gateway/registry node, PSU) | **Deck** | one deck | moderate | rare |
| Fundamental redesign | **System** | the machine | rebuild | designed to be unnecessary |

**The load-bearing example — unforeseeable future hardware:** some future single-board computer beats the current fleet but is physically larger. This does *not* require rebuilding the tower. It enters at the **rack** level: add a new rack cartridge sized for it, or reconfigure an underutilized existing rack to the new pitch and remount both new and old nodes onto carriers for that rack. This is more work than a node swap, but *bounded* work: the remaining racks and the entire facilities deck are untouched and continue running. The future board cannot be predicted, but the change can be guaranteed to stay local.

---

## 4. Stable interfaces — the rule that makes it work

Bounded reconfiguration only holds if **each level presents a stable interface to the level above, independent of its own internals.** This is the encapsulation rule, and it is the single most important constraint in the physical design:

- A **carrier** presents a standard face to the bay — so the board on it can be anything (different SBC, different generation, different hole pattern) without the bay caring.
- A **bay** presents a standard carrier interface — so what a carrier holds is irrelevant to the rack.
- A **rack** presents a standard cartridge mount to its deck — so a rack's internal pitch/size can change without the deck caring.
- A **deck** presents a standard footprint to the system frame — so a deck's contents (compute vs. facilities) are irrelevant to the box.

As long as each interface is held constant, the internals of any level are free to change. Breaking an interface — making the rack mount depend on bay pitch, or the bay depend on board type — causes change to leak across boundaries, which returns the system to requiring a full rebuild for any modification. Every part should be designed to keep its upward interface constant.

---

## 5. The deck layer (current plan)

The system is split vertically into zones. Heavy, static power infrastructure low; reconfigurable compute in the middle; network switching high, so patch cables drop down to the carriers below — matching each element's role to its tier.

- **Power deck (bottom, full footprint):** PSU, fuse block / distribution, ground bus. Kept low for stability and serviceability; displayed as a feature through the panels.
- **Compute deck(s) (middle):** one or more rack cartridges — the node bays, which also hold facilities-role boards that occupy a bay like any other node (e.g. the gateway), even though such a board's *software* role sits outside k3s.
- **Network deck (top):** switch(es) — one now, a second and third cascaded later — the "top-of-rack" analog, patch cables dropping to the carriers below. Room for an optional additional facilities node (e.g. a self-hosted registry).

## 6. The rack layer (current plan)

Racks are independent cartridges, each at a single bay pitch, sized to a **class** of node. Interchangeability is guaranteed *within* a class, not forced *across* classes — which is what lets different node shapes coexist without a single compromise pitch.

- **Compute rack — dense pitch (30 mm):** bare/diskless nodes (compute + network only). Most of the fleet. Tight because there is nothing stacked to heat-soak; the small gap is adequate airflow for a cooled bare board.
- **Expansion rack — tall pitch (42 mm):** nodes with vertical accessories — NVMe storage HATs, AI accelerators, or future add-ons. Fewer bays, generous height each (which also means generous airflow). Sized from the current ~34 mm Pi-5-plus-SSD stack plus headroom for taller HATs and future options.

Two pitches means two bead sizes (rod-and-bead rack) — a one-time design cost, not a per-change one. Each rack remains an independently-assemblable cartridge: build and wire it on the bench, drop it into its deck as a unit, and reconfigure it later without disturbing its neighbors.

## 7. The bay & carrier layers

Covered in detail in the rack design doc and the carrier part README. In short:
- A **bay** is one pitch-slot presenting the standard carrier interface.
- A **carrier** is the standardized tray that makes a node a field-replaceable unit and holds the board-specific detail (hole pattern), so the board type never propagates up to the bay.

---

## 8. Why this matters (and why it's worth the extra fabrication)

Uniform-everything would be simpler to build but would either waste space (one tall pitch for all) or force compromises (one medium pitch that serves nothing well). Fully bespoke would pack tightest but make every change a rebuild. Hierarchical reconfigurability is the middle path that real infrastructure converges on: **standardize interfaces, vary internals, bound every change to one level.**

The cost is a modest, one-time design variety (two rack pitches, a few carrier variants). The benefit is durable: the machine grows, upgrades, and adapts to hardware that does not yet exist, and every such change is a bounded, local operation rather than a teardown. It functions at every stage and continues to function as it changes.

*This is the conceptual spine of the build. When in doubt about a physical decision, ask: which level does this belong to, and does it keep that level's upward interface constant?*
