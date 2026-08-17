# -*- coding: utf-8 -*-
# colloquy/base_thread/thread_error/__init__.py
import traceback
from html import escape

from colloquy.base import Base
from threading import Lock
from pathlib import Path


class ThreadError(Base):
    _counter = 0
    _counter_lock = Lock()

    def __init__(self, owner, name, origin, error):
        self._name = name
        super().__init__(owner=owner)
        self._error = error
        self._origin = origin

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def name(self):
        return self._name

    @property
    def error(self):
        return self._error

    @property
    def origin(self):
        return self._origin

    @property
    def snapshot_children(self):
        return {}

    def as_html(self):
        """The failing thread's path and its full traceback, as one block.

        Rendered inline by ThreadErrors rather than hidden behind an "open"
        link: this is only ever shown when a thread has already died, and at
        that moment the traceback is the only thing worth reading. It used to
        be unreachable - the snapshot() this replaces called Base.snapshot()
        with the wrong arguments, so merely *looking at* a failed thread
        raised TypeError and took down the whole page, hiding the very error
        it was there to report.
        """
        text = "".join(traceback.format_exception(self._error))
        return (
            f"<p style='margin:0 0 0.2rem 0;'><b>{escape(self._origin.path.as_posix())}</b></p>"
            f"<pre style='white-space:pre-wrap;margin:0 0 0.8rem 0;'>{escape(text)}</pre>"
        )
