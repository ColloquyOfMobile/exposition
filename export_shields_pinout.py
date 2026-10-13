"""Generate the paired shield pinouts without importing the application.

    py export_shields_pinout.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Source code/Python/colloquy/hardware/electronics'))
import shields_pinout


if __name__ == '__main__':
    for path in shields_pinout.write():
        print('wrote', path.relative_to(ROOT))
    assert 'colloquy' not in sys.modules
