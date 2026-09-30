# Circuit decisions — revision A prototype

The inherited `../next_pcb.net` defines the fixed Mega firmware and four-connector harness mapping. `circuit.json` completes that design and is the connectivity contract for this new KiCad project. The old generator does not generate this completed project. `scripts/build_schematic.py` uses only Python's standard library and never imports the installation's runtime.

## Audio receivers

Each socketed MSGEQ7P uses the manufacturer's DIP pin assignment: **1 VDD, 2 VSS, 3 OUT, 4 STROBE, 5 IN, 6 internal GND reference, 7 RESET, 8 CKIN**. Pin 6 is approximately half the supply voltage; it connects only to its local 100 nF reference capacitor, whose other terminal is AGND. It is never directly grounded. A separate 100 nF capacitor bypasses VDD to VSS. The clock uses 200 kΩ and nominal 33 pF; the manufacturer's 33 pF value includes stray capacitance. Check frequency after assembly and adjust the C0G capacitor if necessary. [MSGEQ7 manufacturer datasheet](https://mix-sig.com/images/datasheets/MSGEQ7.pdf).

R111/R211/R311/R411/R511 (47 kΩ) and the corresponding 6.8 kΩ shunts attenuate microphone signals by approximately 0.126 before 100 nF AC coupling. A 2 Vpp input becomes approximately 0.25 Vpp, providing useful margin against MSGEQ7 saturation. JS1–JS5 are **open by default**; bridge a jumper only after measuring a weak microphone signal and receiver headroom. Bypass still presents at least 6.8 kΩ to the microphone, above the MAX9814's 5 kΩ minimum load specification. [MAX9814 manufacturer datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX9814.pdf).

Five passive two-stage transmit filters retain the specified values and Mega timer pins. Each has a 100 Ω output resistor and separate audio-return link. Body amplifiers and microphones remain external assemblies; their power rating is not established by this PCB.

## Power and harness corrections

- J2 accepts **regulated 5 V, center positive**. J7 is GND / 12 V / Dynamixel data. Verify actual mating-part polarity before energizing.
- External `+5V` and `MEGA_5V` remain separate. Every Mega 5 V pad belongs to the latter; all Mega GND pads join GND.
- RS1 pulls reserved D2 up to **MEGA_5V**, correcting the old external-5 V pullup that could feed an unpowered Mega through its I/O protection.
- All same-polarity J6 lugs are assigned: 1/2/4 GND; 3/5/6 external +5 V. M1 is a padless U2D2 mount; the real electrical connection is J7.
- B-J4 carries **no supply power**. Existing center-board power distribution and harness current limitations remain applicable.
- PWR_FLAG symbols declare the externally supplied rails and AGND bond for ERC. They are not regulators, fuses, or protection devices. Use a suitably current-limited external supply.

## Provisional assembly values and verification

RP1–RP11 are replaceable **10 kΩ** photosensor shunts. This is a provisional design choice, not a measurement of the existing installation: measure the old board and recalibrate before deployment. JP1 is the single AGND-to-GND link; JP2–JP6 separately bond each body audio return.

The project includes explicit electrical pin types, 48 intentional unused Mega pads, local symbols and footprints, and a ten-sheet schematic. After exporting the root schematic's netlist, run `python scripts/verify_schematic.py exported.net --pcb colloquy-control-v2.kicad_pcb` to compare every connected pad against both `circuit.json` and the PCB. ERC/DRC and this comparison verify design-file consistency; they do not substitute for polarity, current, sensor and audio measurements on the assembled installation.
