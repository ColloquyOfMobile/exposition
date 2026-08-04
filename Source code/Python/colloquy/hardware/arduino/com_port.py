from colloquy.hardware.com_port import ComPort


class ComPort(ComPort):
    def __init__(self, owner, value=None):
        super().__init__(owner=owner, value=None)

    def set(self, com_port, *args, **kwargs):
        self.owner.port_handler.port = com_port
        self.owner.params["arduino"]["communication port"] = com_port
        self._value = com_port
