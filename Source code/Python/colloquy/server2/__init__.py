import sys, os
from colloquy.base import Base
from threading import Event
from wsgiref.simple_server import make_server, WSGIRequestHandler

# from .wsgi import WSGI
from .wsgi2 import WSGI2

WSGIRequestHandler.log_message = lambda *args, **kwargs: None


class Server2(Base):
    # The installation's own port. Anything else pointed at this server -
    # the mock UI - must pick another, or two servers end up bound to the
    # same one and requests are answered by whichever the OS picks.
    DEFAULT_PORT = 8087

    def __init__(self, colloquy, port=None):
        super().__init__(
            owner=None,
        )
        self._shutdown_event = Event()
        self._restart_event = Event()
        self._colloquy = colloquy
        self.run(port=self.DEFAULT_PORT if port is None else port)

    @property
    def colloquy(self):
        return self._colloquy

    @property
    def shutdown_event(self):
        return self._shutdown_event

    @property
    def restart_event(self):
        return self._restart_event

    def run(self, port=DEFAULT_PORT):
        hostname = "localhost"  # socket.gethostname()
        with make_server("localhost", port, self.wsgi) as httpd:
            WSGIRequestHandler.log_message = lambda *args, **kwargs: None
            print(f"Accessible at http://{hostname}:{port}/")

            while True:
                httpd.handle_request()

                if self.shutdown_event.is_set():
                    print("Shutdown event!")
                    break
            print("Out from server loop.")
        print("Out from server context.")

        if self.restart_event.is_set():
            self.restart_process()

    def wsgi(self, environ, start_response):
        try:
            return WSGI2(server=self, environ=environ, start_response=start_response)
        except Exception:
            # An unhandled exception here only kills the HTTP loop below
            # (self.shutdown_event) - it does NOT touch BaseThread._shutdown,
            # so any hardware thread that's running (bar/body oscillation,
            # blink, search, ...) would otherwise keep moving completely
            # unsupervised with no UI left to stop it. Treat any crash as an
            # emergency stop.
            self.colloquy.emergency_stop()
            self.shutdown_event.set()
            raise

    def restart_process(self):
        # raise NotImplementedError
        python = sys.executable
        args = ["main.py", "colloquy1"]
        # args.append()
        os.execl(python, python, *args)
