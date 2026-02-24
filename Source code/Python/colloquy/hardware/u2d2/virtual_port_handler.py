from time import sleep
import json
from pathlib import Path
import re
from queue import Queue

class VirtualPortHandler:

    def __init__(self, port):
        self._port = port
        self.is_using = False
    
    def setBaudRate(self, *args, **kwargs):
        return
    
    def closePort(self, *args, **kwargs):
        return
    
    def writePort(self, *args, **kwargs):
        return
    
    def clearPort(self, *args, **kwargs):
        return


    

