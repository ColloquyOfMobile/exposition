# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/line.py

import textwrap
import ast
from yattag import Doc, indent
import string
from colloquy.base_html import BaseHTML
from colloquy.base import Base


class Line(Base):
    def __init__(self, owner, name, keys):
        super().__init__(owner=owner, name=name)
        self._html = HTML(owner=self)
        self._keys = keys

    @property
    def keys(self):
        return self._keys


class HTML(BaseHTML):

    def html_independant_args(self):
        doc, tag, text = Doc().tagtext()
        style = [
            "flex:1",
            "display: flex",
            "flex-direction: row",
            "gap: 0.5ch",
            "align-items: center",
            "justify-content: center",
        ]
        with tag("div", name=self.owner.name, style="; ".join(style)):
            for line in self.owner.keys:
                doc.asis(line.html.as_button())

        html = doc.getvalue()
        return indent(html)

    def call_no_args_unsafe(self):
        return ""

    def call_direction_independant(self):
        return ""
