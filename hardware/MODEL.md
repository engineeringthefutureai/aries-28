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
runs on its own — `freecadcmd hardware/rack/bay_base_generator.py` and so on —
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
PropertyPythonObject::Restore: blocked import of module 'rack.bay_base_generator'.
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

`generate_rack.py` assembles eight bays with boards in the bottom six
(`BAY_COUNT` / `OCCUPIED_BAYS` at the top of the file).

| Generator | Builds |
|---|---|
| `carrier/rpi5_generator.py` | A real Raspberry Pi 5, from its mechanical drawing. **This is the board the rack builds, and the parameter source for everything else.** |
| `carrier/pcb_generator.py` | The old stand-in: a plain 85×56 slab and a block for its ports. Not built by default — see below. |
| `rack/rods_generator.py` | The four support rods, and the rod diameter/gap every other part reads. |
| `rack/rack_plate_generator.py` | The top and bottom plates. |
| `carrier/carrier_plate_generator.py` | The carrier: hook on the left, fork on the right, spacer bosses for the board. |
| `rack/bay_base_generator.py` | The bay base — the bridged bottom of a bay, and the part the carrier rides in. |
| `rack/bay_post_generator.py` | The bay post — one of the four collars that fill the rest of a bay. |
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
are 1.0mm from a connector to a post, 1.5mm from the microSD socket to its own
carrier, 3.7mm from a connector to a rod, 3.8mm to the base overhead and 6.8mm
to the carrier overhead.

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

A third master is parked but never used in place for a different reason:

- **`Bay_Post_Original`** sits in front of the rack and is hidden; four
  `Bay_Post_BayN_*` clones stand in each bay.

The carrier's split is load-bearing. The bay base is carved by the carrier's
solid, while the carrier's seat height comes from the base's web. Pointed at
one object those two would be a dependency loop and FreeCAD would refuse to
recompute at all. Split, it runs one way:

```
Carrier_Original  ->  Bay_Base  ->  Carrier_BayN
                             \->  Bay_Post  ->  Bay_Post_BayN_*
```

The base takes the master's *profile* and seats it on its own web, so it never
reads where the master is parked — move it anywhere and the carve is unchanged.

**Do not point the base's `Carrier_Plate` link at a clone**, and do not give
the master a placement that depends on the base. Either closes the loop.

Everything flows outward from `Bay_Base`, and that is deliberate: the post
takes its height, wall, bore clearance and key size from the base by
expression, because those are exactly the numbers the two parts have to agree
on for a key to drop into its hole. The post never feeds anything back.

Post *placement* is parametric too. `Bay_Base` publishes its four rod centres
as a read-only `RodCenters` property and each post clone reads its own off it
(`Bay_Base.RodCenters[2].x`), so moving the rods moves the posts. Only the
rotation is written out, since which way a post faces is a design constant and
not something the board size can change.

## The bay base and the bay post

A bay is one base plus four posts. Splitting them is what lets the whole thing
be simple: the base is the part with all the geometry in it, and it is only
6 mm tall; the post is a plain collar, and it is the only part that changes
with the pitch.

**Bay base** — the bridged bottom of a bay:

| | |
|---|---|
| Bay pitch | 30 mm — the base plus one post; the number the rack is specified by |
| Webs | 3 mm, tying the four rod stations into one printed part |
| Landing pads | 3 mm tall, set from the carrier's own thickness |
| Pad relief | 2° trimmed off each end of the measured opening |
| Discs | two rod diameters across, so the key holes have material round them |
| Key holes | 2.4 mm × 1 mm, blind, one per station |
| Wall | 2.5 mm |
| Bore | on the nominal rod, no clearance |

The carrier rides in the pad band, resting on the webs and captured from above
by the posts' feet. The webs and the discs are untouched by any of this — the
carrier is above them, and nothing is ever cut with the carrier's solid at all.

A **landing pad** stands at each station in that band, and it is what a bay
post stands on. A pad is a plain sector of the tube: bore, outer wall, two
straight radial cuts, four rounded corners — 1.0 mm against the outer wall,
0.5 mm against the bore.

It is deliberately **not** the shape the carrier leaves. Cutting the pad to the
carrier's own silhouette is the obvious thing to do and it is a trap: the
carrier's outline is all fillet arcs and its fork slots run tangent to the rod,
so the pad comes out a crescent that tapers to knife points against the bore
with nothing on it a rolling ball can round. Half the corners then cannot be
filleted at all, and a fillet forced into one of the tangent points runs away
along the feather and eats most of the pad.

So the carrier is **measured, not cut with**. `_clear_arc` samples how far round
the station the carrier is absent — through the wall, at three radii — and the
pad is that arc less `PadRelief` off each end. At the pivot the whole
`SwingAngle` comes off the leading end as well, since the carrier has to sweep
out through there. What that gives up is a little area; what it buys is a shape
that is trivial to build, to fillet, to print and to think about.

The base does **not** change with the pitch, so there is one `rack-bay-base.stl`
for both the 30 mm and the 42 mm rack.

**Bay post** — one of the four collars above it:

| | |
|---|---|
| Height | 24 mm — the pitch less the base, so this is what a pitch change moves |
| Wrap | 225° round the rod |
| Wall | 2.5 mm |
| Key | 2.4 mm × 1 mm stub on top, one per post |
| Bore | on the nominal rod, no clearance |

All four posts in a bay are the same part; only the rotation differs. Each
turns its opening onto the rack's diagonal, which does two things: the wall
wraps the outside of the stack rather than the board side, and wrapping more
than half the rod means a post clips on instead of being threaded over the end
of one. The key stands proud of `Height` and drops into the base above, so the
pitch is unaffected by how tall it is.

That opening is what retired the old bead's board clip: where the bead's full
tube overhung the board by 0.5 mm, a post's nearest wall stands 1.0 mm off it.

## Known gaps

Recorded here rather than in the part READMEs, since they are properties of
the model:

- **The top plate's key holes are not modelled.** The rods are sized to the
  stack exactly, so the plate lands where the posts end and the topmost bay's
  four keys stand 1 mm into it. The plan is four blind holes in the top plate
  only, drilled by hand rather than cut — see `docs/rack-design.md` §4. Until
  they are added the model shows that interference, and the plate would sit
  1 mm proud in reality.
- **45° is the relief, not a proven extraction.** Swept a degree at a time
  through 45°, the carrier and its board clear every pad and every post with
  nothing touching — but whether the hook clears the left rods far enough to
  then lift the carrier away has not been worked out.
- **Two posts stand mostly on the carrier, not on their pad.** A post's foot is
  a 225° annulus and the carrier leaves it far less than that to stand on: the
  rear pair land 93–99% on pad, but the front-right is at 32% and the
  front-left at 18%. The rest of each foot rests on the carrier plate, which is
  what captures the carrier — but it also means pulling a carrier out drops the
  stack above onto whatever pad is left. Accepted for now: a post carries only
  the stack's own weight. Whether the foot should be trimmed back to the pad
  has not been decided.
