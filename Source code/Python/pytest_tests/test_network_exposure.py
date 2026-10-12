"""The server answers from the network, and what that had to bring with it.

It listened on localhost alone until 2026-10-12. Three things are pinned:

1. it is bound to every interface, with the handler that goes with it;
2. a connection that goes quiet cannot hold up a shutdown - which was
   harmless on localhost, where a dead browser takes its sockets with it,
   and across a network is a restart that never finishes;
3. working out what to type on the other computer never stops the server
   from starting, whatever state the network is in.

No test here listens on anything but 127.0.0.1: binding every interface
from a test would raise the firewall's dialog on whichever machine ran
the suite first.
"""
import socket
from threading import Thread
from time import monotonic
from types import SimpleNamespace
from wsgiref.simple_server import make_server

from colloquy import server2
from colloquy.server2 import (
    CONNECTION_TIMEOUT,
    RequestHandler,
    Server2,
    ThreadingWSGIServer,
    network,
)


# --- the bind -------------------------------------------------------------


def test_the_server_listens_on_every_interface(monkeypatch):
    asked = {}

    def record(host, port, app, **kwargs):
        asked.update(host=host, port=port, app=app, **kwargs)
        return "the server"

    monkeypatch.setattr(server2, "make_server", record)
    fake = SimpleNamespace(BIND_ADDRESS=Server2.BIND_ADDRESS, wsgi="the application")

    assert Server2.listen(fake, 8087) == "the server"

    # The empty string is every interface; "localhost" is what it was.
    assert asked["host"] == ""
    assert asked["port"] == 8087
    assert asked["app"] == "the application"
    assert asked["server_class"] is ThreadingWSGIServer
    assert asked["handler_class"] is RequestHandler


# --- a peer that goes quiet -----------------------------------------------


def _application(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"answered"]


class _Quick(RequestHandler):
    """The real handler, with a timeout a test can wait out."""

    timeout = 0.2


def test_connections_are_given_a_bounded_time_to_speak():
    # Long enough that no browser on a slow link is cut off mid-request,
    # short enough that a restart waiting on one is not a minute late.
    assert 2.0 <= CONNECTION_TIMEOUT <= 30.0
    assert RequestHandler.timeout == CONNECTION_TIMEOUT


def test_a_silent_connection_does_not_hold_up_closing_the_server(capsys):
    """The one that matters. `server_close()` joins every connection in
    flight, so a peer that connected and never spoke used to hold it for
    as long as it stayed silent - which over a network is for ever."""
    httpd = make_server(
        "127.0.0.1", 0, _application, server_class=ThreadingWSGIServer, handler_class=_Quick
    )
    httpd.timeout = 0.5
    silent = socket.create_connection(httpd.server_address)
    try:
        httpd.handle_request()

        took = []

        def close():
            began = monotonic()
            httpd.server_close()
            took.append(monotonic() - began)

        closer = Thread(target=close, daemon=True)
        closer.start()
        closer.join(5.0)
    finally:
        silent.close()

    assert took, "server_close() was still waiting on a connection that never spoke"
    # And it is an ordinary event, not a traceback on the console.
    assert "Traceback" not in capsys.readouterr().err


def test_a_connection_that_does_speak_is_still_answered():
    httpd = make_server(
        "127.0.0.1", 0, _application, server_class=ThreadingWSGIServer, handler_class=_Quick
    )
    httpd.timeout = 0.5
    try:
        with socket.create_connection(httpd.server_address) as client:
            client.sendall(b"GET / HTTP/1.0\r\n\r\n")
            httpd.handle_request()
            client.settimeout(5.0)
            answer = b""
            while True:
                piece = client.recv(4096)
                if not piece:
                    break
                answer += piece
    finally:
        httpd.server_close()

    assert answer.startswith(b"HTTP/1.0 200")
    assert answer.endswith(b"answered")


# --- a response goes out in pieces ----------------------------------------


def _response(content):
    """A WSGI2 holding an answer, without a request having been parsed."""
    from colloquy.server2.wsgi2 import WSGI2

    response = WSGI2.__new__(WSGI2)
    response._start_response = lambda status, headers: None
    response._status, response._headers, response._content = "200 OK", [], content
    return response


def test_a_large_answer_is_written_in_pieces_and_arrives_whole():
    """Each write has `CONNECTION_TIMEOUT` to leave, so a whole Gerber
    package in one write would only work over a fast link."""
    from colloquy.server2.wsgi2 import PIECE

    content = bytes(range(256)) * 3000  # 768 000 bytes: the package's size
    pieces = list(_response(content))

    assert len(pieces) > 1
    assert max(len(piece) for piece in pieces) <= PIECE
    assert all(type(piece) is bytes for piece in pieces), "wsgiref refuses anything else"
    assert b"".join(pieces) == content


def test_an_ordinary_answer_goes_out_as_it_always_did():
    assert list(_response(b"<html></html>")) == [b"<html></html>"]
    # A redirect has no body, and still writes once: that write is what
    # sends its headers.
    assert list(_response(b"")) == [b""]


def test_a_streamed_answer_is_passed_through_untouched():
    pieces = [b"one", b"two"]

    assert list(_response(iter(pieces))) == pieces


# --- what to type on the other computer -----------------------------------


def _network(monkeypatch, leaving, every, name="Colloquy-Laptop"):
    monkeypatch.setattr(network, "_leaving_address", lambda: leaving)
    monkeypatch.setattr(network, "_every_address", lambda: list(every))
    monkeypatch.setattr(network, "name", lambda: name)


def test_the_address_the_machine_reaches_the_network_by_comes_first(monkeypatch):
    _network(monkeypatch, "192.168.1.23", ["172.28.0.1", "192.168.1.23"])

    assert network.addresses() == ("192.168.1.23", "172.28.0.1")


def test_this_machine_itself_is_not_an_address_for_another(monkeypatch):
    _network(monkeypatch, None, ["127.0.0.1", "0.0.0.0", "192.168.1.23"])

    assert network.addresses() == ("192.168.1.23",)


def test_a_self_assigned_address_is_kept_and_put_last(monkeypatch):
    """Two machines on one cable with no router have nothing else."""
    _network(monkeypatch, "169.254.10.4", ["169.254.10.4", "192.168.1.23"])

    assert network.addresses() == ("192.168.1.23", "169.254.10.4")


def test_the_name_is_offered_before_any_address(monkeypatch):
    _network(monkeypatch, "192.168.1.23", ["192.168.1.23"])

    assert network.urls(8087) == (
        "http://Colloquy-Laptop:8087/",
        "http://192.168.1.23:8087/",
    )


def test_a_machine_with_no_network_has_nothing_to_say_and_says_it_quietly(monkeypatch):
    _network(monkeypatch, None, [], name="")

    assert network.addresses() == ()
    assert network.urls(8087) == ()


def test_no_lookup_that_fails_reaches_the_caller(monkeypatch):
    """It is asked on the way to starting the server."""

    def refuses(*args, **kwargs):
        raise OSError("the network is unreachable")

    class Unroutable:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self, address):
            raise OSError("no route")

        def close(self):
            pass

    monkeypatch.setattr(network.socket, "socket", Unroutable)
    monkeypatch.setattr(network.socket, "gethostbyname_ex", refuses)
    monkeypatch.setattr(network.socket, "gethostname", refuses)

    assert network.addresses() == ()
    assert network.name() == ""
    assert network.urls(8087) == ()
