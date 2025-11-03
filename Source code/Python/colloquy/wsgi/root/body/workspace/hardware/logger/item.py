from time import sleep, time
from pathlib import Path
from threading import Timer
from datetime import datetime
from .base import Base

class Item(Base):        

    def __init__(self, owner):
        Base.__init__(self, owner)
        # self._owner = owner
        self._folder = self.parent.folder / owner.name
        self._path = self.folder.parent / f"{owner.name}.log"

        assert self._path not in self._instances, f"{self._path=}"
        self._instances[self._path] = self

    def _init_file(self):
        if not self._path.exists():
            if not self._owner.owner.log.folder.is_dir():
                self._owner.owner.log.mkdir()
            self._path.touch()

    @property
    def parent(self):
        return self.owner.owner.log

    def mkdir(self):
        if not self.parent.folder.is_dir():
            self.parent.mkdir()
        self._folder.mkdir()