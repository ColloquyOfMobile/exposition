from colloquy.base import Base
from .commands import Commands

# from .test_neopixel_consumption import TestNeopixelConsumption
# from .test_neopixel_communication import TestNeopixelCommunication
from .test_neopixel_segments import TestNeopixelSegments


class TestNeopixels(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._commands = Commands(owner=self)
        self._test_neopixel_segments = TestNeopixelSegments(owner=self)

    def __call__(self):
        if not self.is_opened:
            self.open()

    @property
    def name(self):
        return "test Neopixels"

    @property
    def test_neopixel_segments(self):
        return self._test_neopixel_segments

    @property
    def tests(self):
        return self.owner.tests
