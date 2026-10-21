# Electronics: designs, references and production

Use these four folders to distinguish the files' purpose:

| Folder | Contents |
| --- | --- |
| [proposed-solutions](proposed-solutions/) | Editable replacement designs, including selected boards and alternative designs. |
| [old-reference](old-reference/) | Original installation boards, superseded designs and historical exports. |
| [provided-elements](provided-elements/) | Reference models and footprints of purchased/provided modules and component datasheets. |
| [production](production/) | Current checked fabrication, JLCPCB assembly files, schematic SVGs and 45° PCB previews. |

The authoritative manufacture selection is `export_gerbers.py` at the repository root;
`production/manifest.json` records its exact source files and hashes. The server reads
this selection and refuses stale packages. Alternative designs are not manufacturing orders.

| Manufacture | Quantity |
| --- | ---: |
| Shields backplane | 1 |
| Teensy 4.1 adapter | 1 |
| Voice Thomas card | 5 |
| Analyser carrier | 1 |
| **Microphone flex holder, Rev C (32 × 62 mm)** | **6** |
| Female base v2 | 3 |
| Male static v2 | 2 |

The Rev B microphone holder is historical. Manufacture the Rev C **microphone-flex**
board with removable JP1/JP2 selectors and three alternative module orientations.
Fit one MAX9814 module per holder; see its README for initial selector settings and fit checks.

Order packages are under `production/assembly/<board>/`; the combined download is
`production/assembly/colloquy-production.zip`. Each board package contains `gerbers.zip`,
`BOM.csv` with exact manufacturer/LCSC identification, `CPL.csv`, and manual/DNP instructions.
The analyser carrier has no SMD population and is assembled by hand.

Regenerate from the repository root using KiCad's Python: `python export_jlcpcb.py`.
This checks DRC, produces the assembly packages, and refreshes browser assets.
