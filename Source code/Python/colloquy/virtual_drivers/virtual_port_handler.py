

class VirtualPortHandler:
    def __init__(self, port):
        self._port = port
        self.is_open = True

    def setBaudRate(self, *args, **kwargs):
        return

    def closePort(self, *args, **kwargs):
        self.is_open = False
        return

    def writePort(self, *args, **kwargs):
        return

    def clearPort(self, *args, **kwargs):
        return
