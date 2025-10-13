from colloquy.wsgi.item import Item
from pathlib import Path
import os
import sys
from time import sleep

class Restart(Item):
    def __init__(self, owner):
        Item.__init__(self, owner)

    def __call__(self, **kwargs):
        raise NotImplementedError()
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