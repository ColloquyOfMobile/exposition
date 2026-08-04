# -*- coding: utf-8 -*-
# colloquy/base_thread/thread_error/__init__.py
from colloquy.base import Base
from .html import HTML
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
        self._html = HTML(owner=self)

        self[self.html.name] = self.html.handle_request

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
    def html(self):
        return self._html

    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]

        return states
