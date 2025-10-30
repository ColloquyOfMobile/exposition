from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse

class ColloquyItem:

    @staticmethod
    def retrieve_call_origin():
        """Used for debug."""
        stack = inspect.stack()
        if len(stack) > 2:
            caller_frame = stack[2]
            caller_filename = caller_frame.filename  # File where the call happened
            caller_lineno = caller_frame.lineno      # Line number of the call
            return f"{caller_filename}:{caller_lineno}"
        else:
            return "unknown origin"

    def __init__(self, owner):
        self._owner = owner
        self._elements = {}

    def __getitem__(self, key):
        return self._elements[key]

    def __setitem__(self, key, value):
        self._elements[key] = value

    def __contains__(self, key):
        return key in self._elements

    def __repr__(self):
        return f"{type(self).__name__}({self.path.as_posix()})"

    @property
    def path(self):
        return self.owner.path / self.name

    @property
    def owner(self):
        return self._owner
    
    @property
    def events(self):
        return self.owner.events    
    
    def add(self, element):
        self[element.name] = element