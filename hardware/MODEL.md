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

### The cable combs

Two of them, one per run. Both are rows of clips a cable is pressed into and
stays in, both are eight wide because the bottom bay's comb has to pass every
bay's cable, and both put the face they hang off directly behind every clip so
none of their depth is spent on a wall that is already there. They differ in
what they carry and in how far up the base they reach.

#### Ethernet, off the back of the rear bridge

| | |
|---|---|
| Clips | 8 — one per bay, since the bottom bay's comb passes every bay's cable |
| Bore | 7/32 in (5.556 mm), the cable itself |
| Mouth | 5/32 in (3.969 mm), so the clip wraps 269° and a cable has to be pressed in |
| Between clips | 1/8 in (3.175 mm), and half that outboard of the two end ones |
| Depth | 6 mm proud of the bridge |
| Height | 6 mm — the full thickness of the base, not just the bridge's 3 mm |
| Backing | a beam rod-centre to rod-centre, forward to the line tangent to both rear bores |
| Offset | 15.15 mm from the base's right edge to the right end of the comb |

Each bore is **tangent to the back of the bridge** rather than standing off it,
which is what keeps the comb shallow: the bridge is the back wall of every
clip, so the 6 mm buys the cable plus the horns either side of the mouth and
nothing else. Those horns come out 1.3 mm thick, and everything the cable can
touch is rounded — 0.5 mm on each horn tip and on the barb behind it, 1.0 mm
on the comb's two ends.

The comb stands the **full thickness of the base**, so its clips are as tall as
the bay's landing pads rather than only as tall as the bridge — and standing
that tall, its upper half sits in the band the carrier rides in with only a 3 mm
web under it. So it is backed by a **beam**: rod centre to rod centre, forward
to the line tangent to both rear bores, which is as far in as anything can reach
without eating into a rod. Below the pads that beam is buried in the bridge and
does nothing. Through the pad band it is the root the comb cantilevers off, and
it swallows both rear landing pads on the way, which is what carries the comb's
load into the rest of the base. It also turns the back of the base into a
full-height beam rather than a 3 mm web, which the rack gets for free.

The carrier's own deepest reach is at rest, and it only moves forward as it
swings, so that tangent line keeps one rod radius (3.175 mm) of clearance at the
worst moment.

Six corners come out of all that, and all six are rounded at 1.0 mm:

| Where | |
|---|---|
| Beam into a rear pad | 2 — one per pad, on the inboard side; the beam stops at the rod centres, so the outboard crossings are past its end |
| Comb's left end | 2 — stacked, because the base's outline steps there: the disc reaches furthest back below the pads, the pad above them |
| Comb's right end | 1 — the shoulder where the comb stops and the beam carries on |
| Bridge onto the rear-right disc | 1 — pre-existing, and the shallowest of them at 153° |

Two things had to be got right for those to take at all. They are filleted
**after** the refine, not before: the same fillet that fails on the 240-face
solid the booleans leave takes cleanly on the 130-face one. And the two at the
comb's left end go bottom-first, since rounding the upper one drags the lower a
few hundredths sideways — far enough that looking it up by position afterwards
finds nothing.

The whole row lands on the rear bridge with nothing overhanging. 8 clips need
66.7 mm of the bridge's 78.7 mm, so the offset is what is left after the end
walls: at more than 15.15 mm the row runs off the left end.

#### Power, on the left web

The node's XT30 pigtail is a bonded red/black pair, and it is carried **on
edge** — one lead behind the other rather than side by side. So a clip here is
not a bore but a **stadium**: two wire diameters long, one wide, standing normal
to the web, with the inner circle tangent to the web's face and the outer one
tangent to that in turn. The pair drops in the way it comes off the reel, red
inboard against the web and black outboard behind it.

| | |
|---|---|
| Clips | 8 — one per bay, as on the ethernet comb |
| Wire | 3/32 in (2.381 mm) per conductor |
| Pocket | 2.381 × 4.763 mm — one wire wide, two deep |
| Mouth | 2.143 mm, 90% of the wire, so the lip a lead is pressed past is 0.12 mm |
| Between clips | 1/8 in (3.175 mm), and half that outboard of the two end ones |
| Depth | 6 mm proud of the web, leaving 1.24 mm of horn |
| Height | 3 mm — the web band, and nothing above it |
| Backing | none |
| Position | centred on the web; 44.45 mm of clips on a 72.58 mm face |

Nothing pinches between the two wires — the pocket's waist is its full width.
That is not an oversight: the pair is bonded, so it cannot be separated to be
threaded in a lead at a time, and a waist would only be something to fight.
The mouth is looser than the ethernet comb's 71% for the same reason it can
afford to be: the web is the back wall, these leads are lighter than a patch
cable, and the clip is a keeper rather than a clamp.

