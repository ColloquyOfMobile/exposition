from colloquy.body import Body
from colloquy.neopixel import Neopixel
from colloquy.drives import Drives
from colloquy.microphone import Microphone
from .body_neopixels import BodyNeopixels
from .search import Search
from .conversation import Conversation
from .light_sensors import UpSensor, DownSensor
from time import time, sleep
from threading import Event, Thread
import traceback


class MaleDriver(Body):

    def __init__(self, **kwargs):
        Body.__init__(
            self,
            **kwargs,
            )
        self.body_neopixel = BodyNeopixels(owner=self)
        self.up_ring = Neopixel(owner=self, name="up_ring")
        self.up_sensor = UpSensor(owner=self, name="up sensor")
        self.down_sensor = DownSensor(owner=self, name="down sensor")

        self.light_sensors = {
            "O":self.up_sensor,
            "P": self.down_sensor,
            }

        self.microphone = Microphone(owner=self)

        self._search = Search(owner=self)
        self._conversation = Conversation(owner=self)

        self.drives = Drives(owner=self, neopixel=self.body_neopixel.drive)

    def open(self):
        Body.open(self)
        self.body_neopixel.off()

    def __enter__(self):
        assert self.dxl_origin is not None, "Calibrate colloquy."
        self.stop_event.clear()
        self.body_neopixel.start()
        self.drives.start()
        self.body_neopixel.drive.on()

    # @property
    # def target_drive(self):
        # assert not self.drives.is_started
        # return self.drives.state

    # @male_target_drive.setter
    # def male_target_drive(self, value):
        # self._male_target_drive = value

    @property
    def beam(self):
        return self.body_neopixel.beam

    @property
    def conversation(self):
        return self._conversation

    @property
    def is_beaming(self):
        return self.body_neopixel.beam.is_started

    def _loop(self):
        pass

    # def _interact(self):
        # self.body_neopixel.stop()
        # self.body_neopixel.thread.join()
        # self.body_neopixel.ring.on()

        # iterations = 2
        # self.turn_to_origin_position()
        # while self.interaction_event.is_set():
            # if self.stop_event.is_set():
                # break
            # self._sleep_min()

        # self.interaction_event.clear()

        # self.turn_on_speaker()
        # sleep(0.5)
        # self.turn_off_speaker()
        # print(f"{self.name} finished interaction.")
        # self.body_neopixel.start()

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(f"{self.name.title()}:")

        if self.colloquy.is_open:
                if not self._is_started:
                    self._add_html_start()
                else:
                    self._add_html_stop()

        self._add_html_params()

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.name}/start"):
                text(f"Start.")
            self.colloquy.actions[f"{self.name}/start"] = self.start

        self._search.add_html()
        # self.body_neopixel.add_html()

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