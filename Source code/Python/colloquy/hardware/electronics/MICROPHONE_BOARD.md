# The microphone holder board

**One 20 × 62 mm holder per body, carrying the existing violet MAX9814
module and screwing onto the body's aluminium extrusion.** Revision B,
2026-10-08, replaces the former bare-chip microphone PCB with a removable
five-pin socket and two insulating M2 supports. No separate MAX9814 or
electret is fitted to the holder. Build six holders, five and a spare.

Open `CAD/KiCad/old-reference/microphone-rev-b/microphone.kicad_pro`. Module dimensions
come from Adafruit's original CAD, retained in `max9814-reference/source/`.
Confirm the physical violet module's mounting/pin grid before fabrication.

## 1. Attachment to the artwork

The **20 × 62 mm** rounded outline is retained. Two **5.5 mm** non-plated
M5 clearance holes are on the long centreline, **50 mm apart**, 6 mm from
each end. Keep-out: 12 mm round each hole, both faces, no copper or parts.
The holder PCB is 1.6 mm FR-4, two layers, with no bottom-mounted parts.

Use M5 washers (10 mm outside diameter, nominal 1 mm thick), 5 mm high
nylon spacers (10 mm outside diameter) and profile-matched T-nuts.
M5 × 12 leaves **4.4 mm** below the spacer for the nut. This is an
engagement allowance, not proof the screw cannot bottom out. Check the
nut seating depth and remaining screw travel before selecting its length.
Keep the frame electrically isolated from circuit ground.

The frame has no dimensioned drawing here. Earlier videos suggest
20-series T-slot profiles; measure face width and slot opening before
choosing T-nuts. Existing harness mounts remain the reference:
`female base` two, 43 mm apart; `female static` two, 50 mm;
`male static` one and a slot, 50 mm; `center` two, 70 mm.

Nylon provides electrical separation. Vibration isolation is unverified:
the screw path can transmit servo motion. If recordings show frame noise,
test a complete compliant bush/washer arrangement with servos moving/still.

## 2. Mounting the violet module

The 25.4 × 14.097 mm module runs along the holder's length, capsule facing
the room. Its two holes are **10.033 mm apart**. The holder has matching
**2.2 mm NPTH** holes with 6 mm keep-outs. Use insulating M2 supports
and heads **no larger than 4 mm**. Do not fit 5 mm washers beside the capsule.

M1 is a **1×5 female socket, 2.54 mm pitch**. With the upper artwork
fixing at the top, its contacts run right to left: GND, Vdd, Gain, Out, AR.
Check the actual module's printed labels before applying power.

**Match spacer length to the seated socket/header combination.** The
3D model uses 8.5 mm socket body + 2.54 mm header collar, giving an
**11.04 mm module-to-carrier underside gap**. This is a nominal reference,
not an instruction to force an 11 mm spacer into place. Check insertion
depth and use suitable spacers/shims so the module sits without bending.
The 5 mm frame spacers beneath the holder are a separate fixing stack.

## 3. Circuit and connector

| Ref | Fit | Purpose |
|---|---|---|
| M1 | existing module and 1×5 female socket | 1 GND; 2 Vdd; 3 Gain; 4 Out; 5 AR |
| R1 | 0 Ω | Gain to module Vdd: 40 dB, bench setting |
| R2 | 0 Ω | AR to GND: 1:500, bench setting |
| R4, C7 | 33 Ω; 22 µF X5R 10 V | harness +5V to filtered module Vdd |
| C6 | 100 nF | extra module supply bypass |
| R5 | 470 Ω | raw module MICOUT to harness OUT |
| D1, R6 | green LED; 2.2 kΩ | incoming 5V indicator, before filter |
| J1 | JST EH 3, B3B-EH-A | existing harness connection |
| TP1, TP2 | single 2.54 mm pins | MICOUT and GND |

There are no JP1/JP2 shunts. Change a strap by removing its 0 Ω link and
deliberately wiring the alternative; never connect supply and ground
together on Gain/AR. Do not duplicate conflicting straps on the module.

| J1 pin | Signal |
|---|---|
| 1 | `GND` |
| 2 | `+5V` |
| 3 | `OUT` |

This is unchanged on `female base` J3 and `male static` J3. Use a
pin-1-to-pin-1 lead. Output stays DC coupled through R5: the module's
approximately 1.23–1.25 V resting bias remains available for diagnostics
and the backplane's direct input. Measure peaks and receiver headroom.

For nominal 3.1 mA amplifier current the retained supply filter has
a 219 Hz corner for a 0.10 V drop. With an assumed 1 nF cable load,
the corner is 339 kHz for R5. These `microphone_board.py` calculations
are design estimates, not measurements of the physical module.

## 4. Assembly and checks

1. Assemble holder parts and headers; verify harness and module pin order.
2. Seat the module with power off; dry-fit both insulating M2 supports.
   Check head clearance, insertion depth and module underside clearance.
3. Mount on insulating frame spacers; trim tails clear of aluminium and
   confirm neither M5 screw bottoms out.
4. Apply 5 V: D1 lights, TP1 reads the resting bias, and J1 OUT shows the
   same DC level. Check audio and servo noise before fitting all five.
5. Capsule faces the room, roughly 10 cm from its own speaker where the
   body permits; keep cable away from speaker and NeoPixel wiring.

ERC/DRC, schematic/PCB parity and module pin/hole alignment are checked
in CAD. Physical fit, fasteners, profile depth and acoustic behaviour
remain bench checks. This is an engineering prototype.
