# Assembly

One Thomas RC voice PCB is used for both Mega and Teensy. Default population
is female1: R1=R2=1K2 and C1=C2=150nF. The five body BOMs and thirteen pitch
BOMs are in voice-thomas/variants; variants.csv lists all values and windows.
R1/R2 are axial metal film, 1%, 0.25W, 7.62mm lead pitch. C1/C2 are radial
PET/PP film, 5%, >=50V, 5mm pitch; the reserved body envelope is 7 x 6.5mm.
Select actual capacitors within this envelope (including 470nF). No ceramic
substitution. Optional machine-pin sockets use the same holes. R3 is 100K
0603. Slot +5V is unused. Write pitch/body on front and tick the back table.

Test headers are individual gold 1x1 2.54mm pins: 26 backplane, 3 adapter,
2 per voice card. The microphone adds MICOUT/GND, 2.54mm apart. Backplane
12V has an empty grid position either side. Eight LEDs are on the backplane:
three green supply indicators and five yellow tone indicators.

Build six microphone boards, five plus a spare. JP1 GAIN defaults to VDD
(pins 2-3, 40dB); JP2 A/R defaults to GND (pins 1-2, 1:500). Order two shunts
per board. U1 exposed pad and NC4/NC11 go to GND. J1 is GND/+5V/OUT.
Confirm the stocked electret's polarity and pin spacing before fabrication;
the 9.7mm/2.5mm footprint is provisional. Two M5 x 12 ISO7380 screws,
10mm washers, 5mm-high nylon spacers (10mm diameter) and profile-matched T-nuts
mount each PCB. Keep the frame electrically isolated. Check assembled height.

Use gold contacts on mating headers; remove male key 6/22 and block the
matching socket cavity. Voice sockets are on B.Cu. Teensy input caps CM1-CM5
are on B.Cu; microphone components are all on F.Cu. Use insulated M3 standoffs
for shield retention. Computing USB and rack power switch together; unplug
both before swapping cards. Verify numbering and rail isolation before power.

The Mega or Teensy adapter goes on the DSUB/front face. Mega components and
female sockets face the backplane; the Teensy adapter's sockets face the
backplane and its Teensy faces outward. The male/female plastic stack is
nominally 11 mm (2.5 + 8.5 mm); verify the selected connectors when choosing
post length. The USB end remains at the top edge.

For HM1-HM4 use M3 posts/round spacers **no more than 4 mm outside diameter
on the front**; fit screw heads on the back. Standard wide hex standoffs or
front washers conflict with the nearby headers at HM2/HM3. The custom
mounting footprints retain 3.2 mm holes, a 4.1 mm front courtyard and 6.9 mm
rear screw-head courtyard. Confirm hardware fit during the enclosure dry fit.
Do not place pads, vias or test pins beneath the Mega USB/power housings.

Exhibition build: backplane, five Thomas cards, Mega and measured DFRobot
carrier. Teensy follows with the analyser slot empty. The carrier uses photo-derived module mounts; use its 1:1 template to
confirm fit. Module 0 is rotated 180 degrees. Fit the converted modules to the carrier sockets using its README pin table.
The old bare-chip analyser is not an approved substitute.

## Direct-plug carrier revision — 2026-10-07

The analyser carrier now uses female sockets beneath modified modules. No
module-to-carrier leads remain. Each module requires removal of its left-input
22K resistor R4, an on-module jumper from isolated L to OUT, and downward
male headers. Read analyser-carrier/README.md before assembly. Socket positions
are photo-derived; check all contacts against the updated 1:1 template.
