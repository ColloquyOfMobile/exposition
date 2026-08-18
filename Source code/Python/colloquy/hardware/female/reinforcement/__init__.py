from colloquy.base_thread import BaseThread
from colloquy.ui import leaves


class Reinforcement(BaseThread):
    """What a female does once she has found a male: not implemented yet.

    Started by Female.loop() when her search ends on a find, with the pair
    it found in `partner`. This is the half of the interaction that brings
    an appetite back down, and the reason nothing in the installation
    currently comes of a match.

    For reference, what it has to do (TJ's Logic_fem.ino /
    logic35_systems, see SCENARIOS.md section 8):
      - hold the body still, and answer the male by transmitting the
        pattern she decoded back to him as *sound*;
      - while she keeps hearing his reinforcement pattern in reply,
        subtract from the shared drive - a fixed amount per body in the
        original (FEMALE_reinforcement_decrement, 1200/600/1200 for
        females 1/2/3);
      - when that drive falls below the interested floor, zero it and
        enter a satisfaction moment, during which neither drive climbs;
      - give up and go back to searching if the reply never comes.

    Deliberately raising rather than quietly doing nothing: a placeholder
    that silently succeeded would leave the female looking like she had
    been satisfied when nothing happened at all.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)
        self.partner = None

    @property
    def name(self):
        return "reinforcement"

    @property
    def female(self):
        return self.owner

    def setup(self):
        raise NotImplementedError(
            f"{self.female.name} found {self.partner}, but reinforcement is "
            "not implemented yet: nothing brings a drive back down."
        )

    def loop(self):
        raise NotImplementedError(f"User defined! ({self=})")

    def setdown(self):
        # Must not raise: BaseThread runs this from a finally block, so an
        # error here would escape the thread's own error handling and hide
        # the one setup() reports.
        pass

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self.partner is not None:
            male, drive = self.partner
            states["partner"] = leaves.value(
                path,
                "partner",
                f"{male}, sharing the {drive} drive",
            )
        return states
