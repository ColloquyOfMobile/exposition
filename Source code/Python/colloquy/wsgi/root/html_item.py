from utils import CustomDoc
import traceback
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.wsgi.item import Item as _Item

class HtmlItem(_Item):

    def __call__(self):  
        try:   
            self._call_unsafe()                    
        except Exception as exception:
            doc, tag, text = self.doc.tagtext()  
            with tag("div"):
                with tag("h2"):
                    text(f"Error html for {self.owner.name}!")
                                    
                with tag("div", style="display: flex; flex-direction: column;"):
                    style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                    for line in traceback.format_exc().splitlines():
                        with tag("pre", style=style):
                            text(line)

    @property
    def doc(self):
        # print(f"#"*50)
        # print(f"#"*50)
        # print(f"{self=}")
        # print(f"{self.owner.name=}")
        # print(f"{self.owner.owner.name=}")
        # print(f"{self.parent=}")
        return self.parent.doc

    @property
    def parent(self):
        return self.owner.owner.html
    
    def _call_unsafe(self):
        raise NotImplementedError