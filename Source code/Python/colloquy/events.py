from threading import Event

class Events():

    def __init__(self):
        self._shutdown = Event()
        self._restart= Event()

    @property
    def shutdown(self):
        return self._shutdown

    @property
    def restart(self):
        return self._restart