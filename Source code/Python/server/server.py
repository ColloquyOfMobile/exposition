from pathlib import Path
from urllib.parse import unquote
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import mimetypes
import os
from .root import Root
from .calibration import Calibration
from .tests import Tests
from .shutdown import Shutdown
from develop import Develop
from utils import CustomDoc

class WSGI:
    def __init__(self):
        self._shut_server = False
        self.doc = None
        self.handlers = [
            Shutdown(wsgi=self),
            Calibration(wsgi=self),
            Tests(wsgi=self),
            Develop(wsgi=self),
        ]
        self._path_handlers = {
            Path(""): Root(self),
            }
        for handler in self.handlers:
            self._path_handlers[handler.wsgi_path] = handler
        # self._path_handlers = {
            # Path("shutdown"): self._handle_shutdown,
            # Path(""): Root(self),
            # Path("calibration"): Calibration(self),
            # Path("tests"): Tests(self),
            # # Path("TATU"): Tatu(self),
        # }
        self._path_handler = None
        # self._archive_2025_01_24 = UpgradeColloquy()
        self._path = None
        self._start_response = None
        self._data = None

    @property
    def driver(self):
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
    def path_handler(self):
        return self._path_handler

    @path_handler.setter
    def path_handler(self, value):

        if value is self._path_handler:
            return

        if value is None:
            if hasattr(self._path_handler, "close"):
                self._path_handler.close()
            self._path_handler = value
            return

        if self._path_handler is not None:
            if hasattr(self._path_handler, "close"):
                self._path_handler.close()


        if hasattr(value, "open"):
            value.open()

        self._path_handler = value

    def __call__(self, environ, start_response):
        # Get the requested path from the environment
        self.doc = CustomDoc()
        self._parse_path(environ)
        self._parse_post_data(environ)
        print(f"{self._path}, {self._data}")
        self._start_response = start_response
        for response in self._handle_request():
            yield response

    def _handle_request(self):
        file_path = self._path
        self.path_handler = self._path_handlers.get(file_path)
        if self.path_handler is not None:

            for response in  self.path_handler(**self._data):
                yield response
            return

        yield from self._handle_file()

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
            # Handle other request methods or unsupported content types
            data = {}

        self._data = data

    # def _handle_archive(self,):
            # self._start_response('200 OK', [('Content-Type', 'text/html')])
            # return [self._archive_2025_01_24.html.encode()]


    def _handle_file(self):
        file_path = self._path
        try:
            # Open the requested file
            with open(file_path, 'rb') as f:
                content = f.read()

            # Use mimetypes.guess_type to determine the content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'  # Default content type

            self._start_response('200 OK', [('Content-Type', content_type)])
            yield content

        except IOError:
            # File not found
            self._start_response('404 Not Found', [('Content-Type', 'text/plain')])
            message = f'{file_path.as_posix()} not found !'
            print(message)
            yield message.encode()

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
            print(f"Finished handling request...")
        print(f"Stopped server...")