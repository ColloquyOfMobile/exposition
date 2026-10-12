from traceback import format_exc
import sys, os
from colloquy.base import Base
from socketserver import ThreadingMixIn
from threading import Event
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

# from .wsgi import WSGI
from . import network
from .wsgi2 import WSGI2

WSGIRequestHandler.log_message = lambda *args, **kwargs: None

# How often the accept loop below wakes to look at shutdown_event. Only
# ever costs an idle wakeup twice a second; see run().
ACCEPT_TIMEOUT = 0.5

# How long a connection may sit without a byte moving before it is
# dropped. See RequestHandler: this is what keeps a peer that has gone
# quiet from holding up a restart, not a limit on how long a request may
# take - a command runs for as long as it runs.
CONNECTION_TIMEOUT = 10.0


class RequestHandler(WSGIRequestHandler):
    """A connection that goes quiet is dropped instead of waited on.

    `server_close()` joins every connection still in flight (see
    ThreadingWSGIServer), and a handler with no timeout sits in its first
    read until the other end speaks or hangs up. On localhost that was
    always one or the other: a browser that dies takes its sockets with
    it. Across a network it is neither - a phone that falls asleep, a
    laptop carried out of range of the access point - and then that read
    never returns, `server_close()` never returns, and a shutdown or a
    restart stops for good with the listening socket already closed.
    Measured: one silent connection was still holding `server_close()`
    when the test gave up waiting, and it returns the moment this fires.
    On a machine that restarts itself unattended (`restart_for_update`)
    that is the installation with no server until somebody walks over.

    The timeout is on the socket, so it only ever measures the other end:
    a command that takes a minute is not waiting on the socket while it
    runs. A download is sent in pieces and each has this long to leave,
    which a link that is moving at all manages.
    """

    timeout = CONNECTION_TIMEOUT

    def handle(self):
        try:
            super().handle()
        except TimeoutError:
            # Nothing to answer and nobody to answer it to. Left to
            # propagate it reaches socketserver, which prints a traceback
            # for what is an ordinary event - a browser opens connections
            # it never uses.
            pass


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """One thread per connection, instead of one request at a time.

    `wsgiref.simple_server` serves strictly serially, which made the red
    EMERGENCY STOP unreachable for as long as any request was busy -
    including the requests most likely to be busy, since a command that
    drives a servo runs inside one. `Colloquy.emergency_stop`'s docstring
    was written around that constraint, and the emergency-stop route does
    not go through the tree at all (see wsgi2._parse), so it is now
    answerable while something else is mid-command.

    It also stops the static assets a page pulls (svg_zoom.js, and any
    picture beside it) from queueing behind one another - wsgiref speaks
    HTTP/1.0, so each is its own connection. There were four until uPlot
    was retired on 2026-09-09.

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

    # Every interface, so the page answers from another computer on the
    # same network and not only on this machine - which is what a laptop
    # handing out Gerbers is for, and how the piece is looked after from
    # somewhere other than the chair in front of it. It was "localhost".
    #
    # **Nothing on the page asks who is asking.** There is no login, and
    # every link is a GET that does what it says, so whoever can reach
    # this port can do everything the page can: shut the installation
    # down, unmount its board, flash its Arduino. What stands between
    # that and the building is the network this machine is on and its
    # firewall, and neither is this program's to answer for.
    BIND_ADDRESS = ""

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

    def listen(self, port):
        """The listening server, bound and not yet serving."""
        return make_server(
            self.BIND_ADDRESS,
            port,
            self.wsgi,
            server_class=ThreadingWSGIServer,
            handler_class=RequestHandler,
        )

    def run(self, port=DEFAULT_PORT):
        with self.listen(port) as httpd:
            WSGIRequestHandler.log_message = lambda *args, **kwargs: None
            print(f"Accessible at http://localhost:{port}/")
            elsewhere = network.urls(port)
            if elsewhere:
                print(
                    "From another computer on this network: "
                    + " or ".join(elsewhere)
                )

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

                # Asked here, twice a second, because nothing in the tree
                # can restart the server and nothing should be able to:
                # the repository says when a restart is due and this loop
                # is what acts on it. See restart_for_update().
                if self.update_wants_a_restart():
                    self.restart_for_update()

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
            #
            # The nested try is the lesson of a real traceback: the
            # emergency stop raised too - a bare AssertionError out of
            # U2D2.open, on an installation whose main PCB was noted as
            # unmounted - and took the two lines below with it. So the
            # server was never asked to stop, and the crash that reached
            # wsgiref was the second one, with the first nowhere in it.
            # A handler that can fail the same way as the thing it is
            # handling is not a handler.
            try:
                self.colloquy.emergency_stop()
            except Exception:
                self.log("The emergency stop itself failed:")
                self.log(format_exc())
            finally:
                self.shutdown_event.set()
            # Bare, so this is still the original exception rather than
            # anything that happened while handling it.
            raise

    def update_wants_a_restart(self):
        """Has the repository pulled new code and counted down to it?

        Only ever True on the installation's laptop, and there only when
        nothing that drives the piece is running - see
        `Repository.restart_is_due`, which holds every condition. Once a
        stop is already under way there is nothing further to decide.
        """
        if self.shutdown_event.is_set():
            return False
        return self.colloquy.repository.restart_is_due

    def restart_for_update(self):
        """Restart onto the code the repository has just pulled.

        `/restart` with nobody pressing it: the same two calls and the
        same two events, on the accept loop instead of in a request. It
        waits for a command in flight the way `/shutdown` does, since
        this is the one restart no person chose the moment of.

        The page has been saying it was coming for `RESTART_NOTICE`
        seconds (`server2/updates.py`), and the repository leaves a note
        for the next process to say that it happened.
        """
        print("An update was pulled - restarting to run it.")
        self.colloquy.repository.restarting()
        with self.colloquy.hold_commands():
            self.colloquy.shutdown()
            self.colloquy.join_all()
        self.shutdown_event.set()
        self.restart_event.set()

    def restart_process(self):
        """Start this process again, exactly as it was started.

        It used to re-exec a hardcoded `main.py colloquy1` whatever had
        actually been run. sys.argv is what was typed, and the working
        directory survives an exec, so this process restarts as itself.
        """
        python = sys.executable
        os.execl(python, python, *sys.argv)
