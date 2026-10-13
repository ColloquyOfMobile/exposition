# Manufacturer ZIPs

Generated from the current active PCB designs on 2026-10-13. Each project has
its own `manufacturing` directory containing a ZIP and short instructions.

| Project | Copper layers | Manufacturer package |
| --- | --- | --- |
| Backplane | 4 | [backplane-manufacturing.zip](backplane/manufacturing/backplane-manufacturing.zip) |
| Teensy adapter | 4 | [teensy-adapter-manufacturing.zip](teensy-adapter/manufacturing/teensy-adapter-manufacturing.zip) |
| Thomas voice card | 2 | [voice-thomas-manufacturing.zip](voice-thomas/manufacturing/voice-thomas-manufacturing.zip) |
| Analyser carrier | 2 | [analyser-carrier-manufacturing.zip](analyser-carrier/manufacturing/analyser-carrier-manufacturing.zip) |
| MAX9814 microphone holder | 2 | [microphone-manufacturing.zip](microphone/manufacturing/microphone-manufacturing.zip) |

Each ZIP includes Gerber X2 copper/mask/silkscreen/outline files, the Gerber job
file, separate metric PTH/NPTH Excellon drills (including slots), drill maps,
BOM, assembly reference CSVs, assembly SVGs, applicable project
notes and variant BOMs, a fresh DRC report, and checksums.
Gerbers and drills use the same absolute origin. Board thickness is 1.6 mm.

The board maker places front SMD only on the backplane, Teensy adapter and
microphone holder. Their packages include front paste and front SMD placement
files. Every through-hole part is fitted by hand. Order all Thomas voice
cards bare and solder their single 100K 0603 by hand with the pitch parts;
their packages omit stencil and machine-placement files. The analyser carrier
also needs no machine assembly. All-component CSVs and BOMs are assembly
references for manual fitting, not machine-placement orders.

All five freshly refilled export boards passed native KiCad DRC with zero
violations and zero unconnected items. ZIP integrity and archived file hashes
were checked. [MANUFACTURING.json](MANUFACTURING.json) identifies each archive;
its enclosed manifest records the source PCB hash and every payload file.

These packages provide the fabrication artwork for the current engineering
prototypes. Carrier physical fit remains subject to the documented dry-fit
checks. Before ordering, select quantity, copper weight, finish, mask colour
and the manufacturer's stack-up. For outsourced assembly, confirm exact
purchasing part numbers and variant population: existing BOMs include blank
or descriptive MPNs and composite module/socket references. Do not submit
those references as automatically qualified pick-and-place components.

`dfrobot-module`, `arduino-mega-reference`, `teensy41-reference`,
`max9814-reference` and `gf1002-reference` are purchased-module or mechanical
reference models, not fabrication designs. They intentionally have no
production Gerber ZIP. The obsolete analyser and the Blender staging copies
are likewise excluded. No source PCB was modified by this export.

Regenerate from the shields directory:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' scripts/manufacturing.py
```
