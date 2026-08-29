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
        self._in_burst = False

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
        self._in_burst = False

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

        heard = self.hearing.hears(self.male, self.female_name, self.answer)
        if self._count_this_burst(heard):
            self._reinforce()
            return
        if heard:
            return

        if time() - self._last_heard > self.PATIENCE:
            self.log(
                f"{self.male.name} stopped hearing {self.female_name} - "
                "going back to calling."
            )
            self.stop()

    def _count_this_burst(self, hearing_it):
        """One round per burst, not one per tick.

        The loop runs every few milliseconds and a burst sounds for two
        seconds, so asking "can I hear it now" and acting on every yes
        takes the appetite down hundreds of times per message. TJ counts
        a *match*: his receiver produces one per pattern, and
        `timer_reinforce` is reset by the match rather than by the sound
        still being there. So this counts the rising edge - the first tick
        of a burst - and nothing again until the silence that frames it
        has come and gone.

        Found by running it on the simulator: a pair went from a full
        appetite to nothing in four seconds.
        """
        if not hearing_it:
            self._in_burst = False
            return False
        if self._in_burst:
            return False
        self._in_burst = True
        return True

    def _reinforce(self):
        self._last_heard = time()
        self._rounds += 1
        self.shared_drive.decrease(self.male.reinforcement_decrement)

        if self.shared_drive.is_satisfied:
            with self.shared_drive.lock:
                self.shared_drive.value = 0
            self._satisfied_at = time()
            self.log(
                f"{self.male.name} is satisfied by {self.female_name} after "
                f"{self._rounds} rounds."
            )
            self.sing.stop()
            # His own rhythm, and the only sound he makes that is not a
            # message - drivers/satisfaction/.
            self.male.satisfaction.about(self.male.name, self.drive_name)
            self.male.satisfaction.start(started_by=self)

    def setdown(self):
        # Must not raise - BaseThread calls this from a finally block.
        for what, action in (
            ("singing", self.sing.stop),
            ("his moment", self.male.satisfaction.stop),
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
