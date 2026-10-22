# -*- coding: utf-8 -*-
# Source code/Python/colloquy/server2/exclusive_port.py

"""One server on the port: a second one is turned away, not let in beside it.

On 2026-10-22 two `main.py` were running on the bench at once, both
answering on 8087, and a restart onto new code went on showing the old
page - each connection went to whichever of the two Windows handed it to.
Python's `HTTPServer` sets SO_REUSEADDR, and on Windows that option does
not mean what it means on Linux (bind a port whose old connections are
still closing): it lets a socket bind a port that another one is
*listening* on, as long as both asked for it. Measured on the bench, a
second bind from another process:

    already listening      second bind       result
    SO_REUSEADDR           SO_REUSEADDR      bound - both serve
    SO_REUSEADDR           exclusive         refused
    exclusive              anything          refused

So the server binds with SO_EXCLUSIVEADDRUSE and without SO_REUSEADDR,
and a second one is refused - even beside an old process still running
the code that asked for reuse. A restart is unaffected: the listener is
closed before the exec, and an exclusive bind succeeded at once beside
the old process's connections still closing (measured the same day).

`main.py` claims the port before anything else, because by the time the
server binds, a second process has already imported `colloquy` - which
empties `local/logs` under the first - opened the serial ports, and
started the repository watch and the schedule. It loads this module by
path for the same reason, so: stdlib only.
"""
from __future__ import annotations

import socket
import subprocess
import time

PORT = 8087
# Every interface - see `Server2.BIND_ADDRESS`, which is this.
ADDRESS = ""

# A restart's old process, or one the dev watcher (test_process.py) has
# just killed, may still be letting go of the port.
CLAIM_PATIENCE = 3.0
CLAIM_INTERVAL = 0.25


class PortInUse(OSError):
    """Another process has the port; the message says which, and what to do."""


def exclusive(sock: socket.socket) -> None:
    """Before the bind: while this socket has the port, nobody else gets it.

    The option is Windows' own; elsewhere a second listener is refused
    without it.
    """
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)


def claim(address: str = ADDRESS, port: int = PORT,
          patience: float = CLAIM_PATIENCE) -> socket.socket:
    """Bind the port as the server will, and hold it until the server binds.

    Bound, not listening: nothing is answered on it, and nothing else can
    have it. Raises `PortInUse` once `patience` has run out.
    """
    deadline = time.monotonic() + patience
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        exclusive(sock)
        try:
            sock.bind((address, port))
            return sock
        except OSError as error:
            sock.close()
            if time.monotonic() >= deadline:
                raise PortInUse(refusal(port, error)) from error
            time.sleep(CLAIM_INTERVAL)


def holders(port: int) -> list[tuple[str, str]]:
    """(PID, command line) of each process listening on the port.

    Whatever Windows will say, and nothing at all rather than an
    exception: this is only ever asked on the way to a refusal.
    """
    try:
        listing = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True, errors="replace", timeout=10,
        ).stdout
    except Exception:  # noqa: BLE001 - see the docstring
        return []
    pids = []
    for line in listing.splitlines():
        fields = line.split()
        # Proto, local, foreign, state, PID. The state is written in the
        # machine's own language (ABHÖREN on the bench); a listener's
        # foreign address is not.
        if (len(fields) == 5 and fields[1].endswith(f":{port}")
                and fields[2] in ("0.0.0.0:0", "[::]:0") and fields[4] not in pids):
            pids.append(fields[4])
    return [(pid, _command_line(pid)) for pid in pids]


def _command_line(pid: str) -> str:
    if not pid.isdigit():
        return ""
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True, errors="replace", timeout=10,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - see holders()
        return ""


def refusal(port: int, error: OSError | None = None) -> str:
    """What a second server says on its way out, and what to do instead."""
    found = holders(port)
    lines = [f"Port {port} is already taken"
             + (f" ({error.strerror or error})" if error else "") + "."]
    if found:
        lines.append("It is held by:")
        lines += [f"  PID {pid}: {command or 'command line unknown'}" for pid, command in found]
    lines += [
        "Nothing was started: a second server would share the port with the",
        "first, and each page would come from either one.",
        "To run new code, press 'restart' on the running server's page.",
        "To start this one instead, stop the other first - 'shutdown' on its",
        "page" + (f", or: Stop-Process -Id {found[0][0]}" if found else "") + ".",
    ]
    return "\n".join(lines)
