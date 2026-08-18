from pathlib import Path
from colloquy.base_thread import BaseThread
from colloquy.utils import timelap_to_string

from threading import Event
import traceback
from threading import Thread, Lock
from time import sleep, time
from colloquy.ui import leaves


class TestDriveLightValues(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)

        for drive in self.hardware.drives:
            self[drive.name] = drive

        self._start_time = None
        self._timelap = None

    @property
    def name(self):
        return "test drives light values"

    def setup(self):
        self._start_time = time()

        for drive in self.hardware.drives:
            drive.start(started_by=self)

        for neopixel in self.hardware.neopixels:
            neopixel.on()

    def setdown(self):
        for drive in self.hardware.drives:
            drive.stop()
        for neopixel in self.hardware.neopixels:
            neopixel.off()

    def loop(self):
        self._timelap = time() - self._start_time
        if all(drive.value == 100 for drive in self.hardware.drives):
            self.stop()
        return

    @property
    def snapshot_children(self):
        children = {}
        for drive in self.hardware.drives:
            children[drive.name] = drive
        return children

    def _snapshot_if_opened(self, path):
        # The elapsed time was built in snapshot_children off a name that
        # does not exist there, so opening this node raised NameError once
        # the test had run - and a leaf could not have lived there anyway,
        # since children are walked with snapshot_as_child().
        states = super()._snapshot_if_opened(path)
        if self._timelap is not None:
            states["timelap"] = leaves.value(
                path, "timelap", timelap_to_string(seconds_elapsed=self._timelap)
            )
        return states
