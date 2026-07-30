from threading import Event


class Events:
    def __init__(self, shutdown):
        self._shutdown = Event()  # shutdown
        self._restart = Event()

    @property
    def shutdown(self):
        return self._shutdown

    @property
    def restart(self):
        return self._restart
