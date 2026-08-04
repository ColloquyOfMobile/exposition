from colloquy.base_thread import BaseThread
from datetime import datetime
from time import time

# Test-only indicator colors (not part of the installation's own palette,
# see Neopixel.orange/.puce for the drive colors used on the body segments).
HEAD_COLOR_BY_MALE = {
    "male1": dict(red=0, green=0, blue=255, white=0),
    "male2": dict(red=255, green=0, blue=0, white=0),
}


class TestReadPattern(BaseThread):
    """Lets a tester pick which male sends his identity pattern and which
    female receives it, moves the bar so they face each other, blinks the
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
        def selector(request=None):
            if self.is_started:
                self.stop()
                self.join()
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
        self._last_log_time = 0.0
        self._match_count = 0
        self._mismatch_count = 0
        self._file.write(
            "seconds, sender, receiver, expected drive, detected male, detected drive, match\n"
        )

        self.hardware.bar.move_male_in_front_of_female_and_wait(
            self._male_name, self._female_name
        )
        self.male.drives.set_o_and_p_to_100()
        self.male.search.blink.start(started_by=self)
        self.female.search.read_pattern.start(started_by=self)

    def setdown(self):
        self._start_time = None
        self.male.search.blink.stop()
        self.female.search.read_pattern.stop()
        self.male.ring.off()
        self._clear_indicator()
        self._file.close()

    def loop(self):
        if not self.male.search.blink.is_started:
            self.stop()
            return

        now = time()
        if (now - self._last_log_time) < 1.0:
            return
        self._last_log_time = now

        expected_drive = self.male.drives.which_is_frustated()
        match = self.female.search.read_pattern.last_match

        detected_male, detected_drive, is_match = None, None, None
        if match is not None:
            detected_male, detected_drive = match
            is_match = (detected_male, detected_drive) == (
                self._male_name,
                expected_drive,
            )
            if is_match:
                self._match_count += 1
            else:
                self._mismatch_count += 1
            self._update_indicator(detected_male, detected_drive)

        timestamp = now - self._start_time
        self._file.write(
            f"{timestamp}, {self._male_name}, {self._female_name}, {expected_drive}, "
            f"{detected_male}, {detected_drive}, {is_match}\n"
        )

    def _update_indicator(self, detected_male, detected_drive):
        neopixels = self.female.neopixels

        head = neopixels.head
        head.color = HEAD_COLOR_BY_MALE.get(detected_male, head.color)
        head.on()

        body_o = neopixels.body_o
        if "O" in detected_drive:
            body_o.color = body_o.orange
            body_o.on()
        else:
            body_o.off()

        body_p = neopixels.body_p
        if "P" in detected_drive:
            body_p.color = body_p.puce
            body_p.on()
        else:
            body_p.off()

    def _clear_indicator(self):
        neopixels = self.female.neopixels
        neopixels.head.off()
        neopixels.body_o.off()
        neopixels.body_p.off()

    @property
    def snapshot_children(self):
        children = {}
        for male in self._males.values():
            children[male.drives.name] = male.drives
            children[male.search.blink.name] = male.search.blink
        for female in self._females.values():
            children[female.search.read_pattern.name] = female.search.read_pattern
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        # Plain commands, injected directly (not via snapshot_children) the
        # same way BaseThread injects "start"/"stop": snapshot_children
        # entries get .snapshot_as_child() called on them when this node is
        # opened, which only real Base objects support - a bare function
        # would crash that walk.
        for key, selector in {**self._male_selectors, **self._female_selectors}.items():
            states[key] = selector

        states["sender"] = {
            "path": path + ("sender",),
            "name": "sender",
            "value": self._male_name,
        }
        states["receiver"] = {
            "path": path + ("receiver",),
            "name": "receiver",
            "value": self._female_name,
        }
        if self._start_time is not None:
            states["matches"] = {
                "path": path + ("matches",),
                "name": "matches",
                "value": f"{self._match_count} correct / {self._mismatch_count} incorrect",
            }
        return states
