from colloquy.base_thread import BaseThread
from time import sleep
from threading import Lock
from pathlib import Path
from .html import HTML
from .emulate_read_pattern import EmulateReadPattern

class LightSensor(BaseThread):

    def __init__(self, name, owner):
        self._name = name
        super().__init__(owner=owner)
        self._lock = Lock()
        self._read_pattern = None
        self._html = HTML(owner=self) 
        self[self.html.name] = self.html.handle_request  
        self[self.read_pattern.name] = self.read_pattern
    
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
    def params(self):
        return self.owner.params

    @property
    def name(self):
        return self._name

    @property
    def read_pattern(self):
        if self._read_pattern is None:
            if self.is_simulated:
                self._read_pattern = EmulateReadPattern(owner=self)
            else:
                self._read_pattern = ReadPattern(owner=self)
        return self._read_pattern

    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/light sensor")

    # def detect_male(self):
        # with self.hardware.lock:
            # female = self.owner

            # if not female.near_origin():
                # return

            # interaction = self.hardware.bar.nearby(female)
            # if interaction is None:
                # return

            # male = interaction.male
            # if not male.near_origin():
                # return

            # common_drives = set(female.drives.state).intersection(male.drives.state)
            # if common_drives:
                # interaction.target_drive = tuple(common_drives)
                # interaction.start()

    def read(self):
        # if self.is_emulated:
            # raise NotImplementedError
        
        with self.arduino:
            response = self.arduino.send(self.arduino_path)
        return int(response)