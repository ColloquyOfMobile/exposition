from colloquy.base_thread import BaseThread
from time import time


class Blink(BaseThread):
    def __init__(self, owner):
        self._name = f"blink {owner.male.name}"
        super().__init__(owner=owner)
        self._timestamp = 0
        self._blink_step = 0.5

    @property
    def male(self):
        return self.owner.male

    @property
    def name(self):
        return self._name

    @property
    def white(self):
        return dict(red=0, green=0, blue=0, white=255)

    def loop(self):
        if (time() - self._timestamp) > self._blink_step:
            light_pattern = self.male.get_blink_pattern()
            value = light_pattern.popleft()
            light_pattern.append(value)
            self.male.ring.set(value)
            self._timestamp = time()

    def setup(self):
        self.male.ring.color = self.white
        self.male.ring.on()
        self._timestamp = 0
        pass

    def setdown(self):
        self.male.ring.off()
        pass

    @property
    def snapshot_children(self):
        return {}
