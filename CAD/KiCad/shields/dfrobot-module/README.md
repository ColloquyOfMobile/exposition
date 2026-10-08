# DFRobot Audio Analyzer V2.0 — mechanical reconstruction

Open `dfrobot-module.kicad_pcb` in KiCad PCB Editor and press Alt+3 for the
interactive 3D viewer. `dfrobot-module.step` is the assembled solid model for
measurement in mechanical CAD; `preview.png` and `underside.png` are previews.
All component STEP models are included locally in `3dmodels/`.

This is a photo-derived size study of the **modified plug-in module** requested
by the user, with the six input contacts and two control contacts pointing
downward. It is not a fabrication design or an exact reverse-engineered module.
The carrier boards have not been changed by this model.

| Feature | Model value | Basis |
|---|---:|---|
| PCB outline | 29 × 32 mm | Provisional photo estimate, matching carrier's reserved envelope |
| Corner radius | 2 mm | Visual estimate |
| PCB thickness | 1.6 mm | Assumed |
| Mounting-hole centre spacing | 20.32 mm | Nominal 8 × 2.54 mm photo inference |
| Mounting holes | 3.2 mm round | Assumed M3 clearance; no tolerance slots on module |
| Header pitch | 2.54 mm | User-authorized standard pitch assumption |
| DIP-8 row spacing | 7.62 mm | Standard DIP package model |
| White output connector | JST XH horizontal 3-pin proxy | Visual envelope only; identity/pitch unconfirmed |

The manufacturer's catalogue lists 30 × 20 mm, which does not clearly match
the photographed V2 board. Therefore **29 × 32 mm is an assumption to inspect,
not a confirmed module dimension**. Small SMD positions, sizes and assembly
heights are representative. Standard KiCad header models are used, including
their nominal body and pin lengths; actual replacement headers can differ.
The white connector extends beyond the PCB outline, so the assembled envelope
is larger than the board dimensions above.

Origin is the mounting hole next to the L input. In the PCB's top view, +X
runs toward the second mounting hole, and +Y runs toward the white connector.
Relative header centres match `../analyser-carrier/mechanical.json`:
six contacts at X=3.81, 6.35, 8.89, 11.43, 13.97, 16.51 and Y=-5.08 mm;
two contacts at X=17.78, 20.32 and Y=17.78 mm. The STEP exporter uses this
origin (its Cartesian Y axis is opposite the PCB editor's downward Y axis).

R4 is omitted for the previously documented L-to-OUT plug-in modification.
The tiny insulated jumper is not modelled. See the carrier README for electrical
conversion instructions. No schematic, tracks or fabrication outputs were
created for this mechanical study.

Sources: the two user photos supplied in this conversation; [DFRobot wiki](https://wiki.dfrobot.com/dfr0126/);
[manufacturer schematic](https://dfimg.dfrobot.com/wiki/17648/DFR0126_msgeq7-spectrum-analyzer-module_schematics_V1.pdf).
Library geometry comes from the installed KiCad 9 footprint/3D libraries
(KiCad library CC-BY-SA 4.0 with its library exception).

Regenerate with KiCad's Python: `python build_model.py`. Validation performed:
KiCad loaded the model, the six contact positions were checked against the
carrier grid, STEP export succeeded, and top/underside 3D renders were inspected.
Physical fit has not been verified.
