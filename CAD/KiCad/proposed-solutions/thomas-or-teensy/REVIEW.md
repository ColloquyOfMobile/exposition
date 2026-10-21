# Specification review and implementation decisions

Review date: 2026-10-01. Basis: `THOMAS_OR_TEENSY.md`, the completed v2
`circuit.json`, native board geometry, and the manufacturer sources below.
This project implements the two-mode PCB. Firmware, assembly, enclosure dry-fit,
and electrical qualification are separate work; they have not been performed.

## Corrections made while implementing

1. **The suggested SN74LV1T34 does not provide Ioff protection.** TI explicitly
   confirms this in its [product support response](https://e2e.ti.com/support/logic-group/logic/f/logic-forum/679969/sn74lv1t34-has-partial-power-down-operation).
   UB1–UB4 are **SN74LVC1T45DBVR**, with source-side VCCA, destination-side VCCB,
   DIR tied to VCCA, and 100k pull-downs on both ports. Its
   [datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc1t45.pdf) specifies Ioff
   and high-impedance ports when either supply is at ground. This also gives a
   specified 3.3V-to-5V UART level, instead of relying on a 5V CMOS threshold.
   Each supply pin has its own 100nF bypass.

2. **A series resistor limits injection; it does not prevent phantom power.**
   The [MCP6004 datasheet](https://ww1.microchip.com/downloads/aemDocuments/documents/MSLD/ProductDocuments/DataSheets/MCP6001-1R-1U-2-4-1-MHz-Low-Power-Op-Amp-DS20001733L.pdf)
   specifies input current limits, not powered-off isolation. UX1/UX2 are
   [TMUX1511PWR](https://www.ti.com/lit/ds/symlink/tmux1511.pdf), placed electrically
   **after the first 10k resistor and before the Sallen–Key feedback node**.
   Thus neither the input clamp nor the feedback capacitor has a path to a live
   microphone when Teensy power is absent. The switches follow TEENSY_3V3,
   independently of MODE. Both ears remain active whenever their processor has
   power. This is a deliberate deviation from the specification's entirely
   unswitched receive path. The first 10k still isolates the cable from local
   capacitance. Typical switch resistance is insignificant beside 20k; measure
   the final response and power-off leakage during bring-up.

3. **An exact 470nF PPS part must not be invented.** The verified
   [Panasonic ECHU(X) catalogue](https://mediap.industry.panasonic.eu/assets/imported/industrial.panasonic.com/cdbs/www-data/pdf/RDI0000/ABD0000C173.pdf)
   lists 150nF and 220nF at 50V, with 6041 bodies and D1/D4 recommended lands.
   C101/C102 each use a parallel **220nF + 220nF + 30nF = 470nF** network.
   The 220nF parts are ECHU1H224JX9; the 30nF parts are 1206 C0G, 5%, >=25V.
   The 400Hz stages use ECHU1H224JX9 and the 1kHz stages ECHU1H154JX9.
   The 47nF and 10nF stages use 1206 C0G, 5%, >=25V. No filter stage uses X7R.
   `PPS_6041` follows the manufacturer's 4mm inner gap, 7mm overall span,
   and 3.8mm pad height. Verify procurement and the assembly reflow profile.

4. **Thomas-only population still needs the relays.** An absent relay has no
   normally-closed contact. Fit K1–K3 even if the Teensy and DAC circuitry are
   deferred. Omitting the whole Teensy option is not electrically identical to
   leaving its socket empty. Fit the 100k source pull-downs with the translators.

5. **The mode is a command, not contact feedback.** D30 and Teensy pin3 report
   shunt voltage; they cannot prove that every relay moved. A stuck relay, missing
   board +5V, or a shorted driver can disagree with the requested mode. Use TPL1–5
   to inspect the actual selected signal. Changing a relay carrying a DC-biased
   Thomas signal can click; stop/mute voices before moving the shunt.

6. **Use four layers for the clock return paths.** The specification does not
   fix a layer count. The initial two-layer routing fragmented the ground fill
   beneath BCLK/LRCLK, despite passing connectivity and clearance checks. The
   finished 1.6mm board therefore adds two internal ground planes, each split
   into AGND and GND with JP1 as the only bond. The five I2S signals cross the
   split within 4mm of JP1. The relay-coil supply and return are routed outside
   the analog region; the supply is checked as a physical connectivity graph.
   `clock-ground-review.json` records sampled plane coverage; this is a geometry
   check, not an impedance calculation or signal-integrity simulation. Final
   dielectric construction and copper weight must be agreed with the fabricator.

## Confirmed choices and pin numbering

- [Omron G6K-2F-Y DC5](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf):
  non-latching DPDT, 5V/237-ohm coil, nominal 21.1mA each (63.3mA total),
  contact resistance <=100mOhm initially. Datasheet top view: coil +1/-8,
  NC2/7, COM3/6, NO4/5. The selected KiCad footprint uses that numbering.
  Minimum-load figures are reference reliability data, not a promise of noiseless
  switching at every arbitrarily small signal. Three SOD-123 flyback diodes have
  cathodes at +5V. QK1 is a 2N7002 driven at approximately 5V.
- [PCM5102APWR](https://www.ti.com/lit/gpn/pcm5102a): TSSOP-20; CPVDD1,
  CAPP2, CPGND3, CAPM4, VNEG5, OUTL6, OUTR7, AVDD8, AGND9, DEMP10,
  FLT11, SCK12, BCK13, DIN14, LRCK15, FMT16, XSMT17, LDOO18, DGND19,
  DVDD20. All three ground pins share local AGND. Each supply has 100nF+10uF;
  charge-pump capacitors are 2.2uF and LDOO has 100nF. Outputs have 470R/2.2nF.
- [TLV75533PDBVR](https://www.ti.com/lit/ds/symlink/tlv755p.pdf): SOT-23-5,
  IN1/GND2/EN3/NC4/OUT5; 500mA rating. EN follows VIN and there are 10uF input
  and output capacitors. Its rating does not establish the Teensy's USB current
  budget; measure the assembled load. VIN is never fed by the carrier.
- MCP6004-I/SL: SOIC-14. Three filters and one grounded-input spare follower per
  package. The nominal filter is approximately 10.73kHz, Q=0.742, with 10k/10k,
  2.2nF feedback and 1nF shunt. Six 100R/1nF ADC networks are at the socket.
- [PJRC pin card](https://www.pjrc.com/teensy/card11a_rev4_web.pdf) and
  [dimensions](https://www.pjrc.com/teensy/dimensions.html): two 24-pin rows,
  2.54mm pitch, 15.24mm separation, approximately 60.96 x 17.78mm module.
  JT1/JT2 pad1 are at the USB end. **Socket pad numbers are not GPIO numbers.**
  The current card shows a 200mA external 3.3V figure; this design's op-amps and
  translators are well below that, while DACs use the separate VIN-fed regulator.
  Check the actual fitted module's revision. MCLK23, OUT1D6 and LED13 are NC.

## Preserved interfaces

All pads on J5/J1/A-J3/B-J4/J2/J6/J7/Extra1/Extra2/Extra3 retain the v2 net
assignments. All previously connected Mega pads are unchanged; only D18, D19,
and D30 become connected. The five build-outs are still 100R after the relay
common. JP1 alone bonds AGND to GND, and JP2–JP6 retain the five audio returns.
All fixed footprints, rotations, the 210 x 297mm outline, and nine NPTH holes
come from the completed v2 board. Mega is underneath; Teensy is on the front.
The external amplifier rail choice and provisional photosensor loads remain open.

## Required hardware acceptance

- Current-limited power and continuity tests for every combination of board,
  Mega USB and Teensy USB supplies. Confirm no phantom rail with any lead absent.
- Thomas mode with Teensy removed: firmware4 and the existing audio tests.
- Blank/resetting Teensy: XSMT low and no DAC output until deliberately enabled.
- Bench microphone/DC bias and bench line output, then all five channels in both
  modes. Start at the five Thomas pitches and about -7.5dBFS / 2.5Vpp.
- Measure anti-alias response, ADC acquisition/crosstalk and five-channel USB
  sampling throughput. 44.1kSPS per microphone is a target, not a measured result.
- Full harness test with servos and pixels active, rail drop and connector heat;
  microphone source impedance/cable capacitance, and amplifier clipping.
- Mechanical dry-fit of the third USB cable, standoffs and underside Mega.

No firmware, physical measurements, supplier inventory, or installation current
rating is established by KiCad's electrical and geometrical checks.
