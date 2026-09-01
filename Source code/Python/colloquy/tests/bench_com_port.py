# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/bench_com_port.py

"""Which lead a bench board is on.

There are two of them now - Thomas's audio subsystem and the Goertzel ear
- and there was very nearly a second copy of all of this, which is the
same reason `MarkdownDocument` exists. A bench board is not the
installation's Arduino: it is another Mega on another USB lead, and
picking the wrong one of the two or three plugged in is the first thing
that goes wrong at a desk.

**The question is the lead, not the machine.** This asked `is_bench` and
listed real ports only there, which quietly decided that a bench board
can only ever be on the bench. It cannot: Thomas's board gets carried to
the installation's own laptop to be run at 12 V beside the piece, and on
that machine the picker offered one stand-in and nothing else - two
passes against a simulator that differ by nothing, which reads exactly
like a rail change that bought you nothing. The Arduino driver had
already learned this the other way round (the main PCB coming *off* the
installation and onto a desk); see `Arduino.is_using_the_stand_in` and
`drivers/arduino/com_port.py`, which this now mirrors.

So: real leads are listed **wherever `boards.detect()` finds any**, named
by the chip bridging them to USB so the U2D2's FTDI lead is visibly not a
Mega, and the stand-in is offered as well wherever the piece is
simulated - it is the only port CI and the other dev machine have. Which
handler gets opened follows the port chosen here rather than the
hostname, so the page can always say which of the two answered.

What differs between the two boards is where the choice is remembered, so
that is the one thing a subclass says.
"""
from functools import partial

from colloquy.drivers.arduino import boards
from colloquy.drivers.com_port import ComPort


class BenchComPort(ComPort):
    """Subclass and set `params_section` to the params key that owns the
    remembered port."""

    params_section = None
    stand_in = "simulated bench port"

    def __init__(self, owner, value=None):
        super().__init__(owner=owner, value=None)
        # label on the page -> the port name to actually open, as the
        # Arduino's picker holds it. The label is the key because the key
        # is what is drawn; the device is what gets stored, and a COM
        # number is not a fact worth carrying in anybody's head.
        self._devices = {}

    def set(self, com_port, *args, **kwargs):
        """Remember the lead, then point the link at it.

        Params first, then the handler. Which handler is the right one is
        now read back out of params (`is_using_the_stand_in`), so building
        it before the write would build one for the lead being replaced -
        the same ordering, and for the same reason, as the Arduino's.
        """
        self.owner.params[self.params_section]["communication port"] = com_port
        self.owner.use_port(com_port)
        self._value = com_port

    @property
    def chosen(self):
        """The port name in params, which outlives the machine that chose
        it - that is what `_why_not_open` is checking."""
        return self.owner.params[self.params_section]["communication port"]

    @property
    def is_using_the_stand_in(self):
        """Is the chosen lead the simulator, rather than a board?

        One property, asked by the owner's `port_handler` and said on its
        page. A question about the lead: it is true on the bench if
        somebody picked the stand-in there, and false on the installation
        the afternoon the board is carried over.
        """
        return self.chosen == self.stand_in

    @property
    def ports(self):
        """The port names that can be chosen here.

        Devices, not labels - this is what gets stored in params and what
        `_why_not_open` checks the remembered name against. The labels are
        the keys the page draws; see `snapshot_children`.
        """
        for label in self._ports:
            self._dict.pop(label, None)

        self._devices = {board.label: board.device for board in boards.detect()}
        if self.is_simulated:
            # Last, because on a machine with a board plugged into it the
            # board is the answer.
            self._devices[self.stand_in] = self.stand_in

        self._ports = list(self._devices)
        for label, device in self._devices.items():
            self[label] = partial(self.set, com_port=device)

        return list(self._devices.values())

    @property
    def snapshot_children(self):
        """The leads to choose from, one command each.

        The base `ComPort` does not answer this at all - the
        installation's Arduino and U2D2 are reached by path dispatch and
        never drawn - so a bench test that is meant to be used from the
        page had to add it. Asking `ports` first is what refreshes both
        the list and the commands behind it.
        """
        self.ports
        return {label: self[label] for label in self._devices}
