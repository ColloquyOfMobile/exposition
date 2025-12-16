from colloquy.base_thread import BaseThread
from time import time, sleep

class Search(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)

    def _loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_position()

        self.owner.sensor.detect_male()

    @property
    def name(self):
        return "search"

    # def _run_unsafe(self):
        # stop_event = self._stop_event.is_set
        # while not stop_event():
            # self._loop()
            # self.leave_some_time_to_other_threads()

    # def add_html(self):
        # doc, tag, text = self.html_doc.tagtext()

        # with tag("h4"):
            # text(f"Search:")

        # if self.hardware.is_open:
            # if not self._is_started:
                # self._add_html_start()
            # else:
                # self._add_html_stop()

    # def _add_html_start(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("form", method="post"):
            # with tag("button", name="action", value=f"{self.path.as_posix()}/start"):
                # text(f"Start.")
        # self.hardware.actions[f"{self.path.as_posix()}/start"] = self.start

    # def _add_html_stop(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("form", method="post"):
            # with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                # text(f"Stop.")
            # self.hardware.actions[f"{self.path.as_posix()}/stop"] = self.stop