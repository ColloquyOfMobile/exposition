# Female base v2 — directly mounted GF1002 amplifier

Open `female-base-v2.kicad_pro` in KiCad 9. The project includes a schematic,
routed two-layer PCB, assembled STEP model, top/underside previews, BOM and
CAD verification reports. The original `../female base/` project is preserved.

The **amplifier module itself** mounts on this PCB. Thomas's green perfboard,
its JST sockets and blue terminal are absent. **Specification (revision D,
2026-10-19): the module plugs into a 1 × 11 female socket on this board
through male header pins on its contact row.** The socket carries every
connection, and two insulating supports hold the module level. The board
files in this folder are still **revision C**, in which six hand wires
connect the module to JA1. They are regenerated to revision D before
ordering. This is an engineering prototype based on the approximate GF1002
reference, not a physically qualified production release.

## Revision D specification: plug-in on header pins (2026-10-19)

The module plugs in the way the DFRobot modules plug into the analyser
carrier: male header pins on the module, a female socket on the board. It
comes out without desoldering. The contact positions come from
`../shields/gf1002-reference/README.md`.

**Socket.** One 1 × 11 female socket, 2.54 mm pitch, vertical
(`Connector_PinSocket_2.54mm:PinSocket_1x11_P2.54mm_Vertical`), placed on
the module's contact row. Its centre line is at X = 49.55 mm (module origin
+ 18.55 mm, the reference model's contact X). Pin 1 is at the pot end at
Y = 56.2 mm, and pin n is at 56.2 + 2.54·(n − 1), so pin 11 is at 81.6 mm.
Solder all eleven socket pins for strength; positions 4 and 7 have no
module pin.

**Module.** Fit straight 2.54 mm male headers through positions 1–3 (1 × 3),
5–6 (1 × 2) and 8–11 (1 × 4), plastic underneath. Solder them while they
sit in the socket, so they line up with it. Thomas's carriers already have
pins in these holes, so standard header pins should pass; check one module.

| Socket pin | Module contact | Net |
|---:|---|---|
| 1 | input R | `AMP_INPUT` |
| 2 | input G | `AUDIO_RETURN` |
| 3 | input L | none |
| 4 | no contact | none |
| 5 | power + | `5V` |
| 6 | power − | `GND` |
| 7 | no contact | none |
| 8, 9 | LOUT pair | none |
| 10, 11 | ROUT pair | `AMP_OUT_P`, `AMP_OUT_N`, to J6 |

The photo doesn't show which of pins 10 and 11 is ROUT+. Read it on the
module and record it; J6 pin 1 is ROUT+. Swapping them only inverts the
speaker's phase. No output contact, ROUT or LOUT, is ever connected to
ground.

**Height.** The shields use the same stack, a 2.5 mm male header plastic on
an 8.5 mm female socket (`../shields/ASSEMBLY.md`). It puts the module's
underside about **11 mm** above the board, 8 mm higher than revision C's
3 mm. The pot then stands about **28 mm** above the board, and the shaft
rises by the same 8 mm. Check both inside the female body before ordering.
Any part under the module must be lower than the socket body.

**Supports.** H1 (shaft edge, (28.5, 74.5)) and H2 (short end, (41.1, 87.5))
stay where they are. They become supports at the stack height, measured on
the header and socket actually bought. The socket fixes where the module
sits, so the supports' seats must allow ±0.5 mm, the photo's uncertainty in
the row's offset. Their lips may stay, but the module must come out after
loosening them. H1 takes the push when the knob is turned or pressed, so
the knob doesn't lever the socket.

**Removed from revision C.** JA1 and its six wires; the instruction to cut
the pin tails flush; the rule area that keeps pads out of the contact strip.
The socket sits in that strip now, and no other part or via may.

**Schematic and checks.** The GF1002 becomes a 1 × 11 connector symbol
with the nets above, and no-connect flags on pins 3, 4, 7, 8 and 9. ERC and
schematic/PCB parity then cover the module's connections. `verify_boards.py`
checks the socket's position against the reference model's contact row,
and every pin's net.

### Routing rules

