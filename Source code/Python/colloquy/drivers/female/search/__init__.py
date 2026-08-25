from colloquy.base_thread import BaseThread
from .read_pattern import ReadPattern
from colloquy.ui import leaves


class Search(BaseThread):
    # Her sway and her reading, together - the pattern-reading she
    # starts is described inside it rather than in its own file, since
    # nothing about it is visible in the room on its own.
    scenario_names = ("female-looking",)

    """A female looking for a male worth answering.

    Two things at once: she sways between her min and max position, and
    her ReadPattern child decodes whatever her light sensor sees. The
    search ends the moment she recognises a male who wants something she
    wants - that pair is left in `partner` for Female.loop() to pick up
    and hand to reinforcement.

    Ending on a find is the point. Before this, search ran forever: she
    decoded patterns continuously and nothing ever became of it, so a
    match had no consequence anywhere in the installation.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._read_pattern = None
        self._partner = None

        self[self.read_pattern.name] = self.read_pattern

    @property
    def name(self):
        return "search"

    @property
    def female(self):
        return self.owner

    @property
    def read_pattern(self):
        if self._read_pattern is None:
            self._read_pattern = ReadPattern(owner=self)
        return self._read_pattern

    @property
    def partner(self):
        """(male name, drive) if this search ended on a find, else None."""
        return self._partner

    def take_partner(self):
        """Read the find and forget it, so one find is acted on once."""
        partner, self._partner = self._partner, None
        return partner

    def start(self, started_by=None):
        # Forget the previous find here rather than in setup(): setup()
        # runs on the new thread, a tick or more after start() returns, and
        # anything looking at `partner` in between would read the answer
        # from the *previous* search. That window is long enough to matter
        # - whoever starts a search usually has bodies to move first - and
        # it read as an instant find the moment a second run began.
        self._partner = None
        super().start(started_by=started_by)

    def setup(self):
        self.read_pattern.start(started_by=self)

    def _decoded_before_this_search_began(self):
        """Is the answer she is holding left over from the last search?

        `read_pattern` is one long-lived object restarted alongside each
        search, and its setup() - which forgets the previous run's answer
        - runs on its own thread a tick or two after start() returns. So
        `loop()` can get here first and read the match that *ended the
        last search*, act on it, and find the same male again instantly
        without having looked at anything.

        Seen as a doubled find in `test_search`: the same partner logged
        twice, a tenth of a second apart. Harmless today only because
        reinforcement is a placeholder - it is still a find made on no
        evidence.

        Both times are None until a search has actually been started and
        a decode has actually happened, which is the case in unit tests
        that call loop() directly; nothing is stale until there are two
        times to compare.
        """
        started_at = self._started_at
        match_time = self.read_pattern.last_match_time
        if started_at is None or match_time is None:
            return False
        return match_time < started_at

    def loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_position()

        match = self.read_pattern.last_match
        if match is None:
            return

        if self._decoded_before_this_search_began():
            return

        male, offered = match
        shared = self._shared_drive(male=male, offered=offered)
        if shared is None:
            # Somebody she can hear but doesn't want: he is asking for a
            # drive she is not short of. She keeps looking, exactly as in
            # TJ's Logic_fem.ino, where a match outside her own drive
            # state falls through every branch and nothing happens.
            return

        self._partner = (male, shared)
        self.log(f"{self.female.name} found {male}, sharing the {shared} drive.")
        self.stop()

    def _shared_drive(self, male, offered):
        """Which single drive this pair would share, or None if she isn't
        interested in what he is asking for.

        She only answers a male asking for something she is short of
        herself (Logic_fem.ino switches on her own drive state and ignores
        every match outside it). The result is one drive, not a set: the
        reinforcement that follows draws down one appetite.
        """
        wanted = set(self.female.drives.which_is_frustated())
        shared = wanted & set(offered)

        if not shared:
            return None
        if len(shared) == 1:
            return shared.pop()

        # She wants both and he offers both. TJ picks one, and a different
        # one per male (Logic_fem.ino case 4: male I gives O, male II
        # gives P), so two males courting equally hungry females don't
        # always end up sharing the same drive.
        return "O" if male == "male1" else "P"

    def setdown(self):
        pass

    @property
    def snapshot_children(self):
        children = {}
        children.update(
            {
                self.read_pattern.name: self.read_pattern,
            }
        )
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._partner is not None:
            male, drive = self._partner
            states["found"] = leaves.value(
                path,
                "found",
                f"{male}, sharing the {drive} drive",
            )
        return states
