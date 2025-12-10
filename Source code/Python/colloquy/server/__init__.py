from pathlib import Path
import webbrowser
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
import sys
from colloquy.base import Base
from .wsgi import WSGI
from .cli import CLI
from .start import Start
from .restarted import Restarted


class CustomHandler(WSGIRequestHandler):

    def log_message(self, *args, **kwargs):
        return

class Server(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._wsgi = WSGI(owner=self)
        self._start = Start(owner=self)
        self._restarted = Restarted(owner=self)
        self._cli = CLI(owner=self)


    @property
    def name(self):
        return "server"

    @property
    def cli(self):
        return self._cli

    @property
    def wsgi(self):
        return self._wsgi

    @property
    def port(self):
        return 8000

    @property
    def start(self):
        return self._start

    @property
    def restarted(self):
        return self._restarted

    @property
    def colloquy(self):
        return self.owner.colloquy

    def restart_process(self):
        python = sys.executable
        args = ["main.py", "server/restarted"]
        # args.append()
        os.execl(python, python, *args)


    def run(self):
        with make_server("0.0.0.0", self.port, self.wsgi, handler_class=CustomHandler) as httpd:

            while True:
                httpd.handle_request()
                if self.events.shutdown.is_set():
                    self.owner.colloquy.shutdown()
                    break

