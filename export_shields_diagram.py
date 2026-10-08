# -*- coding: utf-8 -*-
# export_shields_diagram.py

"""Draw the shields backplane with its slots and its two configurations.

    py export_shields_diagram.py

Writes `shields-configurations.svg` under `Source code/Python/colloquy/
server2/static/hardware/`, which `SHIELDS.md` and `main pcb >
configuration` show. The drawing itself is
`colloquy/hardware/electronics/shields_diagram.py`; re-run this after any
change to a board under `CAD/KiCad/shields/` or to the slots in
`main_pcb/configuration/table.py`.

**Nothing here imports the `colloquy` package**, because importing it
wipes `local/logs` - which, on a machine where the server is running, are
its logs. Each module the drawing needs is loaded by path and registered
under its own full name, so its `from colloquy.x.y import z` finds it
already loaded and never runs a package `__init__` above it.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parent
COLLOQUY = ROOT / "Source code" / "Python" / "colloquy"

# In dependency order: each is loaded before anything that imports it.
MODULES = (
    ("colloquy.drivers.audio", "drivers/audio.py"),
    ("colloquy.hardware.electronics.harness", "hardware/electronics/harness.py"),
    ("colloquy.hardware.main_pcb.configuration.table", "hardware/main_pcb/configuration/table.py"),
    ("colloquy.hardware.electronics.shields_diagram", "hardware/electronics/shields_diagram.py"),
)


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, COLLOQUY / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    for name, relative in MODULES:
        module = _load(name, relative)
    assert "colloquy" not in sys.modules, "the package ran - local/logs would be gone"
    path = module.write()
    print(f"wrote {path.relative_to(ROOT.resolve())}")


if __name__ == "__main__":
    main()
