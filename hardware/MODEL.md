# The parametric model

The rack is generated, not drawn. A suite of Python scripts builds the whole
assembly inside FreeCAD from one set of parameters, and the fabrication files
in the part folders are **exports from that model** rather than hand-authored
drawings.

This does not change the project's rule that [fabrication is specified by
requirement, not by tool](README.md#fabrication-is-specified-by-requirement-not-by-tool).
It sharpens it: the model *is* the requirement now, and the `.svg` and `.stl`
files are the conveniences. Where the two disagree, the model wins and the
export is stale.

## Running it

```
freecadcmd hardware/generate_rack.py
```

writes `complete_rack_assembly.FCStd` next to the script. Every generator also
runs on its own — `freecadcmd hardware/rack/bead_generator.py` and so on —
though the ones that need a board to measure against will say so and stop if
the document has no `Parametric_PCB` in it.

In the GUI, open `generate_rack.py` as a macro. It rebuilds into the existing
document rather than replacing it, so the 3D view keeps its camera across
rebuilds. From the Python console the same thing, re-runnable:

```python
import sys, importlib
sys.path.append("/path/to/aries-28/hardware")
import generate_rack

def reload():
    importlib.reload(generate_rack)
    generate_rack.build_rack_assembly()
```

`generate_rack` reloads every other generator on import, `hardware_utils`
first, so edits to any of them take effect on the next `reload()`.

### A saved .FCStd is not parametric on its own

FreeCAD 1.1 refuses to import a document's proxy modules on restore unless
they come from FreeCAD itself or an installed addon:

```
PropertyPythonObject::Restore: blocked import of module 'rack.bead_generator'.
Only modules from FreeCAD or installed addons are permitted.
```

Reopen `complete_rack_assembly.FCStd` without arranging for that and the parts
keep their shapes but lose their behaviour — change a parameter and nothing
moves. Exposing `hardware/` as a Mod directory fixes it:

```
ln -s /path/to/aries-28/hardware ~/.local/share/FreeCAD/Mod/aries_hardware
```

With that in place the proxies rebind and the saved file is fully live. Without
it, treat the `.FCStd` as a snapshot and re-run the script to change anything.

## What it builds

`generate_rack.py` assembles eight bead bays with boards in the bottom six
(`BAY_COUNT` / `OCCUPIED_BAYS` at the top of the file).

| Generator | Builds |
|---|---|
| `carrier/rpi5_generator.py` | A real Raspberry Pi 5, from its mechanical drawing. **This is the board the rack builds, and the parameter source for everything else.** |
| `carrier/pcb_generator.py` | The old stand-in: a plain 85×56 slab and a block for its ports. Not built by default — see below. |
| `rack/rods_generator.py` | The four support rods, and the rod diameter/gap every other part reads. |
| `rack/rack_plate_generator.py` | The top and bottom plates. |
| `carrier/carrier_plate_generator.py` | The carrier: hook on the left, fork on the right, spacer bosses for the board. |
| `rack/bead_generator.py` | The beads — the printed tubes that set the bay pitch. |
| `hardware_utils.py` | Everything the parts must agree on: rod placement, hole positions, plate proportions, fillet sizes. |
| `carrier/animate_carrier.FCMacro` | Swings one bay's carrier and board out, to check the mechanism. GUI only. |

### The board is a real Pi 5

`carrier/rpi5_generator.py` builds an actual Raspberry Pi 5 — outline, six
holes, connectors, headers and package footprints — from Raspberry Pi Ltd
drawing RP-008347-DS-1, and that is what stands in each bay. It doubles as the
parameter source: it exposes `Width`, `Length`, `Thickness`, `HoleDiameter` and
the four hole offsets under the same names the rest of the model reads, and its
object is named `Parametric_PCB` because that is the name they look a board up
by. Its own holes come from `hardware_utils.mounting_hole_centers()`, the same
call the carrier stands its bosses on, so the two cannot drift apart.

`pcb_generator.py` is the plain slab it replaced. Nothing builds it now, but it
still runs, and step 1 of `generate_rack.py` says how to put it back — worth
keeping for the day a bay has to carry something that is not a Pi.

Modelling the real board is what makes bay clearances answerable, because a Pi
has parts a slab does not: a microSD socket under the laminate, connectors past
three edges, and 15.8mm USB stacks reaching into the bay above. As built, a
seated board clears every one of the rack's other parts — nearest approaches
are 1.5mm from the microSD socket to its own carrier, 3.7mm from a connector to
a rod, 3.8mm to the beads overhead and 6.8mm to the carrier overhead.

Its footprints are the drawing's own vector geometry rather than its printed
callouts, so they carry more decimals than the callouts show, and they agree
with every callout to within 0.01mm. Two things in it are *not* from the
drawing and are marked in the source: the heights of packages the side view
never elevates, and how wide the microSD socket is along y.

The parts are grouped one object per material so the board comes out looking
like a board — green laminate, nickel shells, gold pins, black packages. That
grouping is only for the 3D view; the drawing says nothing about materials.
Since colour is a view property, a `.FCStd` built by `freecadcmd` carries none
until it is opened in the GUI — run `rpi5_generator.apply_colours()` there.

Rod placement lives in `hardware_utils.calculate_rod_centers()` and nowhere
else. Three rods sit tight against the board's footprint; the front-left one is
pushed further out so the carrier's hook clears the rear-left rod as it swings.
That offset is the mechanism — see the docstring for the derivation.

## How the parts depend on each other

Two parts are built as a **master parked off the rack plus a clone in it**,
which looks like indirection until you try to remove it:

- **`Blade_Original`** sits to the +x side, `Blade_BayN` clones in the bays.
- **`Carrier_Original`** sits in front of the rack and is hidden, `Carrier_BayN`
  clones in the bays.

The carrier's split is load-bearing. The beads are carved by the carrier's
solid, while the carrier's seat height comes from the beads' web. Pointed at
one object those two would be a dependency loop and FreeCAD would refuse to
recompute at all. Split, it runs one way:

```
Carrier_Original  ->  Rack_Beads  ->  Carrier_BayN
```

The beads take the master's *profile* and seat it on their own web, so they
never read where the master is parked — move it anywhere and the carve is
unchanged.

**Do not point the bead's `Carrier_Plate` link at a clone**, and do not give
the master a placement that depends on the beads. Either closes the loop.

## The bead

The part that makes a stack a rack. Defaults:

| | |
|---|---|
| Height | 30 mm — this *is* the bay pitch |
| Wall | 2.5 mm |
| Base web | 3 mm, tying the four tubes into one printed part |
| Base discs | two rod diameters across, so the key holes have material round them |
| Keys | 2.4 mm × 1 mm, one per tube |
| Bore | on the nominal rod, no clearance |

Each tube is shaped by what the carrier leaves it. The rear pair are halved
above the base; the front pair are trimmed to a wedge where the carrier passes
and flare back out to a 135° opening at the top. The flare widens the *arc*
rather than thickening the wall, so the tube grips the rod over a growing
circumference instead of a fixed one.

The pivot tube is the fussy one. The carrier swings about it, so the surviving
material is only what the carrier never sweeps through — measured off the
carrier rather than modelled, because the opening is not just the fork slot:
the lead-in tab stops short of the plate edge and the plate itself ends before
the bead's wall does. Every degree of swing costs half a degree of that wedge
on each side, which is why `SwingAngle` is 45° and not more.

Keys stand proud of `Height` and drop into the base of the bead above, so
stacking pitch is unaffected by key height.

## Known gaps

Recorded here rather than in the part READMEs, since they are properties of
the model:

- **The beads clip the board by 0.5 mm.** Clearance needs `Gap >= WallThickness`
  and it is 2.0 against 2.5. The same 0.5 mm limits how far the carrier's rear
  corner can swing before it fouls the front-left bead. Raising `Gap` moves rod
  placement, so it is a real decision, not a tweak.
- **The top plate's key holes are not modelled.** The rods are sized to the
  stack exactly, so the plate lands where the beads end and the topmost bead's
  four keys stand 1 mm into it. The plan is four blind holes in the top plate
  only, drilled by hand rather than cut — see `docs/rack-design.md` §4. Until
  they are added the model shows that interference, and the plate would sit
  1 mm proud in reality.
- **45° is the relief, not a proven extraction.** The beads clear the carrier
  through 45°, but whether the hook clears the left rods far enough to lift the
  carrier away has not been worked out.
- **The transition's side edges are sharp.** They spiral as the wedge widens,
  and a fillet driven along them leaves an invalid solid.
