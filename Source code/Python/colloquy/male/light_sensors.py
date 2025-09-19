from colloquy.light_sensor import LightSensor

class UpSensor(LightSensor):

    def beamed(self):
        raise NotImplementedError

    def engaged(self):
        return self.hardware.interaction.female.mirror.is_up

class DownSensor(LightSensor):

    def beamed(self):
        raise NotImplementedError

    def engaged(self):
        return self.hardware.interaction.female.mirror.is_down