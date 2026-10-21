# Backplane: continuous-wire reading copy

Open `backplane-wired.kicad_sch` in KiCad. Read `backplane-wired.pdf` for
bookmarked sections, or `backplane-wired-master.pdf` for one uninterrupted
sheet. The PDF has a guide, five channel views, and four lower-section views.
The original `../backplane.kicad_sch`, its child sheets and PCB are unchanged.

**There are no added, removed or changed electronic or mechanical parts.**
The comparison baseline is the current original backplane schematic in this
directory, not an older installation board or another revision.

All 94 nets are real, continuous wires. There are no local, global or
hierarchical net labels making hidden connections. Blue names are ordinary
text. Dots mean joined wires; crossings without dots are separate.

## Drawing changes: why, and necessary?

| Change | Why? | Necessary? |
|---|---|---|
| Wires replace electrical labels | Follow connections directly | Yes, for this requested version |
| Five repeated channel sections | Read one mobile's signal paths together | Readability only |
| Connector contacts shown as separate symbol units | Keep pin numbers close to their wires and avoid a large tangle | Readability only; repeated references are the same physical connector |
| Logical contact positions, short reference captions and simplified pin-name display | Make the circuit easier to follow while retaining real pin numbers | Readability only; not a connector mating-face or assembly drawing |
| Plain-text signal captions, junction dots, unused-pin crosses | Identify functions, joined wires and intentional unused contacts | Documentation/checking only; no added parts |
| A single tall master sheet and cropped PDF reading pages | Preserve uninterrupted electrical wiring while allowing useful viewing sizes | Presentation only; shared rails continue across PDF crops |

Shared vertical rails, from left to right, are GND, AGND, +5V, MEGA_5V,
+12V, dxl_data, analyser/strobe, analyser/reset and amp shutdown. Some
control nets need only a local row; empty rail positions are not connections.
Supply contacts are grouped under their actual supply wire in the lower section.

## Existing components that can look like additions

Every reference below is already in the original. The purposes are inferred
from their existing connections and values. “Optional” describes their role,
not a validated recommendation to depopulate the existing PCB. This task
does not redesign or prove which parts can safely be removed.

| Original elements | Why are they there? | Necessary? |
|---|---|---|
| A1 | Mega-pattern controller connection, including direct microphone contacts D26-D30 | Required for the existing controller interface |
| J2, J6 | Existing +5V input and screw-bridge distribution | A supply path is required; these particular connector choices belong to the original design |
| J7 | Ground, +12V and Dynamixel data interface | Required for that existing interface |
| J5, J1, A-J3, B-J4 | Carry the mobile harness signals and supplies | Required for the present harness pinout |
| JA1 | Analyser carrier socket | Required when using the analyser carrier |
| JV1-JV5 | Tone input, audio output, ground and power for voice cards | Required when using those voice cards |
| C1 (470uF), C2 (100nF) | Bulk and high-frequency bypass between +5V and GND | Supply conditioning retained from the original; removal needs a separate supply review |
| JP1 (0R) | The existing explicit AGND-to-GND connection | Required to preserve the present ground topology; AGND and GND remain distinct nets joined through this part |
| JP2-JP6 (0R) | Connect each harness audio return to AGND | Required for the existing audio-return path |
| R103, R203, R303, R403, R503 (100R) | Series resistance from voice filter output to harness line output | Part of the existing audio interface; no removal assessment performed |
| RL1-RL5 (100K) | Load/pulldown from filter output to AGND | Retain the existing output bias/load; actual need depends on the connected voice circuit |
| RN1-RN7 (330R) | Series resistance on mobile and bar NeoPixel data | Existing signal conditioning; retain pending any separate signal-integrity review |
| RND1-RND7 (100K) | Pull the driven NeoPixel data nodes to GND | Establish a low level when the controller does not drive; normal steady-state operation alone does not show whether they can be omitted |
| RA1, RA2 (330R) | Series resistance on the two auxiliary outputs | Existing output conditioning; requirement depends on the attached load |
| RP1-RP11 (10K provisional) | Photosensor load to AGND | Needed by the intended sensor readout; 10K is explicitly provisional and needs hardware confirmation |
| RS1 (10K) | Pull amp-shutdown control toward MEGA_5V | Defines the control node when undriven; enabled/disabled behavior depends on the receiving circuitry |
| RM1-RM5 (4K7) | Series resistance in the direct microphone branches to A1 | Part of the existing direct-input interface; this drawing makes no voltage-compatibility or protection guarantee |
| RMD1-RMD5 (1M) | Weak direct-microphone-input pull to AGND | Defines that node when its source is absent; requirement depends on the attached input and microphone |
| RLT1-RLT5 (1K5), DT1-DT5 (yellow LEDs) | Tone activity indication | Indicator function is optional; current-limiting resistors are required if their LEDs are fitted |
| RLP5 (2K2), DP5; RLP12 (4K7), DP12; RLPUSB (2K2), DPUSB (green LEDs) | +5V, +12V and MEGA_5V presence indications | Indicator function is optional; each fitted LED needs its series resistor |
| TP1-TP5, TPL1-TPL5 | Access to filter outputs (including existing duplicate probe access) | Optional for operation; useful for testing |
| TPM1-TPM5, TPD1-TPD5, TPA1-TPA5, TPV1-TPV5 | Access to raw/direct microphone, analyser and tone signals | Optional for operation; useful for testing |
| TP20, TP21, TP30 | Access to analyser strobe/reset and shutdown | Optional for operation; useful for testing |
| TP31-TP34, TPUSB, TPVG, TPEG | Supply and ground probe access | Optional for operation; useful for testing |
| Extra1, Extra2, Extra3 | Break out existing spare harness contacts | Optional unless those spare connections are used; spares stay electrically separate |
| M1 | U2D2 mounting representation, with no electrical pins in this schematic | Needed for the existing mechanical arrangement, not a newly added circuit |
| HV1-HV5, HA1, HA2 | Voice/analyser card mounting and retention | Mechanical function; not part of signal connectivity |
| #FLG1 | Original GND supply declaration for KiCad ERC | Checking symbol only; no physical part or new ground connection |

The voice and analyser circuits remain represented by their original socket
interfaces. Their internal components are not newly inserted into the backplane.

## Validation and regeneration

Run from the repository root:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/proposed-solutions/shields/backplane/build_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/proposed-solutions/shields/backplane/verify_wired_schematic.py'
# Use a Python with pypdf and reportlab for the PDF export:
& '<document-python>' 'CAD/KiCad/proposed-solutions/shields/backplane/export_wired_pdf.py'
```

The verifier independently exports both KiCad netlists, compares component
references/values/footprints and all connected-pin groups, compares against
`circuit.json` and PCB pads, checks unused pins and absence of electrical
labels, and runs native KiCad ERC. Result: **137 components, 366 connected
pins, 94 nets, zero ERC violations**. See `validation.json` and `erc.json`.
KiCad also prints the original annotation warning for the pre-existing
reference naming; the exported graph and ERC checks still pass.

The PDF exporter normalizes KiCad 9's exponent-form numeric tokens for large
page backgrounds into valid PDF decimal numbers, then crops reading pages
without changing the drawing. All ten pages were rendered and visually checked.
Drawing equivalence does not establish physical connector fit or hardware behavior.
