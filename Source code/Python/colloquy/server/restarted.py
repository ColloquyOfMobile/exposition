from pathlib import Path
import webbrowser
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
import sys
from colloquy.base import Base


class Restarted(Base):
    
    def __init__(self, owner):
        super().__init__(owner=owner)
    
    def __call__(self):        
        self.owner.run()
    
    @property
    def name(self):
        return "restarted"
    
    
    def cli(self, request):
        print(f"Restarting server on port {self.owner.port}...")
        self()
        if self.owner.events.shutdown.is_set():
            print(f"Server was shutdown.")            
        if self.owner.events.restart.is_set():
            print(f"Server should restart...")
            self.owner.restart_process()
        
            