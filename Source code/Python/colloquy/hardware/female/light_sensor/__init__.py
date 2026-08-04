from colloquy.base_thread import BaseThread
from time import sleep
from threading import Lock
from pathlib import Path
from .html import HTML

class LightSensor(BaseThread):
    def __init__(self, name, owner):
        self._name = name
        super().__init__(owner=owner)
        self._lock = Lock()
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request

    @property
    def female(self):
        return self.owner

    @property
    def arduino(self):
        return self.owner.arduino

    @property
    def html(self):
        return self._html

    @property
    def is_simulated(self):
        if super().is_simulated:
            return True
        return self.params["emulate light sensor"]

    @property
    def threashold(self):
        return self.params["photosensor_threashold"]

    @property
    def params(self):
        return self.owner.params

    @property
    def name(self):
        return self._name

    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/light sensor")

    def read_as_bool(self):
        return self.read() > self.threashold

    def read(self):
        # if self.is_emulated:
        # raise NotImplementedError

        with self.arduino:
            response = self.arduino.send(self.arduino_path)

        # rint(response)
        return int(response)

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["read"] = self.read
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self.read(),
        }
        return states
