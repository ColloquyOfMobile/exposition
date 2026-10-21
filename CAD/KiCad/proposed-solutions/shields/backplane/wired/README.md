# Backplane connection blocks

Open `backplane-wired.kicad_sch` in KiCad or `backplane-wired.pdf` for a
single, continuous vector drawing. The master PDF contains the same sheet.
This replaces the earlier contact-by-contact drawing.

The broad arrangement follows the PCB's top view: U2D2 at upper left,
Arduino/Teensy controller above centre, power entry at upper right, five
voice-card sockets across the middle, and the analyser carrier below them.
The four D-subs occupy the left, right and lower edges. Signal-conditioning
parts stay near their associated functions. This is a logical schematic,
not a physical pin-position or assembly drawing.

## Blocks and signal names

- **U2D2 / Dynamixel:** M1 is the original U2D2 mounting representation;
  it has no electrical PCB pads. J7 is the existing servo-bus connector.
  The USB host lead is identified as external, without inventing PCB nets.
- **Arduino Mega / Teensy adapter:** A1 is one complete Mega-pattern
  connection block. A Teensy uses this interface through its existing
  adapter. Actual backplane pin numbers and signal functions are retained.
- **Audio analysers:** JA1 is one complete 21-contact carrier socket,
  showing the five microphone inputs, five analyser outputs, shared
  reset/strobe, supply and returns. Module internals remain off-board.
- **Voices:** JV1-JV5 are complete socket symbols, each identified with its
  mobile and its tone, audio, power and return connections. Original loads,
  series resistors, return jumpers and activity indicators are retained.
- **D-subs:** J1, J5, A-J3 and B-J4 use KiCad's stock
  `Connector:DA15_Pins_MountingHoles`, including the original grounded
  shield contact 0. Their standard artwork and pin numbering are unmodified.

All electrical connections are actual wires. Blue captions and block titles
are plain text and create no hidden connections. Dots join wires;
crossings without dots remain separate. AGND and GND remain separate nets
connected by the original JP1. Unused controller contacts carry NC crosses.

## Changes and necessity

| Drawing change | Why? | Necessary? |
|---|---|---|
| One controller, one analyser and five voice socket blocks | Recognize complete interfaces and follow the PCB arrangement | Requested readability change only |
| Standard complete D-sub symbols | Recognize the harness connectors and their real pin numbers | Requested; no physical connector change |
| Four D-sub pin/function keys in the clear centre | Read every signal name without crowding the wires | Plain-text reference only |
| Orthogonal continuous wires and explicit signal captions | Follow connections visually | Requested; no added circuitry |
| Forty test points omitted from this copy | Remove diagnostic clutter | Requested; test points remain on the PCB and original schematic |
| Component positions and logical controller pin grouping | Give wires space and keep functions together | Presentation only |

No physical components, values, footprints, PCB routes or manufacturing
files are changed by this schematic revision. The reading copy contains
97 of the original 137 components; only the 40 `TP*` references are omitted.
The original component-purpose notes remain in [COMPONENT_NOTES.md](COMPONENT_NOTES.md).

## Regeneration and validation

Run `build_wired_schematic.py` with KiCad Python, then
`verify_wired_schematic.py`. Run `export_wired_pdf.py` with Python containing
`pypdf`. Existing wire routes are reused only after checking all symbol and
pin positions, nets and blocked areas. `--reroute` forces routing from scratch;
`--reuse-wires` refuses any layout mismatch during artwork-only adjustments.

The verifier independently exports both native KiCad netlists, removes only
the explicitly omitted test-point nodes from the baseline, and compares all
remaining connected-pin groups, component values, footprints, unused pins,
the circuit manifest and PCB pads. It also checks for absence of electrical
net labels and runs native ERC. `validation.json` records the result and hashes.
The 97 retained components, 326 connected pins and all 94 nets match the
baseline after the requested test-point omission. ERC has zero violations.
The stock D-sub artwork and single-instance interface blocks are also checked.
Drawing equivalence does not establish physical hardware behavior.
