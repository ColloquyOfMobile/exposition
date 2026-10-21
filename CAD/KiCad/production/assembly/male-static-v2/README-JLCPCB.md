# Male static v2: JLCPCB fabrication and SMD assembly

Upload gerbers.zip for the PCB, then BOM.csv and CPL.csv for assembly.
Fit exactly the 4 Top-side SMD references in BOM.csv; Quantity is per PCB.
Each row specifies the manufacturer, exact orderable MPN and LCSC part number.
Do not substitute parts automatically. Check JLCPCB's current stock/assembly options.

All through-hole parts, plug-in modules and mounting hardware are hand fitted.
manual-and-DNP.csv lists every excluded reference and why. DNP means do not fit.
The U2D2 and screw/power hardware are not machine-placed SMD parts even where
their KiCad footprint attribute says SMD. The voice-card R3 IS machine placed;
its pitch-dependent through-hole parts remain hand fitted according to variants.

CPL coordinates are mm using the same absolute origin as Gerbers and drills.
KiCad's exported Y convention is retained. Rotations are CCW degrees, 0 <= angle < 360.
Do not mirror supplied coordinates. reference/assembly-top.svg shows the layout.
Confirm the JLCPCB assembly preview before ordering: LEDs and Schottky diodes
have pad 1 = cathode; electrolytics pad 1 = positive; IC pin 1 must match the drawing.
The CPL contains footprint rotations; the assembler must verify its library's
reel orientation. No unverified global rotation correction has been applied.

Backplane RP1-RP11 remain the designed provisional 10K population for calibration.
Body-board C1 remains the designed provisional 220uF/10V reservoir; the chosen
exact part is specified, but this does not settle amplifier transient tests.
Existing module-fit, connector-keying and enclosure checks still apply.
This file supersedes older bare-board/hand-SMD advice in reference documents.

Source: CAD/KiCad/male static v2/male-static-v2.kicad_pcb
Source SHA256 (LF normalized): 54679c0808152b8f7bb86007bfc54a492216110ab05349565d3c06a81fd68858
KiCad: 9.0.7. DRC: zero errors and zero unconnected items.
JLCPCB formats: https://jlcpcb.com/help/article/how-to-generate-bom-and-centroid-files-from-kicad-8
https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
