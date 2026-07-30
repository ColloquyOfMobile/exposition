from colloquy.base import Base
from threading import Lock, Thread
from time import sleep


class VirtualDXL(Base):
    def __init__(self, owner, dxl_id):
        self._name = f"virtual_dxl_{dxl_id}"
        super().__init__(owner=owner)
        self._dict = {
            "drive mode": None,
            "temperature": 25,
            "position": 0,
            "goal position": 0,
            "operating mode": 0,
            "profile velocity": 0,
            "profile acceleration": 0,
            "torque enabled": 0,
        }
        # self._owner = owner
        self._dxl_id = dxl_id
        self._thread = None
        self._lock = Lock()
        self._goal_position = 0
        self._position = 0
        self._step = 10
        self._lim_min = None
        self._lim_max = None

    @property
    def name(self):
        return self._name

    @property
    def position(self):
        return self["position"]

    def get(self, label):
        return self._dict[label]

    def set(self, label, value):
        self._dict[label] = value
        if label == "goal position":
            if self._dict["torque enabled"] == 0:
                raise NotImplementedError

            if self._thread is not None:
                if self._thread.is_alive():
                    return

            self._thread = thread = Thread(
                target=self.run, name=self.path.as_posix(), daemon=True
            )
            thread.start()

    def run(self):

        while True:
            position = self._dict["position"]
            goal = self._dict["goal position"]

            lim_min = goal - 2 * self._step
            lim_max = goal + 2 * self._step

            if lim_min < position < lim_max:
                return

            if position < goal:
                self._dict["position"] += self._step
            else:
                self._dict["position"] -= self._step
            sleep(0.025)

    def _loop(self):
        lim_min, lim_max = self._lim_min, self._lim_max

        if self._lim_min < self._position < self._lim_max:
            self.stop_event.set()
            return

        if self._position < self.goal_position:
            self._position += self._step
            return

        self._position -= self._step
