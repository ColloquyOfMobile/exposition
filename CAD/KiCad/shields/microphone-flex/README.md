# Microphone holder Rev C — left, right or upward

Prototype based on the user's annotated picture, 2026-10-15. The support PCB
stays on the aluminium profile; **one MAX9814 module** faces left, right or up.
This is a separate revision study. The current `../microphone/` Rev B board
and its existing fabrication package remain unchanged.

The PCB is **32 × 62 mm**, widened from 20 mm while retaining the 62 mm length
and 50 mm frame-fixing spacing. Its two **12 × 5.5 mm NPTH oblong slots** run
across the profile, with 6.5 mm between the semicircular end centres. The
18.5 × 12 mm capsule-shaped copper/part keepouts cover the entire slot travel,
not just the middle of each hole. The nominal 5 mm insulating frame spacers
remain separate from the module supports. Check washers, screw engagement and
the actual imperial profile/T-nuts before selecting frame fixings.

## Choose one module position

| Position | Socket | Module support |
| --- | --- | --- |
| Up / position 3 | M1, vertical 1×5 socket | Existing H3/H4 insulating M2 posts; match seated height |
| Left / position 1 | J2, horizontal 1×5 socket | Two prototype insulating arms on H5/H6 |
| Right / position 2 | J3, opposing horizontal 1×5 socket | Two prototype insulating arms on H7/H8 |

All three socket rows carry the same five signals. **Fit exactly one module.**
The gain and A/R straps, supply filter, output resistor, LED and external J1
pin order are retained from Rev B. J1 remains GND / +5V / OUT. SMD parts remain
on the front. Socket rows may all be populated, but only the selected module
supports are fitted. Do not force a module into a socket of unverified geometry.

The side sockets' **physical pad order is reversed** relative to M1:

| Physical socket pad | M1 up | J2 left / J3 right |
| --- | --- | --- |
| 1 | GND | AR |
| 2 | Vdd | Out |
| 3 | Gain | Gain |
| 4 | Out | Vdd |
| 5 | AR | GND |

This follows the rotations of the original module, rather than assuming
pin-1-to-pin-1 geometry for a right-angle socket. Independent checks compare
all ten side contacts against the original module pad coordinates and nets.
Generic KiCad socket proxies set the nominal contact axis at 1.27 mm above
the holder component face. The side module underside is 2.54 mm outside the
socket mouth; the existing 6 mm pin projection gives 3.46 mm nominal insertion.
Purchased sockets, header seating and the actual violet module must be measured.

The side module rises to approximately 26.9 mm above the holder underside,
before the separate 5 mm frame gap. Two insulating arms support its original
M2 mounting holes, 10.033 mm apart; the pin row does not carry the whole load.
The four arm STL files in `3dmodels/` are **fitting prototypes**, with 2.2 mm
holes for insulating M2 fixings. Module screw heads must remain no larger than
4 mm beside the microphone capsule. Frame screws, module screws and cable
routes are not represented as verified purchased hardware. Print and dry-fit
the arms before relying on their dimensions or mechanical stiffness.

## Files and 3D views

`microphone-flex.kicad_pro` opens the routed electrical prototype. Its board
contains the three socket footprints and all alternative support holes.
`variants/up.kicad_pcb`, `left.kicad_pcb` and `right.kicad_pcb` are assembled
viewing copies with identical copper and exactly one seated module. Their
3D references resolve to local repository models. The shared combined Blender
file in `../assembly-3d/` is self-contained and adds six body scenes:

- Female body / Male body: upward module.
- Female body - mic left / Male body - mic left.
- Female body - mic right / Male body - mic right.

Earlier edited body scenes are retained as **Rev B reference** scenes.
The Mega and Teensy rack scenes are retained. The aluminium profile is still
the explicitly unconfirmed 1 × 2 inch reference described in the assembly
README; no installed TJ part number was found.

## Generation and verification

Run from the repository root:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/scripts/microphone_flex.py
& 'C:/Program Files/FreeCAD 1.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/build_models.py
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/scripts/route.py --only microphone-flex --jar tmp/shields-tools/freerouting-2.4.1.jar --work tmp/microphone-flex-route
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/check_layout.py
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/export_variants.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 --python CAD/KiCad/shields/assembly-3d/add_body_scenes.py -- --replace-body-scenes
```

The final command replaces generated Rev C body scenes; preserve any edits
to those scenes before rerunning. Earlier Rev B scenes are retained rather
than rebuilt. Backup combined files are saved under `tmp/body-model/`.

`layout-validation.json`: zero ERC/DRC violations and zero unconnected items;
all 36 connected pins agree between the native schematic, circuit manifest
and PCB. Slot geometry and spacing, side pin polarity, and contact alignment
are independently checked. `support-model-validation.json`: connected, valid
support solids without module intersection. `variant-validation.json` and
the assembly's `body-scenes-validation.json` record source/output hashes.
Simulation and CAD checks do not establish physical fit, acoustic performance,
vibration isolation or mechanical strength. No fabrication release is claimed.

Sources and attribution: Rev B microphone holder; retained Adafruit MAX9814
reference (Limor Fried/Ladyada, CC BY-SA 3.0; see
`../max9814-reference/source/license.txt`); generic KiCad connector geometry
(CC BY-SA 4.0 with library exception). New support arms are provisional geometry
for this installation.
