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

Exhibition build: backplane, five Thomas cards, Mega and measured DFRobot
carrier. Teensy follows with the analyser slot empty. The carrier is pending
module geometry; the old bare-chip analyser is not an approved substitute.
