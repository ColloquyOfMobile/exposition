from colloquy.base import Base

from colloquy.hardware.value_setter import ValueSetter

class Brightness(Base):
    def __init__(self, owner, name):
        Base.__init__(self, owner)
        self._name = name
        self._value = 0

        self._neopixel = owner

        self._setter = ValueSetter(owner=self, limit=101, get_func=lambda: self.value)

        # self._increment1 = Increment(owner=self, multiplier=1)
        # self._increment10 = Increment(owner=self, multiplier=10)
        # self._increment100 = Increment(owner=self, multiplier=100)

        # self[self._increment1.name] = self._increment1
        # self[self._increment10.name] = self._increment10
        # self[self._increment100.name] = self._increment100

    @property
    def neopixel(self):
        return self._neopixel

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def setter(self):
        return self._setter

    @value.setter
    def value(self, value):
        self.set_without_updating(value)
        self.neopixel.update()

    def set(self, value):
        self.value = value

    def set_without_updating(self, value):
        if value > 100:
            value = 100
        if value < 0:
            value = 0
        self._value = value

    @property
    def snapshot_children(self):
        children = {}
        children.update(
            {
                self.setter.name: self.setter,
            }
        )
        return children

    def _snapshot_if_opened(self, path):
        # "value" was a bare int in snapshot_children, which Base._snapshot_
        # if_opened's default walk crashes on the instant this node is
        # opened directly (calls .snapshot_as_child() on it, which an int
        # doesn't have). Inject it as a proper display leaf instead.
        states = super()._snapshot_if_opened(path)
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self.value,
        }
        return states
