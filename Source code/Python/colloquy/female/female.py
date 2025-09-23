from colloquy.body import Body
from colloquy.drives import Drives
from colloquy.thread_element import ThreadElement
from colloquy.light_sensor import LightSensor
from colloquy.microphone import Microphone
from .female_neopixel import FemaleNeopixel
from .mirror import Mirror
from .search import Search
from .conversation import Conversation
from threading import Lock
from time import sleep

class FemaleDriver(Body):
    
    _classes = {
        "sensor": LightSensor
    }

    def __init__(self, owner, **kwargs):
        # self._lock = Lock()
        Body.__init__(
            self,
            owner,
            **kwargs,
            )
        self.neopixel = FemaleNeopixel(owner=self, name="neopixel")
        self.drives = Drives(owner=self, neopixel=self.neopixel)
        self.sensor = self._classes["sensor"](owner=self, name="sensor")
        self.microphone = Microphone(owner=self)

        self._search = Search(owner=self)
        self._conversation = Conversation(owner=self)
        self._is_notifing = False
        self._emulate_light_sensor = None

        dxl_manager = kwargs["dynamixel manager"]
        dxl_id = kwargs["dynamixel id"]
        origin = kwargs["origin"]


        mirror_kwargs = kwargs.get("mirror")
        self.mirror = None
        if mirror_kwargs:
            mirror_kwargs["dynamixel manager"] = dxl_manager
            self.mirror = Mirror(owner=self, **mirror_kwargs)
        self._target_drive = None
        self._male_target_drive = None

    def __enter__(self):
        assert self.dxl_origin is not None, "Calibrate hardware."
        self.stop_event.clear()
        self.drives.start()
    
    @property
    def emulate_light_sensor(self):
        if self._emulate_light_sensor is None:
            return self.owner.emulate_light_sensors
        return self._emulate_light_sensor
    
    @emulate_light_sensor.setter
    def emulate_light_sensor(self, value):
        self._emulate_light_sensor = value

    @property
    def is_notifing(self):
        return self._is_notifing

    @property
    def conversation(self):
        return self._conversation

    def listen_for_confirmation(self):
        return True

    def _loop(self):
        pass

    def stop(self):
                
        if self._is_started:            
            # self.drives.stop()
            self.neopixel.off()
        Body.stop(self)

    def open(self):
        Body.open(self)
        self.neopixel.open()
        self.mirror.open()

    def notify_male(self):
        self._is_notifing = True
        self.speaker.notify()
        self._is_notifing = False

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.name}/start"):
                text(f"Start.")
            self.hardware.actions[f"{self.name}/start"] = self.start

        self._search.add_html()