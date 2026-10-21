# Audio analyser carrier: continuous-wire schematic

Open `analyser-carrier-wired.kicad_sch` in KiCad, or read
`analyser-carrier-wired.pdf`. The original hierarchical schematic and PCB
are preserved. This is a second, electrically equivalent reading copy.

All 14 connected nets are drawn as continuous wires: no global, local or
hierarchical net labels provide hidden connections. Blue signal captions
are plain text. Dots mean joined wires; crossings without dots are separate.
The five channels run left to right; power, analog ground, reset and strobe
use four shared vertical wires. Socket pin numbers are preserved but
reordered on the drawing for readability; this is not a physical pin-layout
or assembly drawing. The page is 420 x 330 mm to leave the title block clear.

## What changed, why, and is it necessary?

**No electrical or mechanical components were added, removed or changed.**
The connected pins, unused pins, values and footprints match the original.

| Drawing change | Why | Necessary? |
|---|---|---|
| One sheet instead of multiple hierarchical sheets | See all five channels together | Only for readability |
| Continuous wires replace net labels | Follow each connection directly | Required by the requested second version |
| Logical symbol pin order, retaining actual numbers | Avoid long, tangled wire routes | Only for readability; no physical change |
| Plain text channel, signal and module-conversion notes | Identify functions and explain the existing module modification | Documentation only; no new connection |
| Explicit junction dots and unused-pin crosses | Distinguish joined crossings and deliberately unused JA1 pins 20/21 | Drawing clarity and electrical checks; no new part |

## Existing items that might look like additions

These are all present in the original carrier design:

| Existing item | Purpose | Necessary? |
|---|---|---|
| TPA0-TPA4 | Probe each analyser output | Optional for operation; useful for diagnosis |
| TP5 and TPG | Probe +5 V and analog ground | Optional for operation; useful for diagnosis |
| H1 and H2 | M3 carrier retention | Mechanical retention; not part of the electrical circuit |
| Both +5 V and both GND contacts on each module | Preserve the two existing input-header supply/ground groups | Retained as designed; no attempt to remove duplicate contacts |
| Module R3 removal and isolated R-to-OUT jumper | Use the former R input terminal as the analyser output, with microphone on L | Required for the existing carrier pin mapping; already required by the original, not introduced here |

The module conversion is documented in the parent README. Module internals
are represented by the same composite M1-M5 symbols as the original; this
copy does not add a second depiction of their internal circuit.

## Validation and regeneration

Run from the repository root with KiCad's Python:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/proposed-solutions/shields/analyser-carrier/build_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/proposed-solutions/shields/analyser-carrier/verify_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe' sch export pdf --output 'CAD/KiCad/proposed-solutions/shields/analyser-carrier/wired/analyser-carrier-wired.pdf' 'CAD/KiCad/proposed-solutions/shields/analyser-carrier/wired/analyser-carrier-wired.kicad_sch'
```

The verifier compares independently exported KiCad netlists with each
other and with `circuit.json`, compares the PCB's pad connectivity, verifies
unchanged components and unused pins, and runs native ERC. `validation.json`
records checks and input hashes; `erc.json` records the electrical rules check.
This confirms drawing equivalence, not physical socket fit or hardware behavior.
