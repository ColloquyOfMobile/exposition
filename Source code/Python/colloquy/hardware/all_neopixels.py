from colloquy.base import Base


class AllNeopixels(Base):
    def __init__(self, owner, bodies):
        super().__init__(owner=owner)
        self._list = []
        for body in bodies:
            self._list.extend(body.neopixels)

    def __iter__(self):
        yield from self._list

    @property
    def name(self):
        return "all neopixels"

    def turn_all_on(self):
        for neopixel in self:
            neopixel.on()

    def turn_all_off(self):
        for neopixel in self:
            neopixel.off()

    @property
    def snapshot_children(self):
        children = {}
        children["turn all neopixels on"] = self.turn_all_on
        children["turn all neopixels off"] = self.turn_all_off
        return children

    # def snapshot(self, path):
    # states = super().snapshot(path=path)
    # states["turn all neopixels on"] = self.turn_all_on
    # states["turn all neopixels off"] = self.turn_all_off
    # return states
