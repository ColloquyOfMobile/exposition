from pathlib import Path
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
import webbrowser
import sys
# from .calibration import Calibration
from .shutdown import Shutdown
from .restart import Restart
from .file_handler import FileHandler
from .root import Root
from colloquy.colloquy_item import ColloquyItem
from utils import CustomDoc
from urllib.parse import unquote
import urllib.parse

class WSGI(ColloquyItem):
    def __init__(self, owner):
        ColloquyItem.__init__(self, owner)
        # self._html = HTML(owner=self)
        # self._
        self._doc = None

        self._file_handler = FileHandler(owner=self)
        self._shutdown = Shutdown(owner=self)
        self._restart = Restart(owner=self)
        
        self._root = Root(owner)

        self._handler = None
        self._path = None
        self._start_response = None

    def __call__(self, environ, start_response):
        
        self._start_response = start_response
        self._environ = environ
        try:        
            yield from self._call_1()
        except Exception:
            self.events.shutdown.set()
            raise
            
    
    @property
    def threads(self):
        return self.owner.threads
    
    @property
    def start_response(self):
        return self._start_response

    
    @property
    def request_path(self):
        """Parse the path."""
        environ = self._environ
        request_path = environ["PATH_INFO"]
        request_path = unquote(request_path)
        request_path = request_path.strip("/")
        request_path = request_path.encode("iso-8859-1").decode("utf-8")
        request_path = Path(request_path)
        return request_path
        # return request_path

    def _call_1(self):
        if not self.request_path.parts:
            yield from self.root()
            return
        key, *_ = self.request_path.parts
        
        if key in self:
            yield from self[key]()
            return
        
        yield from self.file_handler()

    def _parse_data(self, environ):
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

        self._post_data = data