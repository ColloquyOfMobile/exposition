from time import time, sleep
import traceback
from colloquy.base_thread import BaseThread
from pathlib import Path
from threading import Thread, Event, Lock


class Exposition(BaseThread):
    def __init__(self, owner):
        super().__init__(owner)
        self._hardware = self.owner.hardware

        self._thread = None

    @property
    def is_started(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()

    @property
    def child_errors(self):
        return self._child_errors

    @property
    def name(self):
        return "exposition"

    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace

    @property
    def hardware(self):
        return self._hardware

    @property
    def colloquy(self):
        return self.owner.colloquy

    def open(self):
        self._is_opened = True

    def close(self):
        self._is_opened = False

    def setup(self):
        self.hardware.start(started_by=self)

    def loop(self):
        if not self.hardware.is_started:
            self.stop()

    def setdown(self):
        if self.thread_errors:
            self.hardware.shutdown()
        self.hardware.stop()

    @property
    def snapshot_children(self):
        children = {}
        return children
