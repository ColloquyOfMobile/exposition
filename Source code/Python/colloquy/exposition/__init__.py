from colloquy.base_thread import BaseThread

from .schedule import ExpositionSchedule


class Exposition(BaseThread):
    def __init__(self, owner):
        super().__init__(owner)
        self._drivers = self.owner.drivers

        self._thread = None

        # When the piece runs itself. Empty and switched off unless
        # somebody has written one, so by default this changes nothing
        # at all and the exposition is started by hand from this page.
        self._schedule = ExpositionSchedule(owner=self)

    @property
    def is_started(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()

    @property
    def name(self):
        return "exposition"

    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace

    @property
    def drivers(self):
        return self._drivers

    @property
    def colloquy(self):
        return self.owner.colloquy

    def open(self):
        self._is_opened = True

    def close(self):
        self._is_opened = False

    def setup(self):
        self.drivers.start(started_by=self)

    def loop(self):
        if not self.drivers.is_started:
            self.stop()

    def setdown(self):
        if self.thread_errors:
            self.drivers.shutdown()
        self.drivers.stop()

    @property
    def schedule(self):
        return self._schedule

    @property
    def snapshot_children(self):
        children = {self._schedule.name: self._schedule}
        return children
