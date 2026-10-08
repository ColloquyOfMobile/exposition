# Teensy 4.1 — mechanical and 3D reference

Open `teensy41-reference.kicad_pcb` in KiCad and press **Alt+3**.
`teensy41-reference.step` is the assembled model, including two downward-facing
24-pin headers and an inserted microSD card. `preview.png` is the preview.

The installed shield design uses Teensy **4.1**. This reference imports the
existing community assembly by **Zack Kummer**, distributed with
[XenGi's Teensy library](https://github.com/XenGi/teensy.pretty), rather than
reconstructing its component shapes. The source footprint, original STEP,
upstream README, MIT license and pinned Git revision are retained in `source/`.

Main geometry agrees with [PJRC's dimensional drawing](https://www.pjrc.com/teensy/dimensions.html):

| Feature | Reference value |
|---|---:|
| PCB outline | 60.96 × 17.78 mm (2.4 × 0.7 inches) |
| Long header rows | 2 × 24 contacts |
| Contact pitch | 2.54 mm |
| Row separation | 15.24 mm |
| End contact centre to board end | 1.27 mm |
| PCB thickness | 1.6 mm (source slab approximately 1.598 mm) |
| Original assembly length including USB and inserted card | 66.56 mm |

The community STEP includes both top and underside component geometry and an
inserted microSD card. KiCad supplies the PCB slab and the two new standard
header models; the original slab is removed from the imported geometry to
avoid duplicate solids. All 3D dependencies are local in `3dmodels/`.
The retained source STEP is the original board without the added headers.

This is a reference model, not a certified exact copy of the user's physical
unit. PJRC documents component/SD-socket revisions over time; the community
model may represent an older assembly. Header pin lengths and body heights
come from KiCad's standard models and should be compared with the actual
headers when checking tight clearances. No schematic or routing was created.
The existing adapter/carrier PCB projects were not changed.

Regenerate by running `prepare_model.py` with FreeCAD Python, then
`build_reference.py` with KiCad Python. The former reads the original STEP;
the latter packages the footprint and creates the native PCB reference.
Export STEP with KiCad CLI using `--user-origin 100x100mm` (board centre).

Validation: native KiCad reload; 48 header contacts matched to the original
footprint grid; all referenced 3D files present; STEP export; visual inspection
of the rendered assembly. Electrical DRC/fabrication checks are outside this
mechanical reference's scope.

Sources retrieved 2026-10-08. Upstream MIT license is preserved in
`source/LICENSE`; KiCad header models use CC BY-SA 4.0 with the KiCad library
exception. PJRC product/revision reference: https://www.pjrc.com/store/teensy41.html
