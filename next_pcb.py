# -*- coding: utf-8 -*-
# next_pcb.py

"""Regenerate the next PCB's netlist and bill of materials.

    py next_pcb.py

Writes into `CAD/KiCad/electronic box v2/`. The design itself is
`Source code/Python/colloquy/hardware/electronics/next_pcb.py`; this only
puts it on disk, in the folder the KiCad project will live in, so that the
wiring sits beside the drawing rather than inside a Python package nobody
opens with a schematic editor in front of them.

Run it after changing the design, and after changing
`colloquy/drivers/audio.py` - the board reads that table, which is the
point of generating any of this.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.append(str((ROOT / "Source code" / "Python").resolve()))

from colloquy.hardware.electronics.next_pcb import Design
from colloquy.hardware.electronics.next_pcb_report import (
    bom_markdown,
    mechanical_markdown,
    netlist_markdown,
)

FOLDER = ROOT / "CAD" / "KiCad" / "electronic box v2"


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    design = Design()

    for name, text in (
        ("NETLIST.md", netlist_markdown(design)),
        ("BOM.md", bom_markdown(design)),
        ("MECHANICAL.md", mechanical_markdown()),
    ):
        path = FOLDER / name
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT).as_posix()}")

    parts = len(design.parts)
    nets = len(design.nets)
    confirm = sum(1 for part in design.parts if part.confirm)
    print(f"{parts} parts, {nets} nets, {confirm} values still to confirm.")


if __name__ == "__main__":
    main()
