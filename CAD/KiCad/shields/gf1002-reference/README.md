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
footprints are illustrative. The corrected nine-contact row is described below; its locations remain
photo-derived. Perfboard pads have no nets.

## Correction, 2026-10-19: the module's contacts

The module's contacts are **nine pads in one row along its right-hand long
edge**, the edge opposite the volume shaft, on a 2.54 mm grid of eleven
positions. They are read from Thomas's photo (`source/reference-photo.jpg`),
where they sit in the perfboard's holes, so the pitch is the perfboard's.
The three groups agree with a PAM8403 board of the same kind
([Protosupplies](https://protosupplies.com/product/pam8403-mini-stereo-audio-amp/):
input L/G/R, power −/+, speakers ROUT−/ROUT+/LOUT−/LOUT+).

Coordinates are from the module's corner at the pot end, on the side away
from the shaft: Y along the edge, away from the pot. The row is about
**1.45 mm in from the edge**. Read from the photo, so each value is good to
about 0.5 mm.

| Position | Contact | Y, mm (1.2 + 2.54 per position) | Photo, mm |
|---:|---|---:|---:|
| 1 | input R | 1.2 | 1.2 |
| 2 | input G | 3.7 | 3.7 |
| 3 | input L | 6.3 | 6.4 |
| 4 | none | 8.8 | |
| 5 | power + | 11.4 | 11.6 |
| 6 | power − | 13.9 | 14.2 |
| 7 | none | 16.4 | |
| 8, 9 | LOUT pair | 19.0, 21.5 | 19.0, 21.5 |
| 10, 11 | ROUT pair | 24.1, 26.6 | 24.3, 27.1 |

The silkscreen reads `R G L` under `input`, `power` with `+` on the input
side, then `Lout` and `rout`. Polarity within the two output pairs is not
legible in the photo. Thomas's speaker is on the ROUT pair (his Figure 6);
on a stereo board of this kind that pair is driven from the R input.

**Size**: 29.5 × 20.2 mm, 15 mm overall
([Tindie listing that names the model GF1002](https://www.tindie.com/products/robotart/pam8403-mini-5v-digital-amplifier-board/):
"Dimensions: 29.5 * 20.2 * 15mm"). The model's 20 × 30 mm is within 0.5 mm
of that. In the photo the pot body overhangs the shaft-side edge by about
3 mm; the model has 1 mm.

These are seller listings and a photo, not a datasheet: **measure one
module** before a footprint depends on them (row offset, first contact,
pin length below the board, pot overhang).

**Regenerated 2026-10-19:** reference PCB, STEP/VRML envelopes, previews,
body-board assemblies, Blender body scenes and 1:1 templates now use the
nine-contact row. Contact numbers retain the eleven grid positions (4 and
7 absent). LOUT/ROUT contacts are labelled A/B because polarity is unreadable.
The conservative envelope is 20.2 × 30 mm; the contact X remains the photo
estimate 18.55 mm (1.65 mm from that envelope's edge). Pot overhang is now
3 mm. Body boards use wires and flush-cut tails rather than a mating footprint.
Physical fit is still unverified; see the body-board READMEs and F8.

## Geometry and uncertainty

Scale is estimated from the photographed carrier, assuming a standard
**2.54 mm perfboard pitch**. Rounded outline estimates are deliberately used
rather than claiming precise measurements from the perspective photograph.
No dimensions have been confirmed on a physical sample.

| Feature | Reference value | Basis |
|---|---:|---|
| Module envelope | 20.2 × 30 mm | Conservative allowance for seller size 20.2 × 29.5 mm; unmeasured |
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
validated for CAD consistency. Top and
underside renders were inspected. These checks establish CAD consistency only; physical fit
and electrical operation have not been validated. Existing installation
and shield designs were not modified.
