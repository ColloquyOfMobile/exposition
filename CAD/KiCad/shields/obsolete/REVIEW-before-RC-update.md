# SHIELDS specification review — 2026-10-05

Source: `Source code/Python/colloquy/hardware/electronics/SHIELDS.md`, dated
2026-10-03, and the completed v2 circuit and fixed mechanical geometry.
This directory contains five PCB projects; the Mega and U2D2 are purchased
modules, not additional PCB designs. Existing installation harness boards do
not change. Firmware 5 is separate work and has not been implemented here.

## Direct-microphone specification update

Implements SHIELDS.md's 2026-10-05 revision. The direct analyser PCB and its
MCP6004 filters are removed. Each microphone branches through 4.7K on the
backplane to a new Mega-footprint contact D26-D30, with 1M to AGND and a
labelled MIC DIRECT test pad. The adapter takes these to Teensy GPIO14-18
(A0-A4), with 1nF C0G to GND beside each socket contact on B.Cu.

The adapter leaves Mega A0-A4, D3, D4 and IOREF unconnected. GPIO34/35 are
now spare test pads. The MSGEQ7 shield receives MEGA_5V at JA1 pin 19;
backplane JA1 pins 20/21 are GND. JA1 is left empty with the Teensy.
The eleven photosensor dividers and translated outputs are unchanged.

Identification remains silkscreen only. Voice connectors are keyed 2x3 and
JA1 is keyed 2x11. The voice cards are 30 x 42 mm; the MSGEQ7 shield is
150 x 55 mm. Fixed harness positions, body order and complete voice-card
population tables are retained. Body order is female1, female2, female3,
male1, male2. Slot solder-mask openings are present on both faces.

Build priority: backplane + five Thomas cards + MSGEQ7 with the Mega;
then Teensy adapter with JA1 empty; then active-card corners 1414, 4000,
8000, 250, 500. Other corners are optional later builds.

## Manufacturer checks

* TI's [SN74LV4T125 datasheet](https://www.ti.com/lit/ds/symlink/sn74lv4t125.pdf)
  specifies 3.3-to-5V translation and partial-power-down Ioff support. The
  adapter uses SN74LV4T125PWR in TSSOP-14, USB-derived VIN supply, grounded
  active-low enables, and grounded unused input. Each package has 100nF bypass.
* [MSGEQ7 manufacturer datasheet](https://mix-sig.com/images/datasheets/MSGEQ7.pdf):
  supply 2.7–5.5V; pin 6 is its internal reference and is bypassed, never tied
  directly to ground. The oscillator resistor is supplied from MEGA_5V.
* [MCP6024](https://www.microchip.com/en-us/product/mcp6024) is the 10MHz
  rail-to-rail active-card amplifier, using the SOIC-14 quad pinout.
* [PJRC Teensy 4.1](https://www.pjrc.com/store/teensy41.html) documents the
  3.3V-only input range and USB/VIN power constraint. The adapter draws from
  VIN; it never feeds VIN. A Schottky points from VIN toward MEGA_5V.
  The selected [Diodes 1N5819HW](https://www.diodes.com/part/view/1N5819HW)
  is SOD-123; this avoids assigning the larger SS14 package to SOD-123 lands.
* The project-local PPS footprint is the earlier reviewed Panasonic 6041
  pattern. See the [Panasonic ECHU catalogue](https://mediap.industry.panasonic.eu/assets/imported/industrial.panasonic.com/cdbs/www-data/pdf/RDI0000/ABD0000C173.pdf).

## Qualification still outstanding

The revised specification requires the rack supply and computing USB to be
powered together, and the boards carry that instruction. The circuit does
not provide powered-off isolation:

1. Eleven 100k/150k dividers limit current from live photosensors into an
   unpowered Teensy, but do not isolate its pin clamps. Nominal current limits
   are not a proof against phantom powering, including the aggregate current.
2. The microphones are DC coupled through 4.7K into Teensy inputs. This
   limits injection current but does not establish safe overvoltage or
   powered-off operation. The MAX9814 output figures at a 3.3V supply do
   not establish an absolute 2.45V ceiling for the modules powered at 5V.
   Measure their peaks and power transients; the specified resistor alone
   does not prove the spec's 5V-short-survival claim. The 34kHz RC pole
   also does not guarantee alias rejection at all sample rates or sounds.
3. The active card can receive a USB-powered 5V square while its own +5V rail
   is off. Its 15k input resistor likewise limits current without isolation.

The specified short-duration tolerance of asymmetric power has not been
validated on hardware. The sequencing instruction is implemented; the claim
that a one-minute interval is safe is not established by ERC/DRC. Step 1
uses the Mega, passive voice cards and AC-coupled MSGEQ7 analyser and does
not depend on qualifying the active-card or Teensy microphone paths.

The inherited backplane Mega footprint omitted its mounting holes. Four
peripheral 3.2mm holes are now added to both mating boards from Arduino's
official `MEGA2560_Rev3e.brd` CAD, with exact transforms recorded in
`mechanical.json`. Its two optional central holes are unused.

Still outstanding: enclosure front/back height, gold-contact part numbers,
keying plugs, stack heights, high-value C0G stock, photosensor calibration,
rail/current budget and the harness measurements remain physical checks.

The backplane is four-layer: F.Cu signals, In1.Cu GND/signal routes, In2.Cu +5V/signal routes, B.Cu signals and local AGND. The Teensy adapter is also
four-layer: F.Cu signals, In1.Cu GND/signal routes, In2.Cu signals, B.Cu
signals/GND. Audio cards are two-layer with an AGND pour. JP1 is still the
single passive GND/AGND bond. Plane connections are solid; finished copper
weight, laminate construction and permissible temperature rise must be set
with the fabricator. DRC does not qualify the 12V harness current or vias.

No hardware is attached or exercised by the generation and validation scripts.
ERC/DRC results cannot establish the powered-off, acoustic or mechanical tests
above. Follow SHIELDS.md section 10 for assembly and bring-up order.
