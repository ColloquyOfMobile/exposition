# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/com_port.py

from functools import partial

from colloquy.drivers.com_port import SIMULATED_ARDUINO_PORT, ComPort
from colloquy.ui import leaves

from . import boards


class ComPort(ComPort):
    """Which lead the installation's Arduino is on.

    The same job as the base class, with the leads named. This machine has
    more than one USB serial device on it - the U2D2 is the other, and
    Thomas's board is a third when it is here - and which COM number each
    one got is not a fact worth carrying in anybody's head. boards.py
    names a board by the chip bridging it to USB, which does not change
    when Windows renumbers the ports.
    """

    def __init__(self, owner, value=None):
        super().__init__(owner=owner, value=None)
        # label on the page -> the COM name to actually open. The label is
        # the key because the key is what is drawn; the device is what
        # gets stored.
        self._devices = {}

    def set(self, com_port, *args, **kwargs):
        """Remember the lead, and point the link at it.

        Params first, then the handler. Which handler is the right one is
        read out of params (`Arduino.is_using_the_stand_in`), so building
        it before the write would build one for the lead being replaced -
        and a change between a real lead and the stand-in would then write
        the new name onto the wrong object and open nothing.
        """
        self.owner.params["arduino"]["communication port"] = com_port
        self.owner.use_port(com_port)
        self._value = com_port

    @property
    def ports(self):
        """Every lead on this machine, and the stand-in where there is one.

        Real leads are listed **wherever there are any**, not only on the
        installation. Which handler is opened follows the lead chosen here
        rather than which computer this is (see `Arduino.port_handler`),
        and the case that forced the two apart is the main PCB coming off
        the installation and onto the bench for an afternoon: the bench is
        `is_simulated`, so this picker offered nothing but the stand-in,
        and every tone "sounded" while the real Mega sat on the desk
        beside it.

        The stand-in is still offered wherever the piece is simulated - it
        is the only port CI and the other dev machine have - and it comes
        last, because on a machine with a board on it the board is the
        answer.
        """
        for name in self._ports:
            self._dict.pop(name, None)

        self._devices = {board.label: board.device for board in boards.detect()}
        if self.is_simulated:
            # One stand-in, not two. The base class offers the U2D2's
            # simulated port here as well, and the only thing that can be
            # done with that one is choose it by mistake.
            self._devices[SIMULATED_ARDUINO_PORT] = SIMULATED_ARDUINO_PORT

        self._ports = list(self._devices)
        for name, device in self._devices.items():
            self[name] = partial(self.set, com_port=device)

        return self._ports

    @property
    def snapshot_children(self):
        """The leads to choose from, one command each.

        The base class does not answer this at all: the installation's
        pickers were reached by path dispatch and never drawn, so nobody
        had needed it.
        """
        return {name: self[name] for name in self.ports}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        leaf(
            "currently",
            self.owner.params["arduino"]["communication port"] or "not set",
        )
        return states
