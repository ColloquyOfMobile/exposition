# Board generator (TJ Brain, TJ Backplane)

The two boards are described in Python and generated into KiCad projects. All the
connectivity lives in one place (`brain.py`, `backplane.py`), and every run checks the
generated schematic against that description.

| File | Role |
|------|------|
| `design.py` | small DSL: parts, nets, footprint aliases |
| `brain.py`, `backplane.py` | the circuits (every part, value and net) |
| `make_lib.py` | writes `../tj_library` (Teensy 4.1 and SparkFun TPA2005D1 breakout symbols and footprints) |
| `schgen.py` | writes hierarchical KiCad schematics (one sheet per block, labelled pin stubs) |
| `netcheck.py` | exports the netlist with `kicad-cli` and compares it net-by-net with the design |
| `pcbgen.py` | builds the board: outline, footprints, nets, locked power trunks, GND fan-out vias, zones, silkscreen |
| `router.py` | two-layer grid autorouter (A* with clearance from distance transforms, 45° tracks, vias, rip-up and reroute) |
| `route_board.py` | routing driver, repair pass, zone fill |
| `export.py` | project file, library tables, DRC, Gerbers, drill, BOM, positions, PDF, renders |
| `build_brain_sch.py`, `build_brain_pcb.py`, `route_brain.py`, `repair_brain.py`, `finish_brain.py` | TJ Brain pipeline |
| `build_backplane.py` | complete TJ Backplane pipeline |

You need KiCad 7 or newer (`pcbnew` Python module and `kicad-cli`) and Python with numpy
and scipy. Intermediate files go to `_build/`, which git ignores.

```
python3 make_lib.py
python3 build_brain_sch.py && python3 build_brain_pcb.py && python3 route_brain.py && python3 finish_brain.py
python3 build_backplane.py
```

Every schematic run writes new symbol UUIDs. After regenerating the schematic, also
regenerate the PCB so the footprints stay linked to their symbols. In KiCad, "Update PCB
from schematic" then also works.

The autorouter is deliberately simple: a cell grid of 0.125 mm, a 0.2 mm clearance plus a
grid margin, and one via size (0.8 / 0.4 mm). It cannot pass a track between 2.54 mm
pitch THT pins. Power trunks are drawn by hand in `build_*_pcb.py` and locked. GND is not
routed: every SMD GND pad gets a via to the bottom plane, and both layers are poured. The
KiCad DRC is the final check, so read the report printed by `finish_brain.py`.
