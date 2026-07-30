# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/erase.py

import textwrap
from yattag import Doc, indent
from colloquy.base import Base

from colloquy.base_html import BaseHTML


class Erase(Base):
    def __init__(self, owner):
        Base.__init__(self, owner=owner)
        self._html = HTML(owner=self)

    def __call__(self):
        self.owner.value = self.owner.value[:-1]

    def http_response(self):
        headers = [("Content-Type", "text/html; charset=utf-8")]
        status = "200 OK"
        args = self.path.parts
        content = self.server.html.doc(*args)
        return status, headers, content.encode()

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "erase"

    @property
    def update(self):
        return self._update


class HTML(BaseHTML):
    def _call_unsafe(self, *args):
        doc, tag, text = Doc().tagtext()
        with tag(
            "a",
            href=f"/{self.owner.path.as_posix()}",
            style="margin-left: 0.5ch; margin-right: 0.5ch;",
        ):
            with tag("div"):
                text(f"<{self.owner.name}|")

        html = doc.getvalue()
        return indent(html)
