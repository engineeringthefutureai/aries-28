# Part: Connection panel

## Purpose & role
The single external-facing I/O face. Fixed cuts: IEC C14 power inlet (with switch/fuse), a recessed soft-power toggle (the DPST toggle from `docs/design-doc.md` §4.4 — a maintained-position switch, not a momentary button), and one standard Decora opening. Comms use off-the-shelf Decora + keystone inserts (RJ45 for WAN and MAINT, optional USB console, blanks) rather than custom-printed sub-panels — an existing modular standard is preferred where one exists. Only the acrylic cutout is fabricated.

## Fabrication route(s)
`[SHEET]` (acrylic cutout to the standard Decora opening dimensions) + `[BUY]` (Decora frame, keystones, IEC inlet, toggle).

See the fabrication legend in [`../README.md`](../README.md) for method tags and material notes (PETG vs. PLA, acrylic, buy-vs-fabricate).

## Status
Specified. See `docs/network-design.md` §8 and `docs/dns-and-exposure.md`.

## Dependencies
- Frame — the panel occupies a rear face opening.
- Network design — WAN/MAINT keystone assignment.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
