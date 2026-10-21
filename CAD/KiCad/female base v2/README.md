# Female base v2 - socketed GF1002 amplifier

Open `female-base-v2.kicad_pro` in KiCad 9. The routed board, main schematic,
continuous-wire schematic, BOM, STEP model, previews, Gerbers and reports follow
the user's **2026-10-21 placement**. The original `../female base/` is preserved.

## Current layout

The authoritative placement checkpoint is `female-base-v2-placed.kicad_pcb`.
The routed `female-base-v2.kicad_pcb` retains all its component positions and
orientations. The user moved four components and removed H1/H2, the two M2
amplifier-support mounting holes. H1/H2 are also removed from both schematics
and the circuit metadata. No replacement support holes were added. The original
artwork outline, cutouts, DSUB geometry and harness pin assignments are retained.

| Part | X (mm) | Y (mm) | Rotation |
|---|---:|---:|---:|
| R1, 22K | 39.545 | 57.390 | 0 degrees |
| R2, 3K3 | 41.345 | 59.930 | 0 degrees |
| C1, 220 uF / 10 V SMD | 33.890 | 46.980 | 180 degrees |
| C2, 100 nF / 0603 | 34.085 | 67.610 | 180 degrees |

The remaining connector and socket positions are unchanged. Every connector
has a front silkscreen name: J2 DXL MIRROR, J3 MICROPHONE, J4 PHOTOSENSOR,
J5 NEOPIXEL, J6 SPEAKER and J7 HARNESS. See
[`reports/connector-names.png`](reports/connector-names.png).

The [continuous-wire schematic](wired/female-base-v2-wired.pdf) is an editable
KiCad reading copy in `wired/`. Its existing layout is preserved. Both schematic
copies contain 11 components and agree on 38 connected pins and 12 electrical
nets. [The comparison](wired/comparison.md) explains the additions relative to
the original female base.

## Audio and power

The module itself mounts on this PCB; Thomas's green perfboard, its JST sockets
and blue terminal are absent. R1 = 22K and R2 = 3K3 reproduce Thomas's input
divider. R2's bottom and module input G use AUDIO_RETURN. Module supply minus
uses GND; these are separate PCB nets.

| J7 pin | v2 function |
|---|---|
| 12 | LINE_IN, formerly remote amplifier speaker + |
| 4 | AUDIO_RETURN, formerly remote amplifier speaker - |
| 15 | 5 V supply, unchanged |
| 8 and shell pad 0 | Supply GND, unchanged |

**Disconnect the old rack class-D speaker output from J7.12/J7.4 before using
this board.** The rack must send line-level audio and its return on that pair.
J6 now connects only to the local GF1002 right-channel output.

C1 is a polarized SMD aluminium electrolytic,
`Capacitor_SMD:CP_Elec_6.3x5.8`, with a nominal 6.3 x 5.8 mm case. Pad 1 is
positive / 5 V; pad 2 is GND. The footprint is now rotated 180 degrees.
An example part is
[Panasonic EEEFN1A221UP](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-smd/models/EEEFN1A221UP).
Match the purchased part's land pattern and assembly requirements. C1's 220 uF
value remains provisional. C2 is 100 nF in 0603. The amplifier branch is on
5 V only; the existing 12 V net serves the servo.

### Placement tradeoffs to verify on the bench

The capacitor positions have been preserved as requested. C2's two pads are
approximately 14.7 and 16.3 mm from the corresponding module supply contacts,
outside the previous less-than-5-mm target. C1's positive pad is about 23.3 mm
from module supply +, outside the previous less-than-9-mm target. These distances
are explicitly reported as unmet proximity targets, not as passing decoupling
checks. Check rail sag, clipping and noise with the actual module, speaker and
harness. CAD continuity does not establish electrical performance.

## Revision D plug-in module interface

The socket/header arrangement introduced on 2026-10-19 remains unchanged.
M1 is a vertical 1 x 11 female socket at 2.54 mm pitch, on the module contact
row. Socket pin 1 is at (49.55, 56.2) mm; pin n is at Y = 56.2 + 2.54*(n-1).
The contact row is based on `../shields/gf1002-reference/`.

| M1 pin | Module contact | Net |
|---:|---|---|
| 1 | input R | AMP_INPUT |
| 2 | input G | AUDIO_RETURN |
| 3 | input L | no connection |
| 4 | no contact | no connection |
| 5 | power + | 5V |
| 6 | power - | GND |
| 7 | no contact | no connection |
| 8, 9 | LOUT pair | no connection |
| 10, 11 | ROUT pair | AMP_OUT_P, AMP_OUT_N to J6 |

Pin 10 = ROUT+ and pin 11 = ROUT- remain provisional: read the real module's
markings before ordering. Neither speaker output is ever connected to ground.
Confirm that input G and power minus are bonded inside the module as expected.
No PCB jumper assumes that bond.

The module uses male headers at positions 1-3, 5-6 and 8-11, plugged into the
female socket. Solder all eleven socket pins for strength. The nominal 8.5 mm
socket plus 2.5 mm header plastic puts the module underside about 11 mm above
the PCB and the pot about 28 mm high. Its shaft overhang is approximately
16 mm beyond the board's left edge. Measure actual parts and installed-body
clearances. H1/H2 are absent in this female revision; do not use the former
two-support assembly instructions for it. The final physical support arrangement
is not validated by the CAD checks.

## Routing and validation

Speaker outputs remain a short front-copper pair using 0.8 mm tracks; their
lengths are 18.153 and 19.191 mm. The input and audio return approach together
on back copper. The relocated divider's complete AMP_INPUT route is 12.275 mm;
the revised CAD length budget is 16 mm, compared with 8 mm for the old placement.
An explicit grounded front guard and local ground pours separate the output
region from the input and sensors. Checks find no parallel sensitive runs
within 2.5 mm of the outputs and no output/sensitive crossings in projection.
AUDIO_RETURN remains separate from the GND pours.

Native ERC, DRC, unconnected items and schematic/PCB parity are all zero.
`reports/validation.json` records source hashes, actual positions, routing,
removed supports and the unmet capacitor proximity targets. Simulation and CAD
checks do not establish physical fit, current capacity or noise performance.

## Rebuild and exports

To reroute from the saved placement, without rebuilding or moving components:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/route_boards.py' --only female-base-v2
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/finish_boards.py' --only female-base-v2
& './CAD/KiCad/female base v2/scripts/export_boards.ps1' -Only female-base-v2
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/verify_boards.py' --only female-base-v2
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/verify_wired_schematic.py'
```

The full `build_boards.py` also records these female coordinates and omits
H1/H2. It regenerates both body projects, whereas the commands above target
only the female board. Gerbers are regenerated with `export_gerbers.py` after
DRC passes. The revised package is still an engineering prototype, not a
physically qualified production release.
