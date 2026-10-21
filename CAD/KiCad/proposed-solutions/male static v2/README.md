# Male static v2 — directly mounted GF1002 amplifier

## Manual placement reroute (2026-10-20)

`male-static-v2.kicad_pcb` is routed from the user's updated
`male-static-v2-placed.kicad_pcb`. All component positions, rotations, pad
nets and the artwork outline are retained. The socket runs horizontally;
the speaker connector is at (48.5, 89) mm. The 0.8 mm front-copper speaker
pair bends around C1, and photosensors C/D use reserved back-copper paths
along the left edge. Supply GND pours are refilled on both copper layers;
AUDIO_RETURN stays a separate net.

Native DRC reports **zero violations and zero unconnected items**. Schematic
parity reports the two supports H1/H2 missing, as in the edited placement;
they remain in the schematic. They have not been restored or relocated.
The placement's distant R1/R2/C2 positions are also retained: the earlier
short-input and close-decoupling geometry checks below do not describe this
layout. Physical fit, amplifier stability and noise have not been checked.

Current results are in `reports/validation.json` and `reports/drc.json`.
`preview.png`, `underside.png`, the STEP model, assembly SVG and production
Gerbers have been refreshed. The previous revision D notes below are design
history; their coordinates, support layout and route lengths are superseded.
`circuit.json` also records that earlier generated placement.

To reproduce this routing, run from the repository root:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/old-reference/male static v2/scripts/route_placement.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' export_gerbers.py
```

The route script uses the local Freerouting jar in `tmp/shields-tools/`.
The shared `build_boards.py`, `route_boards.py` and `verify_boards.py` still
describe the earlier generated revision D placement; rebuilding with them
would overwrite the manual placement or assert the earlier geometry.

## Earlier revision D design notes

All eleven connectors now have names on the front silkscreen: microphone,
DXL BODY, speaker, state LED, body/bar NeoPixels, harness, and photosensors
A/B/C/D (J9/J8/J1/J4). See
[`reports/connector-names.png`](<reports/connector-names.png>). Labels are shared
with the full board builder through `../female base v2/scripts/connector_labels.py`.

**C1 SMD update (2026-10-20).** C1 is now a polarized 220 µF / 10 V SMD
aluminium electrolytic in `Capacitor_SMD:CP_Elec_6.3x5.8`, centred at
(68.2, 71) mm. Pad 1 is positive / 5 V; pad 2 is GND. The 6.3 × 5.8 mm case
stays outside the module envelope. Local supply routing and ground fill have
been adjusted for its surface pads. C2 stays 100 nF / 0603. An example part
is [Panasonic EEEFN1A221UP](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-smd/models/EEEFN1A221UP);
match the purchased part's land pattern and assembly requirements. The 220 µF
value remains provisional pending amplifier/harness measurements.

A second, continuous-wire schematic is available in
[`wired/male-static-v2-wired.pdf`](<wired/male-static-v2-wired.pdf>), with an
editable KiCad project beside it. It preserves revision D's circuit without
electrical labels. [`wired/comparison.md`](<wired/comparison.md>) explains each
element added since the original male static board and whether it is necessary.

Open `male-static-v2.kicad_pro` in KiCad 9. This new project includes the
schematic, routed PCB, assembled STEP model, previews, BOM and verification
reports. The original `../male static/` files are preserved.

The **GF1002 module itself** mounts on the main board; Thomas's perforated
prototype carrier is absent. **Specification (revision D, 2026-10-19): the
module plugs into a 1 × 11 female socket through male header pins on its
contact row**, as on the female base. The schematic and board files now implement **revision D**, with M1 as
the electrical socket, no JA1 hookup pads and no hand wires. The board is an
engineering prototype, subject to physical module and installation
measurements.

## Revision D: plug-in on header pins (2026-10-19)

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
- **Output**: J6 moved to (67,90), rotated −90 degrees. Its pin 2 is
  at (67,92.5). Both 0.8 mm front-copper paths are explicitly paired in
  the lower-right region, with a grounded guard on their input side.
- **Supply**: C2 is at (54.7,67.63), below socket pins 5 and 6 on the
  module side; the SMD C1 is at (68.2,71), outside the module envelope.
- **Input**: R1 is at (53,56.2), R2 at (54.8,58.74). The incoming line
  and return approach together on back copper from the upper board.

## Implemented layout and mechanical interface

The original 50 × 90 mm artwork outline, cutouts and exact DSUB pad/drill
positions are retained. Original connector pin orders are unchanged.
The module uses the same photo-derived 20.2 × 30 mm conservative envelope.
H1 and H2 retain their specified PCB hole positions. Their new insulating
support models have an 11 mm seat, a 1.8 mm module slot, short removable
retaining lips and a 3.2 × 2.2 mm screw slot for ±0.5 mm adjustment.
Select insulating M2 hardware and measure the actual socket/header stack
before printing/fitting the supports. No amplifier PCB drilling is required.

The socket's 8.5 mm body and nominal 2.5 mm header plastic put the module
underside at 11 mm and its PCB top at 12.6 mm above the carrier. Pot height
is approximately 28 mm; the shaft overhang is approximately 7 mm beyond
the board's left edge. Confirm both against the installed body.
Only low-profile divider/bypass parts sit under the module. The SMD C1
reservoir stays outside its envelope. All eleven socket pins are soldered;
module male headers populate positions 1–3, 5–6 and 8–11 only.

The socket alone occupies the contact strip. Native rule areas forbid
vias there; independent checks reject other components or pads in it.
The old pad-exclusion rule and flush-cut-pin instruction are removed.
To remove the amplifier, loosen the support lips and unplug the headers.

R1/R2 sit beside socket pins 1/2. C2 is less than 5 mm from both supply
contacts, with C1 nearby. Main supply and speaker routes use the 0.8 mm
Power width; short 0.25 mm necks enter the 0603 bypass pads. The input
pair approaches on back copper, with AMP_INPUT confined to the divider
and socket. A front grounded guard and ground pours separate the lower
output region from the input and sensor region. No output is grounded.

Speaker paths are 15.582/16.597 mm; the complete AMP_INPUT branch is 7.265 mm.
Independent checks find no parallel sensitive runs within 2.5 mm and no
output/input or sensor crossings in projection, including across layers.
Reports record geometry and source hashes in `reports/validation.json`.
Native ERC/DRC/unconnected/parity are all zero. These CAD checks do not
establish noise performance, current capacity or physical fit.

Inspect the updated STEP, previews and 1:1 templates before the mandatory
real-module fit, stack-height, ground-bond and output-polarity checks.

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

M1 follows the female board's socket table: pin 1 R input, 2 audio return,
5 harness 5 V, 6 supply GND, 10 provisional ROUT+, 11 provisional ROUT−.
Pins 3, 4, 7, 8 and 9 have no connections and schematic no-connect flags.
Confirm the actual ROUT pair polarity and module ground bond before ordering.

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
