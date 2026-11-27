# Original enclosure mounting holes

Recovered from the user-supplied original board:
`CAD/KiCad/old-reference/original-supplied-boards/electronic box/electronic box.kicad_pcb`.
The second archived design, `archive1/electronic box 2/electronic box 2.kicad_pcb`,
contains the same four circles. These files predate the electronic-box
revisions previously present in this repository.

All four holes are **8.00 mm diameter**, represented as circular cutouts on
`Edge.Cuts`, matching the original. They are part of the routed board outline,
not additional electronic components or plated holes. Fabricators must retain
all four internal circles from the Edge.Cuts Gerber. The Excellon NPTH file
continues to describe the separate smaller drilled mounting holes.

| Hole | Centre relative to the board's top-left (mm) | Current KiCad absolute centre (mm) |
|---|---|---|
| Top | 105.00, 20.00 | 149.00, 72.16 |
| Left | 20.00, 150.00 | 64.00, 202.16 |
| Centre | 105.00, 150.00 | 149.00, 202.16 |
| Right | 190.00, 150.00 | 234.00, 202.16 |

Both boards have a 210 x 297 mm outside envelope. The archive uses (0, 0)
for its top-left; the current backplane uses (44, 52.16) mm. Therefore the
transfer is a translation of (+44, +52.16) mm, with no rotation, mirroring or
scaling. The current rounded outside corners remain unchanged. The original
pattern includes a centre hole; it is not a four-corner pattern.

The centre cutout overlaps the former TPL3 probe pad. TPL3 was moved from
(146.04, 202.00) to (141.00, 206.00) mm, and its L3 caption moved with it.
The nearby tone/line legend moved above the cutout. Copper crossing the
left and centre cutouts was rerouted, and pours refilled. Connector locations,
pin assignments, component values and the electrical netlist are preserved.

`enclosure-mounting.json` records the source hash, source coordinates,
coordinate translation and resulting PCB hashes. The holes and TPL3 change
are present in both the routed and placed backplane boards.

To restore the geometry after regenerating a staging layout, run with KiCad Python:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/proposed-solutions/shields/scripts/restore_enclosure_holes.py'
```

This updates geometry and fills pours; routing and native DRC must follow any
layout change. Regenerate fabrication packages after changing the routed PCB.

Validation: native KiCad DRC has zero violations and zero disconnected items.
Independent netlist/PCB comparison retains all 137 components and all 94 nets.
All numbered pads retain their original dimensions and assignments; TPL3 is
the only relocated pad. The +12V routes retain their 2 mm width on outer copper.

## U2D2 mounting at M1

On 2026-11-27 the installer found that the U2D2 assembly did not fit M1
on the Solution 2 Rev A backplane. The installation photo shows the
clear-cased USB module already attached to the blue ROBOTIS Power Hub Board.
The hub's four outer standoffs are the fixings that meet the backplane.

| Hole centres | Across the hub's 48 mm width | Along its 57 mm length |
| --- | ---: | ---: |
| Rev A backplane M1, four Ø4.5 mm holes | 42.00 mm | 42.00 mm |
| ROBOTIS Power Hub Board, four outer holes | 42.07 mm | 48.04 mm |

With one end aligned, the opposite pair is 6.04 mm off along the hub's length.
The four 8 mm enclosure mounts described above serve a separate purpose.
For a future M1 revision or adapter, check the standoff centres against the
physical hub and check plug clearance in the enclosure before fabrication.
[Rev A production drill file](../../../production/backplane/backplane-NPTH.drl) ·
[ROBOTIS U2D2 PHB dimensioned drawing, 2020-03-13](https://en.robotis.com/service/download.php?no=1914).
