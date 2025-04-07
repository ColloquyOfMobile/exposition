from pathlib import Path
from urllib.parse import unquote
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
from .root import Root
# from .calibration import Calibration
from .file_handler import FileHandler
from utils import CustomDoc

class WSGI:
    def __init__(self):
        self._shut_server = False
        self.doc = None
        self.root = Root(wsgi=self)

        self.file_handler = FileHandler(wsgi=self)

        self._handler = None
        self._path = None
        self._start_response = None
        self._data = None

    def __call__(self, environ, start_response):
        # Get the requested path from the environment
        self.doc = CustomDoc()
        self._parse_path(environ)
        self._parse_post_data(environ)
        print(f"{self._path}, {self._data}")
        self._start_response = start_response
        for response in self._handle_request():
            yield response

    @property
    def path(self):
        return self._path

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

    @property
    def handler(self):
        return self._handler

    @handler.setter
    def handler(self, value):
        raise NotImplementedError

        if value is self._handler:
            return

        if value is None:
            raise NotImplementedError
            if hasattr(self._handler, "close"):
                self._handler.close()
            self._handler = value
            return

        if self._handler is not None:
            if hasattr(self._handler, "close"):
                self._handler.close()


        if hasattr(value, "open"):
            value.open()

        self._handler = value

    def _handle_request(self):

        path = Path(*self.path.parts[:1])

        if path == Path():
            yield from self.root(**self._data)
            return

        if path.exists():
            yield from self.file_handler()
            return

        if path in self.root.handlers:
            yield from self.root(**self._data)
            return

        # File not found
        self.start_response('404 Not Found', [('Content-Type', 'text/plain')])
        message = f'{path.as_posix()} not found !'
        print(message)
        yield message.encode()

    def _set_handler(self):
        # path = self._path
        for path in reversed(self._path.parents):
            self.handler = self.handlers.get(path, self.file_handler)


    def _parse_path(self, environ):
        """Parse the path."""
        request_path = environ["PATH_INFO"]
        request_path = unquote(request_path)
        request_path = request_path.strip("/")
        request_path = request_path.encode("iso-8859-1").decode("utf-8")
        request_path = Path(request_path)
        self._path = request_path

    def _parse_post_data(self, environ):
        """Parse the form data."""
        method = environ.get('REQUEST_METHOD', 'GET')
        content_type = environ.get('CONTENT_TYPE', '')

        # Parse form data for POST requests
        if method == 'POST' and content_type.startswith('multipart/form-data'):
            form_data = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
            data = {key: form_data[key].value for key in form_data}
            raise NotImplementedError()

        elif method == 'POST' and content_type.startswith('application/x-www-form-urlencoded'):
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            post_data = environ['wsgi.input'].read(content_length)
            data = urllib.parse.parse_qs(post_data.decode('utf-8'))

        else:
            data = {}

        self._data = data

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