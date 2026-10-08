# MAX9814 violet microphone module — mechanical reference

Open `max9814-reference.kicad_pcb` in KiCad PCB Editor and press **Alt+3**
for the 3D viewer. `max9814-reference.step` is the assembled solid model for
mechanical CAD. `preview.png` and `underside.png` show both sides. All models
are included locally in `3dmodels/`.

The user's photo shows an Adafruit-style **MAX9814 AGC microphone breakout**:
its five contacts read GND, Vdd, Gain, Out, AR, and its gain/output legends
match Adafruit's published board. The exact supplier/revision of the sample
is unconfirmed. This reference uses **Adafruit's original Eagle geometry**;
it does not establish that a clone in the photo has identical dimensions.
The green perfboard and its wiring are outside this reference.

| Feature | Reference value | Basis |
|---|---:|---|
| Board outline | 25.400 × 14.097 mm | Original Eagle Edge.Cuts geometry |
| Corner radius | 1.905 mm | Original Eagle outline arcs |
| PCB thickness | 1.6 mm | Assumed |
| Header pitch | 2.54 mm | Original Eagle pads |
| Header drill | 1.0 mm | Original Eagle pads |
| Mounting-hole drill | 2.2 mm, plated | Original Eagle pads |
| Mounting centre spacing | 10.033 mm | Original Eagle geometry |
| Microphone diameter | 9.602 mm | Original Eagle package outline |
| Microphone height above PCB | Approximately 6.5 mm | Representative envelope, unmeasured |
| Header plastic below PCB | 2.54 mm | Assumed standard header body |
| Header tip below PCB top surface | 7.6 mm | Assumed pin length/installation |

The PCB editor origin used for this study is (50,50) mm, the upper-left
extent of the outline. The STEP origin is the corresponding outline corner;
its Cartesian Y direction is opposite the PCB editor's downward Y direction.
The microphone side is the top; the header pins point down. All dimensions
below are relative to that corner, with PCB-editor +X right, +Y down:

| Item | X (mm) | Y (mm) |
|---|---:|---:|
| Mounting hole 1 | 2.032 | 2.032 |
| Mounting hole 2 | 2.032 | 12.065 |
| Microphone centre | 7.239 | 6.985 |
| J2 pin 1 — GND | 24.003 | 2.159 |
| J2 pin 2 — Vdd | 24.003 | 4.699 |
| J2 pin 3 — Gain | 24.003 | 7.239 |
| J2 pin 4 — Out | 24.003 | 9.779 |
| J2 pin 5 — AR | 24.003 | 12.319 |

Original component pads and positions are retained. Passive bodies use
representative KiCad 0805 models; the MAX9814 has a simplified 3 × 3 × 0.8 mm
envelope. The electret and header have local STEP solids and coloured VRML
previews. Component heights, solder joints and exact header installation
depth are approximate. The silkscreen legends were rearranged for readability.
`model-mapping.json` records the body choices.

This is a mechanical reference, **not a fabrication design**: no electrical
nets, copper routing, ground fills or schematic were reconstructed in KiCad.
The original routed Eagle board and schematic are preserved in `source/`.
Check the physical module before using this model for tight clearances or
designing mating hardware. Existing installation boards were not modified.

## Sources and licensing

- [Adafruit's MAX9814 PCB repository](https://github.com/adafruit/Adafruit-MAX9814-AGC-Microphone-PCB),
  downloaded 2026-10-08; original board, schematic, README and license retained
  verbatim in `source/`. Designed by Limor Fried/Ladyada for Adafruit Industries.
  The adaptation is shared under the source's Creative Commons Attribution /
  Share-Alike 3.0 Unported terms. See `source/license.txt` and `source/README.md` for the
  required original attribution text and license details.
- User-supplied photo, retained as `source/reference-photo.jpg`.
- KiCad library models: CC BY-SA 4.0 with the KiCad library exception.

## Regeneration and validation

Run `build_envelopes.py` using FreeCAD 1.0's Python, then
`build_reference.py` using KiCad 9's Python. Library paths are defined at
the top of the latter script. Export the assembled model with:

```powershell
kicad-cli pcb export step --force --subst-models --user-origin '50x50mm' -o max9814-reference.step max9814-reference.kicad_pcb
kicad-cli pcb render --width 1200 --height 800 --rotate '325,0,335' -o preview.png max9814-reference.kicad_pcb
kicad-cli pcb render --width 1200 --height 800 --side bottom --rotate '25,0,25' -o underside.png max9814-reference.kicad_pcb
```

Validation: KiCad loaded the generated board; all 46 pad locations were compared
against the transformed original Eagle coordinates; the two mounting holes
and header pitch/drills were checked; all local model files were resolved;
STEP export completed (20 valid solids); top and underside renders were inspected. Physical
fit and electrical operation have not been validated.
