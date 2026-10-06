# DFRobot DFR0126 analyser carrier — awaiting measurements

SHIELDS.md section 4b explicitly requires measuring one purchased module
before drawing this carrier. No PCB or guessed module footprint is supplied.
The former bare-chip analyser is in ../obsolete and is not the new design.

Record dimensions in mm relative to one board corner:
- Exact outline; all hole centers and diameters.
- Each header pin center, pitch, side, orientation and labelled pin order.
- Output connector type/pin order, lead exit direction and module height.
- M3 nylon standoff clearance and chosen height.

The carrier may exceed 150 x 55 mm. Recheck its backplane/card/enclosure
clearances after measurement; the old backplane analyser envelope and two
retention holes are provisional and must be reviewed with the new carrier.

Five sites in order: module 0 female1, 1 female2, 2 female3, 3 male1, 4 male2.
For site i=0..4, JA1 odd pin 2i+1 goes directly to module input R (right),
input L is unused; input + to JA1.19 MEGA_5V; input - to AGND.
Module control S to JA1.17 strobe; control R to JA1.18 reset.
Output signal goes to JA1.11+i through its supplied lead; verify that lead's
pin order against the actual module. JA1.2/4/6/8/10/16 carry AGND,
JA1.20/21 are GND, JA1.22 is the removed key. Never join AGND and GND here.
Use through-hole parts only, module standoffs, labelled ANA0-4/MEGA5V/AGND
probe pads. Leave the complete analyser slot empty with the Teensy.
