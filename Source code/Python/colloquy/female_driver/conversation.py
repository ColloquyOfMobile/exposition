from colloquy.thread_driver import ThreadDriver
from time import time, sleep

class Conversation(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"conversation")
        self._timeout_start = None
        self.timeout = 4 # seconds

    def __enter__(self):
        print(f"The {self.owner.name} is engaging...")
        self.stop_event.clear()
        # self.owner.interaction_event.set()
        self.owner.turn_to_origin_position()
        self.owner.mirror.start()
        self.owner.notify_male()
        self._timeout_start = time()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        if self.owner.mirror.is_started:
            self.owner.mirror.start()
        return ThreadDriver.__exit__(self, exc_type, exc_value, traceback_obj)

    def _loop(self):
        if self.listen_confirmation():
            self._timeout_start = time()

        if time() - self._timeout_start > self.timeout:
            print(f"The male doesn't respond...")
            self.stop_event.set()
            self.owner.mirror.stop()
            self.colloquy.bar.nearby_interaction.stop()
            self.owner.search.start()

    def listen_confirmation(self):
        return False

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