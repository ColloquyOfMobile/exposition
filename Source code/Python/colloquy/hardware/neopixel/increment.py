from colloquy.base import Base


class Increment(Base):
    def __init__(self, owner, multiplier):
        super().__init__(owner=owner)
        self._multiplier = multiplier
        self._name = f"*{multiplier}"
        self._value = 0

    def __call__(self, request):
        if request == "+":
            self.owner.value += self.multiplier

        elif request == "-":
            self.owner.value -= self.multiplier

        else:
            raise NotImplementedError(request)

        # self.owner.neopixel.update()

    @property
    def name(self):
        return self._name

    @property
    def multiplier(self):
        return self._multiplier
