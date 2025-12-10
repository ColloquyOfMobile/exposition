# from colloquy.body import Body
# from colloquy.drives import Drives
# from colloquy.thread_element import ThreadElement
# from colloquy.light_sensor import LightSensor
# from colloquy.microphone import Microphone
# from colloquy.neopixel import Neopixel
from .neopixels import Head, BodyO, BodyP, Feet
from .drives import Drives
# from .female_drives import FemaleDrives
# from .mirror import Mirror
# from .search import Search
# from .conversation import Conversation
# from threading import Lock
# from time import sleep
from pathlib import Path
from colloquy.base import Base

class Female(Base):

    # _classes = {
        # "sensor": LightSensor
    # }

    def __init__(self, owner, id_number):
        self._name = f"female{id_number}"
        self._id_number = id_number
        super().__init__(owner=owner)
        self._arduino = owner.arduino

        self._drives = Drives(owner=self)


        self._neopixels = []
        # self.neopixel = FemaleNeopixel(owner=self, name="neopixel")
        self._head = Head(owner=self)
        self._body_o= BodyO(owner=self)
        self._body_p = BodyP(owner=self)
        self._feet = Feet(owner=self)

        self[self.head.name] = self.head
        self[self.body_o.name] = self.body_o
        self[self.body_p.name] = self.body_p
        self[self.feet.name] = self.feet

        self._threaded_elements = {
            *self._drives,
        }

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
    def is_started(self):
        return any(element.is_started for element in self._threaded_elements)

    @property
    def drives(self):
        return self._drives

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def id_number(self):
        return self._id_number

    @property
    def female(self):
        return self

    @property
    def html(self):
        return self.owner.html

    @property
    def arduino(self):
        return self._arduino

    @property
    def head(self):
        return self._head

    @property
    def body_o(self):
        return self._body_o

    @property
    def body_p(self):
        return self._body_p

    @property
    def feet(self):
        return self._feet

    @property
    def name(self):
        return self._name

    @property
    def neopixels(self):
        neopixels = [
            self.head,
            self.body_o,
            self.body_p,
            self.feet,
        ]
        return neopixels

    @property
    def is_started(self):
        return any(element.is_started for element in self._threaded_elements)

    def shutdown(self):
        with self.arduino:
            for element in self._threaded_elements:
                element.shutdown()
            for neopixel in self.neopixels:
                neopixel.off()

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