# Assembly notes — revision A prototype

The CSV BOM lists electrical components. Also provide these assembly items:

| Quantity | Item | Location |
| --- | --- | --- |
| 5 | DIP-8 sockets, 7.62 mm row spacing | U1–U5; insert MSGEQ7P devices with pin 1 at the marked end |
| 1 set | Arduino Mega 2560 R3 mating headers | A1; outer headers are five 1×8, one 1×10, and one 2×18 at 2.54 mm pitch; the central ICSP connection is 2×3 |
| 4 | M3 standoffs, fasteners, and insulating washers as needed | H1–H4; select height after enclosure dry-fit |
| 1 set | Existing U2D2 mounting hardware | M1; preserve the original four-hole mounting pattern |

**The Mega module belongs underneath the PCB.** Its inherited footprint uses
the top-side coordinate convention for the shield mating headers. Consequently,
the native position CSV's `A1, ..., top` row describes that footprint, not an
instruction to put the Mega above the board. Fit the ICSP mating socket and
outer headers in the orientation and heights required by the actual Mega.
Position CSVs are inspection references, not automatic assembly programs.

Leave JS1–JS5 open. Test pads are bare copper and require no bought components.
Ground terminals of RP1–RP11, C301, and A-J3's shell use solid copper joins;
allow enough soldering heat for these connections. Other ground pads generally
retain thermal reliefs.

RP1–RP11 are provisional 10 kΩ sensor loads. Verify them against the installation
before deployment. Confirm jack polarity, inspect the 5 V rail separation, and
use current-limited supplies during first power-up. Follow the staged checks in
the project README before connecting the complete installation.
