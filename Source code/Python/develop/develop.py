from yattag import Doc, indent
from serial.tools import list_ports
from .virtual_colloquy_driver import VirtualColloquyDriver
from parameters import Parameters
from tests import Tests

PARAMETERS = Parameters().as_dict()

class Develop(Tests):
    
    classes = Tests.classes.copy()  
    classes["colloquy_driver"] = VirtualColloquyDriver
    
    def __init__(self, wsgi):
        Tests.__init__(self, wsgi, name="develop")
        # self._doc = None

    