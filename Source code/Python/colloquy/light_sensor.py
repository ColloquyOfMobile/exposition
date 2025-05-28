from colloquy.thread_element import ThreadElement
from time import sleep

class LightSensor(ThreadElement):

    def beamed(self):
        return self.colloquy.interaction.male.is_beaming

    def engaged(self):
        raise NotImplementedError
        return self.colloquy.interaction.female.mirror.is_up