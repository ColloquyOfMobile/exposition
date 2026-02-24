# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/# commit.py

import textwrap
from yattag import Doc, indent
from my_server.solution3.base import Base



from my_server.solution3.html_base import HTMLBase




class Commit(Base):

    def __init__(self, owner):
        Base.__init__(self, owner=owner, name="commit")
        self._html = HTML(owner=self)
        self._wsgi = WSGIBase(owner=self, parse_class=Parse)


    def __call__(self):
        self.owner()
        self.owner.value = ""

    @property
    def update(self):
        return self._update

class HTML(HTMLBase):

    def as_button(self):
        doc, tag, text = Doc().tagtext()
        with tag("a", href=f"/{self.owner.path.as_posix()}", style="margin-left: 0.5ch; margin-right: 0.5ch;"):
            with tag("div"):
                text(f"{self.owner.name}")

        html = doc.getvalue()
        return indent(html)

    def _call_unsafe(self, *args):
        raise NotImplementedError
        return ""


class Parse(ParseBase):


    def call_no_args_unsafe(self,):
        self.wsgi.owner()

        headers = [("Content-Type", "text/html; charset=utf-8")]
        status = '200 OK'
        content = self.wsgi.owner.html.doc
        return status, headers, content.encode()
