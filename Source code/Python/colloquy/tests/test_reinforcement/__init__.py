# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_reinforcement/__init__.py

"""Reinforcement on its own, with nothing in front of it.

`test read pattern` and `test search` both stop at recognition: a female
decodes a male and the run writes it down. This one starts where they
stop. It stages the pair face to face, hands the partner straight to her
reinforcement, and runs **only** the exchange - no search, no blinking,
no light decode anywhere in it. So a run that fails here has failed in
the exchange, which is the whole reason to have it separate.

**What it does to the room.** The bar carries the chosen male to his
meeting point with the chosen female and both turn to their origins. She
sings his pattern; he lights his ring steady white and sings his `R`.
Two voices alternate at their own pitches - male1 at 160 Hz, female1 at
1 kHz and so on - for as long as the exchange lasts, which is a minute at
most. Nothing else on the piece moves.

**The hearing is emulated and this test is the place that says so
loudest.** `drivers/hearing/` computes what each body hears from what is
being sung, because the microphones are not in service. So the loop will
close whether or not a sound ever reaches a microphone, and a clean run
here is **not** evidence that the sound channel works.

Which is exactly why every round also **reads the real analysers** and
writes what they saw into the results file, beside what the emulated ears
did. That column is the bridge: today it is a measurement nobody is
acting on, and on the day the microphones are trusted it is the column
that replaces the emulation. If a body is singing and its own band never
rises here, the behaviour is right and the hardware is not.
"""
from datetime import datetime
from time import time

from colloquy.base_thread import BaseThread
from colloquy.drivers import audio
from colloquy.ui import leaves

# Long enough for a whole exchange and its ending, and short enough that
# a run nobody is watching stops by itself: five rounds at 4.35s, the
# satisfaction moment, and the patience timeout on top.
RUN_LIMIT = 90.0

# What the page keeps of the round-by-round history.
HISTORY = 40