**Where the ethernet comb had to be beefed up, this one does not.** The
ethernet comb stands into the band the carrier rides in, which is why it needs
a beam. The power comb never leaves the web, so the web is its backing and the
carrier never sees it — swept a degree at a time through the full 45°, the
comb costs the swing nothing.

The left web runs on the rack's diagonal rather than square to anything, so the
comb is worked in the web's own frame — `u` along the face from the front-left
station towards the rear-left, `v` out of it — and `_at`/`_place` are the only
two things that know the difference. Being centred, it starts at u=14.07, well
clear of the two stations' discs, which only reach past the face for u<2.85 and
u>69.73.

Two corners come out of it, where the comb's ends run back into the face of the
web, and both are rounded at 1.0 mm.

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

#### The rear-right post is not the same part

It carries one **ethernet clip** on its back, so a bay uses three of the plain
post and one of this. Same generator, one flag (`CableClip`), and
`generate_rack.py` keeps two masters and links the RR station to the second.

The post is built with its opening on +x, so its back is −x — and once it is
turned onto the rack's diagonal that back faces 45° out of the rear-right
corner, which is where the run turns out of the base's comb and heads for the
node.

**The clip is revolved about the post's own axis, not extruded off it.** That
is the whole design. A C is drawn in the meridian plane — bore circle, outer
circle, both concentric, the two ends of the C closed off with semicircular
caps — and swept 30° round the post, 15° either side of its back. What comes
out follows the collar instead of being a block stuck onto a cylinder, and it
has no corner on it anywhere: every boundary of the profile is an arc, and the
caps are tangent to both circles by construction, their radius being half the
wall and their centres sitting on the mid-radius.

| | |
|---|---|
| Bore | 7/32 in (5.556 mm), as on the base's comb |
| Mouth | 5/32 in (3.969 mm), opening radially outward |
| Wall | 2.0 mm, which also sets the 1.0 mm cap radius |
| Wrap | 255.7° — the cap angle falls out of the mouth, not the other way round |
| Sweep | 30°, giving 4.4 mm of grip along the cable |
| Height | 0 → 9.56 mm, tangent to the post's bottom face |
| Cost | +115.6 mm³ |

Two things follow from putting the **bore tangent to the post's outer shell**.
The cable rests on the collar; and the C's back wall lies *inside* the collar's
own wall, so the two merge on the fuse and the collar is the back of the clip
for free — the same trick the base's combs play against the bridge and the web.
That is also why `ClipWallThickness` is 2.0 rather than the post's own 2.5: at
2.5 the C's back would land exactly on the rod bore, and the fuse would be two
solids sharing a face. At 2.0 it stops 0.5 mm short of it.

**Nothing is cut from the post.** The channel and its mouth are holes in the
revolved profile, not cuts into the collar, so the clip is purely fused on and
the 225° collar is untouched underneath it.

One consequence of revolving: the channel is an arc, not a straight tube. Over
30° at a centreline radius of 8.45 mm the arc stands 0.29 mm off its own chord,
so the straight-through aperture is about 5.27 mm rather than the bore's 5.556.
A patch lead will take that up — it is a clip, and the squeeze is grip — but a
full-fat 6 mm jacket would want the bore opened by that much.

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
- **The cable runs clip the top and bottom plates by 0.675 mm.** A bore
  tangent to the bridge puts the cable's near edge at y=66.85 and the plates
  reach y=67.525, so each of the eight cables overlaps a plate corner by
  5.0 mm³ where it passes. Only at the two plates — the bays themselves are
  clear — and a cable will deflect round it, but the tidy fix is a shallow
  scallop on the plates' rear edge at the eight clip positions, which is not
  modelled. Moving the comb back 0.7 mm would also do it, at the cost of the
  tangency.
- **The plates cover the power comb outright.** The plates are rectangles on
  the rod bounding box and the left web runs on the rack's diagonal, so the
  plate's left edge sits outboard of the whole comb — the eight lanes are
  3.6 mm under it at the front clip and 19.4 mm at the rear, and even the
  comb's furthest-out corner is 1.38 mm inside the edge. So this one cannot be
  fixed by nibbling the edge the way the ethernet one can; it wants eight
  **slots** through the plate, on the comb's own axis. Only the bottom plate
  actually has to pass anything, since the runs come up from the facilities
  deck and terminate at their bays. Free on a laser, not modelled, and until it
  is the leads have to be dressed round the outside of the bottom plate.
  Backing the comb off is not an alternative here: there is no depth of comb
  that gets clear of a plate that overhangs it by 19 mm.
- **Two posts stand mostly on the carrier, not on their pad.** A post's foot is
  a 225° annulus and the carrier leaves it far less than that to stand on: the
  rear pair land 93–99% on pad, but the front-right is at 32% and the
  front-left at 18%. The rest of each foot rests on the carrier plate, which is
  what captures the carrier — but it also means pulling a carrier out drops the
  stack above onto whatever pad is left. Accepted for now: a post carries only
  the stack's own weight. Whether the foot should be trimmed back to the pad
  has not been decided.
