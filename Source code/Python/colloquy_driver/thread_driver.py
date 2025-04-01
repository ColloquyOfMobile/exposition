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
        sleep(0.05)