# Male static v2: wired reading copy

Open `male-static-v2-wired.kicad_pro` in KiCad 9, or read
`male-static-v2-wired.pdf`. This is a separate reading copy of revision D.
The original v2 schematic, PCB and the female board are preserved.

Every electrical net is drawn with continuous wires. Signal names are plain
explanatory text, not electrical labels. Dots join wires; crossings without dots
do not. X marks an intentionally unused pin. Connector pins are grouped by
function, **not physical position**: always use the printed pin numbers.

The male board has more connections than the female board, so this drawing uses
one A2 landscape sheet. Zoom in or print at A2 for legible pin names.

## Changes introduced by this reading copy

C1 footprint update (2026-10-20): 220 uF / 10 V **SMD polarized aluminium
electrolytic**, `Capacitor_SMD:CP_Elec_6.3x5.8`; pad 1 = +5 V, pad 2 = GND.
The original v2 schematic and PCB now use the same package. The electrical
value is unchanged; placement and local supply tracks were adjusted. The
220 uF sizing remains provisional pending bench measurements.

No components, values, pin assignments or electrical connections change.
Independent KiCad exports match all 18 component references/values, all 57
connected pins, and all 17 electrical nets against the original v2 schematic.
The circuit manifest and PCB also agree. ERC reports zero violations.
See `validation.json` and `erc.json`. These are CAD equivalence checks, not
physical fit or electrical performance validation.

## Added elements compared with the original male static board

The original `../../male static/male static.kicad_sch` contains J1-J11.
The following seven elements were already added in v2; this reading copy
introduces none of them.

| Element | Why it was added | Is it necessary? |
|---|---|---|
| M1: GF1002 amplifier interface / 1 x 11 socket | Places the amplifier near the speaker and makes the module removable. Only its right channel is used. | A local amplifier is required for this v2 line-level arrangement. The removable socket is a mounting choice; replacing it would require a redesign. |
| R1: 22 kOhm | Series resistor in the amplifier input divider, following Thomas's design. | Needed for the specified divider. Its suitability depends on retaining the intended source/filter/module signal levels. |
| R2: 3.3 kOhm | Return leg of that divider, to AUDIO_RETURN. With R1 it reduces the voltage to about 13% before module loading. | Needed for that attenuation; R1 alone cannot provide it. Thomas specifies this same 22K/3K3 pair for all five channels. |
| C1: 220 uF / 10 V, polarized | Local supply reservoir for amplifier current transients and harness voltage drop. Pin 1 is positive. | Sensible prototype provision, but the need for extra bulk capacitance and the exact 220 uF value remain provisional until rail sag and noise are measured. |
| C2: 100 nF | Local high-frequency bypass from 5 V to GND near the amplifier supply contacts. | Retain in this prototype. Whether the module's onboard bypass could make it redundant is unverified. |
| H1: insulating support at shaft edge | Supports the raised module and reduces socket leverage when its knob is operated. | Mechanical support is needed for this arrangement. The exact support shape may be replaced by an equivalent design; actual height and fit require measurement. |
| H2: insulating support at short end | Keeps the other end level and limits rocking. | Retain for the proposed mounting. An alternative structure could provide equivalent support. |

Thomas's source is `Source code/Thomas/Colloquy - Pask Redesign.pdf`, printed
page 5 (PDF page 6), "Input divider". It explicitly specifies R1/R2 = 22K/3K3
for all five dividers and explains their purpose as avoiding amplifier clipping.
The added reservoir/bypass capacitors are prototype provisions, not established
here as equivalent additions explicitly specified by Thomas.

H1/H2 have no electrical connections. The nominal 11 mm underside gap and
approximately 28 mm pot height need confirmation with the actual socket,
headers and male body.

## Changed audio connections and preserved male connections

- J7.14: originally remote speaker +; now LINE_IN to R1.
- J7.7: originally remote speaker -; now AUDIO_RETURN to R2 and M1.2.
- J6.1/J6.2: now connected only to M1.10/M1.11, not directly to the rack pair.
- J7.9 remains 5 V. J7.2 remains 12 V for the servo; M1 receives 5 V only.
- J7.1 and shell pad 0 remain supply GND. AUDIO_RETURN is a separate PCB net;
  confirm its expected bond to supply ground inside the actual module.
- J9/J8/J1/J4 remain photosensor A/B/C/D respectively. J3 is the microphone;
  J5/J11 are body/bar NeoPixels; J10 is the state LED. J2 is the servo connector.
  Their electrical pin assignments are unchanged from v2 and the original board.
- The legacy schematic calls J2 "dxl mirror"; v2 calls it "dxl male". This is
  a naming change, not a new component or a pinout change.

Disconnect the old rack amplifier output from J7.14/J7.7 before using v2.
Those pins must carry line-level audio and return. M1.10 = ROUT+ and M1.11 =
ROUT- are provisional polarity assignments: verify the actual module markings.
Neither speaker output connects to GND.

## Rebuild and check

From the repository root:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/male static v2/scripts/build_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/male static v2/scripts/verify_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe' sch export pdf -o 'CAD/KiCad/male static v2/wired/male-static-v2-wired.pdf' 'CAD/KiCad/male static v2/wired/male-static-v2-wired.kicad_sch'
```

The scripts reuse the female body's drawing primitives and checker, read the
male `circuit.json`, and write into this male `wired/` folder only. No PCB is
regenerated and no female schematic is rewritten.
