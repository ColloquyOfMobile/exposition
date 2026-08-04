from colloquy.base_thread import BaseThread
from datetime import datetime
from time import time


class TestSensors(BaseThread):
    """Continuously polls every light sensor on the rig (each female's
    single sensor, each male's 4 sensors - a/b/c/d) and logs their values,
    so a human can cover/uncover a specific sensor and watch it react
    live, both in the CSV log and in this node's own "live: ..." readout
    while it's running.

    Also exposes every real sensor object as a child (safe - real Base
    objects, not bare callables) so any one of them can be inspected or
    read individually, independent of the automated polling loop.
    """

    POLL_INTERVAL = 0.5  # seconds between polls of every sensor

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._sensors = {}
        for female in self.hardware.females:
            self._sensors[f"{female.name} light sensor"] = female.light_sensor
        for male in self.hardware.males:
            for letter, sensor in male.light_sensors.items():
                self._sensors[f"{male.name} light sensor {letter}"] = sensor

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._last_poll_time = 0.0
        self._latest_values = {}

    @property
    def name(self):
        return "test sensors"

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
        self._last_poll_time = 0.0
        self._latest_values = {}
        self._file.write("seconds, " + ", ".join(self._sensors.keys()) + "\n")

    def setdown(self):
        self._start_time = None

    def loop(self):
        now = time()
        if (now - self._last_poll_time) < self.POLL_INTERVAL:
            return
        self._last_poll_time = now

        values = {label: sensor.read() for label, sensor in self._sensors.items()}
        self._latest_values = values

        timestamp = now - self._start_time
        row = ", ".join(str(values[label]) for label in self._sensors)
        self._file.write(f"{timestamp}, {row}\n")

    @property
    def snapshot_children(self):
        return dict(self._sensors)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        for label, value in self._latest_values.items():
            key = f"live: {label}"
            states[key] = {
                "path": path + (key,),
                "name": key,
                "value": value,
            }
        return states
