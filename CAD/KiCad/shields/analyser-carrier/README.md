# DFRobot DFR0126 analyser carrier

Routed KiCad 9 carrier for five purchased Audio Analyzer V2.0 modules, in
body order F1, F2, F3, M1, M2. The 150 x 55mm outline, underside keyed JA1
socket and two carrier retention points match the existing backplane.
No bare MSGEQ7 chips or additional input conditioning are fitted.

The user authorized deriving mounting geometry from the module and Thomas
protoboard photos on 2026-10-06, assuming standard 2.54mm pitch. The adopted
hole spacing is **eight pitches, 20.32mm**. This is an inference, not a caliper
measurement or manufacturer mechanical drawing. Each module gets a 3.2mm
round hole and a 5.74 x 3.2mm NPTH slot, giving nominal longitudinal spacing
adjustment from 19.05 to 21.59mm with a 3.2mm locating diameter. Actual screw
clearance adds some play. The reserved module envelope is 29 x 32mm.
Physical fit, hole diameter on the module and actual body outline are unverified.

Module 0 is rotated 180 degrees to clear the underside JA1 socket's mounting
hardware; the other four share one orientation. Fit M3 nylon standoffs, nominal
10mm high, and insulating hardware. Check clearance to module solder joints,
carrier socket tails and the supplied leads. Use the module's existing headers;
do not force them into a guessed matching socket footprint.

## Wiring

All carrier headers below are **2.54mm male headers on the top**, with pin 1
marked by a square pad. Numbers are carrier pin numbers, not a claim about
the original white connector's numbering. Use short leads, matching actual
signal labels. Use the module's supplied output lead, re-pinning its carrier
end if needed to match this table; never assume cable colours or orientation.

| Carrier connector | Pin 1 | Pin 2 | Pin 3 | Module destination |
|---|---|---|---|---|
| JI1-JI5 | body microphone | MEGA_5V | AGND | input R, +, -; L unused |
| JO1-JO5 | AGND | MEGA_5V | analyser output | module output connector GND, +5, signal |
| JC1-JC5 | RESET | STROBE | — | control R, S |

Each module's supply is MEGA_5V, not the rack +5V. Both connector power pairs
are on the same supply/return nets. Grounds stay AGND; JA1.20/21 digital GND
are unconnected. No new AGND/GND bond is introduced. JA1.22 is the blocked key.
ANA0-4, AGND and MEGA5V probe pads are accessible beside the modules.

Electrical mapping was checked against DFRobot's published V2 schematic:
https://dfimg.dfrobot.com/wiki/17648/DFR0126_msgeq7-spectrum-analyzer-module_schematics_V1.pdf
The photographs establish the installed board revision and mounting estimate;
the schematic establishes signal functions, not mechanical dimensions.

## Mounting check

Print mounting-template.svg at **100% / actual size**, not fit-to-page. Verify
the 50mm scale bar, then place a module over its hole pair and reserved outline.
The template is a fit check, not manufacturing artwork. If the module does
not fit, update carrier.py's geometry and rerun routing/DRC before fabrication.
mechanical.json records all assumptions and coordinates. Module origin is its
round hole; angle is 180 degrees for module 0 and 0 for modules 1-4.

Native ERC, DRC and connectivity pass. All five analyser nets, shared control,
slot pin locations and carrier retention coordinates are independently checked
by ../scripts/verify.py. Photos cannot validate assembled height or screw fit.
Leave the whole carrier and its modules out when using the Teensy adapter.

Regenerate only this board with ../scripts/carrier.py, then route.py,
finish.py, planes.py, check.py and verify.py. No fabrication release is implied.
