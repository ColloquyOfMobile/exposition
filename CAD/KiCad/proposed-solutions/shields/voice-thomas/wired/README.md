# Voice filter shield: continuous-wire reading copy

Open `voice-thomas-wired.kicad_sch` in KiCad, or review the PDF. This is a
second schematic for the current `voice-thomas` shield. The original schematic
and PCB are retained. It is a presentation change, with no hardware change.

All five electrical nets are drawn as continuous wires. Text naming a signal
is an annotation only; it does not connect anything. Dots mark connections;
crossings without dots remain separate. Connector pins are ordered by their
role in the drawing, with the original physical pin numbers retained.

## Comparison with the original

No components, power symbols, test points, or electrical connections were added.
R1/R2, C1/C2, R3, JV1, TP1/TP4/TP5, and mounting hole H1 are all original.
All values, footprints, and connected pin groups are unchanged.
JV1 pin 5 remains unused; position 6 is the connector key, not a contact.
GND and AGND remain separate on this shield.

| Drawing change | Why? | Necessary? |
| --- | --- | --- |
| Continuous wires replace net labels | Let the reader follow the entire signal and return paths directly. | Yes, for the requested reading copy; no added hardware. |
| Connector pin names show signal roles | Make input, output, and the two returns easier to identify. | Optional aid; numbers remain authoritative. |
| Junction dots and a crossing legend | Distinguish connections from wire crossings. | Dots are necessary wherever wires join; legend is optional. |
| Section titles and explanatory notes | Explain the signal direction, unused pin, and separate returns. | Optional reading aids. |

## Validation and regeneration

Run `build_wired_schematic.py` with KiCad Python, then run
`verify_wired_schematic.py` with the same interpreter. The verifier exports
the original and wired schematics independently through KiCad, compares their
pin groups and component values/footprints, compares the connected pins to
`circuit.json` and the PCB, and runs ERC without suppressing violations.

Result: **17 connected pins, five electrical nets, JV1.5 unused, zero ERC
violations, no added components**. See `validation.json` and `erc.json`.
This establishes drawing equivalence; it is not a physical hardware test.

Export the reading PDF with:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe' sch export pdf -o 'output/pdf/voice-thomas-wired.pdf' 'CAD/KiCad/proposed-solutions/shields/voice-thomas/wired/voice-thomas-wired.kicad_sch'
```
