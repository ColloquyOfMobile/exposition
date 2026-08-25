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


def open_the_hardware(colloquy):
    """Open both serial links and wake every servo.

    Split out of colloquy1() so that the "main PCB unmounted" case can
    skip the whole of it rather than each line being guarded.
    """
    colloquy.drivers.u2d2.com_port.set("COM4")
    colloquy.drivers.u2d2.open()
    colloquy.drivers.arduino.open()
    for dxl in colloquy.drivers.u2d2.dxl_list:
        dxl.init_hardware()

    # Arduino reboot can turn LEDs on at random. Turn them all on and off again.
    colloquy.drivers.neopixels.turn_all_on()
    sleep(0.5)
    colloquy.drivers.neopixels.turn_all_off()


def colloquy1(*args):
    colloquy = Colloquy()

    if colloquy.drivers.main_pcb.is_mounted:
        open_the_hardware(colloquy)
    else:
        # The board carrying the Arduino and the U2D2 has been taken out
        # (drivers/main_pcb/). Opening either port would fail somewhere
        # down in pyserial, saying something about COM4, which is a poor
        # way to be told a board is missing. Say it here instead and come
        # up anyway: the page still works, and it carries the command to
        # say the board is back.
        since = colloquy.drivers.main_pcb.unmounted_at or "unknown"
        print(
            f"The main PCB is noted as UNMOUNTED (since {since}).\n"
            "The Arduino and the U2D2 have not been opened, so nothing can "
            "move or light up.\n"
            "When the board is back: /app/drivers/main pcb -> "
            "'the main PCB is back', then restart."
        )

    # Watch origin for commits the other computer has pushed. Started
    # here rather than waiting for somebody to click it, because the
    # whole point is that nobody remembers to look. It only ever fetches;
    # pulling stays a link on the page.
    colloquy.repository.start()

    Server2(colloquy=colloquy)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)
