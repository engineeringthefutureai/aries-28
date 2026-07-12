# Part: Panels

## Purpose & role
The enclosure walls. Optional presentation layer — a functional cluster does not require them. Show faces (front, access side, power-bay side) may use smoked or clear acrylic; solid faces (back, bottom) use opaque stock. Panels surface-mount to the frame with printed clips rather than sliding into the extrusion slot (see design doc §3.3).

## Fabrication route(s)
`[SHEET]` — cut to outer dimensions with openings at specified coordinates. Large panels cannot be printed and are always sheet stock.

See the fabrication legend in [`../README.md`](../README.md) for method tags and material notes (PETG vs. PLA, acrylic, buy-vs-fabricate).

## Status
Pending. Per-panel dimensions follow the finalized frame size. Front panel carries optional engraving.

## Dependencies
- Frame — panels are sized to the assembled frame.
- Connection panel — the rear panel integrates the I/O face (separate part).
- Panel retainer clips (`[PRINT]`) — hold panels to the frame.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
