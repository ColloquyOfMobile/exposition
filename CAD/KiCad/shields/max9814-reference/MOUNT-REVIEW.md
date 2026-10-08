# Review of the microphone support for the artwork

Reviewed 2026-10-08 against `../microphone/microphone.kicad_pcb`,
`Source code/Python/colloquy/hardware/electronics/MICROPHONE_BOARD.md`,
and the new violet MAX9814 module reference.

**The existing support cannot take the violet module as drawn.** It is a
complete replacement microphone circuit, with a bare MAX9814 and electret
capsule. Its attachment to the artwork is a useful starting point for a
module carrier, but module mounting and interconnection still need designing.
No production PCB or artwork geometry was changed during this review.

## Findings

1. **The module has no fixing points on the current carrier.** The existing
   board is 20 × 62 mm with two Ø5.5 mm non-plated holes on its centreline,
   50 mm apart. Those are for the artwork's M5 T-nuts. The violet module
   instead has two Ø2.2 mm plated holes, 10.033 mm apart, and a 1×5 header.
   Neither its mounting holes nor its connector exists on the current PCB.
   Overlaying the module would also conflict with the existing circuit parts.
   Use a dedicated carrier revision; do not drill the routed board to suit.

2. **The downward header needs more clearance than short spacers provide.**
   In the reference model its tips are 7.6 mm below the module's top face,
   or **6.0 mm below its underside**. A 3 or 5 mm module-to-carrier gap would
   put the pins into the carrier unless they enter a matching socket or
   through holes. Set the height from the actual socket's seated geometry,
   with the module supported independently by two insulating spacers. If
   the pins hang freely above the carrier, reserve more than 6 mm clear gap;
   a provisional 7 mm underside gap leaves 1 mm margin in this model.
   Check the fitted header and socket before specifying spacer lengths.

3. **Large washers do not fit beside the capsule.** The closest mounting
   centre is 7.186 mm from the capsule centre; with its 4.801 mm radius,
   the remaining radial space is 2.385 mm. A Ø5 mm washer overlaps the
   capsule envelope by approximately 0.115 mm. The holes are also only
   2.032 mm from the board edges. A fixing head no larger than Ø4 mm fits
   within both limits, with approximately 0.385 mm capsule clearance and
   0.032 mm edge margin. Use small-head M2 insulating fixings and check
   their actual envelope. Avoid a metal fixing path from the module's
   plated holes to the artwork; the reference does not establish those
   holes' electrical isolation on the physical sample.

4. **The M5 length calculation does not prove the screw cannot bottom out.**
   The documented stack is 1 mm washer + 1.6 mm PCB + 5 mm spacer, so
   M5×12 leaves 4.4 mm for the T-nut. That arithmetic is correct. Actual
   thread engagement and remaining slot depth depend on the chosen nut
   and extrusion, neither of which has a dimensioned drawing here. The
   document's assertion that this cannot reach the slot floor is unverified.
   Measure the nut seating depth and available screw travel on each profile;
   select the screw length after that check.

5. **Nylon spacers establish electrical separation, not measured vibration
   isolation.** The rigid screw/washer stack can transmit servo vibration.
   Merely replacing the spacers with rubber leaves that screw path. If
   vibration appears in recordings, evaluate compliant bushes/shoulder
   washers as a complete fixing arrangement, with controlled compression,
   then compare servo-running and servo-still recordings. No isolation
   performance can be inferred from this CAD review.

## Geometry that can be retained

The current M5 fixing geometry is internally consistent: both holes are
non-plated, 50 mm apart, with Ø12 mm copper/part keep-outs on both faces.
There are no bottom-mounted components. The Ø10 mm washer/spacer envelope
has 1 mm radial allowance within those keep-outs. The 5 mm carrier-to-frame
stand-off is separate from the module-to-carrier spacing discussed above;
through-hole lead protrusion must still be checked after assembly.

For a revised carrier, orient the module's **25.4 mm side along the
62 mm support**, leaving its 14.097 mm width centred across the 20 mm
support. This leaves 2.9515 mm on each side. Mount the capsule facing the
room; retain the harness connector order GND / +5V / OUT.

A possible planar placement, measured from the support's upper-left
outline corner, is below. It is a layout study, not a released drill
template. Header/socket and screw body heights remain to be selected.

| Feature | X (mm) | Y (mm) |
|---|---:|---:|
| Artwork M5 fixing 1 | 10 | 6 |
| Artwork M5 fixing 2 | 10 | 56 |
| Module outline upper-left | 2.9515 | 17 |
| Module outline lower-right | 17.0485 | 42.4 |
| Module M2 fixing 1 | 15.0165 | 19.032 |
| Module M2 fixing 2 | 4.9835 | 19.032 |
| Capsule centre | 10.0635 | 24.239 |
| Header GND | 14.8895 | 41.003 |
| Header Vdd | 12.3495 | 41.003 |
| Header Gain | 9.8095 | 41.003 |
| Header Out | 7.2695 | 41.003 |
| Header AR | 4.7295 | 41.003 |

The module outline stays outside the two existing M5 keep-out discs.
The existing bare-chip circuit would be replaced by the module connector
and any deliberately retained carrier circuitry. Gain and A/R connections
must reproduce the existing bench straps; pin names alone are insufficient
to assume the carrier's old straps still connect to the new module.

## Evidence and limits

The existing board's outline, hole centres/drills, footprint inventory and
mounting keep-outs were inspected with KiCad's Python API and the repository's
verification code. Module geometry comes from the imported Adafruit source;
head/capsule clearances were calculated from those coordinates. The physical
sample's dimensions, frame profile, fixings and vibration behaviour remain
unmeasured. The new reference remains a mechanical study.
