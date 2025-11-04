from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse

class Base:

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
        assert owner is not self
        self._owner = owner
        self._owners = None
        assert owner is not self.owners
        
        self._dict = {}

    def __repr__(self):
        return f"{type(self).__name__}({self.path.as_posix()})"

    def __getitem__(self, key):
        try:
            item = self._dict[key]
        except KeyError:            
            raise KeyError(f"{key} not in {self=}")
            
        return item # self._elements[key]

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __contains__(self, key):
        return key in self._dict

    @property
    def items(self):
        return self._dict.items

    @property
    def path(self):
        if self.owner is None:
            return Path()
        return self.owner.path / self.name

    @property
    def owner(self):
        return self._owner

    @property
    def owners(self):
        if self.owner is None:
            return []
        if self._owners is None:
            self._owners = [self.owner] + self.owner.owners
        return self._owners
    
    @property
    def events(self):
        return self.owner.events    
    
    def add(self, element):
        self[element.name] = element