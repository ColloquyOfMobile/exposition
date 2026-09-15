# -*- coding: utf-8 -*-
# export_mega_pinout.py

"""Draw the Mega with the signal on every pin around it.

    py export_mega_pinout.py

Writes `mega-pinout.svg` under `Source code/Python/colloquy/server2/
static/hardware/`, which `AS_BUILT.md` shows. The drawing itself is
`colloquy/hardware/electronics/mega_pinout.py`; re-run this after any
change to `electronic box.kicad_pcb`.

The module is imported from its own folder rather than through the
`colloquy` package, because importing the package wipes `local/logs` -
which, on a machine where the server is running, are its logs.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(
    0, str(ROOT / "Source code" / "Python" / "colloquy" / "hardware" / "electronics")
)

import mega_pinout  # noqa: E402


def main():
    path = mega_pinout.write()
    print(f"wrote {path.relative_to(ROOT.resolve())}")


if __name__ == "__main__":
    main()
