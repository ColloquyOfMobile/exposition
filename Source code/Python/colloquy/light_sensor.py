from colloquy.thread_element import ThreadElement
from time import sleep
from threading import Lock

class LightSensor(ThreadElement):

    def __init__(self, name, owner):
        ThreadElement.__init__(self, name=name, owner=owner)
        self._lock = Lock()

    def beamed(self):
        return self.colloquy.interaction.male.is_beaming

    def engaged(self):
        raise NotImplementedError
        return self.colloquy.interaction.female.mirror.is_up

    def detect_male(self):
        with self._lock:
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