# Shields backplane: JLCPCB fabrication and SMD assembly

Upload gerbers.zip for the PCB. Then upload BOM.csv and CPL.csv for assembly.
Fit exactly the 72 Top-side SMD references in BOM.csv; Quantity is per PCB.
Each row specifies the manufacturer, exact orderable MPN and LCSC part number.
Do not substitute parts automatically. Check JLCPCB's current stock/assembly options.

All through-hole parts, plug-in modules and mounting hardware are hand fitted.
manual-and-DNP.csv lists every excluded reference and why. DNP means do not fit.
The U2D2 and screw/power hardware are not machine-placed SMD parts even where
their KiCad footprint attribute says SMD. The voice card is entirely through-hole,
including its 100K axial R3; all its parts are hand fitted according to variants.

CPL coordinates are mm using the same absolute origin as Gerbers and drills.
KiCad's exported Y convention is retained. Rotations are CCW degrees, 0 <= angle < 360.
Do not mirror supplied coordinates. reference/assembly-top.svg shows the layout.
Confirm the JLCPCB assembly preview before ordering: LEDs and Schottky diodes
have pad 1 = cathode; electrolytics pad 1 = positive; IC pin 1 must match the drawing.
The CPL applies only exact-part rotation corrections recorded in assembly-parts.json.
On the Teensy adapter, C90755 (SN74LV4T125PWR) adds 270 degrees to KiCad's
footprint rotation; U1-U4 are therefore 270 degrees. Confirm pin 1 at the upper-left pad in
the top view (2.8625 mm left and 1.95 mm above each footprint center).
Other parts retain their KiCad rotation. Verify the assembly preview before payment.

Backplane RP1-RP11 remain the designed provisional 10K population for calibration.
Body-board C1 remains the designed provisional 220uF/10V reservoir; the chosen
exact part is specified, but this does not settle amplifier transient tests.
Existing module-fit, connector-keying and enclosure checks still apply.
This file supersedes older bare-board/hand-SMD advice in reference documents.

Source: CAD/KiCad/proposed-solutions/shields/backplane/backplane.kicad_pcb
Source SHA256 (LF normalized): 6761e8a29f5aeea09b760586d4aad759f78cdb131f029cef4bdc257749015ec1
KiCad: 9.0.7. DRC: zero errors and zero unconnected items.
JLCPCB formats: https://jlcpcb.com/help/article/how-to-generate-bom-and-centroid-files-from-kicad-8
https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
