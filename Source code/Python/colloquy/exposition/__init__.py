from datetime import datetime

from colloquy.base import Base
from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

from .schedule import ExpositionSchedule


class Exposition(BaseThread):
    def __init__(self, owner):
        super().__init__(owner)
        self._drivers = self.owner.drivers

        self._thread = None
        # Why the last start did nothing, or None. See why_not_start().
        self._refusal = None
        # When and why the last run ended on an error, or None.
        self._error_stop = None
        self["clear the errors and start again"] = self.clear_errors_and_start

        # When the piece runs itself. Empty and switched off unless
        # somebody has written one, so by default this changes nothing
        # at all and the exposition is started by hand from this page.
        self._schedule = ExpositionSchedule(owner=self)

    @property
    def is_started(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()

    @property
    def name(self):
        return "exposition"

    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace

    @property
    def drivers(self):
        return self._drivers

    @property
    def colloquy(self):
        return self.owner.colloquy

    def open(self):
        self._is_opened = True

    def close(self):
        self._is_opened = False

    def why_not_start(self):
        """Why starting the piece would only crash it, or None.

        The Arduino link is opened once, at startup, and stays open
        (`open_the_hardware`). Not open now means that attempt failed - a
        lead not plugged in, or the wrong port chosen - and every body's
        first NeoPixel or light-sensor command would raise. Started anyway,
        that is ten thread errors, and the error path below shuts the
        drivers down with the class-level latch, after which nothing in
        this process can start until a restart (2026-11-24, on the bench:
        COM6 chosen, no board on it). Refused here, it is one sentence and
        the process stays usable.
        """
        arduino = self.drivers.arduino
        try:
            if arduino.is_open:
                return None
            port = arduino.port_name
        except Exception as error:  # noqa: BLE001 - a refusal must not raise
            return f"the Arduino link cannot be asked: {error}"
        return (
            f"the Arduino link is not open (port {port!r}) - it failed at "
            "startup, see 'startup problems'. Pick the board's port under "
            "drivers > arduino > com port (on a machine without the board, "
            "the simulated arduino port), then restart"
        )

    # --- errors -------------------------------------------------------
    #
    # An error in any thread of the piece stops the piece: its drivers
    # are stopped and the errors are kept, each on its thread's page. It
    # used to latch the class-level shutdown as well, which left nothing
    # in the process startable - every test, the schedule, the laptop's
    # automatic update - until a restart, and said so nowhere. Now the
    # piece alone waits, and says why, until a person presses `clear the
    # errors and start again`. The schedule will not press it for them.

    def failed_threads(self):
        """Every thread of the piece holding errors of its own. Found by
        walking the tree, because `all_threads` forgets a thread once it
        has died, and a thread that died of an error always has."""
        found, seen = [], set()
        stack = [self, self.drivers]
        while stack:
            node = stack.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            errors = getattr(node, "thread_errors", None)
            if isinstance(node, BaseThread) and errors is not None and errors.errors:
                found.append(node)
            stack.extend(child for child in node._dict.values() if isinstance(child, Base))
        return found

    def has_errors(self):
        return bool(self.failed_threads())

    def start(self, started_by=None):
        if self.has_errors():
            self._refusal = (
                "it stopped on an error (see 'stopped on an error'). Press "
                "'clear the errors and start again' once the cause is dealt with"
            )
            self.log(f"Not started: {self._refusal}")
            return
        super().start(started_by=started_by)

    def clear_errors_and_start(self, request=None):
        """The confirmation: a person has read why it stopped."""
        for thread in self.failed_threads():
            thread.thread_errors.clear()
        self._error_stop = None
        self.start(started_by=None)

    def setup(self):
        self._refusal = self.why_not_start()
        if self._refusal is not None:
            self.log(f"Not started: {self._refusal}")
            return
        self.drivers.start(started_by=self)

    def loop(self):
        if self._refusal is not None or not self.drivers.is_started:
            self.stop()

    def setdown(self):
        failed = self.failed_threads()
        if failed:
            names = ", ".join(thread.path.as_posix() for thread in failed)
            self._error_stop = (
                f"at {datetime.now():%H:%M:%S}, on an error in {names}. The "
                "tracebacks are on each thread's page and in its log"
            )
            self.log(f"Stopped on an error in {names}.")
        self.drivers.stop()

    @property
    def schedule(self):
        return self._schedule

    @property
    def snapshot_children(self):
        children = {self._schedule.name: self._schedule}
        if not self.is_started and self.has_errors():
            children["clear the errors and start again"] = self.clear_errors_and_start
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        if not self.is_started:
            if self._error_stop is not None:
                leaf("stopped on an error", self._error_stop)
            elif self.has_errors():
                names = ", ".join(t.path.as_posix() for t in self.failed_threads())
                leaf("stopped on an error", f"errors are held by {names}")
            if self._refusal is not None:
                leaf("not started", self._refusal)
        return states
