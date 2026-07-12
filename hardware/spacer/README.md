# Part: Spacer

## Purpose & role
Lifts a single-board computer off a flat sheet carrier, providing airflow beneath the board and clearance for bottom-side components and connectors. Required only for the sheet-cut carrier route; the printed carrier integrates equivalent standoff bosses and needs no separate spacer.

## Fabrication route(s)
`[SHEET]` (cut from the same stock as the carrier) or `[PRINT]`.

See the fabrication legend in [`../README.md`](../README.md) for method tags and material notes (PETG vs. PLA, acrylic, buy-vs-fabricate).

## Status
Pending. Dimensions follow the board mounting-hole pattern and the required standoff height (see the design doc).

## Dependencies
- Carrier (sheet route) — the spacer sits between board and carrier.
- Board mounting-hole pattern — determines spacer hole positions.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
