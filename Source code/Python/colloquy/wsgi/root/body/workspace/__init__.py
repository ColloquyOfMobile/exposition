from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.item import Item
from pathlib import Path
import traceback
from .html import HTML
from .parameters import Parameters
from .hardware import Hardware
from .exception_handler import ExceptionHandler
from .tests import Tests

class Workspace(Item):
    
    def __init__(self, owner):
        Item.__init__(self, owner)
        self._opened = None
        self._html = HTML(owner=self)
        self._action = Action(owner=self)
        
        self._params = Parameters(owner=self)
        self._hardware = Hardware(owner=self)
        self._exception = ExceptionHandler(owner=self) 
        self._tests = Tests(owner=self)
        
        
        if False: 
            raise NotImplementedError
            # self._is_started = True
            # self._owner = owner
            # self._actions = {}
            # self.path = Path("")
            # self._log = Logger(owner=self)
            # self._opened = None
            # self._items = {}
            # self.elements = set()
            # self.threads = set()     
            self._exposition = Exposition(owner=self)
            self._agenda = Agenda(owner=self, params=self.params["agenda"])
        if not self.params.is_calibrated:
            self.params.open()

    @property
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        # Value is None only in a Close(), this is to avoid recursion.
        if value is not None:
            if self._opened is not None:
                self._opened.close()
                
        self._opened = value

    @property
    def name(self):
        return "workspace"

    @property
    def workspace(self):
        return self

    @property
    def params(self):
        return self._params

    @property
    def exception(self):
        return self._exception
        
        
########################################################################################
    @property
    def near_origin_threashold(self):
        return self._params["near_origin_threashold"]

    @near_origin_threashold.setter
    def near_origin_threashold(self, value):
        self._params["near_origin_threashold"] = value 

    @property
    def hardware(self):
        return self._hardware

    @property
    def exposition(self):
        return self._exposition

    @property
    def tests(self):
        return self._tests

    @property
    def agenda(self):
        return self._agenda   

    @property
    def log(self):
        return self._log

    
    # def stop(self):
        # # self.events.shut.shut_server = True
        # self._is_started = False
        # self._shutdown_event.set()
        # # if self._exposition.is_started:
        # self._exposition.stop()
        # self._tests.stop()
        
        # # self._exposition.join()
        # self._tests.join()
            
        # if self._hardware.is_started:
            # self._hardware.stop()
            # print("Waiting hardware thread to stop...")
            # self._hardware.join()
        # print("... exposition and tests threads stopped.")
        
        
        
        

class Action(ActionItem):
    
    def __call__(self):
        try:
            # action = self.post_data.get("action")   
            # if not action:
                # return
            # print(f"{action=}")
            # print(f"{action[0]=}")
            # print(f"{Path=}")
            # action = Path(action[0])
            
            key, *_ = self.request.parts
            if key not in self:
                raise NotImplementedError(f"{key=}, ({action})")
            action = self[key]
            action()
        except Exception as exception:
            traceback.print_exc()
            self.owner.exception.value = exception