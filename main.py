import sys
from time import sleep
from pathlib import Path
# import matplotlib
# # run matplotlib without GUI
# matplotlib.use("Agg")

raise NotImplementedError("Fix the test result UI!")

cwd = Path(__file__).parent
# server_code = cwd / "Server"
# sys.path.append(str(server_code.resolve()))
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

from colloquy import Colloquy
from colloquy.server2 import Server2

# from server import server
# from wsgi import make_wsgi
from threading import Event


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
    colloquy.hardware.u2d2.com_port.set("COM4")
    colloquy.hardware.u2d2.open()
    colloquy.hardware.arduino.open()
    for dxl in colloquy.hardware.u2d2.dxl_list:
        dxl.init_hardware()

    # Arduino reboot can turn LEDs on at random. Turn them all on and off again.
    colloquy.hardware.neopixels.turn_all_on()
    sleep(0.5)
    colloquy.hardware.neopixels.turn_all_off()

    Server2(colloquy=colloquy)


def as_text(memory):
    lines = as_lines(memory)
    return "\n".join("".join(tokens) for tokens in lines)


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
            lines.append([f"{value['name']}:"])
            lines += as_lines(value)
            continue

        if "value" in value:
            lines.append([f"{value['name']}: {value['value']}"])
            continue

        lines.append([f"{value['name']}"])

    return add_indent(lines)


def add_indent(lines):
    return [["|", *tokens] for tokens in lines]


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)
