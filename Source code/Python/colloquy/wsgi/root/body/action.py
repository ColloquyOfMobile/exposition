from pathlib import Path

from colloquy.wsgi.root.body.item import Item

class Action(Item):
    
    def __call__(self):
        action = self.post_data.get("action")
        if not action:
            return
        action = Path(action[0])
        key, *_ = action.parts   
        if key not in self:
            raise NotImplementedError(f"{key=}, ({action})")
        action = self[key]    
        action()
        

    @property
    def path(self):
        return Path()
            
    @property
    def name(self):
        return self.owner.name   