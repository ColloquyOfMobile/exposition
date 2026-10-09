# Thomas GF1002 amplifier — mechanical references

Two editable KiCad boards and assembled STEP models are included:

- `gf1002-reference.kicad_pcb` / `.step`: amplifier module alone, with the
  volume control, shaft, capacitor and representative surface components.
- `thomas-amplifier-carrier-reference.kicad_pcb` / `.step`: Thomas's complete
  prototype arrangement, including the module, perfboard, white connector
  proxies, resistors and blue speaker screw terminal.

Open either PCB in KiCad 9 and press **Alt+3** for the 3D viewer.
`preview.png` and `carrier-preview.png` show the assemblies; the corresponding
`*-underside.png` files show the reverse sides. All 3D assets are local.

These are **photo-derived mechanical studies, not fabrication designs**.
Thomas calls the module **GF1002**; the photographed IC marking is not legible
enough to identify its chip. No electrical schematic, nets, routing, operating
voltage, gain or component values have been reconstructed. The small component
footprints and four lower-edge contacts are illustrative; their electrical
functions and precise positions remain unknown. Perfboard pads have no nets.

## Geometry and uncertainty

Scale is estimated from the photographed carrier, assuming a standard
**2.54 mm perfboard pitch**. Rounded outline estimates are deliberately used
rather than claiming precise measurements from the perspective photograph.
No dimensions have been confirmed on a physical sample.

| Feature | Reference value | Basis |
|---|---:|---|
| Module outline | 20 × 30 mm | Photo estimate |
| Carrier outline | 40 × 60 mm | Photo estimate |
| Both PCB thicknesses | 1.6 mm | Assumed |
| Carrier perfboard grid | 16 × 23 positions, 2.54 mm pitch | Representative standard grid |
| Carrier mounting holes | Ø3.2 mm, 2.5 mm from the corners | Representative; unmeasured |
| Module position on carrier | X = -5 mm, Y = 9 mm | Photo estimate; module overhangs left edge |
| Module top above carrier top | 5 mm | Assumed assembly height |
| Volume-control body | 16 × 13 × 12 mm | Simplified photo envelope |
| Shaft diameter / protrusion | Ø6 mm / 20 mm left of module outline | Assumed envelope |
| Capacitor | Ø6.4 × 7.15 mm | Representative envelope |
| White connectors | KiCad JST XH vertical 2/3-pin proxies, 2.50 mm pitch | Exact series and dimensions unknown |
| Blue terminal | 2-pin 5.08 mm footprint, simplified 10.16 × 8 × 8.3 mm body | Assumed pitch and body |

PCB-editor origin is the upper-left outline corner at (50, 50) mm.
Coordinates above use +X right and +Y down. Exported STEP uses the same origin
with Cartesian +Y upward. Module STEP includes its shaft overhang; allow for
that envelope when importing it into an enclosure study.

The photograph's connector labels are retained on the carrier silkscreen:
Audio/GND, Audio/VDD/GND, VDD/GND and ROUT+/ROUT-. They describe the photographed
assembly, not an independently verified module pinout. J1/J2 are at the upper
right, J3 near the centre is supply, J4 at the lower right is speaker output,
and J5 is the blue alternative speaker terminal. Pin numbers on the generic
footprints do not establish wiring polarity.

The module's carrier mounting method, solder joints, underside electronics,
hand wiring and exact potentiometer supports are not modelled. No standoffs
are implied by the provisional 5 mm assembly height. Measure the actual
parts before designing mating hardware or tight clearances.

## Sources and licensing

- `Source code/Thomas/Colloquy - Pask Redesign.pdf`, printed page 5
  (Amplifier), printed page 8, Figure 6 (Amplifier module pinout).
- `source/reference-photo.jpg`: existing Figure 6 image copied from
  `Source code/Python/colloquy/server2/static/hardware/amplifier-module.jpg`.
  Original documentation/photo attribution remains Thomas's; no additional
  redistribution license is asserted for the image.
- Generic footprints and models from KiCad 9 libraries: CC BY-SA 4.0 with
  the KiCad library exception. The custom envelopes are generated locally.

## Regeneration and validation

From the repository root on the Windows CAD machine:

```powershell
& 'C:/Program Files/FreeCAD 1.0/bin/python.exe' 'CAD/KiCad/shields/gf1002-reference/build_envelopes.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/shields/gf1002-reference/build_reference.py'
& './CAD/KiCad/shields/gf1002-reference/export_references.ps1'
```

`mechanical.json` records the principal assumptions. The board generator
reloads both PCBs, verifies that their 3D assets resolve locally, and checks
that there are no tracks or zones. Custom envelope solids are checked for
validity by FreeCAD. Exported STEP assemblies were reopened in FreeCAD and
validated (29 solids for the module, 40 for the carrier assembly). Top and
underside renders were inspected. These checks establish CAD consistency only; physical fit
and electrical operation have not been validated. Existing installation
and shield designs were not modified.
