# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/server.py

"""The mock UI's server - a fork of `server2/__init__.py`.

Same reason as `ui/wsgi.py` next to it: while the page is being rebuilt,
nothing done for the mock should reach the installation. This one binds
8088, serves `ui/wsgi.py`, and knows there is no hardware behind it.
"""

import os
import sys
from socketserver import ThreadingMixIn
from threading import Event
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

from colloquy.ui.wsgi import MockWSGI

WSGIRequestHandler.log_message = lambda *args, **kwargs: None

ACCEPT_TIMEOUT = 0.5


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """One thread per connection - a copy of the installation's, and
    deliberately a copy rather than a shared import.

    The fork is the point (see the module docstring): nothing done here
    should be able to reach the exhibition. The reason the mock wants it
    is the smaller half of the installation's - wsgiref speaks HTTP/1.0
    one request at a time, so the four static assets every page pulls
    queue behind each other, and page work is done against this server.

    There is no command lock beside it, because there is no command to
    serialise: `Colloquy.get_states` holds one and `ui/mock.py` has no
    hardware, no threads and no params behind it.
    """


class MockServer:
    # Deliberately not the installation's 8087: on Windows a second
    # server binds that port quite happily rather than refusing, and then
    # requests are answered by whichever socket the OS picks - so a page
    # meant for the mock can arrive at the running installation instead.
    DEFAULT_PORT = 8088

    def __init__(self, colloquy, port=None):
        self.owners = []
        self.name = "mock server"
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
        hostname = "localhost"
        with make_server(
            hostname, port, self.wsgi, server_class=ThreadingWSGIServer
        ) as httpd:
            print(f"Accessible at http://{hostname}:{port}/app")

            # Otherwise this sits in accept() and never notices that a
            # worker thread set the event - see the installation's.
            httpd.timeout = ACCEPT_TIMEOUT

            while True:
                httpd.handle_request()

                if self.shutdown_event.is_set():
                    print("Shutdown event!")
                    break

        if self.restart_event.is_set():
            self.restart_process()

    def wsgi(self, environ, start_response):
        try:
            return MockWSGI(server=self, environ=environ, start_response=start_response)
        except Exception:
            # The installation's server emergency-stops the hardware here,
            # since a crash leaves any running thread moving with no UI
            # left to stop it. Nothing moves behind this one, so a crash
            # only has to take the server down and show itself.
            self.shutdown_event.set()
            raise

    def restart_process(self):
        """Start this process again, exactly as it was started.

        sys.argv is what was typed, and the working directory survives an
        exec, so `py mock_ui.py` comes back as `py mock_ui.py` on this
        same port rather than as the installation on 8087.
        """
        python = sys.executable
        os.execl(python, python, *sys.argv)
