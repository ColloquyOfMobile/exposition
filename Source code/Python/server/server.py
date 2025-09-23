from pathlib import Path
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
from colloquy import Colloquy
import webbrowser
# from .calibration import Calibration
from .shutdown import Shutdown
from .restart import Restart
from .file_handler import FileHandler
from .http_element import HTTPElement
from utils import CustomDoc

class WSGI(HTTPElement):
    def __init__(self):
        HTTPElement.__init__(self, owner=None)
        self._shut_server = False
        self.doc = None
        self.colloquy = Colloquy(owner=self)

        self.file_handler = FileHandler(owner=self)
        self.shutdown = Shutdown(owner=self)
        self.restart = Restart(owner=self)

        self._handler = None
        self._path = None
        self._start_response = None

    def __call__(self, environ, start_response):
        self._start_response = start_response
        for response in self._handle_request(environ):
            yield response
    
    @property
    def start_response(self):
        return self._start_response

    @property
    def shut_server(self):
        return self._shut_server

    @shut_server.setter
    def shut_server(self, value):
        self._shut_server = value

    def _handle_request(self, environ):
        path = self._parse_path(environ)

        if path == Path():
            yield from self.colloquy(environ)
            return

        if path == Path("shutdown"):
            yield from self.shutdown()
            return

        if path == Path("restart"):
            yield from self.restart()
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
        
        webbrowser.open(url=f"http://127.0.0.1:{port}", new=2)
        # raise NotImplementedError("Implement a way to restart the process.")

        while not wsgi.shut_server:
            httpd.handle_request()
        print(f"Stopped server...")