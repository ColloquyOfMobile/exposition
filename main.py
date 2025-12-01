import sys
from pathlib import Path
cwd = Path(__file__).parent
# server_code = cwd / "Server"
# sys.path.append(str(server_code.resolve()))
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

from colloquy import Colloquy

if __name__ == "__main__":
    args = sys.argv[1:]
    colloquy = Colloquy()
    colloquy.cli(*args)