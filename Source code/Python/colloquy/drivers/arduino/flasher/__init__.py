# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/flasher/__init__.py

"""Putting the sketch in this repo onto the board on the other end.

The page has been able to say the board is running the wrong firmware
since the greeting was added; it has never been able to do anything about
it. That gap got worse with the audio rework, because firmware 2 and
firmware 3 disagree about which pin drives which NeoPixel strip - so a
board left on 2 in an installation wired for 3 answers every command
cheerfully and lights the wrong bodies. `MINIMUM_FIRMWARE_VERSION` makes
the driver refuse that link, which is right, and leaves somebody standing
in a gallery being told to go and find a laptop with the Arduino IDE on
it.

This is that laptop, generally. `drivers/arduino` already knows which
lead the board is on, what is on the USB bus, what version the sketch in
the repo is and what version the board says it is running. Flashing is
the one step that was somewhere else.

**Why it is a thread.** A compile takes the better part of a minute from
cold and an upload takes ten seconds, and `Colloquy.get_states` holds one
lock around the whole application - so a minute spent in here is a minute
in which no page in the tree answers, including the emergency stop's
neighbours. Same problem `Repository.pull` has and the same answer: the
click refuses or accepts instantly, and the work happens on another
thread. The difference is that a repository has a reason to run a loop
and this has none, so the thread's whole life *is* the one job: it starts
when asked, does the thing, and stops.

**Why `start` is not on the page.** Every BaseThread draws one, and here
it would be an unlabelled button that reflashes the installation. The two
named commands are the way in; `stop` stays, because a compile that is
going to fail anyway is worth being able to abandon.

**What it will not do.** Every refusal below is instant and reads the
last known state only - no subprocess, no serial port - so somebody who
clicks and cannot flash is told why in the same request. They are not
paranoia: three of the five are things that would otherwise be found out
by watching avrdude talk to a servo controller.
"""

from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

from .. import boards, firmware
from . import toolchain
from .toolchain import ToolchainError


