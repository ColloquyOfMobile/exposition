# Male static v2 — directly mounted GF1002 amplifier

Open `male-static-v2.kicad_pro` in KiCad 9. This new project includes the
schematic, routed PCB, assembled STEP model, previews, BOM and verification
reports. The original `../male static/` files are preserved.

The **GF1002 module itself** mounts on the main board; Thomas's perforated
prototype carrier is absent. **Specification (revision D, 2026-10-19): the
module plugs into a 1 × 11 female socket through male header pins on its
contact row**, as on the female base. The board files here are still
**revision C**: two insulating M2 edge clamps, and six hand wires to JA1.
They are regenerated to revision D before ordering. The board is an
engineering prototype, subject to physical module and installation
measurements.

## Revision D specification: plug-in on header pins (2026-10-19)

Everything in `../female base v2/README.md` under revision D applies: the
socket, the module's headers, the pin-to-net table, height, supports, what
is removed, schematic and checks, the routing rules and the measurements
before ordering. At this board's coordinates:

- **Socket**: centre line at X = 58.55 mm (module origin (40, 55) + 18.55).
  Pin 1 is at the pot end at Y = 56.2 mm, and pin n at 56.2 + 2.54·(n − 1).
- **Supports**: H1 (37.5, 74.5) and H2 (50.1, 87.5) become supports at the
  measured stack height, about 11 mm. The pot then stands about **28 mm**
  above the board, 8 mm higher than revision C, and the shaft rises with
  it. Check both inside the male body.
- **Output**: J6, the speaker, sits at (66.5, 47), about 33 mm from socket
  pins 10 and 11. Bring it closer if the layout allows; either way, the
  ROUT pair runs side by side. Revision C runs the output 9.4 mm alongside
  `AUDIO_RETURN` and 4.3 mm alongside `AMP_INPUT`, within 2 mm on the same
  layer; the routing rules forbid both.
- **Supply**: C2 sits directly beside socket pins 5 and 6 and C1 close by;
  revision C has C2 about 28 mm away, at (40.5, 88).
- **Input**: R1 and R2 move beside socket pins 1 and 2; revision C has
  them at (58, 90) and (58, 94).

## Mechanical interface

Revision C validation (2026-10-19): native ERC/DRC/unconnected/parity 0/0/0/0;
independent contact-strip, clamp-position, harness and original-geometry checks
pass (`reports/validation.json`). The full repository suite passes 1,796 tests.
STEP assemblies reopen with valid geometry; previews inspected.

- Original **50 × 90 mm** outline, rounded corners, Ø8 mm artwork fixing
  at (50,50) mm and lower open artwork slot are retained exactly.
- Original DSUB position, pad centres, drills and harness pin order retained.
- Provisional module outline: (40,55) to (60.2,85) mm.
- New Ø2.2 mm clamp holes: (37.5,74.5) and (50.1,87.5) mm.
- Module underside gap: 3 mm; module PCB top: 4.6 mm above main PCB
  (revision C; about 11 mm in revision D).
- Shaft points left, approximately **7 mm beyond the main board edge**.
- Reference height above carrier top: approximately **20 mm** at the pot.

Coordinates are PCB-editor +X right/+Y down; outline upper-left is (25,20).
The clamps' seats and retaining lips are included in 3D; provisional STEP/STL
parts are in `3dmodels/`. Use insulating clamps and M2 fixings. Confirm
module dimensions, underside clearance, slot fit, screw length and room for
the knob/cables inside the male body before making mating hardware.

## Contact-row clearance revision C (2026-10-19), as drawn now; superseded by D

The GF1002 reference now shows nine contacts along the long edge opposite
the shaft, on an eleven-position 2.54 mm grid with positions 4 and 7 empty.
Its contact coordinates are photo estimates with about 0.5 mm uncertainty.
The 20.2 × 30 mm module envelope conservatively allows the seller's
20.2 × 29.5 mm size. Physical dimensions remain unverified.

H1 stays at (37.5, 74.5). H2 has moved to (50.1, 87.5), rotated 90 degrees to retain
the short edge away from the pot. The contact-side strip is clear of
clamps, screws, components and hookup pads along the full module length.
Native rule areas exclude pads and vias from that strip. The nearby
reservoir and bypass components have moved to clear the new clamp.

JA1 is beside the contact row at (63.5, 74), keeping the six individual hookup
wires short. Connect AMP_INPUT to the module's **R input**, input return
to **G**, and the speaker to **ROUT**. Confirm +/− within the ROUT pair
on the actual module: the photo does not establish pair polarity.
No guessed mating header or through-hole pattern has been added.

**Cut existing module pin tails flush before mounting.** The retained
3 mm underside gap is for this assembly choice; long pins must not be
pressed against the carrier. Use insulating clamps and hardware.

Before ordering, measure the module width/length, row offset and first
contact, pin protrusion, pot overhang and clamp slot fit. Dry-fit the
real module on the updated 1:1 print. This revision resolves the drawn
contact/clamp conflict; it does not establish physical fit or release the
board for production (RELEASE_REVIEW.md F8).

Small connectors have moved to leave room for the module and shaft. J9 is
rotated 90 degrees; its pad order is retained. J3 remains microphone; J1,
J4, J8 and J9 remain the four photosensors; J5 is body NeoPixel, J11 is bar
NeoPixel, J10 is state LED, J2 is servo and J6 is speaker. The artwork's
existing fixing hardware is separate from the amplifier clamps.

## Audio interface

| DSUB J7 pin | v2 function |
|---|---|
| 14 | LINE_IN, formerly remote amplifier speaker + |
| 7 | AUDIO_RETURN, formerly remote amplifier speaker − |
| 9 | Harness 5 V, unchanged |
| 1 and shell pads | Supply GND, unchanged |

The rack must be converted to **line-level audio and audio return** on the
former speaker pair. Disconnect its original class-D output from that pair
before using this board. J6 now goes only to the local GF1002 output:
pin 1 ROUT+, pin 2 ROUT−, with neither terminal connected to ground.

In revision C (replaced by the socket in revision D), JA1's six solder pads connect by short wires: **1 VDD/5V, 2 supply GND,
3 divided Audio, 4 input GND/AUDIO_RETURN, 5 ROUT+, 6 ROUT−**. This is the
carrier's pad order; identify the physical module contacts independently.
The reference module's illustrative contacts do not define this wiring.

R1=22K/R2=3K3 reproduce Thomas's input divider. AUDIO_RETURN is routed
separately from the local supply GND pours; module-internal ground bonds
and return current behaviour need bench verification. The amplifier is
fed from harness **5 V only**; 12 V remains the servo rail. C1=220 µF/10 V
and C2=100 nF provide local decoupling. Reservoir sizing, the module's
actual supply rating, and shared harness current capacity remain to be
verified on the physical system.

## Regeneration and checks

The shared build, route, finish, export and verification scripts are in
`../female base v2/scripts/`. See that project's README for exact commands,
clamp assumptions, source attribution and assembly instructions.
`circuit.json` records component nets and positions; the unrouted placement
checkpoint is `male-static-v2-placed.kicad_pcb`. `reports/` contains native
ERC/DRC/parity results, netlist, schematic and assembly SVGs.

Native ERC and DRC, completed routing, schematic/PCB parity, retained original
outline/fixings/DSUB geometry, unchanged harness pin orders/drills, 5 V
amplifier connections and model resolution are checked. Exported STEP
assemblies were reopened and checked; top/underside previews inspected.
The module's undocumented internal circuit is outside ERC's scope.
Physical fit, acoustic/electrical operation and enclosure clearance have
not been established. No fabrication package is released at this stage.
