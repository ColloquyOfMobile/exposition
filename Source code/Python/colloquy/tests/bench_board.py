# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/bench_board.py

"""The serial link to Thomas's board, on whichever desk it is on today.

`BenchComPort` is which lead was chosen; this is what gets opened on the
other end of it, and the two are halves of one arrangement - the picker
lists the leads, this follows the choice. They were separate copies in
`test audio subsystem` and `test audio at 12v`, identical down to the
comment, and both said the same wrong thing: `is_bench`.

**A board is on a lead, not on a hostname.** The bench is only where the
board usually lives. It gets carried to the installation's own laptop to
be run at 12 V beside the piece, and there `is_bench` is False, so both
tests opened the stand-in and reported plausible numbers about hardware
they were not talking to. That is precisely the failure `is_bench` was
introduced to fix, one machine over: the picker used to ask
`is_simulated`, which sent the tests at the stand-in while the real Mega
sat on the bench beside them. The lesson did not stick because it was
written as another hostname instead of as a question about the lead.

`Arduino.is_using_the_stand_in` is the same property for the
installation's own board, and `Arduino.use_port` is the same swap.
"""
import serial


class BenchBoardLink:
    """Mixed into a test that owns a `BenchComPort` as `self._com_port`.

    Wants `self._port_handler` initialised to None by the test's
    `__init__`, and a `baudrate`.
    """

    # As both audio tests used. Short: the board talks when it likes and
    # every read is inside a deadline loop that will come round again.
    SERIAL_TIMEOUT = 0.05

    # Which kind is in hand. Set whenever a handler is built; read only
    # when there is one, so the None is never compared against.
    _handler_is_the_stand_in = None

    @property
    def board_is_real(self):
        """Shown on the page, because a wrong answer here is otherwise
        silent: a run against the stand-in passes everything and looks
        exactly like a run against a working bench.

        It asks the lead, not the machine - see the module docstring.
        """
        return not self._com_port.is_using_the_stand_in

    @property
    def stand_in_handler(self):
        return self.colloquy.virtual_drivers.audio_serial_port

    @property
    def port_handler(self):
        if self._port_handler is None:
            self._handler_is_the_stand_in = self._com_port.is_using_the_stand_in
            if self._handler_is_the_stand_in:
                self._port_handler = self.stand_in_handler
            else:
                self._port_handler = serial.Serial(
                    baudrate=self.baudrate, timeout=self.SERIAL_TIMEOUT
                )
            # Setting the name here rather than opening: opening resets
            # the board, and nothing has asked for that yet.
            self._port_handler.port = self._com_port.chosen
        return self._port_handler

    def use_port(self, com_port):
        """Point the link at a newly chosen lead.

        A real lead and the stand-in are different objects, so moving
        between them is not a matter of writing a new name onto the
        handler already in hand - that one has to go first, and it is
        closed before it is dropped. A discarded pyserial handle keeps
        the COM port open until the garbage collector reaches it, and the
        next open then fails saying the port is busy, which reads exactly
        like a board that is not there. Straight out of
        `Arduino.use_port`, which learned it the hard way.
        """
        wants_the_stand_in = com_port == self._com_port.stand_in
        if (
            self._port_handler is not None
            and self._handler_is_the_stand_in != wants_the_stand_in
        ):
            if self._port_handler.is_open:
                self._port_handler.close()
            self._port_handler = None

        self.port_handler.port = com_port