class TestReinforcement(BaseThread):
    # What the room does while this runs.
    scenario_names = ("reinforcement-test",)

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._male_name = "male1"
        self._female_name = "female1"
        self._drive_name = "O"

        self._males = {male.name: male for male in self.drivers.males}
        self._females = {female.name: female for female in self.drivers.females}

        for name in self._males:
            self[f"male {name}"] = self._selector("_male_name", name)
        for name in self._females:
            self[f"female {name}"] = self._selector("_female_name", name)
        for drive in ("O", "P"):
            self[f"share the {drive} drive"] = self._selector("_drive_name", drive)

        # The drives are the tester's, as in `test search`: this run does
        # not set them. What it does do is refuse to start against a pair
        # that is already satisfied, since there would be nothing to take
        # down and the exchange would end on its first round.
        self["make them both hungry"] = self.make_them_hungry

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._rounds = []
        self._outcome = None
        self._staged = None
        self._last = (0, 0)
        self._noted = set()

    # --- what is being tested --------------------------------------------

    @property
    def name(self):
        return "test reinforcement"

    @property
    def male(self):
        return self._males[self._male_name]

    @property
    def female(self):
        return self._females[self._female_name]

    @property
    def drive_name(self):
        return self._drive_name

    @property
    def partner_for_her(self):
        return (self._male_name, self._drive_name)

    @property
    def partner_for_him(self):
        return (self._female_name, self._drive_name)

    def _selector(self, attribute, value):
        def choose(request=None):
            setattr(self, attribute, value)
            return f"{attribute.strip('_')} = {value}"

        return choose

    def _drive_of(self, body):
        drives = body.drives
        return drives.p_drive if self._drive_name == "P" else drives.o_drive

    def make_them_hungry(self, request=None):
        """Put the shared appetite at full on both, and the other at
        nothing, so the pair wants one thing and wants it badly.

        Offered rather than done: `test search` makes the same point, that
        a run which sets the drives is a run measuring its own settings.
        This is one press, and the page says what it did.
        """
        for body in (self.male, self.female):
            for drive in body.drives:
                wanted = drive.name.endswith(f"{self._drive_name} drive")
                with drive.lock:
                    drive.value = 100 if wanted else 0
        return (
            f"{self._male_name} and {self._female_name} both want "
            f"{self._drive_name} and nothing else"
        )

    # --- the run ----------------------------------------------------------

    def run(self):
        now = datetime.now()
        path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_"
            f"{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._rounds = []
        self._outcome = None
        self._staged = None
        self._last = (0, 0)
        self._noted = set()
        self._file.write(
            "seconds, event, her rounds, his rounds, her drive, his drive, "
            "singing, " + ", ".join(f"{hz} Hz" for hz in audio.BANDS_HZ) + "\n"
        )

        refusal = self._why_not_run()
        if refusal is not None:
            self._refuse(refusal)
            return

        male, female = self.male, self.female
        self.log(f"Staging {female.name} and {male.name} on the {self._drive_name} drive.")
        if not self._move_into_position():
            return

        # Straight into the exchange. No search, no blink, no decode: the
        # find is asserted rather than waited for, which is the whole
        # point of testing this half on its own.
        female.reinforcement.partner = self.partner_for_her
        male.reinforcement.partner = self.partner_for_him
        female.reinforcement.start(started_by=self)
        male.reinforcement.start(started_by=self)
        self._staged = (female, male)
        self._record("staged")

    def _why_not_run(self):
        """Why the exchange could not say anything, or None."""
        if self.male.name == self.female.name:
            return "a body cannot reinforce with itself"

        for body in (self.male, self.female):
            drive = self._drive_of(body)
            if drive.is_satisfied:
                return (
                    f"{body.name}'s {self._drive_name} drive is already "
                    f"satisfied ({drive.value}) - there is nothing to take "
                    "down. Press 'make them both hungry' first."
                )
        return None

    def _move_into_position(self):
        drivers = self.drivers
        male, female = self.male, self.female
        drivers.bar.set_male_in_front_of_female(male.name, female.name)
        male.turn_to_origin()
        female.turn_to_origin()

        arrived = drivers.wait_until_everything_is_still(
            dxls=(drivers.bar.dxl, male.dxl, female.dxl),
            should_stop=self._stop_event.is_set,
        )
        if self._stop_event.is_set():
            return False
        if not arrived:
            # Not raised, for `test read pattern`'s reason: an error
            # recorded here would block every later run until a restart.
            self.log("A body did not arrive - running anyway, and saying so.")
            self._record("did not arrive")
        return True

    def loop(self):
        if self._staged is None:
            return

        female, male = self._staged
        her, his = female.reinforcement, male.reinforcement
        counts = (her.rounds, his.rounds)

        if counts != self._last:
            self._last = counts
            self._record("round")

        # A set rather than a scan of the rows: the row history is
        # trimmed, so an event that scrolled off it would be recorded a
        # second time.
        for who, node in (("her", her), ("him", his)):
            if node.is_satisfied_moment and who not in self._noted:
                self._noted.add(who)
                self._record(f"{who} satisfied")

        if not her.is_started and not his.is_started:
            self._finish("both ended")
            self.stop()
            return

        if time() - self._start_time > RUN_LIMIT:
            self._finish(f"stopped at the {RUN_LIMIT:.0f}s limit")
            self.stop()

    # --- what gets written ------------------------------------------------

    def _record(self, event):
        """One row, and the real analysers read alongside the emulated ears.

        The sweep is the point of doing this on hardware at all: it is
        what a microphone actually saw while a body was singing, written
        next to a loop that did not need it.
        """
        female, male = self._staged if self._staged else (self.female, self.male)
        her, his = female.reinforcement, male.reinforcement
        elapsed = time() - (self._start_time or time())

        # Joined with a plus and never a comma: this is a column in a CSV,
        # and both of them singing at once is an ordinary moment rather
        # than a rare one. `test search` lost a column to exactly this
        # (see test_search_events.py).
        singing = " + ".join(
            body.name for body in (female, male) if body.sing.is_transmitting
        ) or "nobody"

        bands = self._read_bands(female)
        row = {
            "seconds": elapsed,
            "event": event,
            "her": her.rounds,
            "his": his.rounds,
            "her drive": self._drive_of(female).value,
            "his drive": self._drive_of(male).value,
            "singing": singing,
            "bands": bands,
        }
        self._rounds.append(row)
        del self._rounds[:-HISTORY]

        if self._file is not None:
            self._file.write(
                f"{elapsed:.2f}, {event}, {row['her']}, {row['his']}, "
                f"{row['her drive']}, {row['his drive']}, {singing}, "
                + ", ".join(f"{value}" for value in bands)
                + "\n"
            )
            self._file.flush()

    def _read_bands(self, listener):
        """What `listener`'s own analyser sees right now, or zeros.

        Swallowed rather than raised: a link that drops must not end a run
        that is measuring behaviour, and the zeros are visible in the file
        for what they are.
        """
        try:
            return list(self.drivers.audio.read_all()[listener.name])
        except Exception as error:  # noqa: BLE001 - see the docstring
            self.log(f"Could not read the analysers: {error}")
            return [0] * len(audio.BANDS_HZ)

    def _finish(self, how):
        female, male = self._staged
        her, his = female.reinforcement, male.reinforcement
        self._outcome = (
            f"{how} - {female.name} {her.rounds} rounds "
            f"(drive {self._drive_of(female).value}), "
            f"{male.name} {his.rounds} rounds "
            f"(drive {self._drive_of(male).value})"
        )
        self._record("finished")
        self.log(self._outcome)

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self.log(f"Refusing to run: {reason}")
        self.stop()

    def setdown(self):
        self._start_time = None
        staged, self._staged = self._staged, None
        if staged is not None:
            female, male = staged
            for node in (female.reinforcement, male.reinforcement):
                try:
                    node.stop()
                except Exception as error:  # noqa: BLE001
                    self.log(f"Could not stop {node}: {error}")
        # Whatever happened: nothing left sounding.
        try:
            self.colloquy.silence_speakers()
        finally:
            if self._file is not None:
                self._file.close()

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = dict(
            {f"male {name}": self[f"male {name}"] for name in self._males},
            **{f"female {name}": self[f"female {name}"] for name in self._females},
        )
        for drive in ("O", "P"):
            children[f"share the {drive} drive"] = self[f"share the {drive} drive"]
        children["make them both hungry"] = self.make_them_hungry
        children[self.male.drives.name + f" ({self._male_name})"] = self.male.drives
        children[self.female.drives.name + f" ({self._female_name})"] = (
            self.female.drives
        )
        children["her reinforcement"] = self.female.reinforcement
        children["his reinforcement"] = self.male.reinforcement
        children["hearing"] = self.drivers.hearing
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf(
            "pair",
            f"{self._female_name} and {self._male_name}, sharing "
            f"{self._drive_name}",
        )
        leaf(
            "voices",
            f"{self._female_name} {audio.VOICES[self._female_name]['hz']} Hz, "
            f"{self._male_name} {audio.VOICES[self._male_name]['hz']} Hz",
        )
        # The caveat this test exists inside. Said here as well as on the
        # hearing node, because this is the page somebody reads a green
        # result off.
        leaf(
            "ears",
            "EMULATED - the loop closes whether or not a microphone hears "
            "anything. The band columns in the file are the real reading."
            if self.drivers.hearing.is_emulated
            else "the microphones",
        )

        refusal = self._why_not_run()
        leaf("can run", "yes" if refusal is None else f"no - {refusal}")
        if self._outcome is not None:
            leaf("outcome", self._outcome)

        for row in self._rounds[-8:]:
            leaf(
                f"{row['seconds']:6.1f}s {row['event']}",
                f"her {row['her']} ({row['her drive']}), "
                f"his {row['his']} ({row['his drive']}) - singing: "
                f"{row['singing']}",
            )
        return states
