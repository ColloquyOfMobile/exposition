from time import sleep, time
from pathlib import Path
from .logger import Logger

class ThreadDriver:

    def __init__(self, name):
        self._name = name
        self._log = Logger(owner=self)

    @property
    def name(self):
        return self._name

    @property
    def log(self):
        return self._log

    def sleep_min(self):
        sleep(0.01)

    def run(self, **kwargs):
        print(f"Running {self.name}...")
        try:
            self._run_setup()
            self._run_loop()
            self._run_setdown()
        except Exception:
            msg = traceback.format_exc()
            self.log(msg)
            self.colloquy.stop_event.set()
            self._run_setdown()
            raise

    def _run_setup(self):
        raise NotImplementedError("""Possible implementation:
self.stop_event.clear()
self.drives.start()
self.turn_on_neopixel()""")

    def _run_loop(self):
        raise NotImplementedError("""Possible implementation:
while not self.stop_event.is_set():

    if not self.is_moving:
        self.toggle_position()

    if self.interaction_event.is_set():
        self._interact()
    self.sleep_min()""")

    def _run_setdown(self):
        raise NotImplementedError("""Possible implementation:
self.drives.stop()
self.turn_off_neopixel()""")