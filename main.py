import importlib.util
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


def claim_the_port():
    """The server's port, held from the first line to the server's bind.

    Before anything else, the colloquy import included: importing it
    empties local/logs, and a second main.py must be turned away before it
    has touched what the first one is running on - its logs, its serial
    ports, its schedule. Loaded by path for that reason. See
    colloquy/server2/exclusive_port.py.
    """
    path = source_code / "colloquy" / "server2" / "exclusive_port.py"
    spec = importlib.util.spec_from_file_location("exclusive_port", path)
    exclusive_port = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exclusive_port)
    try:
        return exclusive_port.claim()
    except exclusive_port.PortInUse as refusal:
        print(refusal)
        sys.exit(1)


# Only when run: the tests import this file for open_the_hardware().
PORT_CLAIM = claim_the_port() if __name__ == "__main__" else None

from colloquy import Colloquy
from colloquy.drivers.arduino.errors import FirmwareTooOld
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
    """Open both serial links and wake every servo, and come up either way.

    Split out of colloquy1() so that the "main PCB unmounted" case can
    skip the whole of it rather than each line being guarded. The
    "motors unplugged" case skips only the servo bus, since the Arduino
    is on its own lead and a bench with no chain on it still wants its
    lights and its sound.

    **Nothing in here may stop the server starting.** It used to: every
    call was unguarded, so a board carrying last month's sketch, or one
    servo that did not answer, ended the process on a traceback - taking
    with it the page that would have explained the fault and the command
    that would have fixed it (docs/errors/2026-08-27-01.txt). An
    installation that comes up unable to move is worth far more than one
    that does not come up, so every failure is reported to
    `colloquy.startup` and the rest of the sequence carries on.

    The three halves are independent on purpose. A dead Arduino must not
    cost the servos, a dead servo bus must not cost the lights, and one
    servo that does not answer must not cost the other five.
    """
    if colloquy.hardware.motors.is_plugged_in:
        colloquy.drivers.u2d2.com_port.set("COM4")

        try:
            colloquy.drivers.u2d2.open()
        except Exception as error:
            colloquy.startup.servo_bus_failed(error)
            servos_are_open = False
        else:
            servos_are_open = True
    else:
        # The Dynamixel chain has been taken off (colloquy/hardware/motors/),
        # usually because something else wanted the U2D2's 12 V. The port
        # itself would open perfectly well - the U2D2 is a USB adapter and
        # enumerates with nothing behind it - and then all six servos would
        # fail to answer, one at a time, filling the startup page with six
        # reports of one fact. Say the one fact here instead.
        #
        # Not opening it at all is also what leaves
        # Colloquy.servos_were_opened False, so every homing and torque
        # guard downstream is already right with no extra condition in it.
        since = colloquy.hardware.motors.unplugged_at or "unknown"
        print(
            f"The motors are noted as UNPLUGGED (since {since}).\n"
            "The servo bus has not been opened, so nothing can move. The "
            "Arduino, the lights and every bench test are unaffected.\n"
            "When the chain is back: /app/hardware/motors -> "
            "'the motors are back', then restart."
        )
        servos_are_open = False

    try:
        colloquy.drivers.arduino.open()
    except FirmwareTooOld as error:
        # The one failure here the page can offer a fix for.
        colloquy.startup.arduino_firmware_is_old(error)
        arduino_is_open = False
    except Exception as error:
        colloquy.startup.arduino_failed(error)
        arduino_is_open = False
    else:
        arduino_is_open = True

    if servos_are_open:
        # The six that are wired, not all nine: the three mirrors may not
        # be connected at all, and nothing may enable torque on one until
        # somebody asks for it by hand. See U2D2.body_dxls.
        for body_name, dxl in colloquy.drivers.u2d2.body_dxls.items():
            try:
                dxl.init_hardware()
            except Exception as error:
                colloquy.startup.servo_failed(body_name, dxl, error)

    if arduino_is_open:
        # Arduino reboot can turn LEDs on at random. Turn them all on and off again.
        try:
            colloquy.drivers.neopixels.turn_all_on()
            sleep(0.5)
            colloquy.drivers.neopixels.turn_all_off()
        except Exception as error:
            # The link greeted and then would not carry a command. Worth
            # saying, and not worth refusing to start over.
            colloquy.startup.arduino_failed(error)


def colloquy1(*args):
    colloquy = Colloquy()

    if colloquy.hardware.main_pcb.is_mounted:
        open_the_hardware(colloquy)
    else:
        # The board carrying the Arduino and the U2D2 has been taken out
        # (colloquy/hardware/main_pcb/). Opening either port would fail somewhere
        # down in pyserial, saying something about COM4, which is a poor
        # way to be told a board is missing. Say it here instead and come
        # up anyway.
        #
        # Nothing under `drivers` is opened, started or reachable in this
        # state: the server answers with the standby page instead of the
        # tree (colloquy/server2/standby.py), which offers the files for
        # the boards that replace this one and the press that says a
        # board is back - and that press restarts into the branch above.
        since = colloquy.hardware.main_pcb.unmounted_at or "unknown"
        print(
            f"The main PCB is noted as UNMOUNTED (since {since}).\n"
            "The Arduino and the U2D2 have not been opened and the drivers "
            "are off, so nothing can move or light up.\n"
            "The front page offers the Gerbers and the KiCad projects of "
            "the boards that replace it.\n"
            "When a board is back in the rack: press 'the new PCB is "
            "mounted' on the front page."
        )

    # Watch origin for commits the other computer has pushed. Started
    # here rather than waiting for somebody to click it, because the
    # whole point is that nobody remembers to look. Everywhere but the
    # installation's own laptop it only ever fetches, and pulling stays a
    # link on the page; that one machine pulls what it finds and has the
    # server restart onto it (colloquy/repository/).
    colloquy.repository.start()
    if colloquy.repository.auto_update:
        print(
            "This is the installation's laptop: it pulls what origin has "
            "and restarts onto it by itself."
        )

    # And watch the clock, but only if somebody has switched a schedule
    # on. The note lives in params.json so it survives a restart; with no
    # schedule written this does nothing and the exposition is started by
    # hand from the page, as it always has been.
    if colloquy.exposition.schedule.start_if_enabled():
        print("The exposition schedule is enabled and is now watching the clock.")

    Server2(colloquy=colloquy, claim=PORT_CLAIM)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(*args)
