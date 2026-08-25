# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/main_pcb/__init__.py

"""The board carrying the Arduino and the U2D2, and taking it out safely.

Both serial links into the installation land on one PCB, so unmounting it
disconnects the Arduino and the U2D2 together. Two things have to happen
before the cables come off, and one of them is easy to forget:

**Everything has to go home first.** Every servo runs in extended
position mode, where the count of whole turns lives in volatile memory.
The bar's travel is 293 degrees of bar, which is 2.4 turns of its servo,
so a bar powered down at the far end wakes up believing it is somewhere
else entirely - and its calibration is then a lie. Homed first, it is
within one turn of its own zero and a power cut costs nothing. The bodies
sway either side of their own origins and so are never more than half a
turn out, but they are sent home too: it is free, and "the ones that
mattered" is a worse rule to remember than "everything".

**The next start has to know.** Otherwise it reaches for two serial ports
that are physically not there and fails somewhere down in pyserial,
saying something about COM4. With the note written, `main.py` skips
opening them and says plainly what it is doing.

Nothing clears the note by itself. A board that is out stays out until
somebody presses `the main PCB is back`, because the alternative is an
installation that quietly decides it has hardware when it has not.

**On where this lives.** Under `hardware`, not under `drivers`. The
difference is the one the 2026-08-21 rename drew: `drivers` is the layer
that drives the piece, and this is the equipment itself - a board, its
screws, and whether it is in the rack. It is also neither the Arduino's
nor the U2D2's to own, since it carries both and unmounting it takes out
both at once.
"""
from datetime import datetime

from colloquy.base import Base
from colloquy.ui import leaves


class MainPCB(Base):
    """Is the board in, and the command to take it out."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self["unmount the main PCB"] = self.unmount
        self["the main PCB is back"] = self.remount

    @property
    def name(self):
        return "main pcb"

    @property
    def params(self):
        return self.colloquy.params["main pcb"]

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def is_mounted(self):
        return bool(self.params["mounted"])

    @property
    def unmounted_at(self):
        return self.params["unmounted at"]

    # --- the two commands -------------------------------------------------

    def unmount(self, request=None):
        """Write the note, bring everything home, cut torque, stop the server.

        In that order, and the order is the whole point: the note is
        written *first* so that a shutdown which then fails halfway still
        leaves the next start knowing the board is going away. Homing
        before torque is cut is what saves the calibration.

        This runs inside a page request, which already holds the command
        lock (`Colloquy.get_states`), so it calls `power_down()` directly
        rather than `hold_commands()` - that would sit waiting for a lock
        this very call is holding.
        """
        self.params["mounted"] = False
        self.params["unmounted at"] = datetime.now().isoformat(timespec="seconds")
        self.log("Main PCB is being unmounted - bringing everything home.")

        arrived = self.colloquy.power_down()
        stopping = self.colloquy.request_stop()

        lines = [
            "The main PCB is noted as unmounted.",
            (
                "Everything reached its origin."
                if arrived
                else "WARNING: not everything reached its origin before torque "
                "was cut - check the bar before trusting its calibration."
            ),
            "Torque is off on every servo.",
            (
                "The server is stopping; it is safe to disconnect once this "
                "page has finished loading."
                if stopping
                else "No server to stop - close the process by hand before "
                "disconnecting."
            ),
        ]
        return " ".join(lines)

    def remount(self, request=None):
        """Say the board is back. Takes effect at the next start, since
        the ports are opened once, at startup."""
        self.params["mounted"] = True
        self.params["unmounted at"] = ""
        self.log("Main PCB is noted as mounted again.")
        return (
            "The main PCB is noted as mounted. Restart the process to open "
            "the Arduino and the U2D2 again."
        )

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        if self.is_mounted:
            return {"unmount the main PCB": self.unmount}
        return {"the main PCB is back": self.remount}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        if self.is_mounted:
            leaf("state", "mounted")
        else:
            leaf("state", f"UNMOUNTED since {self.unmounted_at or 'unknown'}")
            leaf(
                "what that means",
                "the Arduino and the U2D2 were not opened at startup - "
                "nothing can move or light up until the board is back",
            )
        return states
