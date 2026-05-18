import sys
from pathlib import Path
cwd = Path(__file__).parent
# server_code = cwd / "Server"
# sys.path.append(str(server_code.resolve()))
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

from colloquy import Colloquy
from colloquy2 import colloquy2 as _colloquy2
from colloquy.server2 import Server2
from server import server

def main(*args):
    memory = {
        "colloquy1": colloquy1,
        "colloquy2": colloquy2,
    }
    
    if args:    
        key, *leftovers = args
        if key in memory:
            return memory[key](*leftovers)
    
    print(as_text(memory))
        

def colloquy2(*args):    
    server(colloquy=_colloquy2)
        

def colloquy1(*args):    
    colloquy = Colloquy()
    colloquy.hardware.u2d2.com_port.set("COM4")
    colloquy.hardware.u2d2.open()
    colloquy.hardware.arduino.open()
    for dxl in colloquy.hardware.u2d2.dxl_list:
        dxl.init_hardware()
    colloquy.hardware.arduino.html.open(request=None)
    # colloquy.hardware.arduino.commands[0]._send()
    
    Server2(colloquy=colloquy)

def as_text(memory):    
    lines = as_lines(memory)
    return "\n".join( "".join(tokens) for tokens in lines) 

def as_lines(memory):
    if not isinstance(memory, dict):
        raise NotImplementedError(memory) 
        
    lines = []    
    for key, value in memory.items():
        tokens = []
        
        if not isinstance(value, dict):
            lines.append([f"{key}()"])
            continue
            
        if "opened" in value:
            lines.append([f'{value["name"]}:'])
            lines += as_lines(value)
            continue
            
        if "value" in value:
            lines.append([f'{value["name"]}: {value["value"]}'])
            continue
            
        lines.append([f'{value["name"]}'])
    
    return add_indent(lines)
    
def add_indent(lines):
    return  [["|", *tokens] for tokens in lines]
    

if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)