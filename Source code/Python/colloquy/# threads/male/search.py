from colloquy.thread_element import ThreadElement
from time import time, sleep

class Search(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"search")
        self._blink = Blink(owner=self)

    def __enter__(self):
        self.stop_event.clear()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    @property
    def blink(self):
        return self._blink

    @property
    def body_neopixel(self):
        return self.owner.body_neopixel

    @property
    def microphone(self):
        return self.owner.microphone

    def _loop(self):
        with self.hardware.lock:
            if not self.hardware.bar.search.is_started:
                if self.hardware.interaction is None:
                    self.hardware.bar.search.start()
                else:
                    if not self.hardware.interaction.is_started:
                        self.hardware.bar.search.start()

        if not self.owner.is_moving:
            self.owner.toggle_position()

        if self.owner.microphone.is_notified:
           self.stop()
           self.owner.conversation.start()

    def _setup(self):
        self.blink.start()

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()

        with tag("h4"):
            text(f"Search:")

        if self.hardware.is_open:
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
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                text(f"Stop.")
            self.hardware.actions[f"{self.path.as_posix()}/stop"] = self.stop

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                text(f"Stop.")
            self.hardware.actions[f"{self.path.as_posix()}/stop"] = self.stop_from_ui

    def stop_from_ui(self):
        self.stop()
        self.thread.join()
        self.hardware.bar.search.stop()



class Blink(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"blink")
        self._timestamp = None
        self._blink_step = 0.5

    def __enter__(self):
        self.stop_event.clear()
        self._timestamp = 0
        self.ring.configure(
            red = 0,
            green = 0,
            blue = 0,
            white = 255,
            brightness = 255,)

    def _loop(self):
        if (time() - self._timestamp) > self._blink_step:
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

        # if self.hardware.is_open:
        if not self._is_started:
            self._add_html_start()
        else:
            self._add_html_stop()

        self.drives.add_html()

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):

            with tag("button", name="action", value=f"{self.path.as_posix()}/start"):
                text(f"Start.")
        self.hardware.actions[f"{self.path.as_posix()}/start"] = self.start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.path.as_posix()}/stop"):
                text(f"Stop.")
            self.hardware.actions[f"{self.path.as_posix()}/stop"] = self.stop