# -*- coding: utf-8 -*-
# Source code/Python/colloquy/server2/network.py

"""Where another computer on the network finds this server.

The server listens on every interface (`Server2.BIND_ADDRESS`), and the
one thing somebody at the other computer then needs is what to type. That
is this machine's name, which is stable, and its addresses, which are not
- a DHCP lease moves - so both are said, at every start.

Nothing here may raise. It is asked on the way to starting the server,
and a machine with no network at all - a gallery laptop is off it as
often as not - must come up exactly as it did before and simply have
less to say.
"""
import socket

# Never routed anywhere (TEST-NET-1, reserved for documentation), which
# is the point: see _leaving_address.
_NOWHERE = ("192.0.2.1", 9)


def _leaving_address():
    """The address of the interface this machine reaches the network by.

    Connecting a datagram socket sends nothing at all - it only has the
    system choose a route, and the socket's own name is then the address
    on that route. A machine with several adapters (and a development
    machine has a row of virtual ones) is reachable on this one first.
    None when there is no route to choose.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(_NOWHERE)
        return probe.getsockname()[0]
    except (OSError, UnicodeError):
        return None
    finally:
        probe.close()


def _every_address():
    try:
        return socket.gethostbyname_ex(socket.gethostname())[2]
    except (OSError, UnicodeError):
        return []


def addresses():
    """This machine's IPv4 addresses, the likeliest to be reachable first.

    Self-assigned ones (169.254.x.x) are kept and put last rather than
    dropped: two machines joined by one cable and no router have nothing
    else, and that is a perfectly good way to reach a laptop in a gallery.
    """
    found = []
    leaving = _leaving_address()
    if leaving:
        found.append(leaving)
    found.extend(_every_address())

    usable = []
    for address in found:
        if address.startswith("127.") or address == "0.0.0.0":
            continue
        if address not in usable:
            usable.append(address)
    return tuple(sorted(usable, key=lambda address: address.startswith("169.254.")))


def name():
    """This machine's name, or "" if it will not say."""
    try:
        return socket.gethostname()
    except (OSError, UnicodeError):
        return ""


def urls(port):
    """What to type on another computer, by name first and then by address."""
    hosts = [host for host in (name(), *addresses()) if host]
    return tuple(f"http://{host}:{port}/" for host in hosts)
