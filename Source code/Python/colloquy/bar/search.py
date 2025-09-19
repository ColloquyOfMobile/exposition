from colloquy.thread_element import ThreadElement
from time import time, sleep

class Search(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"search")

    def __enter__(self):
        self.stop_event.clear()

    def run(self, **kwargs):
        with self:
            self._setup(**kwargs)
            while not self.stop_event.is_set():
                if self.owner.stop_event.is_set():
                    break
                self._loop()
                self._sleep_min()

    def _loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_max_min_position()

        if self.owner.interaction_event.is_set():
            self.stop()

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()

        with tag("h4"):
            text(f"Search:")

        if self.hardware.is_open:
            with tag("form", method="post"):
                if not self._is_started:
                    self._add_html_start()
                else:
                    self._add_html_stop()

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/start"):
                text(f"Start.")
        self.hardware.actions[f"{self.path.as_posix()}/start"] = self.start
        self.blink.add_html()

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
            text(f"Stop.")
        self.hardware.actions[f"{self.path.as_posix()}/stop"] = self.stop