from colloquy.base import Base
# from .html import HTML
from .close import Close

class Commands(Base):
    
    def __init__(self, owner):
        super().__init__(owner)
        # self._html = HTML(owner=self)
        self._close = Close(owner=self)

    @property
    def close(self):
        return self._close

    @property
    def name(self):
        return "command"
        
        
    def open(self, **kwargs):
        pass