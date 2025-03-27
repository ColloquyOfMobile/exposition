# from .shared_driver import SharedDriver
# from .neopixel_driver import NeopixelDriver
# from .speaker_driver import SpeakerDriver
# from pathlib import Path
# from threading import Event
from threading import Timer
from threading import Lock
# import traceback

class DrivesHandler:

    def __init__(self):
        self.o_drive = 0
        self.p_drive = 0
        self._timer = None
        self._update_interval = 1

        self._step_o = 1
        self._step_p = 2

        self._max = 255
        self._min = 0

        self._satisfied = 20
        self._frustrated = 235

        self._lock = Lock()

    def __getitem__(self, key):
        assert key in (None, "O", "P", "O or P"), f"{key=}"
        with self._lock:
            if key == "O":
                return self.o_drive
            if key == "P":
                return self.p_drive
            return max(self.p_drive, self.o_drive)

    @property
    def value(self):
        state = self.state
        return state, self[state]


    @property
    def state(self):
        with self._lock:
            o_satisfied = self.o_drive < self._satisfied
            p_satisfied = self.p_drive < self._satisfied
            o_frustated = self.o_drive > self._frustrated
            p_frustated = self.p_drive > self._frustrated

            if o_satisfied and p_satisfied:
                return None
            if o_frustated and p_frustated:
                return "O or P"
            if self.o_drive > self.p_drive:
                assert not o_satisfied
                return "O"
            if self.p_drive > self.o_drive:
                assert not p_satisfied
                return "P"
            if self.p_drive == self.o_drive:
                return "O or P"

            raise ValueError(f"Drive Error, {self.o_drive=}, {self.p_drive=}")

    def run(self):
        """This function repeat every "self._update_interval"."""
        self.o_drive += self._step_o
        self.p_drive += self._step_p
        if self.o_drive > self._max:
            self.o_drive = self._max
        if self.p_drive > self._max:
            self.p_drive = self._max

        self._timer = Timer(self._update_interval, self.run)
        self._timer.start()

    def start(self):
        self._timer = Timer(self._update_interval, self.run)
        self._timer.start()

    def stop(self):
        self._timer.cancel()