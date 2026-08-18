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
        if self._timelap is not None:
            children["timelap"] = leaves.value(
                _path, "timelap", timelap_to_string(seconds_elapsed=self._timelap)
            )
        for drive in self.hardware.drives:
            name = f"{drive.body.name}'s {drive.name} drive"
            children[drive.name] = drive
        return children
