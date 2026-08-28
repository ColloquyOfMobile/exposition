import serial
import serial.tools.list_ports

import json
from time import time
from threading import Lock
from colloquy.base import Base
from colloquy.ui import leaves
from . import boards
from . import firmware
from colloquy.drivers.com_port import SIMULATED_ARDUINO_PORT

from .boards import Boards
from .com_port import ComPort
from .errors import ArduinoError, FirmwareTooOld
from .flasher import Flasher

from .neopixel_command import NeopixelCommand
from .light_sensor_command import LightSensorCommand


class Arduino(Base):
    _classes = {
        "serial": serial.Serial,
    }

    # How long the board is given to announce itself after the port is
    # opened. It reboots when the port opens, and a Mega spends most of a
    # second in its bootloader before the sketch runs at all.
    GREETING_TIMEOUT = 2.0

    def __init__(self, owner, **kwargs):
        """
        Initialise la communication série avec l'Arduino.
        """
        super().__init__(owner=owner)
        self.lock = Lock()
        self._port_handler = None
        # Which kind the handler in hand is, since the two are different
        # objects and changing lead may mean replacing it. None until one
        # has been built. See use_port().
        self._handler_is_the_stand_in = None
        self._was_open = None
        self._context_depth = 0
        self._commands = [
            NeopixelCommand(owner=self, arduino_path="f1/head"),
            NeopixelCommand(owner=self, arduino_path="f1/bodyO"),
            NeopixelCommand(owner=self, arduino_path="f1/bodyP"),
            NeopixelCommand(owner=self, arduino_path="f1/feet"),
            LightSensorCommand(owner=self, arduino_path="f1/light sensor"),
            NeopixelCommand(owner=self, arduino_path="f2/head"),
            NeopixelCommand(owner=self, arduino_path="f2/bodyO"),
            NeopixelCommand(owner=self, arduino_path="f2/bodyP"),
            NeopixelCommand(owner=self, arduino_path="f2/feet"),
            LightSensorCommand(owner=self, arduino_path="f2/light sensor"),
            NeopixelCommand(owner=self, arduino_path="f3/head"),
            NeopixelCommand(owner=self, arduino_path="f3/bodyO"),
            NeopixelCommand(owner=self, arduino_path="f3/bodyP"),
            NeopixelCommand(owner=self, arduino_path="f3/feet"),
            LightSensorCommand(owner=self, arduino_path="f3/light sensor"),
            NeopixelCommand(owner=self, arduino_path="m1/ring"),
            NeopixelCommand(owner=self, arduino_path="m1/up ring"),
            NeopixelCommand(owner=self, arduino_path="m1/p drive level"),
            NeopixelCommand(owner=self, arduino_path="m1/o drive level"),
            LightSensorCommand(owner=self, arduino_path="m1/light sensor/a"),
            LightSensorCommand(owner=self, arduino_path="m1/light sensor/b"),
            LightSensorCommand(owner=self, arduino_path="m1/light sensor/c"),
            LightSensorCommand(owner=self, arduino_path="m1/light sensor/d"),
            NeopixelCommand(owner=self, arduino_path="m2/ring"),
            NeopixelCommand(owner=self, arduino_path="m2/up ring"),
            NeopixelCommand(owner=self, arduino_path="m2/p drive level"),
            NeopixelCommand(owner=self, arduino_path="m2/o drive level"),
            LightSensorCommand(owner=self, arduino_path="m2/light sensor/a"),
            LightSensorCommand(owner=self, arduino_path="m2/light sensor/b"),
            LightSensorCommand(owner=self, arduino_path="m2/light sensor/c"),
            LightSensorCommand(owner=self, arduino_path="m2/light sensor/d"),
        ]

        for command in self._commands:
            self[command.name] = command

        self._com_port = ComPort(owner=self)
        self[self.com_port.name] = self.com_port

        # What is on the USB bus, whether or not any of it is ours. Every
        # other diagnosis in here needs a working link first; this one
        # does not need the link at all.
        self._boards = Boards(owner=self)
        self[self._boards.name] = self._boards

        # Putting the sketch in this repo onto the board on the other end.
        # It belongs here rather than anywhere else because everything it
        # needs is already on this node - which lead, what is on the bus,
        # what version the sketch is and what version the board says it
        # is. Flashing was the one step that was somewhere else.
        self._flasher = Flasher(owner=self)
        self[self._flasher.name] = self._flasher

        # What the board said about itself the last time the port was
        # opened - None until it has been asked. See firmware.py.
        self._greeting = None

        self["open"] = self.open
        self["close"] = self.close

    def __enter__(self):
        with self.lock:
            if self._context_depth == 0:
                self._was_open = self.port_handler.is_open
                if not self._was_open:
                    self.open()
            self._context_depth += 1

    def __exit__(self, *args, **kwargs):
        with self.lock:
            self._context_depth -= 1
            if self._context_depth == 0 and not self._was_open:
                self.close()

    @property
    def commands(self):
        return self._commands

    @property
    def port_name(self):
        return self.port_handler.port

    @property
    def com_port(self):
        return self._com_port

    @property
    def boards(self):
        return self._boards

    @property
    def flasher(self):
        return self._flasher

    @property
    def greeting(self):
        """What the board said about itself when the port was last
        opened, or None if it has not been asked yet."""
        return self._greeting

    @property
    def problems(self):
        """Everything currently wrong with this link, in words.

        Empty when params.json, the sketch in this repo and the board on
        the other end all say the same thing. Read on the page rather
        than raised: a request that raises is taken for a crash serious
        enough to emergency-stop the installation (Server2.wsgi), and a
        baud rate typed wrong on the params page is not that. It becomes
        fatal at open(), which is where it stops anything from working.
        """
        return firmware.problems(self.baudrate, self._greeting)

    @property
    def is_open(self):
        return self.port_handler.is_open

    @property
    def colloquy(self):
        return self.owner.colloquy

    # @property

    @property
    def params(self):
        return self.owner.params

    @property
    def name(self):
        return "arduino"

    @property
    def baudrate(self):
        return self.params["arduino"]["baudrate"]

    @property
    def is_using_the_stand_in(self):
        """Is this link the virtual serial port rather than a real lead?

        Asked of the **lead**, not of the machine. `is_simulated` answers
        "is the piece here", which is not the same question as "is an
        Arduino plugged into this computer" - and the two came apart the
        first afternoon the main PCB was carried off to a desk to be
        debugged. On the bench `is_simulated` is true and the board is
        nonetheless on the end of a USB lead.

        Everything the sound channel does goes through this link and
        nothing else in it asks the question at all (speaker, microphone,
        all audio and both installation audio tests are silent on
        `is_simulated`), so this one property is the whole of what "real"
        means for a voice.
        """
        return self.params["arduino"]["communication port"] == SIMULATED_ARDUINO_PORT

    @property
    def port_handler(self):
        if self._port_handler is None:
            self._handler_is_the_stand_in = self.is_using_the_stand_in
            if self._handler_is_the_stand_in:
                self._port_handler = self.colloquy.virtual_drivers.arduino_serial_port
            else:
                self._port_handler = serial.Serial(baudrate=self.baudrate, timeout=1)

            # Setting port name here avoid opening the port
            self._port_handler.port = self.params["arduino"]["communication port"]

        return self._port_handler

    def use_port(self, port_name):
        """Point the link at a lead, with the right handler behind it.

        A real lead and the stand-in are different objects, so moving
        between them is not a matter of writing a new name onto the
        handler already in hand - that one has to go first. It is closed
        before it is dropped: a discarded pyserial handle keeps the COM
        port open until the garbage collector reaches it, and the next
        open then fails saying the port is busy, which reads exactly like
        a board that is not there.
        """
        wants_the_stand_in = port_name == SIMULATED_ARDUINO_PORT
        if (
            self._port_handler is not None
            and self._handler_is_the_stand_in != wants_the_stand_in
        ):
            if self._port_handler.is_open:
                self._port_handler.close()
            self._port_handler = None

        self.port_handler.port = port_name

    def send(self, path, **data):
        with self:
            return self._send_unsafe(path, **data)

    def _send_unsafe(self, path, **data):
        command = {"path": path.as_posix(), **data}
        self.log(f"{command=}")
        serialized_command = f"{json.dumps(command)}\n"  # Conversion en JSON
        with self.lock:
            self.port_handler.write(
                serialized_command.encode("utf-8")
            )  # Envoie de la commande

            data = self.port_handler.readline()  # Lit une ligne du port série
        # if not data:
        # raise TimeoutError("No response from Arduino.")

        return data

    def _parse(self, data):
        """
        Analyse les données brutes reçues de l'Arduino.

        Arguments :
        - data : Données brutes (bytes) reçues.

        Retourne :
        - Un type natif Python (par exemple dictionnaire).
        """
        data = data.decode("utf-8")
        try:
            data = json.loads(data)  # Convertir JSON en dictionnaire
        except json.JSONDecodeError:
            raise ValueError(f"Invalid response format from Arduino. ({data=})")

        if data["status"] == "error":
            raise RuntimeError(data["message"])

        self.log(f"response={data}")
        return data

    def close(self, request=None):
        """
        Ferme le port série.
        """
        self.port_handler.close()

    def open(self, request=None):
        """Open the link, and make sure it is one.

        Three things have to agree before a single command means anything:
        what params.json is about to open the port at, what the sketch in
        this repo sets, and what is actually flashed on the board. They
        are checked in that order, which is the order they cost in - the
        first needs no hardware at all, and it is the mismatch that
        happens by itself, since the two numbers live in two files edited
        on two different occasions.

        All three failures are raised rather than logged. Every one of
        them means nothing that follows will work, and the way they show
        up otherwise is a female who reads no pattern for forty minutes.
        """
        self._greeting = None

        problems = firmware.baudrate_problems(self.baudrate)
        if problems:
            raise ArduinoError(f"Arduino: {' '.join(problems)}")

        # The handler was built with whatever params said at the time, and
        # params can be edited from the page between two opens.
        self.port_handler.baudrate = self.baudrate
        self.port_handler.open()
        self.wait_for_reboot()

    def wait_for_reboot(self):
        """Wait for the board to say who it is, and check the answer.

        Opening the port reboots the board, and it greets. Since firmware
        2 the greeting is a line of JSON naming the protocol version and
        the baud rate it is running at, which is what makes this a check
        and not just a wait: a board flashed with something older, or
        talking at some other rate, says so here instead of half-working
        for the rest of the run.
        """
        greeting = self._read_greeting()
        if greeting is None:
            raise ArduinoError(self._diagnose_silence())

        self._greeting = greeting
        self.log(f"Arduino on {self.port_name}: {firmware.describe(greeting)}")

        problems = firmware.greeting_problems(greeting, self.baudrate)
        if problems:
            message = f"Arduino on {self.port_name}: {' '.join(problems)}"
            # An old sketch is the one failure here with a remedy the page
            # can offer, so it gets its own class and startup turns it into
            # the offer instead of a traceback. See drivers/arduino/errors.py.
            if firmware.is_too_old(greeting):
                raise FirmwareTooOld(message, greeting=greeting)
            raise ArduinoError(message)

    def _read_greeting(self, timeout=None):
        """The board's own line about itself, or None if none arrived.

        Anything unparseable is logged and skipped rather than believed:
        at the wrong baud rate the board answers with rubbish, and rubbish
        occasionally contains a newline.
        """
        if timeout is None:
            timeout = self.GREETING_TIMEOUT
        start = time()
        while time() - start < timeout:
            self.log("Waiting for Arduino to reboot.")
            line = self.port_handler.readline().strip()
            if not line:
                continue
            greeting = firmware.parse_greeting(line)
            if greeting is not None:
                return greeting
            self.log(f"Not a greeting: {line!r}")
        return None

    def _diagnose_silence(self):
        """Nothing legible came back. Say what is actually on the lead.

        A wrong baud rate is the quietest failure this link has: the board
        is there, it is answering, and every byte of it is rubbish. So
        before giving up, the port is reopened at each rate the sketch has
        ever run at - reopening toggles DTR, which reboots the Mega, which
        makes it greet again - and if one of them produces a greeting then
        that is the whole diagnosis in one sentence.

        Failing that, the USB bus itself is worth reporting: a board that
        has never been flashed still enumerates, so "a Mega is plugged in
        and it is not talking" is a different thing from "there is nothing
        there", and only one of them means fetch a cable. See boards.py.

        Not on the stand-in, which ignores baud rates entirely - it would
        "find" the board at the first rate tried and say something
        confidently wrong. The stand-in is told by the lead rather than by
        the machine: a real board on a simulated machine is now an
        ordinary thing to meet.
        """
        where = f"Arduino on {self.port_name}"
        if self.is_using_the_stand_in:
            return f"{where} did not greet within {self.GREETING_TIMEOUT}s."

        for baudrate in firmware.PROBE_BAUDRATES:
            if baudrate == self.baudrate:
                continue
            greeting = self._greet_at(baudrate)
            if greeting is None:
                continue
            return (
                f"{where} is talking at {baudrate} baud, not the "
                f"{self.baudrate} this port was opened at: it is running "
                f"{firmware.describe(greeting)}. Flash "
                f"{firmware.SKETCH_PATH.name} onto it."
            )

        plugged_in = boards.detect()
        if not plugged_in:
            return (
                f"{where} did not answer, and this machine has no serial "
                f"ports at all. Is the USB lead in?"
            )
        return (
            f"{where} did not answer at any rate this sketch has ever "
            f"used. What is plugged in: "
            f"{'; '.join(board.label for board in plugged_in)}. A board "
            f"that has never been flashed looks exactly like this - it "
            f"appears on the bus and says nothing."
        )

    def _greet_at(self, baudrate):
        """Reopen the port at one other rate and listen for a greeting.

        The port is left as it was found, open at its own baud rate,
        whatever the answer - the caller is about to raise, and a port
        left closed behind a raised exception is one more thing wrong
        than there needs to be.
        """
        handler = self.port_handler
        self.log(f"Listening for the Arduino at {baudrate} baud.")
        try:
            handler.close()
            handler.baudrate = baudrate
            handler.open()
            return self._read_greeting()
        finally:
            handler.close()
            handler.baudrate = self.baudrate
            handler.open()


    # --- the page ---------------------------------------------------------

    def _open_node(self):
        """Expand this node on the page.

        Not self.open(): that one opens the serial port. Base.open/close
        are what the page's open/close link calls on every node, and this
        class happens to have overridden both of those names with the
        link's own. Drawn as it stood, clicking the Arduino to look inside
        it would have opened the port instead of the node.
        """
        self._is_opened = True

    def _close_node(self):
        self._is_opened = False

    def _snapshot_base_states(self, path):
        states = super()._snapshot_base_states(path)
        states["open"] = self._open_node
        states["close"] = self._close_node
        return states

    @property
    def snapshot_children(self):
        """Which lead, and what is on the bus.

        Not the thirty-odd pixel groups and sensors: those are reached
        from the bodies that own them, and a flat list of them here would
        bury the two things this node is for.
        """
        return {
            self.com_port.name: self.com_port,
            self._boards.name: self._boards,
            self._flasher.name: self._flasher,
        }

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf("port", self.params["arduino"]["communication port"] or "not set")
        # The one thing this node must never be ambiguous about. The
        # stand-in answers every command exactly as the board does - a
        # speaker reports "sounding", a microphone reports a band rising -
        # so without this line a simulated run and a real one read alike,
        # which is how an afternoon gets spent debugging a simulation.
        leaf(
            "driving",
            "the stand-in - nothing here is a board"
            if self.is_using_the_stand_in
            else "a real board on this lead",
        )
        leaf("baudrate", f"{self.baudrate} baud")
        leaf("link", "open" if self.is_open else "closed")
        # The two ends, side by side, which is the whole point of showing
        # any of this: one line for what this repo would flash, one for
        # what the board last said it was running.
        leaf(
            "sketch in this repo",
            f"firmware {firmware.sketch_firmware_version()} "
            f"at {firmware.sketch_baudrate()} baud",
        )
        leaf("board says", firmware.describe(self._greeting))

        problems = self.problems
        leaf("in sync", "yes" if not problems else "NO")
        for number, problem in enumerate(problems, start=1):
            leaf(f"problem {number}", problem)

        # Named for what they do, since "open" and "close" on this node
        # now mean the node - see _open_node above.
        states["open port"] = self.open
        states["close port"] = self.close
        return states
