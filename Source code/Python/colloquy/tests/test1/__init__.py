from pathlib import Path
from colloquy.base_thread import BaseThread

from threading import Event
import traceback
from threading import Thread, Lock
from time import sleep


class Test1(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def name(self):
        return "test1"

    def setdown(self):
        for neopixel in self.hardware.neopixels:
            neopixel.off()

    def _run_unsafe(self):
        stop_event = self._stop_event.is_set
        hardware = self.hardware
        neopixels = hardware.neopixels

        if stop_event():
            return

        with hardware.arduino:
            for neopixel in neopixels:
                neopixel.off()

            for i in range(10):
                for neopixel in neopixels:
                    neopixel.set_test_default()
                    neopixel.on()

                for e in range(10):
                    sleep(0.1)
                    if stop_event():
                        return

                for neopixel in neopixels:
                    neopixel.off()

                for e in range(5):
                    sleep(0.1)
                    if stop_event():
                        return
