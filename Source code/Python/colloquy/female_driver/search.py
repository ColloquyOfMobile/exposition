from colloquy.thread_driver import ThreadDriver
from time import time, sleep

class Search(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"search")

    def __enter__(self):
        print(f"The {self.owner.name} is searching...")
        self.stop_event.clear()

    def _loop(self):
        if not self.owner.is_moving:
            print(f"{self.owner.name} toggle position...")
            self.owner.toggle_position()

        # if self.owner.interaction_event.is_set():
            # raise NotImplementedError()

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()

        with tag("h4"):
            text(f"Search:")

        if self.colloquy.is_open:
            if not self._is_started:
                self._add_html_start()
            else:
                self._add_html_stop()

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/start"):
                text(f"Start.")
        self.colloquy.actions[f"{self.path.as_posix()}/start"] = self.start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                text(f"Stop.")
            self.colloquy.actions[f"{self.path.as_posix()}/stop"] = self.stop