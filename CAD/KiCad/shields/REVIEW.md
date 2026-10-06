# Engineering review — 2026-10-05

Current basis: SHIELDS.md at 2d9fe1d and MICROPHONE_BOARD.md. These are editable
engineering prototypes; native checks do not constitute fabrication release.

The analyser carrier uses user-authorized photo inference from Thomas's
2.54mm-grid setup: nominal module mounting pitch 20.32mm, one round hole
and one tolerance slot. Its 150 x 55mm outline and existing JA1/retention
coordinates are preserved. Module 0 rotates 180 degrees to clear JA1.
See analyser-carrier/README.md and its 1:1 mounting template. The module
outline, screw fit, standoff height and lead routing still need physical
confirmation; this is not a manufacturer-verified land pattern.

Voice cards now contain only Thomas's two RC sections and 100K pull-down.
Four pitch components are THT; no op amp or active-filter supply remains.
Capacitor selection must fit the 7 x 6.5mm, 5mm-pitch film envelope.

Microphone U1 is MAX9814ETD+, TDFN14 with exposed ground pad. Pin assignment
was checked against Analog Devices' MAX9814 datasheet:
https://www.analog.com/media/en/technical-documentation/data-sheets/max9814.pdf
Pins 4/11 and EP are grounded; SHDN is tied to VDD. Bias, threshold divider,
AGC capacitors, gain/A-R jumpers and output resistor follow the spec.
The 9.7mm capsule part number is still open: the supplied 2.5mm-pitch pattern
is provisional. Confirm polarity, lead spacing, sensitivity and body height
against the purchased capsule before fabrication. Hole centers are 50mm
apart, 5.5mm NPTH, with 12mm-diameter copper/part exclusion on both faces.
Rule areas allow the NPTH itself; independent checks reject other pads inside.
Nylon spacer/frame fit and acoustic effects require physical testing.

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

No hardware was connected; follow SHIELDS.md bring-up instructions. Previous
component-selection notes for obsolete circuits are archived under obsolete/.
