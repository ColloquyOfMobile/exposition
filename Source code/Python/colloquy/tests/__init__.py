from pathlib import Path
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
import webbrowser
import sys
# from .calibration import Calibration
# from .threads import Threads
# from .http_element import HTTPElement
from colloquy.hardware import Hardware
from utils import CustomDoc
        
class Tests():
    
    def __init__(self):
        hw = Hardware(owner=None, surname="test")
        print(f"{hw.female1.head_neopixel.toggle_on_off()=}")