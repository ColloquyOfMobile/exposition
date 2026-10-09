# Female base v2 — directly mounted GF1002 amplifier

Open `female-base-v2.kicad_pro` in KiCad 9. The project includes a schematic,
routed two-layer PCB, assembled STEP model, top/underside previews, BOM and
CAD verification reports. The original `../female base/` project is preserved.

The **amplifier module itself** mounts on this PCB. Thomas's green perfboard,
its JST sockets and blue terminal are absent. Two insulating M2 edge clamps
hold the module without drilling it; short individually identified wires
connect it to JA1. This is an engineering prototype based on the approximate
GF1002 reference, not a physically qualified production release.

## Mechanical arrangement

The original **50 × 80 mm** outline, rounded corners, two Ø8 mm artwork
fixing cutouts and DSUB footprint/pad positions are retained exactly.
The artwork fixing centres remain (50,47) and (50,90) mm in PCB coordinates.
The module outline runs from (31,55) to (51,85) mm. New Ø2.2 mm clamp screw
holes are at (28.5,74.5) and (53.5,74.5) mm. All coordinates here use the
PCB editor's +X right, +Y down; the outline's upper-left extent is (25,20).

The module has a provisional **3 mm underside gap** above the main PCB.
With its assumed 1.6 mm PCB, its top is 4.6 mm above the carrier top.
Clamp seats support the edges; lips retain them from above. The clamps are
shown in 3D, and provisional STEP/STL bodies are in `3dmodels/`. Use insulating
M2 screws, nuts and clamps; determine screw length from the actual stack.
The artwork's existing fixings remain separate from these two new fixings.

The volume shaft faces left and extends approximately **14 mm beyond the
main board's left edge**. The reference assembly needs approximately
**20 mm above the carrier top** at the volume-control body. Check these
clearances inside the actual female body, together with cable access and
artwork fastener access. Module size (20 × 30 mm), underside components,
knob dimensions and clamp fit need measuring on the physical GF1002.
The clamp's nominal 1.6 mm slot is provisional; adjust fit/tolerance and
support geometry after measurement. No module solder-pad pitch is assumed.

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

| JA1 pad | Short wire to the identified module connection |
|---|---|
| 1 | VDD, from harness 5 V |
| 2 | Supply GND |
| 3 | Audio input, after the divider |
| 4 | Input GND / audio return |
| 5 | ROUT+ |
| 6 | ROUT− |

JA1 is a set of **carrier-defined solder pads**, not a direct mating header
for the GF1002. Verify the module contacts before attaching wires. The 3D
module's four illustrative contacts are not used by the carrier circuit.
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

Sources: original repository body-board designs; Thomas's documentation
and the photo-derived `../shields/gf1002-reference/` model. Generic KiCad
library models retain their CC BY-SA 4.0 license with the library exception.
