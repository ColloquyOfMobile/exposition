from pathlib import Path
import urllib
import os
import sys
from colloquy.base import Base
from .file_handler import FileHandler
from .root import Root
from .head import Head
from .commands import Commands
# from colloquy.colloquy_item import ColloquyItem
from utils import CustomDoc
from urllib.parse import unquote
import urllib.parse

class WSGI(Base):
    def __init__(self, owner):
        Base.__init__(self, owner)
        self._server = owner
        self._doc = None
        self._head = Head(owner=self)
        self._commands= Commands(owner=self)

        self._file_handler = FileHandler(owner=self)

        self._root = Root(owner=self)

        self._handler = None
        self._path = None
        self._start_response = None
        self._post_data = None

        self["shutdown"] = self.commands.shutdown
        self["restart"] = self.commands.restart
        self["hardware"] = self.colloquy.hardware
        self["tests"] = self.colloquy.tests
        self["exposition"] = self.colloquy.exposition
        # self["workspace"] = self.root.body.workspace.handle_request

    def __call__(self, environ, start_response):
        self._start_response = start_response
        self._environ = environ
        self._post_data = self.parse_data()
        print(f"request: {self.request}")
        print(f"post_data: {self._post_data}")
        try:
            yield from self._call_unsafe()
        except Exception:
            self.events.shutdown.set()
            raise

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def name(self):
        return "WSGI"

    @property
    def server(self):
        return self._server

    @property
    def head(self):
        return self._head

    @property
    def file_handler(self):
        return self._file_handler


    @property
    def environ(self):
        return self._environ


    @property
    def root(self):
        return self._root


    @property
    def threads(self):
        return self.owner.threads

    @property
    def start_response(self):
        return self._start_response


    @property
    def request(self):
        """Parse the path."""
        environ = self._environ
        request = environ["PATH_INFO"]
        request = unquote(request)
        request = request.strip("/")
        request = request.encode("iso-8859-1").decode("utf-8")
        request = Path(request)
        return request

    @property
    def post_data(self):
        return self._post_data

    @property
    def commands(self):
        return self._commands

    def parse_data(self):
        """Parse the form data."""
        environ = self.environ
        method = environ.get('REQUEST_METHOD', 'GET')
        content_type = environ.get('CONTENT_TYPE', '')

        # Parse form data for POST requests
        if method == 'POST' and content_type.startswith('application/x-www-form-urlencoded'):
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            post_data = environ['wsgi.input'].read(content_length)
            data = urllib.parse.parse_qs(post_data.decode('utf-8'))

        else:
            data = {}
        return data

    @property
    def wsgi(self):
        return self

    @property
    def hardware(self):
        if self._hardware is None:
            self._hardware = self.owner.hardware
        return self._hardware

    def _call_unsafe(self):
        if not self.request.parts:
            yield from self.root()
            return

        key, *leftover = self.request.parts

        if key in self:
            self[key](request="/".join(leftover))
            yield from self.root()
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