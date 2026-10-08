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
| PCB outline | 22 × 34 mm | User correction on User.Comments, 2026-10-08; X=22, Y=34 |
| Corner radius | 2 mm | Visual estimate |
| PCB thickness | 1.6 mm | Assumed |
| Mounting-hole centre spacing | 20.32 mm | Nominal 8 × 2.54 mm photo inference |
| Mounting holes | 3.2 mm, 3.6 mm copper diameter | Centres retained at user's request; holes intersect the narrower side edges |
| Header pitch | 2.54 mm | User-authorized standard pitch assumption |
| DIP-8 row spacing | 7.62 mm | Standard DIP package model |
| White output connector | Horizontal SMD 3-pin proxy, wholly inside PCB outline | SMD corrected by user; exact identity/pitch/height unconfirmed |

The user's 22 × 34 mm correction supersedes the earlier 29 × 32 mm photo estimate.
The retained 20.32 mm mounting centres are only 0.84 mm from the side edges:
the retained 3.2 mm holes consequently break through those edges. Copper pads
were reduced from 6.4 mm to 3.6 mm. This is the requested reference-only treatment,
not a manufacturable mounting-hole design. Small SMD positions, sizes and assembly
heights are representative. Standard KiCad header models are used, including
their nominal body and pin lengths; actual replacement headers can differ.
The white SMD connector uses a simplified local STEP body and surface leads,
with no through-hole tails. Its complete 12.6 × 9.8 mm footprint envelope is
inside the board boundary; connector height is provisionally 6 mm.

Origin is the mounting hole next to the L input. In the PCB's top view, +X
runs toward the second mounting hole, and +Y runs toward the white connector.
Relative input header centres still match `../analyser-carrier/mechanical.json`:
six contacts at X=3.81, 6.35, 8.89, 11.43, 13.97, 16.51 and Y=-5.08 mm;
two control contacts are now at X=16.51, 19.05 and Y=17.78 mm. J4 pin 1 is
exactly aligned in X with J2J3 pin 6 (world X=70.85 mm), correcting the user's
approximate move to X=70.825 mm. The carrier's two-pin sockets have now also
moved 1.27 mm to match, including their attached tracks. The STEP exporter uses this
origin (its Cartesian Y axis is opposite the PCB editor's downward Y axis).

R4 is omitted for the previously documented L-to-OUT plug-in modification.
The tiny insulated jumper is not modelled. See the carrier README for electrical
conversion instructions. No schematic, tracks or fabrication outputs were
created for this mechanical study.

Sources: the two user photos supplied in this conversation; [DFRobot wiki](https://wiki.dfrobot.com/dfr0126/);
[manufacturer schematic](https://dfimg.dfrobot.com/wiki/17648/DFR0126_msgeq7-spectrum-analyzer-module_schematics_V1.pdf).
Library geometry comes from the installed KiCad 9 footprint/3D libraries
(KiCad library CC-BY-SA 4.0 with its library exception).

Generate the SMD proxy with FreeCAD's Python: `python build_smd_connector.py`;
then regenerate with KiCad's Python: `python build_model.py`. User.Comments
annotations are retained when regenerating. Validation performed:
KiCad loaded the model, the six contact positions were checked against the
carrier grid, STEP export succeeded, and top/underside 3D renders were inspected.
Physical fit has not been verified.
