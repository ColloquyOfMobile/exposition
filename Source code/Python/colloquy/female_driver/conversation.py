from colloquy.thread_driver import ThreadDriver
from time import time, sleep

class Conversation(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"conversation")
        self._watch_out_for_beam = WatchOutForBeam(owner=self)

    def __enter__(self):
        print(f"The {self.owner.name} is engaging...")
        self.stop_event.clear()
        self.owner.turn_to_origin_position()
        self.owner.notify_male()
        self._watch_out_for_beam.start()

    def _loop(self):
        pass
        # if self.watch_out_for_beam():
            # self._timeout_start = time()

        # if time() - self._timeout_start > self.timeout:
            # print(f"The male doesn't respond...")
            # self.stop_event.set()
            # self.owner.mirror.stop()
            # self.colloquy.bar.nearby_interaction.stop()
            # self.owner.search.start()

    # def add_html(self):
        # doc, tag, text = self.html_doc.tagtext()

        # with tag("h4"):
            # text(f"Search:")

        # if self.colloquy.is_open:
            # if not self._is_started:
                # self._add_html_start()
            # else:
                # self._add_html_stop()

    # def _add_html_start(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("form", method="post"):
            # with tag("button", name="action", value=f"{self.path.as_posix()}/start"):
                # text(f"Start.")
        # self.colloquy.actions[f"{self.path.as_posix()}/start"] = self.start

    # def _add_html_stop(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("form", method="post"):
            # with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                # text(f"Stop.")
            # self.colloquy.actions[f"{self.path.as_posix()}/stop"] = self.stop


class WatchOutForBeam(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"watch out for beam")
        self._timeout_start = None
        self.timeout = 4 # seconds

    def __enter__(self):
        print(f"The {self.owner.owner.name} is waiting for beam...")
        self.stop_event.clear()
        self._timeout_start = time()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        if self.owner.owner.mirror.is_started:
            self.owner.owner.mirror.stop()
        return ThreadDriver.__exit__(self, exc_type, exc_value, traceback_obj)

    def enter(self):
        print(f"The {self.owner.owner.name} is waiting for beam...")
        self.stop_event.clear()
        self._timeout_start = time()

    def _loop(self):
        if self.sense():
            self.stop_event.set()
            self.owner.owner.mirror.start()

        if time() - self._timeout_start > self.timeout:
            print(f"The male doesn't respond...")
            self.stop_event.set()
            self.colloquy.bar.nearby_interaction.stop()
            self.owner.owner.search.start()

    def sense(self):
        return self.colloquy.nearby_interaction.male.is_beaming