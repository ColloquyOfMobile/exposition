from datetime import datetime
from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

# Drive values that produce each drive state, via which_is_frustated()
# (hardware/drive/__init__.py): both below the satisfied floor means she is
# short of nothing; both above the frustrated floor means both; otherwise
# the larger one wins.
DRIVE_VALUES = {
    tuple(): (0, 0),
    ("O",): (100, 50),
    ("P",): (50, 100),
    ("O", "P"): (100, 100),
}

DRIVE_LABELS = {
    tuple(): "nothing",
    ("O",): "O",
    ("P",): "P",
    ("O", "P"): "both",
}


class TestFemaleSearch(BaseThread):
    # The one test whose passing result can be nothing happening at
    # all, which is worth knowing before watching it.
    scenario_names = ("female-search-test",)
    """Watch one female run a whole search on the real bodies, and see
    whether it ends the way it should.

    The behaviour under test is Search.loop()'s decision (hardware/female/
    search): she ends her search on the first male asking for a drive she
    is short of, and ignores one asking for anything else. Set what he
    asks for and what she wants from the control page, press start, and
    watch: "found" for a pair she should accept, and nothing at all for a
    pair she should ignore.

    What makes this safe to run on the installation:

    - It refuses to start while the installation itself is running. With
      Exposition going, every body drives its own threads and the bar
      wanders off on its own, which would both fight this test and move
      things you didn't ask to move. Stop the installation first.
    - Only the chosen pair and the bar ever move, and only once, at the
      start. After that the female sways within her own travel, which is
      the movement she makes anyway.
    - It always ends by itself: on a find, on an error in any thread it
      started, or when the time limit runs out.
    - Stop takes effect immediately, including in the middle of the
      opening move (the position wait is interruptible), rather than
      finishing a bar crossing first.
    - It puts back what it changed: the drive values it forced on both
      bodies are restored, the ring is turned off, and the search is
      stopped.
    """

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._male_name = "male1"
        self._female_name = "female1"
        self._male_asks = ("O", "P")
        self._she_wants = ("O", "P")
        self._duration = 180

        self._males = {male.name: male for male in self.hardware.males}
        self._females = {female.name: female for female in self.hardware.females}

        self._commands = {}
        for name in self._males:
            self._commands[f"send from {name}"] = self._setter("_male_name", name)
        for name in self._females:
            self._commands[f"search with {name}"] = self._setter("_female_name", name)
        for drives, label in DRIVE_LABELS.items():
            self._commands[f"he asks for {label}"] = self._setter("_male_asks", drives)
            self._commands[f"she wants {label}"] = self._setter("_she_wants", drives)
        for seconds in (60, 180, 600):
            self._commands[f"stop after {seconds}s"] = self._setter(
                "_duration", seconds
            )
        for key, command in self._commands.items():
            self[key] = command

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._last_log_time = 0.0
        self._outcome = None
        self._restore = []

    @property
    def name(self):
        return "test female search"

    @property
    def male(self):
        return self._males[self._male_name]

    @property
    def female(self):
        return self._females[self._female_name]

    @property
    def should_find(self):
        """What the search is expected to do with this pairing."""
        return bool(set(self._she_wants) & set(self._male_asks))

    def _setter(self, attribute, value):
        def setter(request=None):
            if self.is_started:
                # Unlike test_read_pattern, which re-stages mid-run, this
                # one is a single measured attempt: changing what is being
                # measured halfway through would make the result
                # unreadable. Set it up first, then start.
                self.log(f"Ignoring {attribute}={value}: stop the run first.")
                return
            setattr(self, attribute, value)

        return setter

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self.log(f"Refusing to run: {reason}")
        self.stop()

    def run(self):
        now = datetime.now()
        file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = file_path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._last_log_time = 0.0
        self._outcome = None
        self._restore = []
        self._file.write(
            "seconds, sender, receiver, he asks, she wants, should find, "
            "searching, decoded, found\n"
        )

        if self._busy_bodies():
            self._refuse(
                f"{', '.join(self._busy_bodies())} already running - stop the "
                "installation (and any other test) before running this one, or "
                "they will move the bodies while it measures them"
            )
            return

        self._force_drives()
        if not self._move_into_position():
            return

        self.male.search.blink.start(started_by=self)
        self.female.search.start(started_by=self)

    def _busy_bodies(self):
        """Anything already driving the bodies this test needs."""
        busy = []
        for node in (self.hardware, self.male, self.female, self.hardware.bar):
            if node.is_started:
                busy.append(node.name)
        return busy

    def _force_drives(self):
        """Put both bodies in the drive state this run is about, and
        remember what to put back."""
        for body, wanted in ((self.male, self._male_asks), (self.female, self._she_wants)):
            o_value, p_value = DRIVE_VALUES[tuple(wanted)]
            drives = body.drives
            self._restore.append(
                (drives, drives.o_drive.value, drives.p_drive.value)
            )
            drives.o_drive.commit(o_value)
            drives.p_drive.commit(p_value)
            self.log(f"{body.name} set to {DRIVE_LABELS[tuple(wanted)]}.")

    def _restore_drives(self):
        for drives, o_value, p_value in self._restore:
            drives.o_drive.commit(o_value)
            drives.p_drive.commit(p_value)
        self._restore = []

    def _move_into_position(self):
        """Bar to their meeting point, both bodies facing forward. Returns
        False if the run was stopped while they were still moving."""
        hardware = self.hardware
        hardware.bar.set_male_in_front_of_female(self._male_name, self._female_name)
        self.male.turn_to_origin()
        self.female.turn_to_origin()

        dxls = (hardware.bar.dxl, self.male.dxl, self.female.dxl)
        arrived = hardware.wait_until_everything_is_still(
            dxls=dxls, should_stop=self._stop_event.is_set
        )
        if self._stop_event.is_set():
            return False
        if not arrived:
            self._refuse(
                "the bar or a body did not reach its position in time - check "
                "for something jammed before trying again"
            )
            return False
        return True

    def loop(self):
        search = self.female.search
        elapsed = time() - self._start_time

        for node in (search, self.male.search.blink):
            if node.thread_errors:
                self._outcome = f"error in {node.name}"
                self.stop()
                return

        partner = search.partner
        if partner is not None:
            male, drive = partner
            self._outcome = f"found {male}, sharing the {drive} drive"
            self._log_row(elapsed, search, partner)
            self.stop()
            return

        if not search.is_started:
            self._outcome = "the search stopped without finding anyone"
            self.stop()
            return

        if elapsed > self._duration:
            self._outcome = f"no one found within {self._duration}s"
            self.stop()
            return

        if (time() - self._last_log_time) < 1.0:
            return
        self._last_log_time = time()
        self._log_row(elapsed, search, partner)

    def _log_row(self, elapsed, search, partner):
        decoded = search.read_pattern.last_match
        self._file.write(
            f"{elapsed:.1f}, {self._male_name}, {self._female_name}, "
            f"{DRIVE_LABELS[tuple(self._male_asks)]}, "
            f"{DRIVE_LABELS[tuple(self._she_wants)]}, {self.should_find}, "
            f"{search.is_started}, {decoded}, {partner}\n"
        )

    def setdown(self):
        self.female.search.stop()
        self.male.search.blink.stop()
        self.male.ring.off()
        self._restore_drives()
        self._start_time = None
        if self._outcome:
            self.log(f"Outcome: {self._outcome}")
            self._file.write(f"# {self._outcome}\n")
        self._file.close()

    @property
    def snapshot_children(self):
        children = {}
        for male in self._males.values():
            children[male.search.blink.name] = male.search.blink
        for female in self._females.values():
            # Every female's search is called just "search", so keying by
            # its own name would leave only the last one reachable here.
            children[f"{female.name}'s search"] = female.search
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        for key, command in self._commands.items():
            states[key] = command

        leaf = leaves.into(states, path)

        leaf("sender", self._male_name)
        leaf("receiver", self._female_name)
        leaf("he asks for", DRIVE_LABELS[tuple(self._male_asks)])
        leaf("she wants", DRIVE_LABELS[tuple(self._she_wants)])
        leaf(
            "expected",
            "she should find him" if self.should_find else "she should ignore him",
        )
        leaf("time limit", f"{self._duration}s")
        if self._start_time is not None:
            leaf("running for", f"{time() - self._start_time:.0f}s")
        if self._outcome:
            leaf("outcome", self._outcome)
        return states
