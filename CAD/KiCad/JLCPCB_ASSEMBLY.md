# JLCPCB fabrication and SMD assembly

Each of the seven production PCBs has a complete package in
`production/assembly/<board>/<board>-manufacturing.zip`. The home page's
**fabrication + SMD BOM/CPL** link serves this package. **Download all
production packages** collects the seven packages. The separate bare-board
Gerber download addresses redirect to the same checked production packages.

Unpack a board's manufacturing ZIP, then upload:

1. `gerbers.zip` for PCB fabrication, including paste layers.
2. `BOM.csv` for assembly: one row per reference, with quantity per PCB,
   package, manufacturer, exact orderable MPN and LCSC part number.
3. `CPL.csv` for the matching references' position in mm, Top side and CCW
   rotation in degrees. Coordinates share the Gerbers' absolute origin.

JLCPCB places the discrete SMD electronics, including the voice-card R3.
Fit through-hole components, existing modules, sockets and mounting hardware
by hand. `manual-and-DNP.csv` accounts for every excluded reference.
The analyser carrier has no SMD parts: its BOM and CPL contain headers only;
order that PCB bare.

The backplane has 72 placements, adapter 65, voice card 0, microphone-flex 6,
female base 4 and male static 4, per board. Quantities of boards are separate
order choices. Pitch-dependent voice-card components remain through-hole and
are described by the enclosed variant BOMs.

The exact part choices are in `assembly-parts.json`. In particular, C0G filter
capacitors remain C0G, and the SMD electrolytic body dimensions and polarity
are specified. The backplane's provisional 10K calibration resistors and
body boards' provisional 220uF reservoirs retain their circuit values; selecting
exact MPNs does not establish their hardware performance.

Check current JLCPCB availability and the assembly preview before placing an
order. Verify pin 1, diode/LED cathodes and electrolytic polarity against
`reference/assembly-top.svg`. The silkscreen prints `+` and `-` beside the
pads of every LED, diode and electrolytic (`mark_polarity.py`), so the preview
and a fitted board can both be checked by eye. The CPL applies the exact-part
rotation offsets in the part table. If a selected part is unavailable,
update the reviewed part table and regenerate; do not silently substitute.

RA1 and RA2 on each backplane use two 160 ohm, 0603, 1%, 0.1 W resistors.
The selected part is now UNI-ROYAL 0603WAF1600T5E
([C22814](https://jlcpcb.com/partdetail/23541-0603WAF1600T5E/C22814)), replacing
the short-stock YAGEO C185369. Its specifications match: 160 ohm, 0603, 1%,
0.1 W, 75 V, +/-100 ppm/degree C. JLCPCB's public listing retrieved on
2026-10-22 reported 41,635 overseas stock; confirm availability for the order
quantity and assembly attrition in JLC's BOM matching page before payment;
stock is not reserved or checked by the exporter. The selected entry is:

```json
"160R": ["UNI-ROYAL", "0603WAF1600T5E", "C22814"]
```

Two-element entries retain the existing YAGEO default; three-element entries
specify manufacturer, MPN and LCSC number explicitly. Regenerate all packages
after changing the part table, since its hash is recorded in every package.

The Teensy adapter's U1-U4 (C90755, SN74LV4T125PWR, TSSOP-14) need +270
degrees relative to KiCad in the CPL. This follows the TSSOP correction in
[KiBot's upstream rotation table](https://github.com/INTI-CMNB/KiBot/blob/master/kibot/misc.py).
The correction is keyed to this exact footprint/value in `assembly-parts.json`,
not applied to other IC packages. With these footprints at 0 degrees on the
PCB, the exported JLC rotation is 270 degrees. The board's pin 1 is 2.8625 mm
left and 1.95 mm above each center; it connects to GND, while pin 14 is at
the upper right on VIN_USB. Confirm this pin-1 location in JLC's final preview.
The supplier library API could not be read (HTTP 403); the correction is based
on the published export convention and the actual PCB pad numbering.

The voice card is now entirely through-hole: R3 is a 100K axial DIN0207
resistor at 7.62 mm pitch, like R1/R2. Order the card bare with PCB Assembly OFF.
Its machine BOM and CPL contain headers only. Carrier and voice-card project
constraints now enforce 0.15 mm minimum clearance and track width (F6).

Regenerate from the repository root using KiCad 9 Python:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' export_jlcpcb.py
```

`--only backplane` limits regeneration to one board. The exporter checks native
DRC, rejects unknown SMD parts, excludes DNP parts, verifies BOM/CPL identity,
and records the PCB and part-table hashes. It leaves the source PCBs untouched.
The server refuses stale assembly downloads. The older shields
`scripts/manufacturing.py` entry point delegates to this exporter.
The exporter also refreshes the legacy Gerber exports and renders the web
45-degree 3D preview images directly from the PCB sources. Preview and schematic hashes prevent
older drawings being served after a source edit. The page shows the export
time, PCB revision hash and package hash; ZIP downloads are not browser-cached
and their file names include the package hash.

The identical per-project `manufacturing/<board>-manufacturing.zip` files are
retained for existing users. `MANUFACTURING.json` in shields tracks those five
shields' checksums. Commit regenerated packages with the source changes.

Format references:

- [JLCPCB BOM and KiCad export guide](https://jlcpcb.com/help/article/how-to-generate-bom-and-centroid-files-from-kicad-8)
- [JLCPCB pick-and-place specification](https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly)
