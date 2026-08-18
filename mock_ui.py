"""Serve the web UI against a mock application, for working on the page.

    py mock_ui.py

then http://localhost:8088/app - port 8088, not the installation's 8087,
so this can be run while the installation itself is up.

Same server and same renderer as `main.py`, pointed at
`colloquy/ui/mock.py` instead of the installation: a handful of nodes
covering every kind of leaf and link the page can draw, with no servos,
no Arduino, no threads and no params file behind them.

Path handling copied from main.py rather than shared with it: this has to
work before anything under `colloquy/` is importable.
"""
import sys
from pathlib import Path

cwd = Path(__file__).parent
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

from colloquy.ui.mock import serve

if __name__ == "__main__":
    serve()
