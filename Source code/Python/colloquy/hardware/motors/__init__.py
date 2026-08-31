# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/motors/__init__.py

"""The Dynamixel chain, and taking it off without losing the calibration.

Beside `main_pcb` because it is the same kind of fact - a cable is about
to come off, and something has to happen first or a number nobody can
recompute is gone. What differs is which cable, how much of the
installation leaves with it, and, crucially, whether the server is
supposed to survive.

**The software already survives unplugged motors, and that is not the
question worth asking.** The U2D2 is a USB adapter: its bridge chip
enumerates whether or not there are servos on the bus behind it, so
`U2D2.open()` succeeds on a bare connector and only the six
`init_hardware()` calls fail - one at a time, each into
`colloquy/startup/`, which is exactly the arrangement `main.py` was
given for a bus that is half there. The page comes up, the Arduino comes
up, the lights work, and the front page grows a `startup problems` node
listing six servos that did not answer. Nothing needed adding for that.

**What does not survive is the calibration**, and that is why this node
exists. Every servo runs in extended position mode, where the count of
whole turns lives in volatile memory. The bar's travel is 293 degrees of
bar, which is 2.4 turns of its servo, so a bar that loses power at the
far end wakes believing it is somewhere else entirely and its
`dxl origin` is then a lie - a measurement at the rig to get back, not a
setting to retype. Homed first it is within one turn of its own zero,
where a power cut costs nothing. Pulling the plug is a power cut.

**Why this does not call `power_down()`.** It is the same first three
steps, and the fourth is fatal here: `power_down()` opens with
`BaseThread.shutdown()`, which sets the **class-level** `_shutdown`
event, and `BaseThread.start()` returns immediately for the rest of the
process once it is set. That is right for `/shutdown` and for unmounting
the main PCB, both of which end with the server stopped and the page
gone. It is precisely wrong here: the reason to unplug the motors is
usually to take the U2D2's 12 V somewhere else and then go on testing
whatever it now feeds, from this same page. A command that silently made
every later `start` a no-op would look like hardware that had stopped
answering. So this stops what drives the piece, homes, cuts torque, and
leaves the process exactly as able to run a test as it was before.

**Two notes, because there are two different facts with two different
lifetimes.**

- `params["motors"]["plugged in"]` is for the **next** start. `main.py`
  reads it and does not open the bus at all, which leaves
  `Colloquy.servos_were_opened` False and every later guard already
  correct, with no new condition anywhere. Written *first*, for
  `main_pcb.unmount`'s reason: a homing that fails halfway must still
  leave the next start knowing.
- `were_unplugged_this_run` is for **this** run, and it is set only once
  the homing has actually happened. It has to be an instance latch
  rather than the params note, and the ordering is the whole reason:
  the note is written before the move, so a guard reading the note would
  skip the very move that protects the calibration. What it buys is a
  later `/shutdown` in the same session that does not spend
  `HOMING_TIMEOUT` - ninety seconds - commanding servos that are lying
  on the bench, and does not then warn that the bar may have lost its
  turn count when it was walked home on purpose.

Nothing clears either note by itself, exactly as nothing clears the main
PCB's: `the motors are back` is a deliberate press, because the
alternative is an installation that quietly decides it can move when it
cannot.
"""
from datetime import datetime

from colloquy.base import Base
from colloquy.ui import leaves


