# Part: Switch mount

## Purpose & role
A cradle holding up to three identical 8-port switches in a switch rack on the facilities deck. Because these switches have no off-the-shelf mounting standard, this cradle is fabricated — an example of the 'fabricate only what has no existing standard' principle (contrast the connection panel, which uses off-the-shelf Decora).

## Fabrication route(s)
`[PRINT]` — sized to the specific switch model.

See the fabrication legend in [`../README.md`](../README.md) for method tags and material notes (PETG vs. PLA, acrylic, buy-vs-fabricate).

## Status
Pending. Dimensions follow the chosen switch (TP-Link TL-SG108E in the reference build).

## Dependencies
- Frame / facilities deck — the switch rack mounts low.
- Network design — cascade wiring, see `docs/network-design.md` §5.

## Related documentation
- `docs/design-doc.md` — overall physical design and where this part fits.
- `docs/architecture.md` — the containment hierarchy and stable-interface rule.
