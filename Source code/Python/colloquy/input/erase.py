# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/erase.py

from colloquy.base import Base


class Erase(Base):
    def __init__(self, owner):
        Base.__init__(self, owner=owner)

    def __call__(self):
        self.owner.value = self.owner.value[:-1]

    def http_response(self):
        headers = [("Content-Type", "text/html; charset=utf-8")]
        status = "200 OK"
        args = self.path.parts
        content = self.server.html.doc(*args)
        return status, headers, content.encode()

    @property
    def name(self):
        return "erase"

    @property
    def update(self):
        return self._update