class Flasher(BaseThread):
    """Compile the sketch, and put it on the board."""

    # None, and there will not be one: a scenario says what the piece does
    # in the room, and this is maintenance. It does turn every light off
    # for twenty seconds, which is why it refuses to run while anything
    # else is - see _why_not_flash. See pytest_tests/test_scenarios.py.
    scenario_names = ()

    def __init__(self, owner):
        super().__init__(owner=owner)

        self._job = None
        self._outcome = None
        self._detail = None
        self._started = None
        self._finished = None

        self["compile only"] = self.compile_only
        self["flash the board"] = self.flash

    @property
    def name(self):
        return "flash firmware"

    @property
    def arduino(self):
        return self.owner

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.owner.params

    # --- what it would run ------------------------------------------------

    @property
    def sketch_folder(self):
        """The folder, not the .ino: that is what arduino-cli takes, and
        `firmware.py` already owns the path to the file inside it."""
        return firmware.SKETCH_PATH.parent

    @property
    def fqbn(self):
        return self.params["arduino"]["fqbn"]

    @property
    def override(self):
        return self.params["arduino"]["arduino-cli"]

    @property
    def port(self):
        return self.params["arduino"]["communication port"]

    def executable(self):
        """Where arduino-cli is, or a ToolchainError saying where it is
        not."""
        return toolchain.find(self.override)

    @property
    def outcome(self):
        """What the last job came to, or None if none has run.

        Public because `test microphone signal` draws it. That test is
        the one place where reflashing this board is part of following
        the instructions rather than a repair, so it offers the flash
        back on its own page - which would be worth nothing if the
        answer only appeared on this one.
        """
        return self._outcome

    # --- the refusals -----------------------------------------------------

    def _why_not_flash(self):
        """Why flashing would be a bad idea, or None if it would not.

        Ordered by what they cost to check and by how badly they end.
        """
        if not self.colloquy.hardware.main_pcb.is_mounted:
            return (
                "the main PCB is noted as unmounted, so the board is not on "
                "the end of anything - put it back first"
            )

        port = self.port
        if not port:
            return "no port chosen - pick the board under 'com port' first"

        found = {board.device: board for board in boards.detect()}
        if port not in found:
            available = ", ".join(sorted(found)) or "none, is the USB lead in?"
            return f"{port!r} is not a port on this machine - available: {available}"

        board = found[port]
        if not board.is_arduino:
            # The one this exists for. The installation has at least two
            # USB serial leads in it, and the other one is the servo bus.
            return (
                f"{port} is {board.name}, which is not a board to flash. "
                "Check 'usb boards' and 'com port'."
            )

        busy = self._threads_in_the_way()
        if busy:
            names = ", ".join(sorted(thread.name for thread in busy))
            return (
                f"{names} still running - the board spends twenty seconds "
                "in its bootloader and answers nothing while it does. Stop "
                "the piece first."
            )

        return None

    # Threads that hang under these are ones that drive the piece, and so
    # ones that will be talking to this board while it is being rewritten.
    IN_THE_WAY = ("drivers", "tests")

    def _threads_in_the_way(self):
        """Running threads that would notice the board going away.

        Not *every* thread, and the difference matters: `Repository` is
        started by main.py on every run and never touches a serial port,
        so refusing on "something is running" would have hidden the flash
        link on the installation permanently - the one machine it is for.
        Filed by where a thread hangs in the tree, which is the only thing
        here that knows what a thread is for.
        """
        return [
            thread
            for thread in self.all_threads
            if thread is not self
            and thread.path.parts
            and thread.path.parts[0] in self.IN_THE_WAY
        ]

    # --- the two commands -------------------------------------------------

    def compile_only(self, request=None):
        """Build the sketch and say whether it built.

        No refusals and no board: it touches nothing but a temporary
        folder, so it is the safe half and it is worth having on its own.
        It is also the honest way to find out whether this machine has a
        working toolchain at all, without gambling a board on the answer.
        """
        return self._begin(("compile", None))

    def flash(self, request=None):
        """Build the sketch and put it on the board."""
        refusal = self._why_not_flash()
        if refusal is not None:
            self._outcome = f"refused: {refusal}"
            self._detail = None
            return self._outcome
        return self._begin(("flash", self.port))

    def _begin(self, job):
        if self.is_started:
            return "already running - wait for it to finish"

        # Found here rather than on the worker, so that "there is no
        # arduino-cli on this machine" is answered in the request that
        # asked instead of appearing as an outcome a refresh later.
        try:
            self.executable()
        except ToolchainError as error:
            self._outcome = f"refused: {error}"
            self._detail = None
            return self._outcome

        self._job = job
        self._outcome = None
        self._detail = None
        self.start()
        doing = "compiling" if job[0] == "compile" else "flashing"
        return f"{doing} - refresh in a moment"

    # --- the work ---------------------------------------------------------

    def setup(self):
        self._started = time()
        self._finished = None

    def loop(self):
        """One job, then done. There is nothing to poll."""
        job, self._job = self._job, None
        if job is None:
            self.stop()
            return

        kind, port = job
        try:
            if kind == "compile":
                self._compile()
            else:
                self._flash(port)
        except ToolchainError as error:
            # A missing toolchain or a subprocess that would not start is
            # a reading, not a thread error: nothing about the
            # installation is broken by it.
            self._outcome = f"failed: {error}"
        self.stop()

    def setdown(self):
        self._finished = time()

    def _compile(self):
        executable = self.executable()
        result = toolchain.run(
            toolchain.compile_command(executable, self.sketch_folder, self.fqbn),
            toolchain.COMPILE_TIMEOUT,
        )
        self._detail = result.tail
        if not result.ok:
            self._outcome = f"compile failed: {toolchain.explain(result)}"
            return
        self._outcome = (
            f"compiled firmware {firmware.sketch_firmware_version()} "
            "- not sent to the board"
        )

    def _flash(self, port):
        """Close the link, upload, open it again.

        Opening it again is not tidiness - it is the check. `Arduino.open`
        waits for the board's greeting and refuses a version it was not
        written for, so a reopen that succeeds is the board saying, in its
        own words, which firmware it is now running. An upload that
        avrdude called a success and that left the wrong image on the
        board would be caught here and nowhere else.
        """
        was_open = self.arduino.is_open
        if was_open:
            # avrdude cannot have the port while pyserial holds it, and
            # the error it gives for that names neither.
            self.arduino.close()

        executable = self.executable()
        result = toolchain.run(
            toolchain.upload_command(executable, self.sketch_folder, self.fqbn, port),
            toolchain.UPLOAD_TIMEOUT,
        )
        self._detail = result.tail

        if not result.ok:
            self._outcome = f"upload failed: {toolchain.explain(result)}"
            self._reopen(was_open)
            return

        if not self._reopen(was_open):
            return

        self._outcome = (
            f"flashed - board says {firmware.describe(self.arduino.greeting)}"
        )

    def _reopen(self, was_open):
        """Put the link back if it was up. Returns whether the board
        greeted, and sets the outcome itself when it did not."""
        if not was_open:
            self._outcome = (
                f"uploaded firmware {firmware.sketch_firmware_version()} "
                "- the link was closed, open the port to check the board"
            )
            return False
        try:
            self.arduino.open()
        except RuntimeError as error:
            self._outcome = f"uploaded, but the board did not come back: {error}"
            return False
        return True

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {"compile only": self.compile_only}
        # The flash link appears only when it would actually do something,
        # the way `Repository.pull` does: the node is quiet until there is
        # a reason not to be, and the reason is on the reading below.
        if self._why_not_flash() is None:
            children["flash the board"] = self.flash
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        # A bare `start` here is an unlabelled button that reflashes the
        # installation. `stop` stays: a compile that is going to fail is
        # worth being able to abandon.
        states.pop("start", None)

        leaf = leaves.into(states, path)

        try:
            leaf("arduino-cli", str(self.executable()))
        except ToolchainError as error:
            leaf("arduino-cli", str(error))

        leaf("board type", self.fqbn)
        leaf("sketch", self.sketch_folder.name)
        leaf(
            "would flash",
            f"firmware {firmware.sketch_firmware_version()} "
            f"at {firmware.sketch_baudrate()} baud",
        )
        leaf("board says", firmware.describe(self.arduino.greeting))

        refusal = self._why_not_flash()
        leaf("can flash", "yes" if refusal is None else f"no - {refusal}")

        if self.is_started:
            leaf("running", f"for {time() - (self._started or time()):.0f}s")
        if self._outcome is not None:
            leaf("outcome", self._outcome)
        if self._detail is not None:
            leaf("arduino-cli said", self._detail)

        return states
