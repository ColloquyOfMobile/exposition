from colloquy.base_thread import BaseThread
from time import time, sleep
from .html import HTML

class Blink(BaseThread):

    def __init__(self, owner):
        self._name = f"blink {owner.male.name}"
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        self._timestamp = 0
        self._blink_step = 0.5

    @property
    def male(self):
        return self.owner.male

    @property
    def html(self):
        return self._html

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


# class _Blink():

    # def __init__(self, owner):
        # ThreadElement.__init__(self, owner=owner, name=f"blink")
        # self._timestamp = None
        # self._blink_step = 0.5

    # def __enter__(self):
        # self.stop_event.clear()
        # self._timestamp = 0
        # self.ring.configure(
            # red = 0,
            # green = 0,
            # blue = 0,
            # white = 255,
            # brightness = 255,)

    # def _loop(self):
        # if (time() - self._timestamp) > self._blink_step:
            # light_pattern = self.light_patterns[self.drives.state]
            # value = light_pattern.popleft()
            # light_pattern.append(value)
            # self.ring.set(value)
            # self._timestamp = time()

    # @property
    # def light_patterns(self):
        # return self.owner.body_neopixel.light_patterns

    # @property
    # def drives(self):
        # return self.owner.body_neopixel.drives

    # @property
    # def ring(self):
        # return self.owner.body_neopixel.ring

    # @property
    # def body_neopixel(self):
        # return self.owner.body_neopixel