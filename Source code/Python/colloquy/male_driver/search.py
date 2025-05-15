from colloquy.thread_driver import ThreadDriver
from time import time, sleep

class Search(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"search")
        self._blink = Blink(owner=self)

    def __enter__(self):
        print(f"The {self.owner.name} is searching...")
        self.stop_event.clear()
        self.blink.start()
        if not self.colloquy.bar.search.is_started:
            if self.colloquy.bar.interaction_event.is_set():
                print(f"The bar is already interacting")
            print(f"Tell the bar to start searching.")
        else:
            print(f"Bar is already searching.")

    @property
    def blink(self):
        return self._blink

    @property
    def body_neopixel(self):
        return self.owner.body_neopixel

    def _loop(self):
        if not self.colloquy.bar.search.is_started:
            if not self.colloquy.bar.interaction_event.is_set():
                self.colloquy.bar.search.start()

        if not self.owner.is_moving:
            print(f"{self.owner.name} toggle position...")
            self.owner.toggle_position()

        if self.owner.listen_for_notification():
            raise NotImplementedError()

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

        self.blink.add_html()

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                text(f"Stop.")
            self.colloquy.actions[f"{self.path.as_posix()}/stop"] = self.stop

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                text(f"Stop.")
            self.colloquy.actions[f"{self.path.as_posix()}/stop"] = self.stop_from_ui

    def stop_from_ui(self):
        self.stop()
        self.thread.join()
        self.colloquy.bar.search.stop()



class Blink(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"blink")
        self._timestamp = None
        self._blink_step = 0.5

    def __enter__(self):
        print(f"Start blinking...")
        self.stop_event.clear()
        self._timestamp = 0
        self.ring.configure(
            red = 0,
            green = 0,
            blue = 0,
            white = 255,
            brightness = 255,)

    def _loop(self):
        if (time() - self._timestamp) > 0.5:
            light_pattern = self.light_patterns[self.drives.state]
            value = light_pattern.popleft()
            light_pattern.append(value)
            self.ring.set(value)
            self._timestamp = time()

    @property
    def light_patterns(self):
        return self.owner.body_neopixel.light_patterns

    @property
    def drives(self):
        return self.owner.body_neopixel.drives

    @property
    def ring(self):
        return self.owner.body_neopixel.ring

    @property
    def body_neopixel(self):
        return self.owner.body_neopixel

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()

        with tag("h4"):
            text(f"Blink:")

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