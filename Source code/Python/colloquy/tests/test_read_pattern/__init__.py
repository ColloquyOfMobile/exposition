from colloquy.base_thread import BaseThread
from datetime import datetime
from time import time
from colloquy.ui import leaves

# Test-only indicator colors (not part of the installation's own palette,
# see Neopixel.orange/.puce for the drive colors used on the body segments).
HEAD_COLOR_BY_MALE = {
    "male1": dict(red=0, green=0, blue=255, white=0),
    "male2": dict(red=255, green=0, blue=0, white=0),
}

# Full brightness: this is a readout to be seen across a room while testing,
# not a body indicating how hungry it is.
INDICATOR_BRIGHTNESS = 100


class TestReadPattern(BaseThread):
    # What this test does to the room once it is started, so that what
    # the bodies are seen doing can be told from what has gone wrong.
    scenario_names = ("pattern-reading-test",)

    """Lets a tester pick which male sends his identity pattern and which
    female receives it, brings the pair face to face (bar to their meeting
    point, both bodies turned to their own origin), blinks the
    sender and starts the receiver's read_pattern, and gives a visual
    readout on the receiver's own neopixels - test-only, the installation
    itself doesn't do this: head blue for male1 / red for male2, body_o lit
    orange when "O" was decoded and body_p lit puce when "P" was, mirroring
    how the sending male's own o/p drive level indicators work.

    Exposes every male's drives and every body's blink/read_pattern as
    children so a tester can force a drive state (or fiddle with an
    unrelated body) from the web UI while a run is going.
    """

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._male_name = "male1"
        self._female_name = "female1"
        self._males = {male.name: male for male in self.hardware.males}
        self._females = {female.name: female for female in self.hardware.females}

        self._male_selectors = {
            f"send from {name}": self._make_selector("_male_name", name)
            for name in self._males
        }
        self._female_selectors = {
            f"receive with {name}": self._make_selector("_female_name", name)
            for name in self._females
        }
        for key, selector in {**self._male_selectors, **self._female_selectors}.items():
            self[key] = selector

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._last_log_time = 0.0
        self._match_count = 0
        self._mismatch_count = 0
        self._blank_count = 0
        self._row_count = 0

        # The pair the run is currently set up around: bodies positioned,
        # blink and read_pattern running. Kept separate from the selected
        # pair above so loop() can notice the two have drifted apart and
        # re-stage - and so tearing the old pair down targets the bodies
        # that were actually started, not the ones just selected.
        self._staged_male = None
        self._staged_female = None

    @property
    def name(self):
        return "test read pattern"

    @property
    def male(self):
        return self._males[self._male_name]

    @property
    def female(self):
        return self._females[self._female_name]

    def _make_selector(self, attribute, value):
        """Pick a sender or a receiver, before or during a run.

        All this does is record the choice. It used to stop the whole test,
        which made switching pair mid-run impossible - you had to stop,
        select, start again, and lost the run. Now the test's own loop()
        notices that the selection no longer matches what is staged and
        re-stages: old blink/read_pattern stopped, bodies moved to the new
        pair, new blink/read_pattern started.

        Deliberately doing nothing here beyond the assignment: this runs in
        the web server's request thread, and the staging it triggers takes
        seconds of servo movement. Doing that work here would block the
        single-threaded server - including the page that reports what is
        happening - for the whole move.
        """

        def selector(request=None):
            setattr(self, attribute, value)

        return selector

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
        self._file.write(
            "seconds, sender, receiver, expected drive, detected male, detected drive, match\n"
        )
        self._stage_selected_pair()

    def _stage_selected_pair(self):
        """Set the run up around whichever pair is currently selected: stop
        whatever the previous pair was doing, move the new one face to face,
        and start the new sender blinking and the new receiver reading.

        Used both for the initial setup() and for every mid-run switch, so
        the two can't drift apart.
        """
        self._teardown_staged_pair()

        male, female = self.male, self.female
        self._staged_male, self._staged_female = male, female
        self.log(f"Staging {male.name} -> {female.name}.")

        if not self._move_into_position():
            # Stopped while the bodies were still moving: don't light the
            # sender up on the way out. setdown() clears what was staged.
            return

        male.drives.set_o_and_p_to_100()
        male.search.blink.start(started_by=self)
        female.search.read_pattern.start(started_by=self)

        # Counters describe one pair, so a switch starts a fresh count. The
        # results file keeps every row, sender and receiver included in each,
        # so nothing measured before the switch is lost.
        self._last_log_time = 0.0
        self._match_count = 0
        self._mismatch_count = 0
        self._blank_count = 0
        self._row_count = 0

    def _teardown_staged_pair(self):
        """Stop and darken the pair a run was staged around, if any.

        Joins rather than just stopping: blink turns the male's ring off from
        its own setdown(), so returning before that has run would leave the
        previous sender lit while the next one starts blinking - two lit
        males, and a receiver with no way to tell which she is reading.
        """
        male, female = self._staged_male, self._staged_female
        self._staged_male = self._staged_female = None
        if male is None:
            return

        blink = male.search.blink
        read_pattern = female.search.read_pattern
        blink.stop()
        read_pattern.stop()
        blink.join()
        read_pattern.join()

        male.ring.off()
        self._clear_indicator(female)

    def _move_into_position(self):
        """Bring the pair face to face before anything is measured: the bar
        carries the male to his meeting point with this female, and both
        bodies turn back to their own origin so they actually point at each
        other. Positioning the bar alone isn't enough - a body left facing
        elsewhere (by an earlier test, by hand, or by its own search sway)
        stays that way for the whole run, and the female then reads nothing
        at all for reasons that have nothing to do with the pattern.

        All three are commanded first and waited on together rather than one
        after another: they move concurrently anyway, and the wait is scoped
        to these three servos so it isn't defeated by some other body swaying
        elsewhere on the bus.

        Returns False if the run was stopped while the bodies were still
        moving, so the caller knows not to go on and start anything.
        """
        hardware = self.hardware
        male, female = self.male, self.female
        hardware.bar.set_male_in_front_of_female(male.name, female.name)
        male.turn_to_origin()
        female.turn_to_origin()

        dxls = (hardware.bar.dxl, male.dxl, female.dxl)
        arrived = hardware.wait_until_everything_is_still(
            dxls=dxls, should_stop=self._stop_event.is_set
        )
        if self._stop_event.is_set():
            return False
        if not arrived:
            # Deliberately not raised: an error here would be recorded on
            # this node and, with no way to clear it, would block every
            # later run until the process restarts. A run against a body
            # that never arrived is worth flagging, not worth bricking the
            # test with.
            self.log(
                f"WARNING: {male.name}, {female.name} and the bar "
                "were not all in position in time - they may not be facing "
                "each other, so this run's results are not trustworthy."
            )
        return True

    def setdown(self):
        self._start_time = None
        self._teardown_staged_pair()
        self._file.close()

    def loop(self):
        male, female = self._staged_male, self._staged_female

        if (male, female) != (self.male, self.female):
            # Somebody picked a different sender or receiver from the web UI
            # while the run was going. Move to them and carry on - this is
            # the point of the selectors, and stopping the run instead is
            # what they used to do.
            self._stage_selected_pair()
            return

        if not male.search.blink.is_started:
            # The sender's blink died or was stopped by hand: there is
            # nothing left to read, so the run is over.
            self.stop()
            return

        now = time()
        if (now - self._last_log_time) < 1.0:
            return
        self._last_log_time = now

        expected_drive = male.drives.which_is_frustated()
        # Only counts as something she sees now: read_pattern expires a
        # detection once it stops being refreshed, so a second in which she
        # saw nothing is recorded as nothing rather than repeating the last
        # answer. Each row is therefore one second of "what was true then",
        # and the three counters below add up to the seconds logged.
        match = female.search.read_pattern.last_match

        detected_male, detected_drive, is_match = None, None, None
        self._row_count += 1
        if match is None:
            self._blank_count += 1
            self._clear_indicator(female)
        else:
            detected_male, detected_drive = match
            is_match = (detected_male, detected_drive) == (
                male.name,
                expected_drive,
            )
            if is_match:
                self._match_count += 1
            else:
                self._mismatch_count += 1
            self._update_indicator(female, detected_male, detected_drive)

        timestamp = now - self._start_time
        self._file.write(
            f"{timestamp}, {male.name}, {female.name}, {expected_drive}, "
            f"{detected_male}, {detected_drive}, {is_match}\n"
        )

    def _update_indicator(self, female, detected_male, detected_drive):
        neopixels = female.neopixels

        head = neopixels.head
        # Brightness has to be set explicitly here. A female's segments start
        # at brightness 0 and are only ever raised by her own Drives thread,
        # as it maps her appetites onto them - and this test doesn't run that
        # thread. Without this the readout still "lights up", but every
        # channel is scaled by 0, so the arduino is sent plain black and
        # nothing is visible on the body: exactly what the real-hardware log
        # showed (f1/head, f1/bodyO, f1/bodyP all r0 g0 b0 w0, once a second).
        head.brightness.value = INDICATOR_BRIGHTNESS
        head.color = HEAD_COLOR_BY_MALE.get(detected_male, head.color)
        head.on()

        body_o = neopixels.body_o
        if "O" in detected_drive:
            body_o.brightness.value = INDICATOR_BRIGHTNESS
            body_o.color = body_o.orange
            body_o.on()
        else:
            body_o.off()

        body_p = neopixels.body_p
        if "P" in detected_drive:
            body_p.brightness.value = INDICATOR_BRIGHTNESS
            body_p.color = body_p.puce
            body_p.on()
        else:
            body_p.off()

    def _clear_indicator(self, female):
        neopixels = female.neopixels
        neopixels.head.off()
        neopixels.body_o.off()
        neopixels.body_p.off()

    def _selection_value(self, selected, staged):
        """What the web UI shows for "sender"/"receiver".

        A selection made mid-run only takes effect on the test's next tick,
        and the move itself takes seconds, so during that window the page
        would otherwise claim a body is in use before it has even started
        moving. Say so instead."""
        if staged is None or staged.name == selected:
            return selected
        return f"{selected} (moving into position, still on {staged.name})"

    @property
    def snapshot_children(self):
        children = {}
        for male in self._males.values():
            children[male.drives.name] = male.drives
            children[male.search.blink.name] = male.search.blink
        for female in self._females.values():
            children[female.search.read_pattern.name] = female.search.read_pattern
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        # Plain commands, injected directly (not via snapshot_children) the
        # same way BaseThread injects "start"/"stop": snapshot_children
        # entries get .snapshot_as_child() called on them when this node is
        # opened, which only real Base objects support - a bare function
        # would crash that walk.
        for key, selector in {**self._male_selectors, **self._female_selectors}.items():
            states[key] = selector

        states["sender"] = leaves.value(
            path,
            "sender",
            self._selection_value(self._male_name, self._staged_male),
        )
        states["receiver"] = leaves.value(
            path,
            "receiver",
            self._selection_value(self._female_name, self._staged_female),
        )
        if self._start_time is not None:
            states["matches"] = leaves.value(
                path,
                "matches",
                f"{self._match_count} correct / {self._mismatch_count} wrong / "
                    f"{self._blank_count} nothing seen, out of {self._row_count} seconds",
            )
        return states