1. **Class-D output.** The ROUT pair (pins 10, 11) runs to J6 side by side,
   as short as the layout allows, in the Power class as now. Thomas's
   document asks for short speaker leads: the output is a ~250 kHz PWM
   signal with sharp edges and high currents.
2. **Keep the output away from every input.** Put ground, as a pour or a
   track, between the output pair and `AMP_INPUT`, `LINE_IN`,
   `AUDIO_RETURN`, the microphone line and the photosensor lines. They may
   cross only at right angles, never run alongside. Revision C on this
   board runs the output 20.7 mm alongside `AMP_INPUT`, within 2 mm, on
   the same layer.
3. **Input.** `LINE_IN` and `AUDIO_RETURN` run together from J7 to the
   divider. R1 and R2 sit beside socket pins 1 and 2, so `AMP_INPUT` is
   only a few millimetres long.
4. **Supply.** `5V` and `GND` reach pins 5 and 6 in the Power class. C2
   (100 nF) sits directly beside pins 5 and 6, with C1 (220 µF) close by;
   revision C has them about 30 mm away. C2 may sit under the module if it
   is lower than the socket body.
5. **The grounds meet only on the module.** `AUDIO_RETURN` goes to pin 2
   only and `GND` to pin 6; nothing else on this board joins them. Check
   with a meter that the module's G and − contacts are joined on the module
   itself (expected). If they are not, stop and decide before ordering.
6. **Unused contacts.** Pins 3, 4, 7, 8 and 9 have no net.

### Before ordering

