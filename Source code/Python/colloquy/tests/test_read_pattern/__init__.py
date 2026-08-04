from colloquy.base_thread import BaseThread
from datetime import datetime
from time import time


class TestReadPattern(BaseThread):
    """Moves male1 (and the bar) in front of female1, blinks male1's identity
    pattern, and checks whether female1's read_pattern decodes it correctly.

    Exposes male1's drives, blink, and female1's read_pattern as children so
    a tester can switch the drive state (O/P/both/neither) live from the web
    UI and watch the decoded match track it - on real hardware or in
    simulation (the virtual f1 light sensor reacts to male1's ring state).
    """

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._male = self.hardware.male1
        self._female = self.hardware.female1
        self._blink = self._male.search.blink
        self._read_pattern = self._female.search.read_pattern
        self._drives = self._male.drives

        self[self._drives.name] = self._drives
        self[self._blink.name] = self._blink
        self[self._read_pattern.name] = self._read_pattern

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
            "seconds, expected male, expected drive, detected male, detected drive, match\n"
        )

        self.hardware.bar.move_male1_in_front_of_female1_and_wait()
        self._drives.set_o_and_p_to_100()
        self._blink.start(started_by=self)
        self._read_pattern.start(started_by=self)

    def setdown(self):
        self._start_time = None
        self._blink.stop()
        self._read_pattern.stop()
        self._male.ring.off()
        self._file.close()

    def loop(self):
        if not self._blink.is_started:
            self.stop()
            return

        now = time()
        if (now - self._last_log_time) < 1.0:
            return
        self._last_log_time = now

        expected_male = self._male.name
        expected_drive = self._drives.which_is_frustated()
        match = self._read_pattern.last_match

        detected_male, detected_drive, is_match = None, None, None
        if match is not None:
            detected_male, detected_drive = match
            is_match = (detected_male, detected_drive) == (
                expected_male,
                expected_drive,
            )
            if is_match:
                self._match_count += 1
            else:
                self._mismatch_count += 1

        timestamp = now - self._start_time
        self._file.write(
            f"{timestamp}, {expected_male}, {expected_drive}, "
            f"{detected_male}, {detected_drive}, {is_match}\n"
        )

    @property
    def snapshot_children(self):
        children = {}
        children[self._drives.name] = self._drives
        children[self._blink.name] = self._blink
        children[self._read_pattern.name] = self._read_pattern
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._start_time is not None:
            states["matches"] = {
                "path": path + ("matches",),
                "name": "matches",
                "value": f"{self._match_count} correct / {self._mismatch_count} incorrect",
            }
        return states
