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
    colloquy.hardware.u2d2.com_port.set("u2d2 com")
    colloquy.hardware.u2d2.html.open(request=None)
    colloquy.hardware.u2d2.html.open(request=None)
    colloquy.hardware.u2d2.dxl_list[0].html.open(request=None)
    # colloquy.exposition.start_command()    
    colloquy.cli(*args)