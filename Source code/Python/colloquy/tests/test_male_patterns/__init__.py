from colloquy.base_thread import BaseThread

from time import time


class TestMalePatterns(BaseThread):
    # Two rings blinking side by side, out of step with each other,
    # and how to read that as expected rather than as a fault.
    scenario_names = ("male-patterns-test",)
    def __init__(self, owner):
        super().__init__(owner=owner)

        self._blink_handlers = []
        self._drives = []
        for male in self.hardware.males:
            blink_handler = male.search.blink
            self[blink_handler.name] = blink_handler
            self._blink_handlers.append(blink_handler)

            drives = male.drives
            self[drives.name] = drives
            self._drives.append(drives)

        self._start_time = None
        self._timelap = None

    @property
    def name(self):
        return "test male pattern"

    def setup(self):
        self._start_time = time()

        for blink_handler in self._blink_handlers:
            blink_handler.start(started_by=self)

    def setdown(self):
        for blink_handler in self._blink_handlers:
            blink_handler.stop()

    def loop(self):
        if any(not blink_handler.is_started for blink_handler in self._blink_handlers):
            self.stop()
        return

    @property
    def snapshot_children(self):
        children = {}
        for drives in self._drives:
            children[drives.name] = drives

        for blink_handler in self._blink_handlers:
            children[blink_handler.name] = blink_handler
        return self._with_scenarios(children)
