from server.http_element import HTTPElement
from pathlib import Path
import os
import sys
from time import sleep

class Restart(HTTPElement):
    def __init__(self, owner):
        HTTPElement.__init__(self, owner)
        self.path = Path("restart")

    def __eq__(self, other):
        return other.name == self.name

    def __lt__(self, other):
        return self.name < other.name

    def __call__(self, **kwargs):
        self.owner.shut_server = True
        self.owner.start_response('200 OK', [('Content-Type', 'text/plain')])
        
        text = b'Restarting... Refresh the page to see changes.'
        yield text
        print(text)
        sleep(0.5)
        
        self.owner.restart_server = True

    @property
    def name(self):
        return "restart"

    def open(self):
        pass

    def close(self):
        pass