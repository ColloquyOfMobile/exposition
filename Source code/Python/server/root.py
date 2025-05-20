from pathlib import Path
from colloquy import Colloquy
from virtual_colloquy import VirtualColloquy
import socket
from .file_handler import FileHandler
from .shutdown import Shutdown
from .html_element import HTMLElement
from colloquy.logger import Logger as _Logger

class Root(HTMLElement):
    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._owner = owner
        self.path = Path("")
        self._log = Logger(owner=self)
        self.active = None
        self._items = {}
        self.elements = set()
        self.threads = set()
        self._colloquy = None
        self.init()

    def __call__(self, **kwargs):
        self._init_html_doc()
        self.write_html(**kwargs)
        return [self.html_doc.getvalue().encode()]

    @property
    def log(self):
        return self._log

    def init(self):
        hostname = socket.gethostname()
        if hostname == "DESKTOP-MRSLS88":
            self._items["colloquy"] = self._colloquy = VirtualColloquy(owner=self)
            return

        self._items["colloquy"] = self._colloquy = Colloquy(owner=self)

    def write_html(self, **kwargs):
        doc, tag, text = self.html_doc.tagtext()

        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            self._write_html_head()
            self._write_body(**kwargs)

    def _write_html_head(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("head"):
            with tag("title"):
                text(f"Colloquy of Mobiles")
            doc.asis(
                '<meta name="viewport"'
                ' content="width=device-width,'
                " initial-scale=1,"
                ' interactive-widget=resizes-content" />'
            )

        # response = doc.read()
        # yield response.encode()

    def _write_body(self, **kwargs):
        doc, tag, text = self.html_doc.tagtext()
        with tag("body"):
            with tag("h1",):
                text(
                    f"Colloquy of Mobiles (threads={self._colloquy.thread_count})"
                    )

            if self._colloquy.thread_count:
                with tag("details",):
                    with tag("summary",):
                        text(
                            f"threads: {self._colloquy.thread_count}"
                            )
                    for e in self._colloquy.iter_thread_pool():
                        with tag("summary",):
                            text(
                                f"{e.name}"
                                )

            if self.active is not None:
                self.active(**kwargs)
            else:
                self._handle_request(**kwargs)

    def _handle_request(self, **kwargs):
        if kwargs:
            action = kwargs.pop("action")[0]
            self._colloquy.actions[action](**kwargs)

        self._colloquy.add_html()

class Logger(_Logger):

    def __init__(self, owner):
        self._owner = owner
        self._folder = self._log_folder
        self._path = self._folder / f"root.log"
        self._line_count = None

        assert self._path not in self._instances, f"{self._path=}"
        self._instances[self._path] = self