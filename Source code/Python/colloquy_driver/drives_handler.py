from threading import Timer
from threading import Lock

class DrivesHandler:

    def __init__(self):
        self._started = False
        self.o_drive = 0
        self.p_drive = 0
        self._timer = None
        self._update_interval = 1

        self._step_o = 1
        self._step_p = 2

        self._max = 255
        self._min = 0

        self._satisfied = 2
        self._frustrated = 235

        self._lock = Lock()

        self._orange = dict(red=255, green=165, blue=0, white=0)
        self._white = dict(red=0, green=0, blue=0, white=255)
        self._colors = {
            ("O",): self._white,
            ("P",): self._orange,
            None: self._white,
            ("O", "P",): self._white,
        }

    def __getitem__(self, key):
        # assert key in (None, "O", "P", "O or P"), f"{key=}"
        for_max = list()
        with self._lock:
            if key is None:
                return  max(self.o_drive, self.p_drive)

            if "O" in key:
                for_max.append(self.o_drive)
            if "P" in key:
                for_max.append(self.p_drive)
            return max(for_max)

    @property
    def color(self):
        return self._colors[self.state]

    @property
    def value(self):
        state = self.state
        return state, self[state], self._colors[state]


    @property
    def state(self):
        # raise NotImplementedError(f"Update to return a tuple for the states")
        with self._lock:
            o_satisfied = self.o_drive < self._satisfied
            p_satisfied = self.p_drive < self._satisfied
            o_frustated = self.o_drive > self._frustrated
            p_frustated = self.p_drive > self._frustrated

            if o_satisfied and p_satisfied:
                return None
            if o_frustated and p_frustated:
                return ("O", "P")
            if self.o_drive > self.p_drive:
                assert not o_satisfied
                return ("O", )
            if self.p_drive > self.o_drive:
                assert not p_satisfied
                return ("P", )
            if self.p_drive == self.o_drive:
                return ("O", "P")

            raise ValueError(f"Drive Error, {self.o_drive=}, {self.p_drive=}")

    def run(self):
        """This function repeat every "self._update_interval"."""
        if not self._started:
            return
        self.o_drive += self._step_o
        self.p_drive += self._step_p
        if self.o_drive > self._max:
            self.o_drive = self._max
        if self.p_drive > self._max:
            self.p_drive = self._max

        self._timer = Timer(self._update_interval, self.run)
        self._timer.start()

    def start(self):
        self._started = True
        self._timer = Timer(self._update_interval, self.run)
        self._timer.start()

    def stop(self):
        self._timer.cancel()
        self._started = False

    def satisfy(self):
        self.o_drive =  self._satisfied
        self.p_drive =  self._satisfied