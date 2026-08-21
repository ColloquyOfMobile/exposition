import sys
from time import sleep
from pathlib import Path
import matplotlib

# Plots are built in background threads (test_light_sensor_values,
# test_movements); matplotlib's default GUI backend isn't thread-safe and
# throws "main thread is not in main loop" errors from a non-main thread.
matplotlib.use("Agg")

cwd = Path(__file__).parent
# server_code = cwd / "Server"
# sys.path.append(str(server_code.resolve()))
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

from colloquy import Colloquy
from colloquy.server2 import Server2


def main(*args):
    memory = {
        "colloquy1": colloquy1,
    }

    if args:
        key, *leftovers = args
        if key in memory:
            return memory[key](*leftovers)
    else:
        # default
        colloquy1()


def colloquy1(*args):
    colloquy = Colloquy()
    colloquy.drivers.u2d2.com_port.set("COM4")
    colloquy.drivers.u2d2.open()
    colloquy.drivers.arduino.open()
    for dxl in colloquy.drivers.u2d2.dxl_list:
        dxl.init_hardware()

    # Arduino reboot can turn LEDs on at random. Turn them all on and off again.
    colloquy.drivers.neopixels.turn_all_on()
    sleep(0.5)
    colloquy.drivers.neopixels.turn_all_off()

    Server2(colloquy=colloquy)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)
