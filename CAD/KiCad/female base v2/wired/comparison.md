# Female base v2: wired reading copy

Open `female-base-v2-wired.kicad_pro` in KiCad 9, or read
`female-base-v2-wired.pdf`. This is a second schematic for review, not a PCB
revision. The original schematic and PCB are preserved.

Every electrical connection is drawn as a continuous wire. Signal names remain
as explanatory text only: they do not connect distant points. Connector pins
are arranged by function, **not physical position**; use the printed pin numbers
when identifying a real connector. A dot joins wires; a crossing without a dot
does not. X marks an intentionally unused pin.

## What changed in this second schematic?

C1 footprint update (2026-10-20): 220 uF / 10 V **SMD polarized aluminium
electrolytic**, `Capacitor_SMD:CP_Elec_6.3x5.8`; pad 1 = +5 V, pad 2 = GND.
The original v2 schematic and PCB have been updated to match. Capacitance and
voltage rating are unchanged; only the package, local placement/routing and
polarity marking were updated. The 220 uF value remains provisional.

No added parts, removed parts, changed values, or changed electrical connections
relative to `../female-base-v2.kicad_sch` (revision D).
The connector symbols are rearranged for reading. M1 is still the existing
11-position socket and amplifier interface, not a new amplifier circuit.
H1/H2 are mechanical supports with no electrical connections.

Independent KiCad netlist exports agree for all 13 components, including values,
all 38 connected pins, and all 12 electrical nets. The PCB and circuit manifest
also agree. KiCad ERC: zero violations. See `validation.json` and `erc.json`.
These checks establish drawing equivalence; they do not qualify the hardware.

## Added elements compared with the original female base

The comparison here is with `../../female base/female base.kicad_sch`, which
contains only J2-J7. All seven elements below were **already present in v2**;
none was introduced by the wired copy.

| Element | Why v2 adds it | Is it necessary? |
|---|---|---|
| M1: GF1002 amplifier interface, 1 x 11 socket | Moves speaker amplification into the female body. The socket makes the module removable. Only the right channel is used. | A local amplifier is required for this v2 arrangement because the rack now sends line-level audio. A removable socket is a design choice; permanent mounting could be redesigned, but is not this revision. |
| R1: 22 kOhm | Series leg of Thomas's audio input divider. Works with R2 to reduce the rack audio voltage before M1 input R. | Required to preserve the specified divider. Its exact value is not established as universally necessary; changing it requires checking the actual source level, module input impedance and clipping. |
| R2: 3.3 kOhm | Divider return leg to AUDIO_RETURN. Together with R1 gives about 0.130 times the input voltage, ignoring module loading. | Required for that attenuation. R1 alone does not implement the specified divider. Exact sizing still depends on measured signal levels. |
| C1: 220 uF, 10 V, polarized | Local energy reservoir across the 5 V supply for amplifier current transients and harness voltage drop. Pin 1 is positive. | Local bulk capacitance is prudent; the necessity of this additional capacitor and the exact 220 uF value remain provisional until supply sag/noise are measured with the real module and harness. |
| C2: 100 nF | Local high-frequency supply bypass between 5 V and GND near M1. | Retain it in this prototype. Whether the module's own bypass could make it redundant has not been demonstrated. |
| H1: insulating support at shaft edge | Supports the raised module and resists force from turning or pressing the knob, reducing leverage on the socket. | Mechanical support is needed for this mounting arrangement. This exact support shape is replaceable by an equivalent support; actual fit and stack height need measurement. |
| H2: insulating support at short end | Holds the other end level and limits rocking of the plug-in module. | Retain for the proposed mounting. An alternative mechanical design could provide the same support. |

The approximately 11 mm module underside height and 28 mm pot height are nominal,
not measured acceptance dimensions. Supports must match the purchased socket/header stack.

## Connections whose function changed from the original

- J7.12 originally carried remote speaker +; v2 uses it for LINE_IN.
- J7.4 originally carried remote speaker -; v2 uses it for AUDIO_RETURN.
- J6.1/J6.2 originally connected straight to that rack pair. In v2 they connect
  only to M1.10/M1.11, the local right-channel amplifier output.
- AUDIO_RETURN and supply GND are separate PCB nets. The expected internal bond
  between module input G and supply minus must be confirmed on the actual module.
  Do not add a jumper on this reading copy to assume that bond.
- J7.15 remains 5 V; J7.7 remains 12 V for the mirror servo. M1 receives 5 V only.
  Other original connector pin assignments are unchanged.

Disconnect the old rack amplifier speaker output from J7.12/J7.4 before using
the v2 board. Those pins must receive line-level audio and its return instead.
M1.10 = ROUT+ and M1.11 = ROUT- remain provisional assignments: check the real
module markings. Neither speaker output connects to GND.

## Reproduce the drawing and checks

From the repository root, run:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/build_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/female base v2/scripts/verify_wired_schematic.py'
& 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe' sch export pdf -o 'CAD/KiCad/female base v2/wired/female-base-v2-wired.pdf' 'CAD/KiCad/female base v2/wired/female-base-v2-wired.kicad_sch'
```

The builder reads `../circuit.json` and writes only into this `wired/` folder.
It does not rebuild either body PCB or modify the male board.
