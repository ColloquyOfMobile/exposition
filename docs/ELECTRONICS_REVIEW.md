# Electronics Review and Next Steps

Reviewed 2026-09-27 against repository commit `59c4af3`.

**Design update, 2026-09-30:** the [v2 KiCad prototype](../CAD/KiCad/electronic%20box%20v2/colloquy-control-v2/README.md) now has a complete schematic, routed PCB, and fabrication exports. ERC, DRC, and native schematic/PCB parity pass with no findings. The historical assessment below predates that implementation; physical harness, sensor, amplifier, and enclosure validation remain commissioning work.

## Assessment

The electronics have a credible prototype architecture and useful bench evidence, but the proposed replacement board is not ready for fabrication. The immediate work is to complete the receiver circuit, establish the actual amplifier and power requirements, and demonstrate reliable audio over the installed harness. Those results should decide how much circuitry to centralize.

Keep three versions distinct: the original rack PCB, the physically reworked prototype, and the proposed v2 board. `AS_BUILT.md` describes the original copper, not a verified inventory of every subsequent cut, jumper, and fitted module. The replacement design has a generated parts/net model, but still needs an electrical schematic and layout.

## What Was Checked

- Original electronic-box KiCad schematic/PCB and its exported schematic PDF.
- V2 BOM, mechanical constraints, exported netlist, generator, and netlist tests.
- Harness routing, rework instructions, architecture alternatives, and recorded amplifier/microphone investigations.
- Thomas Erforth's design notes, especially printed pages 5-6 on amplification and detection.
- Manufacturer datasheets for MSGEQ7, TPA2005D1, and MAX9814.

KiCad 9.0.7 checks on the **original electronic-box files** produced:

| Check | Result | Interpretation |
| --- | --- | --- |
| PCB DRC | 0 unconnected items; 45 warnings | 13 footprint-library issues, 31 footprint mismatches, one back-layer text warning. Useful evidence about the stored old board, not a release check for v2. |
| Schematic ERC | 11 errors; 112 warnings | Errors are power-input pins not driven; warnings are library links/symbols and off-grid endpoints. Resolve supply modelling and library dependencies before relying on ERC as a gate. These messages alone do not prove a physical supply is absent. |
| V2 export inspection | 113 components; 30 with no net nodes | Five analyser ICs and 25 support components have no exported electrical connections. |

Checks wrote temporary reports only. No board was powered, measured, modified, or flashed. No full harness-board DRC or v2 schematic/PCB check was possible as part of this pass; the v2 folder contains only `BOM.md`, `NETLIST.md`, `MECHANICAL.md`, and `next_pcb.net`.

Library-related results depend on the review machine and its isolated KiCad configuration. They identify portability/reconciliation work, not a count of electrically defective components.

## 1. Complete the MSGEQ7 circuit before layout

This is the clearest fabrication blocker. In [next_pcb.py](../Source%20code/Python/colloquy/hardware/electronics/next_pcb.py), `_build_ears()` creates the input/clock/decoupling parts but does not connect them. In [next_pcb_kicad.py](../Source%20code/Python/colloquy/hardware/electronics/next_pcb_kicad.py), `UNNUMBERED` excludes every analyser terminal from export. A test explicitly preserves this unfinished state. Checking that existing nets have multiple ends does not detect components attached to no nets.

The model also needs a correct distinction between supply return and internal reference: the manufacturer's pinout names **VSS, pin 2**, as the supply return, while **GND, pin 6**, is an internally generated reference, typically 2.5 V. CKIN is pin 8. The current six-terminal model omits VSS and CKIN and attaches its terminal named GND to board AGND; it must be resolved before assigning real pad numbers. Do not map that terminal blindly. [MSGEQ7 datasheet, pages 2-4](https://mix-sig.com/images/datasheets/MSGEQ7.pdf).

**Next:** implement all eight pins, the complete coupling/reference/oscillator/decoupling network, and an explicit pin-to-pad map. Prototype one finished channel before replicating it five times. Add checks that all required pins and both terminals of each support part are connected, with explicit exceptions only for intentional no-connects.

**Ready when:** the channel works on the bench; its schematic matches the datasheet and actual selected package; the export contains its complete connectivity; no confirmation placeholders remain in the released circuit.

## 2. Freeze the amplifier identity and power plan

The repository contains different hardware that must not share an assumed rating:

- Original rack board: SparkFun TPA2005D1 breakouts.
- Thomas's prototype: GF1002 modules.
- Proposed body-mounted amplifiers: a selection still to be made.

