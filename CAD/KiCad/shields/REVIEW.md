# Engineering review — 2026-10-08

Current basis: SHIELDS.md at 79e994b and MICROPHONE_BOARD.md. These are editable
engineering prototypes; native checks do not constitute fabrication release.

The analyser carrier uses user-authorized photo inference from Thomas's
2.54mm-grid setup: nominal module mounting pitch 20.32mm, one round hole
and one tolerance slot. Its 150 x 55mm outline and existing JA1/retention
coordinates are preserved. Module 0 rotates 180 degrees to clear JA1.
See analyser-carrier/README.md and its 1:1 mounting template. The module
outline, screw fit, standoff height and socket alignment still need physical
confirmation; this is not a manufacturer-verified land pattern.

Voice cards now contain only Thomas's two RC sections and 100K pull-down.
Four pitch components are THT; no op amp or active-filter supply remains.
Capacitor selection must fit the 7 x 6.5mm, 5mm-pitch film envelope.

Microphone revision B carries the existing violet MAX9814 module on a 1x5
female socket. Module contacts and M2 holes match the local Adafruit reference;
actual clone geometry remains unverified. R1 straps Gain to Vdd (40dB), R2
straps AR to GND (1:500); supply filtering and output build-out remain.
Artwork holes retain 50mm spacing, 5.5mm NPTH and 12mm keep-outs. Module
holes are 2.2mm NPTH, 10.033mm apart, with 6mm keep-outs. Rule areas allow
their own NPTH; independent checks reject other pads inside. Use insulating
M2 supports, <=4mm heads, and match spacer length to the seated socket/header
(11.04mm nominal). Verify M5 travel and clearance on the actual profile.
Nylon does not establish vibration isolation. See microphone/README.md.

Teensy microphones remain DC coupled through 4K7/1M on the backplane and
1nF at each adapter ADC input. A resistor limits injection current but does
not prove powered-off or 5V-short survival. MAX9814 output figures at 3.3V
do not establish an absolute 2.45V ceiling at 5V. Measure peaks/transients,
power sequencing, ADC settling and alias rejection on the real assembly.
Eleven photosensor dividers also limit current without providing isolation.

The four-layer backplane has GND and +5V inner pours interspersed with signal
tracks; they are not uninterrupted planes. The adapter also has four layers.
Voice uses a bottom AGND pour; microphone a bottom GND pour. JP1 remains the
only backplane AGND/GND bond. Finished copper, stackup, current/temperature
rise, EMC, connector height/keying and enclosure fit need qualification.
Mega mounting coordinates come from Arduino MEGA2560_Rev3e.brd; see
mechanical.json. Preserve the fixed harness pinout and locations.

The computing slot is now on the front with mirrored contacts/holes. USB and
power-jack rule areas prohibit pads and vias. +12V uses outer layers only,
with every trace at least 2mm wide. DRC and the interface checker enforce
these constraints. HM1-HM4 require <=4mm OD front spacers/posts and rear screw
heads; wide hex hardware clashes with the header bodies (ASSEMBLY.md).

No hardware was connected; follow SHIELDS.md bring-up instructions. Previous
component-selection notes for obsolete circuits are archived under obsolete/.

## Direct-plug carrier revision — 2026-10-07

The analyser carrier now uses female sockets beneath modified modules. No
module-to-carrier leads remain. Each module requires removal of its left-input
22K resistor R4, an on-module jumper from isolated L to OUT, and downward
male headers. Read analyser-carrier/README.md before assembly. Socket positions
are photo-derived; check all contacts against the updated 1:1 template.