class Motors(Base):
    """Is the servo chain plugged in, and the command to take it off."""

    # Threads hanging under these are the ones that drive the piece, and
    # so the ones that would go on writing goal positions to a bus whose
    # servos are being unplugged. Filed by where a thread hangs in the
    # tree - the same filter, and the same reasoning, as the flasher's
    # IN_THE_WAY: `Repository` is started by main.py on every run, never
    # touches a servo, and must not be stopped by this.
    DRIVING_THE_PIECE = ("drivers", "tests")

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._were_unplugged = False
        self._outcome = None
        self["unplug the motors"] = self.unplug
        self["the motors are back"] = self.replug

    @property
    def name(self):
        return "motors"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.colloquy.params["motors"]

    @property
    def is_plugged_in(self):
        """What the *next* start will believe. Read by main.py."""
        return bool(self.params["plugged in"])

    @property
    def unplugged_at(self):
        return self.params["unplugged at"]

    @property
    def were_unplugged_this_run(self):
        """Has this run already walked them home and cut torque?

        Asked by `Colloquy.servos_can_be_commanded`, and deliberately not
        the same question as `is_plugged_in` - see the module docstring
        on why the note and the latch cannot be one thing.
        """
        return self._were_unplugged

    # --- taking them off --------------------------------------------------

    def unplug(self, request=None):
        """Stop what is driving, walk everything home, cut torque, note it.

        In that order, and every step of it is load-bearing. Returns a
        sentence, which the tree throws away - so the same sentence is
        kept as `outcome` and drawn on the node, which is what the reader
        actually sees when the page re-renders.
        """
        if not self.is_plugged_in:
            self._outcome = (
                "already noted as unplugged - nothing was moved. Press "
                "'the motors are back' first if the chain is on."
            )
            return self._outcome

        # First, and before anything can fail: see the module docstring.
        self.params["plugged in"] = False
        self.params["unplugged at"] = datetime.now().isoformat(timespec="seconds")
        self.log("The motors are being unplugged - bringing everything home.")

        stopped = self._stop_what_drives_the_piece()
        # Still the real, still-connected bus at this point - the latch
        # below is what makes it stop being one, and it is set after.
        arrived = self.colloquy.move_to_origin()
        self.colloquy.disable_torque()
        self._were_unplugged = True

        parts = []
        if stopped:
            parts.append(f"stopped {', '.join(stopped)}")
        if arrived:
            parts.append(
                "everything reached its origin and torque is off - safe to "
                "unplug the chain"
            )
        else:
            parts.append(
                "WARNING: not everything reached its origin before torque was "
                "cut. A servo powered down away from its origin loses its turn "
                "count - check the bar before trusting its calibration"
            )
        self._outcome = "; ".join(parts)
        self.log(self._outcome)
        return self._outcome

    def replug(self, request=None):
        """Say the chain is back. Takes effect at the next start, since
        the bus is opened once, by `main.py`."""
        self.params["plugged in"] = True
        self.params["unplugged at"] = ""
        self._were_unplugged = False
        self._outcome = (
            "The motors are noted as plugged in. Restart the process to open "
            "the servo bus again - nothing has been opened by this."
        )
        self.log(self._outcome)
        return self._outcome

    def _stop_what_drives_the_piece(self):
        """Stop and join every running thread that commands a body.

        Stopped rather than refused-over, unlike the flasher: a flash can
        wait for somebody to press stop, and this cannot usefully - the
        whole sequence exists to get the bodies home, and a search thread
        left running would drive them straight back off their origins
        between the move and the torque being cut.
        """
        threads = [
            thread
            for thread in list(self.all_threads)
            if thread.path.parts and thread.path.parts[0] in self.DRIVING_THE_PIECE
        ]
        for thread in threads:
            thread.stop()
        for thread in threads:
            thread.join()
        return sorted(thread.name for thread in threads)

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        if self.is_plugged_in:
            return {"unplug the motors": self.unplug}
        return {"the motors are back": self.replug}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        if self.is_plugged_in:
            leaf("state", "plugged in")
            leaf(
                "taking them off",
                "'unplug the motors' stops whatever is driving, sends every "
                "body and the bar home, and cuts torque - so the chain can "
                "come off without any servo losing its turn count. The "
                "server keeps running.",
            )
        else:
            leaf("state", f"UNPLUGGED since {self.unplugged_at or 'unknown'}")
            leaf(
                "what that means",
                "the servo bus is not opened at startup, so nothing can move "
                "- the Arduino, the lights and every bench test are "
                "unaffected",
            )
            if not self.were_unplugged_this_run:
                leaf(
                    "this run",
                    "started with the note already written, so the bus was "
                    "never opened",
                )

        if self._outcome is not None:
            leaf("outcome", self._outcome)
        return states
