# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/com_port.py

from functools import partial

from colloquy.drivers.com_port import ComPort
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
        self.owner.port_handler.port = com_port
        self.owner.params["arduino"]["communication port"] = com_port
        self._value = com_port

    @property
    def ports(self):
        for name in self._ports:
            self._dict.pop(name, None)

        if self.is_simulated:
            # One stand-in, not two. The base class offers the U2D2's
            # simulated port here as well, and the only thing that can be
            # done with that one is choose it by mistake.
            self._devices = {"simulated arduino port": "simulated arduino port"}
        else:
            self._devices = {
                board.label: board.device for board in boards.detect()
            }

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
