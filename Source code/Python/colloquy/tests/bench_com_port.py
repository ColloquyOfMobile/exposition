# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/bench_com_port.py

"""Which lead a bench board is on.

There are two of them now - Thomas's audio subsystem and the Goertzel ear
- and there was very nearly a second copy of all of this, which is the
same reason `MarkdownDocument` exists. A bench board is not the
installation's Arduino: it is another Mega on another USB lead, and
picking the wrong one of the two or three plugged in is the first thing
that goes wrong at a desk.

The base `ComPort` answers with the *piece's* simulated ports, which is
the wrong question here. On the bench this lists the actual leads; off it
there is one stand-in and nothing else, because offering the U2D2's and
the Arduino's port names on this picker only ever invited somebody to
choose one.

What differs between the two boards is where the choice is remembered, so
that is the one thing a subclass says.
"""
from functools import partial

import serial.tools.list_ports as list_ports

from colloquy.drivers.com_port import ComPort


class BenchComPort(ComPort):
    """Subclass and set `params_section` to the params key that owns the
    remembered port."""

    params_section = None
    stand_in = "simulated bench port"

    def __init__(self, owner, value=None):
        super().__init__(owner=owner, value=None)

    def set(self, com_port, *args, **kwargs):
        self.owner.port_handler.port = com_port
        self.owner.params[self.params_section]["communication port"] = com_port
        self._value = com_port

    @property
    def ports(self):
        for name in self._ports:
            self._dict.pop(name, None)

        if self.is_bench:
            self._ports = [port.device for port in list_ports.comports()]
        else:
            self._ports = [self.stand_in]

        for name in self._ports:
            self[name] = partial(self.set, com_port=name)

        return self._ports

    @property
    def snapshot_children(self):
        """The ports to choose from, one command each.

        The base `ComPort` does not answer this at all - the
        installation's Arduino and U2D2 are reached by path dispatch and
        never drawn - so a bench test that is meant to be used from the
        page had to add it.
        """
        return {name: self[name] for name in self.ports}
