from pathlib import Path
import webbrowser
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
import sys
from colloquy.base import Base


class CustomHandler(WSGIRequestHandler):

    def log_message(self, *args, **kwargs):
        return

class Start(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)

    def __call__(self):
        webbrowser.open(url=f"http://127.0.0.1:{self.owner.port}", new=2)
        self.owner.run()

    @property
    def name(self):
        return "start"


    def cli(self, request):
        print(f"Starting server on port {self.owner.port}...")
        self()
        if self.owner.events.shutdown.is_set():
            print(f"Server was shutdown.")

        if self.owner.events.restart.is_set():
            print(f"Server should restart...")
            self.owner.restart_process()

