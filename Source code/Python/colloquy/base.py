from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
import socket

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
        self._dict = {}
        self._path = None
        assert owner is not self
        self._owner = owner
        self._owners = None
        assert owner is not self.owners

    def __repr__(self):
        return f"{type(self).__name__}({self.path.as_posix()})"

    def __getitem__(self, key):
        try:
            item = self._dict[key]
        except KeyError:            
            raise KeyError(f"{key} not in {self=}")
            
        return item

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __contains__(self, key):
        return key in self._dict

    def __iter__(self):
        yield from self._dict

    @property
    def items(self):
        return self._dict.items

    @property
    def path(self):
        if self._path is not None:
            return self._path
            
        if self.owner is not None:
            self._path = self.owner.path / self.name
            return self._path
            
        self._path = Path()
        return self._path

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
    
    @property
    def is_simulated(self):
        if socket.gethostname() == 'Colloquy-Laptop':
            return False
        return True
    
    def add(self, element):
        self[element.name] = element