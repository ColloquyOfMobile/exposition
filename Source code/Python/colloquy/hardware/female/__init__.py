from .neopixels import Neopixels # Head, BodyO, BodyP, Feet
from .drives import Drives
from pathlib import Path
from colloquy.base_thread import BaseThread
from .search import Search
from .html import HTML
from .test import Test

class Female(BaseThread):

    def __init__(self, owner, id_number):
        self._name = f"female{id_number}"
        self._id_number = id_number
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self._arduino = owner.arduino

        self._drives = Drives(owner=self)
        self._search = Search(owner=self)

        self._neopixels = Neopixels(owner=self)
        self._test = Test(owner=self)

        self[self.html.name] = self.html.handle_request
        self[self.neopixels.name] = self.neopixels
        self[self.drives.name] = self.drives
        self[self.test.name] = self.test
        self[self.search.name] = self.search

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def test(self):
        return self._test

    @property
    def search(self):
        return self._search

    @property
    def drives(self):
        return self._drives

    @property
    def id_number(self):
        return self._id_number

    @property
    def female(self):
        return self

    @property
    def html(self):
        return self._html

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return self._name

    @property
    def neopixels(self):
        return self._neopixels

    def loop(self):
        pass

    def setup(self):
        self.drives.start(started_by=self)

    def setdown(self):
        self.drives.stop()
        self.search.stop()

    # def stop(self):
        # with self.arduino:
            # self.drives.stop()
            # self.search.stop()
            # for neopixel in self.neopixels:
                # neopixel.off()

    # @property
    # def emulate_light_sensor(self):
        # if self._emulate_light_sensor is None:
            # return self.owner.emulate_light_sensors
        # return self._emulate_light_sensor

    # @emulate_light_sensor.setter
    # def emulate_light_sensor(self, value):
        # self._emulate_light_sensor = value

    # @property
    # def is_notifing(self):
        # return self._is_notifing

    # @property
    # def conversation(self):
        # return self._conversation

    # def listen_for_confirmation(self):
        # return True

    # def _loop(self):
        # pass

    # def stop(self):

        # # if self._is_started:
            # # self.drives.stop()
        # for segment in self.segments:
            # segment.off()
        # Body.stop(self)

    # def open(self):
        # Body.open(self)
        # self.head.open()
        # self.body_neopixel.open()
        # self.feet.open()
        # self.mirror.open()

    # def notify_male(self):
        # self._is_notifing = True
        # self.speaker.notify()
        # self._is_notifing = False

    # def _add_html_start(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("form", method="post"):
            # with tag("button", name="action", value=f"{self.name}/start"):
                # text(f"Start.")
            # self.hardware.actions[f"{self.name}/start"] = self.start

        # self._search.add_html()