The [incident report](errors/2026-09-01-01.txt) records a GF1002 destroyed when 12 V was applied. `NEXT_PCB.md` later reopens the supply decision, but its introduction and parts of `DIRTY_REWORK.md` still present 12 V as settled. The TPA2005D1 itself specifies a 2.5-5.5 V operating supply, with additional load-dependent restrictions; this is not evidence for a GF1002 module rating. [TI datasheet](https://www.ti.com/lit/ds/symlink/tpa2005d1.pdf).

**Next:** record the actual module/chip identity, supply limits, gain, input requirements, and speaker load. Reconcile all instructions. Recalculate the input divider and local decoupling for the selected module; the existing values are prototype choices, not automatically correct for a replacement amplifier. Check the signal channel implicated in the damaged-module incident before using it as a reference.

Do not extrapolate a transient-current allowance solely by scaling a different amplifier's power by voltage. Establish the load case and measure it.

## 3. Treat the shared power branch as a design constraint

[harness.py](../Source%20code/Python/colloquy/hardware/electronics/harness.py) traces `A-J3` pin 9 through the center board to female3, male1, and male2. Those three bodies therefore share an upstream 5 V conductor. `B-J4` carries signals, not a separate supply. Moving amplifiers to the bodies changes the branch load; choosing another rail changes which branch must be checked rather than eliminating the question.

**Next:** produce one power-tree drawing showing the source, connector contacts, cable gauge/length, copper widths, returns, and actual protection for every branch. Measure voltage at the farthest body during the intended simultaneous light, sound, and movement load, plus startup. Check connector/cable heating and current margins against the actual parts.

The generated v2 BOM contains no dedicated fuse, reverse-polarity, or surge-protection parts. That does not establish that the installation lacks external protection; it means the protection boundary is not captured in this board design. Document the existing protection, then specify any missing branch protection against the weakest rated wiring/component. Local bulk capacitance cannot substitute for adequate wiring or fault protection.

## 4. Prove both directions of the analogue link

Moving the class-D amplifier close to its speaker is well motivated: the existing arrangement sends switching speaker outputs down the harness. TI explicitly discusses output filtering for long speaker leads. Treat both speaker terminals as driven outputs; the old speaker-minus conductor must not become a ground return until the old amplifier output has been disconnected. [TI datasheet, section 9.3.3](https://www.ti.com/lit/ds/symlink/tpa2005d1.pdf).

The proposed replacement sends line-level audio outward and microphone audio back through the same harness. Test both, including the actual ground bonds and return paths. Merely naming nets `AGND` and `audio return` does not establish where current flows once single-ended modules and power returns are connected at the bodies.

There is a specific receiver-side constraint: the MAX9814 datasheet lists a **200 pF maximum capacitive drive**. The actual cable load has not been established here. Measure the installed cable capacitance and waveform response; determine whether output isolation or buffering is needed from those results and the module circuit. Its AGC also changes gain over time, so a steady-tone reading is insufficient to establish reliable message reception. [MAX9814 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX9814.pdf).

**Bench experiment:** instrument one complete channel through the longest real cable, with nearby NeoPixels and servos operating. Compare source and destination levels, clipping, interference, and microphone output. Then test every speaker-to-microphone combination at representative positions with realistic background noise and simultaneous callers. Record false detections, missed messages, and timing, not just whether a tone is audible.

Thomas's notes specifically leave speaker performance at 160 and 400 Hz for field testing. The repository's September microphone investigation also found a faulty module and ADC ghost readings from an open input. Use known-good modules and defined unused inputs when building the evidence.

## 5. Finish assembly details and make the design reproducible

Before ordering a v2 PCB:

- Resolve the 11 `TBC` light-sensor resistors by inspecting the installed circuit. Confirm topology as well as resistance: the generator assumes a shunt to AGND, while the existing documentation describes unknown fitted elements across break points.
- Specify component tolerances, voltage/power ratings, packages, and purchasable identities. Verify support-component connections as well as the BOM list.
- Capture the actual rework and up-ring identification in a dated wiring record. A firmware version does not verify that the physical jumpers match it.
- Make custom symbols and footprints available with the project; adjudicate library mismatches rather than blindly replacing embedded footprints.
- Complete the schematic, enclosure fit, support/mounting arrangement, current-carrying copper, and layout. The proposed A4 board currently inherits no dedicated mounting-hole scheme.
- Run ERC, schematic-to-PCB parity, and DRC on that completed revision; review any intentional exceptions; inspect final manufacturing outputs.

The documentation's statement that every decision is taken should be replaced with this explicit list of remaining release conditions.

## Architecture Recommendation

**Continue evaluating the centralized Mega/U2D2 design first**, because the firmware, pin assignments, test pages, and prototype are already present. This is a recommendation to finish and validate it, not to manufacture the current export.

If the full harness experiment passes, complete the central receiver board and body-mounted amplifier assemblies. If it fails, first determine whether a defined buffer/receiver/return-path change solves the problem; audible noise alone does not prove that a distributed redesign is necessary.

The per-body processor/RS-485 alternative remains a valid development option, but its documents still leave the bus protocol, programming access, sampling during NeoPixel updates, and embedded processing performance unresolved. Its 15% CPU estimate is not a measured complete-node budget. Prototype one node with the actual strips, sampling, communication, and processing together before committing to five. The OpenCM variation additionally needs a controller and defined communication-loss behavior; replacing the U2D2 does not by itself implement an independent stop.

## Recommended Next Electronics Work

| Order | Deliverable | Decision enabled |
| --- | --- | --- |
| 1 | Verified fitted-parts/rework inventory; corrected amplifier instructions | Which hardware and supply limits are actually being designed around |
| 2 | Power tree and loaded measurements on the shared three-body branch | Supply, wiring, connector, protection, and decoupling requirements |
| 3 | One complete audio channel through the real harness | Whether the centralized analogue architecture is viable |
| 4 | Complete MSGEQ7 schematic/prototype and light-sensor circuits | A genuinely complete v2 netlist and BOM |
| 5 | Five-channel acoustic/message tests under interference | Whether physical hearing meets the exhibition's agreed behavior |
| 6 | Schematic/layout release and assembly test procedure | Whether to order boards and commission the installation |

Steps 2-4 can progress alongside each other after the component/supply facts are settled. The most useful immediate bench result is a trustworthy complete audio channel under realistic load; the most useful immediate design result is completing the analyser circuit that is currently absent from the netlist.

## Local Source PDFs

- [Original schematic export](schematics.v1.pdf).
- [Thomas Erforth, Colloquy - Pask Redesign, 23 June 2026](../Source%20code/Thomas/Colloquy%20-%20Pask%20Redesign.pdf).
