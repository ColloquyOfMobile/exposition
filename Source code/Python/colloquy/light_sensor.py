from colloquy.thread_element import ThreadElement

class LightSensor(ThreadElement):

    def beamed(self):
        return self.colloquy.interaction.male.is_beaming
        raise NotImplementedError
        return True

    def engaged(self):
        raise NotImplementedError
        return self.colloquy.interaction.female.mirror.is_up