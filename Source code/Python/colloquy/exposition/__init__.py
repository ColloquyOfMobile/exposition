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
        if self.thread_errors:
            self.drivers.shutdown()
        self.drivers.stop()

    @property
    def schedule(self):
        return self._schedule

    @property
    def snapshot_children(self):
        children = {self._schedule.name: self._schedule}
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._refusal is not None and not self.is_started:
            leaves.into(states, path)("not started", self._refusal)
        return states
