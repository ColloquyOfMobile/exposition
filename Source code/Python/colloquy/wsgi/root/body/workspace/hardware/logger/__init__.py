from time import sleep, time
from pathlib import Path
from threading import Timer
from .base import Base
from datetime import datetime

class Logger(Base):     

    def __init__(self, owner):
        Base.__init__(self, owner)
        # self._owner = owner
        self._folder = self._log_folder / self.owner.name
        self._path = self._folder.parent / f"{owner.name}.log"

        assert self._path not in self._instances, f"{self._path=}"
        self._instances[self._path] = self   

    def _init_file(self):
        if not self._path.exists():
            self._path.touch()

    def mkdir(self):
        self._folder.mkdir()