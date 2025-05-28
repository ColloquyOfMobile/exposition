from pathlib import Path
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
from .root import Root
# from .calibration import Calibration
from .file_handler import FileHandler
from .http_element import HTTPElement
from utils import CustomDoc

class WSGI(HTTPElement):
    def __init__(self):
        HTTPElement.__init__(self, owner=None)
        self._shut_server = False
        self.doc = None
        self.root = Root(owner=self)

        self.file_handler = FileHandler(owner=self)

        self._handler = None
        self._path = None
        self._start_response = None

    def __call__(self, environ, start_response):
        # Get the requested path from the environment
        self.doc = CustomDoc()
        # self._parse_post_data(environ)
        self._start_response = start_response
        for response in self._handle_request(environ):
            yield response

    @property
    def driver(self):
        raise NotImplementedError
        return self._driver

    @property
    def start_response(self):
        return self._start_response

    @property
    def shut_server(self):
        return self._shut_server

    @shut_server.setter
    def shut_server(self, value):
        self._shut_server = value

    # @property
    # def handler(self):
        # return self._handler

    # @handler.setter
    # def handler(self, value):
        # raise NotImplementedError

        # if value is self._handler:
            # return

        # if value is None:
            # raise NotImplementedError
            # if hasattr(self._handler, "close"):
                # self._handler.close()
            # self._handler = value
            # return

        # if self._handler is not None:
            # if hasattr(self._handler, "close"):
                # self._handler.close()

        # if hasattr(value, "open"):
            # value.open()

        # self._handler = value

    def _handle_request(self, environ):
        path = self._parse_path(environ)

        if path == Path():
            yield from self.root(environ)
            return

        yield from self.file_handler(environ)
        return

class CustomHandler(WSGIRequestHandler):

    def log_message(self, *args, **kwargs):
        return

def run():
    wsgi = WSGI()
    port = 8000
    if Path("Local/logs.txt").exists():
        Path("Local/logs.txt").unlink()
    with make_server("0.0.0.0", port, wsgi, handler_class=CustomHandler) as httpd:
        WSGIRequestHandler.log_message = lambda *args, **kwargs: None
        print(f"Serving on port {port}...")

        while not wsgi.shut_server:
            httpd.handle_request()
        print(f"Stopped server...")