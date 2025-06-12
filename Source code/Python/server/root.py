from pathlib import Path
from colloquy import Colloquy
from virtual_colloquy import VirtualColloquy
import socket
from .file_handler import FileHandler
from .shutdown import Shutdown
from .html_element import HTMLElement
from parameters import Parameters
from colloquy.logger import Logger as _Logger

class Root(HTMLElement):
    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._owner = owner
        self._actions = {}
        self.path = Path("")
        self._log = Logger(owner=self)
        self._opened = None
        self._items = {}
        self.elements = set()
        self.threads = set()
        self._colloquy = None
        self.init()

    def __call__(self, environ):
        self._init_html_doc()
        self.write_html(environ)
        return [self.html_doc.getvalue().encode()]

    @property
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        self._opened = value

    @property
    def log(self):
        return self._log

    def init(self):
        hostname = socket.gethostname()
        if hostname == "DESKTOP-MRSLS88":
            self._items["colloquy"] = self._colloquy = VirtualColloquy(owner=self)
            return

        self._items["colloquy"] = self._colloquy = Colloquy(owner=self)


    def write_html(self, environ):
        self._parse_data(environ)
        data = self.post_data
        action = data.get("action")
        doc, tag, text = self.html_doc.tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            self._write_html_head()
            
            if action == ["shutdown"]:
                self.owner.shut_server = True
                with tag("body"):
                    text("Goodbye !")
                return
                # raise NotImplementedError

            self._write_body()

    def _write_html_head(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("head"):
            with tag("title"):
                text(f"Colloquy of Mobiles")
            doc.asis(
                '<meta name="viewport"'
                ' content="width=device-width,'
                " initial-scale=1,"
                ' interopened-widget=resizes-content" />'
            )

    def _write_body(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("body"):
            with tag("div", style="display: flex; "):
                with tag("h1", style="display: flex; flex: 1; justify-items: center;"):
                    text(
                        f"Colloquy of Mobiles"
                        )

                with tag("form", method="post", style="display: flex;"):
                    with tag("button", name="action", value="shutdown", style="align-self:center;"):
                        text(f"Shutdown.")

            data = self.post_data

            action = data.get("action")
            if action:
                action = action[0]
            action = self.actions.get(action, )
            if action:
                action(**data)
            return self._write_root()
            # raise NotImplementedError(f"{data=}")

    def _write_root(self, **data):
        doc, tag, text = self.html_doc.tagtext()
        with tag("div"):
            self._colloquy.write_html()

    def _handle_request(self, environ):
        if not kwargs:
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