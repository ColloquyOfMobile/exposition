from pathlib import Path
import traceback
import socket
from threading import Thread, Event, Lock
from colloquy.base import Base
from utils import CustomDoc
# from colloquy.wsgi.root.html_item import HtmlItem
# from server.html_element import HTMLElement
# from .html import HTML
# from .action import Action
from .workspace import Workspace

class Body(Base):

    def __init__(self, owner):
        super().__init__(owner)
        self._server = owner.server
        self._opened = None
        self._commands = self.owner.owner.commands
        self._workspace = Workspace(owner=self)
        # self.init()

    def __call__(self):
        try:
            html = self._call_unsafe()
        except Exception as exception:
            html = self._call_if_error()

        return html

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def server(self):
        return self._server

    @property
    def body(self):
        return self

    @property
    def commands(self):
        return self._commands

    @property
    def workspace(self):
        return self._workspace

    @property
    def name(self):
        return "body"

    @property
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        # Value is None only in a Close(), this is to avoid recursion.
        if value is not None:
            if self._opened is not None:
                self._opened.close()

        self._opened = value


    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("body", style="display: flex; flex-direction: column;"):
            with tag("h1", style="display: flex; flex: 1; justify-items: center;"):
                text(
                    f"Colloquy of Mobiles"
                    )
            if self.owner.events.restart.is_set():
                doc.asis(self._call_if_restart())
            elif self.owner.events.shutdown.is_set():
                doc.asis(self._call_if_shutdown())
            else:
                doc.asis(self.commands())
                
                with tag("div", style="margin-bottom: 1rem;"):
                    text("TODO: Reintegrate the search for the Females.")
                    
                doc.asis(self.workspace())

        return doc.getvalue()

    def _call_if_error(self):
        doc, tag, text = CustomDoc().tagtext()
        self.events.shutdown.set()
        with tag("body"):
            with tag("h1"):
                text(f"Error html for {self.name}!")

            with tag("h2"):
                text(f"NOTE: Server was shutdown! Restart manually...)")

            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exc().splitlines():
                    with tag("pre", style=style):
                        text(line)

        return doc.getvalue()


    def _call_if_shutdown(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div"):
            text(
                f"Server was shutdown. You can close this tab. Goodbye."
                )

        return doc.getvalue()


    def _call_if_restart(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div"):
            text(
                f"Server is restarted. Reload to see the changes."
                )
        with tag("div"):
            with tag("a", href="/"):
                text(
                    f"Reload."
                    )

        return doc.getvalue()