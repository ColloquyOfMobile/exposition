# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/flasher/base.py

"""Compiling a sketch folder onto a port, for whoever owns the board.

This is `Flasher` with the installation taken out of it. It was written
for the one board in the rack, and then `test goertzel ear` and `scope`
turned out to want exactly the same thing for a different board, a
different sketch and a different lead - and `test microphone signal`
wanted it twice, in two directions, on one lead.

**What is genuinely shared is not the board, it is the shape of the
job.** A compile is most of a minute and `Colloquy.get_states` holds one
lock around the whole application, so the click has to refuse or accept
instantly and the work has to happen on another thread. Then the
refusals, which are all instant and all read last-known state - and
three of the four are about the *port*, which every one of these has.
Then the page, which says the same six things in every case: what would
be flashed, whether it can be, what happened, and what the board said
afterwards.

**What is not shared is the link.** The installation's flasher closes
`Arduino`'s port and opens it again, because `Arduino.open()` waits for
the greeting and refuses a version it was not written for - so a reopen
that succeeds is the board saying in its own words which firmware it is
now running. A bench test's link is its own `serial.Serial` and its own
greeting line, and `microphone_plotter` has no greeting at all. So
`_check_the_board()` is a hook, and an owner that cannot ask says so
rather than passing avrdude's word off as the board's.

Subclasses provide `name`, `sketch_folder`, `port` and `sketch_says`,
and may provide `_extra_refusals()`, `_release_the_link()`,
`_check_the_board()` and `_extra_readings()`.
"""

from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

from .. import boards
from . import toolchain
from .toolchain import ToolchainError


