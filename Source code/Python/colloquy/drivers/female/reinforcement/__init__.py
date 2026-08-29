# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/female/reinforcement/__init__.py

"""What a female does once she has found a male.

Started by `Female.loop()` when her search ends on a find, with the pair
it found in `partner`. This is the half of the interaction that brings an
appetite back down, and until it was written nothing in the installation
came of a match.

**The exchange, as TJ runs it** (`Logic_fem.ino`, and the
`an-answer-in-sound` scenario in plain language):

1. She stops turning and sings **his own pattern back to him** - the same
   ten bits she just decoded off his ring, as tone rather than light. It
   is not a message of her own: it is his identity with the one appetite
   named that they share.
2. He accepts it, stops calling, and sings his `R` - the seventh message,
   one per male, the only thing a male ever sings.
3. Every time she hears that `R` she takes a fixed amount off the shared
   appetite and resets her patience.
4. When that appetite falls below the interested floor it is zeroed and a
   satisfaction moment begins - the only moment in the piece where a body
   has what it wanted.
5. If the `R` stops coming for long enough she gives up and goes back to
   looking.

**Two deliberate divergences**, both recorded in CODE_DOCUMENTATION 8:

- **The ears are emulated** (`drivers/hearing/`). The microphones are not
  in service, so what she hears is computed from what is being sung. The
  behaviour is real; the hearing is not, and the page says so.
- **She does not wiggle her mirror.** In the original her mirror returns
  his own lamp light to the sensors above and below his ring, and *that*
  is what he measures to decide the exchange is working. Nothing drives a
  mirror here yet (`drivers/mirror/`), so the male's half runs on the
  sound channel instead - see `male/reinforcement/`. When the mirrors are
  driven, his measurement moves back to light and hers does not change.
"""
from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves


class Reinforcement(BaseThread):
    # The whole exchange, both bodies, end to end.
    scenario_names = ("an-answer-in-sound",)

    # TJ's `timer_reinforce > (com_pattern_count * 5) + 5` - 205 ticks of
    # his 50 ms clock. Long enough to sit through two of his bursts and
    # the silences around them without giving up on a partner who is
    # simply between messages.
    PATIENCE = 205 * 0.05

    # `timer_satisfaction > com_pattern_count * 3` - 120 ticks. The one
    # moment in the piece where a body has what it wanted, and it is over
    # in six seconds.
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
    def female(self):
        return self.owner

    @property
    def hearing(self):
        return self.female.drivers.hearing

    @property
    def sing(self):
        return self.female.sing

    @property
    def male_name(self):
        return self.partner[0] if self.partner else None

    @property
    def drive_name(self):
        return self.partner[1] if self.partner else None

    @property
    def shared_drive(self):
        """The one appetite this encounter is about."""
        drives = self.female.drives
        return drives.p_drive if self.drive_name == "P" else drives.o_drive

    @property
    def answer(self):
        """His pattern, which is what she sings back."""
        return self.female.colloquy.light_patterns[self.male_name][
            (self.drive_name,)
        ]

    @property
    def reinforcement_pattern(self):
        """His `R` - TJ's com_pattern_I_R / II_R, kept in the same table
        under the empty tuple. See Colloquy.light_patterns."""
        return self.female.colloquy.light_patterns[self.male_name][tuple()]

    @property
    def is_satisfied_moment(self):
        return self._satisfied_at is not None

    @property
    def rounds(self):
        """How many times she has heard his `R` this encounter."""
        return self._rounds

    # --- the run ----------------------------------------------------------

    def setup(self):
        if self.partner is None:
            raise ValueError(
                f"{self.female.name} entered reinforcement with no partner."
            )
        self._last_heard = time()
        self._satisfied_at = None
        self._rounds = 0
        self._in_burst = False

        # She stops turning. The search thread has already ended; this is
        # the body itself being held still while the exchange happens.
        self.female.turn_to_origin()

        self.sing.pattern = self.answer
        self.sing.start(started_by=self)

    def loop(self):
        if self.is_satisfied_moment:
            self._run_satisfaction()
            return

        heard = self.hearing.hears(
            self.female, self.male_name, self.reinforcement_pattern
        )
        if self._count_this_burst(heard):
            self._reinforce()
            return
        if heard:
            return

        if time() - self._last_heard > self.PATIENCE:
            self.log(
                f"{self.female.name} heard nothing from {self.male_name} for "
                f"{self.PATIENCE:.1f}s - giving up and going back to looking."
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
        """One round: take the agreed amount off the shared appetite."""
        self._last_heard = time()
        self._rounds += 1
        self.shared_drive.decrease(self.female.reinforcement_decrement)

        if self.shared_drive.is_satisfied:
            self._begin_satisfaction()

    def _begin_satisfaction(self):
        """Zero it outright and stop asking for anything.

        TJ zeroes the drive rather than leaving it just under the floor,
        so the moment is a real reset and not a body that becomes hungry
        again three seconds later.
        """
        with self.shared_drive.lock:
            self.shared_drive.value = 0
        self._satisfied_at = time()
        self.log(
            f"{self.female.name} is satisfied by {self.male_name} after "
            f"{self._rounds} rounds - {self.SATISFACTION:.0f}s of it."
        )
        # Nothing more to say to him.
        self.sing.stop()

    def _run_satisfaction(self):
        if time() - self._satisfied_at >= self.SATISFACTION:
            self.stop()

    def setdown(self):
        # Must not raise: BaseThread runs this from a finally block, and
        # an error here would escape the thread's own error handling.
        try:
            self.sing.stop()
        except Exception as error:  # noqa: BLE001 - a silent body, not a crash
            self.log(f"Could not stop {self.female.name} singing: {error}")
        self.partner = None

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return self._with_scenarios({"sing": self.sing})

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        if self.partner is not None:
            leaf("partner", f"{self.male_name}, sharing the {self.drive_name} drive")
            leaf("singing back", "".join(str(bit) for bit in self.answer))
            leaf(
                "listening for",
                f"{self.male_name}'s R - "
                + "".join(str(bit) for bit in self.reinforcement_pattern),
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
