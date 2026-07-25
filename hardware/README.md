# Hardware

Fabrication files for Aries 28, organized **by part**. Each part has its own folder containing a `README.md` and all of its file-format options side by side. A part may offer several fabrication routes (for example a 3D-printable `.stl` and a laser/CNC `.svg`); these are **options, not competing versions** — the part's README explains which route each file serves and what is decided or open.

## Fabrication is specified by requirement, not by tool

Files here are references. The **requirement** — material, dimensions, tolerances, hole positions — is the specification. Any process that meets it is valid: a CO2 or diode laser, a CNC router, or hand tools (saw and drill press) following the drawing. Where a dimensioned drawing is provided, it is the authority; the `.svg`/`.stl`/`.step` files are conveniences for specific routes.

## Method legend

| Tag | Method | Typical use | Notes |
|---|---|---|---|
| `[PRINT]` | 3D print (FDM) | carriers, mounts, cable management, bezels, spacers | PETG preferred over PLA for heat tolerance and toughness; per-part README notes where this matters |
| `[SHEET]` | Laser / CNC / hand-cut sheet stock | panels, sheet carriers | Flat stock cut to outer dimensions with holes/cutouts at specified coordinates. Large panels cannot be printed (size) and are always sheet stock. Any color acrylic is acceptable; clear/translucent transmits more light, opaque gives contrast |
| `[BUY]` | Off-the-shelf | extrusion, corner brackets, rods, PSU, switch, fans, keystones | Precision or strength items where a commodity part is better than fabricating; prefer an existing standard where one exists |

## Material notes

- **PETG vs. PLA (printed parts):** PLA softens near ~50–60 °C and is brittle; PETG tolerates ~80 °C and flexes before failing. Use PETG for load-bearing parts, parts near the power supply, and any snap/latch feature. PLA is acceptable for test-fit mockups.
- **Acrylic (sheet parts):** any color; the choice is aesthetic and depends on tool access and available materials. Some cutting methods cannot cut some materials (e.g. certain lasers and clear acrylic) — this is a tool constraint, not a design one; follow the dimensions with whatever cuts the chosen stock.
- **The enclosure and any lighting are an optional presentation layer.** A functional cluster does not require the smoked panels, engraving, or LEDs.

## Parts index

| Part | Folder | Purpose | Routes | Status |
|---|---|---|---|---|
| Carrier | [`carrier/`](carrier/) | Holds one SBC; mounts into the rack | `[PRINT]` / `[SHEET]` | SHEET provided (`carrier-rpi-b.svg`, spacers nested); PRINT STL pending |
| Spacer | [`spacer/`](spacer/) | Lifts a board off a sheet carrier | `[SHEET]` / `[PRINT]` | superseded for SHEET route — nested in the carrier SVG; see carrier |
| Rack | [`rack/`](rack/) | Cartridge of bays at one pitch (30 mm or 42 mm) | `[PRINT]` / `[BUY]` | in progress (STL present; pitches set 30/42 mm) |
| Panels | [`panels/`](panels/) | Enclosure walls (show/solid faces) | `[SHEET]` | pending; optional layer |
| Frame | [`frame/`](frame/) | 2020 extrusion skeleton + corners | `[BUY]` | specified (cut plan pending) |
| Power bay | [`power-bay/`](power-bay/) | PSU/fuse/distribution mounting | `[PRINT]` / `[BUY]` | pending |
| Switch mount | [`switch-mount/`](switch-mount/) | Cradle for up to 3 identical switches | `[PRINT]` | pending (no off-the-shelf standard → fabricated) |
| Cable brace | [`cable-brace/`](cable-brace/) | Parallel-run holder + service-loop park | `[PRINT]` | pending |
| Connection panel | [`connection-panel/`](connection-panel/) | External I/O face (inlet, soft-power toggle, Decora) | `[SHEET]` + `[BUY]` | specified (Decora + keystones) |

Statuses are indicative and will change as the build progresses. "Pending" means the requirement is described in the design docs but no fabrication file has been finalized.
