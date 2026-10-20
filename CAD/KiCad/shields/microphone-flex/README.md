# Microphone holder Rev C — left, right or upward

## Side modules hang down — 2026-10-20

J2 and J3 modules are turned 180 degrees about the horizontal socket insertion
axis, so their bodies hang below the carrier PCB. M1 remains upward.
The socket footprints and all other component positions are unchanged.
This turn reverses the module's five-pin order along each side socket;
J2/J3 are rewired and the carrier is rerouted to match. Do not use the earlier
side-socket pin mapping with this orientation.

## User-approved placement — 2026-10-20

The routed board follows the saved microphone-flex-placed layout exactly:
all 16 footprint positions, rotations and sides are retained. Routing uses
the placement project's nominal 0.20 mm track width and clearance, with
router pad neckdowns subject to the project's minimum-width rules. J2/J3
overhang the PCB; their off-board outlines are on F.Fab rather than printed
silkscreen. The left/right footprint variants preserve the same pads and bodies.

Only H1/H2 frame slots remain. H3-H8 module-support mounting holes were removed
in the user's placement and are absent from the current schematic and views.
The older support STL/STEP files are retained as reference geometry; they are
not installed in the current variants. Side module views follow the moved
socket rows. Module retention requires a separate mechanical arrangement.

## Removable selectors — 2026-10-20

JP1 and JP2 are gold plated 1x03, 2.54 mm through-hole headers, each supplied
with one removable two-contact shunt. They replace the fixed R1/R2 zero-ohm
links on the current microphone flex board. The older Rev B microphone board
is retained as a historical design and is unchanged.

Both headers have pad 1 = GND and pad 3 = filtered VDD. Pad 2 is GAIN on JP1
and A/R on JP2. Install exactly one shunt per selector, or leave it off for
the open setting:

| Selector | Shunt 1–2 | Shunt 2–3 | No shunt | Initial assembly |
| --- | --- | --- | --- | --- |
| JP1 maximum gain | 50 dB | 40 dB | 60 dB | 2–3: 40 dB |
| JP2 attack/release | 1:500 | 1:2000 | 1:4000 | 1–2: 1:500 |

The gain figures apply before automatic gain compression. Switch power off
before moving shunts. The centre signal pins feed all three alternative
module sockets; only one MAX9814 module is fitted. The initial settings
preserve the former electrical configuration while allowing later adjustment.
The schematic shows the three separate selector contacts; the removable
shunt positions are assembly instructions, not permanent PCB copper bridges.
The 3D files show generic shunt proxies at the initial positions. Purchased
header/shunt dimensions, access beneath the module, and physical fit still
need checking.

## Continuous-wire schematic for review

Open wired/microphone-flex-wired.kicad_pro for the separate editable reading
copy, or wired/microphone-flex-wired.pdf for the single A3 sheet. The SVG and
PNG preview are alongside it. Every connection is drawn with continuous wires;
the signal captions are plain text, not electrical labels. Dots mark joined
wires; crossings without dots are separate.

The three socket symbols align pins by signal for easier tracing. Their
physical pad numbers are retained, including the downward J2/J3 mapping.
J1 also groups its pins by signal rather than physical order. Fit one module
only. Component references, values, footprints, mounting holes, and electrical
connections follow the current source schematic and PCB.

Regenerate and validate from the repository root:

~~~powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/build_wired_schematic.py
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/verify_wired_schematic.py
& 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe' sch export pdf -o CAD/KiCad/shields/microphone-flex/wired/microphone-flex-wired.pdf CAD/KiCad/shields/microphone-flex/wired/microphone-flex-wired.kicad_sch
& 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe' sch export svg -o CAD/KiCad/shields/microphone-flex/wired/ CAD/KiCad/shields/microphone-flex/wired/microphone-flex-wired.kicad_sch
pdftoppm -scale-to 2600 -png -singlefile CAD/KiCad/shields/microphone-flex/wired/microphone-flex-wired.pdf CAD/KiCad/shields/microphone-flex/wired/preview
~~~

