import traceback
# from colloquy.wsgi.root.item import Item
from utils import CustomDoc
from colloquy.base import Base
from .share_commands import Commands



class ExceptionHandler(Base):
    
    def __init__(self, owner):
        super().__init__(owner)
        self._value = None
        # self._html = HTML(owner=self)
        self._commands = Commands(owner=self)

    
    @property
    def commands(self):
        return self._commands
        
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self.open()
        self._value = value

    @property
    def name(self):
        return "exception"
        
    @property
    def opened(self):
        return self.owner.opened
        
    @opened.setter
    def opened(self, value):
        self.owner.opened = value
        
    @property
    def close(self):
        return self.commands.close
        
    def open(self):
        self.owner.opened = self
        
    def is_opened(self):
        self.owner.opened is self
        

# class HTML(HtmlItem):
        
    # def __call__(self, parent_doc):
        # self._doc = CustomDoc()
        # doc, tag, text = self.doc.tagtext()
        # with tag("div", style="display: flex; flex-direction: column;"):
            # with tag("h2"):
                # text(f"{repr(self.owner.value)}")
                
            # self.owner.commands.html()
                
            # with tag("div", style="display: flex; flex-direction: column;"):
                # style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                # for line in traceback.format_exception(self.owner.value):
                    # with tag("pre", style=style):
                        # text(line)
        # self.parent.doc.asis(self.doc.getvalue()) 
            
            # # with tag("pre", ):
                # # text(traceback.format_exception(self.owner.value))

    # @property
    # def name(self):
        # return "HTML"