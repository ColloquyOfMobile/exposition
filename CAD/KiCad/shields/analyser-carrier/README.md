# Direct-plug DFRobot analyser carrier

Five modified DFR0126 Audio Analyzer V2.0 modules plug directly into this
150 x 55mm carrier. Each site has one gold 1x6 female socket and one gold
1x2 female socket, both 2.54mm pitch. Downward male headers on the modules
mate with them; no module-to-carrier cables are used. The carrier's keyed
JA1 connector and two retention holes still match the backplane.

**Unmodified modules must not be plugged in.** The output is brought to the
unused left-input header by the following conversion, authorized by the user.
The white output connector can remain fitted but is unused.

## Convert each module

1. With power disconnected, remove **module R4, the 22K left-input summing
   resistor**. This is on the DFRobot module, not the carrier. If reference
   markings differ, identify the resistor between L and the input summing
   node from the schematic/continuity before removing it. Leave R3 (right
   input) and the MSGEQ7 clock/reference parts in place.
2. Link the now-isolated **L signal terminal to OUT**, using a short insulated
   jumper on the module's component side. OUT is MSGEQ7 pin 3 and the signal
   contact of the white output connector. Do not connect it to +5V or GND.
   R4 must be removed first; otherwise this feeds output back into the input.
3. Refit the input connector positions as a downward-facing 1x6 male header
   (or two aligned 1x3 headers) and the control connector as a downward-facing
   1x2 male header. All eight mating pins point toward the carrier. Mark L as
   OUT permanently. The L input is no longer available for audio.
4. Before power, check continuity OUT-to-converted-L, supply polarity at the
   mating pins, and isolation of converted L from the removed R4 summing-side
   pad. Check there is no solder bridge between +5V and ground.
5. Seat the module fully in both sockets, then select nylon standoffs/shims
   matching that seated PCB gap. Do not force a predetermined spacer height
   against the sockets. M3 hardware retains the module; it does not pull the
   connectors into alignment. Module 0 is rotated 180 degrees.

DFRobot's V2 schematic identifies R4 as the left branch, R3 as the right,
and U1.3 as OUT:
https://dfimg.dfrobot.com/wiki/17648/DFR0126_msgeq7-spectrum-analyzer-module_schematics_V1.pdf

## Socket mapping

The table describes the carrier component-side view in each module's local
coordinate frame. The round mounting hole is (0,0); the slot is (20.32,0).
Module 0 rotates this complete pattern 180 degrees; the others do not.
Coordinates are **photo-derived assumptions**, not a manufacturer land pattern.

| Contact | Local X mm | Local Y mm | Signal / module marking |
|---|---:|---:|---|
| 1 | 3.81 | -5.08 | OUT, formerly L |
| 2 | 6.35 | -5.08 | +5V (left group) |
| 3 | 8.89 | -5.08 | GND (left group) |
| 4 | 11.43 | -5.08 | R microphone input |
| 5 | 13.97 | -5.08 | +5V (right group) |
| 6 | 16.51 | -5.08 | GND (right group) |
| 7 | 17.78 | 17.78 | R reset |
| 8 | 20.32 | 17.78 | S strobe |

All module +5V contacts use MEGA_5V; all module grounds use AGND. No digital
GND bond is added. The original microphone signal still feeds the R input.
ANA0-4, AGND and MEGA5V probe pads remain accessible. Leave the carrier out
when the Teensy adapter is fitted.

## Photo-derived fit

The user authorized using the supplied photographs and standard pitch on
2026-10-07. The adopted grid has 2.54mm pin pitch and 22.86mm row separation.
Header offsets relative to holes, group ordering/orientation and the 20.32mm
hole spacing are inferred and require a physical fit/polarity check. The
29 x 32mm module envelope is also estimated. A 3.2mm hole and 5.74 x 3.2mm
slot allow mounting adjustment, but **slots do not correct socket misalignment**.

Print mounting-template.svg at 100%, verify its 50mm scale, then compare all
eight module pins and both mounting holes. Confirm against one converted
module before manufacturing the set. This is an engineering prototype, not
a fit-verified fabrication release. Native DRC does not prove connector fit.
mechanical.json preserves these assumptions; socket-assembly.csv lists hardware.

M1-M5 in the KiCad BOM are composite module/socket assemblies. Fit the purchased
modules after soldering sockets to the carrier; do not solder the modules to it.
Use carrier.py to regenerate, then route.py, finish.py, planes.py, check.py and
verify.py. The latter independently checks all eight mating pad positions/nets.
