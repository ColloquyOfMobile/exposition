from colloquy.light_sensor import LightSensor
from time import sleep
from threading import Lock

class VirtualLightSensor(LightSensor):

    # def __init__(self, name, owner):
        # LightSensor.__init__(self, name=name, owner=owner)
        # self._lock = Lock()
        # self.arduino_manager = owner.arduino_manager
        # self._request_path = self._path.relative_to(self.hardware.path).as_posix()
    
    # @property
    # def emulated(self):
        # return self.owner.emulate_light_sensor

    # def beamed(self):
        # return self.hardware.interaction.male.is_beaming

    # def engaged(self):
        # raise NotImplementedError
        # return self.hardware.interaction.female.mirror.is_up

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
        if self.hardware.male1.body_neopixel.ring.state:
            return 500
            
        return 0
        # if self.emulated:
            # raise NotImplementedError
        # # path = f"{self._owner.name}/neopixel"
        # response = self.arduino_manager.send(self._request_path)
        # return int(response["value"])
        # raise NotImplementedError(f"{self=}, {response=}")