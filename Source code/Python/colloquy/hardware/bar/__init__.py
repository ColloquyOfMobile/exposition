from pathlib import Path
from colloquy.base_thread import BaseThread
from .dxl_origin import DXLOrigin
from .dxl_position import DXLPosition
from .search import Search
from .html import HTML


class Bar(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._position_memory = None
        
        self._motion_range = 10000
        self._dxl_origin = DXLOrigin(owner=self)
        self._position = DXLPosition(owner=self)
        
        self._dxl = owner.u2d2.dxls[self.name]
        self._html = HTML(owner=self)

        self._search = Search(owner=self)
        
        self[self.html.name] = self.html.handle_request
        self[self.search.name] = self.search
        self[self.dxl_origin.name] = self.dxl_origin
        self[self.position.name] = self.position
        self["set current position as dxl origin"] = self.set_current_position_as_dxl_origin

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def params(self):
        return self.owner.params

    @property
    def dxl_origin(self):
        return self._dxl_origin

    @property
    def dxl(self):
        return self._dxl
    @property
    def search(self):
        return self._search

    @property
    def drives(self):
        return self._drives

    @property
    def html(self):
        return self._html

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return "bar"

    @property
    def is_moving(self):
        return self.dxl.is_moving
    
    @property
    def position(self):
        return self._position
    
    @property
    def goal_position(self):         
        return self.dxl.goal_position
    
    @property
    def torque_enabled(self):
        return self.dxl.torque_enabled
    
    @property
    def males(self):
        return self.owner.males
    
    def set_current_position_as_dxl_origin(self, request=None):
        self.dxl_origin.set(self.dxl.position.read())

    def turn_to_max_position(self):
        value = self._dxl_origin.get() + self._motion_range/2
        self.dxl.goal_position.write(value)
        self._position_memory = "max"

    def turn_to_min_position(self):
        value = self._dxl_origin.get() - self._motion_range/2
        self.dxl.goal_position.write(value)
        self._position_memory = "min"

    def toggle_position(self):
        if self._position_memory is None:
            self.turn_to_max_position()
            return

        if self._position_memory == "max":
            self.turn_to_min_position()
            return

        if self._position_memory == "min":
            self.turn_to_max_position()
            return

    def loop(self):   
        if self.search.is_started:
            return
            
        for male in self.males:
            if male.search.is_started:
                self.search.start(started_by=self)
                return

    def setup(self):
        self.dxl.init_hardware()
        return

    def setdown(self):
        return
        
    def get_states(self, *args):
        states = {
            "path": ("hardware", self.name),
            "name": self.name,
        }
        if args:
            raise NotImplementedError(self)
        return states