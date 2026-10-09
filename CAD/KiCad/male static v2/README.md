# Male static v2 — directly mounted GF1002 amplifier

Open `male-static-v2.kicad_pro` in KiCad 9. This new project includes the
schematic, routed PCB, assembled STEP model, previews, BOM and verification
reports. The original `../male static/` files are preserved.

The **GF1002 module itself** mounts on the main board using two insulating
M2 edge clamps. Thomas's perforated prototype carrier is absent. Short
individually identified wires connect the module to JA1; an assumed module
solder-pin pattern is not used. The board is an engineering prototype,
subject to physical module and installation measurements.

## Mechanical interface

- Original **50 × 90 mm** outline, rounded corners, Ø8 mm artwork fixing
  at (50,50) mm and lower open artwork slot are retained exactly.
- Original DSUB position, pad centres, drills and harness pin order retained.
- Provisional module outline: (40,55) to (60,85) mm.
- New Ø2.2 mm clamp holes: (37.5,74.5) and (62.5,74.5) mm.
- Module underside gap: 3 mm; module PCB top: 4.6 mm above main PCB.
- Shaft points left, approximately **5 mm beyond the main board edge**.
- Reference height above carrier top: approximately **20 mm** at the pot.

Coordinates are PCB-editor +X right/+Y down; outline upper-left is (25,20).
The clamps' seats and retaining lips are included in 3D; provisional STEP/STL
parts are in `3dmodels/`. Use insulating clamps and M2 fixings. Confirm
module dimensions, underside clearance, slot fit, screw length and room for
the knob/cables inside the male body before making mating hardware.

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

JA1's six solder pads connect by short wires: **1 VDD/5V, 2 supply GND,
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
