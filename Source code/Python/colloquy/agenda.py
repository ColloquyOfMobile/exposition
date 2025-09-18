from server.html_element import HTMLElement
from datetime import time


class Agenda(HTMLElement):
	
    def __init__(self, owner, params):
        HTMLElement.__init__(self, owner)
        # self._owner = owner
        self._days = []
        self._week = {}
        
        for name in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            day = Day(owner=self, name=name, params=params[name])
            setattr(self, name, day)
            
    @property
    def days(self):
        return self._days
        
    @property
    def week(self):
        return self._week
            
    @property
    def colloquy(self):
        return self.owner.colloquy
    
    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("div"):            
            for day in self._days:
                day.add_html()


class Day(HTMLElement):
	
    def __init__(self, owner, name, params):
        HTMLElement.__init__(self, owner)
        owner.days.append(self)
        owner.week[name] = self
        self._name = name
        self._state = params["state"]
        self._start = None 
        self._end = None
        
        if params["start"] is not None:
            self._start = time.fromisoformat(params["start"])
        if params["end"] is not None:
            self._end = time.fromisoformat(params["end"])
            
    @property
    def colloquy(self):
        return self.owner.colloquy
    
    @property
    def name(self):
        return self._name
        
    @property
    def state(self):
        return self._state
        
    @property
    def start(self):
        return self._start
        
    @property
    def end(self):
        return self._end
    
    def save(self):
        return self.colloquy.save()
    
    def _set_end_start(self, **kwargs):
        start = kwargs["start"][0] # gives "17:20"
        end = kwargs["end"][0]  # gives "17:20"
        
        self._start = time.fromisoformat(start)
        self._end = time.fromisoformat(end)
        self.colloquy.params["agenda"][self.name]["start"] = start
        self.colloquy.params["agenda"][self.name]["end"] = end
        self.save()
    
    def _toggle_state(self, **kwargs):
        if self._state:
            self._state = False
            self.colloquy.params["agenda"][self.name]["state"] = self._state
            self.save()
            return 
        self._state = True
        self.colloquy.params["agenda"][self.name]["state"] = self._state
        self.save()
        # raise NotImplementedError(f"{kwargs=}")
        
    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("label"):
                text(f"{self.name}: ")
            
            path =f"colloquy/{self._name}/toggle"
            self.actions[path] = self._toggle_state
            if not self._state:                
                with tag("button", name="action", value=path):
                    text("set on")
                return 
            
            with tag("button", name="action", value=path):
                text("set off")
                
            path =f"colloquy/{self._name}/set"
            
            kwargs = {}
            if self._start is not None:
                kwargs["value"]=self._start.strftime("%H:%M")
            doc.stag("input", type="time", name="start", **kwargs)
            
            
            kwargs = {}
            if self._end is not None:
                kwargs["value"]=self._end.strftime("%H:%M")
            doc.stag("input", type="time", name="end", **kwargs)
            
            with tag("button", name="action", value=path):
                text("set")
            self.actions[path] = self._set_end_start