Measure one module:
- the row's offset from its edge and the first contact's distance from the
  pot end (these place the module against H1, H2 and the outline; the
  pitch is the socket's);
- that a header pin passes its holes;
- the stack height of the chosen header and socket;
- the pot overhang, and the knob's height inside the body.

Then plug the module into a socket on a 1:1 print of the revision D board.
`../shields/RELEASE_REVIEW.md` F8 stays open until then.

## Mechanical arrangement

The original **50 × 80 mm** outline, rounded corners, two Ø8 mm artwork
fixing cutouts and DSUB footprint/pad positions are retained exactly.
The artwork fixing centres remain (50,47) and (50,90) mm in PCB coordinates.
The conservative module envelope runs from (31,55) to (51.2,85) mm.
New Ø2.2 mm clamp screw holes are at (28.5,74.5) and (41.1,87.5) mm;
H2 points towards the short edge, away from the contacts. All coordinates here use the
PCB editor's +X right, +Y down; the outline's upper-left extent is (25,20).

In revision C the module has a provisional **3 mm underside gap** above the main PCB.
With its assumed 1.6 mm PCB, its top is 4.6 mm above the carrier top.
Clamp seats support the edges; lips retain them from above. The clamps are
shown in 3D, and provisional STEP/STL bodies are in `3dmodels/`. Use insulating
M2 screws, nuts and clamps; determine screw length from the actual stack.
The artwork's existing fixings remain separate from these two new fixings.

The volume shaft faces left and extends approximately **16 mm beyond the
main board's left edge**. The reference assembly needs approximately
**20 mm above the carrier top** at the volume-control body. Check these
clearances inside the actual female body, together with cable access and
artwork fastener access. Module envelope (20.2 × 30 mm), underside components,
knob dimensions and clamp fit need measuring on the physical GF1002.
The clamp's nominal 1.6 mm slot is provisional; adjust fit/tolerance and
support geometry after measurement. No mating solder footprint is assumed.

## Contact-row clearance revision C (2026-10-19), as drawn now; superseded by D

The GF1002 reference now shows nine contacts along the long edge opposite
the shaft, on an eleven-position 2.54 mm grid with positions 4 and 7 empty.
Its contact coordinates are photo estimates with about 0.5 mm uncertainty.
The 20.2 × 30 mm module envelope conservatively allows the seller's
20.2 × 29.5 mm size. Physical dimensions remain unverified.

H1 stays at (28.5, 74.5). H2 has moved to (41.1, 87.5), rotated 90 degrees to retain
the short edge away from the pot. The contact-side strip is clear of
clamps, screws, components and hookup pads along the full module length.
Native rule areas exclude pads and vias from that strip. The nearby
reservoir and bypass components have moved to clear the new clamp.

JA1 is beside the contact row at (54.5, 66.5), keeping the six individual hookup
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

The smaller JST connectors have moved to clear the module. Their references,
pin orders, drills and electrical purposes are retained: J2 mirror servo,
J4 photosensor, J5 NeoPixel, J3 microphone and J6 speaker. Consult the
schematic and assembly drawing when making the new board's internal leads.

## Audio and power

The DSUB J7 retains its exact physical pinout, with this change in function:

| J7 pin | v2 function |
|---|---|
| 12 | LINE_IN, formerly remote amplifier speaker + |
| 4 | AUDIO_RETURN, formerly remote amplifier speaker − |
| 15 | 5 V supply, unchanged |
| 8 and shell pads | Supply GND, unchanged |

**The rack must supply line-level audio and audio return on the former
speaker pair before this board is connected.** The original rack class-D
speaker output must be disconnected from that pair. J6 now connects only
to the local GF1002 output, never directly to J7.

R1=22K and R2=3K3 reproduce Thomas's input divider. The divider's bottom and
the module's input-ground wire use AUDIO_RETURN. The module supply-ground
wire uses GND. These are separate PCB nets; the amplifier's internal ground
connections and resulting return currents require bench verification.
Both copper faces have local GND pours, with full pad connections; isolated
islands are removed. AUDIO_RETURN has its own routed connection.

Revision C only; in revision D the socket replaces JA1 (table above).

| JA1 pad | Short wire to the identified module connection |
|---|---|
| 1 | VDD, from harness 5 V |
| 2 | Supply GND |
| 3 | Audio input, after the divider |
| 4 | Input GND / audio return |
| 5 | ROUT+ |
| 6 | ROUT− |

JA1 is a set of **carrier-defined solder pads**, not a direct mating header
for the GF1002. Verify the module contacts before attaching wires. In
revision C the 3D module's contacts are not connected by the carrier circuit.
J6 pin 1 is ROUT+, pin 2 ROUT−; neither speaker terminal is grounded.

The GF1002 branch is connected to **5 V only**. The existing 12 V net serves
the servo and does not reach JA1. A 220 µF/10 V local reservoir and 100 nF
bypass are fitted; reservoir sizing is provisional. This does not establish
the GF1002's supply rating or the shared harness's current capacity. Check
rail sag, clipping and noise with the actual module, speaker and harness.

## Rebuild and verification

Shared scripts in `scripts/` regenerate this project and `../male static v2/`:

```powershell
& 'C:/Program Files/FreeCAD 1.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/build_clamps.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/build_boards.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/route_boards.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/finish_boards.py'
& './CAD/KiCad/female base v2/scripts/export_boards.ps1'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/verify_boards.py'
```

Routing uses the existing local Freerouting 2.4.1 jar and Android Studio Java
paths declared in the script. Rebuilding replaces the v2 schematic and board.
`*-placed.kicad_pcb` is the unrouted checkpoint. `circuit.json` records the
circuit and positions; `reports/` contains ERC, DRC, native schematic parity,
netlist and SVG exports. No fabrication package is released at this stage.

Validation covers native ERC/DRC, completed routing, schematic/PCB parity,
unchanged original artwork cutouts and DSUB pad positions, original connector
pin order/drills, 5 V amplifier wiring and local model resolution. STEP
assemblies were reopened and checked; top and underside previews inspected.
Physical fit, electrical performance and installation clearances remain
unverified. The schematic models the GF1002 as a wire-connected module,
so ERC does not validate its undocumented internal circuit or solder pads.

Revision C validation (2026-10-19): native ERC/DRC/unconnected/parity 0/0/0/0;
independent contact-strip, clamp-position, harness and original-geometry
checks pass (`reports/validation.json`). The full repository suite passes
1,796 tests. STEP assemblies reopen with valid geometry; previews inspected.

Sources: original repository body-board designs; Thomas's documentation
and the photo-derived `../shields/gf1002-reference/` model. Generic KiCad
library models retain their CC BY-SA 4.0 license with the library exception.
