# Violet MAX9814 module holder — revision B

The 20 × 62 mm PCB now holds the existing violet microphone module on
a 1×5 female socket, with two insulating M2 supports. The former bare
MAX9814, separate capsule and strap headers are removed. Open
`microphone.kicad_pro`; press Alt+3 in PCB Editor for the assembled 3D view.
`microphone.step` and `preview.png` show the carrier, module and supports.
`holder-preview.png` shows the carrier without the module for assembly.

- Artwork mounting: two Ø5.5 mm NPTH M5 holes at (10,6) and (10,56) mm.
  Their 50 mm spacing and Ø12 mm keep-outs remain unchanged.
- Module mounting: two Ø2.2 mm NPTH holes at (15.0165,19.032) and
  (4.9835,19.032) mm, 10.033 mm apart, with Ø6 mm keep-outs.
- Module runs along the carrier: outline (2.9515,17) to (17.0485,42.4) mm.
- Socket contacts run right to left at Y=41.003 mm:
  GND (14.8895), Vdd (12.3495), Gain (9.8095), Out (7.2695), AR (4.7295).
- J1 remains GND / +5V / OUT, pin 1 to pin 1 with the existing harness.

Coordinates are relative to the outline's upper-left corner, +Y down.
`mechanical.json` records the interface dimensions. Module holes/contacts
are independently compared with `../max9814-reference` during verification.

## Fixings and clearances

Use insulating M2 screws/supports with heads <=4 mm diameter; Ø5 mm washers
overlap the capsule. **Match spacer length to the actual seated header and
socket**. The reference uses 8.5 mm socket body + 2.54 mm header collar:
11.04 mm between module underside and carrier top. This height is provisional,
not a guaranteed stocked connector/spacer specification. The reference pin
tips are 6 mm below the module underside, inserting 3.46 mm into this socket.
Dry-fit before choosing spacers/shims; avoid forcing the module or its pins.

The module's underside component envelope is included in the local model.
Carrier parts underneath are low SMD bodies; test pins stay beyond the module
outline. The separate 5 mm insulating frame spacers remain beneath the carrier.
Select M5 screw length for the actual extrusion/T-nut: the nominal 12 mm screw
has 4.4 mm allowance after washer/PCB/spacer, but slot-floor clearance has not
been established. Trim through-hole tails clear of the frame. Nylon separation
does not establish acoustic isolation; check noise with moving servos.

## Circuit and assembly

R1=0R ties Gain to filtered module Vdd (40 dB); R2=0R ties AR to GND (1:500).
No removable shunts are needed. A different setting requires removing the
corresponding link and wiring the alternative deliberately; do not short Vdd
and GND. Check that on-module wiring does not contradict these straps.

Retained circuitry: R4=33R and C7=22uF supply filter; C6=100nF bypass;
R5=470R output build-out; D1/R6 incoming 5 V indication; MICOUT/GND test pins.
The signal stays DC coupled. J1 pin order and position are unchanged.
No separate chip/capsule is fitted. `bom.csv` includes the module/socket;
order insulating fixings separately according to the verified stack.

Fit carrier components and connectors, confirm pin numbering, then seat and
screw down the module with power off. Capsule faces the room. Apply 5 V and
check D1, raw MICOUT resting bias, harness OUT bias, audio and servo noise.

## Regeneration and checks

Run `build_module_model.py` with FreeCAD Python, then the following with
KiCad 9 Python from the repository root:

```powershell
python CAD/KiCad/shields/scripts/microphone_holder.py
python CAD/KiCad/shields/scripts/route.py --only microphone --jar tmp/shields-tools/freerouting-2.4.1.jar --work tmp/microphone-holder-route
python CAD/KiCad/shields/scripts/finish.py microphone
python CAD/KiCad/shields/scripts/planes.py microphone
```

Run `check.run(check.ROOT/'microphone')` and `verify.py` for native ERC/DRC,
schematic/manifest/PCB parity, source module alignment and fixing keep-outs.
The placement checkpoint includes a constrained underside MICOUT test trace.
Reports and front/back assembly SVGs are in `reports/`.

This remains an engineering prototype. The exact violet sample's geometry,
connector height, fastener fit and acoustics require physical validation.
The module model derives from Adafruit's CC BY-SA 3.0 source; attribution
and original license/README remain in `../max9814-reference/source/`.
Library socket/component models use KiCad's library license and exception.
Previous bare-chip design history is available in git before this revision.
