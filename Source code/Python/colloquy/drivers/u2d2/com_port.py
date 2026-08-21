from colloquy.drivers.com_port import ComPort


class ComPort(ComPort):
    def __init__(self, owner, value=None):
        super().__init__(owner=owner, value=None)

    def set(self, com_port, *args, **kwargs):
        self._value = com_port
