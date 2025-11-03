from pathlib import Path
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
import webbrowser
import sys
# from .calibration import Calibration
# from .threads import Threads
# from .http_element import HTTPElement
from utils import CustomDoc
        
class Tests():
    
    def __init__(self):
        from colloquy.wsgi.root.body.workspace.hardware import Hardware
        Hardware(owner=None)