class SketchFlasher(BaseThread):
    """Compile one sketch folder, and put it on one board."""

    # None, and there will not be one: a scenario says what the piece does
    # in the room, and this is maintenance. It does turn a board off for
    # twenty seconds, which is why it refuses to run while anything else
    # is. See pytest_tests/test_scenarios.py.
    scenario_names = ()

    # Threads that hang under these are ones that drive the piece, and so
    # ones that will be talking to a board while it is being rewritten.
    #
    # Not *every* thread, and the difference matters: `Repository` is
    # started by main.py on every run and never touches a serial port, so
    # refusing on "something is running" would have hidden the flash link
    # on the installation permanently - the one machine it is for. Filed
    # by where a thread hangs in the tree, which is the only thing here
    # that knows what a thread is for.
    IN_THE_WAY = ("drivers", "tests")

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
    def params(self):
        return self.colloquy.params

    # --- what it would run ------------------------------------------------

    @property
    def sketch_folder(self):
        """The folder, not the .ino: that is what arduino-cli takes, and
        it is also the honest unit - a folder whose name does not match
        its .ino is a thing arduino-cli refuses on its own terms."""
        raise NotImplementedError(self)

    @property
    def port(self):
        """The COM name to upload to, or None where none is chosen."""
        raise NotImplementedError(self)

    def sketch_says(self):
        """One line: what the sketch in this repo would put on the board.

        Read out of the .ino rather than restated, in every subclass -
        `firmware.py`'s arrangement, and for its reason. It may raise
        OSError or RuntimeError if the sketch cannot be read, which the
        page catches; a missing file is a thing to say, not to crash on.
        """
        raise NotImplementedError(self)

    @property
    def fqbn(self):
        """What the board is, in arduino-cli's vocabulary.

        Every board this repo flashes is a Mega 2560. The installation's
        is the one that is configurable, because it is the one somebody
        might replace - see `Flasher`.
        """
        return toolchain.DEFAULT_FQBN

    @property
    def override(self):
        """Where arduino-cli is, if params names it.

        Read out of the one `arduino` section whichever board is being
        flashed: it is a fact about this *machine*, not about the board on
        the other end of a lead.
        """
        return self.params["arduino"]["arduino-cli"]

    def executable(self):
        """Where arduino-cli is, or a ToolchainError saying where it is
        not."""
        return toolchain.find(self.override)

    @property
    def outcome(self):
        """What the last job came to, or None if none has run.

        Public because a test that flashes its own board draws it beside
        its own readings - the answer would be worth much less if it only
        ever appeared on this page.
        """
        return self._outcome

    # --- the refusals -----------------------------------------------------

    def _extra_refusals(self):
        """Anything this board's owner knows that this class does not.

        The installation's PCB being unscrewed, a sibling test holding the
        same lead - neither is a question about a port, and neither is
        answerable here.
        """
        return None

    def _why_not_flash(self):
        """Why flashing would be a bad idea, or None if it would not.

        Ordered by what they cost to check and by how badly they end, with
        the owner's own first: it knows things about its board that make
        every question below it moot.
        """
        extra = self._extra_refusals()
        if extra is not None:
            return extra

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
                "it first."
            )

        return None

    def _threads_in_the_way(self):
        """Running threads that would notice the board going away."""
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
        return f"{doing} {self.sketch_folder.name} - refresh in a moment"

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
        self._outcome = f"compiled {self.sketch_says()} - not sent to the board"

    def _flash(self, port):
        """Let go of the link, upload, then ask the board what it now is.

        Asking afterwards is not tidiness - it is the check. An upload
        that avrdude called a success and that left the wrong image on
        the board is caught there and nowhere else.
        """
        state = self._release_the_link()

        executable = self.executable()
        result = toolchain.run(
            toolchain.upload_command(executable, self.sketch_folder, self.fqbn, port),
            toolchain.UPLOAD_TIMEOUT,
        )
        self._detail = result.tail

        if not result.ok:
            self._outcome = f"upload failed: {toolchain.explain(result)}"
            # Still put the link back: the board is in whatever state
            # avrdude left it, and the page is more use saying which.
            self._check_the_board(state)
            return

        said = self._check_the_board(state)
        if said is None:
            # No handshake was possible, and that is said plainly rather
            # than dressed up - avrdude's word is the only word there is.
            self._outcome = (
                f"uploaded {self.sketch_says()} - nothing here reads this "
                "board's greeting, so avrdude's word is all there is"
            )
            return
        self._outcome = said

    def _release_the_link(self):
        """Let go of the port so avrdude can have it.

        Returns whatever `_check_the_board` will need to put it back -
        typically whether it was open. avrdude cannot have the port while
        pyserial holds it, and the error it gives for that names neither.
        """
        return None

    def _check_the_board(self, state):
        """What the board says about itself now, as a whole outcome line.

        None where this owner has no way to ask, which is the honest
        answer for `microphone_plotter`: it streams numbers and greets
        with nothing. An owner that *can* ask returns the sentence it
        wants on the page, because a failed handshake and a successful
        one are two different sentences and only the owner knows how to
        tell them apart.
        """
        return None

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
        # A bare `start` here is an unlabelled button that reflashes a
        # board. `stop` stays: a compile that is going to fail anyway is
        # worth being able to abandon.
        states.pop("start", None)

        leaf = leaves.into(states, path)

        try:
            leaf("arduino-cli", str(self.executable()))
        except ToolchainError as error:
            leaf("arduino-cli", str(error))

        leaf("board type", self.fqbn)
        leaf("sketch", self.sketch_folder.name)
        leaf("port", self.port or "none chosen")
        try:
            leaf("would flash", self.sketch_says())
        except (OSError, RuntimeError) as error:
            leaf("would flash", f"the sketch could not be read: {error}")

        self._extra_readings(leaf)

        refusal = self._why_not_flash()
        leaf("can flash", "yes" if refusal is None else f"no - {refusal}")

        if self.is_started:
            leaf("running", f"for {time() - (self._started or time()):.0f}s")
        if self._outcome is not None:
            leaf("outcome", self._outcome)
        if self._detail is not None:
            leaf("arduino-cli said", self._detail)

        return states

    def _extra_readings(self, leaf):
        """Whatever this owner knows about the board on the other end.

        The installation's flasher says what its link greeted with; a
        bench test's says which firmware it last handshook. Nothing here,
        because this class has no link.
        """
