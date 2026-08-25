import sys, os
from colloquy.base import Base
from socketserver import ThreadingMixIn
from threading import Event
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

# from .wsgi import WSGI
from .wsgi2 import WSGI2

WSGIRequestHandler.log_message = lambda *args, **kwargs: None

# How often the accept loop below wakes to look at shutdown_event. Only
# ever costs an idle wakeup twice a second; see run().
ACCEPT_TIMEOUT = 0.5


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """One thread per connection, instead of one request at a time.

    `wsgiref.simple_server` serves strictly serially, which made the red
    EMERGENCY STOP unreachable for as long as any request was busy -
    including the requests most likely to be busy, since a command that
    drives a servo runs inside one. `Colloquy.emergency_stop`'s docstring
    was written around that constraint, and the emergency-stop route does
    not go through the tree at all (see wsgi2._parse), so it is now
    answerable while something else is mid-command.

    It also stops the four static assets every page pulls (uPlot's css
    and js, uplot_chart.js, svg_zoom.js) from queueing behind one another
    - wsgiref speaks HTTP/1.0, so each is its own connection.

    What this deliberately does NOT do is let two commands run at once:
    serving serially was an accidental lock around the whole application,
    and `Colloquy.get_states` now holds a real one in its place.

    The defaults inherited here are the ones we want and are left alone:
    `daemon_threads` False and `block_on_close` True mean `server_close()`
    joins whatever is still in flight, so /shutdown's goodbye finishes
    being written before the listening socket goes away.
    """


class Server2(Base):
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
        with make_server(
            "localhost", port, self.wsgi, server_class=ThreadingWSGIServer
        ) as httpd:
            WSGIRequestHandler.log_message = lambda *args, **kwargs: None
            print(f"Accessible at http://{hostname}:{port}/")

            # handle_request() otherwise blocks in accept() forever.
            # Serving one request at a time that was harmless: /shutdown
            # ran inline, so the check below saw the event the instant it
            # returned. Threaded, /shutdown is set by a worker while this
            # loop is already back in accept(), and with nothing to wake
            # it the process would sit there until somebody happened to
            # load one more page.
            httpd.timeout = ACCEPT_TIMEOUT

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
        """Start this process again, exactly as it was started.

        It used to re-exec a hardcoded `main.py colloquy1` whatever had
        actually been run. sys.argv is what was typed, and the working
        directory survives an exec, so this process restarts as itself.
        """
        python = sys.executable
        os.execl(python, python, *sys.argv)
