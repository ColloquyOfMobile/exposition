import sys
from pathlib import Path
cwd = Path(__file__).parent
# server_code = cwd / "Server"
# sys.path.append(str(server_code.resolve()))
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

from colloquy import Colloquy
from colloquy.server2 import Server2

if __name__ == "__main__":
    args = sys.argv[1:]
    
    colloquy = Colloquy()
    colloquy.hardware.u2d2.com_port.set("COM4")
    colloquy.hardware.u2d2.open()
    colloquy.hardware.arduino.open()
    for dxl in colloquy.hardware.u2d2.dxl_list:
        dxl.init_hardware()
    colloquy.hardware.arduino.html.open(request=None)
    colloquy.hardware.arduino.commands[0]._send()
    
    Server2(colloquy=colloquy)
    # colloquy.hardware.u2d2.dxl_list[0].html.open(request=None)
    
    # colloquy.hardware.u2d2.dxl_list[0].goal_position.write(400)
    
    # colloquy.hardware.female1.html.open(request=None)
    # colloquy.hardware.male1.neopixels.ring.on()
    # colloquy.hardware.male1.search.blink.start(started_by=None)
    # colloquy.hardware.female1.search.read_pattern.start(started_by=None)
    # colloquy.hardware.female1.html.open(request=None)
    # colloquy.hardware.bar.dxl.init_hardware()
    # colloquy.hardware.bar.goal_position.write(1000)
    # colloquy.hardware.male1.neopixels.html.open(request=None)
    # colloquy.hardware.female1.light_sensor.html.open(request=None)
    # colloquy.hardware.female1.light_sensor.read_pattern.html.open(request=None)
    # colloquy.hardware.female1.torque_enabled.write(value=1)
    
    # colloquy.hardware.u2d2.html.open(request=None)
    # colloquy.hardware.u2d2.dxl_list[0].html.open(request=None)
    
    # colloquy.exposition.html.open(request=None)
    # colloquy.exposition.start_command()    
    # colloquy.cli(*args)