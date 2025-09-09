from colloquy.thread_element import ThreadElement
from time import sleep
from threading import Lock

class LightSensor(ThreadElement):

    def __init__(self, name, owner):
        ThreadElement.__init__(self, name=name, owner=owner)
        self._lock = Lock()
        self.arduino_manager = owner.arduino_manager
        self._request_path = self._path.relative_to(self.colloquy.path).as_posix()
    
    @property
    def emulated(self):
        return self.owner.emulate_light_sensor

    def beamed(self):
        return self.colloquy.interaction.male.is_beaming

    def engaged(self):
        raise NotImplementedError
        return self.colloquy.interaction.female.mirror.is_up

    def detect_male(self):
        with self.colloquy.lock:
            female = self.owner

            if not female.near_origin():
                return

            interaction = self.colloquy.bar.nearby(female)
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
        raise NotImplementedError(f"{self=}, {response=}")
        
        