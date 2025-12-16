from utils import CustomDoc
import inspect
import traceback
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
import socket
from colloquy.base import Base

class BaseHTML(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._is_open = False
        self._is_details_open = False
        self._colloquy = None

        self["open details"] = self.open_details
        self["close details"] = self.close_details
        self["open"] = self.open
        self["close"] = self.close

    def __call__(self):
        try:
            html = self._call_unsafe()
        except Exception as exception:
            html = self._call_if_error()

        return html

    @property
    def is_open(self):
        return self._is_open

    @property
    def is_details_open(self):
        return self._is_details_open

    @property
    def colloquy(self):
        if self._colloquy is None:
            self._colloquy = self.owner.colloquy
        return self._colloquy

    def open(self, request):
        raise NotImplementedError

    def close(self, request=None):
        raise NotImplementedError

    def open_details(self, request):
        raise NotImplementedError

    def close_details(self, request=None):
        raise NotImplementedError

    def handle_request(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    def _call_if_error(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div"):
            with tag("h2"):
                text(f"Error in {self}!")

            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exc().splitlines():
                    with tag("pre", style=style):
                        text(line)

        return doc.getvalue()


    def _svg_down_arrow(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag('svg', width='16', height='16', viewBox='0 0 24 24', fill='none',
             stroke='currentColor', **{'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'}):
            doc.stag('polyline', points='6 9 12 15 18 9')

        return doc.getvalue()


    def _svg_right_arrow(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag('svg', width='16', height='16', viewBox='0 0 24 24', fill='none',
             stroke='currentColor', **{'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'}):
            doc.stag('polyline', points='9 6 15 12 9 18')

        return doc.getvalue()