The wired/validation.json report records 38 connected pins across eight nets,
agreement with the independently exported original schematic, circuit manifest
and PCB, zero electrical labels, and zero ERC violations. The wired copy
changes the presentation; these checks do not establish physical hardware
performance.

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
| Up / position 3 | M1, vertical 1×5 socket | Separate retention; no PCB support holes |
| Left / down / position 1 | J2, horizontal 1×5 socket | Separate retention; no PCB support holes |
| Right / down / position 2 | J3, opposing horizontal 1×5 socket | Separate retention; no PCB support holes |

All three socket rows carry the same five signals. **Fit exactly one module.**
The gain and A/R settings use the removable selectors above. The supply filter,
output resistor, LED and external J1 pin order are retained from Rev B.
J1 remains GND / +5V / OUT. SMD parts remain
on the front. Socket rows may all be populated, but fit only one module.
Do not force a module into a socket of unverified geometry.

With the side modules hanging down, all three sockets have the same physical
pad-to-signal mapping:

| Physical socket pad | M1 up | J2 left / J3 right |
| --- | --- | --- |
| 1 | GND | GND |
| 2 | Vdd | Vdd |
| 3 | Gain | Gain |
| 4 | Out | Out |
| 5 | AR | AR |

This follows the rotations of the original module, rather than assuming
pin-1-to-pin-1 geometry for a right-angle socket. Independent checks compare
all ten side contacts against the original module pad coordinates and nets.
Generic KiCad socket proxies set the nominal contact axis at 1.27 mm above
the holder component face. The side module underside is 2.54 mm outside the
socket mouth; the existing 6 mm pin projection gives 3.46 mm nominal insertion.
Purchased sockets, header seating and the actual violet module must be measured.

The downward side module extends nominally 22.733 mm below the carrier's
component face (21.133 mm below its underside). The CAD model clears the
solid carrier envelope; physical installation and frame clearance still
require checking. The earlier reference study used two
insulating arms at its M2 mounting holes, 10.033 mm apart. These arms are
not installed in the current user placement.
The four arm STL files in `3dmodels/` are **fitting prototypes**, with 2.2 mm
holes for insulating M2 fixings. Module screw heads must remain no larger than
4 mm beside the microphone capsule. Frame screws, module screws and cable
routes are not represented as verified purchased hardware. Print and dry-fit
the arms before relying on their dimensions or mechanical stiffness.

## Files and 3D views

`microphone-flex.kicad_pro` opens the routed electrical prototype. Its board
contains the three socket footprints and the two frame slots.
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
& 'C:/Program Files/FreeCAD 1.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/build_down_modules.py
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/scripts/route.py --only microphone-flex --preserve-netclasses --jar tmp/shields-tools/freerouting-2.4.1.jar --work tmp/microphone-flex-route
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/check_layout.py
& 'C:/Program Files/KiCad/9.0/bin/python.exe' CAD/KiCad/shields/microphone-flex/export_variants.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 --python CAD/KiCad/shields/assembly-3d/update_visual_geometry.py -- --only=shield-configurations.blend --render
```

For a newly edited placement, rebuild the downward models before routing; the first command
recreates the staging board from the generator's recorded placement. The final
command refreshes meshes in place while retaining scene edits and placements.

`layout-validation.json`: zero ERC/DRC violations and zero unconnected items;
all 38 connected pins agree between the native schematic, circuit manifest
and PCB. Slot geometry and spacing, side pin polarity, and contact alignment
are independently checked. `support-model-validation.json` describes only the
older reference support solids, not the current mounting arrangement. The
side-down-validation.json report verifies the current module transforms,
negative Z extent and absence of intersection with the carrier envelope. `variant-validation.json` and
the assembly's `body-scenes-validation.json` record source/output hashes.
Simulation and CAD checks do not establish physical fit, acoustic performance,
vibration isolation or mechanical strength. No fabrication release is claimed.

Sources and attribution: Rev B microphone holder; retained Adafruit MAX9814
reference (Limor Fried/Ladyada, CC BY-SA 3.0; see
`../max9814-reference/source/license.txt`); generic KiCad connector geometry
(CC BY-SA 4.0 with library exception). New support arms are provisional geometry
for this installation.
