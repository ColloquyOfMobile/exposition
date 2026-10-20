# Teensy adapter: continuous-wire reading copy

This second schematic represents the current `teensy-adapter.kicad_sch`
hierarchy, not a revised circuit. The original schematic, circuit manifest and
PCB are retained unchanged. The editable copy is `teensy-adapter-wired.kicad_sch`;
the PDF is a vector A1 landscape sheet intended for zooming or large printing.

## Added electrical elements

**None.** All 81 components retain their original references, values, footprints
and connections. No extra resistor, capacitor, diode, buffer, connector, test
point or power source is required for this copy.

## What looks different, and why

| Drawing change | Why it is shown this way | Necessary? |
| --- | --- | --- |
| Continuous wires replace all electrical net labels | Follow a signal directly between the Teensy socket and backplane socket without finding matching labels on other pages. | Required by the requested reading format; no hardware change. |
| JT1, JT2 and JM1 appear as several lettered units | Group contacts into outputs, sensors, microphones, power, spare GPIO and unused contacts. Pin numbers still identify the physical contacts. Each reference is ONE existing socket, regardless of its unit letter. | Optional for readability; no additional sockets. |
| U1-U4 appear as four gate units and one supply unit each | Put each buffer channel directly in its signal path. The E unit shows the same chip's supply pins. | Optional for readability; still four chips total. |
| Ground branch wires, junction dots and two ground trunks | Show each pulldown, shunt capacitor and output-enable connection explicitly. The two trunks are visibly joined below the microphone section. Crossings without dots remain separate. | Required to express the original shared ground using wires. No new grounding connection. |
| Signal captions, GPIO/ADC captions and section headings | Explain the purpose of each wire and group. These are ordinary text, with no electrical connectivity. | Optional reading aids. |
| Unused contact units with X marks | Show the manifest's unused contacts in one place, including contacts not instantiated in the original's spare-contact drawing. | Optional completeness aid. These remain unconnected; no contacts or components are added to the PCB. |
| Two PWR_FLAG diamonds | Retain the original `supplies.kicad_sch` declarations that GND and VIN_USB are supplied externally. They let KiCad check buffer power inputs without false missing-supply errors. | Needed for the same clean ERC declarations; no physical parts or power sources. Already present in the original. |

The diode, all input divider/filter parts, buffer pulldowns, decoupling capacitors,
microphone shunt capacitors and GPIO test points already exist in the original.
Their presence in this drawing is not a new design recommendation.

## Independent checks

Run from the repository root with KiCad 9's Python:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/shields/teensy-adapter/build_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/shields/teensy-adapter/verify_wired_schematic.py'
```

The verifier exports both schematic netlists through KiCad independently of the
drawing generator. It compares connected pin groups (ignoring KiCad's optional
isolated NC records), checks that unused pins are not connected, compares all
component values and footprints, and compares the manifest with PCB pad nets.
PCB `{slash}` escaping is decoded for the comparison. It also checks that the
copy contains zero electrical labels and has zero ERC violations.

Result: **81 components, 276 connected pins, 71 nets, zero electrical labels,
zero ERC violations**. See `validation.json` for source hashes and results.
The original's letter-based test point references TPV/TPI/TPG are retained;
KiCad's netlist exporter issues its annotation notice for both versions.

These checks establish electrical equivalence of the documents, not physical
validation of the hardware or a new assessment of the original component choices.
