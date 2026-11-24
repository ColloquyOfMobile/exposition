"""Which tree commands are pressed and not yet answered, for every open page.

A press is one request, and the request thread is what knows it is
waiting. It says so twice: `pressed` when the request arrives (queued,
since another command may hold the command lock), and `started` from
inside the walk once the lock is held and the command is about to run.
The live stream (`ui/live.py`) reads `snapshot()` and tells every open
page, so a button spins on every screen looking at it and not only on the
one that pressed it.

A command is named by its node path and its own name with the `call`
marker and the page's root left out: `drivers/female1/call/home` pressed
on `/app/drivers` and `call/home` pressed on `/app/drivers/female1` are
the same command, and both pages draw it.
"""
from contextlib import contextmanager
from threading import Lock, get_ident
from time import monotonic

QUEUED = "queued"
RUNNING = "running"


def command_of(parts):
    """`("drivers", "call", "female1", "home")` -> `"drivers/female1/home"`."""
    return "/".join(str(part) for part in parts if part != "call")


class InFlight:
    def __init__(self):
        self._lock = Lock()
        self._entries = {}
        self.revision = 0

    @contextmanager
    def pressed(self, command):
        """For as long as the request runs. Nested presses on one thread
        (there are none) would keep the outer one."""
        ident = get_ident()
        with self._lock:
            mine = ident not in self._entries
            if mine:
                self._entries[ident] = [command, QUEUED, monotonic()]
                self.revision += 1
        try:
            yield
        finally:
            if mine:
                with self._lock:
                    self._entries.pop(ident, None)
                    self.revision += 1

    def started(self):
        """The calling thread's press has the lock now. A walk with no
        press around it (a test, a direct call) is nobody's business."""
        with self._lock:
            entry = self._entries.get(get_ident())
            if entry is not None and entry[1] != RUNNING:
                entry[1] = RUNNING
                entry[2] = monotonic()
                self.revision += 1

    def snapshot(self):
        """`[{"command", "state", "seconds"}]`, oldest first."""
        now = monotonic()
        with self._lock:
            entries = sorted(self._entries.values(), key=lambda entry: entry[2])
            return [
                {"command": command, "state": state, "seconds": round(now - since, 1)}
                for command, state, since in entries
            ]


# One per process, like the one server per port.
IN_FLIGHT = InFlight()
