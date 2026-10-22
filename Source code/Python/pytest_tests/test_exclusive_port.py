"""One server on the port: a second is refused, a restart is not.

Two `main.py` once ran side by side on 8087 and split the page between
them (2026-10-22): `HTTPServer` asks for SO_REUSEADDR, which on Windows
lets a second socket listen beside the first. Pinned here: the server
binds exclusively, even an old server still asking for reuse keeps a new
one out, a restart binds at once beside the old connections still
closing, `main.py`'s early claim holds the port, and a refused server says
who has it and lets its own threads go.

127.0.0.1 only, like `test_network_exposure.py`: every interface would
raise the firewall's dialog.
"""
import socket
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer

import pytest

from colloquy.server2 import RequestHandler, Server2, ThreadingWSGIServer, exclusive_port

HOST = "127.0.0.1"


def free_port():
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def new_server(port=0):
    return ThreadingWSGIServer((HOST, port), RequestHandler)


def old_server(port=0):
    """What the server was before: `HTTPServer`'s SO_REUSEADDR."""
    return WSGIServer((HOST, port), WSGIRequestHandler)


def _answer(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"answered"]


@pytest.mark.skipif(sys.platform != "win32", reason="the trap is Windows' meaning of SO_REUSEADDR")
def test_the_trap_two_reuse_servers_share_a_port():
    """Why any of this exists - if this ever fails, Windows changed."""
    first = old_server()
    try:
        second = old_server(first.server_address[1])
        second.server_close()
    finally:
        first.server_close()


def test_a_second_server_cannot_listen_beside_the_first():
    first = new_server()
    port = first.server_address[1]
    try:
        with pytest.raises(OSError):
            new_server(port)
        with pytest.raises(OSError):
            old_server(port)
    finally:
        first.server_close()


def test_an_old_server_still_running_keeps_a_new_one_out():
    first = old_server()
    try:
        with pytest.raises(OSError):
            new_server(first.server_address[1])
    finally:
        first.server_close()


def test_a_restart_binds_at_once_beside_the_connections_still_closing():
    first = new_server()
    first.set_app(_answer)
    port = first.server_address[1]
    served = threading.Thread(target=first.handle_request)
    served.start()
    with socket.create_connection((HOST, port)) as client:
        client.sendall(b"GET / HTTP/1.0\r\n\r\n")
        while client.recv(1024):
            pass
    served.join()
    first.server_close()

    second = new_server(port)
    second.server_close()


def test_the_claim_holds_the_port_until_the_server_binds():
    port = free_port()
    claim = exclusive_port.claim(HOST, port, patience=0)
    try:
        with pytest.raises(exclusive_port.PortInUse):
            exclusive_port.claim(HOST, port, patience=0)
        with pytest.raises(OSError):
            new_server(port)
    finally:
        claim.close()
    new_server(port).server_close()


def test_the_claim_waits_for_a_port_being_let_go():
    port = free_port()
    held = exclusive_port.claim(HOST, port, patience=0)
    threading.Timer(0.3, held.close).start()
    exclusive_port.claim(HOST, port, patience=3).close()


NETSTAT = """
Aktive Verbindungen

  Proto  Lokale Adresse         Remoteadresse          Status           PID
  TCP    0.0.0.0:8087           0.0.0.0:0              ABHÖREN          2012
  TCP    127.0.0.1:8087         127.0.0.1:51234        WARTEND          0
  TCP    0.0.0.0:18087          0.0.0.0:0              ABHÖREN          77
"""


def test_the_refusal_says_who_has_the_port_and_what_to_do(monkeypatch):
    def run(command, **kwargs):
        if command[0] == "netstat":
            return SimpleNamespace(stdout=NETSTAT)
        assert "ProcessId=2012" in command[-1]
        return SimpleNamespace(stdout="python.exe main.py\r\n")

    monkeypatch.setattr(exclusive_port.subprocess, "run", run)
    said = exclusive_port.refusal(8087, OSError(10048, "address in use"))
    assert "Port 8087 is already taken" in said
    assert "PID 2012: python.exe main.py" in said
    assert "PID 77" not in said
    assert "restart" in said and "Stop-Process -Id 2012" in said


def test_the_refusal_never_raises(monkeypatch):
    def broken(*args, **kwargs):
        raise subprocess.TimeoutExpired("netstat", 10)

    monkeypatch.setattr(exclusive_port.subprocess, "run", broken)
    assert exclusive_port.holders(8087) == []
    assert "Port 8087 is already taken" in exclusive_port.refusal(8087)


def test_a_refused_server_lets_its_threads_go_without_moving_anything(monkeypatch, capsys):
    monkeypatch.setattr(exclusive_port, "holders", lambda port: [])
    order = []

    def taken(port):
        order.append("bind")
        raise OSError(10048, "address in use")

    fake = SimpleNamespace(listen=taken, colloquy=SimpleNamespace(shutdown=lambda: order.append("shutdown")))
    Server2.run(fake, 8087, claim=SimpleNamespace(close=lambda: order.append("released")))
    assert order == ["released", "bind", "shutdown"]
    assert "Port 8087 is already taken" in capsys.readouterr().out


def test_importing_main_claims_nothing():
    """The tests import main.py for open_the_hardware(); only running it claims."""
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import main

    assert main.PORT_CLAIM is None
