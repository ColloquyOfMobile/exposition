from colloquy.base_thread import BaseThread
from time import sleep
from threading import Lock

class LightSensor(BaseThread):

    def __init__(self, name, owner):
        self._name = name
        super().__init__(owner=owner)
        self._lock = Lock()

    @property
    def emulated(self):
        return self.owner.emulate_light_sensor

    @property
    def name(self):
        return self._name

    def detect_male(self):
        with self.hardware.lock:
            female = self.owner

            if not female.near_origin():
                return

            interaction = self.hardware.bar.nearby(female)
            if interaction is None:
                return

            male = interaction.male
            if not male.near_origin():
                return

            common_drives = set(female.drives.state).intersection(male.drives.state)
            if common_drives:
                interaction.target_drive = tuple(common_drives)
                interaction.start()

    def read(self):
        if self.emulated:
            raise NotImplementedError
        # path = f"{self._owner.name}/neopixel"
        response = self.arduino_manager.send(self._request_path)
        return int(response["value"])