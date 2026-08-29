# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/male/reinforcement/__init__.py

"""What a male does once a female has answered him.

Started by `Male.loop()` when the ears report a female singing **his own
call back to him** while he is searching. That is the whole test: his
identity, naming an appetite he is still short of. A reply meant for the
other male, or naming something he no longer wants, he ignores and
carries on calling (`Logic_male.ino`, and the `an-answer-in-sound`
scenario).

**What he does:** stops calling, stops moving, turns his ring to a steady
full white - the energy lamp - and sings his `R`, the one message a male
ever sings. Every round he takes the same amount off the appetite they
share, and when it falls below the interested floor it is zeroed and the
satisfaction moment begins.

**The divergence, and it is the one worth knowing.** In TJ's original the
male does *not* decide this on sound. Her mirror wiggles his own lamp
light back onto the sensors above and below his ring, and he counts how
many ticks caught light brighter than the room - twenty out of eighty and
the round counts. Sound carries the agreement; what is actually passed
between them is his own light, returned. Nothing drives a mirror in this
port yet (`drivers/mirror/` exists to be calibrated and jogged), so he
runs on the sound channel instead: he keeps going while she keeps
singing. The shape of the exchange, its timing and its endings are hers;
only his *measurement* is substituted, and it goes back to light on the
day a mirror moves.
"""
from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves


class Reinforcement(BaseThread):
    # The whole exchange, both bodies, end to end.
    scenario_names = ("an-answer-in-sound",)

    # Both sides keep the same clock, and it is hers - see
    # female/reinforcement/, which carries where the numbers come from.
    PATIENCE = 205 * 0.05
    SATISFACTION = 120 * 0.05

    def __init__(self, owner):
        super().__init__(owner=owner)
        self.partner = None
        self._last_heard = None
        self._satisfied_at = None
        self._rounds = 0

    @property
    def name(self):
        return "reinforcement"

    @property
    def male(self):
        return self.owner

    @property
    def hearing(self):
        return self.male.drivers.hearing

    @property
    def sing(self):
        return self.male.sing

    @property
    def female_name(self):
        return self.partner[0] if self.partner else None

    @property
    def drive_name(self):
        return self.partner[1] if self.partner else None

    @property
    def shared_drive(self):
        drives = self.male.drives
        return drives.p_drive if self.drive_name == "P" else drives.o_drive

    @property
    def answer(self):
        """His own call - what she is singing back, and what he waits to
        keep hearing."""
        return self.male.colloquy.light_patterns[self.male.name][
            (self.drive_name,)
        ]

    @property
    def reinforcement_pattern(self):
        """His `R`, kept under the empty tuple in the same table."""
        return self.male.colloquy.light_patterns[self.male.name][tuple()]

    @property
    def is_satisfied_moment(self):
        return self._satisfied_at is not None

    @property
    def rounds(self):
        return self._rounds

    @property
    def white(self):
        return dict(red=0, green=0, blue=0, white=255)

    # --- the run ----------------------------------------------------------

    def setup(self):
        if self.partner is None:
            raise ValueError(
                f"{self.male.name} entered reinforcement with no partner."
            )
        self._last_heard = time()
        self._satisfied_at = None
        self._rounds = 0

        self.male.turn_to_origin()

        # The energy lamp: steady, not the pattern. He has stopped asking.
        self.male.ring.color = self.white
        self.male.ring.on()
        self.male.ring.set(1)

        self.sing.pattern = self.reinforcement_pattern
        self.sing.start(started_by=self)

    def loop(self):
        if self.is_satisfied_moment:
            if time() - self._satisfied_at >= self.SATISFACTION:
                self.stop()
            return

        if self.hearing.hears(self.male, self.female_name, self.answer):
            self._reinforce()
            return

        if time() - self._last_heard > self.PATIENCE:
            self.log(
                f"{self.male.name} stopped hearing {self.female_name} - "
                "going back to calling."
            )
            self.stop()

    def _reinforce(self):
        self._last_heard = time()
        self._rounds += 1
        self.shared_drive.decrease()

        if self.shared_drive.is_satisfied:
            with self.shared_drive.lock:
                self.shared_drive.value = 0
            self._satisfied_at = time()
            self.log(
                f"{self.male.name} is satisfied by {self.female_name} after "
                f"{self._rounds} rounds."
            )
            self.sing.stop()

    def setdown(self):
        # Must not raise - BaseThread calls this from a finally block.
        for what, action in (
            ("singing", self.sing.stop),
            ("the ring", self.male.ring.off),
        ):
            try:
                action()
            except Exception as error:  # noqa: BLE001
                self.log(f"Could not stop {self.male.name}'s {what}: {error}")
        self.partner = None

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return self._with_scenarios({"sing": self.sing})

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        if self.partner is not None:
            leaf("partner", f"{self.female_name}, sharing the {self.drive_name} drive")
            leaf("singing", "R - " + "".join(str(b) for b in self.reinforcement_pattern))
            leaf(
                "listening for",
                f"{self.female_name} singing his own call back - "
                + "".join(str(b) for b in self.answer),
            )
        if not self.is_started:
            return states

        leaf("rounds", str(self._rounds))
        leaf("shared drive", str(self.shared_drive.value))
        if self.is_satisfied_moment:
            left = self.SATISFACTION - (time() - self._satisfied_at)
            leaf("satisfaction", f"{max(left, 0):.1f}s left")
        elif self._last_heard is not None:
            leaf("patience", f"{self.PATIENCE - (time() - self._last_heard):.1f}s left")
        return states
